from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..ocr.models import OCRPage
from .models import (
    VisionAuditEntry,
    VisionDecision,
    VisionResponse,
)


@dataclass(slots=True)
class VisionProcessingResult:
    """
    Result of processing one page through Vision.
    """

    success: bool

    decision: VisionDecision

    response: VisionResponse | None = None

    original_ocr_page: OCRPage | None = None

    final_page: OCRPage | None = None

    from_cache: bool = False

    error: str | None = None

    audit: VisionAuditEntry | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        if self.final_page is not None:
            return self.final_page.text

        if self.response is not None:
            return self.response.text

        if self.original_ocr_page is not None:
            return self.original_ocr_page.text

        return ""


@dataclass(slots=True)
class VisionBatchResult:
    """
    Result of routing multiple pages through Vision.
    """

    pages: list[OCRPage] = field(default_factory=list)

    results: list[VisionProcessingResult] = field(
        default_factory=list
    )

    audits: list[VisionAuditEntry] = field(
        default_factory=list
    )

    total_pages: int = 0

    vision_pages: int = 0

    cache_hits: int = 0

    failures: int = 0

    processing_time: float = 0.0

    estimated_cost: float = 0.0

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def vision_usage_ratio(self) -> float:
        if self.total_pages <= 0:
            return 0.0

        return self.vision_pages / self.total_pages