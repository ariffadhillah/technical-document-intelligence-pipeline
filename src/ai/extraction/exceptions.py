from __future__ import annotations

from typing import Any


class ProviderError(RuntimeError):
    """
    Base exception for all provider-related failures.
    """

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        status_code: int | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)

        self.provider = provider
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "provider": self.provider,
            "status_code": self.status_code,
            "retryable": self.retryable,
            "details": self.details,
        }


class ProviderConfigurationError(ProviderError):
    """
    Raised when a provider is incorrectly configured.
    """


class ProviderAuthenticationError(ProviderError):
    """
    Raised when API authentication fails.
    """


class ProviderRateLimitError(ProviderError):
    """
    Raised when the provider rejects a request because of
    rate or quota limits.
    """

    def __init__(
        self,
        message: str,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)


class ProviderTimeoutError(ProviderError):
    """
    Raised when a provider request exceeds its timeout.
    """

    def __init__(
        self,
        message: str,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)


class ProviderConnectionError(ProviderError):
    """
    Raised when the provider cannot be reached.
    """

    def __init__(
        self,
        message: str,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)


class ProviderResponseError(ProviderError):
    """
    Raised when the provider returns an unusable or malformed
    response.
    """


class ProviderContentPolicyError(ProviderError):
    """
    Raised when the provider rejects content under its policy.
    """


class UnsupportedProviderError(ProviderConfigurationError):
    """
    Raised when an unknown provider name is requested.
    """