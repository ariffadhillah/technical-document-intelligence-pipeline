from __future__ import annotations

from collections.abc import Callable

from .base import BaseVisionEngine
from .exceptions import VisionProviderNotFoundError


VisionEngineFactory = Callable[..., BaseVisionEngine]


class VisionRegistry:
    """
    Registry containing Vision provider factories.
    """

    def __init__(self) -> None:
        self._providers: dict[
            str,
            VisionEngineFactory,
        ] = {}

    def register(
        self,
        name: str,
        factory: VisionEngineFactory,
        *,
        replace: bool = False,
    ) -> None:
        normalized = self._normalize_name(name)

        if normalized in self._providers and not replace:
            raise ValueError(
                f"Vision provider already registered: {normalized}"
            )

        self._providers[normalized] = factory

    def unregister(
        self,
        name: str,
    ) -> None:
        normalized = self._normalize_name(name)

        self._providers.pop(normalized, None)

    def create(
        self,
        name: str,
        **kwargs,
    ) -> BaseVisionEngine:
        normalized = self._normalize_name(name)

        factory = self._providers.get(normalized)

        if factory is None:
            available = ", ".join(
                self.available_providers()
            )

            raise VisionProviderNotFoundError(
                f"Vision provider '{normalized}' is not registered. "
                f"Available providers: {available or 'none'}"
            )

        return factory(**kwargs)

    def contains(
        self,
        name: str,
    ) -> bool:
        return self._normalize_name(name) in self._providers

    def available_providers(
        self,
    ) -> list[str]:
        return sorted(self._providers)

    @staticmethod
    def _normalize_name(
        name: str,
    ) -> str:
        normalized = name.strip().lower()

        if not normalized:
            raise ValueError(
                "Vision provider name cannot be empty."
            )

        return normalized


vision_registry = VisionRegistry()