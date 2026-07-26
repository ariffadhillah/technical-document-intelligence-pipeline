from __future__ import annotations

from collections.abc import Callable

from .base import BaseOCREngine
from .exceptions import OCREngineNotFoundError


OCREngineFactory = Callable[..., BaseOCREngine]


class OCRRegistry:
    """
    Registry for OCR engine factories.
    """

    def __init__(self) -> None:
        self._engines: dict[
            str,
            OCREngineFactory,
        ] = {}

    def register(
        self,
        name: str,
        factory: OCREngineFactory,
        *,
        replace: bool = False,
    ) -> None:

        normalized_name = self._normalize_name(name)

        if (
            normalized_name in self._engines
            and not replace
        ):
            raise ValueError(
                f"OCR engine already registered: "
                f"{normalized_name}"
            )

        self._engines[normalized_name] = factory

    def unregister(
        self,
        name: str,
    ) -> None:

        normalized_name = self._normalize_name(name)

        self._engines.pop(
            normalized_name,
            None,
        )

    def create(
        self,
        name: str,
        **kwargs,
    ) -> BaseOCREngine:

        normalized_name = self._normalize_name(name)

        factory = self._engines.get(
            normalized_name
        )

        if factory is None:
            available = ", ".join(
                self.available_engines()
            )

            raise OCREngineNotFoundError(
                f"OCR engine '{normalized_name}' "
                f"is not registered. "
                f"Available engines: {available or 'none'}"
            )

        return factory(**kwargs)

    def contains(
        self,
        name: str,
    ) -> bool:

        return (
            self._normalize_name(name)
            in self._engines
        )

    def available_engines(
        self,
    ) -> list[str]:

        return sorted(self._engines.keys())

    @staticmethod
    def _normalize_name(
        name: str,
    ) -> str:

        normalized = name.strip().lower()

        if not normalized:
            raise ValueError(
                "OCR engine name cannot be empty."
            )

        return normalized


ocr_registry = OCRRegistry()