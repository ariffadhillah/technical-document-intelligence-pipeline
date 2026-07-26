from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class OrientationCorrector:
    """
    Correct image orientation before OCR.
    """

    def rotate(
        self,
        image: np.ndarray,
        angle: float,
    ) -> np.ndarray:

        h, w = image.shape[:2]

        center = (w // 2, h // 2)

        matrix = cv2.getRotationMatrix2D(
            center,
            angle,
            1.0,
        )

        return cv2.warpAffine(
            image,
            matrix,
            (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )

    def rotate_90(self, image: np.ndarray):

        return cv2.rotate(
            image,
            cv2.ROTATE_90_CLOCKWISE,
        )

    def rotate_180(self, image):

        return cv2.rotate(
            image,
            cv2.ROTATE_180,
        )

    def rotate_270(self, image):

        return cv2.rotate(
            image,
            cv2.ROTATE_90_COUNTERCLOCKWISE,
        )

    def auto(
        self,
        image: np.ndarray,
    ) -> np.ndarray:
        """
        Placeholder.

        Nanti akan memakai
        Tesseract OSD atau PaddleOCR
        orientation detection.
        """

        logger.debug(
            "Auto orientation not enabled yet."
        )

        return image