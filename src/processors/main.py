from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")


from src.aggregators.content_aggregator import ContentAggregator
from src.attachments.attachment_processor import AttachmentProcessor
from src.attachments.vision import (
    BaseVisionEngine,
    MockVisionEngine,
    OpenAIVisionEngine,
)
from src.cleaners.text_cleaner import clean_thread
from src.loaders.raw_dataset_loader import load_all_threads
from src.processors.ai_stage_runner import TechnicalAIStageRunner
from src.processors.final_delivery_stage import (
    FinalDeliveryStageRunner,
)
from src.providers import ProviderError
from src.pipeline import DocumentIntelligencePipeline
from src.rag import RAGStageRunner
from src.renderers import RenderingStageRunner


RAW_DIRECTORY = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIRECTORY = PROJECT_ROOT / "data" / "processed"

CLEANED_DIRECTORY = PROJECT_ROOT / "output" / "cleaned"
MERGED_DIRECTORY = PROJECT_ROOT / "output" / "merged"
AGGREGATED_DIRECTORY = PROJECT_ROOT / "output" / "aggregated"

OCR_DIRECTORY = PROJECT_ROOT / "output" / "attachments" / "ocr"
PDF_DIRECTORY = PROJECT_ROOT / "output" / "attachments" / "pdf"
DOCUMENT_PIPELINE_DIRECTORY = (
    PROJECT_ROOT / "output" / "document_pipeline"
)

AI_OUTPUT_DIRECTORY = PROJECT_ROOT / "output" / "ai"
RENDERED_OUTPUT_DIRECTORY = PROJECT_ROOT / "output" / "rendered"
RAG_OUTPUT_DIRECTORY = PROJECT_ROOT / "output" / "rag"
FINAL_OUTPUT_DIRECTORY = PROJECT_ROOT / "output" / "final"

REPORT_DIRECTORY = PROJECT_ROOT / "output" / "reports"

