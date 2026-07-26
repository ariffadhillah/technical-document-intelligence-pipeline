from __future__ import annotations

import logging
from pathlib import Path

import fitz

from .models import (
    PDFAnalysisResult,
    PDFPageAnalysis,
    PDFType,
)

logger = logging.getLogger(__name__)


class PDFAnalyzer:
    """
    Analyze a PDF before extraction.

    Responsibilities
    ----------------
    - Detect number of pages
    - Detect text layer
    - Count extracted characters
    - Determine Digital / Scanned / Hybrid PDF
    """

    MIN_TEXT_THRESHOLD = 40

    def analyze(
        self,
        pdf_path: Path,
    ) -> PDFAnalysisResult:

        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        document = fitz.open(pdf_path)

        pages: list[PDFPageAnalysis] = []

        total_characters = 0

        text_pages = 0
        scanned_pages = 0

        try:

            for index, page in enumerate(document):

                text = page.get_text("text").strip()

                char_count = len(text)

                has_text = char_count >= self.MIN_TEXT_THRESHOLD

                if has_text:
                    text_pages += 1
                else:
                    scanned_pages += 1

                total_characters += char_count

                page_info = PDFPageAnalysis(
                    page_number=index + 1,
                    width=page.rect.width,
                    height=page.rect.height,
                    extracted_characters=char_count,
                    has_text_layer=has_text,
                    is_scanned=not has_text,
                    rotation=page.rotation,
                )

                pages.append(page_info)

            page_count = len(pages)

            if text_pages == page_count:

                pdf_type = PDFType.DIGITAL

            elif scanned_pages == page_count:

                pdf_type = PDFType.SCANNED

            elif text_pages > 0 and scanned_pages > 0:

                pdf_type = PDFType.HYBRID

            else:

                pdf_type = PDFType.UNKNOWN

            result = PDFAnalysisResult(
                source=pdf_path,
                pdf_type=pdf_type,
                page_count=page_count,
                total_characters=total_characters,
                has_text_layer=text_pages > 0,
                is_scanned=scanned_pages == page_count,
                pages=pages,
            )

            logger.info(
                "PDF analyzed | pages=%s type=%s chars=%s",
                page_count,
                pdf_type.value,
                total_characters,
            )

            return result

        finally:

            document.close()