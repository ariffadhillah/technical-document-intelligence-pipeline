from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FinalDeliveryResult:
    document_id: str
    output_directory: Path
    archive_path: Path | None
    markdown_path: Path
    text_path: Path
    structured_path: Path
    attachment_catalog_path: Path
    rag_path: Path
    logbook_path: Path
    manifest_path: Path
    attachment_count: int
    rag_chunk_count: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key, value in payload.items():
            if isinstance(value, Path):
                payload[key] = str(value)
        return payload


class FinalDeliveryStageRunner:
    """
    Packages outputs already produced by the existing pipeline.

    This stage does not repeat OCR, Vision, AI extraction, rendering,
    or RAG chunking. It only assembles those outputs into the final
    client-delivery structure.
    """

    def __init__(
        self,
        output_directory: Path,
        *,
        create_zip: bool = True,
    ) -> None:
        self.output_directory = output_directory
        self.create_zip = create_zip
        self.output_directory.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        *,
        validated_document: Any,
        enriched_thread: dict[str, Any],
        aggregated_document: dict[str, Any],
        validated_response_path: Path,
        rendered_markdown_path: Path,
        rendered_text_path: Path,
        rendered_metadata_path: Path,
        rag_output_path: Path,
        provider_metadata_path: Path | None = None,
    ) -> FinalDeliveryResult:
        validated_payload = self._to_mapping(
            validated_document
        )

        document_id = str(
            validated_payload.get("document_id")
            or enriched_thread.get(
                "metadata",
                {},
            ).get("thread_id")
            or "unknown"
        )

        safe_document_id = self._safe_name(
            document_id
        )

        package_root = (
            self.output_directory
            / safe_document_id
        )

        # kode berikutnya tetap sama
        if package_root.exists():
            shutil.rmtree(package_root)

        documents_dir = package_root / "documents"
        catalogs_dir = package_root / "catalogs"
        reports_dir = package_root / "reports"
        rag_dir = package_root / "rag"
        logbooks_dir = package_root / "logbooks"

        for directory in (
            documents_dir,
            catalogs_dir,
            reports_dir,
            rag_dir,
            logbooks_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        markdown_path = documents_dir / f"{safe_document_id}.md"
        text_path = documents_dir / f"{safe_document_id}.txt"
        structured_path = (
            reports_dir / f"{safe_document_id}_structured.json"
        )
        rendered_metadata_target = (
            reports_dir / f"{safe_document_id}_metadata.json"
        )
        aggregated_target = (
            reports_dir / f"{safe_document_id}_aggregated.json"
        )
        attachment_catalog_path = (
            catalogs_dir / f"{safe_document_id}_attachments.json"
        )
        rag_path = rag_dir / f"{safe_document_id}.jsonl"

        shutil.copy2(rendered_markdown_path, markdown_path)
        shutil.copy2(rendered_text_path, text_path)
        shutil.copy2(validated_response_path, structured_path)
        shutil.copy2(rendered_metadata_path, rendered_metadata_target)
        shutil.copy2(rag_output_path, rag_path)

        self._write_json(
            aggregated_document,
            aggregated_target,
        )

        attachments = self._build_attachment_catalog(
            enriched_thread=enriched_thread,
        )
        self._write_json(
            attachments,
            attachment_catalog_path,
        )

        macro_domain = self._select_macro_domain(
            validated_payload
        )
        logbook_path = (
            logbooks_dir
            / f"{self._safe_name(macro_domain)}_master_logbook.md"
        )
        self._write_logbook(
            source_markdown_path=markdown_path,
            output_path=logbook_path,
            document_id=document_id,
            title=str(
                validated_payload.get("title")
                or document_id
            ),
            macro_domain=macro_domain,
        )

        rag_chunk_count = self._count_jsonl_records(rag_path)

        copied_files = [
            markdown_path,
            text_path,
            structured_path,
            rendered_metadata_target,
            aggregated_target,
            attachment_catalog_path,
            rag_path,
            logbook_path,
        ]

        if (
            provider_metadata_path is not None
            and provider_metadata_path.is_file()
        ):
            provider_target = (
                reports_dir / f"{safe_document_id}_provider_metadata.json"
            )
            shutil.copy2(
                provider_metadata_path,
                provider_target,
            )
            copied_files.append(provider_target)

        manifest_path = reports_dir / "delivery_manifest.json"
        manifest = {
            "document_id": document_id,
            "title": validated_payload.get("title"),
            "status": "ready_for_delivery",
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "macro_domain": macro_domain,
            "counts": {
                "posts": len(
                    enriched_thread.get("posts", [])
                ),
                "attachments": len(attachments),
                "organizations": len(
                    validated_payload.get(
                        "organizations",
                        [],
                    )
                ),
                "contacts": len(
                    validated_payload.get(
                        "contacts",
                        [],
                    )
                ),
                "technical_references": len(
                    validated_payload.get(
                        "technical_references",
                        [],
                    )
                ),
                "technical_specifications": len(
                    validated_payload.get(
                        "technical_specifications",
                        [],
                    )
                ),
                "rag_chunks": rag_chunk_count,
            },
            "files": [
                {
                    "path": str(
                        path.relative_to(package_root)
                    ).replace("\\", "/"),
                    "size_bytes": path.stat().st_size,
                    "sha256": self._sha256(path),
                }
                for path in copied_files
            ],
            "source_traceability": {
                "thread_id": (
                    enriched_thread
                    .get("metadata", {})
                    .get("thread_id")
                ),
                "source_url": (
                    validated_payload
                    .get("source", {})
                    .get("source_url")
                ),
                "forum_name": (
                    validated_payload
                    .get("source", {})
                    .get("forum_name")
                ),
                "attachment_catalog": str(
                    attachment_catalog_path.relative_to(
                        package_root
                    )
                ).replace("\\", "/"),
            },
        }
        self._write_json(manifest, manifest_path)

        self._write_readme(
            output_path=package_root / "README.md",
            document_id=document_id,
            title=str(
                validated_payload.get("title")
                or document_id
            ),
            macro_domain=macro_domain,
            attachment_count=len(attachments),
            rag_chunk_count=rag_chunk_count,
        )

        archive_path: Path | None = None
        if self.create_zip:
            archive_path = (
                self.output_directory
                / f"{safe_document_id}_final_delivery.zip"
            )
            self._create_zip(
                source_directory=package_root,
                output_path=archive_path,
            )

        return FinalDeliveryResult(
            document_id=document_id,
            output_directory=package_root,
            archive_path=archive_path,
            markdown_path=markdown_path,
            text_path=text_path,
            structured_path=structured_path,
            attachment_catalog_path=attachment_catalog_path,
            rag_path=rag_path,
            logbook_path=logbook_path,
            manifest_path=manifest_path,
            attachment_count=len(attachments),
            rag_chunk_count=rag_chunk_count,
        )

    @staticmethod
    def _to_mapping(
        value: Any,
    ) -> dict[str, Any]:
        if isinstance(value, dict):
            return value

        model_dump = getattr(
            value,
            "model_dump",
            None,
        )
        if callable(model_dump):
            payload = model_dump(
                mode="json"
            )
            if isinstance(payload, dict):
                return payload

        legacy_dict = getattr(
            value,
            "dict",
            None,
        )
        if callable(legacy_dict):
            payload = legacy_dict()
            if isinstance(payload, dict):
                return payload

        raise TypeError(
            "validated_document must be a mapping "
            "or a supported Pydantic model"
        )


    @staticmethod
    def _build_attachment_catalog(
        *,
        enriched_thread: dict[str, Any],
    ) -> list[dict[str, Any]]:
        thread_id = (
            enriched_thread
            .get("metadata", {})
            .get("thread_id")
        )
        records: list[dict[str, Any]] = []

        for post in enriched_thread.get("posts", []):
            post_id = post.get("post_id")

            for attachment in post.get("attachments", []):
                intelligence = attachment.get(
                    "document_intelligence",
                    {},
                )
                analysis = intelligence.get(
                    "document_analysis",
                    {},
                )

                records.append(
                    {
                        "thread_id": str(thread_id),
                        "post_id": str(post_id),
                        "kind": (
                            attachment.get("kind")
                            or attachment.get("type")
                        ),
                        "original_name": attachment.get(
                            "original_name"
                        ),
                        "stored_name": attachment.get(
                            "stored_name"
                        ),
                        "relative_path": attachment.get(
                            "relative_path"
                        ),
                        "local_path": attachment.get(
                            "local_path"
                        ),
                        "source_url": attachment.get(
                            "source_url"
                        ),
                        "content_type": attachment.get(
                            "content_type"
                        ),
                        "size_bytes": attachment.get(
                            "size_bytes"
                        ),
                        "sha256": attachment.get("sha256"),
                        "file_status": attachment.get(
                            "file_status"
                        ),
                        "extraction_method": attachment.get(
                            "extraction_method"
                        ),
                        "processing_status": attachment.get(
                            "processing_status"
                        ),
                        "processing_error": attachment.get(
                            "processing_error"
                        ),
                        "extracted_character_count": len(
                            attachment.get(
                                "extracted_text",
                                "",
                            )
                            or ""
                        ),
                        "document_type": analysis.get(
                            "document_type"
                        ),
                        "detected_language": analysis.get(
                            "detected_language"
                        ),
                        "total_pages": intelligence.get(
                            "total_pages"
                        ),
                        "vision_pages": intelligence.get(
                            "vision_pages"
                        ),
                        "vision_failures": intelligence.get(
                            "vision_failures"
                        ),
                        "average_confidence": (
                            intelligence.get(
                                "average_confidence"
                            )
                        ),
                        "average_quality": intelligence.get(
                            "average_quality"
                        ),
                        "document_pipeline_output": (
                            intelligence.get(
                                "output_directory"
                            )
                        ),
                    }
                )

        return records

    @staticmethod
    def _select_macro_domain(
        document: dict[str, Any],
    ) -> str:
        categories = document.get(
            "system_categories",
            [],
        )
        if categories:
            return str(categories[0])

        topics = document.get("topics", [])
        if topics:
            return str(topics[0])

        return "technical_intelligence"

    @staticmethod
    def _write_logbook(
        *,
        source_markdown_path: Path,
        output_path: Path,
        document_id: str,
        title: str,
        macro_domain: str,
    ) -> None:
        markdown = source_markdown_path.read_text(
            encoding="utf-8"
        )

        # Remove an existing YAML block so the logbook has one
        # authoritative metadata block.
        markdown_body = re.sub(
            r"\A---\s*\n.*?\n---\s*\n",
            "",
            markdown,
            count=1,
            flags=re.DOTALL,
        ).strip()

        logbook = "\n".join(
            [
                "---",
                (
                    f'logbook_id: "'
                    f'{FinalDeliveryStageRunner._safe_name(macro_domain)}'
                    f'_master_logbook"'
                ),
                f'domain: "{macro_domain}"',
                "source_document_count: 1",
                f'generated_from: "{document_id}"',
                "rag_ready: true",
                "---",
                "",
                f"# {document_id} — {title}",
                "",
                markdown_body,
                "",
            ]
        )

        output_path.write_text(
            logbook,
            encoding="utf-8",
        )

    @staticmethod
    def _write_readme(
        *,
        output_path: Path,
        document_id: str,
        title: str,
        macro_domain: str,
        attachment_count: int,
        rag_chunk_count: int,
    ) -> None:
        content = f"""# Final Delivery — {title}

This package was generated automatically by the terminal pipeline.

## Document

- Document ID: `{document_id}`
- Macro domain: `{macro_domain}`
- Attachments cataloged: {attachment_count}
- RAG chunks: {rag_chunk_count}

## Output structure

- `documents/`: final Markdown and plain-text documents.
- `catalogs/`: attachment provenance and extraction catalog.
- `reports/`: validated structured data, metadata, aggregation source,
  provider metadata when available, and delivery manifest.
- `rag/`: standalone JSONL chunks.
- `logbooks/`: H1-bounded macro-domain master logbook.

All final files are derived from the existing OCR/Vision, aggregation,
AI validation, rendering, and RAG stages.
"""
        output_path.write_text(
            content,
            encoding="utf-8",
        )

    @staticmethod
    def _write_json(
        payload: Any,
        output_path: Path,
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

    @staticmethod
    def _count_jsonl_records(path: Path) -> int:
        with path.open("r", encoding="utf-8") as handle:
            return sum(
                1
                for line in handle
                if line.strip()
            )

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(
                lambda: handle.read(1024 * 1024),
                b"",
            ):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _safe_name(value: str) -> str:
        normalized = re.sub(
            r"[^A-Za-z0-9._-]+",
            "_",
            str(value).strip(),
        )
        return normalized.strip("._") or "unknown"

    @staticmethod
    def _create_zip(
        *,
        source_directory: Path,
        output_path: Path,
    ) -> None:
        temporary_path = output_path.with_suffix(
            output_path.suffix + ".tmp"
        )

        with zipfile.ZipFile(
            temporary_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for file_path in sorted(
                source_directory.rglob("*")
            ):
                if file_path.is_file():
                    archive.write(
                        file_path,
                        file_path.relative_to(
                            source_directory.parent
                        ),
                    )

        temporary_path.replace(output_path)
