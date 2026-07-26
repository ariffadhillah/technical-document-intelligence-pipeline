from __future__ import annotations

import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from .base import BaseOCREngine
from .cache import OCRCache
from .cleaner import OCRTextCleaner
from .confidence import OCRConfidenceScorer
from .exceptions import (
    OCRConfigurationError,
    OCRProcessingError,
)
from .language import OCRLanguageDetector
from .models import (
    BoundingBox,
    OCRLine,
    OCRPage,
    OCRParagraph,
    OCRWord,
)

logger = logging.getLogger(__name__)


class TesseractOCREngine(BaseOCREngine):
    """
    Structured OCR engine powered by Tesseract.
    """

    engine_name = "tesseract"

    def __init__(
        self,
        *,
        default_language: str = "eng",
        psm: int = 3,
        oem: int = 3,
        tesseract_cmd: str | None = None,
        extra_config: str = "",
        use_cache: bool = True,
        cache_dir: str | Path = "output/cache/ocr",
        retry_threshold: float = 0.60,
    ) -> None:

        try:
            import pytesseract
        except ImportError as exc:
            raise OCRConfigurationError(
                "pytesseract is not installed. "
                "Install it using: pip install pytesseract"
            ) from exc

        self.pytesseract = pytesseract

        if tesseract_cmd:
            self.pytesseract.pytesseract.tesseract_cmd = (
                tesseract_cmd
            )

        self.default_language = default_language

        self.psm = psm

        self.oem = oem

        self.extra_config = extra_config.strip()

        self.cleaner = OCRTextCleaner()

        self.language_detector = OCRLanguageDetector()

        self.confidence_scorer = OCRConfidenceScorer(
            retry_threshold=retry_threshold
        )

        self.cache = OCRCache(
            cache_dir=cache_dir,
            enabled=use_cache,
        )

    def process_image(
        self,
        image: np.ndarray,
        *,
        page_number: int = 1,
        source_path: str | Path | None = None,
        language: str | None = None,
    ) -> OCRPage:

        if image is None or image.size == 0:
            raise OCRProcessingError(
                "Cannot OCR an empty image."
            )

        selected_language = (
            language or self.default_language
        )

        config = self._build_config()

        cache_key = self.cache.build_key(
            image,
            engine_name=self.engine_name,
            language=selected_language,
            config={
                "psm": self.psm,
                "oem": self.oem,
                "extra_config": self.extra_config,
            },
        )

        cached_page = self.cache.get(cache_key)

        if cached_page is not None:
            cached_page.metadata["from_cache"] = True

            logger.info(
                "Loaded OCR page %s from cache.",
                page_number,
            )

            return cached_page

        started_at = time.perf_counter()

        try:
            output = self.pytesseract.image_to_data(
                image,
                lang=selected_language,
                config=config,
                output_type=(
                    self.pytesseract.Output.DICT
                ),
            )

        except Exception as exc:
            raise OCRProcessingError(
                f"Tesseract OCR failed for page "
                f"{page_number}: {exc}"
            ) from exc

        paragraphs = self._build_paragraphs(
            output,
            selected_language,
        )

        raw_text = "\n\n".join(
            paragraph.text
            for paragraph in paragraphs
            if paragraph.text.strip()
        )

        processing_time = (
            time.perf_counter() - started_at
        )

        height, width = image.shape[:2]

        page = OCRPage(
            page_number=page_number,
            paragraphs=paragraphs,
            text=raw_text,
            confidence=self._paragraph_confidence(
                paragraphs
            ),
            language=selected_language,
            width=width,
            height=height,
            source_path=(
                Path(source_path)
                if source_path is not None
                else None
            ),
            engine_name=self.engine_name,
            processing_time=processing_time,
            metadata={
                "psm": self.psm,
                "oem": self.oem,
                "from_cache": False,
            },
        )

        page = self.cleaner.clean_page(page)

        detected_language = (
            self.language_detector.detect(page.text)
        )

        if detected_language.language != "unknown":
            page.language = detected_language.language

        page.metadata["language_detection"] = {
            "language": detected_language.language,
            "confidence": detected_language.confidence,
            "reason": detected_language.reason,
        }

        confidence_report = (
            self.confidence_scorer.score(page)
        )

        page.quality_score = (
            confidence_report.quality_score
        )

        page.metadata["confidence_report"] = {
            "engine_confidence": (
                confidence_report.engine_confidence
            ),
            "word_score": confidence_report.word_score,
            "character_score": (
                confidence_report.character_score
            ),
            "readable_character_score": (
                confidence_report.readable_character_score
            ),
            "quality_score": (
                confidence_report.quality_score
            ),
            "needs_retry": confidence_report.needs_retry,
            "reason": confidence_report.reason,
        }

        self.cache.set(
            cache_key,
            page,
        )

        logger.info(
            (
                "Tesseract completed page %s: "
                "words=%s confidence=%.2f quality=%.2f "
                "time=%.2fs"
            ),
            page_number,
            page.word_count,
            page.confidence,
            page.quality_score,
            processing_time,
        )

        return page

    def is_available(self) -> bool:
        try:
            self.pytesseract.get_tesseract_version()

            return True

        except Exception:
            return False

    def get_version(self) -> str | None:
        try:
            return str(
                self.pytesseract.get_tesseract_version()
            )

        except Exception:
            return None

    def _build_config(self) -> str:

        config_parts = [
            f"--oem {self.oem}",
            f"--psm {self.psm}",
        ]

        if self.extra_config:
            config_parts.append(
                self.extra_config
            )

        return " ".join(config_parts)

    def _build_paragraphs(
        self,
        output: dict[str, list[Any]],
        language: str,
    ) -> list[OCRParagraph]:

        paragraph_groups: dict[
            tuple[int, int, int],
            dict[tuple[int, int, int, int], list[OCRWord]],
        ] = defaultdict(
            lambda: defaultdict(list)
        )

        item_count = len(
            output.get("text", [])
        )

        for index in range(item_count):
            text = str(
                output["text"][index]
            ).strip()

            confidence = self._parse_confidence(
                output["conf"][index]
            )

            if not text or confidence < 0.0:
                continue

            page_num = int(
                output["page_num"][index]
            )

            block_num = int(
                output["block_num"][index]
            )

            paragraph_num = int(
                output["par_num"][index]
            )

            line_num = int(
                output["line_num"][index]
            )

            left = int(output["left"][index])

            top = int(output["top"][index])

            width = int(output["width"][index])

            height = int(output["height"][index])

            word = OCRWord(
                text=text,
                confidence=confidence,
                bounding_box=(
                    left,
                    top,
                    width,
                    height,
                ),
                language=language,
                metadata={
                    "word_num": int(
                        output["word_num"][index]
                    ),
                },
            )

            paragraph_key = (
                page_num,
                block_num,
                paragraph_num,
            )

            line_key = (
                page_num,
                block_num,
                paragraph_num,
                line_num,
            )

            paragraph_groups[
                paragraph_key
            ][line_key].append(word)

        paragraphs: list[OCRParagraph] = []

        for paragraph_key in sorted(
            paragraph_groups
        ):
            line_groups = paragraph_groups[
                paragraph_key
            ]

            lines: list[OCRLine] = []

            for line_key in sorted(line_groups):
                words = line_groups[line_key]

                line = OCRLine(
                    words=words,
                    bounding_box=self._merge_boxes(
                        [
                            word.bounding_box
                            for word in words
                            if word.bounding_box
                            is not None
                        ]
                    ),
                    metadata={
                        "page_num": line_key[0],
                        "block_num": line_key[1],
                        "paragraph_num": line_key[2],
                        "line_num": line_key[3],
                    },
                )

                lines.append(line)

            paragraph = OCRParagraph(
                lines=lines,
                bounding_box=self._merge_boxes(
                    [
                        line.bounding_box
                        for line in lines
                        if line.bounding_box is not None
                    ]
                ),
                metadata={
                    "page_num": paragraph_key[0],
                    "block_num": paragraph_key[1],
                    "paragraph_num": paragraph_key[2],
                },
            )

            paragraphs.append(paragraph)

        return paragraphs

    @staticmethod
    def _parse_confidence(
        raw_confidence: Any,
    ) -> float:

        try:
            confidence = float(
                raw_confidence
            )

        except (
            TypeError,
            ValueError,
        ):
            return -1.0

        if confidence < 0:
            return -1.0

        return min(
            max(confidence / 100.0, 0.0),
            1.0,
        )

    @staticmethod
    def _merge_boxes(
        boxes: list[BoundingBox],
    ) -> BoundingBox | None:

        if not boxes:
            return None

        left = min(
            box[0]
            for box in boxes
        )

        top = min(
            box[1]
            for box in boxes
        )

        right = max(
            box[0] + box[2]
            for box in boxes
        )

        bottom = max(
            box[1] + box[3]
            for box in boxes
        )

        return (
            left,
            top,
            right - left,
            bottom - top,
        )

    @staticmethod
    def _paragraph_confidence(
        paragraphs: list[OCRParagraph],
    ) -> float:

        confidences = [
            paragraph.confidence
            for paragraph in paragraphs
            if paragraph.confidence > 0.0
        ]

        if not confidences:
            return 0.0

        return (
            sum(confidences)
            / len(confidences)
        )