from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


load_dotenv(
    PROJECT_ROOT / ".env"
)


from src.providers import ProviderFactory


def main() -> int:
    print("=" * 72)
    print("OPENAI PROVIDER CONFIGURATION TEST")
    print("=" * 72)

    if not os.getenv("OPENAI_API_KEY"):
        print("[FAILED]")
        print(
            "OPENAI_API_KEY was not found in .env."
        )
        return 1

    provider = ProviderFactory.create(
        "openai"
    )

    health = provider.health_check()

    print(
        f"Available providers : "
        f"{ProviderFactory.available_providers()}"
    )
    print(
        f"Provider            : "
        f"{health['provider']}"
    )
    print(
        f"Status              : "
        f"{health['status']}"
    )
    print(
        f"Default model       : "
        f"{health['default_model']}"
    )
    print(
        f"API key configured  : "
        f"{health['api_key_configured']}"
    )
    print()
    print(
        "[OK] OpenAI provider configuration "
        "is valid"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())