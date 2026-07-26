"""Backward-compatible provider exports.

The canonical provider implementation lives in
``src.ai.extraction``.

This module preserves imports such as:

    from src.providers import ProviderFactory, ProviderError
"""

from .base_provider import BaseProvider
from .mock_provider import MockProvider
from .openai_provider import OpenAIProvider
from .provider_factory import ProviderFactory

from .provider_models import (
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
    ProviderUsage,
)

from .exceptions import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderContentPolicyError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    UnsupportedProviderError,
)


__all__ = [
    "BaseProvider",
    "MockProvider",
    "OpenAIProvider",
    "ProviderFactory",
    "ProviderMessage",
    "ProviderRequest",
    "ProviderResponse",
    "ProviderUsage",
    "ProviderError",
    "ProviderAuthenticationError",
    "ProviderConfigurationError",
    "ProviderConnectionError",
    "ProviderContentPolicyError",
    "ProviderRateLimitError",
    "ProviderResponseError",
    "ProviderTimeoutError",
    "UnsupportedProviderError",
]