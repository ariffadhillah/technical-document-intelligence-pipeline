from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.schemas.technical_knowledge import (
    StructuredTechnicalDocument,
)


class StructuredOutputValidationError(ValueError):
    """
    Raised when an AI or intermediate JSON payload does not
    satisfy the canonical technical knowledge schema.
    """


class StructuredOutputValidator:
    def validate_payload(
        self,
        payload: dict[str, Any],
    ) -> StructuredTechnicalDocument:
        normalized_payload = self._normalize_payload(
            payload
        )

        try:
            return StructuredTechnicalDocument.model_validate(
                normalized_payload
            )

        except ValidationError as error:
            formatted_errors = self._format_errors(error)
            raise StructuredOutputValidationError(
                "Structured document validation failed:\n"
                f"{formatted_errors}"
            ) from error

    def validate_json_text(
        self,
        json_text: str,
    ) -> StructuredTechnicalDocument:
        try:
            payload = json.loads(json_text)

        except json.JSONDecodeError as error:
            raise StructuredOutputValidationError(
                "The provided text is not valid JSON. "
                f"Line {error.lineno}, "
                f"column {error.colno}: {error.msg}"
            ) from error

        if not isinstance(payload, dict):
            raise StructuredOutputValidationError(
                "The JSON root must be an object."
            )

        return self.validate_payload(payload)

    def validate_file(
        self,
        input_path: Path,
    ) -> StructuredTechnicalDocument:
        if not input_path.exists():
            raise FileNotFoundError(
                f"Structured JSON file not found: "
                f"{input_path}"
            )

        json_text = input_path.read_text(
            encoding="utf-8"
        )

        return self.validate_json_text(json_text)

    def save_validated_document(
        self,
        document: StructuredTechnicalDocument,
        output_path: Path,
    ) -> None:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = output_path.with_suffix(
            output_path.suffix + ".tmp"
        )

        temporary_path.write_text(
            document.model_dump_json(
                indent=2,
                exclude_none=True,
            ),
            encoding="utf-8",
        )

        temporary_path.replace(output_path)


    @staticmethod
    def _normalize_payload(
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = dict(payload)

        translation_quality = normalized.get(
            "translation_quality"
        )

        if isinstance(translation_quality, dict):
            normalized_translation_quality = dict(
                translation_quality
            )

            protected_count = (
                normalized_translation_quality.get(
                    "protected_token_count",
                    0,
                )
            )

            preserved_count = (
                normalized_translation_quality.get(
                    "preserved_token_count",
                    0,
                )
            )

            if not isinstance(protected_count, int):
                protected_count = 0

            if not isinstance(preserved_count, int):
                preserved_count = 0

            protected_count = max(protected_count, 0)
            preserved_count = max(preserved_count, 0)

            if preserved_count > protected_count:
                protected_count = preserved_count

                warnings = (
                    normalized_translation_quality.get(
                        "validation_warnings",
                        []
                    )
                )

                if not isinstance(warnings, list):
                    warnings = []

                warnings.append(
                    "protected_token_count was increased "
                    "to match preserved_token_count because "
                    "the provider returned inconsistent counts."
                )

                normalized_translation_quality[
                    "validation_warnings"
                ] = warnings

            normalized_translation_quality[
                "protected_token_count"
            ] = protected_count

            normalized_translation_quality[
                "preserved_token_count"
            ] = preserved_count

            normalized[
                "translation_quality"
            ] = normalized_translation_quality

        return normalized

    @staticmethod
    def _format_errors(
        error: ValidationError,
    ) -> str:
        formatted: list[str] = []

        for item in error.errors():
            location = ".".join(
                str(part)
                for part in item.get("loc", [])
            )

            message = item.get(
                "msg",
                "Unknown validation error",
            )

            formatted.append(
                f"- {location}: {message}"
            )

        return "\n".join(formatted)