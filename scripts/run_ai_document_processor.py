from pathlib import Path
import argparse
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from src.config.settings import get_settings  # noqa: E402
from src.processors.ai_document_processor import (  # noqa: E402
    AIDocumentProcessor,
)
from src.providers.openai_provider import (  # noqa: E402
    OpenAIProvider,
)


DEFAULT_INPUT_PATH = (
    PROJECT_ROOT
    / "output"
    / "merged"
    / "thread_6260_ocr_merged.json"
)

DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "output"
    / "enriched"
    / "thread_6260_ai_enriched.json"
)

DEFAULT_CACHE_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "ai"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Process OCR-completed thread attachments "
            "using structured AI extraction."
        ),
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to OCR-merged thread JSON.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path for AI-enriched thread JSON.",
    )

    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIRECTORY,
        help="Directory for individual AI result files.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Ignore valid cached results and process "
            "eligible attachments again."
        ),
    )

    return parser.parse_args()


def load_json(
    file_path: Path,
) -> dict:
    if not file_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {file_path}"
        )

    return json.loads(
        file_path.read_text(
            encoding="utf-8",
        )
    )


def save_json(
    file_path: Path,
    payload: dict,
) -> None:
    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = file_path.with_suffix(
        file_path.suffix + ".tmp"
    )

    temporary_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temporary_path.replace(file_path)


def main() -> None:
    arguments = parse_arguments()

    print("=" * 70)
    print("AI DOCUMENT PROCESSOR")
    print("=" * 70)
    print(f"Input               : {arguments.input}")
    print(f"Output              : {arguments.output}")
    print(f"Cache directory     : {arguments.cache_dir}")
    print(f"Force processing    : {arguments.force}")

    thread_data = load_json(
        arguments.input,
    )

    settings = get_settings()

    print(f"Provider            : {settings.ai_provider}")
    print(f"Model               : {settings.openai_model}")
    print("-" * 70)

    provider = OpenAIProvider(
        settings=settings,
    )

    processor = AIDocumentProcessor(
        settings=settings,
        provider=provider,
        output_directory=arguments.cache_dir,
        force=arguments.force,
    )

    enriched_thread, stats = (
        processor.process_thread(
            thread_data=thread_data,
        )
    )

    save_json(
        file_path=arguments.output,
        payload=enriched_thread,
    )

    print("-" * 70)
    print(
        f"Total attachments   : "
        f"{stats.total_attachments}"
    )
    print(
        f"Eligible            : "
        f"{stats.eligible_attachments}"
    )
    print(
        f"Processed via AI    : "
        f"{stats.processed}"
    )
    print(
        f"Loaded from cache   : "
        f"{stats.cached}"
    )
    print(
        f"Skipped             : "
        f"{stats.skipped}"
    )
    print(
        f"Failed              : "
        f"{stats.failed}"
    )
    print(f"Output file         : {arguments.output}")

    if stats.failed:
        print("Status              : completed_with_errors")
        raise SystemExit(1)

    print("Status              : success")


if __name__ == "__main__":
    main()