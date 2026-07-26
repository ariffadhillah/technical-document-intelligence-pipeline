from __future__ import annotations


class OCRError(Exception):
    """
    Base exception for all OCR-related errors.
    """


class OCREngineNotFoundError(OCRError):
    """
    Raised when an OCR engine is not registered.
    """


class OCRProcessingError(OCRError):
    """
    Raised when an OCR engine fails to process an image.
    """


class OCRConfigurationError(OCRError):
    """
    Raised when the OCR engine configuration is invalid.
    """


class OCRCacheError(OCRError):
    """
    Raised when OCR cache operations fail.
    """


class OCRLanguageError(OCRError):
    """
    Raised when OCR language configuration or detection fails.
    """