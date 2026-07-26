from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable

from src.attachments.ocr.models import OCRPage

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PageAnalysis:
    """
    Heuristic analysis result for one document page.
    """

    page_number: int
    document_type: str
    detected_language: str
    layout_complexity: str
    layout_score: float
    text_density: float
    average_line_length: float
    short_line_ratio: float
    uppercase_ratio: float
    numeric_ratio: float
    suspicious_character_ratio: float
    likely_multi_column: bool
    likely_table: bool
    likely_brochure: bool
    vision_recommended: bool
    vision_reasons: list[str] = field(
        default_factory=list
    )
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "document_type": self.document_type,
            "detected_language": (
                self.detected_language
            ),
            "layout_complexity": (
                self.layout_complexity
            ),
            "layout_score": self.layout_score,
            "text_density": self.text_density,
            "average_line_length": (
                self.average_line_length
            ),
            "short_line_ratio": (
                self.short_line_ratio
            ),
            "uppercase_ratio": (
                self.uppercase_ratio
            ),
            "numeric_ratio": self.numeric_ratio,
            "suspicious_character_ratio": (
                self.suspicious_character_ratio
            ),
            "likely_multi_column": (
                self.likely_multi_column
            ),
            "likely_table": self.likely_table,
            "likely_brochure": (
                self.likely_brochure
            ),
            "vision_recommended": (
                self.vision_recommended
            ),
            "vision_reasons": list(
                self.vision_reasons
            ),
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class DocumentAnalysis:
    """
    Analysis result for the complete document.
    """

    document_type: str
    detected_language: str
    layout_complexity: str
    average_layout_score: float
    vision_recommended: bool
    vision_pages: list[int]
    vision_reasons: list[str]
    page_analyses: list[PageAnalysis]
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": self.document_type,
            "detected_language": (
                self.detected_language
            ),
            "layout_complexity": (
                self.layout_complexity
            ),
            "average_layout_score": (
                self.average_layout_score
            ),
            "vision_recommended": (
                self.vision_recommended
            ),
            "vision_pages": list(
                self.vision_pages
            ),
            "vision_reasons": list(
                self.vision_reasons
            ),
            "page_analyses": [
                page.to_dict()
                for page in self.page_analyses
            ],
            "metadata": dict(self.metadata),
        }


