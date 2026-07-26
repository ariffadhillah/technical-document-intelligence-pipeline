from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.processors.structured_output_validator import (
    StructuredOutputValidator,
)
from src.prompts import TechnicalPromptBuilder
from src.providers import (
    BaseProvider,
    ProviderFactory,
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
)
from src.schemas.technical_knowledge import (
    StructuredTechnicalDocument,
)


@dataclass(frozen=True)
class AIStageResult:
    """
    Result metadata produced by one AI extraction stage.
    """

    document_id: str
    provider: str
    model: str

    output_directory: str
    system_prompt_path: str
    user_prompt_path: str
    provider_request_path: str
    raw_response_path: str
    validated_response_path: str
    provider_metadata_path: str

    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None

    duration_seconds: float | None
    status: str = "success"

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "provider": self.provider,
            "model": self.model,
            "output_directory": self.output_directory,
            "system_prompt_path": self.system_prompt_path,
            "user_prompt_path": self.user_prompt_path,
            "provider_request_path": (
                self.provider_request_path
            ),
            "raw_response_path": self.raw_response_path,
            "validated_response_path": (
                self.validated_response_path
            ),
            "provider_metadata_path": (
                self.provider_metadata_path
            ),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
        }


class TechnicalAIStageRunner:
    """
    Executes the provider-agnostic technical AI stage.

    Flow:

        Aggregated document
            -> Prompt Builder
            -> ProviderRequest
            -> Provider
            -> ProviderResponse
            -> Structured validator
            -> Audit artifacts
    """

    def __init__(
        self,
        *,
        output_directory: Path,
        model: str,
        temperature: float = 0.0,
        max_output_tokens: int = 16000,
        timeout_seconds: float = 60.0,
    ) -> None:
        if not model.strip():
            raise ValueError(
                "AI stage model cannot be empty."
            )

        if max_output_tokens <= 0:
            raise ValueError(
                "max_output_tokens must be greater than zero."
            )

        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater than zero."
            )

        self.output_directory = output_directory.resolve()
        self.model = model.strip()
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.timeout_seconds = timeout_seconds

        self.prompt_builder = TechnicalPromptBuilder()
        self.validator = StructuredOutputValidator()

    def run(
        self,
        *,
        aggregated_document: dict[str, Any],
        provider: BaseProvider,
    ) -> AIStageResult:
        prompt = self.prompt_builder.build(
            aggregated_document
        )

        document_output_directory = (
            self.output_directory / prompt.document_id
        )

        document_output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        request = self._build_request(
            prompt=prompt
        )

        system_prompt_path = (
            document_output_directory
            / "01_system_prompt.md"
        )

        user_prompt_path = (
            document_output_directory
            / "02_user_prompt.md"
        )

        provider_request_path = (
            document_output_directory
            / "03_provider_request.json"
        )

        raw_response_path = (
            document_output_directory
            / "04_raw_response.json"
        )

        validated_response_path = (
            document_output_directory
            / "05_validated_response.json"
        )

        provider_metadata_path = (
            document_output_directory
            / "06_provider_metadata.json"
        )

        self._atomic_write_text(
            output_path=system_prompt_path,
            content=prompt.system_prompt + "\n",
        )

        self._atomic_write_text(
            output_path=user_prompt_path,
            content=prompt.user_prompt + "\n",
        )

        self._atomic_write_json(
            output_path=provider_request_path,
            payload=request.to_dict(),
        )

        response = provider.generate(request)

        raw_response_payload = (
            self._parse_raw_response(response)
        )

        self._atomic_write_json(
            output_path=raw_response_path,
            payload=raw_response_payload,
        )

        validated_document = (
            self.validator.validate_json_text(
                response.raw_text
            )
        )

        self.validator.save_validated_document(
            document=validated_document,
            output_path=validated_response_path,
        )

        provider_metadata = (
            self._build_provider_metadata(
                response=response,
                prompt=prompt,
            )
        )

        self._atomic_write_json(
            output_path=provider_metadata_path,
            payload=provider_metadata,
        )

        return AIStageResult(
            document_id=prompt.document_id,
            provider=response.provider,
            model=response.model,
            output_directory=str(
                document_output_directory
            ),
            system_prompt_path=str(
                system_prompt_path
            ),
            user_prompt_path=str(
                user_prompt_path
            ),
            provider_request_path=str(
                provider_request_path
            ),
            raw_response_path=str(
                raw_response_path
            ),
            validated_response_path=str(
                validated_response_path
            ),
            provider_metadata_path=str(
                provider_metadata_path
            ),
            input_tokens=(
                response.usage.input_tokens
            ),
            output_tokens=(
                response.usage.output_tokens
            ),
            total_tokens=(
                response.usage.total_tokens
            ),
            duration_seconds=(
                response.duration_seconds
            ),
        )

    def create_provider(
        self,
        *,
        provider_name: str,
        configuration: dict[str, Any],
    ) -> BaseProvider:
        """
        Create a provider through the central factory.

        Keeping this method here prevents main.py from knowing
        individual provider constructor details.
        """

        return ProviderFactory.create(
            provider_name,
            **configuration,
        )

    def _build_request(
        self,
        *,
        prompt: Any,
    ) -> ProviderRequest:
        """
        Build a schema-constrained provider request.

        The JSON schema is supplied directly to the provider instead
        of relying only on instructions written inside the prompt.
        """

        response_schema = (
            StructuredTechnicalDocument.model_json_schema()
        )

        return ProviderRequest(
            messages=(
                ProviderMessage(
                    role="system",
                    content=prompt.system_prompt,
                ),
                ProviderMessage(
                    role="user",
                    content=prompt.user_prompt,
                ),
            ),
            model=self.model,
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            timeout_seconds=self.timeout_seconds,
            response_format="json_schema",
            json_schema=response_schema,
            metadata={
                "document_id": prompt.document_id,
                "prompt_name": prompt.prompt_name,
                "prompt_version": prompt.prompt_version,
                "system_prompt_sha256": (
                    prompt.system_prompt_sha256
                ),
                "user_prompt_sha256": (
                    prompt.user_prompt_sha256
                ),
                "source_content_sha256": (
                    prompt.source_content_sha256
                ),
            },
        )


    @staticmethod
    def _parse_raw_response(
        response: ProviderResponse,
    ) -> dict[str, Any]:
        try:
            payload = json.loads(
                response.raw_text
            )

        except json.JSONDecodeError:
            return {
                "raw_text": response.raw_text,
            }

        if isinstance(payload, dict):
            return payload

        return {
            "raw_value": payload,
        }

    @staticmethod
    def _build_provider_metadata(
        *,
        response: ProviderResponse,
        prompt: Any,
    ) -> dict[str, Any]:
        metadata = response.to_dict(
            include_raw_response=False
        )

        # Full content already exists in 04_raw_response.json.
        metadata.pop("raw_text", None)

        metadata["prompt"] = {
            "prompt_name": prompt.prompt_name,
            "prompt_version": prompt.prompt_version,
            "document_id": prompt.document_id,
            "system_prompt_sha256": (
                prompt.system_prompt_sha256
            ),
            "user_prompt_sha256": (
                prompt.user_prompt_sha256
            ),
            "source_content_sha256": (
                prompt.source_content_sha256
            ),
            "source_character_count": (
                prompt.source_character_count
            ),
            "generated_at": prompt.generated_at,
        }

        return metadata

    @staticmethod
    def _atomic_write_json(
        *,
        output_path: Path,
        payload: dict[str, Any],
    ) -> None:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = output_path.with_suffix(
            output_path.suffix + ".tmp"
        )

        temporary_path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )

        temporary_path.replace(output_path)

    @staticmethod
    def _atomic_write_text(
        *,
        output_path: Path,
        content: str,
    ) -> None:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = output_path.with_suffix(
            output_path.suffix + ".tmp"
        )

        temporary_path.write_text(
            content,
            encoding="utf-8",
        )

        temporary_path.replace(output_path)