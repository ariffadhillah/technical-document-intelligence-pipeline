from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.providers.base_provider import BaseProvider
from src.providers.exceptions import (
    ProviderConfigurationError,
    UnsupportedProviderError,
)


ProviderCreator = Callable[..., BaseProvider]


class ProviderFactory:
    """
    Registry-based factory for provider implementations.

    New providers can be registered without changing the pipeline
    that consumes BaseProvider.
    """

    _registry: dict[str, ProviderCreator] = {}

    @classmethod
    def register(
        cls,
        provider_name: str,
        creator: ProviderCreator,
        *,
        replace: bool = False,
    ) -> None:
        normalized_name = cls._normalize_name(
            provider_name
        )

        if (
            normalized_name in cls._registry
            and not replace
        ):
            raise ProviderConfigurationError(
                (
                    "Provider is already registered: "
                    f"{normalized_name}"
                ),
                provider=normalized_name,
            )

        if not callable(creator):
            raise ProviderConfigurationError(
                (
                    "Provider creator must be callable "
                    f"for provider '{normalized_name}'."
                ),
                provider=normalized_name,
            )

        cls._registry[normalized_name] = creator

    @classmethod
    def unregister(
        cls,
        provider_name: str,
    ) -> None:
        normalized_name = cls._normalize_name(
            provider_name
        )

        cls._registry.pop(
            normalized_name,
            None,
        )

    @classmethod
    def create(
        cls,
        provider_name: str,
        **configuration: Any,
    ) -> BaseProvider:
        normalized_name = cls._normalize_name(
            provider_name
        )

        creator = cls._registry.get(
            normalized_name
        )

        if creator is None:
            available = ", ".join(
                cls.available_providers()
            )

            raise UnsupportedProviderError(
                (
                    f"Unsupported provider: "
                    f"'{normalized_name}'. "
                    f"Available providers: "
                    f"{available or 'none'}."
                ),
                provider=normalized_name,
                details={
                    "available_providers": (
                        cls.available_providers()
                    ),
                },
            )

        try:
            provider = creator(
                **configuration
            )

        except ProviderConfigurationError:
            raise

        except Exception as error:
            raise ProviderConfigurationError(
                (
                    "Unable to initialize provider "
                    f"'{normalized_name}': {error}"
                ),
                provider=normalized_name,
                details={
                    "configuration_keys": sorted(
                        configuration.keys()
                    ),
                    "original_error_type": (
                        error.__class__.__name__
                    ),
                },
            ) from error

        if not isinstance(provider, BaseProvider):
            raise ProviderConfigurationError(
                (
                    "Provider factory creator did not "
                    "return a BaseProvider instance."
                ),
                provider=normalized_name,
                details={
                    "returned_type": (
                        provider.__class__.__name__
                    ),
                },
            )

        return provider

    @classmethod
    def available_providers(
        cls,
    ) -> list[str]:
        return sorted(
            cls._registry.keys()
        )

    @classmethod
    def is_registered(
        cls,
        provider_name: str,
    ) -> bool:
        normalized_name = cls._normalize_name(
            provider_name
        )

        return normalized_name in cls._registry

    @staticmethod
    def _normalize_name(
        provider_name: str,
    ) -> str:
        if not isinstance(provider_name, str):
            raise ProviderConfigurationError(
                "provider_name must be a string."
            )

        normalized_name = (
            provider_name.strip().lower()
        )

        if not normalized_name:
            raise ProviderConfigurationError(
                "provider_name cannot be empty."
            )

        return normalized_name