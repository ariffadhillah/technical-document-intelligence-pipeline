from __future__ import annotations

from .base import BaseOCREngine
from .cache import OCRCache
from .cleaner import OCRTextCleaner
from .confidence import (
    OCRConfidenceReport,
    OCRConfidenceScorer,
)
from .exceptions import (
    OCRCacheError,
    OCRConfigurationError,
    OCREngineNotFoundError,
    OCRError,
    OCRLanguageError,
    OCRProcessingError,
)
from .language import (
    LanguageDetectionResult,
    OCRLanguageDetector,
)
from .merger import OCRPageMerger
from .models import (
    BoundingBox,
    OCRDocument,
    OCRLine,
    OCRPage,
    OCRParagraph,
    OCRWord,
)
from .registry import OCRRegistry, ocr_registry
from .result import (
    OCRDocumentResult,
    OCRProcessingResult,
)
from .tesseract import TesseractOCREngine


if not ocr_registry.contains("tesseract"):
    ocr_registry.register(
        "tesseract",
        TesseractOCREngine,
    )


__all__ = [
    "BaseOCREngine",
    "BoundingBox",
    "LanguageDetectionResult",
    "OCRCache",
    "OCRCacheError",
    "OCRConfidenceReport",
    "OCRConfidenceScorer",
    "OCRConfigurationError",
    "OCRDocument",
    "OCRDocumentResult",
    "OCREngineNotFoundError",
    "OCRError",
    "OCRLanguageDetector",
    "OCRLanguageError",
    "OCRLine",
    "OCRPage",
    "OCRPageMerger",
    "OCRParagraph",
    "OCRProcessingError",
    "OCRProcessingResult",
    "OCRRegistry",
    "OCRTextCleaner",
    "OCRWord",
    "TesseractOCREngine",
    "ocr_registry",
]