from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


MessageRole = Literal[
    "system",
    "user",
    "assistant",
]


@dataclass(frozen=True)
class ProviderMessage:
    """
    Provider-agnostic chat message.

    Every provider implementation is responsible for translating
    this representation into its own API format.
    """

    role: MessageRole
    content: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError(
                "ProviderMessage.content cannot be empty."
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "content": self.content,
        }


@dataclass(frozen=True)
class ProviderRequest:
    """
    Standard request accepted by every language-model provider.
    """

    messages: tuple[ProviderMessage, ...]

    model: str
    temperature: float = 0.0
    max_output_tokens: int | None = None
    timeout_seconds: float | None = None

    response_format: Literal[
        "text",
        "json_object",
        "json_schema",
    ] = "text"

    json_schema: dict[str, Any] | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError(
                "ProviderRequest.messages cannot be empty."
            )

        if not self.model.strip():
            raise ValueError(
                "ProviderRequest.model cannot be empty."
            )

        if not 0 <= self.temperature <= 2:
            raise ValueError(
                "ProviderRequest.temperature must be "
                "between 0 and 2."
            )

        if (
            self.max_output_tokens is not None
            and self.max_output_tokens <= 0
        ):
            raise ValueError(
                "ProviderRequest.max_output_tokens must "
                "be greater than zero."
            )

        if (
            self.timeout_seconds is not None
            and self.timeout_seconds <= 0
        ):
            raise ValueError(
                "ProviderRequest.timeout_seconds must "
                "be greater than zero."
            )

        if (
            self.response_format == "json_schema"
            and not self.json_schema
        ):
            raise ValueError(
                "json_schema is required when "
                "response_format='json_schema'."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "messages": [
                message.to_dict()
                for message in self.messages
            ],
            "model": self.model,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "timeout_seconds": self.timeout_seconds,
            "response_format": self.response_format,
            "json_schema": self.json_schema,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ProviderUsage:
    """
    Token usage returned by a provider.
    """

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None

    def __post_init__(self) -> None:
        numeric_fields = (
            self.input_tokens,
            self.output_tokens,
            self.total_tokens,
            self.cached_input_tokens,
            self.reasoning_tokens,
        )

        if any(
            value is not None and value < 0
            for value in numeric_fields
        ):
            raise ValueError(
                "Provider token usage cannot be negative."
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderResponse:
    """
    Standard response returned by every provider implementation.
    """

    provider: str
    model: str

    raw_text: str

    request_id: str | None = None
    finish_reason: str | None = None

    usage: ProviderUsage = field(
        default_factory=ProviderUsage
    )

    started_at: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )

    finished_at: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )

    duration_seconds: float | None = None

    raw_response: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError(
                "ProviderResponse.provider cannot be empty."
            )

        if not self.model.strip():
            raise ValueError(
                "ProviderResponse.model cannot be empty."
            )

        if not self.raw_text.strip():
            raise ValueError(
                "ProviderResponse.raw_text cannot be empty."
            )

        if (
            self.duration_seconds is not None
            and self.duration_seconds < 0
        ):
            raise ValueError(
                "ProviderResponse.duration_seconds "
                "cannot be negative."
            )

    def to_dict(
        self,
        include_raw_response: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "provider": self.provider,
            "model": self.model,
            "raw_text": self.raw_text,
            "request_id": self.request_id,
            "finish_reason": self.finish_reason,
            "usage": self.usage.to_dict(),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": self.duration_seconds,
            "raw_response": self.raw_response,
            "metadata": self.metadata,
        }

        if not include_raw_response:
            payload.pop("raw_response", None)

        return payload