DEFAULT_MOCK_RESPONSE_PATH = (
    PROJECT_ROOT
    / "data"
    / "samples"
    / "thread_6260_structured_sample.json"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the end-to-end technical document "
            "intelligence pipeline."
        )
    )

    parser.add_argument(
        "--provider",
        choices=("none", "mock", "openai"),
        default="none",
        help=(
            "AI provider to use. 'none' runs only the "
            "deterministic document-processing stages."
        ),
    )

    parser.add_argument(
        "--ai-thread-id",
        default=None,
        help=(
            "Run AI, rendering, and RAG only for this "
            "thread ID. Example: 6260."
        ),
    )

    parser.add_argument(
        "--mock-response",
        type=Path,
        default=DEFAULT_MOCK_RESPONSE_PATH,
        help="Structured response file used by MockProvider.",
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
        default=6000,
        help="Maximum provider output tokens.",
    )

    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=60.0,
        help="Provider timeout in seconds.",
    )

    parser.add_argument(
        "--rag-max-chars",
        type=int,
        default=1800,
        help="Maximum character count per RAG chunk.",
    )

    parser.add_argument(
        "--rag-overlap-chars",
        type=int,
        default=180,
        help="Character overlap between oversized RAG chunks.",
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


def build_attachment_vision_engine(
    *,
    provider: str,
    model: str | None,
) -> BaseVisionEngine:
    """
    Gunakan provider CLI yang sama untuk attachment Vision.

    `openai` mengaktifkan OpenAI Vision. `mock` dan `none`
    mempertahankan mode lokal/deterministik tanpa API Vision.
    """
    selected_provider = provider.strip().lower()

    if selected_provider == "openai":
        return OpenAIVisionEngine(
            model=(
                model
                or os.getenv("OPENAI_MODEL")
                or "gpt-4.1-mini"
            ),
            detail=(
                os.getenv("OPENAI_VISION_DETAIL")
                or "high"
            ),
        )

    return MockVisionEngine()


def process_thread(
    *,
    thread_data: dict[str, Any],
    position: int,
    total: int,
    attachment_processor: AttachmentProcessor,
    content_aggregator: ContentAggregator,
    ai_stage_runner: TechnicalAIStageRunner | None,
    ai_provider: Any | None,
    rendering_stage_runner: RenderingStageRunner | None,
    rag_stage_runner: RAGStageRunner | None,
    final_delivery_runner: FinalDeliveryStageRunner | None,
    ai_thread_id: str | None,
) -> dict[str, Any]:
    metadata = thread_data.get("metadata", {})

    thread_id = str(
        metadata.get("thread_id", "unknown")
    )
    title = metadata.get("title", "Untitled thread")
    posts = thread_data.get("posts", [])

    attachment_count = sum(
        len(post.get("attachments", []))
        for post in posts
    )

    print()
    print(f"[{position}/{total}] thread_{thread_id}")
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
    rendering_result: dict[str, Any] | None = None
    rag_result: dict[str, Any] | None = None
    final_delivery_result: dict[str, Any] | None = None

    should_run_ai = (
        ai_stage_runner is not None
        and ai_provider is not None
        and (
            ai_thread_id is None
            or thread_id == str(ai_thread_id)
        )
    )

    if should_run_ai:
        print(
            "    [AI] Running structured "
            "technical extraction"
        )

        result = ai_stage_runner.run(
            aggregated_document=aggregated_document,
            provider=ai_provider,
        )

        ai_result = result.to_dict()

        print(
            "    [OK] AI extraction completed "
            f"(provider={result.provider}, "
            f"model={result.model}, "
            f"tokens={result.total_tokens})"
        )
        print(
            "    AI output   : "
            f"{result.validated_response_path}"
        )

        validated_document = (
            RenderingStageRunner.load_validated_document(
                Path(result.validated_response_path)
            )
        )

        if rendering_stage_runner is not None:
            rendered = rendering_stage_runner.run(
                document=validated_document,
            )
            rendering_result = rendered.to_dict()

            print(
                "    [OK] Rendered outputs created"
            )
            print(
                "    Markdown    : "
                f"{rendered.markdown_path}"
            )
            print(
                "    Plain text  : "
                f"{rendered.text_path}"
            )
            print(
                "    Metadata    : "
                f"{rendered.metadata_path}"
            )

        if rag_stage_runner is not None:
            rag = rag_stage_runner.run(
                document=validated_document,
            )
            rag_result = rag.to_dict()

            print(
                "    [OK] RAG chunks created "
                f"(chunks={rag.chunk_count})"
            )
            print(
                "    RAG output  : "
                f"{rag.output_path}"
            )

        if (
            final_delivery_runner is not None
            and rendering_result is not None
            and rag_result is not None
        ):
            provider_metadata_value = getattr(
                result,
                "provider_metadata_path",
                None,
            )

            final_delivery = final_delivery_runner.run(
                validated_document=validated_document,
                enriched_thread=enriched_thread,
                aggregated_document=aggregated_document,
                validated_response_path=Path(
                    result.validated_response_path
                ),
                rendered_markdown_path=Path(
                    rendered.markdown_path
                ),
                rendered_text_path=Path(
                    rendered.text_path
                ),
                rendered_metadata_path=Path(
                    rendered.metadata_path
                ),
                rag_output_path=Path(
                    rag.output_path
                ),
                provider_metadata_path=(
                    Path(provider_metadata_value)
                    if provider_metadata_value
                    else None
                ),
            )
            final_delivery_result = (
                final_delivery.to_dict()
            )

            print(
                "    [OK] Final delivery package created"
            )
            print(
                "    Final folder: "
                f"{final_delivery.output_directory}"
            )
            if final_delivery.archive_path is not None:
                print(
                    "    Final ZIP   : "
                    f"{final_delivery.archive_path}"
                )

    elif (
        ai_stage_runner is not None
        and ai_thread_id is not None
    ):
        print(
            "    [SKIP] AI, rendering, and RAG "
            f"not selected for thread_{thread_id}"
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
        "rendering": rendering_result,
        "rag": rag_result,
        "final_delivery": final_delivery_result,
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

    try:
        attachment_vision_engine = (
            build_attachment_vision_engine(
                provider=arguments.provider,
                model=arguments.model,
            )
        )
    except Exception as error:
        print()
        print("Attachment Vision initialization failed:")
        print(error)
        return 1

    document_pipeline = DocumentIntelligencePipeline(
        vision_engine=attachment_vision_engine,
        output_root=DOCUMENT_PIPELINE_DIRECTORY,
        render_dpi=400,
        use_ocr_cache=True,
        use_vision_cache=True,
        vision_threshold=0.60,
        use_analyzer_vision_recommendation=True,
        fail_open=True,
    )

    attachment_processor = AttachmentProcessor(
        ocr_output_directory=OCR_DIRECTORY,
        pdf_output_directory=PDF_DIRECTORY,
        document_pipeline=document_pipeline,
    )

    content_aggregator = ContentAggregator()

    rendering_stage_runner = RenderingStageRunner(
        output_directory=RENDERED_OUTPUT_DIRECTORY,
    )

    rag_stage_runner = RAGStageRunner(
        output_directory=RAG_OUTPUT_DIRECTORY,
        max_chars=arguments.rag_max_chars,
        overlap_chars=arguments.rag_overlap_chars,
    )

    final_delivery_runner = FinalDeliveryStageRunner(
        output_directory=FINAL_OUTPUT_DIRECTORY,
        create_zip=True,
    )

    ai_stage_runner: TechnicalAIStageRunner | None = None
    ai_provider: Any | None = None

    if arguments.model:
        selected_model = arguments.model
    elif arguments.provider == "openai":
        selected_model = (
            os.getenv("OPENAI_MODEL")
            or "gpt-4.1-mini"
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

        if arguments.provider == "mock":
            provider_configuration: dict[str, Any] = {
                "response_file": (
                    arguments.mock_response.resolve()
                ),
            }
        else:
            provider_configuration = {}

        try:
            ai_provider = ai_stage_runner.create_provider(
                provider_name=arguments.provider,
                configuration=provider_configuration,
            )
        except ProviderError as error:
            print()
            print("AI provider initialization failed:")
            print(error)
            return 1

        print(f"AI provider  : {arguments.provider}")
        print(f"AI model     : {selected_model}")

        if arguments.ai_thread_id:
            print(
                "AI thread ID : "
                f"{arguments.ai_thread_id}"
            )
    else:
        print(
            "AI provider  : none "
            "(rendering and RAG will not run)"
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
                rendering_stage_runner=(
                    rendering_stage_runner
                ),
                rag_stage_runner=rag_stage_runner,
                final_delivery_runner=(
                    final_delivery_runner
                ),
                ai_thread_id=arguments.ai_thread_id,
            )

            results.append(result)

        except Exception as error:
            thread_id = str(
                thread_data
                .get("metadata", {})
                .get("thread_id", "unknown")
            )

            print(
                f"    [FAILED] thread_{thread_id}: "
                f"{error}"
            )

            details = getattr(error, "details", None)

            if details:
                print(
                    "    Error details: "
                    f"{json.dumps(details, ensure_ascii=False)}"
                )

            failures.append(
                {
                    "thread_id": thread_id,
                    "error": str(error),
                }
            )

    ai_results = [
        result["ai_processing"]
        for result in results
        if result.get("ai_processing") is not None
    ]

    rendered_results = [
        result["rendering"]
        for result in results
        if result.get("rendering") is not None
    ]

    rag_results = [
        result["rag"]
        for result in results
        if result.get("rag") is not None
    ]

    final_delivery_results = [
        result["final_delivery"]
        for result in results
        if result.get("final_delivery") is not None
    ]

    manifest = {
        "pipeline_stage": (
            "load_clean_attachment_extract_"
            "aggregate_ai_render_rag"
        ),
        "provider": arguments.provider,
        "ai_thread_id": arguments.ai_thread_id,
        "thread_count": len(threads),
        "successful": len(results),
        "failed": len(failures),
        "ai_documents_processed": len(ai_results),
        "rendered_documents": len(rendered_results),
        "rag_documents": len(rag_results),
        "final_delivery_documents": len(
            final_delivery_results
        ),
        "rag_chunks": sum(
            item.get("chunk_count", 0)
            for item in rag_results
        ),
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
    print(f"Threads discovered : {len(threads)}")
    print(f"Successful         : {len(results)}")
    print(f"Failed             : {len(failures)}")
    print(f"AI provider        : {arguments.provider}")
    print(f"AI documents       : {len(ai_results)}")
    print(f"Rendered documents : {len(rendered_results)}")
    print(f"RAG documents      : {len(rag_results)}")
    print(
        "Final deliveries   : "
        f"{len(final_delivery_results)}"
    )
    print(
        "RAG chunks         : "
        f"{manifest['rag_chunks']}"
    )
    print(f"Manifest           : {manifest_path}")

    if failures:
        print("Status             : completed with errors")
        return 1

    print("Status             : success")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
