from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Final


class ImageOperation(str, Enum):
    """
    Supported preprocessing operations.
    """

    ORIENTATION = "orientation"

    DESKEW = "deskew"

    RESIZE = "resize"

    GRAYSCALE = "grayscale"

    DENOISE = "denoise"

    CLAHE = "clahe"

    ADAPTIVE_THRESHOLD = "adaptive_threshold"

    OTSU_THRESHOLD = "otsu_threshold"

    MORPHOLOGY = "morphology"

    SHARPEN = "sharpen"

    AUTO_CONTRAST = "auto_contrast"

    REMOVE_BORDER = "remove_border"

    REMOVE_SHADOW = "remove_shadow"

    PERSPECTIVE_CORRECTION = "perspective_correction"

    SUPER_RESOLUTION = "super_resolution"


@dataclass(slots=True)
class ImageProfile:
    """
    OCR preprocessing profile.

    A profile defines WHICH operations
    should be executed and in WHICH order.
    """

    name: str

    operations: list[ImageOperation] = field(
        default_factory=list
    )

    resize_scale: float = 2.0

    description: str = ""


# =====================================================
# Technical Manual
# =====================================================

MANUAL_PROFILE = ImageProfile(
    name="manual",
    description="Scanned manuals and technical documents.",
    operations=[
        ImageOperation.ORIENTATION,
        ImageOperation.DESKEW,
        ImageOperation.GRAYSCALE,
        ImageOperation.DENOISE,
        ImageOperation.CLAHE,
        ImageOperation.ADAPTIVE_THRESHOLD,
        ImageOperation.MORPHOLOGY,
        ImageOperation.SHARPEN,
    ],
)

# =====================================================
# Invoice
# =====================================================

INVOICE_PROFILE = ImageProfile(
    name="invoice",
    description="Invoices, receipts and financial documents.",
    operations=[
        ImageOperation.ORIENTATION,
        ImageOperation.DESKEW,
        ImageOperation.GRAYSCALE,
        ImageOperation.ADAPTIVE_THRESHOLD,
        ImageOperation.MORPHOLOGY,
    ],
)

# =====================================================
# Brochure
# =====================================================

BROCHURE_PROFILE = ImageProfile(
    name="brochure",
    description="Marketing brochures and catalogs.",
    operations=[
        ImageOperation.ORIENTATION,
        ImageOperation.GRAYSCALE,
    ],
)

# =====================================================
# Flyer
# =====================================================

FLYER_PROFILE = ImageProfile(
    name="flyer",
    description="Flyers and advertisements.",
    operations=[
        ImageOperation.ORIENTATION,
        ImageOperation.GRAYSCALE,
        ImageOperation.CLAHE,
    ],
)

# =====================================================
# Wiring Diagram
# =====================================================

WIRING_PROFILE = ImageProfile(
    name="wiring",
    description="Electrical wiring diagrams and CAD drawings.",
    resize_scale=3.0,
    operations=[
        ImageOperation.ORIENTATION,
        ImageOperation.DESKEW,
        ImageOperation.RESIZE,
        ImageOperation.GRAYSCALE,
        ImageOperation.SHARPEN,
    ],
)

# =====================================================
# Engineering Drawing
# =====================================================

DRAWING_PROFILE = ImageProfile(
    name="drawing",
    description="Mechanical and engineering drawings.",
    resize_scale=3.0,
    operations=[
        ImageOperation.ORIENTATION,
        ImageOperation.DESKEW,
        ImageOperation.RESIZE,
        ImageOperation.GRAYSCALE,
        ImageOperation.SHARPEN,
        ImageOperation.ADAPTIVE_THRESHOLD,
    ],
)

# =====================================================
# Generic Document
# =====================================================

DOCUMENT_PROFILE = ImageProfile(
    name="document",
    description="Default document profile.",
    operations=[
        ImageOperation.ORIENTATION,
        ImageOperation.DESKEW,
        ImageOperation.GRAYSCALE,
        ImageOperation.DENOISE,
        ImageOperation.CLAHE,
        ImageOperation.ADAPTIVE_THRESHOLD,
    ],
)

# =====================================================
# Registry
# =====================================================

IMAGE_PROFILES: Final[dict[str, ImageProfile]] = {
    profile.name: profile
    for profile in (
        DOCUMENT_PROFILE,
        MANUAL_PROFILE,
        INVOICE_PROFILE,
        BROCHURE_PROFILE,
        FLYER_PROFILE,
        WIRING_PROFILE,
        DRAWING_PROFILE,
    )
}