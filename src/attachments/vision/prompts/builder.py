from __future__ import annotations

from .templates import (
    VISION_OUTPUT_SCHEMA,
    VISION_SYSTEM_PROMPT,
)


class VisionPromptBuilder:
    """
    Builds prompts for every Vision provider.

    The generated prompt is provider-independent.
    """

    @staticmethod
    def build(
        *,
        document_type: str | None = None,
        language: str | None = None,
    ) -> str:

        document_type = document_type or "general_document"

        language = language or "unknown"

        return f"""
{VISION_SYSTEM_PROMPT}

Document type:

{document_type}

Detected language:

{language}

Return JSON matching exactly this schema:

{VISION_OUTPUT_SCHEMA}
""".strip()