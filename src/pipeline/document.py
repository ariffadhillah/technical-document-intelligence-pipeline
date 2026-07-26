from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Mapping

import cv2
import numpy as np

from src.attachments.ocr import (
    BaseOCREngine,
    TesseractOCREngine,
)
from src.attachments.pdf.renderer import PDFRenderer
from src.attachments.vision import (
    BaseVisionEngine,
    MockVisionEngine,
    VisionCache,
    VisionFallbackProcessor,
    VisionRouter,
    VisionRouterConfig,
)

from .models import (
    DocumentPipelineResult,
    PreparedPage,
)

logger = logging.getLogger(__name__)


class UnsupportedDocumentTypeError(ValueError):
    """
    Raised when the document type is unsupported.
    """


class DocumentIntelligencePipeline:
    """
    Main document intelligence orchestrator.

    Pipeline:

        PDF / Image
            ↓
        Prepare page images
            ↓
        OCR
            ↓
        Vision routing and fallback
            ↓
        Final normalized pages
            ↓
        JSON and Markdown output
    """

    SUPPORTED_IMAGE_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
        ".tif",
        ".tiff",
    }

    SUPPORTED_DOCUMENT_EXTENSIONS = (
        SUPPORTED_IMAGE_EXTENSIONS | {".pdf"}
    )

    def __init__(
        self,
        *,
        ocr_engine: BaseOCREngine | None = None,
        vision_engine: BaseVisionEngine | None = None,
        pdf_renderer: PDFRenderer | None = None,
        vision_router: VisionRouter | None = None,
        vision_processor: (
            VisionFallbackProcessor | None
        ) = None,
        output_root: str | Path = (
            "output/document_pipeline"
        ),
        render_dpi: int = 400,
        use_ocr_cache: bool = True,
        use_vision_cache: bool = True,
        vision_threshold: float = 0.60,
        fail_open: bool = True,
    ) -> None:
        self.output_root = Path(output_root)

        self.render_dpi = render_dpi

        self.ocr_engine = (
            ocr_engine
            or TesseractOCREngine(
                use_cache=use_ocr_cache,
            )
        )

        self.vision_engine = (
            vision_engine
            or MockVisionEngine()
        )

        self.pdf_renderer = (
            pdf_renderer
            or PDFRenderer()
        )

        self.vision_router = (
            vision_router
            or VisionRouter(
                config=VisionRouterConfig(
                    default_provider=(
                        self.vision_engine
                        .get_provider_name()
                    ),
                    default_model=(
                        self.vision_engine
                        .get_model_name()
                    ),
                    vision_threshold=(
                        vision_threshold
                    ),
                )
            )
        )

        self.vision_processor = (
            vision_processor
            or VisionFallbackProcessor(
                engine=self.vision_engine,
                router=self.vision_router,
                cache=VisionCache(
                    enabled=use_vision_cache,
                ),
                fail_open=fail_open,
            )
        )

    def process(
        self,
        source_path: str | Path,
        *,
        output_dir: str | Path | None = None,
        language: str | None = None,
        force_vision: bool = False,
        force_vision_pages: set[int] | None = None,
        image_types: Mapping[int, str] | None = None,
        write_outputs: bool = True,
    ) -> DocumentPipelineResult:
        """
        Process one PDF or image through the complete
        OCR and Vision pipeline.
        """

        started_at = time.perf_counter()

        source = Path(source_path).expanduser().resolve()

        self._validate_source(source)

        document_output_dir = (
            Path(output_dir).expanduser().resolve()
            if output_dir is not None
            else self._build_output_directory(source)
        )

        document_output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        source_type = self._detect_source_type(
            source
        )

        logger.info(
            "Starting document pipeline: source=%s "
            "type=%s",
            source,
            source_type,
        )

        prepared_pages, images = (
            self._prepare_pages(
                source=source,
                source_type=source_type,
                output_dir=document_output_dir,
            )
        )

        original_ocr_pages = self._run_ocr(
            prepared_pages=prepared_pages,
            images=images,
            language=language,
        )

        resolved_image_types = dict(
            image_types or {}
        )

        force_pages = set(
            force_vision_pages or set()
        )

        if force_vision:
            force_pages.update(
                page.page_number
                for page in original_ocr_pages
            )

        vision_batch = (
            self.vision_processor.process_pages(
                pages=original_ocr_pages,
                images=images,
                image_types=resolved_image_types,
                force_pages=force_pages,
            )
        )

        final_pages = sorted(
            vision_batch.pages,
            key=lambda page: page.page_number,
        )

        merged_text = self._merge_pages(
            final_pages
        )

        result = DocumentPipelineResult(
            source_path=source,
            source_type=source_type,
            pages=final_pages,
            original_ocr_pages=(
                original_ocr_pages
            ),
            vision_results=(
                vision_batch.results
            ),
            audits=vision_batch.audits,
            merged_text=merged_text,
            total_pages=vision_batch.total_pages,
            vision_pages=vision_batch.vision_pages,
            vision_cache_hits=(
                vision_batch.cache_hits
            ),
            vision_failures=(
                vision_batch.failures
            ),
            processing_time=(
                time.perf_counter()
                - started_at
            ),
            estimated_cost=(
                vision_batch.estimated_cost
            ),
            output_directory=(
                document_output_dir
            ),
            metadata={
                "render_dpi": self.render_dpi,
                "ocr_engine": (
                    self.ocr_engine.engine_name
                ),
                "vision_provider": (
                    self.vision_engine
                    .get_provider_name()
                ),
                "vision_model": (
                    self.vision_engine
                    .get_model_name()
                ),
                "force_vision": force_vision,
                "force_vision_pages": sorted(
                    force_pages
                ),
                "prepared_pages": [
                    page.to_dict()
                    for page in prepared_pages
                ],
            },
        )

        if write_outputs:
            self.write_outputs(result)

        logger.info(
            "Document pipeline completed: "
            "pages=%s vision_pages=%s "
            "failures=%s time=%.2fs",
            result.total_pages,
            result.vision_pages,
            result.vision_failures,
            result.processing_time,
        )

        return result

    def write_outputs(
        self,
        result: DocumentPipelineResult,
    ) -> None:
        """
        Write the standard pipeline artifacts.
        """

        output_dir = result.output_directory

        if output_dir is None:
            raise ValueError(
                "Result output_directory is not set."
            )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        result_json_path = (
            output_dir / "result.json"
        )

        result_json_path.write_text(
            json.dumps(
                result.to_dict(),
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        markdown_path = (
            output_dir / "final_text.md"
        )

        markdown_path.write_text(
            result.merged_text,
            encoding="utf-8",
        )

        summary_path = (
            output_dir / "summary.json"
        )

        summary_payload = {
            "source_path": str(
                result.source_path
            ),
            "source_type": result.source_type,
            "success": result.success,
            "total_pages": result.total_pages,
            "vision_pages": (
                result.vision_pages
            ),
            "vision_cache_hits": (
                result.vision_cache_hits
            ),
            "vision_failures": (
                result.vision_failures
            ),
            "vision_usage_ratio": (
                result.vision_usage_ratio
            ),
            "average_confidence": (
                result.average_confidence
            ),
            "average_quality": (
                result.average_quality
            ),
            "processing_time": (
                result.processing_time
            ),
            "estimated_cost": (
                result.estimated_cost
            ),
        }

        summary_path.write_text(
            json.dumps(
                summary_payload,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        logger.info(
            "Pipeline outputs written to %s",
            output_dir,
        )

    def _prepare_pages(
        self,
        *,
        source: Path,
        source_type: str,
        output_dir: Path,
    ) -> tuple[
        list[PreparedPage],
        dict[int, np.ndarray],
    ]:
        if source_type == "pdf":
            return self._prepare_pdf_pages(
                source=source,
                output_dir=output_dir,
            )

        return self._prepare_image_page(
            source=source
        )

    def _prepare_pdf_pages(
        self,
        *,
        source: Path,
        output_dir: Path,
    ) -> tuple[
        list[PreparedPage],
        dict[int, np.ndarray],
    ]:
        render_directory = (
            output_dir / "rendered"
        )

        rendered_pages = (
            self.pdf_renderer.render(
                pdf_path=source,
                output_dir=render_directory,
                dpi=self.render_dpi,
            )
        )

        prepared_pages: list[
            PreparedPage
        ] = []

        images: dict[int, np.ndarray] = {}

        for rendered_page in rendered_pages:
            image = self._load_image(
                rendered_page.image_path
            )

            prepared_pages.append(
                PreparedPage(
                    page_number=(
                        rendered_page.page_number
                    ),
                    image_path=(
                        rendered_page.image_path
                    ),
                    width=rendered_page.width,
                    height=rendered_page.height,
                    source_type="pdf",
                    metadata={
                        "dpi": rendered_page.dpi,
                        "original_pdf": str(
                            source
                        ),
                    },
                )
            )

            images[
                rendered_page.page_number
            ] = image

        if not prepared_pages:
            raise ValueError(
                f"PDF produced no rendered pages: "
                f"{source}"
            )

        return prepared_pages, images

    def _prepare_image_page(
        self,
        *,
        source: Path,
    ) -> tuple[
        list[PreparedPage],
        dict[int, np.ndarray],
    ]:
        image = self._load_image(source)

        height, width = image.shape[:2]

        prepared_page = PreparedPage(
            page_number=1,
            image_path=source,
            width=width,
            height=height,
            source_type="image",
            metadata={
                "extension": (
                    source.suffix.lower()
                ),
            },
        )

        return (
            [prepared_page],
            {1: image},
        )

    def _run_ocr(
        self,
        *,
        prepared_pages: list[PreparedPage],
        images: Mapping[int, np.ndarray],
        language: str | None,
    ) -> list:
        pages = []

        for prepared_page in sorted(
            prepared_pages,
            key=lambda page: page.page_number,
        ):
            image = images.get(
                prepared_page.page_number
            )

            if image is None:
                raise ValueError(
                    "Prepared image is missing for "
                    f"page "
                    f"{prepared_page.page_number}."
                )

            page = self.ocr_engine.process_image(
                image,
                page_number=(
                    prepared_page.page_number
                ),
                source_path=(
                    prepared_page.image_path
                ),
                language=language,
            )

            pages.append(page)

            logger.info(
                "OCR page completed: page=%s "
                "confidence=%.3f quality=%.3f "
                "words=%s",
                page.page_number,
                page.confidence,
                page.quality_score,
                page.word_count,
            )

        return pages

    @staticmethod
    def _load_image(
        path: Path,
    ) -> np.ndarray:
        """
        Load an image safely on Windows, including
        file paths containing non-ASCII characters.
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

    @staticmethod
    def _merge_pages(
        pages: list,
    ) -> str:
        return "\n\n".join(
            (
                f"## Page {page.page_number}\n\n"
                f"{page.text.strip()}"
            )
            for page in pages
            if page.text.strip()
        )

    def _build_output_directory(
        self,
        source: Path,
    ) -> Path:
        safe_name = self._safe_directory_name(
            source.stem
        )

        return (
            self.output_root
            / safe_name
        ).resolve()

    @staticmethod
    def _safe_directory_name(
        value: str,
    ) -> str:
        normalized = "".join(
            character
            if (
                character.isalnum()
                or character in {"-", "_"}
            )
            else "_"
            for character in value
        )

        normalized = normalized.strip("_")

        return normalized or "document"

    def _validate_source(
        self,
        source: Path,
    ) -> None:
        if not source.exists():
            raise FileNotFoundError(
                f"Document not found: {source}"
            )

        if not source.is_file():
            raise ValueError(
                f"Document path is not a file: "
                f"{source}"
            )

        suffix = source.suffix.lower()

        if (
            suffix
            not in self.SUPPORTED_DOCUMENT_EXTENSIONS
        ):
            supported = ", ".join(
                sorted(
                    self.SUPPORTED_DOCUMENT_EXTENSIONS
                )
            )

            raise UnsupportedDocumentTypeError(
                f"Unsupported document type: "
                f"{suffix or '<no extension>'}. "
                f"Supported types: {supported}"
            )

    @staticmethod
    def _detect_source_type(
        source: Path,
    ) -> str:
        if source.suffix.lower() == ".pdf":
            return "pdf"

        return "image"