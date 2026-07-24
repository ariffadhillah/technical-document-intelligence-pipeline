from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.settings import get_settings
from src.providers.openai_provider import OpenAIProvider


def main():

    print("=" * 70)
    print("OPENAI CONNECTION TEST")
    print("=" * 70)

    settings = get_settings()

    provider = OpenAIProvider(settings)

    result = provider.health_check()

    print("Provider :", settings.ai_provider)
    print("Model    :", settings.openai_model)
    print("Reply    :", result)
    print("Status   : success")


if __name__ == "__main__":
    main()