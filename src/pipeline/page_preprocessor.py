from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np

from src.attachments.image.orientation import (
    ImageOrientationCorrector,
)

from .models import PreparedPage

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PagePreprocessingResult:
    """
    Result of preprocessing all prepared document pages.
    """

    images: dict[int, np.ndarray]

    metadata_by_page: dict[
        int,
        dict[str, Any],
    ] = field(default_factory=dict)


class PagePreprocessor:
    """
    Apply image preprocessing before OCR and Vision.

    Current processing:
    - orientation detection
    - orientation correction

    Future processing can include:
    - deskew
    - denoise
    - contrast enhancement
    - binarization
    """

    def __init__(
        self,
        *,
        orientation_corrector: (
            ImageOrientationCorrector | None
        ) = None,
    ) -> None:
        self.orientation_corrector = (
            orientation_corrector
        )

    def process_pages(
        self,
        *,
        prepared_pages: list[PreparedPage],
        images: Mapping[int, np.ndarray],
    ) -> PagePreprocessingResult:
        processed_images: dict[
            int,
            np.ndarray,
        ] = {}

        metadata_by_page: dict[
            int,
            dict[str, Any],
        ] = {}

        for prepared_page in sorted(
            prepared_pages,
            key=lambda item: item.page_number,
        ):
            page_number = (
                prepared_page.page_number
            )

            image = images.get(page_number)

            self._validate_image(
                image=image,
                page_number=page_number,
            )

            page_metadata: dict[
                str,
                Any,
            ] = {}

            processed_image = image

            if self.orientation_corrector is not None:
                orientation_result = (
                    self.orientation_corrector.correct(
                        image
                    )
                )

                processed_image = (
                    orientation_result.image
                )

                page_metadata["orientation"] = {
                    "detected_angle": (
                        orientation_result
                        .detected_angle
                    ),
                    "applied_rotation": (
                        orientation_result
                        .applied_rotation
                    ),
                    "confidence": (
                        orientation_result
                        .confidence
                    ),
                    "corrected": (
                        orientation_result
                        .corrected
                    ),
                }

                logger.info(
                    "Page preprocessing completed: "
                    "page=%s orientation_corrected=%s "
                    "rotation=%s confidence=%.2f",
                    page_number,
                    orientation_result.corrected,
                    orientation_result.applied_rotation,
                    orientation_result.confidence,
                )

            processed_images[
                page_number
            ] = processed_image

            metadata_by_page[
                page_number
            ] = page_metadata

        return PagePreprocessingResult(
            images=processed_images,
            metadata_by_page=metadata_by_page,
        )

    @staticmethod
    def _validate_image(
        *,
        image: np.ndarray | None,
        page_number: int,
    ) -> None:
        if image is None:
            raise ValueError(
                "Prepared image is missing for "
                f"page {page_number}."
            )

        if image.size == 0:
            raise ValueError(
                "Prepared image is empty for "
                f"page {page_number}."
            )