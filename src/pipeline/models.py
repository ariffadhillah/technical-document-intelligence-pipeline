from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.attachments.ocr.models import OCRPage
from src.attachments.vision.models import VisionAuditEntry
from src.attachments.vision.result import VisionProcessingResult


@dataclass(slots=True)
class PreparedPage:
    """
    One document page prepared as an image.

    For image inputs, there will normally be one page.
    For PDF inputs, each rendered PDF page becomes one
    PreparedPage.
    """

    page_number: int
    image_path: Path

    width: int | None = None
    height: int | None = None

    source_type: str = "image"
    image_type: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "image_path": str(self.image_path),
            "width": self.width,
            "height": self.height,
            "source_type": self.source_type,
            "image_type": self.image_type,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class DocumentPipelineResult:
    """
    Final result produced by DocumentIntelligencePipeline.
    """

    source_path: Path
    source_type: str

    pages: list[OCRPage] = field(
        default_factory=list
    )

    original_ocr_pages: list[OCRPage] = field(
        default_factory=list
    )

    vision_results: list[
        VisionProcessingResult
    ] = field(
        default_factory=list
    )

    audits: list[VisionAuditEntry] = field(
        default_factory=list
    )

    merged_text: str = ""

    total_pages: int = 0
    vision_pages: int = 0
    vision_cache_hits: int = 0
    vision_failures: int = 0

    processing_time: float = 0.0
    estimated_cost: float = 0.0

    output_directory: Path | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def success(self) -> bool:
        return self.vision_failures == 0

    @property
    def vision_usage_ratio(self) -> float:
        if self.total_pages <= 0:
            return 0.0

        return self.vision_pages / self.total_pages

    @property
    def average_confidence(self) -> float:
        confidences = [
            page.confidence
            for page in self.pages
            if page.confidence > 0.0
        ]

        if not confidences:
            return 0.0

        return sum(confidences) / len(confidences)

    @property
    def average_quality(self) -> float:
        scores = [
            page.quality_score
            for page in self.pages
            if page.quality_score > 0.0
        ]

        if not scores:
            return 0.0

        return sum(scores) / len(scores)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": str(self.source_path),
            "source_type": self.source_type,
            "success": self.success,
            "total_pages": self.total_pages,
            "vision_pages": self.vision_pages,
            "vision_cache_hits": (
                self.vision_cache_hits
            ),
            "vision_failures": self.vision_failures,
            "vision_usage_ratio": (
                self.vision_usage_ratio
            ),
            "average_confidence": (
                self.average_confidence
            ),
            "average_quality": (
                self.average_quality
            ),
            "processing_time": (
                self.processing_time
            ),
            "estimated_cost": self.estimated_cost,
            "output_directory": (
                str(self.output_directory)
                if self.output_directory is not None
                else None
            ),
            "merged_text": self.merged_text,
            "pages": [
                page.to_dict()
                for page in self.pages
            ],
            "original_ocr_pages": [
                page.to_dict()
                for page in self.original_ocr_pages
            ],
            "vision_results": [
                {
                    "success": item.success,
                    "from_cache": item.from_cache,
                    "error": item.error,
                    "text": item.text,
                    "decision": {
                        "page_number": (
                            item.decision.page_number
                        ),
                        "use_vision": (
                            item.decision.use_vision
                        ),
                        "provider": (
                            item.decision.provider
                        ),
                        "model": item.decision.model,
                        "priority": (
                            item.decision.priority.value
                        ),
                        "reasons": [
                            reason.value
                            for reason
                            in item.decision.reasons
                        ],
                        "quality_score": (
                            item.decision.score.quality_score
                            if item.decision.score
                            is not None
                            else None
                        ),
                    },
                    "metadata": item.metadata,
                }
                for item in self.vision_results
            ],
            "audits": [
                {
                    "page_number": audit.page_number,
                    "ocr_quality": audit.ocr_quality,
                    "ocr_confidence": (
                        audit.ocr_confidence
                    ),
                    "vision_used": audit.vision_used,
                    "vision_provider": (
                        audit.vision_provider
                    ),
                    "vision_model": (
                        audit.vision_model
                    ),
                    "cache_hit": audit.cache_hit,
                    "retry_count": audit.retry_count,
                    "processing_time": (
                        audit.processing_time
                    ),
                    "estimated_cost": (
                        audit.estimated_cost
                    ),
                    "final_quality": (
                        audit.final_quality
                    ),
                    "reasons": audit.reasons,
                    "metadata": audit.metadata,
                }
                for audit in self.audits
            ],
            "metadata": self.metadata,
        }