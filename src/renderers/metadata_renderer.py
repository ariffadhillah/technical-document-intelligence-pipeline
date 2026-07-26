from __future__ import annotations

from typing import Any

from src.schemas.technical_knowledge import (
    StructuredTechnicalDocument,
)


class MetadataRenderer:
    """Build compact metadata for downstream delivery and indexing."""

    def render(
        self,
        document: StructuredTechnicalDocument,
    ) -> dict[str, Any]:
        evidence_posts: set[str] = set()
        evidence_attachments: set[str] = set()
        evidence_urls: set[str] = set()

        for item in self._iter_evidence(document):
            if item.post_id:
                evidence_posts.add(item.post_id)
            if item.attachment_filename:
                evidence_attachments.add(
                    item.attachment_filename
                )
            if item.source_url:
                evidence_urls.add(item.source_url)

        return {
            "document_id": document.document_id,
            "document_type": document.document_type,
            "title": document.title,
            "source_language": document.source_language,
            "output_language": document.output_language,
            "source": document.source.model_dump(mode="json"),
            "topics": document.topics,
            "system_categories": document.system_categories,
            "counts": {
                "entities": len(document.entities),
                "vehicles": len(document.vehicles),
                "engines": len(document.engines),
                "transmissions": len(document.transmissions),
                "technical_specifications": len(
                    document.technical_specifications
                ),
                "parts": len(document.parts),
                "maintenance_tasks": len(
                    document.maintenance_tasks
                ),
                "diagnostics": len(document.diagnostics),
                "organizations": len(document.organizations),
                "contacts": len(document.contacts),
                "technical_references": len(
                    document.technical_references
                ),
                "warnings": len(document.warnings),
                "recommendations": len(
                    document.recommendations
                ),
            },
            "provenance": {
                "post_ids": sorted(evidence_posts),
                "attachment_filenames": sorted(
                    evidence_attachments
                ),
                "source_urls": sorted(evidence_urls),
            },
            "translation_quality": (
                document.translation_quality.model_dump(
                    mode="json"
                )
            ),
            "processing": document.processing.model_dump(
                mode="json"
            ),
        }

    @staticmethod
    def _iter_evidence(
        document: StructuredTechnicalDocument,
    ):
        collections = [
            document.entities,
            document.vehicles,
            document.engines,
            document.transmissions,
            document.contacts,
            document.organizations,
            document.technical_specifications,
            document.parts,
            document.maintenance_tasks,
            document.diagnostics,
            document.warnings,
            document.technical_references,
        ]

        for collection in collections:
            for item in collection:
                for evidence in getattr(item, "evidence", []):
                    yield evidence

                for service in getattr(item, "services", []):
                    for evidence in getattr(service, "evidence", []):
                        yield evidence

                for relationship in getattr(
                    item,
                    "relationships",
                    [],
                ):
                    for evidence in getattr(
                        relationship,
                        "evidence",
                        [],
                    ):
                        yield evidence

                contact = getattr(item, "contact", None)
                if contact is not None:
                    for evidence in getattr(
                        contact,
                        "evidence",
                        [],
                    ):
                        yield evidence
