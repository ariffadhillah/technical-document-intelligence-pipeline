from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from src.schemas.technical_knowledge import (
    ContactDetail,
    DiagnosticFinding,
    EngineEntity,
    ExtractedEntity,
    MaintenanceTask,
    PartReference,
    SourceEvidence,
    StructuredTechnicalDocument,
    TechnicalSpecification,
    TechnicalWarning,
    TransmissionEntity,
    VehicleEntity,
)


class MarkdownRenderingError(Exception):
    """
    Raised when a structured technical document cannot be rendered.
    """


class TechnicalMarkdownRenderer:
    """
    Render a canonical StructuredTechnicalDocument as readable Markdown.

    The renderer only understands the canonical technical schema.
    It does not know which AI provider produced the document.
    """

    def __init__(
        self,
        *,
        include_evidence: bool = True,
        include_empty_sections: bool = False,
        include_processing_metadata: bool = True,
    ) -> None:
        self.include_evidence = include_evidence
        self.include_empty_sections = include_empty_sections
        self.include_processing_metadata = (
            include_processing_metadata
        )

    def render(
        self,
        document: StructuredTechnicalDocument,
    ) -> str:
        """
        Convert a validated technical document into Markdown.
        """

        sections: list[str] = []

        sections.append(self._render_header(document))
        sections.append(self._render_summary(document))
        sections.append(self._render_document_overview(document))

        self._append_section(
            sections,
            self._render_topics(document),
        )

        self._append_section(
            sections,
            self._render_vehicles(document.vehicles),
        )

        self._append_section(
            sections,
            self._render_engines(document.engines),
        )

        self._append_section(
            sections,
            self._render_transmissions(
                document.transmissions
            ),
        )

        self._append_section(
            sections,
            self._render_specifications(
                document.technical_specifications
            ),
        )

        self._append_section(
            sections,
            self._render_parts(document.parts),
        )

        self._append_section(
            sections,
            self._render_maintenance_tasks(
                document.maintenance_tasks
            ),
        )

        self._append_section(
            sections,
            self._render_diagnostics(
                document.diagnostics
            ),
        )

        self._append_section(
            sections,
            self._render_warnings(document.warnings),
        )

        self._append_section(
            sections,
            self._render_recommendations(
                document.recommendations
            ),
        )

        self._append_section(
            sections,
            self._render_contacts(document.contacts),
        )

        self._append_section(
            sections,
            self._render_entities(document.entities),
        )

        self._append_section(
            sections,
            self._render_references(
                document.technical_references
            ),
        )

        self._append_section(
            sections,
            self._render_translated_content(
                document.translated_markdown_content
            ),
        )

        if self.include_processing_metadata:
            self._append_section(
                sections,
                self._render_processing_metadata(
                    document
                ),
            )

        sections.append(self._render_footer(document))

        markdown = "\n\n".join(
            section.strip()
            for section in sections
            if section and section.strip()
        )

        return markdown.rstrip() + "\n"

    def render_from_dict(
        self,
        payload: dict[str, Any],
    ) -> str:
        try:
            document = (
                StructuredTechnicalDocument
                .model_validate(payload)
            )

        except ValidationError as error:
            raise MarkdownRenderingError(
                "Structured document validation failed "
                f"before rendering: {error}"
            ) from error

        return self.render(document)

    def render_from_json_file(
        self,
        input_path: Path,
    ) -> str:
        resolved_path = input_path.resolve()

        if not resolved_path.exists():
            raise MarkdownRenderingError(
                "Structured input file was not found: "
                f"{resolved_path}"
            )

        if not resolved_path.is_file():
            raise MarkdownRenderingError(
                "Structured input path is not a file: "
                f"{resolved_path}"
            )

        try:
            payload = json.loads(
                resolved_path.read_text(
                    encoding="utf-8"
                )
            )

        except OSError as error:
            raise MarkdownRenderingError(
                "Unable to read structured input file: "
                f"{resolved_path}"
            ) from error

        except json.JSONDecodeError as error:
            raise MarkdownRenderingError(
                "Structured input file contains invalid "
                f"JSON at line {error.lineno}, "
                f"column {error.colno}: {error.msg}"
            ) from error

        if not isinstance(payload, dict):
            raise MarkdownRenderingError(
                "Structured document JSON must contain "
                "an object at the root."
            )

        return self.render_from_dict(payload)

    def save(
        self,
        *,
        document: StructuredTechnicalDocument,
        output_path: Path,
    ) -> Path:
        markdown = self.render(document)

        return self._atomic_write_text(
            output_path=output_path,
            content=markdown,
        )

    def render_file(
        self,
        *,
        input_path: Path,
        output_path: Path,
    ) -> Path:
        markdown = self.render_from_json_file(
            input_path
        )

        return self._atomic_write_text(
            output_path=output_path,
            content=markdown,
        )

    def _render_header(
        self,
        document: StructuredTechnicalDocument,
    ) -> str:
        source_url = self._source_value(
            document.source,
            "source_url",
        )

        lines = [
            f"# {self._escape_heading(document.title)}",
            "",
            "> Technical knowledge document generated "
            "from structured forum and attachment data.",
            "",
            "| Document information | Value |",
            "|---|---|",
            (
                "| Document ID | "
                f"`{self._escape_table(document.document_id)}` |"
            ),
            (
                "| Document type | "
                f"{self._escape_table(document.document_type)} |"
            ),
            (
                "| Source language | "
                f"{self._escape_table(document.source_language)} |"
            ),
            (
                "| Output language | "
                f"{self._escape_table(document.output_language)} |"
            ),
        ]

        if source_url:
            safe_url = self._escape_link_url(
                str(source_url)
            )

            lines.append(
                "| Original source | "
                f"[Open source thread]({safe_url}) |"
            )

        return "\n".join(lines)

    def _render_summary(
        self,
        document: StructuredTechnicalDocument,
    ) -> str:
        return "\n".join(
            [
                "## Executive Summary",
                "",
                document.summary.strip(),
            ]
        )

    def _render_document_overview(
        self,
        document: StructuredTechnicalDocument,
    ) -> str:
        source_rows: list[tuple[str, Any]] = []

        preferred_keys = [
            "forum_name",
            "thread_id",
            "thread_title",
            "source_url",
            "author",
            "created_at",
        ]

        for key in preferred_keys:
            value = document.source.get(key)

            if value not in (None, "", [], {}):
                source_rows.append(
                    (
                        self._humanize(key),
                        value,
                    )
                )

        for key, value in document.source.items():
            if key in preferred_keys:
                continue

            if value in (None, "", [], {}):
                continue

            source_rows.append(
                (
                    self._humanize(key),
                    value,
                )
            )

        if (
            not source_rows
            and not self.include_empty_sections
        ):
            return ""

        lines = [
            "## Source Overview",
            "",
        ]

        if not source_rows:
            lines.append(
                "_No source metadata was provided._"
            )

            return "\n".join(lines)

        lines.extend(
            [
                "| Field | Value |",
                "|---|---|",
            ]
        )

        for label, value in source_rows:
            rendered_value = self._format_source_value(
                label,
                value,
            )

            lines.append(
                f"| {self._escape_table(label)} "
                f"| {rendered_value} |"
            )

        return "\n".join(lines)

    def _render_topics(
        self,
        document: StructuredTechnicalDocument,
    ) -> str:
        if (
            not document.topics
            and not document.system_categories
            and not self.include_empty_sections
        ):
            return ""

        lines = [
            "## Topics and System Categories",
            "",
        ]

        if document.topics:
            lines.append("### Topics")
            lines.append("")

            lines.extend(
                f"- {topic}"
                for topic in document.topics
            )

        elif self.include_empty_sections:
            lines.append(
                "_No topics were extracted._"
            )

        if document.system_categories:
            if document.topics:
                lines.append("")

            lines.append("### System Categories")
            lines.append("")

            lines.extend(
                f"- {category}"
                for category in (
                    document.system_categories
                )
            )

        elif self.include_empty_sections:
            lines.append(
                "_No system categories were extracted._"
            )

        return "\n".join(lines)

    def _render_vehicles(
        self,
        vehicles: list[VehicleEntity],
    ) -> str:
        if (
            not vehicles
            and not self.include_empty_sections
        ):
            return ""

        lines = [
            "## Vehicle Information",
            "",
        ]

        if not vehicles:
            lines.append(
                "_No vehicle information was extracted._"
            )

            return "\n".join(lines)

        for index, vehicle in enumerate(
            vehicles,
            start=1,
        ):
            name = " ".join(
                part
                for part in [
                    vehicle.manufacturer,
                    vehicle.model,
                    vehicle.variant,
                ]
                if part
            )

            if len(vehicles) > 1:
                lines.append(
                    f"### Vehicle {index}: "
                    f"{self._escape_heading(name)}"
                )
            else:
                lines.append(
                    f"### {self._escape_heading(name)}"
                )

            lines.append("")
            lines.extend(
                [
                    "| Attribute | Value |",
                    "|---|---|",
                ]
            )

            rows = [
                (
                    "Manufacturer",
                    vehicle.manufacturer,
                ),
                ("Model", vehicle.model),
                ("Variant", vehicle.variant),
                (
                    "Production year",
                    vehicle.production_year,
                ),
                (
                    "Drive configuration",
                    vehicle.drive_configuration,
                ),
                (
                    "Vehicle type",
                    vehicle.vehicle_type,
                ),
                (
                    "Gross weight",
                    self._format_measurement(
                        vehicle.gross_weight_kg,
                        "kg",
                    ),
                ),
                (
                    "Empty weight",
                    self._format_measurement(
                        vehicle.empty_weight_kg,
                        "kg",
                    ),
                ),
                (
                    "Confidence",
                    self._format_confidence(
                        vehicle.confidence
                    ),
                ),
            ]

            self._append_table_rows(lines, rows)

            self._append_evidence_block(
                lines,
                vehicle.evidence,
            )

            if index < len(vehicles):
                lines.extend(["", "---", ""])

        return "\n".join(lines)

    def _render_engines(
        self,
        engines: list[EngineEntity],
    ) -> str:
        if (
            not engines
            and not self.include_empty_sections
        ):
            return ""

        lines = [
            "## Engine",
            "",
        ]

        if not engines:
            lines.append(
                "_No engine information was extracted._"
            )

            return "\n".join(lines)

        for index, engine in enumerate(
            engines,
            start=1,
        ):
            name = " ".join(
                part
                for part in [
                    engine.manufacturer,
                    engine.model,
                ]
                if part
            )

            if len(engines) > 1:
                lines.append(
                    f"### Engine {index}: "
                    f"{self._escape_heading(name)}"
                )
            else:
                lines.append(
                    f"### {self._escape_heading(name)}"
                )

            lines.append("")
            lines.extend(
                [
                    "| Attribute | Value |",
                    "|---|---|",
                ]
            )

            rows = [
                (
                    "Manufacturer",
                    engine.manufacturer,
                ),
                ("Model", engine.model),
                (
                    "Engine type",
                    engine.engine_type,
                ),
                (
                    "Cylinder count",
                    engine.cylinder_count,
                ),
                (
                    "Displacement",
                    self._format_measurement(
                        engine.displacement_cc,
                        "cc",
                    ),
                ),
                (
                    "Power",
                    self._format_power(engine),
                ),
                (
                    "Fuel type",
                    engine.fuel_type,
                ),
                (
                    "Cooling type",
                    engine.cooling_type,
                ),
                (
                    "Confidence",
                    self._format_confidence(
                        engine.confidence
                    ),
                ),
            ]

            self._append_table_rows(lines, rows)

            self._append_evidence_block(
                lines,
                engine.evidence,
            )

            if index < len(engines):
                lines.extend(["", "---", ""])

        return "\n".join(lines)

    def _render_transmissions(
        self,
        transmissions: list[TransmissionEntity],
    ) -> str:
        if (
            not transmissions
            and not self.include_empty_sections
        ):
            return ""

        lines = [
            "## Transmission",
            "",
        ]

        if not transmissions:
            lines.append(
                "_No transmission information was extracted._"
            )

            return "\n".join(lines)

        for index, transmission in enumerate(
            transmissions,
            start=1,
        ):
            name = " ".join(
                part
                for part in [
                    transmission.manufacturer,
                    transmission.model,
                ]
                if part
            )

            if len(transmissions) > 1:
                lines.append(
                    f"### Transmission {index}: "
                    f"{self._escape_heading(name)}"
                )
            else:
                lines.append(
                    f"### {self._escape_heading(name)}"
                )

            lines.append("")
            lines.extend(
                [
                    "| Attribute | Value |",
                    "|---|---|",
                ]
            )

            rows = [
                (
                    "Manufacturer",
                    transmission.manufacturer,
                ),
                (
                    "Model",
                    transmission.model,
                ),
                (
                    "Transmission type",
                    transmission.transmission_type,
                ),
                (
                    "Gear count",
                    transmission.gear_count,
                ),
                (
                    "Notes",
                    transmission.notes,
                ),
                (
                    "Confidence",
                    self._format_confidence(
                        transmission.confidence
                    ),
                ),
            ]

            self._append_table_rows(lines, rows)

            self._append_evidence_block(
                lines,
                transmission.evidence,
            )

            if index < len(transmissions):
                lines.extend(["", "---", ""])

        return "\n".join(lines)

    def _render_specifications(
        self,
        specifications: list[
            TechnicalSpecification
        ],
    ) -> str:
        if (
            not specifications
            and not self.include_empty_sections
        ):
            return ""

        lines = [
            "## Technical Specifications",
            "",
        ]

        if not specifications:
            lines.append(
                "_No technical specifications "
                "were extracted._"
            )

            return "\n".join(lines)

        grouped: dict[
            str,
            list[TechnicalSpecification],
        ] = defaultdict(list)

        for specification in specifications:
            category = (
                specification.category
                or "General"
            )

            grouped[category].append(specification)

        for category_index, category in enumerate(
            sorted(
                grouped,
                key=str.casefold,
            )
        ):
            category_items = grouped[category]

            lines.append(
                f"### {self._escape_heading(category.title())}"
            )
            lines.append("")
            lines.extend(
                [
                    "| Specification | Value | "
                    "Normalized value | Confidence |",
                    "|---|---:|---:|---|",
                ]
            )

            for item in category_items:
                value = self._combine_value_unit(
                    item.value,
                    item.unit,
                )

                normalized = (
                    self._combine_value_unit(
                        item.normalized_value,
                        item.normalized_unit,
                    )
                    if item.normalized_value is not None
                    else "—"
                )

                lines.append(
                    "| "
                    f"{self._escape_table(item.name)} | "
                    f"{self._escape_table(value)} | "
                    f"{self._escape_table(normalized)} | "
                    f"{self._format_confidence(item.confidence)} "
                    "|"
                )

                self._append_evidence_block(
                    lines,
                    item.evidence,
                    heading=(
                        f"Evidence for {item.name}"
                    ),
                )

            if category_index < len(grouped) - 1:
                lines.append("")

        return "\n".join(lines)

    def _render_parts(
        self,
        parts: list[PartReference],
    ) -> str:
        if (
            not parts
            and not self.include_empty_sections
        ):
            return ""

        lines = [
            "## Parts and Component References",
            "",
        ]

        if not parts:
            lines.append(
                "_No part references were extracted._"
            )

            return "\n".join(lines)

        for index, part in enumerate(
            parts,
            start=1,
        ):
            lines.append(
                f"### {index}. "
                f"{self._escape_heading(part.name)}"
            )
            lines.append("")

            rows = [
                (
                    "Manufacturer",
                    part.manufacturer,
                ),
                (
                    "Part number",
                    part.part_number,
                ),
                (
                    "Alternative part numbers",
                    ", ".join(
                        part.alternative_part_numbers
                    ),
                ),
                (
                    "Confidence",
                    self._format_confidence(
                        part.confidence
                    ),
                ),
            ]

            lines.extend(
                [
                    "| Attribute | Value |",
                    "|---|---|",
                ]
            )

            self._append_table_rows(lines, rows)

            if part.description:
                lines.extend(
                    [
                        "",
                        part.description,
                    ]
                )

            self._append_evidence_block(
                lines,
                part.evidence,
            )

            if index < len(parts):
                lines.extend(["", "---", ""])

        return "\n".join(lines)

    def _render_maintenance_tasks(
        self,
        tasks: list[MaintenanceTask],
    ) -> str:
        if (
            not tasks
            and not self.include_empty_sections
        ):
            return ""

        lines = [
            "## Maintenance and Workshop Tasks",
            "",
        ]

        if not tasks:
            lines.append(
                "_No maintenance tasks were extracted._"
            )

            return "\n".join(lines)

        for index, task in enumerate(
            tasks,
            start=1,
        ):
            lines.append(
                f"### {index}. "
                f"{self._escape_heading(task.title)}"
            )
            lines.append("")

            if task.description:
                lines.append(task.description)
                lines.append("")

            rows = [
                (
                    "System category",
                    task.system_category,
                ),
                (
                    "Action type",
                    task.action_type,
                ),
                (
                    "Confidence",
                    self._format_confidence(
                        task.confidence
                    ),
                ),
            ]

            lines.extend(
                [
                    "| Task attribute | Value |",
                    "|---|---|",
                ]
            )

            self._append_table_rows(lines, rows)

            self._append_list_subsection(
                lines,
                title="Tools",
                values=task.tools,
            )

            self._append_list_subsection(
                lines,
                title="Parts",
                values=task.parts,
            )

            self._append_list_subsection(
                lines,
                title="Measurements",
                values=task.measurements,
            )

            self._append_list_subsection(
                lines,
                title="Task Warnings",
                values=task.warnings,
            )

            self._append_evidence_block(
                lines,
                task.evidence,
            )

            if index < len(tasks):
                lines.extend(["", "---", ""])

        return "\n".join(lines)

    def _render_diagnostics(
        self,
        diagnostics: list[DiagnosticFinding],
    ) -> str:
        if (
            not diagnostics
            and not self.include_empty_sections
        ):
            return ""

        lines = [
            "## Diagnostics and Troubleshooting",
            "",
        ]

        if not diagnostics:
            lines.append(
                "_No diagnostic findings were extracted._"
            )

            return "\n".join(lines)

        for index, finding in enumerate(
            diagnostics,
            start=1,
        ):
            lines.append(
                f"### {index}. "
                f"{self._escape_heading(finding.symptom)}"
            )
            lines.append("")

            lines.append(
                "**Confidence:** "
                f"{self._format_confidence(finding.confidence)}"
            )

            self._append_list_subsection(
                lines,
                title="Possible Causes",
                values=finding.possible_causes,
            )

            self._append_list_subsection(
                lines,
                title="Recommended Actions",
                values=finding.recommended_actions,
            )

            self._append_evidence_block(
                lines,
                finding.evidence,
            )

            if index < len(diagnostics):
                lines.extend(["", "---", ""])

        return "\n".join(lines)

    def _render_warnings(
        self,
        warnings: list[TechnicalWarning],
    ) -> str:
        if (
            not warnings
            and not self.include_empty_sections
        ):
            return ""

        lines = [
            "## Safety and Technical Warnings",
            "",
        ]

        if not warnings:
            lines.append(
                "_No warnings were extracted._"
            )

            return "\n".join(lines)

        severity_labels = {
            "informational": "Information",
            "caution": "Caution",
            "warning": "Warning",
            "critical": "Critical",
        }

        for index, warning in enumerate(
            warnings,
            start=1,
        ):
            severity = severity_labels.get(
                warning.severity,
                warning.severity.title(),
            )

            lines.extend(
                [
                    f"### {index}. {severity}: "
                    f"{self._escape_heading(warning.warning_type.title())}",
                    "",
                    f"> **{severity}:** "
                    f"{warning.description}",
                ]
            )

            self._append_evidence_block(
                lines,
                warning.evidence,
            )

            if index < len(warnings):
                lines.extend(["", "---", ""])

        return "\n".join(lines)

    def _render_recommendations(
        self,
        recommendations: list[str],
    ) -> str:
        if (
            not recommendations
            and not self.include_empty_sections
        ):
            return ""

        lines = [
            "## Recommendations",
            "",
        ]

        if not recommendations:
            lines.append(
                "_No recommendations were extracted._"
            )

            return "\n".join(lines)

        lines.extend(
            f"{index}. {recommendation}"
            for index, recommendation in enumerate(
                recommendations,
                start=1,
            )
        )

        return "\n".join(lines)

    def _render_contacts(
        self,
        contacts: list[ContactDetail],
    ) -> str:
        if (
            not contacts
            and not self.include_empty_sections
        ):
            return ""

        lines = [
            "## Contacts and Organizations",
            "",
        ]

        if not contacts:
            lines.append(
                "_No contact information was extracted._"
            )

            return "\n".join(lines)

        for index, contact in enumerate(
            contacts,
            start=1,
        ):
            heading = (
                contact.organization
                or contact.person_name
                or f"Contact {index}"
            )

            lines.append(
                f"### {self._escape_heading(heading)}"
            )
            lines.append("")
            lines.extend(
                [
                    "| Field | Value |",
                    "|---|---|",
                ]
            )

            rows = [
                (
                    "Organization",
                    contact.organization,
                ),
                (
                    "Person",
                    contact.person_name,
                ),
                ("Role", contact.role),
                ("Email", contact.email),
                ("Phone", contact.phone),
                ("Mobile", contact.mobile),
                ("Fax", contact.fax),
                ("Website", contact.website),
                ("Address", contact.address),
                (
                    "Coordinates",
                    contact.coordinates,
                ),
                (
                    "Confidence",
                    self._format_confidence(
                        contact.confidence
                    ),
                ),
            ]

            self._append_table_rows(lines, rows)

            self._append_evidence_block(
                lines,
                contact.evidence,
            )

            if index < len(contacts):
                lines.extend(["", "---", ""])

        return "\n".join(lines)

    def _render_entities(
        self,
        entities: list[ExtractedEntity],
    ) -> str:
        if (
            not entities
            and not self.include_empty_sections
        ):
            return ""

        lines = [
            "## Extracted Entities",
            "",
        ]

        if not entities:
            lines.append(
                "_No additional entities were extracted._"
            )

            return "\n".join(lines)

        lines.extend(
            [
                "| Type | Name | Normalized name | "
                "Aliases | Confidence |",
                "|---|---|---|---|---|",
            ]
        )

        for entity in entities:
            lines.append(
                "| "
                f"{self._escape_table(entity.entity_type)} | "
                f"{self._escape_table(entity.name)} | "
                f"{self._escape_table(entity.normalized_name or '—')} | "
                f"{self._escape_table(', '.join(entity.aliases) or '—')} | "
                f"{self._format_confidence(entity.confidence)} |"
            )

            if entity.description:
                lines.extend(
                    [
                        "",
                        f"**{entity.name}:** "
                        f"{entity.description}",
                    ]
                )

            self._append_evidence_block(
                lines,
                entity.evidence,
                heading=(
                    f"Evidence for {entity.name}"
                ),
            )

        return "\n".join(lines)

    def _render_references(
        self,
        references: list[str],
    ) -> str:
        if (
            not references
            and not self.include_empty_sections
        ):
            return ""

        lines = [
            "## Technical References",
            "",
        ]

        if not references:
            lines.append(
                "_No technical references were extracted._"
            )

            return "\n".join(lines)

        lines.extend(
            f"- `{reference}`"
            for reference in references
        )

        return "\n".join(lines)

    def _render_translated_content(
        self,
        translated_content: str | None,
    ) -> str:
        if not translated_content:
            if self.include_empty_sections:
                return "\n".join(
                    [
                        "## Translated Source Content",
                        "",
                        "_No translated source content "
                        "was provided._",
                    ]
                )

            return ""

        return "\n".join(
            [
                "## Translated Source Content",
                "",
                translated_content.strip(),
            ]
        )

    def _render_processing_metadata(
        self,
        document: StructuredTechnicalDocument,
    ) -> str:
        processing = document.processing
        translation = document.translation_quality

        lines = [
            "## Processing and Quality Metadata",
            "",
            "| Field | Value |",
            "|---|---|",
            (
                "| Schema version | "
                f"`{self._escape_table(processing.schema_version)}` |"
            ),
            (
                "| Extraction provider | "
                f"{self._escape_table(processing.extraction_provider or '—')} |"
            ),
            (
                "| Extraction model | "
                f"{self._escape_table(processing.extraction_model or '—')} |"
            ),
            (
                "| Source stage | "
                f"`{self._escape_table(processing.source_stage)}` |"
            ),
            (
                "| Output stage | "
                f"`{self._escape_table(processing.output_stage)}` |"
            ),
            (
                "| Ready for rendering | "
                f"{'Yes' if processing.ready_for_rendering else 'No'} |"
            ),
            (
                "| Generated at | "
                f"{self._escape_table(processing.generated_at)} |"
            ),
            (
                "| Translation performed | "
                f"{'Yes' if translation.translated else 'No'} |"
            ),
            (
                "| Translation direction | "
                f"{self._escape_table(translation.source_language)} "
                "→ "
                f"{self._escape_table(translation.target_language)} |"
            ),
            (
                "| Translation fidelity | "
                f"{self._format_score(translation.fidelity_score)} |"
            ),
            (
                "| Protected tokens preserved | "
                f"{translation.preserved_token_count}/"
                f"{translation.protected_token_count} |"
            ),
        ]

        all_warnings = [
            *processing.warnings,
            *translation.validation_warnings,
        ]

        if all_warnings:
            lines.extend(
                [
                    "",
                    "### Processing Warnings",
                    "",
                ]
            )

            lines.extend(
                f"- {warning}"
                for warning in all_warnings
            )

        return "\n".join(lines)

    def _render_footer(
        self,
        document: StructuredTechnicalDocument,
    ) -> str:
        return "\n".join(
            [
                "---",
                "",
                "_This document was generated from "
                "structured technical evidence. "
                "Important maintenance, modification, "
                "and safety decisions should be verified "
                "against official manufacturer documentation "
                "and qualified technical inspection._",
                "",
                (
                    f"`Document: {document.document_id}` "
                    f"· `Schema: "
                    f"{document.processing.schema_version}`"
                ),
            ]
        )

    def _append_evidence_block(
        self,
        lines: list[str],
        evidence_items: list[SourceEvidence],
        *,
        heading: str = "Source Evidence",
    ) -> None:
        if (
            not self.include_evidence
            or not evidence_items
        ):
            return

        lines.extend(
            [
                "",
                f"<details>",
                f"<summary>{heading}</summary>",
                "",
            ]
        )

        for index, evidence in enumerate(
            evidence_items,
            start=1,
        ):
            references: list[str] = [
                (
                    "**Type:** "
                    f"{self._humanize(evidence.evidence_type)}"
                )
            ]

            if evidence.post_id:
                references.append(
                    f"**Post ID:** `{evidence.post_id}`"
                )

            if evidence.attachment_filename:
                references.append(
                    "**Attachment:** "
                    f"`{evidence.attachment_filename}`"
                )

            if evidence.source_url:
                references.append(
                    "**Source:** "
                    f"[link]({self._escape_link_url(evidence.source_url)})"
                )

            lines.append(
                f"{index}. "
                + " · ".join(references)
            )

            if evidence.quote:
                lines.extend(
                    [
                        "",
                        f"   > {self._escape_quote(evidence.quote)}",
                    ]
                )

        lines.extend(
            [
                "",
                "</details>",
            ]
        )

    def _append_list_subsection(
        self,
        lines: list[str],
        *,
        title: str,
        values: Iterable[str],
    ) -> None:
        cleaned_values = [
            value.strip()
            for value in values
            if value and value.strip()
        ]

        if not cleaned_values:
            return

        lines.extend(
            [
                "",
                f"#### {title}",
                "",
            ]
        )

        lines.extend(
            f"- {value}"
            for value in cleaned_values
        )

    def _append_table_rows(
        self,
        lines: list[str],
        rows: Iterable[tuple[str, Any]],
    ) -> None:
        appended = False

        for label, value in rows:
            if value in (None, "", [], {}):
                continue

            rendered_value = self._escape_table(
                self._stringify(value)
            )

            lines.append(
                f"| {self._escape_table(label)} "
                f"| {rendered_value} |"
            )

            appended = True

        if not appended:
            lines.append(
                "| Information | Not available |"
            )

    def _append_section(
        self,
        sections: list[str],
        section: str,
    ) -> None:
        if section and section.strip():
            sections.append(section)

    @staticmethod
    def _format_power(
        engine: EngineEntity,
    ) -> str | None:
        values: list[str] = []

        if engine.power_kw is not None:
            values.append(
                f"{TechnicalMarkdownRenderer._format_number(engine.power_kw)} kW"
            )

        if engine.power_hp is not None:
            values.append(
                f"{TechnicalMarkdownRenderer._format_number(engine.power_hp)} hp"
            )

        return " / ".join(values) or None

    @staticmethod
    def _format_measurement(
        value: int | float | None,
        unit: str,
    ) -> str | None:
        if value is None:
            return None

        return (
            f"{TechnicalMarkdownRenderer._format_number(value)} "
            f"{unit}"
        )

    @staticmethod
    def _combine_value_unit(
        value: Any,
        unit: str | None,
    ) -> str:
        formatted_value = (
            TechnicalMarkdownRenderer
            ._stringify(value)
        )

        if not unit:
            return formatted_value

        return f"{formatted_value} {unit}"

    @staticmethod
    def _format_confidence(
        confidence: str,
    ) -> str:
        labels = {
            "low": "Low",
            "medium": "Medium",
            "high": "High",
        }

        return labels.get(
            confidence,
            confidence.title(),
        )

    @staticmethod
    def _format_score(
        score: float | None,
    ) -> str:
        if score is None:
            return "—"

        percentage = score * 100

        return f"{percentage:.1f}%"

    @staticmethod
    def _format_number(
        value: int | float,
    ) -> str:
        if isinstance(value, bool):
            return str(value)

        if isinstance(value, int):
            return f"{value:,}"

        if float(value).is_integer():
            return f"{int(value):,}"

        return f"{value:,.3f}".rstrip("0").rstrip(".")

    @staticmethod
    def _stringify(value: Any) -> str:
        if isinstance(value, bool):
            return "Yes" if value else "No"

        if isinstance(value, float):
            return (
                TechnicalMarkdownRenderer
                ._format_number(value)
            )

        if isinstance(value, int):
            return (
                TechnicalMarkdownRenderer
                ._format_number(value)
            )

        if isinstance(value, list):
            return ", ".join(
                TechnicalMarkdownRenderer
                ._stringify(item)
                for item in value
            )

        if isinstance(value, dict):
            return json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
            )

        return str(value)

    @staticmethod
    def _source_value(
        source: dict[str, Any],
        key: str,
    ) -> Any:
        value = source.get(key)

        if value in (None, "", [], {}):
            return None

        return value

    @staticmethod
    def _format_source_value(
        label: str,
        value: Any,
    ) -> str:
        rendered = (
            TechnicalMarkdownRenderer
            ._stringify(value)
        )

        if (
            "url" in label.casefold()
            and isinstance(value, str)
            and value.startswith(
                ("http://", "https://")
            )
        ):
            return (
                f"[Open link]("
                f"{TechnicalMarkdownRenderer._escape_link_url(value)}"
                ")"
            )

        return (
            TechnicalMarkdownRenderer
            ._escape_table(rendered)
        )

    @staticmethod
    def _humanize(value: str) -> str:
        return value.replace("_", " ").strip().title()

    @staticmethod
    def _escape_table(value: Any) -> str:
        return (
            str(value)
            .replace("\\", "\\\\")
            .replace("|", "\\|")
            .replace("\n", "<br>")
        )

    @staticmethod
    def _escape_heading(value: str) -> str:
        return (
            value.replace("\n", " ")
            .replace("#", "\\#")
            .strip()
        )

    @staticmethod
    def _escape_quote(value: str) -> str:
        return value.replace(
            "\n",
            "<br>",
        )

    @staticmethod
    def _escape_link_url(value: str) -> str:
        return (
            value.strip()
            .replace(" ", "%20")
            .replace("(", "%28")
            .replace(")", "%29")
        )

    @staticmethod
    def _atomic_write_text(
        *,
        output_path: Path,
        content: str,
    ) -> Path:
        resolved_path = output_path.resolve()

        resolved_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = resolved_path.with_suffix(
            resolved_path.suffix + ".tmp"
        )

        try:
            temporary_path.write_text(
                content,
                encoding="utf-8",
            )

            temporary_path.replace(
                resolved_path
            )

        except OSError as error:
            if temporary_path.exists():
                temporary_path.unlink(
                    missing_ok=True
                )

            raise MarkdownRenderingError(
                "Unable to write Markdown output: "
                f"{resolved_path}"
            ) from error

        return resolved_path