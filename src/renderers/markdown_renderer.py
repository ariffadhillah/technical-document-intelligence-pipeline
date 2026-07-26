from __future__ import annotations

from typing import Iterable

from src.schemas.technical_knowledge import (
    SourceEvidence,
    StructuredTechnicalDocument,
)


class MarkdownRenderer:
    """Render a validated technical document as readable Markdown."""

    def render(
        self,
        document: StructuredTechnicalDocument,
    ) -> str:
        lines: list[str] = [
            f"# {document.title}",
            "",
            document.summary,
            "",
        ]

        self._append_string_section(
            lines,
            "Topics",
            document.topics,
        )
        self._append_string_section(
            lines,
            "System Categories",
            document.system_categories,
        )

        if document.vehicles:
            lines.extend(["## Vehicles", ""])
            for item in document.vehicles:
                heading = " ".join(
                    value
                    for value in [
                        item.manufacturer,
                        item.model,
                        item.variant,
                    ]
                    if value
                )
                lines.append(f"### {heading}")
                lines.append("")
                self._append_fields(
                    lines,
                    [
                        ("Production year", item.production_year),
                        (
                            "Drive configuration",
                            item.drive_configuration,
                        ),
                        ("Vehicle type", item.vehicle_type),
                        ("Gross weight", self._unit(item.gross_weight_kg, "kg")),
                        ("Empty weight", self._unit(item.empty_weight_kg, "kg")),
                        ("Confidence", item.confidence),
                    ],
                )
                self._append_evidence(lines, item.evidence)

        if document.engines:
            lines.extend(["## Engines", ""])
            for item in document.engines:
                heading = " ".join(
                    value
                    for value in [item.manufacturer, item.model]
                    if value
                )
                lines.append(f"### {heading}")
                lines.append("")
                self._append_fields(
                    lines,
                    [
                        ("Engine type", item.engine_type),
                        ("Cylinders", item.cylinder_count),
                        (
                            "Displacement",
                            self._unit(item.displacement_cc, "cc"),
                        ),
                        ("Power", self._unit(item.power_hp, "hp")),
                        ("Power", self._unit(item.power_kw, "kW")),
                        ("Fuel type", item.fuel_type),
                        ("Cooling type", item.cooling_type),
                        ("Confidence", item.confidence),
                    ],
                )
                self._append_evidence(lines, item.evidence)

        if document.transmissions:
            lines.extend(["## Transmissions", ""])
            for item in document.transmissions:
                heading = " ".join(
                    value
                    for value in [item.manufacturer, item.model]
                    if value
                )
                lines.append(f"### {heading}")
                lines.append("")
                self._append_fields(
                    lines,
                    [
                        ("Type", item.transmission_type),
                        ("Gear count", item.gear_count),
                        ("Notes", item.notes),
                        ("Confidence", item.confidence),
                    ],
                )
                self._append_evidence(lines, item.evidence)

        if document.technical_specifications:
            lines.extend(["## Technical Specifications", ""])
            lines.extend(
                [
                    "| Category | Name | Value | Confidence |",
                    "|---|---|---:|---|",
                ]
            )
            for item in document.technical_specifications:
                value = str(item.value)
                if item.unit:
                    value = f"{value} {item.unit}"
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            self._escape_table(item.category or "General"),
                            self._escape_table(item.name),
                            self._escape_table(value),
                            self._escape_table(item.confidence),
                        ]
                    )
                    + " |"
                )
            lines.append("")

        if document.parts:
            lines.extend(["## Parts and Part References", ""])
            for item in document.parts:
                lines.append(f"### {item.name}")
                lines.append("")
                self._append_fields(
                    lines,
                    [
                        ("Manufacturer", item.manufacturer),
                        ("Part number", item.part_number),
                        (
                            "Alternative part numbers",
                            ", ".join(item.alternative_part_numbers)
                            if item.alternative_part_numbers
                            else None,
                        ),
                        ("Description", item.description),
                        ("Confidence", item.confidence),
                    ],
                )
                self._append_evidence(lines, item.evidence)

        if document.maintenance_tasks:
            lines.extend(["## Maintenance Tasks", ""])
            for item in document.maintenance_tasks:
                lines.append(f"### {item.title}")
                lines.append("")
                self._append_fields(
                    lines,
                    [
                        ("Description", item.description),
                        ("System category", item.system_category),
                        ("Action type", item.action_type),
                        ("Tools", ", ".join(item.tools) or None),
                        ("Parts", ", ".join(item.parts) or None),
                        (
                            "Measurements",
                            ", ".join(item.measurements) or None,
                        ),
                        ("Warnings", ", ".join(item.warnings) or None),
                        ("Confidence", item.confidence),
                    ],
                )
                self._append_evidence(lines, item.evidence)

        if document.diagnostics:
            lines.extend(["## Diagnostic Findings", ""])
            for item in document.diagnostics:
                lines.append(f"### {item.symptom}")
                lines.append("")
                self._append_string_section(
                    lines,
                    "Possible Causes",
                    item.possible_causes,
                    heading_level=4,
                )
                self._append_string_section(
                    lines,
                    "Recommended Actions",
                    item.recommended_actions,
                    heading_level=4,
                )
                self._append_fields(
                    lines,
                    [("Confidence", item.confidence)],
                )
                self._append_evidence(lines, item.evidence)

        if document.organizations:
            lines.extend(["## Organizations", ""])
            for item in document.organizations:
                lines.append(f"### {item.name}")
                lines.append("")
                self._append_fields(
                    lines,
                    [
                        ("Type", item.organization_type),
                        ("Description", item.description),
                        ("Country", item.country),
                        ("City", item.city),
                        (
                            "Capabilities",
                            ", ".join(item.capabilities) or None,
                        ),
                        ("Products", ", ".join(item.products) or None),
                        (
                            "Represented brands",
                            ", ".join(item.represented_brands) or None,
                        ),
                        (
                            "Certifications",
                            ", ".join(item.certifications) or None,
                        ),
                        ("Notes", item.notes),
                        ("Confidence", item.confidence),
                    ],
                )
                if item.services:
                    lines.extend(["#### Services", ""])
                    for service in item.services:
                        lines.append(f"##### {service.name}")
                        lines.append("")
                        price = self._format_price(
                            service.price,
                            service.currency,
                        )
                        self._append_fields(
                            lines,
                            [
                                ("Category", service.category),
                                ("Description", service.description),
                                ("Price", price),
                                ("Price basis", service.price_basis),
                                ("Confidence", service.confidence),
                            ],
                        )
                        self._append_evidence(
                            lines,
                            service.evidence,
                            heading_level=6,
                        )

                if item.relationships:
                    lines.extend(["#### Relationships", ""])
                    for relationship in item.relationships:
                        lines.append(
                            "- "
                            f"**{relationship.relationship_type}:** "
                            f"{relationship.target_organization}"
                            + (
                                f" — {relationship.description}"
                                if relationship.description
                                else ""
                            )
                            + f" (confidence: {relationship.confidence})"
                        )
                    lines.append("")

                if item.contact:
                    lines.extend(["#### Contact", ""])
                    self._append_contact(lines, item.contact)

                self._append_evidence(lines, item.evidence)

        if document.contacts:
            lines.extend(["## Contacts", ""])
            for index, item in enumerate(document.contacts, start=1):
                name = (
                    item.person_name
                    or item.organization
                    or f"Contact {index}"
                )
                lines.append(f"### {name}")
                lines.append("")
                self._append_contact(lines, item)
                self._append_evidence(lines, item.evidence)

        if document.technical_references:
            lines.extend(["## Technical References", ""])
            for item in document.technical_references:
                lines.append(f"### {item.title}")
                lines.append("")
                self._append_fields(
                    lines,
                    [
                        ("Type", item.reference_type),
                        ("Identifier", item.identifier),
                        ("Organization", item.organization),
                        ("URL", item.url),
                        ("Description", item.description),
                        ("Confidence", item.confidence),
                    ],
                )
                self._append_evidence(lines, item.evidence)

        if document.warnings:
            lines.extend(["## Technical Warnings", ""])
            for item in document.warnings:
                lines.append(
                    f"- **{item.severity.upper()} — "
                    f"{item.warning_type}:** {item.description}"
                )
            lines.append("")

        self._append_string_section(
            lines,
            "Recommendations",
            document.recommendations,
        )

        lines.extend(
            [
                "## Processing Metadata",
                "",
                f"- Schema version: `{document.processing.schema_version}`",
                f"- Provider: `{document.processing.extraction_provider or 'unknown'}`",
                f"- Model: `{document.processing.extraction_model or 'unknown'}`",
                f"- Generated at: `{document.processing.generated_at}`",
                f"- Source stage: `{document.processing.source_stage}`",
                f"- Output stage: `{document.processing.output_stage}`",
                "",
            ]
        )

        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _append_fields(
        lines: list[str],
        fields: Iterable[tuple[str, object]],
    ) -> None:
        for label, value in fields:
            if value is None or value == "":
                continue
            lines.append(f"- **{label}:** {value}")
        lines.append("")

    @staticmethod
    def _append_string_section(
        lines: list[str],
        title: str,
        values: list[str],
        *,
        heading_level: int = 2,
    ) -> None:
        if not values:
            return
        lines.extend(
            [
                f"{'#' * heading_level} {title}",
                "",
            ]
        )
        lines.extend(f"- {value}" for value in values)
        lines.append("")

    def _append_contact(
        self,
        lines: list[str],
        contact: object,
    ) -> None:
        self._append_fields(
            lines,
            [
                ("Organization", getattr(contact, "organization", None)),
                ("Person", getattr(contact, "person_name", None)),
                ("Role", getattr(contact, "role", None)),
                ("Email", getattr(contact, "email", None)),
                ("Phone", getattr(contact, "phone", None)),
                ("Mobile", getattr(contact, "mobile", None)),
                ("Fax", getattr(contact, "fax", None)),
                ("Website", getattr(contact, "website", None)),
                ("Address", getattr(contact, "address", None)),
                ("Coordinates", getattr(contact, "coordinates", None)),
                ("Confidence", getattr(contact, "confidence", None)),
            ],
        )

    @staticmethod
    def _append_evidence(
        lines: list[str],
        evidence: list[SourceEvidence],
        *,
        heading_level: int = 4,
    ) -> None:
        if not evidence:
            return
        lines.extend(
            [
                f"{'#' * heading_level} Evidence",
                "",
            ]
        )
        for item in evidence:
            references = [
                f"type={item.evidence_type}",
            ]
            if item.post_id:
                references.append(f"post={item.post_id}")
            if item.attachment_filename:
                references.append(
                    f"attachment={item.attachment_filename}"
                )
            if item.source_url:
                references.append(f"url={item.source_url}")
            suffix = ", ".join(references)
            if item.quote:
                lines.append(f"- {item.quote} ({suffix})")
            else:
                lines.append(f"- {suffix}")
        lines.append("")

    @staticmethod
    def _format_price(
        value: float | int | None,
        currency: str | None,
    ) -> str | None:
        if value is None:
            return None

        number = f"{value:g}"
        return f"{number} {currency}" if currency else number

    @staticmethod
    def _unit(
        value: float | int | None,
        unit: str,
    ) -> str | None:
        if value is None:
            return None
        return f"{value:g} {unit}"

    @staticmethod
    def _escape_table(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")
