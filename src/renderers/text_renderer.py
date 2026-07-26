from __future__ import annotations

import re

from src.renderers.markdown_renderer import MarkdownRenderer
from src.schemas.technical_knowledge import (
    StructuredTechnicalDocument,
)


class TextRenderer:
    """Render a validated document as plain UTF-8 text."""

    def __init__(self) -> None:
        self.markdown_renderer = MarkdownRenderer()

    def render(
        self,
        document: StructuredTechnicalDocument,
    ) -> str:
        markdown = self.markdown_renderer.render(document)

        text = re.sub(
            r"^#{1,6}\s+",
            "",
            markdown,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"\*\*(.*?)\*\*",
            r"\1",
            text,
        )
        text = re.sub(
            r"`([^`]*)`",
            r"\1",
            text,
        )
        text = re.sub(
            r"^\|[-|: ]+\|\s*$",
            "",
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^\|\s*(.*?)\s*\|$",
            lambda match: " | ".join(
                part.strip()
                for part in match.group(1).split("|")
            ),
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip() + "\n"
