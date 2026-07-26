from __future__ import annotations

from ..schemas import (
    StructuredVisionResult,
)


class StructuredVisionValidator:
    """
    Validates and normalizes StructuredVisionResult.

    Every Vision provider should pass through this
    validator before entering the pipeline.
    """

    @staticmethod
    def validate(
        result: StructuredVisionResult,
    ) -> StructuredVisionResult:

        result.provider = (
            result.provider or "unknown"
        ).strip()

        result.model = (
            result.model or "unknown"
        ).strip()

        result.document_type = (
            StructuredVisionValidator
            ._normalize_name(
                result.document_type,
                default="unknown",
            )
        )

        result.page_type = (
            StructuredVisionValidator
            ._normalize_name(
                result.page_type,
                default="unknown",
            )
        )

        result.language = (
            result.language or "unknown"
        ).lower()

        result.title = (
            result.title.strip()
            if result.title
            else None
        )

        result.summary = (
            result.summary.strip()
            if result.summary
            else None
        )

        result.ocr_text = (
            result.ocr_text or ""
        ).strip()

        result.keywords = list(
            dict.fromkeys(
                keyword.strip()
                for keyword in result.keywords
                if keyword
            )
        )

        result.warnings = list(
            dict.fromkeys(
                warning.strip()
                for warning in result.warnings
                if warning
            )
        )

        if result.confidence is None:
            result.confidence = 0.0

        result.confidence = max(
            0.0,
            min(
                float(result.confidence),
                1.0,
            ),
        )

        if result.metadata is None:
            result.metadata = {}

        return result

    @staticmethod
    def _normalize_name(
        value: str | None,
        *,
        default: str,
    ) -> str:

        if not value:
            return default

        return (
            value.strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )