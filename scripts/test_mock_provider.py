from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.providers import (
    ProviderFactory,
    ProviderMessage,
    ProviderRequest,
)


DEFAULT_RESPONSE_FILE = (
    PROJECT_ROOT
    / "data"
    / "samples"
    / "thread_6260_structured_sample.json"
)


def main() -> int:
    print("=" * 72)
    print("MOCK PROVIDER AND FACTORY TEST")
    print("=" * 72)

    provider = ProviderFactory.create(
        "mock",
        response_file=DEFAULT_RESPONSE_FILE,
    )

    request = ProviderRequest(
        messages=(
            ProviderMessage(
                role="system",
                content=(
                    "You are a technical "
                    "documentation analyst."
                ),
            ),
            ProviderMessage(
                role="user",
                content=(
                    "Return a structured technical "
                    "knowledge document."
                ),
            ),
        ),
        model="mock-technical-extraction-v1",
        temperature=0.0,
        max_output_tokens=8000,
        timeout_seconds=30,
        response_format="json_schema",
        json_schema={
            "type": "object",
        },
        metadata={
            "document_id": "thread_6260",
            "test_mode": True,
        },
    )

    response = provider.generate(request)

    health = provider.health_check()

    print(
        f"Available providers : "
        f"{ProviderFactory.available_providers()}"
    )
    print(
        f"Provider            : "
        f"{response.provider}"
    )
    print(
        f"Model               : "
        f"{response.model}"
    )
    print(
        f"Finish reason       : "
        f"{response.finish_reason}"
    )
    print(
        f"Input tokens        : "
        f"{response.usage.input_tokens}"
    )
    print(
        f"Output tokens       : "
        f"{response.usage.output_tokens}"
    )
    print(
        f"Total tokens        : "
        f"{response.usage.total_tokens}"
    )
    print(
        f"Duration            : "
        f"{response.duration_seconds} seconds"
    )
    print(
        f"Health status       : "
        f"{health['status']}"
    )
    print(
        f"External API called : "
        f"{response.metadata['external_request_performed']}"
    )

    print()
    print(
        "[OK] Mock provider and provider "
        "factory are working"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())