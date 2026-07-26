from __future__ import annotations

from abc import ABC, abstractmethod

from .models import VisionRequest, VisionResponse


class BaseVisionEngine(ABC):
    """
    Base interface implemented by every Vision provider.

    Future implementations may include:

        OpenAI
        Gemini
        Claude
        Local vision-language models
    """

    provider_name: str = "base"

    model_name: str = "unknown"

    @abstractmethod
    def analyze_page(
        self,
        request: VisionRequest,
    ) -> VisionResponse:
        """
        Analyze one page and return normalized text.
        """

    def is_available(self) -> bool:
        """
        Return whether the provider is correctly configured.
        """

        return True

    def get_provider_name(self) -> str:
        return self.provider_name

    def get_model_name(self) -> str:
        return self.model_name