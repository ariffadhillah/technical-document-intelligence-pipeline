from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from ..ocr.models import OCRPage


class VisionPriority(str, Enum):
    """
    Priority assigned to a Vision request.
    """

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class VisionReason(str, Enum):
    """
    Reason why a page is routed to Vision.
    """

    NONE = "none"
    EMPTY_OCR = "empty_ocr"
    LOW_OCR_QUALITY = "low_ocr_quality"
    LOW_OCR_CONFIDENCE = "low_ocr_confidence"
    LOW_WORD_COUNT = "low_word_count"
    HIGH_NOISE_RATIO = "high_noise_ratio"
    UNKNOWN_LANGUAGE = "unknown_language"
    TABLE_CONTENT = "table_content"
    DIAGRAM_CONTENT = "diagram_content"
    DRAWING_CONTENT = "drawing_content"
    PHOTO_CONTENT = "photo_content"
    MANUAL_OVERRIDE = "manual_override"


@dataclass(slots=True)
class VisionPageScore:
    """
    Quality evaluation for one OCR page.

    All normalized scores use the range 0.0–1.0.
    """

    page_number: int

    quality_score: float

    ocr_confidence_score: float

    word_count_score: float

    character_density_score: float

    readable_character_score: float

    language_score: float

    noise_score: float

    needs_vision: bool

    reasons: list[VisionReason] = field(default_factory=list)

    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VisionDecision:
    """
    Routing decision for one page.
    """

    page_number: int

    use_vision: bool

    provider: str | None = None

    model: str | None = None

    priority: VisionPriority = VisionPriority.NORMAL

    reasons: list[VisionReason] = field(default_factory=list)

    score: VisionPageScore | None = None

    estimated_cost: float | None = None

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VisionRequest:
    """
    Request sent to a Vision provider.
    """

    image: np.ndarray

    page_number: int

    prompt: str

    provider: str

    model: str

    prompt_version: str = "1.0"

    source_path: Path | None = None

    ocr_page: OCRPage | None = None

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VisionResponse:
    """
    Raw normalized response from a Vision provider.
    """

    page_number: int

    text: str

    provider: str

    model: str

    confidence: float | None = None

    processing_time: float = 0.0

    input_tokens: int | None = None

    output_tokens: int | None = None

    estimated_cost: float | None = None

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VisionAuditEntry:
    """
    Complete processing audit for one page.
    """

    page_number: int

    ocr_quality: float

    ocr_confidence: float

    vision_used: bool

    vision_provider: str | None = None

    vision_model: str | None = None

    cache_hit: bool = False

    retry_count: int = 0

    processing_time: float = 0.0

    estimated_cost: float | None = None

    final_quality: float | None = None

    reasons: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)