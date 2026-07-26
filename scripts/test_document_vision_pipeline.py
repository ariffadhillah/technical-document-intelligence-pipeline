from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

from src.attachments.ocr import TesseractOCREngine
from src.attachments.pdf.renderer import PDFRenderer
from src.attachments.vision import (
    MockVisionEngine,
    VisionBenchmark,
    VisionFallbackProcessor,
    VisionRouter,
    VisionRouterConfig,
)


SUPPORTED_IMAGES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}


def load_cv_image(path: Path) -> np.ndarray:
    """
    Load an image safely, including paths containing
    non-ASCII characters on Windows.
    """

    raw_bytes = np.fromfile(
        str(path),
        dtype=np.uint8,
    )

    image = cv2.imdecode(
        raw_bytes,
        cv2.IMREAD_COLOR,
    )

    if image is None or image.size == 0:
        raise ValueError(
            f"Unable to load image: {path}"
        )

    return image


def prepare_images(
    input_path: Path,
    output_dir: Path,
) -> dict[int, tuple[Path, np.ndarray]]:
    suffix = input_path.suffix.lower()

    if suffix == ".pdf":
        render_dir = output_dir / "rendered"

        renderer = PDFRenderer()

        rendered_pages = renderer.render(
            pdf_path=input_path,
            output_dir=render_dir,
        )

        return {
            page.page_number: (
                page.image_path,
                load_cv_image(page.image_path),
            )
            for page in rendered_pages
        }

    if suffix in SUPPORTED_IMAGES:
        return {
            1: (
                input_path,
                load_cv_image(input_path),
            )
        }

    raise ValueError(
        f"Unsupported input type: {suffix}. "
        "Use PDF, PNG, JPG, JPEG, WebP, BMP, "
        "TIFF, or TIF."
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Test OCR and Vision fallback on a PDF "
            "or image."
        )
    )

    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to a PDF or image.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/vision_test"),
    )

    parser.add_argument(
        "--vision-threshold",
        type=float,
        default=0.60,
    )

    parser.add_argument(
        "--force-vision",
        action="store_true",
        help="Send every page to the mock Vision provider.",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
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

    input_path = args.input_path.resolve()

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}"
        )

    output_dir = args.output_dir.resolve()

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    page_images = prepare_images(
        input_path,
        output_dir,
    )

    ocr_engine = TesseractOCREngine(
        use_cache=not args.no_cache,
    )

    router = VisionRouter(
        config=VisionRouterConfig(
            default_provider="mock",
            default_model="mock-vision-v1",
            vision_threshold=args.vision_threshold,
        )
    )

    vision_engine = MockVisionEngine()

    vision_processor = VisionFallbackProcessor(
        engine=vision_engine,
        router=router,
    )

    ocr_pages = []
    images: dict[int, np.ndarray] = {}

    print("\nRunning OCR...\n")

    for page_number, (
        image_path,
        image,
    ) in sorted(page_images.items()):
        page = ocr_engine.process_image(
            image,
            page_number=page_number,
            source_path=image_path,
        )

        ocr_pages.append(page)
        images[page_number] = image

        print(
            f"Page {page_number}: "
            f"OCR confidence={page.confidence:.3f}, "
            f"OCR quality={page.quality_score:.3f}, "
            f"words={page.word_count}"
        )

    force_pages = (
        set(images)
        if args.force_vision
        else set()
    )

    print("\nRunning Vision routing...\n")

    batch = vision_processor.process_pages(
        pages=ocr_pages,
        images=images,
        force_pages=force_pages,
    )

    for result in batch.results:
        score = result.decision.score

        print("=" * 72)
        print(
            f"Page             : "
            f"{result.decision.page_number}"
        )
        print(
            f"Routing quality   : "
            f"{score.quality_score:.3f}"
            if score is not None
            else "Routing quality   : unknown"
        )
        print(
            f"Vision used       : "
            f"{result.decision.use_vision}"
        )
        print(
            f"Provider          : "
            f"{result.decision.provider}"
        )
        print(
            f"Cache hit         : "
            f"{result.from_cache}"
        )
        print(
            f"Success           : "
            f"{result.success}"
        )
        print(
            "Reasons           : "
            + ", ".join(
                reason.value
                for reason in result.decision.reasons
            )
        )
        print(
            f"Final engine      : "
            f"{result.final_page.engine_name}"
        )
        print(
            f"Final text preview: "
            f"{result.text[:180]!r}"
        )

    benchmark = VisionBenchmark()

    summary = benchmark.summarize(
        batch.audits
    )

    result_payload = {
        "source": str(input_path),
        "summary": asdict(summary),
        "batch": {
            "total_pages": batch.total_pages,
            "vision_pages": batch.vision_pages,
            "cache_hits": batch.cache_hits,
            "failures": batch.failures,
            "processing_time": batch.processing_time,
            "estimated_cost": batch.estimated_cost,
            "mock_provider_calls": (
                vision_engine.call_count
            ),
        },
        "pages": [
            page.to_dict()
            for page in batch.pages
        ],
        "audits": [
            asdict(audit)
            for audit in batch.audits
        ],
    }

    result_path = output_dir / "result.json"

    result_path.write_text(
        json.dumps(
            result_payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    benchmark.export_json(
        batch.audits,
        output_dir / "benchmark.json",
    )

    benchmark.export_csv(
        batch.audits,
        output_dir / "benchmark.csv",
    )

    final_text = "\n\n".join(
        (
            f"--- Page {page.page_number} ---\n\n"
            f"{page.text}"
        )
        for page in batch.pages
    )

    (
        output_dir / "final_text.md"
    ).write_text(
        final_text,
        encoding="utf-8",
    )

    print("\n" + "=" * 72)
    print("PIPELINE SUMMARY")
    print("=" * 72)
    print(f"Total pages      : {batch.total_pages}")
    print(f"Vision pages     : {batch.vision_pages}")
    print(f"Cache hits       : {batch.cache_hits}")
    print(f"Failures         : {batch.failures}")
    print(
        f"Vision usage     : "
        f"{batch.vision_usage_ratio:.2%}"
    )
    print(
        f"Mock API calls   : "
        f"{vision_engine.call_count}"
    )
    print(f"Output directory : {output_dir}")


if __name__ == "__main__":
    main()