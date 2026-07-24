from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from src.config.settings import (  # noqa: E402
    ConfigurationError,
    get_settings,
)


def mask_secret(secret: str) -> str:
    """
    Return a safe representation of a secret.
    """

    if len(secret) <= 8:
        return "*" * len(secret)

    return (
        secret[:4]
        + "*" * (len(secret) - 8)
        + secret[-4:]
    )


def main() -> None:
    print("=" * 70)
    print("AI SETTINGS TEST")
    print("=" * 70)

    try:
        settings = get_settings()

    except ConfigurationError as error:
        print(f"Status              : failed")
        print(f"Reason              : {error}")
        raise SystemExit(1) from error

    print(
        f"AI provider         : "
        f"{settings.ai_provider}"
    )
    print(
        f"OpenAI model        : "
        f"{settings.openai_model}"
    )
    print(
        f"API key             : "
        f"{mask_secret(settings.openai_api_key)}"
    )
    print(
        f"Max output tokens   : "
        f"{settings.ai_max_output_tokens}"
    )
    print(
        f"Request timeout     : "
        f"{settings.ai_request_timeout}"
    )
    print(
        f"Maximum retries     : "
        f"{settings.ai_max_retries}"
    )
    print("Status              : success")


if __name__ == "__main__":
    main()