from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.attachments.vision import (
    MockVisionEngine,
)
from src.pipeline import (
    DocumentIntelligencePipeline,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the complete document intelligence "
            "pipeline on a PDF or image."
        )
    )

    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to a PDF or image file.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Optional custom output directory."
        ),
    )

    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help=(
            "Optional Tesseract language, "
            "for example eng or deu."
        ),
    )

    parser.add_argument(
        "--vision-threshold",
        type=float,
        default=0.60,
    )

    parser.add_argument(
        "--force-vision",
        action="store_true",
        help=(
            "Send every page through Vision."
        ),
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help=(
            "Disable OCR and Vision cache."
        ),
    )

    parser.add_argument(
        "--render-dpi",
        type=int,
        default=400,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )

    vision_engine = MockVisionEngine()

    pipeline = DocumentIntelligencePipeline(
        vision_engine=vision_engine,
        render_dpi=args.render_dpi,
        use_ocr_cache=not args.no_cache,
        use_vision_cache=not args.no_cache,
        vision_threshold=(
            args.vision_threshold
        ),
    )

    result = pipeline.process(
        args.input_path,
        output_dir=args.output_dir,
        language=args.language,
        force_vision=args.force_vision,
    )

    print("\n" + "=" * 72)
    print("DOCUMENT INTELLIGENCE PIPELINE")
    print("=" * 72)

    print(
        f"Source            : "
        f"{result.source_path}"
    )

    print(
        f"Source type       : "
        f"{result.source_type}"
    )

    print(
        f"Success           : "
        f"{result.success}"
    )

    print(
        f"Total pages       : "
        f"{result.total_pages}"
    )

    print(
        f"Vision pages      : "
        f"{result.vision_pages}"
    )

    print(
        f"Vision cache hits : "
        f"{result.vision_cache_hits}"
    )

    print(
        f"Vision failures   : "
        f"{result.vision_failures}"
    )

    print(
        f"Vision usage      : "
        f"{result.vision_usage_ratio:.2%}"
    )

    print(
        f"Average confidence: "
        f"{result.average_confidence:.3f}"
    )

    print(
        f"Average quality   : "
        f"{result.average_quality:.3f}"
    )

    print(
        f"Processing time   : "
        f"{result.processing_time:.2f}s"
    )

    print(
        f"Mock API calls    : "
        f"{vision_engine.call_count}"
    )

    print(
        f"Output directory  : "
        f"{result.output_directory}"
    )

    print("\nPAGE RESULTS")

    for page in result.pages:
        print("-" * 72)

        print(
            f"Page              : "
            f"{page.page_number}"
        )

        print(
            f"Final engine      : "
            f"{page.engine_name}"
        )

        print(
            f"Confidence        : "
            f"{page.confidence:.3f}"
        )

        print(
            f"Quality           : "
            f"{page.quality_score:.3f}"
        )

        print(
            f"Text preview      : "
            f"{page.text[:180]!r}"
        )


if __name__ == "__main__":
    main()