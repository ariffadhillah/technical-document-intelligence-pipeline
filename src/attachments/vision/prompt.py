from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VisionPrompt:
    """
    Versioned prompt used by Vision providers.
    """

    version: str = "1.0"

    template: str = (
        "Analyze this technical-document page carefully.\n\n"
        "Return all readable text while preserving:\n"
        "- headings\n"
        "- paragraphs\n"
        "- lists\n"
        "- warnings\n"
        "- labels\n"
        "- table-like structure where possible\n"
        "- technical symbols and measurements\n\n"
        "Do not summarize the page.\n"
        "Do not invent missing information.\n"
        "Return only the extracted page content."
    )

    def build(
        self,
        *,
        ocr_text: str | None = None,
        page_number: int | None = None,
    ) -> str:
        sections = [self.template]

        if page_number is not None:
            sections.append(
                f"\nDocument page number: {page_number}"
            )

        if ocr_text and ocr_text.strip():
            sections.append(
                "\nExisting OCR output is included only as a hint. "
                "Correct it when it is inaccurate:\n\n"
                f"{ocr_text.strip()}"
            )

        return "\n".join(sections)