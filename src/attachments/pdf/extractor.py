from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from .analyzer import PDFAnalyzer
from .models import (
    ExtractionMethod,
    OCRPageResult,
    PDFAnalysisResult,
    PDFExtractionResult,
)
from .renderer import PDFRenderer

logger = logging.getLogger(__name__)


class OCREngine(Protocol):
    """
    Interface OCR Engine.

    Nanti Tesseract, PaddleOCR, EasyOCR,
    maupun Vision OCR akan mengimplementasikan
    interface ini.
    """

    def process_image(
        self,
        image_path: Path,
        page_number: int,
    ) -> OCRPageResult:
        ...


class PDFExtractor:
    """
    High-level PDF extraction pipeline.

    Pipeline

        Analyze
            │
            ▼
      Digital / Hybrid / Scan
            │
            ▼
      Text Layer OR OCR
            │
            ▼
       Merge All Text
    """

    def __init__(
        self,
        analyzer: PDFAnalyzer | None = None,
        renderer: PDFRenderer | None = None,
    ):

        self.analyzer = analyzer or PDFAnalyzer()
        self.renderer = renderer or PDFRenderer()

    def extract(
        self,
        pdf_path: Path,
        render_directory: Path,
        ocr_engine: OCREngine,
    ) -> PDFExtractionResult:

        logger.info("Analyzing PDF %s", pdf_path)

        analysis = self.analyzer.analyze(pdf_path)

        if analysis.has_text_layer and not analysis.is_scanned:

            return self._extract_text_layer(
                pdf_path,
                analysis,
            )

        logger.info("PDF requires OCR.")

        return self._extract_via_ocr(
            pdf_path=pdf_path,
            render_directory=render_directory,
            analysis=analysis,
            ocr_engine=ocr_engine,
        )

    def _extract_text_layer(
        self,
        pdf_path: Path,
        analysis: PDFAnalysisResult,
    ) -> PDFExtractionResult:

        import fitz

        pages: list[OCRPageResult] = []

        merged = []

        document = fitz.open(pdf_path)

        try:

            for page_number, page in enumerate(document, start=1):

                text = page.get_text("text").strip()

                pages.append(
                    OCRPageResult(
                        page_number=page_number,
                        confidence=100.0,
                        word_count=len(text.split()),
                        character_count=len(text),
                        language=None,
                        text=text,
                    )
                )

                merged.append(text)

        finally:

            document.close()

        return PDFExtractionResult(
            source=pdf_path,
            method=ExtractionMethod.TEXT_LAYER,
            page_count=len(pages),
            pages=pages,
            merged_text="\n\n".join(merged),
            average_confidence=100.0,
        )

    def _extract_via_ocr(
        self,
        pdf_path: Path,
        render_directory: Path,
        analysis: PDFAnalysisResult,
        ocr_engine: OCREngine,
    ) -> PDFExtractionResult:

        rendered_pages = self.renderer.render(
            pdf_path=pdf_path,
            output_dir=render_directory,
        )

        results: list[OCRPageResult] = []

        merged = []

        confidence_sum = 0.0

        for page in rendered_pages:

            logger.info(
                "OCR page %s",
                page.page_number,
            )

            result = ocr_engine.process_image(
                image_path=page.image_path,
                page_number=page.page_number,
            )

            results.append(result)

            merged.append(result.text)

            confidence_sum += result.confidence

        average = (
            confidence_sum / len(results)
            if results
            else 0.0
        )

        return PDFExtractionResult(
            source=pdf_path,
            method=ExtractionMethod.OCR,
            page_count=len(results),
            pages=results,
            merged_text="\n\n".join(merged),
            average_confidence=average,
        )