from __future__ import annotations

import logging
from typing import Any, Mapping

import numpy as np

from src.attachments.ocr import BaseOCREngine
from src.attachments.ocr.models import OCRPage

from .models import PreparedPage

logger = logging.getLogger(__name__)


class OCRRunner:
    """
    Run OCR on prepared and preprocessed pages.
    """

    def __init__(
        self,
        *,
        engine: BaseOCREngine,
    ) -> None:
        self.engine = engine

    def run(
        self,
        *,
        prepared_pages: list[PreparedPage],
        images: Mapping[int, np.ndarray],
        language: str | None = None,
        preprocessing_metadata: (
            Mapping[int, dict[str, Any]]
            | None
        ) = None,
    ) -> list[OCRPage]:
        pages: list[OCRPage] = []

        metadata_by_page = (
            preprocessing_metadata or {}
        )

        for prepared_page in sorted(
            prepared_pages,
            key=lambda item: item.page_number,
        ):
            page_number = (
                prepared_page.page_number
            )

            image = images.get(page_number)

            if image is None or image.size == 0:
                raise ValueError(
                    "OCR image is missing or empty "
                    f"for page {page_number}."
                )

            page = self.engine.process_image(
                image,
                page_number=page_number,
                source_path=(
                    prepared_page.image_path
                ),
                language=language,
            )

            page_metadata = dict(
                metadata_by_page.get(
                    page_number,
                    {},
                )
            )

            if page.metadata is None:
                page.metadata = {}

            page.metadata.update(
                page_metadata
            )

            pages.append(page)

            logger.info(
                "OCR page completed: page=%s "
                "confidence=%.3f quality=%.3f "
                "words=%s",
                page.page_number,
                page.confidence,
                page.quality_score,
                page.word_count,
            )

        return pages