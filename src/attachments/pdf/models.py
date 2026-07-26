from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class PDFType(str, Enum):
    """Jenis PDF yang berhasil dideteksi."""

    DIGITAL = "digital"
    SCANNED = "scanned"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class ExtractionMethod(str, Enum):
    """Metode yang dipakai untuk menghasilkan text."""

    TEXT_LAYER = "text_layer"
    OCR = "ocr"
    VISION = "vision"


@dataclass(slots=True)
class PDFPageAnalysis:
    """
    Hasil analisa satu halaman PDF.
    """

    page_number: int

    width: float
    height: float

    extracted_characters: int

    has_text_layer: bool

    is_scanned: bool

    rotation: int = 0


@dataclass(slots=True)
class PDFAnalysisResult:
    """
    Hasil analisa keseluruhan PDF.
    """

    source: Path

    pdf_type: PDFType

    page_count: int

    total_characters: int

    has_text_layer: bool

    is_scanned: bool

    pages: list[PDFPageAnalysis] = field(default_factory=list)


@dataclass(slots=True)
class RenderedPage:
    """
    Hasil render PDF menjadi image.
    """

    page_number: int

    image_path: Path

    dpi: int

    width: int

    height: int


@dataclass(slots=True)
class OCRPageResult:
    """
    Hasil OCR per halaman.
    """

    page_number: int

    confidence: float

    word_count: int

    character_count: int

    language: Optional[str]

    text: str


@dataclass(slots=True)
class PDFExtractionResult:
    """
    Hasil akhir extraction.
    """

    source: Path

    method: ExtractionMethod

    page_count: int

    pages: list[OCRPageResult]

    merged_text: str

    average_confidence: float

    used_vision_fallback: bool = False