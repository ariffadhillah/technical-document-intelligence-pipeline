from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any

from .models import VisionAuditEntry


@dataclass(slots=True)
class VisionBenchmarkSummary:
    """
    Summary of OCR and Vision performance.
    """

    total_pages: int = 0

    vision_pages: int = 0

    cache_hits: int = 0

    failed_pages: int = 0

    average_ocr_quality: float = 0.0

    average_final_quality: float = 0.0

    quality_improvement: float = 0.0

    vision_usage_ratio: float = 0.0

    total_processing_time: float = 0.0

    total_estimated_cost: float = 0.0

    provider_usage: dict[str, int] = field(
        default_factory=dict
    )


class VisionBenchmark:
    """
    Generate benchmark statistics from page audit entries.
    """

    def summarize(
        self,
        audits: list[VisionAuditEntry],
    ) -> VisionBenchmarkSummary:
        if not audits:
            return VisionBenchmarkSummary()

        total_pages = len(audits)

        vision_pages = sum(
            1
            for audit in audits
            if audit.vision_used
        )

        cache_hits = sum(
            1
            for audit in audits
            if audit.cache_hit
        )

        failed_pages = sum(
            1
            for audit in audits
            if (
                audit.vision_used
                and audit.final_quality is None
            )
        )

        ocr_scores = [
            audit.ocr_quality
            for audit in audits
        ]

        final_scores = [
            (
                audit.final_quality
                if audit.final_quality is not None
                else audit.ocr_quality
            )
            for audit in audits
        ]

        average_ocr_quality = mean(ocr_scores)

        average_final_quality = mean(final_scores)

        provider_usage: dict[str, int] = {}

        for audit in audits:
            if not audit.vision_provider:
                continue

            provider_usage[audit.vision_provider] = (
                provider_usage.get(
                    audit.vision_provider,
                    0,
                )
                + 1
            )

        return VisionBenchmarkSummary(
            total_pages=total_pages,
            vision_pages=vision_pages,
            cache_hits=cache_hits,
            failed_pages=failed_pages,
            average_ocr_quality=average_ocr_quality,
            average_final_quality=average_final_quality,
            quality_improvement=(
                average_final_quality
                - average_ocr_quality
            ),
            vision_usage_ratio=(
                vision_pages / total_pages
            ),
            total_processing_time=sum(
                audit.processing_time
                for audit in audits
            ),
            total_estimated_cost=sum(
                audit.estimated_cost or 0.0
                for audit in audits
            ),
            provider_usage=provider_usage,
        )

    def export_json(
        self,
        audits: list[VisionAuditEntry],
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        summary = self.summarize(audits)

        payload: dict[str, Any] = {
            "summary": asdict(summary),
            "pages": [
                asdict(audit)
                for audit in audits
            ],
        }

        path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        return path

    def export_csv(
        self,
        audits: list[VisionAuditEntry],
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fieldnames = [
            "page_number",
            "ocr_quality",
            "ocr_confidence",
            "vision_used",
            "vision_provider",
            "vision_model",
            "cache_hit",
            "retry_count",
            "processing_time",
            "estimated_cost",
            "final_quality",
            "reasons",
        ]

        with path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            for audit in audits:
                writer.writerow(
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
                        "vision_model": audit.vision_model,
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
                        "reasons": "|".join(
                            audit.reasons
                        ),
                    }
                )

        return path