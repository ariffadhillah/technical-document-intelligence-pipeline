from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


ConfidenceLevel = Literal[
    "low",
    "medium",
    "high",
]

EvidenceType = Literal[
    "forum_post",
    "ocr",
    "pdf_text",
    "vision_summary",
    "metadata",
]

EntityType = Literal[
    "vehicle",
    "engine",
    "transmission",
    "manufacturer",
    "organization",
    "person",
    "location",
    "part",
    "supplier",
    "technical_reference",
]


class StrictBaseModel(BaseModel):
    """
    Base model shared by every structured AI output model.

    Unknown fields are rejected so malformed or unexpected AI output
    cannot silently enter downstream renderers or databases.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class SourceEvidence(StrictBaseModel):
    """
    Traceable evidence supporting an extracted fact.
    """

    evidence_type: EvidenceType
    post_id: str | None = None
    attachment_filename: str | None = None
    source_url: str | None = None
    quote: str | None = None

    @model_validator(mode="after")
    def validate_evidence_reference(
        self,
    ) -> SourceEvidence:
        if not any(
            [
                self.post_id,
                self.attachment_filename,
                self.source_url,
                self.quote,
            ]
        ):
            raise ValueError(
                "Evidence must contain at least one reference "
                "such as post_id, attachment_filename, "
                "source_url, or quote."
            )

        return self


class ExtractedEntity(StrictBaseModel):
    """
    Generic named entity found in a technical document.
    """

    entity_type: EntityType
    name: str = Field(min_length=1)
    normalized_name: str | None = None
    description: str | None = None
    role: str | None = None
    aliases: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = "medium"
    evidence: list[SourceEvidence] = Field(
        default_factory=list
    )

    @field_validator("aliases")
    @classmethod
    def deduplicate_aliases(
        cls,
        aliases: list[str],
    ) -> list[str]:
        unique_aliases: list[str] = []
        seen: set[str] = set()

        for alias in aliases:
            normalized = alias.strip()

            if not normalized:
                continue

            key = normalized.casefold()

            if key not in seen:
                seen.add(key)
                unique_aliases.append(normalized)

        return unique_aliases


class VehicleEntity(StrictBaseModel):
    manufacturer: str | None = None
    model: str = Field(min_length=1)
    variant: str | None = None
    production_year: int | None = Field(
        default=None,
        ge=1880,
        le=2100,
    )
    drive_configuration: str | None = None
    vehicle_type: str | None = None
    gross_weight_kg: float | None = Field(
        default=None,
        ge=0,
    )
    empty_weight_kg: float | None = Field(
        default=None,
        ge=0,
    )
    confidence: ConfidenceLevel = "medium"
    evidence: list[SourceEvidence] = Field(
        default_factory=list
    )


class EngineEntity(StrictBaseModel):
    manufacturer: str | None = None
    model: str = Field(min_length=1)
    engine_type: str | None = None
    cylinder_count: int | None = Field(
        default=None,
        ge=1,
        le=32,
    )
    displacement_cc: float | None = Field(
        default=None,
        ge=0,
    )
    power_hp: float | None = Field(
        default=None,
        ge=0,
    )
    power_kw: float | None = Field(
        default=None,
        ge=0,
    )
    fuel_type: str | None = None
    cooling_type: str | None = None
    confidence: ConfidenceLevel = "medium"
    evidence: list[SourceEvidence] = Field(
        default_factory=list
    )


class TransmissionEntity(StrictBaseModel):
    manufacturer: str | None = None
    model: str = Field(min_length=1)
    transmission_type: str | None = None
    gear_count: int | None = Field(
        default=None,
        ge=1,
        le=32,
    )
    notes: str | None = None
    confidence: ConfidenceLevel = "medium"
    evidence: list[SourceEvidence] = Field(
        default_factory=list
    )


class ContactDetail(StrictBaseModel):
    organization: str | None = None
    person_name: str | None = None
    role: str | None = None
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    fax: str | None = None
    website: str | None = None
    address: str | None = None
    coordinates: str | None = None
    confidence: ConfidenceLevel = "medium"
    evidence: list[SourceEvidence] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_contact_content(
        self,
    ) -> ContactDetail:
        meaningful_fields = [
            self.organization,
            self.person_name,
            self.email,
            self.phone,
            self.mobile,
            self.fax,
            self.website,
            self.address,
            self.coordinates,
        ]

        if not any(meaningful_fields):
            raise ValueError(
                "Contact detail must contain at least one "
                "organization, person, email, phone, website, "
                "address, or coordinate value."
            )

        return self


class TechnicalSpecification(StrictBaseModel):
    name: str = Field(min_length=1)
    value: str | int | float | bool
    unit: str | None = None
    category: str | None = None
    normalized_value: float | None = None
    normalized_unit: str | None = None
    confidence: ConfidenceLevel = "medium"
    evidence: list[SourceEvidence] = Field(
        default_factory=list
    )


class PartReference(StrictBaseModel):
    name: str = Field(min_length=1)
    manufacturer: str | None = None
    part_number: str | None = None
    alternative_part_numbers: list[str] = Field(
        default_factory=list
    )
    description: str | None = None
    confidence: ConfidenceLevel = "medium"
    evidence: list[SourceEvidence] = Field(
        default_factory=list
    )


class MaintenanceTask(StrictBaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    system_category: str | None = None
    action_type: str | None = None
    tools: list[str] = Field(default_factory=list)
    parts: list[str] = Field(default_factory=list)
    measurements: list[str] = Field(
        default_factory=list
    )
    warnings: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = "medium"
    evidence: list[SourceEvidence] = Field(
        default_factory=list
    )


class DiagnosticFinding(StrictBaseModel):
    symptom: str = Field(min_length=1)
    possible_causes: list[str] = Field(
        default_factory=list
    )
    recommended_actions: list[str] = Field(
        default_factory=list
    )
    confidence: ConfidenceLevel = "medium"
    evidence: list[SourceEvidence] = Field(
        default_factory=list
    )


class TechnicalWarning(StrictBaseModel):
    warning_type: str
    description: str = Field(min_length=1)
    severity: Literal[
        "informational",
        "caution",
        "warning",
        "critical",
    ] = "caution"
    evidence: list[SourceEvidence] = Field(
        default_factory=list
    )


class TranslationQuality(StrictBaseModel):
    source_language: str = "de"
    target_language: str = "en"
    translated: bool = False
    protected_token_count: int = Field(
        default=0,
        ge=0,
    )
    preserved_token_count: int = Field(
        default=0,
        ge=0,
    )
    fidelity_score: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )
    validation_warnings: list[str] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_preservation_counts(
        self,
    ) -> TranslationQuality:
        if (
            self.preserved_token_count
            > self.protected_token_count
        ):
            raise ValueError(
                "preserved_token_count cannot exceed "
                "protected_token_count."
            )

        return self


class ProcessingMetadata(StrictBaseModel):
    schema_version: str = "1.0.0"
    extraction_provider: str | None = None
    extraction_model: str | None = None
    generated_at: str = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )
    source_stage: str = "content_aggregated"
    output_stage: str = "structured_knowledge"
    ready_for_rendering: bool = False
    warnings: list[str] = Field(default_factory=list)


class StructuredTechnicalDocument(StrictBaseModel):
    """
    Canonical structured output produced after AI extraction.

    Markdown, CSV, PostgreSQL, and future API renderers should
    consume this model rather than raw model-provider output.
    """

    document_id: str = Field(min_length=1)
    document_type: str = "forum_thread"
    title: str = Field(min_length=1)

    source_language: str = "de"
    output_language: str = "en"

    source: dict[str, Any] = Field(
        default_factory=dict
    )

    summary: str = Field(min_length=1)
    topics: list[str] = Field(default_factory=list)
    system_categories: list[str] = Field(
        default_factory=list
    )

    entities: list[ExtractedEntity] = Field(
        default_factory=list
    )
    vehicles: list[VehicleEntity] = Field(
        default_factory=list
    )
    engines: list[EngineEntity] = Field(
        default_factory=list
    )
    transmissions: list[TransmissionEntity] = Field(
        default_factory=list
    )
    contacts: list[ContactDetail] = Field(
        default_factory=list
    )

    technical_specifications: list[
        TechnicalSpecification
    ] = Field(default_factory=list)

    parts: list[PartReference] = Field(
        default_factory=list
    )
    maintenance_tasks: list[MaintenanceTask] = Field(
        default_factory=list
    )
    diagnostics: list[DiagnosticFinding] = Field(
        default_factory=list
    )
    warnings: list[TechnicalWarning] = Field(
        default_factory=list
    )

    recommendations: list[str] = Field(
        default_factory=list
    )
    technical_references: list[str] = Field(
        default_factory=list
    )

    translated_markdown_content: str | None = None

    translation_quality: TranslationQuality = Field(
        default_factory=TranslationQuality
    )
    processing: ProcessingMetadata = Field(
        default_factory=ProcessingMetadata
    )

    @field_validator(
        "topics",
        "system_categories",
        "recommendations",
        "technical_references",
    )
    @classmethod
    def normalize_string_lists(
        cls,
        values: list[str],
    ) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        for value in values:
            cleaned_value = value.strip()

            if not cleaned_value:
                continue

            key = cleaned_value.casefold()

            if key not in seen:
                seen.add(key)
                result.append(cleaned_value)

        return result