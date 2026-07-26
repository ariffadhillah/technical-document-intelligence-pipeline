from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .models import DocumentPipelineResult

logger = logging.getLogger(__name__)


class PipelineOutputWriter:
    """
    Write standard document pipeline artifacts.
    """

    def write(
        self,
        result: DocumentPipelineResult,
    ) -> None:
        output_dir = self._resolve_output_dir(
            result
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._write_json(
            output_dir / "result.json",
            result.to_dict(),
        )

        self._write_json(
            output_dir / "summary.json",
            self._build_summary(result),
        )

        self._write_text(
            output_dir / "final_text.md",
            result.merged_text,
        )

        logger.info(
            "Pipeline outputs written to %s",
            output_dir,
        )

    @staticmethod
    def _resolve_output_dir(
        result: DocumentPipelineResult,
    ) -> Path:
        if result.output_directory is None:
            raise ValueError(
                "Result output_directory is not set."
            )

        return result.output_directory

    @staticmethod
    def _build_summary(
        result: DocumentPipelineResult,
    ) -> dict[str, Any]:
        return {
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

    @staticmethod
    def _write_json(
        path: Path,
        payload: dict[str, Any],
    ) -> None:
        path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _write_text(
        path: Path,
        content: str,
    ) -> None:
        path.write_text(
            content,
            encoding="utf-8",
        )