from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.schemas.technical_knowledge import (
    StructuredTechnicalDocument,
)


class PromptBuilderError(ValueError):
    """
    Raised when a prompt cannot be built from the supplied
    aggregated document.
    """


@dataclass(frozen=True)
class BuiltPrompt:
    prompt_name: str
    prompt_version: str

    document_id: str
    document_type: str
    title: str

    system_prompt: str
    user_prompt: str

    system_prompt_sha256: str
    user_prompt_sha256: str
    source_content_sha256: str

    source_character_count: int
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TechnicalPromptBuilder:
    """
    Builds versioned prompts for structured technical
    knowledge extraction.

    This component does not communicate with an LLM provider.
    """

    PROMPT_NAME = "technical_extraction"
    PROMPT_VERSION = "v2"

    DEFAULT_SOURCE_LANGUAGE = "de"
    DEFAULT_OUTPUT_LANGUAGE = "en"
    DEFAULT_DOCUMENT_TYPE = "forum_thread"

    def __init__(
        self,
        templates_directory: Path | None = None,
        max_content_characters: int | None = None,
    ) -> None:
        project_root = Path(__file__).resolve().parents[2]

        self.templates_directory = (
            templates_directory
            or project_root / "src" / "prompts" / "templates"
        )

        self.max_content_characters = max_content_characters

        self.system_template_path = (
            self.templates_directory
            / "technical_extraction_system_v2.md"
        )

        self.user_template_path = (
            self.templates_directory
            / "technical_extraction_user_v2.md"
        )

    def build(
        self,
        aggregated_document: dict[str, Any],
    ) -> BuiltPrompt:
        document_id = self._extract_required_string(
            aggregated_document,
            "document_id",
        )

        title = self._extract_required_string(
            aggregated_document,
            "title",
        )

        document_type = self._extract_optional_string(
            aggregated_document,
            "document_type",
            default=self.DEFAULT_DOCUMENT_TYPE,
        )

        source_language = self._extract_optional_string(
            aggregated_document,
            "source_language",
            default=self.DEFAULT_SOURCE_LANGUAGE,
        )

        output_language = self._extract_optional_string(
            aggregated_document,
            "output_language",
            default=self.DEFAULT_OUTPUT_LANGUAGE,
        )

        source = aggregated_document.get("source", {})

        if not isinstance(source, dict):
            raise PromptBuilderError(
                "aggregated_document.source must be an object."
            )

        document_content = self._extract_document_content(
            aggregated_document
        )

        if self.max_content_characters is not None:
            document_content = document_content[
                : self.max_content_characters
            ]

        system_template = self._load_template(
            self.system_template_path
        )

        user_template = self._load_template(
            self.user_template_path
        )

        json_schema = (
            StructuredTechnicalDocument.model_json_schema()
        )

        source_metadata_text = json.dumps(
            source,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        json_schema_text = json.dumps(
            json_schema,
            ensure_ascii=False,
            indent=2,
        )

        user_prompt = self._render_template(
            template=user_template,
            replacements={
                "DOCUMENT_ID": document_id,
                "DOCUMENT_TYPE": document_type,
                "TITLE": title,
                "SOURCE_LANGUAGE": source_language,
                "OUTPUT_LANGUAGE": output_language,
                "SOURCE_METADATA": source_metadata_text,
                "JSON_SCHEMA": json_schema_text,
                "DOCUMENT_CONTENT": document_content,
            },
        )

        return BuiltPrompt(
            prompt_name=self.PROMPT_NAME,
            prompt_version=self.PROMPT_VERSION,
            document_id=document_id,
            document_type=document_type,
            title=title,
            system_prompt=system_template.strip(),
            user_prompt=user_prompt.strip(),
            system_prompt_sha256=self._sha256_text(
                system_template.strip()
            ),
            user_prompt_sha256=self._sha256_text(
                user_prompt.strip()
            ),
            source_content_sha256=self._sha256_text(
                document_content
            ),
            source_character_count=len(document_content),
            generated_at=datetime.now(
                timezone.utc
            ).isoformat(),
        )

    def build_from_file(
        self,
        input_path: Path,
    ) -> BuiltPrompt:
        if not input_path.exists():
            raise FileNotFoundError(
                f"Aggregated JSON file not found: {input_path}"
            )

        try:
            payload = json.loads(
                input_path.read_text(encoding="utf-8")
            )

        except json.JSONDecodeError as error:
            raise PromptBuilderError(
                "Aggregated file contains invalid JSON. "
                f"Line {error.lineno}, column {error.colno}: "
                f"{error.msg}"
            ) from error

        if not isinstance(payload, dict):
            raise PromptBuilderError(
                "Aggregated JSON root must be an object."
            )

        return self.build(payload)

    def save_prompt_bundle(
        self,
        prompt: BuiltPrompt,
        output_directory: Path,
    ) -> dict[str, Path]:
        """
        Saves an auditable prompt bundle.

        output_directory/
            system_prompt.md
            user_prompt.md
            prompt_metadata.json
        """

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        system_prompt_path = (
            output_directory / "system_prompt.md"
        )

        user_prompt_path = (
            output_directory / "user_prompt.md"
        )

        metadata_path = (
            output_directory / "prompt_metadata.json"
        )

        self._atomic_write_text(
            output_path=system_prompt_path,
            content=prompt.system_prompt + "\n",
        )

        self._atomic_write_text(
            output_path=user_prompt_path,
            content=prompt.user_prompt + "\n",
        )

        metadata = prompt.to_dict()

        # Avoid duplicating the full prompt bodies inside metadata.
        metadata.pop("system_prompt", None)
        metadata.pop("user_prompt", None)

        self._atomic_write_text(
            output_path=metadata_path,
            content=json.dumps(
                metadata,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
        )

        return {
            "system_prompt": system_prompt_path,
            "user_prompt": user_prompt_path,
            "metadata": metadata_path,
        }

    def _extract_document_content(
        self,
        aggregated_document: dict[str, Any],
    ) -> str:
        content = aggregated_document.get("content")

        if isinstance(content, dict):
            candidate_fields = (
                "combined_text",
                "translated_text",
                "forum_text",
                "attachment_text",
            )

            for field_name in candidate_fields:
                value = content.get(field_name)

                if isinstance(value, str) and value.strip():
                    return value.strip()

        candidate_root_fields = (
            "combined_text",
            "document_text",
            "text",
            "content_text",
        )

        for field_name in candidate_root_fields:
            value = aggregated_document.get(field_name)

            if isinstance(value, str) and value.strip():
                return value.strip()

        raise PromptBuilderError(
            "No usable document text was found. Expected "
            "content.combined_text or another supported text field."
        )

    @staticmethod
    def _extract_required_string(
        payload: dict[str, Any],
        field_name: str,
    ) -> str:
        value = payload.get(field_name)

        if not isinstance(value, str) or not value.strip():
            raise PromptBuilderError(
                f"Required field '{field_name}' must be "
                "a non-empty string."
            )

        return value.strip()

    @staticmethod
    def _extract_optional_string(
        payload: dict[str, Any],
        field_name: str,
        default: str,
    ) -> str:
        value = payload.get(field_name)

        if value is None:
            return default

        if not isinstance(value, str):
            raise PromptBuilderError(
                f"Optional field '{field_name}' must be "
                "a string when supplied."
            )

        cleaned_value = value.strip()

        return cleaned_value or default

    @staticmethod
    def _load_template(
        template_path: Path,
    ) -> str:
        if not template_path.exists():
            raise FileNotFoundError(
                f"Prompt template not found: {template_path}"
            )

        content = template_path.read_text(
            encoding="utf-8"
        )

        if not content.strip():
            raise PromptBuilderError(
                f"Prompt template is empty: {template_path}"
            )

        return content

    @staticmethod
    def _render_template(
        template: str,
        replacements: dict[str, str],
    ) -> str:
        rendered = template

        for key, value in replacements.items():
            rendered = rendered.replace(
                "{{" + key + "}}",
                value,
            )

        unresolved_tokens = [
            token
            for token in (
                "{{DOCUMENT_ID}}",
                "{{DOCUMENT_TYPE}}",
                "{{TITLE}}",
                "{{SOURCE_LANGUAGE}}",
                "{{OUTPUT_LANGUAGE}}",
                "{{SOURCE_METADATA}}",
                "{{JSON_SCHEMA}}",
                "{{DOCUMENT_CONTENT}}",
            )
            if token in rendered
        ]

        if unresolved_tokens:
            raise PromptBuilderError(
                "Unresolved prompt tokens: "
                + ", ".join(unresolved_tokens)
            )

        return rendered

    @staticmethod
    def _sha256_text(
        text: str,
    ) -> str:
        return hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _atomic_write_text(
        output_path: Path,
        content: str,
    ) -> None:
        temporary_path = output_path.with_suffix(
            output_path.suffix + ".tmp"
        )

        temporary_path.write_text(
            content,
            encoding="utf-8",
        )

        temporary_path.replace(output_path)