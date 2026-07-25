from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.renderers import (
    MarkdownRenderingError,
    TechnicalMarkdownRenderer,
)


DEFAULT_INPUT_PATH = (
    PROJECT_ROOT
    / "output"
    / "ai"
    / "thread_6260"
    / "05_validated_response.json"
)

DEFAULT_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "rendered"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render a validated structured technical "
            "document as Markdown."
        )
    )

    parser.add_argument(
        "input_path",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=(
            "Path to a validated structured JSON file."
        ),
    )

    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help=(
            "Base directory for rendered Markdown files."
        ),
    )

    parser.add_argument(
        "--output-name",
        default="technical_manual.md",
        help="Rendered Markdown filename.",
    )

    parser.add_argument(
        "--hide-evidence",
        action="store_true",
        help=(
            "Do not include source evidence blocks."
        ),
    )

    parser.add_argument(
        "--show-empty-sections",
        action="store_true",
        help=(
            "Include sections that contain no data."
        ),
    )

    parser.add_argument(
        "--hide-processing-metadata",
        action="store_true",
        help=(
            "Do not include processing metadata."
        ),
    )

    return parser.parse_args()


def determine_document_id(
    input_path: Path,
) -> str:
    parent_name = input_path.parent.name

    if parent_name.startswith("thread_"):
        return parent_name

    stem = input_path.stem

    if stem.endswith("_structured_sample"):
        return stem.removesuffix(
            "_structured_sample"
        )

    if stem.endswith("_validated_response"):
        return stem.removesuffix(
            "_validated_response"
        )

    return stem


def main() -> int:
    arguments = parse_arguments()

    input_path = arguments.input_path.resolve()
    output_directory = (
        arguments.output_directory.resolve()
    )

    document_id = determine_document_id(
        input_path
    )

    output_path = (
        output_directory
        / document_id
        / arguments.output_name
    )

    print("=" * 72)
    print("TECHNICAL MARKDOWN RENDERER")
    print("=" * 72)

    renderer = TechnicalMarkdownRenderer(
        include_evidence=(
            not arguments.hide_evidence
        ),
        include_empty_sections=(
            arguments.show_empty_sections
        ),
        include_processing_metadata=(
            not arguments.hide_processing_metadata
        ),
    )

    try:
        rendered_path = renderer.render_file(
            input_path=input_path,
            output_path=output_path,
        )

    except MarkdownRenderingError as error:
        print()
        print("[FAILED]")
        print(error)

        return 1

    markdown_size = rendered_path.stat().st_size

    print(f"Input document : {input_path}")
    print(f"Document ID    : {document_id}")
    print(f"Output file    : {rendered_path}")
    print(f"Output size    : {markdown_size:,} bytes")
    print()
    print("[OK] Technical Markdown rendered successfully")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())