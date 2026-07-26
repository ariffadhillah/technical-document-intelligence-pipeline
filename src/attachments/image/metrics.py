from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ImageMetrics:
    """
    Quality metrics after preprocessing.
    """

    brightness: float

    contrast: float

    blur_score: float

    noise: float

    estimated_ocr_quality: float

    preprocessing_time: float


class OCRQualityEstimator:
    """
    Estimate OCR quality score.
    """

    def score(
        self,
        brightness: float,
        contrast: float,
        blur: float,
        noise: float,
    ) -> float:

        score = 100.0

        if brightness < 70:
            score -= 12

        if contrast < 35:
            score -= 15

        if blur < 150:
            score -= 20

        if noise > 12:
            score -= 10

        return max(score, 0.0)