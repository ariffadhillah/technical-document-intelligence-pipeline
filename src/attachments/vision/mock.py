from __future__ import annotations

import time

from .base import BaseVisionEngine
from .models import VisionRequest, VisionResponse


class MockVisionEngine(BaseVisionEngine):
    """
    Deterministic Vision provider used for integration testing.

    This provider does not call an external API.
    """

    provider_name = "mock"
    model_name = "mock-vision-v1"

    def __init__(
        self,
        *,
        replacement_text: str | None = None,
        confidence: float = 0.95,
        simulated_delay: float = 0.0,
    ) -> None:
        self.replacement_text = replacement_text
        self.confidence = confidence
        self.simulated_delay = simulated_delay
        self.call_count = 0

    def analyze_page(
        self,
        request: VisionRequest,
    ) -> VisionResponse:
        started_at = time.perf_counter()

        self.call_count += 1

        if self.simulated_delay > 0:
            time.sleep(self.simulated_delay)

        original_text = (
            request.ocr_page.text.strip()
            if request.ocr_page is not None
            else ""
        )

        text = self.replacement_text or (
            f"[Mock Vision extraction for page "
            f"{request.page_number}]\n\n"
            f"{original_text or 'No readable OCR text was available.'}"
        )

        return VisionResponse(
            page_number=request.page_number,
            text=text,
            provider=self.provider_name,
            model=self.model_name,
            confidence=self.confidence,
            processing_time=(
                time.perf_counter() - started_at
            ),
            input_tokens=None,
            output_tokens=None,
            estimated_cost=0.0,
            metadata={
                "mock": True,
                "prompt_version": request.prompt_version,
            },
        )