from __future__ import annotations
import os
import argparse
import json
import sys
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent

load_dotenv(
    PROJECT_ROOT / ".env"
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.aggregators.content_aggregator import (
    ContentAggregator,
)
from src.attachments.attachment_processor import (
    AttachmentProcessor,
)
from src.cleaners.text_cleaner import clean_thread
from src.loaders.raw_dataset_loader import (
    load_all_threads,
)
from src.processors.ai_stage_runner import (
    TechnicalAIStageRunner,
)
from src.providers import ProviderError


RAW_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "raw"
)

PROCESSED_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

CLEANED_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "cleaned"
)

MERGED_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "merged"
)

AGGREGATED_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "aggregated"
)

OCR_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "attachments"
    / "ocr"
)

PDF_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "attachments"
    / "pdf"
)

REPORT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "reports"
)

AI_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "ai"
)

DEFAULT_MOCK_RESPONSE_PATH = (
    PROJECT_ROOT
    / "data"
    / "samples"
    / "thread_6260_structured_sample.json"
)

PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.aggregators.content_aggregator import (
    ContentAggregator,
)
from src.attachments.attachment_processor import (
    AttachmentProcessor,
)
from src.cleaners.text_cleaner import clean_thread
from src.loaders.raw_dataset_loader import load_all_threads


RAW_DIRECTORY = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIRECTORY = PROJECT_ROOT / "data" / "processed"

CLEANED_DIRECTORY = PROJECT_ROOT / "output" / "cleaned"
MERGED_DIRECTORY = PROJECT_ROOT / "output" / "merged"
AGGREGATED_DIRECTORY = PROJECT_ROOT / "output" / "aggregated"

OCR_DIRECTORY = PROJECT_ROOT / "output" / "attachments" / "ocr"
PDF_DIRECTORY = PROJECT_ROOT / "output" / "attachments" / "pdf"
REPORT_DIRECTORY = PROJECT_ROOT / "output" / "reports"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the technical document intelligence "
            "pipeline."
        )
    )

    parser.add_argument(
        "--provider",
        choices=(
            "none",
            "mock",
            "openai",
        ),
        default="none",
        help=(
            "AI provider to use. The default 'none' "
            "runs document processing without AI."
        ),
    )

    parser.add_argument(
        "--ai-thread-id",
        default=None,
        help=(
            "Run the AI stage only for this thread ID. "
            "Example: 6260."
        ),
    )

    parser.add_argument(
        "--mock-response",
        type=Path,
        default=DEFAULT_MOCK_RESPONSE_PATH,
        help=(
            "Structured response file used by MockProvider."
        ),
    )

    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Provider model identifier. When omitted, "
            "the provider default is used."
        ),
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Provider sampling temperature.",
    )

    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=16000,
        help="Maximum provider output tokens.",
    )

    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=60.0,
        help="Provider timeout in seconds.",
    )

    return parser.parse_args()