class DocumentAnalyzer:
    """
    Analyze OCR output before Vision processing.

    The analyzer uses lightweight heuristics and does
    not require an external AI provider.
    """

    LANGUAGE_MARKERS = {
        "de": {
            "der",
            "die",
            "das",
            "und",
            "mit",
            "für",
            "von",
            "ist",
            "im",
            "eine",
            "einer",
            "auf",
            "durch",
            "fahrzeug",
            "leistung",
        },
        "en": {
            "the",
            "and",
            "with",
            "for",
            "from",
            "is",
            "are",
            "this",
            "that",
            "vehicle",
            "service",
            "document",
        },
        "id": {
            "yang",
            "dan",
            "dengan",
            "untuk",
            "dari",
            "adalah",
            "ini",
            "pada",
            "dalam",
            "atau",
        },
        "fr": {
            "le",
            "la",
            "les",
            "de",
            "des",
            "avec",
            "pour",
            "est",
            "une",
            "dans",
        },
    }

    TABLE_KEYWORDS = {
        "part number",
        "item number",
        "quantity",
        "description",
        "price",
        "total",
        "datum",
        "menge",
        "nummer",
        "bezeichnung",
    }

    BROCHURE_KEYWORDS = {
        "service",
        "services",
        "programme",
        "program",
        "classic",
        "classics",
        "leistung",
        "leistungen",
        "angebot",
        "contact",
        "telefon",
        "website",
        "www",
    }

    def __init__(
        self,
        *,
        low_confidence_threshold: float = 0.65,
        low_quality_threshold: float = 0.65,
        complex_layout_threshold: float = 0.60,
        suspicious_character_threshold: (
            float
        ) = 0.08,
    ) -> None:
        self.low_confidence_threshold = (
            low_confidence_threshold
        )
        self.low_quality_threshold = (
            low_quality_threshold
        )
        self.complex_layout_threshold = (
            complex_layout_threshold
        )
        self.suspicious_character_threshold = (
            suspicious_character_threshold
        )

    def analyze(
        self,
        pages: Iterable[OCRPage],
    ) -> DocumentAnalysis:
        ordered_pages = sorted(
            pages,
            key=lambda page: page.page_number,
        )

        page_analyses = [
            self.analyze_page(page)
            for page in ordered_pages
        ]

        document_type = (
            self._resolve_document_type(
                page_analyses
            )
        )

        detected_language = (
            self._resolve_language(
                page_analyses
            )
        )

        average_layout_score = (
            self._average(
                analysis.layout_score
                for analysis in page_analyses
            )
        )

        layout_complexity = (
            self._layout_complexity_label(
                average_layout_score
            )
        )

        vision_pages = [
            analysis.page_number
            for analysis in page_analyses
            if analysis.vision_recommended
        ]

        vision_reasons = sorted(
            {
                reason
                for analysis in page_analyses
                for reason in (
                    analysis.vision_reasons
                )
            }
        )

        result = DocumentAnalysis(
            document_type=document_type,
            detected_language=detected_language,
            layout_complexity=(
                layout_complexity
            ),
            average_layout_score=round(
                average_layout_score,
                4,
            ),
            vision_recommended=bool(
                vision_pages
            ),
            vision_pages=vision_pages,
            vision_reasons=vision_reasons,
            page_analyses=page_analyses,
            metadata={
                "total_pages": len(
                    page_analyses
                ),
                "analyzer": (
                    self.__class__.__name__
                ),
                "strategy": (
                    "deterministic_heuristics"
                ),
            },
        )

        logger.info(
            "Document analysis completed: "
            "type=%s language=%s "
            "layout=%s vision_recommended=%s "
            "vision_pages=%s",
            result.document_type,
            result.detected_language,
            result.layout_complexity,
            result.vision_recommended,
            result.vision_pages,
        )

        return result

    def analyze_page(
        self,
        page: OCRPage,
    ) -> PageAnalysis:
        text = page.text or ""

        lines = self._clean_lines(
            text.splitlines()
        )

        words = re.findall(
            r"\b[\wÀ-ÿ'-]+\b",
            text.lower(),
        )

        characters = [
            character
            for character in text
            if not character.isspace()
        ]

        average_line_length = (
            self._average(
                len(line)
                for line in lines
            )
        )

        short_line_ratio = (
            self._ratio(
                sum(
                    1
                    for line in lines
                    if len(line) <= 30
                ),
                len(lines),
            )
        )

        uppercase_ratio = (
            self._uppercase_ratio(text)
        )

        numeric_ratio = self._ratio(
            sum(
                character.isdigit()
                for character in characters
            ),
            len(characters),
        )

        suspicious_character_ratio = (
            self._suspicious_character_ratio(
                characters
            )
        )

        text_density = self._text_density(
            page=page,
            character_count=len(
                characters
            ),
        )

        detected_language = (
            self._detect_language(words)
        )

        likely_table = self._likely_table(
            text=text,
            lines=lines,
            numeric_ratio=numeric_ratio,
        )

        likely_multi_column = (
            self._likely_multi_column(
                lines=lines,
                short_line_ratio=(
                    short_line_ratio
                ),
            )
        )

        likely_brochure = (
            self._likely_brochure(
                words=words,
                uppercase_ratio=(
                    uppercase_ratio
                ),
                short_line_ratio=(
                    short_line_ratio
                ),
            )
        )

        layout_score = (
            self._calculate_layout_score(
                short_line_ratio=(
                    short_line_ratio
                ),
                uppercase_ratio=(
                    uppercase_ratio
                ),
                numeric_ratio=numeric_ratio,
                likely_table=likely_table,
                likely_multi_column=(
                    likely_multi_column
                ),
                likely_brochure=(
                    likely_brochure
                ),
            )
        )

        document_type = (
            self._classify_page_type(
                likely_table=likely_table,
                likely_brochure=(
                    likely_brochure
                ),
                likely_multi_column=(
                    likely_multi_column
                ),
                average_line_length=(
                    average_line_length
                ),
            )
        )

        vision_reasons = (
            self._build_vision_reasons(
                page=page,
                layout_score=layout_score,
                suspicious_character_ratio=(
                    suspicious_character_ratio
                ),
                likely_table=likely_table,
                likely_multi_column=(
                    likely_multi_column
                ),
                likely_brochure=(
                    likely_brochure
                ),
            )
        )

        return PageAnalysis(
            page_number=page.page_number,
            document_type=document_type,
            detected_language=(
                detected_language
            ),
            layout_complexity=(
                self._layout_complexity_label(
                    layout_score
                )
            ),
            layout_score=round(
                layout_score,
                4,
            ),
            text_density=round(
                text_density,
                6,
            ),
            average_line_length=round(
                average_line_length,
                2,
            ),
            short_line_ratio=round(
                short_line_ratio,
                4,
            ),
            uppercase_ratio=round(
                uppercase_ratio,
                4,
            ),
            numeric_ratio=round(
                numeric_ratio,
                4,
            ),
            suspicious_character_ratio=round(
                suspicious_character_ratio,
                4,
            ),
            likely_multi_column=(
                likely_multi_column
            ),
            likely_table=likely_table,
            likely_brochure=likely_brochure,
            vision_recommended=bool(
                vision_reasons
            ),
            vision_reasons=vision_reasons,
            metadata={
                "ocr_confidence": (
                    page.confidence
                ),
                "ocr_quality": (
                    page.quality_score
                ),
                "word_count": page.word_count,
                "line_count": len(lines),
                "character_count": len(
                    characters
                ),
            },
        )

    def _build_vision_reasons(
        self,
        *,
        page: OCRPage,
        layout_score: float,
        suspicious_character_ratio: float,
        likely_table: bool,
        likely_multi_column: bool,
        likely_brochure: bool,
    ) -> list[str]:
        reasons: list[str] = []

        if (
            page.confidence
            < self.low_confidence_threshold
        ):
            reasons.append(
                "low_ocr_confidence"
            )

        if (
            page.quality_score
            < self.low_quality_threshold
        ):
            reasons.append(
                "low_ocr_quality"
            )

        if (
            layout_score
            >= self.complex_layout_threshold
        ):
            reasons.append(
                "complex_layout"
            )

        if (
            suspicious_character_ratio
            >= self.suspicious_character_threshold
        ):
            reasons.append(
                "suspicious_ocr_characters"
            )

        if likely_table:
            reasons.append(
                "possible_table"
            )

        if likely_multi_column:
            reasons.append(
                "possible_multi_column_layout"
            )

        if likely_brochure:
            reasons.append(
                "possible_brochure_layout"
            )

        return reasons

    def _calculate_layout_score(
        self,
        *,
        short_line_ratio: float,
        uppercase_ratio: float,
        numeric_ratio: float,
        likely_table: bool,
        likely_multi_column: bool,
        likely_brochure: bool,
    ) -> float:
        score = 0.0

        score += min(
            short_line_ratio * 0.30,
            0.30,
        )

        score += min(
            uppercase_ratio * 0.20,
            0.20,
        )

        score += min(
            numeric_ratio * 0.15,
            0.15,
        )

        if likely_table:
            score += 0.20

        if likely_multi_column:
            score += 0.20

        if likely_brochure:
            score += 0.20

        return min(score, 1.0)

    def _detect_language(
        self,
        words: list[str],
    ) -> str:
        if not words:
            return "unknown"

        word_set = set(words)

        scores = {
            language: len(
                word_set.intersection(markers)
            )
            for language, markers in (
                self.LANGUAGE_MARKERS.items()
            )
        }

        language, score = max(
            scores.items(),
            key=lambda item: item[1],
        )

        if score == 0:
            return "unknown"

        return language

    def _likely_table(
        self,
        *,
        text: str,
        lines: list[str],
        numeric_ratio: float,
    ) -> bool:
        normalized = text.lower()

        keyword_matches = sum(
            1
            for keyword in self.TABLE_KEYWORDS
            if keyword in normalized
        )

        aligned_spacing_lines = sum(
            1
            for line in lines
            if re.search(r"\S+\s{3,}\S+", line)
        )

        return (
            keyword_matches >= 2
            or aligned_spacing_lines >= 3
            or (
                numeric_ratio >= 0.20
                and len(lines) >= 5
            )
        )

    @staticmethod
    def _likely_multi_column(
        *,
        lines: list[str],
        short_line_ratio: float,
    ) -> bool:
        separated_lines = sum(
            1
            for line in lines
            if re.search(r"\S+\s{5,}\S+", line)
        )

        return (
            separated_lines >= 3
            or (
                len(lines) >= 12
                and short_line_ratio >= 0.65
            )
        )

    def _likely_brochure(
        self,
        *,
        words: list[str],
        uppercase_ratio: float,
        short_line_ratio: float,
    ) -> bool:
        word_set = set(words)

        keyword_matches = len(
            word_set.intersection(
                self.BROCHURE_KEYWORDS
            )
        )

        return (
            keyword_matches >= 2
            and (
                uppercase_ratio >= 0.08
                or short_line_ratio >= 0.50
            )
        )

    @staticmethod
    def _classify_page_type(
        *,
        likely_table: bool,
        likely_brochure: bool,
        likely_multi_column: bool,
        average_line_length: float,
    ) -> str:
        if likely_table:
            return "table_or_catalog"

        if likely_brochure:
            return "brochure_or_flyer"

        if likely_multi_column:
            return "multi_column_document"

        if average_line_length >= 65:
            return "narrative_document"

        return "general_document"

    @staticmethod
    def _text_density(
        *,
        page: OCRPage,
        character_count: int,
    ) -> float:
        metadata = page.metadata or {}

        width = metadata.get("width")
        height = metadata.get("height")

        if not width or not height:
            return float(character_count)

        area = float(width) * float(height)

        if area <= 0:
            return float(character_count)

        return character_count / area

    @staticmethod
    def _uppercase_ratio(
        text: str,
    ) -> float:
        alphabetic = [
            character
            for character in text
            if character.isalpha()
        ]

        if not alphabetic:
            return 0.0

        uppercase = sum(
            character.isupper()
            for character in alphabetic
        )

        return uppercase / len(alphabetic)

    @staticmethod
    def _suspicious_character_ratio(
        characters: list[str],
    ) -> float:
        if not characters:
            return 0.0

        suspicious = sum(
            1
            for character in characters
            if character in {
                "�",
                "¦",
                "¬",
                "¤",
                "§",
                "©",
                "®",
                "™",
            }
        )

        return suspicious / len(characters)

    @staticmethod
    def _clean_lines(
        lines: Iterable[str],
    ) -> list[str]:
        return [
            line.strip()
            for line in lines
            if line.strip()
        ]

    @staticmethod
    def _ratio(
        numerator: int,
        denominator: int,
    ) -> float:
        if denominator <= 0:
            return 0.0

        return numerator / denominator

    @staticmethod
    def _average(
        values: Iterable[float],
    ) -> float:
        materialized = list(values)

        if not materialized:
            return 0.0

        return sum(materialized) / len(
            materialized
        )

    @staticmethod
    def _layout_complexity_label(
        score: float,
    ) -> str:
        if score >= 0.70:
            return "high"

        if score >= 0.40:
            return "medium"

        return "low"

    @staticmethod
    def _resolve_document_type(
        analyses: list[PageAnalysis],
    ) -> str:
        if not analyses:
            return "unknown"

        counter = Counter(
            analysis.document_type
            for analysis in analyses
        )

        return counter.most_common(1)[0][0]

    @staticmethod
    def _resolve_language(
        analyses: list[PageAnalysis],
    ) -> str:
        languages = [
            analysis.detected_language
            for analysis in analyses
            if analysis.detected_language
            != "unknown"
        ]

        if not languages:
            return "unknown"

        return Counter(
            languages
        ).most_common(1)[0][0]