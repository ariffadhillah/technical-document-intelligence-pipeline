from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.attachments.image_ocr_processor import process_image
from src.attachments.ocr_engine import (
    configure_tesseract,
    get_available_languages,
    select_ocr_language,
)
from src.attachments.pdf_extractor import extract_pdf
from src.pipeline import DocumentIntelligencePipeline


@dataclass
class AttachmentProcessingStats:
    total: int = 0
    images: int = 0
    pdfs: int = 0
    documents: int = 0
    completed: int = 0
    empty: int = 0
    skipped: int = 0
    failed: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


class AttachmentProcessor:
    """
    Memproses seluruh attachment dalam satu thread.

    Image:
        Pillow validation -> preprocessing -> Tesseract OCR

    PDF:
        pypdf text extraction

    Hasil ekstraksi disematkan kembali ke attachment asal.
    """

    def __init__(
        self,
        ocr_output_directory: Path,
        pdf_output_directory: Path,
        document_pipeline: DocumentIntelligencePipeline | None = None,
    ) -> None:
        self.ocr_output_directory = ocr_output_directory
        self.pdf_output_directory = pdf_output_directory
        self.document_pipeline = document_pipeline

        self.ocr_output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.pdf_output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._ocr_language: str | None = None

    def process_thread(
        self,
        thread_data: dict[str, Any],
    ) -> tuple[dict[str, Any], AttachmentProcessingStats]:
        """
        Memproses seluruh attachment dari seluruh post.
        """
        stats = AttachmentProcessingStats()

        metadata = thread_data.setdefault("metadata", {})
        thread_id = metadata.get("thread_id", "unknown")

        for post in thread_data.get("posts", []):
            post_id = str(post.get("post_id", "unknown"))

            processed_attachments = []

            for attachment in post.get("attachments", []):
                stats.total += 1

                processed_attachment = self.process_attachment(
                    attachment=attachment,
                    thread_id=thread_id,
                    post_id=post_id,
                    stats=stats,
                )

                processed_attachments.append(
                    processed_attachment
                )

            post["attachments"] = processed_attachments

        metadata["processing_status"] = (
            "attachments_processed"
        )
        metadata["attachment_processing"] = stats.to_dict()

        return thread_data, stats

    def process_attachment(
        self,
        attachment: dict[str, Any],
        thread_id: int | str,
        post_id: str,
        stats: AttachmentProcessingStats,
    ) -> dict[str, Any]:
        """
        Memproses satu attachment dan mempertahankan metadata aslinya.
        """
        enriched_attachment = attachment.copy()

        local_path_value = attachment.get("local_path")

        if not local_path_value:
            enriched_attachment["processing_status"] = (
                "attachment_missing"
            )
            enriched_attachment["processing_error"] = (
                "local_path is empty"
            )
            stats.failed += 1
            return enriched_attachment

        local_path = Path(local_path_value)

        if not local_path.is_file():
            enriched_attachment["processing_status"] = (
                "attachment_missing"
            )
            enriched_attachment["processing_error"] = (
                f"File not found: {local_path}"
            )
            stats.failed += 1
            return enriched_attachment

        attachment_type = (
            attachment.get("kind")
            or attachment.get("type")
            or "document"
        ).lower()

        try:
            if attachment_type == "image":
                stats.images += 1

                return self._process_image_attachment(
                    attachment=enriched_attachment,
                    image_path=local_path,
                    thread_id=thread_id,
                    post_id=post_id,
                    stats=stats,
                )

            if attachment_type == "pdf":
                stats.pdfs += 1

                return self._process_pdf_attachment(
                    attachment=enriched_attachment,
                    pdf_path=local_path,
                    thread_id=thread_id,
                    post_id=post_id,
                    stats=stats,
                )

            stats.documents += 1
            stats.skipped += 1

            enriched_attachment["processing_status"] = (
                "unsupported_document"
            )
            enriched_attachment["processing_error"] = None

            return enriched_attachment

        except Exception as error:
            stats.failed += 1

            enriched_attachment["processing_status"] = (
                "attachment_processing_failed"
            )
            enriched_attachment["processing_error"] = str(error)

            return enriched_attachment

    def _process_with_document_pipeline(
        self,
        attachment: dict[str, Any],
        source_path: Path,
        thread_id: int | str,
        post_id: str,
        stats: AttachmentProcessingStats,
    ) -> dict[str, Any]:
        """
        Jalankan PDF/image melalui DocumentIntelligencePipeline yang
        sama dengan scripts.run_document_pipeline.

        `result.merged_text` ditempatkan ke `extracted_text`, yaitu
        field yang sudah dikonsumsi ContentAggregator. Dengan begitu
        seluruh hasil OCR atau Vision mengalir ke AI extraction,
        renderer, dan RAG tanpa mengubah tahap-tahap tersebut.
        """
        if self.document_pipeline is None:
            raise RuntimeError(
                "DocumentIntelligencePipeline is not configured"
            )

        language = self._get_ocr_language()

        output_directory = (
            self.document_pipeline.output_root
            / f"thread_{thread_id}"
            / f"post_{post_id}"
            / source_path.stem
        )

        result = self.document_pipeline.process(
            source_path,
            output_dir=output_directory,
            language=language,
            force_vision=False,
            write_outputs=True,
        )

        extracted_text = result.merged_text.strip()
        analysis = result.metadata.get(
            "document_analysis",
            {},
        )

        attachment["extracted_text"] = extracted_text
        attachment["extraction_method"] = (
            "document_intelligence_pipeline"
        )
        attachment["processing_status"] = (
            "document_pipeline_completed"
            if extracted_text
            else "document_pipeline_empty"
        )
        attachment["processing_error"] = None

        attachment["document_intelligence"] = {
            "success": result.success,
            "source_type": result.source_type,
            "total_pages": result.total_pages,
            "vision_pages": result.vision_pages,
            "vision_cache_hits": result.vision_cache_hits,
            "vision_failures": result.vision_failures,
            "vision_usage_ratio": result.vision_usage_ratio,
            "average_confidence": result.average_confidence,
            "average_quality": result.average_quality,
            "processing_time": result.processing_time,
            "estimated_cost": result.estimated_cost,
            "output_directory": (
                str(result.output_directory)
                if result.output_directory is not None
                else None
            ),
            "document_analysis": analysis,
            "pages": [page.to_dict() for page in result.pages],
            "vision_results": [
                {
                    "success": item.success,
                    "from_cache": item.from_cache,
                    "error": item.error,
                    "text": item.text,
                    "provider": item.decision.provider,
                    "model": item.decision.model,
                    "reasons": [
                        reason.value
                        for reason in item.decision.reasons
                    ],
                    "metadata": item.metadata,
                }
                for item in result.vision_results
            ],
        }

        if result.source_type == "image":
            attachment["ocr"] = {
                "engine": (
                    result.pages[0].engine_name
                    if result.pages
                    else "document_intelligence_pipeline"
                ),
                "language": analysis.get(
                    "detected_language",
                    language,
                ),
                "confidence": result.average_confidence,
                "character_count": len(extracted_text),
                "word_count": len(extracted_text.split()),
                "has_extracted_text": bool(extracted_text),
                "processing_status": attachment[
                    "processing_status"
                ],
                "raw_text": extracted_text,
                "result_path": (
                    str(result.output_directory)
                    if result.output_directory is not None
                    else None
                ),
                "vision_used": result.vision_pages > 0,
            }

        if result.source_type == "pdf":
            attachment["pdf_extraction"] = {
                "page_count": result.total_pages,
                "successful_pages": sum(
                    1 for page in result.pages if page.text.strip()
                ),
                "empty_pages": sum(
                    1 for page in result.pages if not page.text.strip()
                ),
                "character_count": len(extracted_text),
                "classification": analysis.get(
                    "document_type",
                    "unknown",
                ),
                "requires_ocr": True,
                "processing_status": attachment[
                    "processing_status"
                ],
                "pages": [
                    page.to_dict() for page in result.pages
                ],
                "raw_text": extracted_text,
                "result_path": (
                    str(result.output_directory)
                    if result.output_directory is not None
                    else None
                ),
                "vision_used": result.vision_pages > 0,
            }

        if extracted_text:
            stats.completed += 1
        else:
            stats.empty += 1

        return attachment

    def _process_image_attachment(
        self,
        attachment: dict[str, Any],
        image_path: Path,
        thread_id: int | str,
        post_id: str,
        stats: AttachmentProcessingStats,
    ) -> dict[str, Any]:
        """
        Menjalankan pipeline dokumen lengkap untuk satu image.

        Jika DocumentIntelligencePipeline belum dikonfigurasi,
        gunakan OCR lama sebagai fallback agar pipeline lama tetap aman.
        """
        if self.document_pipeline is not None:
            return self._process_with_document_pipeline(
                attachment=attachment,
                source_path=image_path,
                thread_id=thread_id,
                post_id=post_id,
                stats=stats,
            )

        language = self._get_ocr_language()

        output_directory = (
            self.ocr_output_directory
            / f"thread_{thread_id}"
            / f"post_{post_id}"
        )

        result = process_image(
            image_path=image_path,
            output_directory=output_directory,
            language=language,
        )

        attachment["ocr"] = {
            "engine": result.get("ocr_engine"),
            "language": result.get("ocr_language"),
            "confidence": result.get("ocr_confidence"),
            "character_count": result.get(
                "character_count",
                0,
            ),
            "word_count": result.get("word_count", 0),
            "has_extracted_text": result.get(
                "has_extracted_text",
                False,
            ),
            "processing_status": result.get(
                "processing_status"
            ),
            "raw_text": result.get("extracted_text", ""),
            "result_path": str(
                output_directory
                / f"{image_path.stem}_ocr.json"
            ),
        }

        attachment["extracted_text"] = result.get(
            "extracted_text",
            "",
        )
        attachment["extraction_method"] = "tesseract_ocr"
        attachment["processing_status"] = result.get(
            "processing_status",
            "ocr_completed",
        )
        attachment["processing_error"] = None

        if result.get("has_extracted_text"):
            stats.completed += 1
        else:
            stats.empty += 1

        return attachment

    def _process_pdf_attachment(
        self,
        attachment: dict[str, Any],
        pdf_path: Path,
        thread_id: int | str,
        post_id: str,
        stats: AttachmentProcessingStats,
    ) -> dict[str, Any]:
        """
        Menjalankan pipeline dokumen lengkap untuk satu PDF.

        Jika DocumentIntelligencePipeline belum dikonfigurasi,
        gunakan ekstraksi pypdf lama sebagai fallback.
        """
        if self.document_pipeline is not None:
            return self._process_with_document_pipeline(
                attachment=attachment,
                source_path=pdf_path,
                thread_id=thread_id,
                post_id=post_id,
                stats=stats,
            )

        result = extract_pdf(pdf_path)

        output_directory = (
            self.pdf_output_directory
            / f"thread_{thread_id}"
            / f"post_{post_id}"
        )
        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = (
            output_directory
            / f"{pdf_path.stem}_pdf.json"
        )

        self._save_json(
            payload=result,
            output_path=output_path,
        )

        attachment["pdf_extraction"] = {
            "page_count": result.get("page_count", 0),
            "successful_pages": result.get(
                "successful_pages",
                0,
            ),
            "empty_pages": result.get("empty_pages", 0),
            "character_count": result.get(
                "character_count",
                0,
            ),
            "classification": result.get(
                "pdf_classification"
            ),
            "requires_ocr": result.get(
                "requires_ocr",
                False,
            ),
            "processing_status": result.get(
                "processing_status"
            ),
            "pages": result.get("pages", []),
            "raw_text": result.get("full_text", ""),
            "result_path": str(output_path),
        }

        attachment["extracted_text"] = result.get(
            "full_text",
            "",
        )
        attachment["extraction_method"] = (
            "pypdf_text_extraction"
        )
        attachment["processing_status"] = (
            result.get(
                "processing_status",
                "pdf_text_extracted",
            )
        )
        attachment["processing_error"] = None

        if result.get("full_text"):
            stats.completed += 1
        else:
            stats.empty += 1

        return attachment

    def _get_ocr_language(self) -> str:
        """
        Mengonfigurasi Tesseract hanya satu kali untuk satu pipeline run.
        """
        if self._ocr_language is not None:
            return self._ocr_language

        configure_tesseract()

        available_languages = get_available_languages()

        self._ocr_language = select_ocr_language(
            available_languages
        )

        print(
            "    OCR language : "
            f"{self._ocr_language}"
        )

        return self._ocr_language

    @staticmethod
    def _save_json(
        payload: dict[str, Any],
        output_path: Path,
    ) -> None:
        import json

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