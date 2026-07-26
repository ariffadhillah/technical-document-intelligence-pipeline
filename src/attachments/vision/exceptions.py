from __future__ import annotations


class VisionError(Exception):
    """
    Base exception for Vision Intelligence.
    """


class VisionConfigurationError(VisionError):
    """
    Raised when a Vision provider is incorrectly configured.
    """


class VisionProcessingError(VisionError):
    """
    Raised when a Vision provider fails to process a page.
    """


class VisionProviderNotFoundError(VisionError):
    """
    Raised when a requested Vision provider is not registered.
    """


class VisionCacheError(VisionError):
    """
    Raised when a Vision cache operation fails.
    """


class VisionRoutingError(VisionError):
    """
    Raised when the Vision router cannot create a decision.
    """