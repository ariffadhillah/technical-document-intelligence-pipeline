from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import OCRDocument, OCRPage


@dataclass(slots=True)
class OCRProcessingResult:
    """
    Result returned by an OCR engine for one page.
    """

    success: bool

    page: OCRPage | None = None

    error: str | None = None

    engine_name: str | None = None

    from_cache: bool = False

    processing_time: float = 0.0

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        if self.page is None:
            return ""

        return self.page.text


@dataclass(slots=True)
class OCRDocumentResult:
    """
    Result returned after processing and merging
    multiple OCR pages.
    """

    success: bool

    document: OCRDocument | None = None

    errors: list[str] = field(default_factory=list)

    engine_name: str | None = None

    processing_time: float = 0.0

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        if self.document is None:
            return ""

        return self.document.text