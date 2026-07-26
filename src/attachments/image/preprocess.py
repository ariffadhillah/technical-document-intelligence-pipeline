from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

from .analyzer import ImageAnalyzer
from .classifier import ImageClassifier
from .deskew import DeskewProcessor
from .enhancement import ImageEnhancer
from .metrics import ImageMetrics, OCRQualityEstimator
from .orientation import OrientationCorrector

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ImagePreprocessResult:
    """
    Final preprocessing result.
    """

    image: np.ndarray

    analysis: object

    classification: object

    metrics: ImageMetrics


class ImagePreprocessor:
    """
    Adaptive OCR preprocessing pipeline.

        Analyze Image
              │
              ▼
      Classify Document
              │
              ▼
       Select Profile
              │
              ▼
      Execute Pipeline
              │
              ▼
      Estimate OCR Quality
    """

    def __init__(self):

        self.analyzer = ImageAnalyzer()

        self.classifier = ImageClassifier()

        self.orientation = OrientationCorrector()

        self.deskew = DeskewProcessor()

        self.enhancer = ImageEnhancer()

        self.quality = OCRQualityEstimator()

    def process(
        self,
        image: np.ndarray,
    ) -> ImagePreprocessResult:

        logger.info("Analyzing image...")

        analysis = self.analyzer.analyze(image)

        logger.info(
            "Classification..."
        )

        classification = self.classifier.classify(
            analysis
        )

        profile = classification.profile

        logger.info(
            "Using profile: %s",
            profile.name,
        )

        #
        # Orientation
        #

        if profile.auto_orientation:

            image = self.orientation.auto(
                image
            )

        #
        # Deskew
        #

        if profile.deskew:

            image = self.deskew.deskew(
                image
            )

        #
        # Resize
        #

        if profile.resize:

            image = self.enhancer.resize(
                image,
                profile.resize_scale,
            )

        #
        # Grayscale
        #

        if profile.grayscale:

            image = self.enhancer.grayscale(
                image
            )

        #
        # Denoise
        #

        if profile.denoise:

            image = self.enhancer.denoise(
                image
            )

        #
        # CLAHE
        #

        if profile.clahe:

            image = self.enhancer.clahe(
                image
            )

        #
        # Threshold
        #

        if profile.adaptive_threshold:

            image = self.enhancer.adaptive_threshold(
                image
            )

        #
        # Morphology
        #

        if profile.morphology:

            image = self.enhancer.morphology(
                image
            )

        #
        # Sharpen
        #

        if profile.sharpen:

            image = self.enhancer.sharpen(
                image
            )

        #
        # Analyze Again
        #

        final_analysis = self.analyzer.analyze(
            image
        )

        score = self.quality.score(
            brightness=final_analysis.brightness,
            contrast=final_analysis.contrast,
            blur=final_analysis.blur_score,
            noise=final_analysis.estimated_noise,
        )

        metrics = ImageMetrics(
            brightness=final_analysis.brightness,
            contrast=final_analysis.contrast,
            blur_score=final_analysis.blur_score,
            noise=final_analysis.estimated_noise,
            estimated_ocr_quality=score,
            preprocessing_time=0.0,
        )

        logger.info(
            "Estimated OCR Quality : %.2f",
            score,
        )

        return ImagePreprocessResult(
            image=image,
            analysis=final_analysis,
            classification=classification,
            metrics=metrics,
        )

    def process_file(
        self,
        image_path: str,
    ) -> ImagePreprocessResult:

        image = cv2.imread(image_path)

        if image is None:

            raise FileNotFoundError(image_path)

        return self.process(image)