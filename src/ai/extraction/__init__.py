"""Provider-agnostic structured extraction services."""

from src.ai.extraction.base_provider import BaseProvider
from src.ai.extraction.exceptions import (
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
from src.ai.extraction.mock_provider import MockProvider
from src.ai.extraction.openai_provider import OpenAIProvider
from src.ai.extraction.provider_factory import ProviderFactory
from src.ai.extraction.provider_models import (
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
    ProviderUsage,
)


def _register_builtin_providers() -> None:
    if not ProviderFactory.is_registered("mock"):
        ProviderFactory.register("mock", MockProvider)

    if not ProviderFactory.is_registered("openai"):
        ProviderFactory.register("openai", OpenAIProvider)


_register_builtin_providers()


__all__ = [
    "BaseProvider",
    "MockProvider",
    "OpenAIProvider",
    "ProviderAuthenticationError",
    "ProviderConfigurationError",
    "ProviderConnectionError",
    "ProviderContentPolicyError",
    "ProviderError",
    "ProviderFactory",
    "ProviderMessage",
    "ProviderRateLimitError",
    "ProviderRequest",
    "ProviderResponse",
    "ProviderResponseError",
    "ProviderTimeoutError",
    "ProviderUsage",
    "UnsupportedProviderError",
]
