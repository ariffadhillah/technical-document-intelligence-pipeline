from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.providers import (
    BaseProvider,
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
    ProviderUsage,
)


class ExampleProvider(BaseProvider):
    """
    Temporary provider used only to verify the base interface.
    """

    def __init__(self) -> None:
        super().__init__(
            provider_name="example"
        )

    def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        self.validate_request(request)

        return ProviderResponse(
            provider=self.provider_name,
            model=request.model,
            raw_text=json.dumps(
                {
                    "status": "success",
                    "message": (
                        "Provider foundation is working."
                    ),
                }
            ),
            finish_reason="stop",
            usage=ProviderUsage(
                input_tokens=20,
                output_tokens=10,
                total_tokens=30,
            ),
            duration_seconds=0.01,
            metadata={
                "test_mode": True,
            },
        )


def main() -> int:
    print("=" * 72)
    print("PROVIDER FOUNDATION TEST")
    print("=" * 72)

    messages = (
        ProviderMessage(
            role="system",
            content=(
                "You are a technical documentation "
                "analyst."
            ),
        ),
        ProviderMessage(
            role="user",
            content=(
                "Extract structured technical knowledge."
            ),
        ),
    )

    request = ProviderRequest(
        messages=messages,
        model="example-model",
        temperature=0.0,
        max_output_tokens=1000,
        timeout_seconds=30,
        response_format="json_object",
        metadata={
            "document_id": "thread_6260",
            "prompt_version": "v1",
        },
    )

    provider = ExampleProvider()

    response = provider.generate(request)

    print(f"Provider           : {response.provider}")
    print(f"Model              : {response.model}")
    print(f"Finish reason      : {response.finish_reason}")
    print(
        "Input tokens       : "
        f"{response.usage.input_tokens}"
    )
    print(
        "Output tokens      : "
        f"{response.usage.output_tokens}"
    )
    print(
        "Total tokens       : "
        f"{response.usage.total_tokens}"
    )
    print(
        "Duration           : "
        f"{response.duration_seconds} seconds"
    )
    print(f"Raw text           : {response.raw_text}")

    health = provider.health_check()

    print()
    print(
        "Health status      : "
        f"{health['status']}"
    )

    print()
    print("[OK] Provider foundation is working")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())