from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .models import OCRDocument, OCRPage


class OCRPageMerger:
    """
    Merge multiple OCR pages into one OCR document.
    """

    def __init__(
        self,
        remove_repeated_headers: bool = True,
        remove_repeated_footers: bool = True,
    ) -> None:

        self.remove_repeated_headers = (
            remove_repeated_headers
        )

        self.remove_repeated_footers = (
            remove_repeated_footers
        )

    def merge(
        self,
        pages: list[OCRPage],
        *,
        source_path: str | Path | None = None,
        page_separator: str = "\n\n",
    ) -> OCRDocument:

        ordered_pages = sorted(
            pages,
            key=lambda page: page.page_number,
        )

        if self.remove_repeated_headers:
            self._remove_repeated_boundary_lines(
                ordered_pages,
                boundary="header",
            )

        if self.remove_repeated_footers:
            self._remove_repeated_boundary_lines(
                ordered_pages,
                boundary="footer",
            )

        document_text = page_separator.join(
            page.text.strip()
            for page in ordered_pages
            if page.text.strip()
        )

        language = self._dominant_language(
            ordered_pages
        )

        confidence = self._average(
            [
                page.confidence
                for page in ordered_pages
                if page.confidence > 0.0
            ]
        )

        quality_score = self._average(
            [
                page.quality_score
                for page in ordered_pages
                if page.quality_score > 0.0
            ]
        )

        return OCRDocument(
            pages=ordered_pages,
            text=document_text,
            confidence=confidence,
            quality_score=quality_score,
            language=language,
            source_path=(
                Path(source_path)
                if source_path is not None
                else None
            ),
            metadata={
                "merged_page_count": len(ordered_pages),
            },
        )

    def _remove_repeated_boundary_lines(
        self,
        pages: list[OCRPage],
        *,
        boundary: str,
    ) -> None:

        if len(pages) < 3:
            return

        boundary_lines: list[str] = []

        for page in pages:
            lines = self._non_empty_lines(page.text)

            if not lines:
                continue

            if boundary == "header":
                boundary_lines.append(
                    self._normalize_boundary_line(lines[0])
                )
            else:
                boundary_lines.append(
                    self._normalize_boundary_line(lines[-1])
                )

        frequencies = Counter(boundary_lines)

        repeated = {
            line
            for line, count in frequencies.items()
            if line and count >= max(2, len(pages) // 2)
        }

        if not repeated:
            return

        for page in pages:
            lines = page.text.splitlines()

            non_empty_indexes = [
                index
                for index, line in enumerate(lines)
                if line.strip()
            ]

            if not non_empty_indexes:
                continue

            index = (
                non_empty_indexes[0]
                if boundary == "header"
                else non_empty_indexes[-1]
            )

            normalized = self._normalize_boundary_line(
                lines[index]
            )

            if normalized in repeated:
                del lines[index]

                page.text = "\n".join(lines).strip()

    @staticmethod
    def _normalize_boundary_line(
        line: str,
    ) -> str:

        line = line.strip().lower()

        line = re.sub(
            r"\bpage\s+\d+\b",
            "page",
            line,
        )

        line = re.sub(
            r"\b\d+\b",
            "#",
            line,
        )

        line = re.sub(
            r"\s+",
            " ",
            line,
        )

        return line

    @staticmethod
    def _non_empty_lines(
        text: str,
    ) -> list[str]:

        return [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

    @staticmethod
    def _dominant_language(
        pages: list[OCRPage],
    ) -> str | None:

        languages = [
            page.language
            for page in pages
            if page.language
            and page.language != "unknown"
        ]

        if not languages:
            return None

        return Counter(languages).most_common(1)[0][0]

    @staticmethod
    def _average(
        values: list[float],
    ) -> float:

        if not values:
            return 0.0

        return sum(values) / len(values)