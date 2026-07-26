from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class LanguageDetectionResult:
    language: str

    confidence: float

    reason: str


class OCRLanguageDetector:
    """
    Lightweight language detector for OCR text.

    This is intentionally dependency-free.

    It can later be replaced by:

        - fastText
        - langdetect
        - lingua
        - compact-language-detector
    """

    ENGLISH_WORDS = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "this",
        "that",
        "installation",
        "manual",
        "warning",
        "system",
        "equipment",
    }

    INDONESIAN_WORDS = {
        "dan",
        "yang",
        "untuk",
        "dengan",
        "dari",
        "ini",
        "pada",
        "adalah",
        "panduan",
        "peringatan",
        "sistem",
        "peralatan",
    }

    GERMAN_WORDS = {
        "der",
        "die",
        "das",
        "und",
        "für",
        "mit",
        "von",
        "ist",
        "anleitung",
        "warnung",
        "system",
    }

    def detect(
        self,
        text: str,
    ) -> LanguageDetectionResult:

        cleaned = text.strip().lower()

        if not cleaned:
            return LanguageDetectionResult(
                language="unknown",
                confidence=0.0,
                reason="No text available.",
            )

        if re.search(r"[\u0600-\u06ff]", cleaned):
            return LanguageDetectionResult(
                language="ara",
                confidence=0.98,
                reason="Arabic Unicode characters detected.",
            )

        if re.search(r"[\u4e00-\u9fff]", cleaned):
            return LanguageDetectionResult(
                language="chi",
                confidence=0.98,
                reason="CJK Unicode characters detected.",
            )

        words = set(
            re.findall(
                r"[a-zA-ZÀ-ÿ]+",
                cleaned,
            )
        )

        scores = {
            "eng": len(words & self.ENGLISH_WORDS),
            "ind": len(words & self.INDONESIAN_WORDS),
            "deu": len(words & self.GERMAN_WORDS),
        }

        language = max(scores, key=scores.get)
        best_score = scores[language]

        if best_score == 0:
            return LanguageDetectionResult(
                language="unknown",
                confidence=0.20,
                reason="No reliable language indicators detected.",
            )

        total_score = sum(scores.values())

        confidence = (
            best_score / total_score
            if total_score > 0
            else 0.0
        )

        return LanguageDetectionResult(
            language=language,
            confidence=min(confidence, 1.0),
            reason=(
                f"Matched {best_score} common words "
                f"for language '{language}'."
            ),
        )