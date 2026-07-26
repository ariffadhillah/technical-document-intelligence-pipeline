from __future__ import annotations

import re
from typing import Any

from src.schemas.technical_knowledge import (
    StructuredTechnicalDocument,
)


class RAGChunkBuilder:
    """
    Build deterministic, provenance-aware chunks.

    Chunking is section based first and character bounded second.
    It does not split technical identifiers or structured records
    unless a section exceeds max_chars.
    """

    def __init__(
        self,
        *,
        max_chars: int = 1800,
        overlap_chars: int = 180,
    ) -> None:
        if max_chars < 300:
            raise ValueError("max_chars must be at least 300.")
        if overlap_chars < 0:
            raise ValueError(
                "overlap_chars cannot be negative."
            )
        if overlap_chars >= max_chars:
            raise ValueError(
                "overlap_chars must be smaller than max_chars."
            )

        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def build(
        self,
        document: StructuredTechnicalDocument,
    ) -> list[dict[str, Any]]:
        sections = self._build_sections(document)
        chunks: list[dict[str, Any]] = []
        sequence = 1

        for section_name, records in sections:
            for record in records:
                content = record["content"].strip()
                if not content:
                    continue

                for piece in self._split_text(content):
                    chunks.append(
                        {
                            "chunk_id": (
                                f"{document.document_id}-"
                                f"{sequence:04d}"
                            ),
                            "document_id": document.document_id,
                            "document_type": (
                                document.document_type
                            ),
                            "title": document.title,
                            "section": section_name,
                            "content": piece,
                            "source_language": (
                                document.source_language
                            ),
                            "output_language": (
                                document.output_language
                            ),
                            "topics": document.topics,
                            "system_categories": (
                                document.system_categories
                            ),
                            "source_post_ids": (
                                record["post_ids"]
                            ),
                            "attachment_filenames": (
                                record["attachments"]
                            ),
                            "source_urls": record["urls"],
                            "processing": {
                                "schema_version": (
                                    document.processing
                                    .schema_version
                                ),
                                "provider": (
                                    document.processing
                                    .extraction_provider
                                ),
                                "model": (
                                    document.processing
                                    .extraction_model
                                ),
                                "generated_at": (
                                    document.processing
                                    .generated_at
                                ),
                            },
                        }
                    )
                    sequence += 1

        return chunks

    def _build_sections(
        self,
        document: StructuredTechnicalDocument,
    ) -> list[tuple[str, list[dict[str, Any]]]]:
        sections: list[
            tuple[str, list[dict[str, Any]]]
        ] = [
            (
                "summary",
                [
                    self._record(
                        document.summary,
                        [],
                    )
                ],
            ),
            (
                "vehicles",
                [
                    self._model_record(
                        item,
                        (
                            f"Vehicle: {item.manufacturer or ''} "
                            f"{item.model} {item.variant or ''}. "
                            f"Year: {item.production_year}. "
                            f"Drive: {item.drive_configuration}. "
                            f"Type: {item.vehicle_type}. "
                            f"Gross weight: {item.gross_weight_kg} kg. "
                            f"Empty weight: {item.empty_weight_kg} kg."
                        ),
                    )
                    for item in document.vehicles
                ],
            ),
            (
                "engines",
                [
                    self._model_record(
                        item,
                        (
                            f"Engine: {item.manufacturer or ''} "
                            f"{item.model}. Type: {item.engine_type}. "
                            f"Cylinders: {item.cylinder_count}. "
                            f"Displacement: {item.displacement_cc} cc. "
                            f"Power: {item.power_hp} hp / "
                            f"{item.power_kw} kW. "
                            f"Fuel: {item.fuel_type}. "
                            f"Cooling: {item.cooling_type}."
                        ),
                    )
                    for item in document.engines
                ],
            ),
            (
                "transmissions",
                [
                    self._model_record(
                        item,
                        (
                            f"Transmission: "
                            f"{item.manufacturer or ''} "
                            f"{item.model}. "
                            f"Type: {item.transmission_type}. "
                            f"Gears: {item.gear_count}. "
                            f"Notes: {item.notes}."
                        ),
                    )
                    for item in document.transmissions
                ],
            ),
            (
                "technical_specifications",
                [
                    self._model_record(
                        item,
                        (
                            f"Technical specification "
                            f"[{item.category or 'General'}]: "
                            f"{item.name} = {item.value}"
                            f"{' ' + item.unit if item.unit else ''}."
                        ),
                    )
                    for item in document.technical_specifications
                ],
            ),
            (
                "parts",
                [
                    self._model_record(
                        item,
                        (
                            f"Part: {item.name}. "
                            f"Manufacturer: {item.manufacturer}. "
                            f"Part number: {item.part_number}. "
                            f"Alternative numbers: "
                            f"{', '.join(item.alternative_part_numbers)}. "
                            f"Description: {item.description}."
                        ),
                    )
                    for item in document.parts
                ],
            ),
            (
                "maintenance_tasks",
                [
                    self._model_record(
                        item,
                        (
                            f"Maintenance task: {item.title}. "
                            f"{item.description or ''} "
                            f"System: {item.system_category}. "
                            f"Action: {item.action_type}. "
                            f"Tools: {', '.join(item.tools)}. "
                            f"Parts: {', '.join(item.parts)}. "
                            f"Measurements: "
                            f"{', '.join(item.measurements)}. "
                            f"Warnings: {', '.join(item.warnings)}."
                        ),
                    )
                    for item in document.maintenance_tasks
                ],
            ),
            (
                "diagnostics",
                [
                    self._model_record(
                        item,
                        (
                            f"Diagnostic symptom: {item.symptom}. "
                            f"Possible causes: "
                            f"{'; '.join(item.possible_causes)}. "
                            f"Recommended actions: "
                            f"{'; '.join(item.recommended_actions)}."
                        ),
                    )
                    for item in document.diagnostics
                ],
            ),
            (
                "organizations",
                [
                    self._model_record(
                        item,
                        (
                            f"Organization: {item.name}. "
                            f"Type: {item.organization_type}. "
                            f"Description: {item.description}. "
                            f"Capabilities: "
                            f"{', '.join(item.capabilities)}. "
                            f"Products: {', '.join(item.products)}. "
                            f"Represented brands: "
                            f"{', '.join(item.represented_brands)}. "
                            f"Country: {item.country}. City: {item.city}. "
                            f"Notes: {item.notes}."
                        ),
                    )
                    for item in document.organizations
                ],
            ),
            (
                "suppliers_and_fabricators",
                [
                    self._model_record(
                        item,
                        (
                            f"Supplier/fabricator: "
                            f"{item.organization}. "
                            f"Type: {item.supplier_type}. "
                            f"Products or services: "
                            f"{', '.join(item.products_or_services)}. "
                            f"Contact: {item.person_name}; "
                            f"{item.role}; {item.email}; "
                            f"{item.phone}; {item.mobile}; "
                            f"{item.website}. "
                            f"Address: {item.address}. "
                            f"Notes: {item.notes}."
                        ),
                    )
                    for item in document.supplier_details
                ],
            ),
            (
                "contacts",
                [
                    self._model_record(
                        item,
                        (
                            f"Contact: {item.person_name}. "
                            f"Organization: {item.organization}. "
                            f"Role: {item.role}. "
                            f"Email: {item.email}. "
                            f"Phone: {item.phone}. "
                            f"Mobile: {item.mobile}. "
                            f"Fax: {item.fax}. "
                            f"Website: {item.website}. "
                            f"Address: {item.address}."
                        ),
                    )
                    for item in document.contacts
                ],
            ),
            (
                "technical_references",
                [
                    self._model_record(
                        item,
                        (
                            f"Technical reference: {item.title}. "
                            f"Type: {item.reference_type}. "
                            f"Identifier: {item.identifier}. "
                            f"Organization: {item.organization}. "
                            f"URL: {item.url}. "
                            f"Description: {item.description}."
                        ),
                    )
                    for item in document.technical_references
                ],
            ),
            (
                "recommendations",
                [
                    self._record(
                        recommendation,
                        [],
                    )
                    for recommendation
                    in document.recommendations
                ],
            ),
        ]

        return sections

    def _model_record(
        self,
        item: object,
        content: str,
    ) -> dict[str, Any]:
        evidence = getattr(item, "evidence", [])
        return self._record(content, evidence)

    @staticmethod
    def _record(
        content: str,
        evidence: list[object],
    ) -> dict[str, Any]:
        return {
            "content": RAGChunkBuilder._clean_content(content),
            "post_ids": sorted(
                {
                    item.post_id
                    for item in evidence
                    if getattr(item, "post_id", None)
                }
            ),
            "attachments": sorted(
                {
                    item.attachment_filename
                    for item in evidence
                    if getattr(
                        item,
                        "attachment_filename",
                        None,
                    )
                }
            ),
            "urls": sorted(
                {
                    item.source_url
                    for item in evidence
                    if getattr(item, "source_url", None)
                }
            ),
        }

    def _split_text(
        self,
        text: str,
    ) -> list[str]:
        if len(text) <= self.max_chars:
            return [text]

        sentences = re.split(
            r"(?<=[.!?])\s+",
            text,
        )
        chunks: list[str] = []
        current = ""

        for sentence in sentences:
            candidate = (
                f"{current} {sentence}".strip()
            )
            if (
                current
                and len(candidate) > self.max_chars
            ):
                chunks.append(current)
                overlap = current[-self.overlap_chars:]
                current = f"{overlap} {sentence}".strip()
            else:
                current = candidate

        if current:
            chunks.append(current)

        return chunks

    @staticmethod
    def _clean_content(content: str) -> str:
        content = re.sub(
            r"\bNone\b",
            "",
            content,
        )
        content = re.sub(
            r"\s+",
            " ",
            content,
        )
        content = re.sub(
            r"\s+([.,;:])",
            r"\1",
            content,
        )
        return content.strip()
