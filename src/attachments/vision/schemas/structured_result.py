from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BoundingBox:
    """
    Normalized bounding box.

    Coordinates use a 0-1 range.
    """

    x: float
    y: float
    width: float
    height: float


@dataclass(slots=True)
class EntityResult:
    """
    Named entity extracted from a page.
    """

    text: str
    label: str
    confidence: float | None = None
    bbox: BoundingBox | None = None


@dataclass(slots=True)
class FigureResult:
    """
    Figure or image detected on a page.
    """

    caption: str | None = None
    description: str | None = None
    bbox: BoundingBox | None = None


@dataclass(slots=True)
class TableResult:
    """
    Structured table.
    """

    rows: list[list[str]] = field(default_factory=list)

    markdown: str | None = None

    csv: str | None = None

    confidence: float | None = None


@dataclass(slots=True)
class StructuredVisionResult:
    """
    Unified internal vision result.

    Every vision provider
    (OpenAI, Gemini, Claude, Ollama, etc.)
    must return this object.
    """

    provider: str

    model: str

    document_type: str

    page_type: str

    language: str

    title: str | None = None

    summary: str | None = None

    ocr_text: str = ""

    keywords: list[str] = field(default_factory=list)

    entities: list[EntityResult] = field(default_factory=list)

    tables: list[TableResult] = field(default_factory=list)

    figures: list[FigureResult] = field(default_factory=list)

    warnings: list[str] = field(default_factory=list)

    confidence: float | None = None

    processing_time: float | None = None

    input_tokens: int | None = None

    output_tokens: int | None = None

    estimated_cost: float | None = None

    metadata: dict[str, Any] = field(default_factory=dict)