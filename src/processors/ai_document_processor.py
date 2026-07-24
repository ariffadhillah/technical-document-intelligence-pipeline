from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
import json

from pydantic import ValidationError

from src.config.settings import Settings
from src.prompts.document_prompt import (
    SYSTEM_PROMPT,
    build_document_prompt,
)
from src.providers.openai_provider import (
    OpenAIProvider,
    OpenAIProviderError,
)
from src.schemas.document_intelligence import (
    DocumentIntelligenceResult,
)


AI_PROCESSING_VERSION = "1.0.0"


@dataclass
class AIProcessingStats:
    """
    Aggregate statistics for one AI processing run.
    """

    total_attachments: int = 0
    eligible_attachments: int = 0
    processed: int = 0
    cached: int = 0
    skipped: int = 0
    failed: int = 0


class AIDocumentProcessor:
    """
    Process OCR-completed attachments using an AI provider.

    Each attachment result is cached in an individual JSON file.
    """

    def __init__(
        self,
        settings: Settings,
        provider: OpenAIProvider,
        output_directory: Path,
        force: bool = False,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.output_directory = output_directory
        self.force = force

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def process_thread(
        self,
        thread_data: dict[str, Any],
    ) -> tuple[dict[str, Any], AIProcessingStats]:
        """
        Process every eligible attachment in a thread.

        Returns:
            Enriched thread data and processing statistics.
        """

        stats = AIProcessingStats()

        for post in thread_data.get("posts", []):
            attachments = post.get("attachments", [])

            for attachment in attachments:
                stats.total_attachments += 1

                if not self._is_eligible(attachment):
                    self._mark_skipped_attachment(
                        attachment=attachment,
                    )
                    stats.skipped += 1
                    continue

                stats.eligible_attachments += 1

                try:
                    result, was_cached = (
                        self.process_attachment(
                            attachment=attachment,
                        )
                    )

                    attachment["ai"] = result

                    if was_cached:
                        stats.cached += 1
                    else:
                        stats.processed += 1

                except Exception as error:
                    attachment["ai"] = (
                        self._build_failed_result(
                            error=error,
                        )
                    )

                    stats.failed += 1

        self._update_thread_metadata(
            thread_data=thread_data,
            stats=stats,
        )

        return thread_data, stats

    def process_attachment(
        self,
        attachment: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        """
        Process one OCR attachment.

        Returns:
            A tuple containing the AI result dictionary and
            whether the result was loaded from cache.
        """

        filename = attachment.get(
            "filename",
            "unknown_attachment",
        )

        raw_ocr_text = (
            attachment
            .get("ocr", {})
            .get("raw_text", "")
        ).strip()

        if not raw_ocr_text:
            raise ValueError(
                f"OCR text is empty for {filename}."
            )

        input_hash = self._build_input_hash(
            filename=filename,
            raw_ocr_text=raw_ocr_text,
        )

        cache_path = self._build_cache_path(
            filename=filename,
        )

        if not self.force:
            cached_result = self._load_valid_cache(
                cache_path=cache_path,
                expected_input_hash=input_hash,
            )

            if cached_result is not None:
                return cached_result, True

        user_prompt = build_document_prompt(
            filename=filename,
            raw_ocr_text=raw_ocr_text,
        )

        parsed_result = (
            self.provider.generate_structured(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_schema=(
                    DocumentIntelligenceResult
                ),
            )
        )

        result_payload = self._build_success_result(
            filename=filename,
            input_hash=input_hash,
            parsed_result=parsed_result,
        )

        self._save_json(
            file_path=cache_path,
            payload=result_payload,
        )

        return result_payload, False

    def _is_eligible(
        self,
        attachment: dict[str, Any],
    ) -> bool:
        """
        Return True when an attachment has usable OCR text.
        """

        file_status = attachment.get(
            "file_status",
            "",
        )

        ocr = attachment.get("ocr", {})

        processing_status = ocr.get(
            "processing_status",
            "",
        )

        raw_text = ocr.get(
            "raw_text",
            "",
        )

        return (
            file_status == "available"
            and processing_status == "ocr_completed"
            and bool(raw_text.strip())
        )

    def _build_input_hash(
        self,
        filename: str,
        raw_ocr_text: str,
    ) -> str:
        """
        Build a reproducible fingerprint for cache validation.

        Changing the OCR text, model, prompt, schema, or processing
        version invalidates the existing result.
        """

        schema_json = (
            DocumentIntelligenceResult
            .model_json_schema()
        )

        hash_payload = {
            "filename": filename,
            "raw_ocr_text": raw_ocr_text,
            "provider": self.settings.ai_provider,
            "model": self.settings.openai_model,
            "system_prompt": SYSTEM_PROMPT,
            "schema": schema_json,
            "processing_version": (
                AI_PROCESSING_VERSION
            ),
        }

        serialized_payload = json.dumps(
            hash_payload,
            ensure_ascii=False,
            sort_keys=True,
        )

        return sha256(
            serialized_payload.encode("utf-8")
        ).hexdigest()

    def _build_cache_path(
        self,
        filename: str,
    ) -> Path:
        """
        Build a safe cache filename.
        """

        source_path = Path(filename)

        safe_stem = "".join(
            character
            if character.isalnum()
            or character in {"-", "_"}
            else "_"
            for character in source_path.stem
        )

        return (
            self.output_directory
            / f"{safe_stem}_document_intelligence.json"
        )

    def _load_valid_cache(
        self,
        cache_path: Path,
        expected_input_hash: str,
    ) -> dict[str, Any] | None:
        """
        Load cache only when its fingerprint is still valid.
        """

        if not cache_path.exists():
            return None

        try:
            cached_payload = json.loads(
                cache_path.read_text(
                    encoding="utf-8",
                )
            )

        except (
            OSError,
            json.JSONDecodeError,
        ):
            return None

        if (
            cached_payload.get("input_hash")
            != expected_input_hash
        ):
            return None

        if (
            cached_payload.get("processing_status")
            != "ai_completed"
        ):
            return None

        result_data = cached_payload.get("result")

        if not isinstance(result_data, dict):
            return None

        try:
            DocumentIntelligenceResult.model_validate(
                result_data
            )

        except ValidationError:
            return None

        return cached_payload

    def _build_success_result(
        self,
        filename: str,
        input_hash: str,
        parsed_result: DocumentIntelligenceResult,
    ) -> dict[str, Any]:
        """
        Build a traceable AI result record.
        """

        return {
            "processing_status": "ai_completed",
            "provider": self.settings.ai_provider,
            "model": self.settings.openai_model,
            "processing_version": (
                AI_PROCESSING_VERSION
            ),
            "processed_at": self._utc_now(),
            "filename": filename,
            "input_hash": input_hash,
            "result": parsed_result.model_dump(
                mode="json",
            ),
            "error": None,
        }

    def _build_failed_result(
        self,
        error: Exception,
    ) -> dict[str, Any]:
        """
        Build a safe failure record.
        """

        if isinstance(error, OpenAIProviderError):
            error_type = "provider_error"
        elif isinstance(error, ValidationError):
            error_type = "validation_error"
        elif isinstance(error, ValueError):
            error_type = "input_error"
        else:
            error_type = type(error).__name__

        return {
            "processing_status": "ai_failed",
            "provider": self.settings.ai_provider,
            "model": self.settings.openai_model,
            "processing_version": (
                AI_PROCESSING_VERSION
            ),
            "processed_at": self._utc_now(),
            "result": None,
            "error": {
                "type": error_type,
                "message": str(error),
            },
        }

    def _mark_skipped_attachment(
        self,
        attachment: dict[str, Any],
    ) -> None:
        """
        Add an explicit AI status for an ineligible attachment.
        """

        ocr_status = (
            attachment
            .get("ocr", {})
            .get("processing_status")
        )

        file_status = attachment.get(
            "file_status",
        )

        attachment["ai"] = {
            "processing_status": "ai_skipped",
            "provider": self.settings.ai_provider,
            "model": self.settings.openai_model,
            "processing_version": (
                AI_PROCESSING_VERSION
            ),
            "processed_at": self._utc_now(),
            "result": None,
            "error": None,
            "skip_reason": (
                f"Attachment is not eligible. "
                f"file_status={file_status}, "
                f"ocr_status={ocr_status}"
            ),
        }

    def _update_thread_metadata(
        self,
        thread_data: dict[str, Any],
        stats: AIProcessingStats,
    ) -> None:
        """
        Store AI processing information in thread metadata.
        """

        metadata = thread_data.setdefault(
            "metadata",
            {},
        )

        metadata["processing_status"] = (
            "ai_enriched"
        )

        metadata["ai_processing"] = {
            "provider": self.settings.ai_provider,
            "model": self.settings.openai_model,
            "processing_version": (
                AI_PROCESSING_VERSION
            ),
            "processed_at": self._utc_now(),
            "total_attachments": (
                stats.total_attachments
            ),
            "eligible_attachments": (
                stats.eligible_attachments
            ),
            "processed": stats.processed,
            "cached": stats.cached,
            "skipped": stats.skipped,
            "failed": stats.failed,
        }

    @staticmethod
    def _save_json(
        file_path: Path,
        payload: dict[str, Any],
    ) -> None:
        """
        Save a dictionary as formatted UTF-8 JSON.
        """

        file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = file_path.with_suffix(
            file_path.suffix + ".tmp"
        )

        temporary_path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        temporary_path.replace(file_path)

    @staticmethod
    def _utc_now() -> str:
        """
        Return the current UTC timestamp.
        """

        return (
            datetime.now(timezone.utc)
            .isoformat()
        )