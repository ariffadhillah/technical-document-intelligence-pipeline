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
        try:
            return StructuredTechnicalDocument.model_validate(
                payload
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