import logging
import time
from pathlib import Path
from typing import Mapping

import cv2
import numpy as np

from .analyzer import (
    DocumentAnalysis,
    DocumentAnalyzer,
)

from src.attachments.image.orientation import (
    ImageOrientationCorrector,
)
from src.attachments.ocr import (
    BaseOCREngine,
    TesseractOCREngine,
)
from src.attachments.ocr.models import OCRPage
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
from .ocr_runner import OCRRunner
from .output_writer import PipelineOutputWriter
from .page_preprocessor import PagePreprocessor

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
        Page preprocessing
            ↓
        OCR
            ↓
        Vision routing and fallback
            ↓
        Final document result
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
        SUPPORTED_IMAGE_EXTENSIONS
        | {".pdf"}
    )

    def __init__(
        self,
        *,
        ocr_engine: BaseOCREngine | None = None,
        vision_engine: BaseVisionEngine | None = None,
        pdf_renderer: PDFRenderer | None = None,
        vision_router: VisionRouter | None = None,
        document_analyzer: DocumentAnalyzer | None = None,
        use_analyzer_vision_recommendation: bool = False,
        vision_processor: (
            VisionFallbackProcessor | None
        ) = None,
        page_preprocessor: (
            PagePreprocessor | None
        ) = None,
        ocr_runner: OCRRunner | None = None,
        output_writer: (
            PipelineOutputWriter | None
        ) = None,
        output_root: str | Path = (
            "output/document_pipeline"
        ),
        render_dpi: int = 400,
        use_ocr_cache: bool = True,
        use_vision_cache: bool = True,
        vision_threshold: float = 0.60,
        enable_orientation_correction: (
            bool
        ) = True,
        orientation_minimum_confidence: (
            float
        ) = 1.0,
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

        self.document_analyzer = (
            document_analyzer
            or DocumentAnalyzer()
        )

        self.use_analyzer_vision_recommendation = (
            use_analyzer_vision_recommendation
        )

        self.vision_engine = (
            vision_engine
            or MockVisionEngine()
        )

        self.pdf_renderer = (
            pdf_renderer
            or PDFRenderer()
        )

        self.page_preprocessor = (
            page_preprocessor
            or self._build_page_preprocessor(
                enabled=(
                    enable_orientation_correction
                ),
                minimum_confidence=(
                    orientation_minimum_confidence
                ),
            )
        )

        self.ocr_runner = (
            ocr_runner
            or OCRRunner(
                engine=self.ocr_engine
            )
        )

        self.vision_router = (
            vision_router
            or self._build_vision_router(
                vision_threshold
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

        self.output_writer = (
            output_writer
            or PipelineOutputWriter()
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
        document intelligence pipeline.
        """

        started_at = time.perf_counter()

        source = (
            Path(source_path)
            .expanduser()
            .resolve()
        )

        self._validate_source(source)

        source_type = (
            self._detect_source_type(source)
        )

        document_output_dir = (
            self._resolve_output_directory(
                source=source,
                output_dir=output_dir,
            )
        )

        logger.info(
            "Starting document pipeline: "
            "source=%s type=%s",
            source,
            source_type,
        )

        prepared_pages, original_images = (
            self._prepare_pages(
                source=source,
                source_type=source_type,
                output_dir=(
                    document_output_dir
                ),
            )
        )

        preprocessing_result = (
            self.page_preprocessor
            .process_pages(
                prepared_pages=prepared_pages,
                images=original_images,
            )
        )

        processed_images = (
            preprocessing_result.images
        )

        original_ocr_pages = (
            self.ocr_runner.run(
                prepared_pages=prepared_pages,
                images=processed_images,
                language=language,
                preprocessing_metadata=(
                    preprocessing_result
                    .metadata_by_page
                ),
            )
        )

        document_analysis = (
            self.document_analyzer.analyze(
                original_ocr_pages
            )
        )

        force_pages = (
            self._resolve_force_pages(
                original_ocr_pages=(
                    original_ocr_pages
                ),
                force_vision=force_vision,
                force_vision_pages=(
                    force_vision_pages
                ),
                analyzer_vision_pages=(
                    document_analysis.vision_pages
                ),
                use_analyzer_recommendation=(
                    self.use_analyzer_vision_recommendation
                ),
            )
        )

        vision_batch = (
            self.vision_processor.process_pages(
                pages=original_ocr_pages,
                images=processed_images,
                image_types=dict(
                    image_types or {}
                ),
                force_pages=force_pages,
            )
        )

        final_pages = sorted(
            vision_batch.pages,
            key=lambda page: page.page_number,
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
            merged_text=self._merge_pages(
                final_pages
            ),
            total_pages=(
                vision_batch.total_pages
            ),
            vision_pages=(
                vision_batch.vision_pages
            ),
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
            metadata=self._build_metadata(
                document_analysis=document_analysis,
                prepared_pages=prepared_pages,
                preprocessing_metadata=(
                    preprocessing_result
                    .metadata_by_page
                ),
                force_vision=force_vision,
                force_pages=force_pages,
            ),
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
        self.output_writer.write(result)

    def _build_page_preprocessor(
        self,
        *,
        enabled: bool,
        minimum_confidence: float,
    ) -> PagePreprocessor:
        if not enabled:
            logger.info(
                "Image orientation correction "
                "is disabled."
            )

            return PagePreprocessor()

        pytesseract_module = getattr(
            self.ocr_engine,
            "pytesseract",
            None,
        )

        if pytesseract_module is None:
            logger.warning(
                "OCR engine does not expose "
                "pytesseract; orientation "
                "correction is disabled."
            )

            return PagePreprocessor()

        orientation_corrector = (
            ImageOrientationCorrector(
                pytesseract_module=(
                    pytesseract_module
                ),
                minimum_confidence=(
                    minimum_confidence
                ),
                fail_open=True,
            )
        )

        return PagePreprocessor(
            orientation_corrector=(
                orientation_corrector
            )
        )

    def _build_vision_router(
        self,
        vision_threshold: float,
    ) -> VisionRouter:
        return VisionRouter(
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

        images: dict[
            int,
            np.ndarray,
        ] = {}

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
                "PDF produced no rendered pages: "
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

    def _resolve_output_directory(
        self,
        *,
        source: Path,
        output_dir: str | Path | None,
    ) -> Path:
        resolved_output_dir = (
            Path(output_dir)
            .expanduser()
            .resolve()
            if output_dir is not None
            else self._build_output_directory(
                source
            )
        )

        resolved_output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        return resolved_output_dir

    @staticmethod
    def _resolve_force_pages(
        *,
        original_ocr_pages: list[OCRPage],
        force_vision: bool,
        force_vision_pages: set[int] | None,
        analyzer_vision_pages: list[int],
        use_analyzer_recommendation: bool,
    ) -> set[int]:
        force_pages = set(
            force_vision_pages or set()
        )

        if force_vision:
            force_pages.update(
                page.page_number
                for page in original_ocr_pages
            )

        if use_analyzer_recommendation:
            force_pages.update(
                analyzer_vision_pages
            )

        return force_pages

    def _build_metadata(
        self,
        *,
        prepared_pages: list[PreparedPage],
        preprocessing_metadata: Mapping[
            int,
            dict,
        ],
        document_analysis: DocumentAnalysis,
        force_vision: bool,
        force_pages: set[int],
    ) -> dict:
        return {
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
            "analyzer_vision_routing_enabled": (
                self.use_analyzer_vision_recommendation
            ),
            "document_analysis": (
                document_analysis.to_dict()
            ),
            "prepared_pages": [
                page.to_dict()
                for page in prepared_pages
            ],
            "preprocessing": {
                str(page_number): metadata
                for (
                    page_number,
                    metadata,
                ) in (
                    preprocessing_metadata.items()
                )
            },
        }

    @staticmethod
    def _load_image(
        path: Path,
    ) -> np.ndarray:
        """
        Load images safely on Windows, including paths
        containing non-ASCII characters.
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
        pages: list[OCRPage],
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

        return (
            normalized.strip("_")
            or "document"
        )

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
                "Document path is not a file: "
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
                "Unsupported document type: "
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