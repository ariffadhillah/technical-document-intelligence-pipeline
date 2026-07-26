from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


BoundingBox = tuple[int, int, int, int]


@dataclass(slots=True)
class OCRWord:
    """
    A single OCR word and its position.

    Bounding box format:

        x, y, width, height
    """

    text: str

    confidence: float = 0.0

    bounding_box: BoundingBox | None = None

    language: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bounding_box": (
                list(self.bounding_box)
                if self.bounding_box is not None
                else None
            ),
            "language": self.language,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> OCRWord:

        bounding_box = data.get("bounding_box")

        return cls(
            text=data.get("text", ""),
            confidence=float(data.get("confidence", 0.0)),
            bounding_box=(
                tuple(bounding_box)
                if bounding_box is not None
                else None
            ),
            language=data.get("language"),
            metadata=data.get("metadata", {}),
        )


@dataclass(slots=True)
class OCRLine:
    """
    A logical line containing one or more OCR words.
    """

    words: list[OCRWord] = field(default_factory=list)

    text: str = ""

    confidence: float = 0.0

    bounding_box: BoundingBox | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text and self.words:
            self.text = " ".join(
                word.text
                for word in self.words
                if word.text.strip()
            )

        if self.confidence <= 0.0 and self.words:
            confidences = [
                word.confidence
                for word in self.words
                if word.confidence > 0.0
            ]

            if confidences:
                self.confidence = sum(confidences) / len(confidences)

    def to_dict(self) -> dict[str, Any]:
        return {
            "words": [word.to_dict() for word in self.words],
            "text": self.text,
            "confidence": self.confidence,
            "bounding_box": (
                list(self.bounding_box)
                if self.bounding_box is not None
                else None
            ),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> OCRLine:

        bounding_box = data.get("bounding_box")

        return cls(
            words=[
                OCRWord.from_dict(item)
                for item in data.get("words", [])
            ],
            text=data.get("text", ""),
            confidence=float(data.get("confidence", 0.0)),
            bounding_box=(
                tuple(bounding_box)
                if bounding_box is not None
                else None
            ),
            metadata=data.get("metadata", {}),
        )


@dataclass(slots=True)
class OCRParagraph:
    """
    A paragraph containing one or more OCR lines.
    """

    lines: list[OCRLine] = field(default_factory=list)

    text: str = ""

    confidence: float = 0.0

    bounding_box: BoundingBox | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text and self.lines:
            self.text = "\n".join(
                line.text
                for line in self.lines
                if line.text.strip()
            )

        if self.confidence <= 0.0 and self.lines:
            confidences = [
                line.confidence
                for line in self.lines
                if line.confidence > 0.0
            ]

            if confidences:
                self.confidence = sum(confidences) / len(confidences)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lines": [line.to_dict() for line in self.lines],
            "text": self.text,
            "confidence": self.confidence,
            "bounding_box": (
                list(self.bounding_box)
                if self.bounding_box is not None
                else None
            ),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> OCRParagraph:

        bounding_box = data.get("bounding_box")

        return cls(
            lines=[
                OCRLine.from_dict(item)
                for item in data.get("lines", [])
            ],
            text=data.get("text", ""),
            confidence=float(data.get("confidence", 0.0)),
            bounding_box=(
                tuple(bounding_box)
                if bounding_box is not None
                else None
            ),
            metadata=data.get("metadata", {}),
        )


@dataclass(slots=True)
class OCRPage:
    """
    OCR result for one image or document page.
    """

    page_number: int

    paragraphs: list[OCRParagraph] = field(
        default_factory=list
    )

    text: str = ""

    confidence: float = 0.0

    quality_score: float = 0.0

    language: str | None = None

    width: int | None = None

    height: int | None = None

    source_path: Path | None = None

    engine_name: str | None = None

    processing_time: float = 0.0

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text and self.paragraphs:
            self.text = "\n\n".join(
                paragraph.text
                for paragraph in self.paragraphs
                if paragraph.text.strip()
            )

        if self.confidence <= 0.0 and self.paragraphs:
            confidences = [
                paragraph.confidence
                for paragraph in self.paragraphs
                if paragraph.confidence > 0.0
            ]

            if confidences:
                self.confidence = sum(confidences) / len(confidences)

    @property
    def word_count(self) -> int:
        return sum(
            len(line.words)
            for paragraph in self.paragraphs
            for line in paragraph.lines
        )

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "paragraphs": [
                paragraph.to_dict()
                for paragraph in self.paragraphs
            ],
            "text": self.text,
            "confidence": self.confidence,
            "quality_score": self.quality_score,
            "language": self.language,
            "width": self.width,
            "height": self.height,
            "source_path": (
                str(self.source_path)
                if self.source_path is not None
                else None
            ),
            "engine_name": self.engine_name,
            "processing_time": self.processing_time,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> OCRPage:

        source_path = data.get("source_path")

        return cls(
            page_number=int(data.get("page_number", 1)),
            paragraphs=[
                OCRParagraph.from_dict(item)
                for item in data.get("paragraphs", [])
            ],
            text=data.get("text", ""),
            confidence=float(data.get("confidence", 0.0)),
            quality_score=float(data.get("quality_score", 0.0)),
            language=data.get("language"),
            width=data.get("width"),
            height=data.get("height"),
            source_path=(
                Path(source_path)
                if source_path
                else None
            ),
            engine_name=data.get("engine_name"),
            processing_time=float(
                data.get("processing_time", 0.0)
            ),
            metadata=data.get("metadata", {}),
        )


@dataclass(slots=True)
class OCRDocument:
    """
    Complete OCR document containing multiple pages.
    """

    pages: list[OCRPage] = field(default_factory=list)

    text: str = ""

    confidence: float = 0.0

    quality_score: float = 0.0

    language: str | None = None

    source_path: Path | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text and self.pages:
            self.text = "\n\n".join(
                page.text
                for page in self.pages
                if page.text.strip()
            )

        if self.confidence <= 0.0 and self.pages:
            confidences = [
                page.confidence
                for page in self.pages
                if page.confidence > 0.0
            ]

            if confidences:
                self.confidence = sum(confidences) / len(confidences)

        if self.quality_score <= 0.0 and self.pages:
            quality_scores = [
                page.quality_score
                for page in self.pages
                if page.quality_score > 0.0
            ]

            if quality_scores:
                self.quality_score = (
                    sum(quality_scores) / len(quality_scores)
                )

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def word_count(self) -> int:
        return sum(page.word_count for page in self.pages)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pages": [page.to_dict() for page in self.pages],
            "text": self.text,
            "confidence": self.confidence,
            "quality_score": self.quality_score,
            "language": self.language,
            "source_path": (
                str(self.source_path)
                if self.source_path is not None
                else None
            ),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> OCRDocument:

        source_path = data.get("source_path")

        return cls(
            pages=[
                OCRPage.from_dict(item)
                for item in data.get("pages", [])
            ],
            text=data.get("text", ""),
            confidence=float(data.get("confidence", 0.0)),
            quality_score=float(data.get("quality_score", 0.0)),
            language=data.get("language"),
            source_path=(
                Path(source_path)
                if source_path
                else None
            ),
            metadata=data.get("metadata", {}),
        )