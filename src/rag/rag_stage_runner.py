from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.rag.chunk_builder import RAGChunkBuilder
from src.schemas.technical_knowledge import (
    StructuredTechnicalDocument,
)


@dataclass(frozen=True)
class RAGStageResult:
    document_id: str
    output_path: str
    chunk_count: int
    status: str = "success"

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "output_path": self.output_path,
            "chunk_count": self.chunk_count,
            "status": self.status,
        }


class RAGStageRunner:
    """Build and persist provenance-aware JSONL chunks."""

    def __init__(
        self,
        *,
        output_directory: Path,
        max_chars: int = 1800,
        overlap_chars: int = 180,
    ) -> None:
        self.output_directory = output_directory.resolve()
        self.chunk_builder = RAGChunkBuilder(
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        )

    def run(
        self,
        *,
        document: StructuredTechnicalDocument,
    ) -> RAGStageResult:
        chunks = self.chunk_builder.build(document)

        output_path = (
            self.output_directory
            / f"{document.document_id}.jsonl"
        )
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = output_path.with_suffix(
            output_path.suffix + ".tmp"
        )
        temporary_path.write_text(
            "".join(
                json.dumps(
                    chunk,
                    ensure_ascii=False,
                )
                + "\n"
                for chunk in chunks
            ),
            encoding="utf-8",
        )
        temporary_path.replace(output_path)

        return RAGStageResult(
            document_id=document.document_id,
            output_path=str(output_path),
            chunk_count=len(chunks),
        )
