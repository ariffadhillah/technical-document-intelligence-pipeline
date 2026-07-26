from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .models import OCRPage


@dataclass(slots=True)
class OCRConfidenceReport:
    """
    Detailed OCR quality report.
    """

    engine_confidence: float

    word_score: float

    character_score: float

    readable_character_score: float

    empty_text_penalty: float

    quality_score: float

    needs_retry: bool

    reason: str


class OCRConfidenceScorer:
    """
    Estimate OCR quality using several signals.

    Final score range:

        0.0 - 1.0
    """

    def __init__(
        self,
        retry_threshold: float = 0.60,
    ) -> None:

        self.retry_threshold = retry_threshold

    def score(
        self,
        page: OCRPage,
    ) -> OCRConfidenceReport:

        text = page.text.strip()

        if not text:
            return OCRConfidenceReport(
                engine_confidence=0.0,
                word_score=0.0,
                character_score=0.0,
                readable_character_score=0.0,
                empty_text_penalty=1.0,
                quality_score=0.0,
                needs_retry=True,
                reason="OCR returned empty text.",
            )

        engine_confidence = self._normalize_confidence(
            page.confidence
        )

        word_score = self._word_score(page.word_count)

        character_score = self._character_score(len(text))

        readable_character_score = (
            self._readable_character_score(text)
        )

        empty_text_penalty = 0.0

        quality_score = (
            engine_confidence * 0.45
            + word_score * 0.20
            + character_score * 0.15
            + readable_character_score * 0.20
            - empty_text_penalty
        )

        quality_score = min(
            max(quality_score, 0.0),
            1.0,
        )

        needs_retry = quality_score < self.retry_threshold

        reason = (
            f"OCR quality score is {quality_score:.2f}. "
            f"Retry threshold is {self.retry_threshold:.2f}."
        )

        return OCRConfidenceReport(
            engine_confidence=engine_confidence,
            word_score=word_score,
            character_score=character_score,
            readable_character_score=readable_character_score,
            empty_text_penalty=empty_text_penalty,
            quality_score=quality_score,
            needs_retry=needs_retry,
            reason=reason,
        )

    @staticmethod
    def _normalize_confidence(
        confidence: float,
    ) -> float:

        if confidence > 1.0:
            confidence = confidence / 100.0

        return min(max(confidence, 0.0), 1.0)

    @staticmethod
    def _word_score(
        word_count: int,
    ) -> float:
        """
        Saturating score so long pages do not receive
        unlimited advantage.
        """

        if word_count <= 0:
            return 0.0

        return min(
            math.log1p(word_count) / math.log1p(100),
            1.0,
        )

    @staticmethod
    def _character_score(
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

        readable_characters = re.findall(
            r"[A-Za-zÀ-ÿ0-9.,:;!?%()/+\-]",
            text,
        )

        return min(
            len(readable_characters) / len(text),
            1.0,
        )