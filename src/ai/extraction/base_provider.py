from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.ai.extraction.provider_models import (
    ProviderRequest,
    ProviderResponse,
)


class BaseProvider(ABC):
    """
    Provider-agnostic interface for language-model services.

    Every concrete provider must implement the generate method
    and return the canonical ProviderResponse model.
    """

    provider_name: str

    def __init__(
        self,
        provider_name: str,
    ) -> None:
        cleaned_name = provider_name.strip().lower()

        if not cleaned_name:
            raise ValueError(
                "provider_name cannot be empty."
            )

        self.provider_name = cleaned_name

    @abstractmethod
    def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        """
        Send a request to the provider and return a normalized
        response.
        """

        raise NotImplementedError

    def validate_request(
        self,
        request: ProviderRequest,
    ) -> None:
        """
        Hook for provider-specific request validation.

        Concrete implementations may override this method.
        """

        if not isinstance(request, ProviderRequest):
            raise TypeError(
                "request must be an instance of "
                "ProviderRequest."
            )

    def health_check(self) -> dict[str, Any]:
        """
        Optional provider health information.

        Cloud providers may override this method to perform a
        lightweight connectivity or configuration check.
        """

        return {
            "provider": self.provider_name,
            "status": "available",
            "message": (
                "No provider-specific health check "
                "has been implemented."
            ),
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"provider_name={self.provider_name!r})"
        )