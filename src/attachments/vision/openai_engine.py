from __future__ import annotations

import base64
import logging
import os
import time
from typing import Any

import cv2
import numpy as np

from .base import BaseVisionEngine
from .exceptions import (
    VisionConfigurationError,
    VisionProcessingError,
)
from .models import (
    VisionRequest,
    VisionResponse,
)

logger = logging.getLogger(__name__)


class OpenAIVisionEngine(BaseVisionEngine):
    """
    OpenAI Vision provider using the Responses API.

    The engine accepts an OpenCV image, encodes it as
    JPEG/Base64, sends it to OpenAI, and normalizes the
    result into VisionResponse.
    """

    provider_name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        detail: str | None = None,
        max_output_tokens: int | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        jpeg_quality: int = 92,
        confidence: float = 0.90,
        client: Any | None = None,
    ) -> None:
        self.api_key = (
            api_key
            or os.getenv("OPENAI_API_KEY")
        )

        self.model_name = (
            model
            or os.getenv(
                "OPENAI_MODEL",
                "gpt-4.1-mini",
            )
        )

        self.detail = (
            detail
            or os.getenv(
                "OPENAI_VISION_DETAIL",
                "high",
            )
        ).lower()

        self.max_output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else self._read_int_environment(
                "AI_MAX_OUTPUT_TOKENS",
                default=6000,
            )
        )

        self.timeout = (
            timeout
            if timeout is not None
            else self._read_float_environment(
                "AI_REQUEST_TIMEOUT",
                default=120.0,
            )
        )

        self.max_retries = (
            max_retries
            if max_retries is not None
            else self._read_int_environment(
                "AI_MAX_RETRIES",
                default=3,
            )
        )

        self.jpeg_quality = max(
            50,
            min(int(jpeg_quality), 100),
        )

        self.confidence = max(
            0.0,
            min(float(confidence), 1.0),
        )

        self._validate_configuration()

        if client is not None:
            self.client = client
        else:
            self.client = self._build_client()

        self.call_count = 0

    def analyze_page(
        self,
        request: VisionRequest,
    ) -> VisionResponse:
        """
        Analyze a page image using OpenAI Vision.
        """

        if request.image is None:
            raise VisionProcessingError(
                "OpenAI Vision received no image."
            )

        if request.image.size == 0:
            raise VisionProcessingError(
                "OpenAI Vision received an empty image."
            )

        if not request.prompt.strip():
            raise VisionProcessingError(
                "OpenAI Vision received an empty prompt."
            )

        started_at = time.perf_counter()

        try:
            image_data_url = (
                self._encode_image_as_data_url(
                    request.image
                )
            )

            self.call_count += 1

            response = self.client.responses.create(
                model=self.model_name,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": request.prompt,
                            },
                            {
                                "type": "input_image",
                                "image_url": (
                                    image_data_url
                                ),
                                "detail": self.detail,
                            },
                        ],
                    }
                ],
                max_output_tokens=(
                    self.max_output_tokens
                ),
            )

        except Exception as exc:
            raise VisionProcessingError(
                "OpenAI Vision request failed for "
                f"page {request.page_number}: {exc}"
            ) from exc

        text = self._extract_output_text(
            response
        )

        if not text:
            raise VisionProcessingError(
                "OpenAI returned no readable text for "
                f"page {request.page_number}."
            )

        input_tokens, output_tokens = (
            self._extract_usage(response)
        )

        processing_time = (
            time.perf_counter() - started_at
        )

        logger.info(
            "OpenAI Vision completed page %s: "
            "model=%s input_tokens=%s "
            "output_tokens=%s time=%.2fs",
            request.page_number,
            self.model_name,
            input_tokens,
            output_tokens,
            processing_time,
        )

        return VisionResponse(
            page_number=request.page_number,
            text=text,
            provider=self.provider_name,
            model=self.model_name,
            confidence=self.confidence,
            processing_time=processing_time,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=None,
            metadata={
                "response_id": getattr(
                    response,
                    "id",
                    None,
                ),
                "prompt_version": (
                    request.prompt_version
                ),
                "detail": self.detail,
                "source_path": (
                    str(request.source_path)
                    if request.source_path
                    else None
                ),
                "request_metadata": dict(
                    request.metadata
                ),
            },
        )

    def is_available(self) -> bool:
        return bool(
            self.api_key
            and self.client is not None
        )

    def _build_client(self) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise VisionConfigurationError(
                "The openai package is not installed. "
                "Install it using: pip install openai"
            ) from exc

        try:
            return OpenAI(
                api_key=self.api_key,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
        except Exception as exc:
            raise VisionConfigurationError(
                "Unable to initialize the OpenAI "
                f"client: {exc}"
            ) from exc

    def _validate_configuration(self) -> None:
        if not self.api_key:
            raise VisionConfigurationError(
                "OPENAI_API_KEY is not configured."
            )

        if not self.model_name:
            raise VisionConfigurationError(
                "OPENAI_MODEL is not configured."
            )

        allowed_details = {
            "low",
            "high",
            "original",
            "auto",
        }

        if self.detail not in allowed_details:
            raise VisionConfigurationError(
                "OPENAI_VISION_DETAIL must be one of: "
                "low, high, original, auto."
            )

        if self.max_output_tokens <= 0:
            raise VisionConfigurationError(
                "AI_MAX_OUTPUT_TOKENS must be "
                "greater than zero."
            )

        if self.timeout <= 0:
            raise VisionConfigurationError(
                "AI_REQUEST_TIMEOUT must be "
                "greater than zero."
            )

        if self.max_retries < 0:
            raise VisionConfigurationError(
                "AI_MAX_RETRIES cannot be negative."
            )

    def _encode_image_as_data_url(
        self,
        image: np.ndarray,
    ) -> str:
        """
        Encode an OpenCV BGR image as a JPEG data URL.
        """

        encode_parameters = [
            cv2.IMWRITE_JPEG_QUALITY,
            self.jpeg_quality,
        ]

        success, encoded_image = cv2.imencode(
            ".jpg",
            image,
            encode_parameters,
        )

        if not success:
            raise VisionProcessingError(
                "Unable to encode page image "
                "as JPEG."
            )

        base64_image = base64.b64encode(
            encoded_image.tobytes()
        ).decode("utf-8")

        return (
            "data:image/jpeg;base64,"
            f"{base64_image}"
        )

    @staticmethod
    def _extract_output_text(
        response: Any,
    ) -> str:
        """
        Read output text from a Responses API result.
        """

        output_text = getattr(
            response,
            "output_text",
            None,
        )

        if isinstance(output_text, str):
            cleaned = output_text.strip()

            if cleaned:
                return cleaned

        text_parts: list[str] = []

        for output_item in (
            getattr(response, "output", None)
            or []
        ):
            content_items = getattr(
                output_item,
                "content",
                None,
            ) or []

            for content_item in content_items:
                text = getattr(
                    content_item,
                    "text",
                    None,
                )

                if isinstance(text, str):
                    cleaned = text.strip()

                    if cleaned:
                        text_parts.append(cleaned)

        return "\n\n".join(text_parts).strip()

    @staticmethod
    def _extract_usage(
        response: Any,
    ) -> tuple[int | None, int | None]:
        usage = getattr(
            response,
            "usage",
            None,
        )

        if usage is None:
            return None, None

        input_tokens = getattr(
            usage,
            "input_tokens",
            None,
        )

        output_tokens = getattr(
            usage,
            "output_tokens",
            None,
        )

        return input_tokens, output_tokens

    @staticmethod
    def _read_int_environment(
        name: str,
        *,
        default: int,
    ) -> int:
        value = os.getenv(name)

        if value is None:
            return default

        try:
            return int(value)
        except ValueError as exc:
            raise VisionConfigurationError(
                f"{name} must be an integer."
            ) from exc

    @staticmethod
    def _read_float_environment(
        name: str,
        *,
        default: float,
    ) -> float:
        value = os.getenv(name)

        if value is None:
            return default

        try:
            return float(value)
        except ValueError as exc:
            raise VisionConfigurationError(
                f"{name} must be numeric."
            ) from exc