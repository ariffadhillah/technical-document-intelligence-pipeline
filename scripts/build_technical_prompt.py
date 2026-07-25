from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.prompts import (
    PromptBuilderError,
    TechnicalPromptBuilder,
)


DEFAULT_AGGREGATED_DIRECTORY = (
    PROJECT_ROOT / "output" / "aggregated"
)

DEFAULT_AI_DIRECTORY = (
    PROJECT_ROOT / "output" / "ai"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an auditable technical extraction prompt "
            "from an aggregated JSON document."
        )
    )

    parser.add_argument(
        "input_path",
        nargs="?",
        type=Path,
        help=(
            "Path to an aggregated JSON document. "
            "When omitted, the first aggregated JSON file "
            "is selected automatically."
        ),
    )

    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_AI_DIRECTORY,
        help=(
            "Base directory where the prompt bundle "
            "will be written."
        ),
    )

    parser.add_argument(
        "--max-content-characters",
        type=int,
        default=None,
        help=(
            "Optional temporary character limit for testing. "
            "Do not use this as the final production "
            "chunking strategy."
        ),
    )

    return parser.parse_args()


def discover_default_input() -> Path:
    if not DEFAULT_AGGREGATED_DIRECTORY.exists():
        raise FileNotFoundError(
            "Aggregated output directory does not exist: "
            f"{DEFAULT_AGGREGATED_DIRECTORY}"
        )

    candidates = sorted(
        DEFAULT_AGGREGATED_DIRECTORY.glob("*.json")
    )

    if not candidates:
        candidates = sorted(
            DEFAULT_AGGREGATED_DIRECTORY.rglob("*.json")
        )

    if not candidates:
        raise FileNotFoundError(
            "No aggregated JSON documents were found in "
            f"{DEFAULT_AGGREGATED_DIRECTORY}"
        )

    return candidates[0]


def main() -> int:
    arguments = parse_arguments()

    try:
        input_path = (
            arguments.input_path.resolve()
            if arguments.input_path
            else discover_default_input().resolve()
        )

        builder = TechnicalPromptBuilder(
            max_content_characters=(
                arguments.max_content_characters
            )
        )

        prompt = builder.build_from_file(
            input_path=input_path
        )

        prompt_output_directory = (
            arguments.output_directory.resolve()
            / prompt.document_id
        )

        saved_paths = builder.save_prompt_bundle(
            prompt=prompt,
            output_directory=prompt_output_directory,
        )

    except (
        FileNotFoundError,
        PromptBuilderError,
        OSError,
    ) as error:
        print("=" * 72)
        print("TECHNICAL EXTRACTION PROMPT BUILDER")
        print("=" * 72)
        print()
        print("[FAILED]")
        print(error)
        return 1

    print("=" * 72)
    print("TECHNICAL EXTRACTION PROMPT BUILDER")
    print("=" * 72)
    print(f"Input              : {input_path}")
    print(f"Document ID        : {prompt.document_id}")
    print(f"Title              : {prompt.title}")
    print(f"Prompt name        : {prompt.prompt_name}")
    print(f"Prompt version     : {prompt.prompt_version}")
    print(
        "Source characters  : "
        f"{prompt.source_character_count:,}"
    )
    print(
        "System prompt SHA  : "
        f"{prompt.system_prompt_sha256}"
    )
    print(
        "User prompt SHA    : "
        f"{prompt.user_prompt_sha256}"
    )
    print()
    print("[OK] Prompt bundle created")
    print(
        "System prompt      : "
        f"{saved_paths['system_prompt']}"
    )
    print(
        "User prompt        : "
        f"{saved_paths['user_prompt']}"
    )
    print(
        "Metadata           : "
        f"{saved_paths['metadata']}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main()) 