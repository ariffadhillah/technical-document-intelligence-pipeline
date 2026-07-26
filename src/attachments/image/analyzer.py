from __future__ import annotations

from dataclasses import dataclass
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ImageAnalysisResult:
    """
    Result of image quality analysis.
    """

    width: int
    height: int

    channels: int

    is_color: bool

    brightness: float

    contrast: float

    blur_score: float

    estimated_noise: float

    needs_grayscale: bool

    needs_denoise: bool

    needs_clahe: bool

    needs_threshold: bool

    needs_sharpen: bool

    needs_resize: bool

    needs_deskew: bool


class ImageAnalyzer:
    """
    Analyze image quality before OCR.
    """

    BRIGHTNESS_LOW = 80
    CONTRAST_LOW = 35
    BLUR_THRESHOLD = 150
    NOISE_THRESHOLD = 12

    def analyze(
        self,
        image: np.ndarray,
    ) -> ImageAnalysisResult:

        h, w = image.shape[:2]

        channels = 1 if len(image.shape) == 2 else image.shape[2]

        is_color = channels == 3

        if is_color:

            gray = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2GRAY,
            )

        else:

            gray = image

        brightness = float(np.mean(gray))

        contrast = float(np.std(gray))

        blur_score = float(
            cv2.Laplacian(
                gray,
                cv2.CV_64F,
            ).var()
        )

        denoised = cv2.GaussianBlur(
            gray,
            (3, 3),
            0,
        )

        estimated_noise = float(
            np.mean(
                cv2.absdiff(
                    gray,
                    denoised,
                )
            )
        )

        return ImageAnalysisResult(

            width=w,

            height=h,

            channels=channels,

            is_color=is_color,

            brightness=brightness,

            contrast=contrast,

            blur_score=blur_score,

            estimated_noise=estimated_noise,

            needs_grayscale=is_color,

            needs_denoise=estimated_noise > self.NOISE_THRESHOLD,

            needs_clahe=contrast < self.CONTRAST_LOW,

            needs_threshold=True,

            needs_sharpen=blur_score < self.BLUR_THRESHOLD,

            needs_resize=min(w, h) < 1200,

            needs_deskew=True,
        )