def save_json(
    payload: dict[str, Any],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = output_path.with_suffix(
        output_path.suffix + ".tmp"
    )

    temporary_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temporary_path.replace(output_path)


def process_thread(
    thread_data: dict[str, Any],
    position: int,
    total: int,
    attachment_processor: AttachmentProcessor,
    content_aggregator: ContentAggregator,
    ai_stage_runner: TechnicalAIStageRunner | None = None,
    ai_provider: Any | None = None,
    ai_thread_id: str | None = None,
) -> dict[str, Any]:
    metadata = thread_data.get("metadata", {})

    thread_id = metadata.get("thread_id", "unknown")
    title = metadata.get("title", "Untitled thread")

    posts = thread_data.get("posts", [])

    attachment_count = sum(
        len(post.get("attachments", []))
        for post in posts
    )

    print()
    print(
        f"[{position}/{total}] "
        f"thread_{thread_id}"
    )
    print(f"    Title       : {title}")
    print(f"    Posts       : {len(posts)}")
    print(f"    Attachments : {attachment_count}")

    parsed_output_path = (
        PROCESSED_DIRECTORY
        / f"thread_{thread_id}_parsed.json"
    )

    save_json(
        payload=thread_data,
        output_path=parsed_output_path,
    )

    print("    [OK] Raw data loaded and normalized")

    cleaned_thread = clean_thread(thread_data)

    cleaned_output_path = (
        CLEANED_DIRECTORY
        / f"thread_{thread_id}_cleaned.json"
    )

    save_json(
        payload=cleaned_thread,
        output_path=cleaned_output_path,
    )

    print("    [OK] Forum text cleaned")

    enriched_thread, attachment_stats = (
        attachment_processor.process_thread(
            thread_data=cleaned_thread,
        )
    )

    merged_output_path = (
        MERGED_DIRECTORY
        / f"thread_{thread_id}_content_merged.json"
    )

    save_json(
        payload=enriched_thread,
        output_path=merged_output_path,
    )

    print(
        "    [OK] Attachments processed "
        f"(completed={attachment_stats.completed}, "
        f"empty={attachment_stats.empty}, "
        f"failed={attachment_stats.failed})"
    )

    aggregated_document = content_aggregator.aggregate(
        thread_data=enriched_thread,
    )

    aggregated_output_path = (
        AGGREGATED_DIRECTORY
        / f"thread_{thread_id}_aggregated.json"
    )

    save_json(
        payload=aggregated_document,
        output_path=aggregated_output_path,
    )

    aggregation_statistics = (
        aggregated_document.get("statistics", {})
    )

    print(
        "    [OK] Content aggregated "
        f"(forum_chars="
        f"{aggregation_statistics.get('forum_character_count', 0)}, "
        f"ocr_chars="
        f"{aggregation_statistics.get('ocr_character_count', 0)}, "
        f"pdf_chars="
        f"{aggregation_statistics.get('pdf_character_count', 0)}, "
        f"total_chars="
        f"{aggregation_statistics.get('combined_character_count', 0)})"
    )

    print(f"    Merged      : {merged_output_path}")
    print(f"    Aggregated  : {aggregated_output_path}")


    ai_result: dict[str, Any] | None = None

    should_run_ai = (
        ai_stage_runner is not None
        and ai_provider is not None
        and (
            ai_thread_id is None
            or str(thread_id) == str(ai_thread_id)
        )
    )

    if should_run_ai:
        print(
            " [AI] Running structured "
            "technical extraction"
        )

        result = ai_stage_runner.run(
            aggregated_document=aggregated_document,
            provider=ai_provider,
        )

        ai_result = result.to_dict()

        print(
            " [OK] AI extraction completed "
            f"(provider={result.provider}, "
            f"model={result.model}, "
            f"tokens={result.total_tokens})"
        )

        print(
            " AI output : "
            f"{result.validated_response_path}"
        )

    elif (
        ai_stage_runner is not None
        and ai_thread_id is not None
    ):
        print(
            " [SKIP] AI stage not selected "
            f"for thread_{thread_id}"
        )


    return {
        "thread_id": thread_id,
        "title": title,
        "posts": len(posts),
        "attachments": attachment_count,
        "attachment_processing": (
            attachment_stats.to_dict()
        ),
        "aggregation_statistics": (
            aggregation_statistics
        ),
        "parsed_output": str(parsed_output_path),
        "cleaned_output": str(cleaned_output_path),
        "merged_output": str(merged_output_path),
        "aggregated_output": str(
            aggregated_output_path
        ),
        "ready_for_ai": (
            aggregated_document
            .get("processing", {})
            .get("ready_for_ai", False)
        ),
        "ai_processing": ai_result,
        "status": (
            "success"
            if attachment_stats.failed == 0
            else "completed_with_attachment_errors"
        ),
    }

def main() -> int:
    arguments = parse_arguments()
    print("=" * 72)
    print("TECHNICAL DOCUMENT INTELLIGENCE PIPELINE")
    print("=" * 72)
    print(f"Project root : {PROJECT_ROOT}")
    print(f"Raw data     : {RAW_DIRECTORY}")


    try:
        threads = load_all_threads(
            raw_directory=RAW_DIRECTORY
        )
    except Exception as error:
        print(f"\nDataset loading failed: {error}")
        return 1

    print(f"Threads found: {len(threads)}")




    attachment_processor = AttachmentProcessor(
        ocr_output_directory=OCR_DIRECTORY,
        pdf_output_directory=PDF_DIRECTORY,
    )

    content_aggregator = ContentAggregator()

    ai_stage_runner: TechnicalAIStageRunner | None = None
    ai_provider: Any | None = None

    if arguments.model:
        selected_model = arguments.model

    elif arguments.provider == "openai":
        selected_model = (
            os.getenv("OPENAI_MODEL")
            or "gpt-5.6-luna"
        )

    else:
        selected_model = (
            "mock-technical-extraction-v1"
        )

    if arguments.provider != "none":
        ai_stage_runner = TechnicalAIStageRunner(
            output_directory=AI_OUTPUT_DIRECTORY,
            model=selected_model,
            temperature=arguments.temperature,
            max_output_tokens=(
                arguments.max_output_tokens
            ),
            timeout_seconds=(
                arguments.timeout_seconds
            ),
        )

        provider_configuration: dict[str, Any]

        if arguments.provider == "mock":
            provider_configuration = {
                "response_file": (
                    arguments.mock_response.resolve()
                ),
            }

        else:
            provider_configuration = {}

        try:
            ai_provider = (
                ai_stage_runner.create_provider(
                    provider_name=arguments.provider,
                    configuration=(
                        provider_configuration
                    ),
                )
            )

        except ProviderError as error:
            print()
            print(
                "AI provider initialization failed:"
            )
            print(error)
            return 1

        print(
            f"AI provider  : {arguments.provider}"
        )

        print(
            f"AI model     : {selected_model.model}"
        )

        if arguments.ai_thread_id:
            print(
                "AI thread ID : "
                f"{arguments.ai_thread_id}"
            )

    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for position, thread_data in enumerate(
        threads,
        start=1,
    ):
        try:

            result = process_thread(
                thread_data=thread_data,
                position=position,
                total=len(threads),
                attachment_processor=attachment_processor,
                content_aggregator=content_aggregator,
                ai_stage_runner=ai_stage_runner,
                ai_provider=ai_provider,
                ai_thread_id=arguments.ai_thread_id,
            )

            results.append(result)

        except Exception as error:
            thread_id = (
                thread_data
                .get("metadata", {})
                .get("thread_id", "unknown")
            )

            print(
                f"    [FAILED] thread_{thread_id}: "
                f"{error}"
            )

            failures.append(
                {
                    "thread_id": str(thread_id),
                    "error": str(error),
                }
            )

    ai_results = [
        result["ai_processing"]
        for result in results
        if result.get("ai_processing") is not None
    ]



    manifest = {
        "pipeline_stage": (
            "load_clean_attachment_extract_"
            "aggregate_and_optional_ai"
        ),
        "provider": arguments.provider,
        "ai_thread_id": arguments.ai_thread_id,
        "thread_count": len(threads),
        "successful": len(results),
        "failed": len(failures),
        "ai_documents_processed": len(ai_results),
        "threads": results,
        "failures": failures,
    }

    manifest_path = (
        REPORT_DIRECTORY
        / "pipeline_manifest.json"
    )

    save_json(
        payload=manifest,
        output_path=manifest_path,
    )

    print()
    print("=" * 72)
    print("PIPELINE SUMMARY")
    print("=" * 72)

    print(
        f"Threads discovered : {len(threads)}"
    )

    print(
        f"Successful         : {len(results)}"
    )

    print(
        f"Failed             : {len(failures)}"
    )

    print(
        f"AI provider        : "
        f"{arguments.provider}"
    )

    print(
        f"AI documents       : "
        f"{len(ai_results)}"
    )

    print(
        f"Manifest           : "
        f"{manifest_path}"
    )

    if failures:
        print("Status             : completed with errors")
        return 1

    print("Status             : success")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())