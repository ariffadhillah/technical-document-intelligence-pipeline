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
from pydantic.json_schema import JsonSchemaValue


ConfidenceLevel = Literal["low", "medium", "high"]

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

OrganizationType = Literal[
    "manufacturer",
    "supplier",
    "fabricator",
    "workshop",
    "dealer",
    "distributor",
    "service_center",
    "engineering_company",
    "restoration_company",
    "coating_company",
    "government_agency",
    "military_organization",
    "standards_organization",
    "certification_body",
    "other",
    "unknown",
]

OrganizationRelationshipType = Literal[
    "partner",
    "supplier",
    "distributor",
    "dealer",
    "service_provider",
    "manufacturer",
    "represented_brand",
    "subsidiary",
    "parent_company",
    "customer",
    "other",
]

TechnicalReferenceType = Literal[
    "manufacturer_document",
    "service_manual",
    "workshop_manual",
    "parts_catalog",
    "product_catalog",
    "technical_drawing",
    "product_datasheet",
    "quotation",
    "brochure",
    "regulation",
    "standard",
    "book",
    "website",
    "forum_thread",
    "model_reference",
    "part_reference",
    "other",
]


def _make_openai_schema_strict(
    schema: Any,
) -> Any:
    """
    Convert Pydantic JSON Schema into the strict subset required by
    OpenAI Structured Outputs.

    OpenAI requires every object property to appear in ``required``.
    Optional values therefore remain required keys whose value can be
    null. Defaults are removed because the Structured Outputs subset
    does not use them.
    """
    if isinstance(schema, dict):
        schema.pop("default", None)

        properties = schema.get("properties")

        if isinstance(properties, dict):
            schema["required"] = list(properties.keys())
            schema["additionalProperties"] = False

        for key, value in list(schema.items()):
            schema[key] = _make_openai_schema_strict(value)

        return schema

    if isinstance(schema, list):
        return [
            _make_openai_schema_strict(item)
            for item in schema
        ]

    return schema


class StrictBaseModel(BaseModel):
    """
    Base class for canonical structured extraction models.

    Runtime validation remains strict, while the generated JSON Schema
    is normalized for OpenAI Structured Outputs.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: Any,
        handler: Any,
    ) -> JsonSchemaValue:
        schema = handler(core_schema)
        return _make_openai_schema_strict(schema)


class DocumentSource(StrictBaseModel):
    """
    Stable source metadata supplied by the extraction model.

    The previous ``dict[str, Any]`` field was intentionally replaced:
    unrestricted dictionaries are not compatible with strict Structured
    Outputs schemas.
    """

    document_id: str | None = None
    thread_id: str | None = None
    thread_url: str | None = None
    source_url: str | None = None
    forum_name: str | None = None
    title: str | None = None
    author: str | None = None
    created_at: str | None = None
    post_count: int | None = Field(default=None, ge=0)
    attachment_count: int | None = Field(default=None, ge=0)


class SourceEvidence(StrictBaseModel):
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
            (
                self.post_id,
                self.attachment_filename,
                self.source_url,
                self.quote,
            )
        ):
            raise ValueError(
                "Evidence must contain at least one reference: "
                "post_id, attachment_filename, source_url, or quote."
            )

        return self


class ExtractedEntity(StrictBaseModel):
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
        meaningful_fields = (
            self.organization,
            self.person_name,
            self.email,
            self.phone,
            self.mobile,
            self.fax,
            self.website,
            self.address,
            self.coordinates,
        )

        if not any(meaningful_fields):
            raise ValueError(
                "Contact detail must contain at least one "
                "meaningful contact value."
            )

        return self


class OrganizationService(StrictBaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    category: str | None = None
    price: float | None = Field(default=None, ge=0)
    currency: str | None = None
    price_basis: str | None = None
    confidence: ConfidenceLevel = "medium"
    evidence: list[SourceEvidence] = Field(
        default_factory=list
    )


class OrganizationRelationship(StrictBaseModel):
    relationship_type: OrganizationRelationshipType
    target_organization: str = Field(min_length=1)
    description: str | None = None
    confidence: ConfidenceLevel = "medium"
    evidence: list[SourceEvidence] = Field(
        default_factory=list
    )


class OrganizationProfile(StrictBaseModel):
    name: str = Field(min_length=1)
    normalized_name: str | None = None
    organization_type: OrganizationType = "unknown"
    description: str | None = None

    capabilities: list[str] = Field(
        default_factory=list
    )
    products: list[str] = Field(
        default_factory=list
    )
    services: list[OrganizationService] = Field(
        default_factory=list
    )
    represented_brands: list[str] = Field(
        default_factory=list
    )
    certifications: list[str] = Field(
        default_factory=list
    )
    relationships: list[
        OrganizationRelationship
    ] = Field(default_factory=list)

    contact: ContactDetail | None = None
    country: str | None = None
    city: str | None = None
    notes: str | None = None
    confidence: ConfidenceLevel = "medium"
    evidence: list[SourceEvidence] = Field(
        default_factory=list
    )

    @field_validator(
        "capabilities",
        "products",
        "represented_brands",
        "certifications",
    )
    @classmethod
    def normalize_organization_string_lists(
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


class TechnicalReference(StrictBaseModel):
    reference_type: TechnicalReferenceType = "other"
    title: str = Field(min_length=1)
    identifier: str | None = None
    organization: str | None = None
    url: str | None = None
    description: str | None = None
    confidence: ConfidenceLevel = "medium"
    evidence: list[SourceEvidence] = Field(
        default_factory=list
    )


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
    # Translation metrics are updated by the AI stage after the provider
    # response has already been validated. Disabling assignment validation
    # here prevents a temporary invalid state when the two counters are
    # updated sequentially (for example, protected=0 while preserved is
    # still 5). Full model validation still runs when the object is created.
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=False,
    )

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
    schema_version: str = "2.1.0"
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
    """

    document_id: str = Field(min_length=1)
    document_type: str = "forum_thread"
    title: str = Field(min_length=1)

    source_language: str = "de"
    output_language: str = "en"

    source: DocumentSource = Field(
        default_factory=DocumentSource
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
    organizations: list[OrganizationProfile] = Field(
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
    technical_references: list[
        TechnicalReference
    ] = Field(default_factory=list)

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
