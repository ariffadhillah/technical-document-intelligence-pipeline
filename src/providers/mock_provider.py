from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from src.providers.base_provider import BaseProvider
from src.providers.exceptions import (
    ProviderConfigurationError,
    ProviderResponseError,
)
from src.providers.provider_models import (
    ProviderRequest,
    ProviderResponse,
    ProviderUsage,
)


class MockProvider(BaseProvider):
    """
    Offline provider implementation for tests and local development.

    The provider reads a predefined response from a JSON or text file
    and returns it through the canonical ProviderResponse interface.

    No external API request is performed.
    """

    DEFAULT_PROVIDER_NAME = "mock"
    DEFAULT_MODEL_NAME = "mock-technical-extraction-v1"

    def __init__(
        self,
        response_file: Path,
        *,
        simulated_input_tokens: int = 0,
        simulated_output_tokens: int = 0,
        simulated_finish_reason: str = "stop",
    ) -> None:
        super().__init__(
            provider_name=self.DEFAULT_PROVIDER_NAME
        )

        self.response_file = response_file.resolve()
        self.simulated_input_tokens = simulated_input_tokens
        self.simulated_output_tokens = simulated_output_tokens
        self.simulated_finish_reason = (
            simulated_finish_reason
        )

        self._validate_configuration()

    def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        self.validate_request(request)

        started_at = datetime.now(
            timezone.utc
        ).isoformat()

        started_timer = perf_counter()

        raw_text = self._load_response_text()

        parsed_response = self._parse_response_if_required(
            raw_text=raw_text,
            request=request,
        )

        finished_timer = perf_counter()

        finished_at = datetime.now(
            timezone.utc
        ).isoformat()

        duration_seconds = round(
            finished_timer - started_timer,
            6,
        )

        input_tokens = (
            self.simulated_input_tokens
            or self._estimate_tokens(
                "\n".join(
                    message.content
                    for message in request.messages
                )
            )
        )

        output_tokens = (
            self.simulated_output_tokens
            or self._estimate_tokens(raw_text)
        )

        usage = ProviderUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=(
                input_tokens + output_tokens
            ),
            cached_input_tokens=0,
            reasoning_tokens=0,
        )

        model_name = (
            request.model.strip()
            or self.DEFAULT_MODEL_NAME
        )

        return ProviderResponse(
            provider=self.provider_name,
            model=model_name,
            raw_text=raw_text,
            request_id=None,
            finish_reason=self.simulated_finish_reason,
            usage=usage,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
            raw_response=parsed_response,
            metadata={
                "mock_mode": True,
                "response_file": str(
                    self.response_file
                ),
                "external_request_performed": False,
            },
        )

    def health_check(self) -> dict[str, Any]:
        exists = self.response_file.exists()

        return {
            "provider": self.provider_name,
            "status": (
                "available"
                if exists
                else "unavailable"
            ),
            "response_file": str(
                self.response_file
            ),
            "response_file_exists": exists,
            "external_service_required": False,
        }

    def _validate_configuration(self) -> None:
        if not self.response_file.exists():
            raise ProviderConfigurationError(
                (
                    "Mock response file was not found: "
                    f"{self.response_file}"
                ),
                provider=self.provider_name,
                details={
                    "response_file": str(
                        self.response_file
                    ),
                },
            )

        if not self.response_file.is_file():
            raise ProviderConfigurationError(
                (
                    "Mock response path is not a file: "
                    f"{self.response_file}"
                ),
                provider=self.provider_name,
            )

        if self.simulated_input_tokens < 0:
            raise ProviderConfigurationError(
                (
                    "simulated_input_tokens cannot "
                    "be negative."
                ),
                provider=self.provider_name,
            )

        if self.simulated_output_tokens < 0:
            raise ProviderConfigurationError(
                (
                    "simulated_output_tokens cannot "
                    "be negative."
                ),
                provider=self.provider_name,
            )

    def _load_response_text(self) -> str:
        try:
            raw_text = self.response_file.read_text(
                encoding="utf-8"
            )

        except OSError as error:
            raise ProviderResponseError(
                (
                    "Unable to read mock response file: "
                    f"{self.response_file}"
                ),
                provider=self.provider_name,
                details={
                    "original_error": str(error),
                },
            ) from error

        if not raw_text.strip():
            raise ProviderResponseError(
                "Mock response file is empty.",
                provider=self.provider_name,
                details={
                    "response_file": str(
                        self.response_file
                    ),
                },
            )

        return raw_text.strip()

    def _parse_response_if_required(
        self,
        raw_text: str,
        request: ProviderRequest,
    ) -> dict[str, Any] | None:
        if request.response_format == "text":
            return {
                "text": raw_text,
            }

        try:
            payload = json.loads(raw_text)

        except json.JSONDecodeError as error:
            raise ProviderResponseError(
                (
                    "Mock provider expected a JSON "
                    "response but the response file "
                    "contains invalid JSON. "
                    f"Line {error.lineno}, "
                    f"column {error.colno}: "
                    f"{error.msg}"
                ),
                provider=self.provider_name,
                details={
                    "response_file": str(
                        self.response_file
                    ),
                    "response_format": (
                        request.response_format
                    ),
                },
            ) from error

        if not isinstance(payload, dict):
            raise ProviderResponseError(
                (
                    "Mock provider JSON response "
                    "must have an object as its root."
                ),
                provider=self.provider_name,
                details={
                    "response_file": str(
                        self.response_file
                    ),
                },
            )

        return payload

    @staticmethod
    def _estimate_tokens(
        text: str,
    ) -> int:
        """
        Lightweight offline estimate.

        This is only for mock metadata and must not be treated
        as official provider billing data.
        """

        if not text:
            return 0

        return max(
            1,
            round(len(text) / 4),
        )