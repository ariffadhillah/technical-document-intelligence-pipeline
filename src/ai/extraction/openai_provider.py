from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from src.ai.extraction.base_provider import BaseProvider
from src.ai.extraction.exceptions import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from src.ai.extraction.provider_models import (
    ProviderRequest,
    ProviderResponse,
    ProviderUsage,
)


class OpenAIProvider(BaseProvider):
    """
    OpenAI implementation of the provider interface.

    The provider translates the canonical ProviderRequest into an
    OpenAI Responses API request and converts the result back into
    ProviderResponse.

    It does not know the technical document schema, renderer,
    validator, database, or pipeline implementation.
    """

    DEFAULT_PROVIDER_NAME = "openai"
    DEFAULT_MODEL = "gpt-5.6-luna"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        default_model: str | None = None,
        max_retries: int = 2,
    ) -> None:
        super().__init__(
            provider_name=self.DEFAULT_PROVIDER_NAME
        )

        resolved_api_key = (
            api_key
            or os.getenv("OPENAI_API_KEY")
        )

        if not resolved_api_key:
            raise ProviderConfigurationError(
                (
                    "OPENAI_API_KEY is not configured. "
                    "Add it to the environment or .env file."
                ),
                provider=self.provider_name,
            )

        if max_retries < 0:
            raise ProviderConfigurationError(
                "max_retries cannot be negative.",
                provider=self.provider_name,
            )

        self.default_model = (
            default_model
            or os.getenv("OPENAI_MODEL")
            or self.DEFAULT_MODEL
        ).strip()

        if not self.default_model:
            raise ProviderConfigurationError(
                "OpenAI default model cannot be empty.",
                provider=self.provider_name,
            )

        self.client = OpenAI(
            api_key=resolved_api_key,
            max_retries=max_retries,
        )

    def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        self.validate_request(request)

        model = (
            request.model.strip()
            if request.model.strip()
            else self.default_model
        )

        started_at = datetime.now(
            timezone.utc
        ).isoformat()

        timer_started = perf_counter()

        try:
            response = self.client.responses.create(
                model=model,
                input=[
                    {
                        "role": message.role,
                        "content": message.content,
                    }
                    for message in request.messages
                ],
                max_output_tokens=(
                    request.max_output_tokens
                ),
                text=self._build_text_configuration(
                    request
                ),
            )

        except AuthenticationError as error:
            raise ProviderAuthenticationError(
                "OpenAI authentication failed.",
                provider=self.provider_name,
                details=self._error_details(error),
            ) from error

        except RateLimitError as error:
            raise ProviderRateLimitError(
                "OpenAI rate limit was reached.",
                provider=self.provider_name,
                details=self._error_details(error),
            ) from error

        except APITimeoutError as error:
            raise ProviderTimeoutError(
                "OpenAI request timed out.",
                provider=self.provider_name,
                details=self._error_details(error),
            ) from error

        except APIConnectionError as error:
            raise ProviderConnectionError(
                "Unable to connect to OpenAI.",
                provider=self.provider_name,
                details=self._error_details(error),
            ) from error

        except APIStatusError as error:
            raise ProviderResponseError(
                (
                    "OpenAI returned an API error "
                    f"with status {error.status_code}."
                ),
                provider=self.provider_name,
                details=self._error_details(error),
            ) from error

        except Exception as error:
            raise ProviderResponseError(
                (
                    "Unexpected OpenAI provider error: "
                    f"{error}"
                ),
                provider=self.provider_name,
                details={
                    "error_type": (
                        error.__class__.__name__
                    ),
                },
            ) from error

        duration_seconds = round(
            perf_counter() - timer_started,
            6,
        )

        finished_at = datetime.now(
            timezone.utc
        ).isoformat()

        raw_text = (
            response.output_text or ""
        ).strip()

        if not raw_text:
            raise ProviderResponseError(
                "OpenAI returned an empty text response.",
                provider=self.provider_name,
                details={
                    "request_id": getattr(
                        response,
                        "id",
                        None,
                    ),
                    "status": getattr(
                        response,
                        "status",
                        None,
                    ),
                },
            )

        if request.response_format in {
            "json",
            "json_schema",
        }:
            try:
                parsed_response = json.loads(
                    raw_text
                )

            except json.JSONDecodeError as error:
                raise ProviderResponseError(
                    (
                        "OpenAI returned invalid JSON at "
                        f"line {error.lineno}, "
                        f"column {error.colno}: "
                        f"{error.msg}"
                    ),
                    provider=self.provider_name,
                    details={
                        "request_id": getattr(
                            response,
                            "id",
                            None,
                        ),
                    },
                ) from error

        else:
            parsed_response = {
                "text": raw_text,
            }

        usage = self._build_usage(response)

        return ProviderResponse(
            provider=self.provider_name,
            model=getattr(
                response,
                "model",
                model,
            ),
            raw_text=raw_text,
            request_id=getattr(
                response,
                "id",
                None,
            ),
            finish_reason=self._finish_reason(
                response
            ),
            usage=usage,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
            raw_response=parsed_response,
            metadata={
                "api": "responses",
                "response_status": getattr(
                    response,
                    "status",
                    None,
                ),
                "response_format": (
                    request.response_format
                ),
                "external_request_performed": True,
            },
        )

    def health_check(self) -> dict[str, Any]:
        """
        Configuration-level health check.

        This does not consume API tokens.
        """

        return {
            "provider": self.provider_name,
            "status": "configured",
            "default_model": self.default_model,
            "external_service_required": True,
            "api_key_configured": True,
        }

    @staticmethod
    def _build_text_configuration(
        request: ProviderRequest,
    ) -> dict[str, Any] | None:
        if request.response_format == "text":
            return None

        if request.response_format == "json":
            return {
                "format": {
                    "type": "json_object",
                }
            }

        if request.response_format == "json_schema":
            if not request.json_schema:
                raise ProviderConfigurationError(
                    (
                        "json_schema is required when "
                        "response_format is json_schema."
                    ),
                    provider="openai",
                )

            return {
                "format": {
                    "type": "json_schema",
                    "name": (
                        request.metadata.get(
                            "prompt_name",
                            "structured_response",
                        )
                    ),
                    "strict": True,
                    "schema": request.json_schema,
                }
            }

        raise ProviderConfigurationError(
            (
                "Unsupported response format for "
                f"OpenAI: {request.response_format}"
            ),
            provider="openai",
        )

    @staticmethod
    def _build_usage(
        response: Any,
    ) -> ProviderUsage:
        response_usage = getattr(
            response,
            "usage",
            None,
        )

        if response_usage is None:
            return ProviderUsage(
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cached_input_tokens=0,
                reasoning_tokens=0,
            )

        input_tokens = int(
            getattr(
                response_usage,
                "input_tokens",
                0,
            )
            or 0
        )

        output_tokens = int(
            getattr(
                response_usage,
                "output_tokens",
                0,
            )
            or 0
        )

        total_tokens = int(
            getattr(
                response_usage,
                "total_tokens",
                input_tokens + output_tokens,
            )
            or input_tokens + output_tokens
        )

        input_details = getattr(
            response_usage,
            "input_tokens_details",
            None,
        )

        output_details = getattr(
            response_usage,
            "output_tokens_details",
            None,
        )

        cached_input_tokens = int(
            getattr(
                input_details,
                "cached_tokens",
                0,
            )
            or 0
        )

        reasoning_tokens = int(
            getattr(
                output_details,
                "reasoning_tokens",
                0,
            )
            or 0
        )

        return ProviderUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cached_input_tokens=(
                cached_input_tokens
            ),
            reasoning_tokens=reasoning_tokens,
        )

    @staticmethod
    def _finish_reason(
        response: Any,
    ) -> str | None:
        status = getattr(
            response,
            "status",
            None,
        )

        incomplete_details = getattr(
            response,
            "incomplete_details",
            None,
        )

        reason = getattr(
            incomplete_details,
            "reason",
            None,
        )

        if reason:
            return str(reason)

        if status == "completed":
            return "stop"

        return str(status) if status else None

    @staticmethod
    def _error_details(
        error: Exception,
    ) -> dict[str, Any]:
        details: dict[str, Any] = {
            "error_type": (
                error.__class__.__name__
            ),
            "message": str(error),
        }

        status_code = getattr(
            error,
            "status_code",
            None,
        )

        request_id = getattr(
            error,
            "request_id",
            None,
        )

        if status_code is not None:
            details["status_code"] = status_code

        if request_id:
            details["request_id"] = request_id

        return details