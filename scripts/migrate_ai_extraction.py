from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OLD_PACKAGE = PROJECT_ROOT / "src" / "providers"
NEW_PACKAGE = PROJECT_ROOT / "src" / "ai" / "extraction"

FILES = (
    "base_provider.py",
    "exceptions.py",
    "mock_provider.py",
    "openai_provider.py",
    "provider_factory.py",
    "provider_models.py",
)

WRAPPERS = {
    "base_provider.py": "from src.ai.extraction.base_provider import *  # noqa: F401,F403\n",
    "exceptions.py": "from src.ai.extraction.exceptions import *  # noqa: F401,F403\n",
    "mock_provider.py": "from src.ai.extraction.mock_provider import *  # noqa: F401,F403\n",
    "openai_provider.py": "from src.ai.extraction.openai_provider import *  # noqa: F401,F403\n",
    "provider_factory.py": "from src.ai.extraction.provider_factory import *  # noqa: F401,F403\n",
    "provider_models.py": "from src.ai.extraction.provider_models import *  # noqa: F401,F403\n",
}

COMPAT_INIT = (
    '"""Backward-compatible imports for the extraction provider package."""\n\n'
    'from src.ai.extraction import *  # noqa: F401,F403\n'
)

AI_INIT = (
    '"""AI services for extraction, vision, validation, prompts, and cost tracking."""\n'
)

EXTRACTION_INIT = '''"""Provider-agnostic structured extraction services."""

from src.ai.extraction.base_provider import BaseProvider
from src.ai.extraction.exceptions import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderContentPolicyError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    UnsupportedProviderError,
)
from src.ai.extraction.mock_provider import MockProvider
from src.ai.extraction.openai_provider import OpenAIProvider
from src.ai.extraction.provider_factory import ProviderFactory
from src.ai.extraction.provider_models import (
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
    ProviderUsage,
)


def _register_builtin_providers() -> None:
    if not ProviderFactory.is_registered("mock"):
        ProviderFactory.register("mock", MockProvider)

    if not ProviderFactory.is_registered("openai"):
        ProviderFactory.register("openai", OpenAIProvider)


_register_builtin_providers()


__all__ = [
    "BaseProvider",
    "MockProvider",
    "OpenAIProvider",
    "ProviderAuthenticationError",
    "ProviderConfigurationError",
    "ProviderConnectionError",
    "ProviderContentPolicyError",
    "ProviderError",
    "ProviderFactory",
    "ProviderMessage",
    "ProviderRateLimitError",
    "ProviderRequest",
    "ProviderResponse",
    "ProviderResponseError",
    "ProviderTimeoutError",
    "ProviderUsage",
    "UnsupportedProviderError",
]
'''


def replace_imports(content: str) -> str:
    return content.replace(
        "from src.providers.",
        "from src.ai.extraction.",
    ).replace(
        "import src.providers.",
        "import src.ai.extraction.",
    )


def update_openai_default_model(content: str) -> str:
    for old_model in ("gpt-5.6-luna", "gpt-4o"):
        content = content.replace(
            f'DEFAULT_MODEL = "{{old_model}}"',
            'DEFAULT_MODEL = "gpt-4.1-mini"',
        )
    return content


def main() -> int:
    if not OLD_PACKAGE.exists():
        raise FileNotFoundError(
            f"Provider package was not found: {OLD_PACKAGE}"
        )

    NEW_PACKAGE.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "src" / "ai").mkdir(parents=True, exist_ok=True)

    (PROJECT_ROOT / "src" / "ai" / "__init__.py").write_text(
        AI_INIT,
        encoding="utf-8",
    )

    copied: list[str] = []

    for filename in FILES:
        source = OLD_PACKAGE / filename
        destination = NEW_PACKAGE / filename

        if not source.exists():
            raise FileNotFoundError(
                f"Required provider file was not found: {source}"
            )

        content = source.read_text(encoding="utf-8")
        content = replace_imports(content)

        if filename == "openai_provider.py":
            content = update_openai_default_model(content)

        destination.write_text(content, encoding="utf-8")
        copied.append(str(destination.relative_to(PROJECT_ROOT)))

    (NEW_PACKAGE / "__init__.py").write_text(
        EXTRACTION_INIT,
        encoding="utf-8",
    )

    for filename, wrapper in WRAPPERS.items():
        (OLD_PACKAGE / filename).write_text(
            wrapper,
            encoding="utf-8",
        )

    (OLD_PACKAGE / "__init__.py").write_text(
        COMPAT_INIT,
        encoding="utf-8",
    )

    print("=" * 72)
    print("AI EXTRACTION PACKAGE MIGRATION")
    print("=" * 72)
    print("Copied provider implementation files:")
    for path in copied:
        print(f"  [OK] {path}")

    print()
    print("Compatibility wrappers retained in src/providers.")
    print("Default OpenAI extraction model: gpt-4.1-mini")
    print()
    print("Next commands:")
    print("  py -m compileall src scripts main.py")
    print("  py -m scripts.test_openai_provider")
    print("  py .\\main.py --provider openai --ai-thread-id 95 --model gpt-4.1-mini")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
