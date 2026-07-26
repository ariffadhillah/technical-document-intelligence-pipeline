from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from src.attachments.ocr.exceptions import (
    OCRProcessingError,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class OrientationResult:
    image: np.ndarray
    detected_angle: int
    applied_rotation: int
    confidence: float
    corrected: bool
    metadata: dict[str, Any]


class ImageOrientationCorrector:
    """
    Detect and correct image orientation using
    Tesseract OSD.

    Supported detected rotations:
    0, 90, 180, and 270 degrees.
    """

    def __init__(
        self,
        *,
        pytesseract_module: Any,
        minimum_confidence: float = 1.0,
        fail_open: bool = True,
    ) -> None:
        self.pytesseract = pytesseract_module
        self.minimum_confidence = (
            minimum_confidence
        )
        self.fail_open = fail_open

    def correct(
        self,
        image: np.ndarray,
    ) -> OrientationResult:
        if image is None or image.size == 0:
            raise OCRProcessingError(
                "Cannot detect orientation of an "
                "empty image."
            )

        try:
            osd = self.pytesseract.image_to_osd(
                image
            )

            detected_angle = self._extract_integer(
                osd,
                "Orientation in degrees",
            )

            rotate_value = self._extract_integer(
                osd,
                "Rotate",
            )

            confidence = self._extract_float(
                osd,
                "Orientation confidence",
            )

        except Exception as exc:
            if not self.fail_open:
                raise OCRProcessingError(
                    "Image orientation detection "
                    f"failed: {exc}"
                ) from exc

            logger.warning(
                "Orientation detection failed; "
                "keeping original image: %s",
                exc,
            )

            return OrientationResult(
                image=image,
                detected_angle=0,
                applied_rotation=0,
                confidence=0.0,
                corrected=False,
                metadata={
                    "error": str(exc),
                    "fail_open": True,
                },
            )

        should_rotate = (
            rotate_value in {90, 180, 270}
            and confidence
            >= self.minimum_confidence
        )

        corrected_image = image

        if should_rotate:
            corrected_image = self._rotate(
                image,
                rotate_value,
            )

            logger.info(
                "Corrected image orientation: "
                "detected=%s rotate=%s "
                "confidence=%.2f",
                detected_angle,
                rotate_value,
                confidence,
            )

        return OrientationResult(
            image=corrected_image,
            detected_angle=detected_angle,
            applied_rotation=(
                rotate_value
                if should_rotate
                else 0
            ),
            confidence=confidence,
            corrected=should_rotate,
            metadata={
                "raw_osd": osd,
            },
        )

    @staticmethod
    def _rotate(
        image: np.ndarray,
        angle: int,
    ) -> np.ndarray:
        if angle == 90:
            return cv2.rotate(
                image,
                cv2.ROTATE_90_CLOCKWISE,
            )

        if angle == 180:
            return cv2.rotate(
                image,
                cv2.ROTATE_180,
            )

        if angle == 270:
            return cv2.rotate(
                image,
                cv2.ROTATE_90_COUNTERCLOCKWISE,
            )

        return image

    @staticmethod
    def _extract_integer(
        osd: str,
        key: str,
    ) -> int:
        match = re.search(
            rf"^{re.escape(key)}:\s*(-?\d+)",
            osd,
            flags=re.MULTILINE,
        )

        if match is None:
            return 0

        return int(match.group(1))

    @staticmethod
    def _extract_float(
        osd: str,
        key: str,
    ) -> float:
        match = re.search(
            rf"^{re.escape(key)}:\s*"
            r"(-?\d+(?:\.\d+)?)",
            osd,
            flags=re.MULTILINE,
        )

        if match is None:
            return 0.0

        return float(match.group(1))