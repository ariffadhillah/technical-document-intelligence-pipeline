from src.providers.base_provider import BaseProvider
from src.providers.exceptions import (
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
from src.providers.mock_provider import MockProvider
from src.providers.provider_factory import (
    ProviderFactory,
)
from src.providers.provider_models import (
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
    ProviderUsage,
)


def _register_builtin_providers() -> None:
    if not ProviderFactory.is_registered("mock"):
        ProviderFactory.register(
            "mock",
            MockProvider,
        )


_register_builtin_providers()


__all__ = [
    "BaseProvider",
    "MockProvider",
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