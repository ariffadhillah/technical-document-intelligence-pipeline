from __future__ import annotations

import json
import re

from ..schemas import (
    StructuredVisionResult,
)


class VisionResponseParser:
    """
    Parses Vision model responses into
    StructuredVisionResult.
    """

    @staticmethod
    def parse(
        text: str,
        *,
        provider: str,
        model: str,
        processing_time: float | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> StructuredVisionResult:

        payload = VisionResponseParser._extract_json(text)

        data = json.loads(payload)

        return StructuredVisionResult(
            provider=provider,
            model=model,
            document_type=data.get(
                "document_type",
                "unknown",
            ),
            page_type=data.get(
                "page_type",
                "unknown",
            ),
            language=data.get(
                "language",
                "unknown",
            ),
            title=data.get("title"),
            summary=data.get("summary"),
            ocr_text=data.get(
                "ocr_text",
                "",
            ),
            keywords=data.get(
                "keywords",
                [],
            ),
            warnings=data.get(
                "warnings",
                [],
            ),
            confidence=data.get(
                "confidence",
                None,
            ),
            processing_time=processing_time,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            metadata={},
        )

    @staticmethod
    def _extract_json(
        text: str,
    ) -> str:

        text = text.strip()

        if text.startswith("```"):
            text = re.sub(
                r"^```(?:json)?",
                "",
                text,
            )
            text = re.sub(
                r"```$",
                "",
                text,
            )

        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:
            raise ValueError(
                "No JSON object found."
            )

        return text[start:end + 1]