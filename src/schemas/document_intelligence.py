from pydantic import BaseModel, Field


class TechnicalEntities(BaseModel):
    """
    Technical entities extracted from the document.

    Empty strings or null values are allowed when information
    is not explicitly available in the source text.
    """

    vehicle: str | None = Field(
        default=None,
        description=(
            "Vehicle manufacturer and model explicitly "
            "mentioned in the document."
        ),
    )

    vehicle_type: str | None = Field(
        default=None,
        description="Vehicle type or technical type code.",
    )

    manufacturing_year: int | None = Field(
        default=None,
        description="Vehicle manufacturing year.",
    )

    drivetrain: str | None = Field(
        default=None,
        description="Drivetrain configuration such as 6x6.",
    )

    engine: str | None = Field(
        default=None,
        description="Engine manufacturer and model.",
    )

    engine_displacement_cc: int | None = Field(
        default=None,
        description="Engine displacement in cubic centimeters.",
    )

    power_hp: int | None = Field(
        default=None,
        description="Engine power in horsepower.",
    )

    power_kw: int | None = Field(
        default=None,
        description="Engine power in kilowatts.",
    )

    transmission: str | None = Field(
        default=None,
        description="Transmission or gearbox description.",
    )

    empty_weight_kg: int | None = Field(
        default=None,
        description="Empty vehicle weight in kilograms.",
    )

    gross_weight_kg: int | None = Field(
        default=None,
        description="Maximum permissible gross weight.",
    )

    manufacturers: list[str] = Field(
        default_factory=list,
        description=(
            "Manufacturers, brands, and technical suppliers "
            "explicitly mentioned."
        ),
    )

    technical_components: list[str] = Field(
        default_factory=list,
        description=(
            "Important technical components explicitly "
            "mentioned in the document."
        ),
    )


class DocumentIntelligenceResult(BaseModel):
    """
    Validated AI output for one OCR document.
    """

    document_type: str = Field(
        description=(
            "Document category, for example technical quotation, "
            "invoice, specification, manual, or correspondence."
        ),
    )

    source_language: str = Field(
        description="Original language of the document.",
    )

    title: str = Field(
        description=(
            "A concise descriptive title generated from "
            "the document contents."
        ),
    )

    summary_en: str = Field(
        description=(
            "A concise English summary of the document."
        ),
    )

    corrected_text_de: str = Field(
        description=(
            "Corrected German OCR text, preserving the original "
            "meaning, structure, units, product names, and numbers."
        ),
    )

    translation_en: str = Field(
        description=(
            "Faithful English translation of the corrected text."
        ),
    )

    technical_entities: TechnicalEntities

    keywords: list[str] = Field(
        default_factory=list,
        description=(
            "Searchable English keywords relevant to the document."
        ),
    )

    correction_notes: list[str] = Field(
        default_factory=list,
        description=(
            "Important OCR corrections made with reasonable "
            "confidence. Do not list stylistic changes."
        ),
    )

    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Uncertain, ambiguous, incomplete, or potentially "
            "incorrect source details."
        ),
    )