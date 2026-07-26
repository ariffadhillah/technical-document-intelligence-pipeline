from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .analyzer import ImageAnalysisResult
from .profile import (
    BROCHURE_PROFILE,
    FLYER_PROFILE,
    IMAGE_PROFILES,
    INVOICE_PROFILE,
    MANUAL_PROFILE,
    WIRING_PROFILE,
    ImageProfile,
)


class ImageType(str, Enum):
    """
    Supported document/image types.
    """

    UNKNOWN = "unknown"

    DOCUMENT = "document"

    MANUAL = "manual"

    BROCHURE = "brochure"

    FLYER = "flyer"

    INVOICE = "invoice"

    FORM = "form"

    WIRING = "wiring"

    DRAWING = "drawing"

    PHOTO = "photo"


@dataclass(slots=True)
class ClassificationResult:

    image_type: ImageType

    profile: ImageProfile

    confidence: float

    reason: str


class ImageClassifier:
    """
    Rule-based image classifier.

    Later this class can be replaced by:

        - CNN
        - Vision Transformer
        - GPT Vision
        - Paddle Classification

    without changing preprocess.py.
    """

    def classify(
        self,
        analysis: ImageAnalysisResult,
    ) -> ClassificationResult:

        #
        # 1. Wiring / Engineering Drawing
        #

        if (
            analysis.blur_score > 300
            and analysis.contrast > 70
            and not analysis.is_color
        ):

            return ClassificationResult(
                image_type=ImageType.WIRING,
                profile=WIRING_PROFILE,
                confidence=0.93,
                reason="High contrast monochrome document.",
            )

        #
        # 2. Invoice
        #

        if (
            not analysis.is_color
            and analysis.contrast < 45
            and analysis.brightness > 140
        ):

            return ClassificationResult(
                image_type=ImageType.INVOICE,
                profile=INVOICE_PROFILE,
                confidence=0.88,
                reason="Bright monochrome document.",
            )

        #
        # 3. Brochure
        #

        if (
            analysis.is_color
            and analysis.contrast > 60
            and analysis.blur_score > 200
        ):

            return ClassificationResult(
                image_type=ImageType.BROCHURE,
                profile=BROCHURE_PROFILE,
                confidence=0.90,
                reason="Color marketing document.",
            )

        #
        # 4. Flyer
        #

        if (
            analysis.is_color
            and analysis.brightness > 160
        ):

            return ClassificationResult(
                image_type=ImageType.FLYER,
                profile=FLYER_PROFILE,
                confidence=0.82,
                reason="Bright color flyer.",
            )

        #
        # 5. Manual
        #

        if (
            analysis.needs_denoise
            or analysis.needs_sharpen
        ):

            return ClassificationResult(
                image_type=ImageType.MANUAL,
                profile=MANUAL_PROFILE,
                confidence=0.85,
                reason="Scanned technical manual.",
            )

        #
        # Default
        #

        return ClassificationResult(
            image_type=ImageType.DOCUMENT,
            profile=MANUAL_PROFILE,
            confidence=0.50,
            reason="Default document profile.",
        )

    def get_profile(
        self,
        analysis: ImageAnalysisResult,
    ) -> ImageProfile:

        return self.classify(analysis).profile

    def available_profiles(self):

        return IMAGE_PROFILES