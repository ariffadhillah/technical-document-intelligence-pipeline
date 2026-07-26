from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.renderers.markdown_renderer import MarkdownRenderer
from src.renderers.metadata_renderer import MetadataRenderer
from src.renderers.text_renderer import TextRenderer
from src.schemas.technical_knowledge import (
    StructuredTechnicalDocument,
)


@dataclass(frozen=True)
class RenderingStageResult:
    document_id: str
    output_directory: str
    markdown_path: str
    text_path: str
    metadata_path: str
    status: str = "success"

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "output_directory": self.output_directory,
            "markdown_path": self.markdown_path,
            "text_path": self.text_path,
            "metadata_path": self.metadata_path,
            "status": self.status,
        }


class RenderingStageRunner:
    """Render one validated AI document into client-facing files."""

    def __init__(
        self,
        *,
        output_directory: Path,
    ) -> None:
        self.output_directory = output_directory.resolve()
        self.markdown_renderer = MarkdownRenderer()
        self.text_renderer = TextRenderer()
        self.metadata_renderer = MetadataRenderer()

    def run(
        self,
        *,
        document: StructuredTechnicalDocument,
    ) -> RenderingStageResult:
        if not document.processing.ready_for_rendering:
            raise ValueError(
                f"{document.document_id} is not ready for rendering."
            )

        target_directory = (
            self.output_directory / document.document_id
        )
        target_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        markdown_path = (
            target_directory
            / f"{document.document_id}.md"
        )
        text_path = (
            target_directory
            / f"{document.document_id}.txt"
        )
        metadata_path = (
            target_directory
            / "metadata.json"
        )

        self._atomic_write_text(
            markdown_path,
            self.markdown_renderer.render(document),
        )
        self._atomic_write_text(
            text_path,
            self.text_renderer.render(document),
        )
        self._atomic_write_json(
            metadata_path,
            self.metadata_renderer.render(document),
        )

        return RenderingStageResult(
            document_id=document.document_id,
            output_directory=str(target_directory),
            markdown_path=str(markdown_path),
            text_path=str(text_path),
            metadata_path=str(metadata_path),
        )

    @staticmethod
    def load_validated_document(
        validated_response_path: Path,
    ) -> StructuredTechnicalDocument:
        return StructuredTechnicalDocument.model_validate_json(
            validated_response_path.read_text(
                encoding="utf-8"
            )
        )

    @staticmethod
    def _atomic_write_text(
        output_path: Path,
        content: str,
    ) -> None:
        temporary_path = output_path.with_suffix(
            output_path.suffix + ".tmp"
        )
        temporary_path.write_text(
            content,
            encoding="utf-8",
        )
        temporary_path.replace(output_path)

    @staticmethod
    def _atomic_write_json(
        output_path: Path,
        payload: dict[str, Any],
    ) -> None:
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
