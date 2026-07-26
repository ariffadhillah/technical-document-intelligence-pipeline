from __future__ import annotations

import math
import re

from ..ocr.models import OCRPage
from .models import (
    VisionPageScore,
    VisionReason,
)


class VisionPageScorer:
    """
    Evaluate whether OCR output is reliable enough.

    Final quality score:

        OCR confidence        35%
        Word count            15%
        Character density     15%
        Readable characters   20%
        Language confidence   10%
        Noise score            5%
    """

    def __init__(
        self,
        *,
        vision_threshold: float = 0.60,
        minimum_word_count: int = 5,
        minimum_character_count: int = 20,
    ) -> None:
        if not 0.0 <= vision_threshold <= 1.0:
            raise ValueError(
                "vision_threshold must be between 0 and 1."
            )

        self.vision_threshold = vision_threshold
        self.minimum_word_count = minimum_word_count
        self.minimum_character_count = (
            minimum_character_count
        )

    def evaluate(
        self,
        page: OCRPage,
    ) -> VisionPageScore:
        text = page.text.strip()

        if not text:
            return VisionPageScore(
                page_number=page.page_number,
                quality_score=0.0,
                ocr_confidence_score=0.0,
                word_count_score=0.0,
                character_density_score=0.0,
                readable_character_score=0.0,
                language_score=0.0,
                noise_score=0.0,
                needs_vision=True,
                reasons=[VisionReason.EMPTY_OCR],
                details={
                    "word_count": 0,
                    "character_count": 0,
                    "vision_threshold": self.vision_threshold,
                },
            )

        confidence_score = self._normalize_confidence(
            page.confidence
        )

        word_count = self._calculate_word_count(page)

        word_count_score = self._word_count_score(
            word_count
        )

        character_count = len(text)

        character_density_score = (
            self._character_density_score(
                character_count
            )
        )

        readable_character_score = (
            self._readable_character_score(text)
        )

        language_score = self._language_score(page)

        noise_ratio = self._noise_ratio(text)

        noise_score = max(0.0, 1.0 - noise_ratio)

        quality_score = (
            confidence_score * 0.35
            + word_count_score * 0.15
            + character_density_score * 0.15
            + readable_character_score * 0.20
            + language_score * 0.10
            + noise_score * 0.05
        )

        quality_score = self._clamp(quality_score)

        reasons: list[VisionReason] = []

        if confidence_score < 0.50:
            reasons.append(
                VisionReason.LOW_OCR_CONFIDENCE
            )

        if word_count < self.minimum_word_count:
            reasons.append(
                VisionReason.LOW_WORD_COUNT
            )

        if noise_ratio > 0.25:
            reasons.append(
                VisionReason.HIGH_NOISE_RATIO
            )

        if language_score < 0.30:
            reasons.append(
                VisionReason.UNKNOWN_LANGUAGE
            )

        if quality_score < self.vision_threshold:
            reasons.insert(
                0,
                VisionReason.LOW_OCR_QUALITY,
            )

        needs_vision = (
            quality_score < self.vision_threshold
            or character_count
            < self.minimum_character_count
        )

        return VisionPageScore(
            page_number=page.page_number,
            quality_score=quality_score,
            ocr_confidence_score=confidence_score,
            word_count_score=word_count_score,
            character_density_score=(
                character_density_score
            ),
            readable_character_score=(
                readable_character_score
            ),
            language_score=language_score,
            noise_score=noise_score,
            needs_vision=needs_vision,
            reasons=reasons,
            details={
                "word_count": word_count,
                "character_count": character_count,
                "noise_ratio": noise_ratio,
                "vision_threshold": self.vision_threshold,
            },
        )

    @staticmethod
    def _normalize_confidence(
        confidence: float,
    ) -> float:
        if confidence > 1.0:
            confidence /= 100.0

        return VisionPageScorer._clamp(confidence)

    @staticmethod
    def _calculate_word_count(
        page: OCRPage,
    ) -> int:
        if page.word_count > 0:
            return page.word_count

        return len(
            re.findall(
                r"\b[\wÀ-ÿ]+\b",
                page.text,
                flags=re.UNICODE,
            )
        )

    @staticmethod
    def _word_count_score(
        word_count: int,
    ) -> float:
        if word_count <= 0:
            return 0.0

        return min(
            math.log1p(word_count) / math.log1p(100),
            1.0,
        )

    @staticmethod
    def _character_density_score(
        character_count: int,
    ) -> float:
        if character_count <= 0:
            return 0.0

        return min(character_count / 500.0, 1.0)

    @staticmethod
    def _readable_character_score(
        text: str,
    ) -> float:
        if not text:
            return 0.0

        readable = sum(
            1
            for character in text
            if (
                character.isalnum()
                or character.isspace()
                or character
                in ".,:;!?%()/+-_=°#@&'\"[]{}"
            )
        )

        return readable / len(text)

    @staticmethod
    def _noise_ratio(
        text: str,
    ) -> float:
        if not text:
            return 1.0

        noisy_characters = sum(
            1
            for character in text
            if (
                not character.isalnum()
                and not character.isspace()
                and character
                not in ".,:;!?%()/+-_=°#@&'\"[]{}"
            )
        )

        return noisy_characters / len(text)

    @staticmethod
    def _language_score(
        page: OCRPage,
    ) -> float:
        detection = page.metadata.get(
            "language_detection",
            {},
        )

        confidence = detection.get("confidence")

        if confidence is not None:
            return VisionPageScorer._clamp(
                float(confidence)
            )

        if page.language and page.language != "unknown":
            return 0.70

        return 0.20

    @staticmethod
    def _clamp(
        value: float,
    ) -> float:
        return min(max(float(value), 0.0), 1.0)