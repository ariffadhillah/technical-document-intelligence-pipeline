from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BoundingBox:
    x: int
    y: int
    width: int
    height: int

    @property
    def area(self) -> int:
        return self.width * self.height

    def to_dict(self) -> dict[str, int]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass(slots=True)
class LayoutRegion:
    region_type: str
    bounding_box: BoundingBox
    confidence: float
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_type": self.region_type,
            "bounding_box": (
                self.bounding_box.to_dict()
            ),
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class PageLayoutResult:
    page_number: int
    width: int
    height: int

    regions: list[LayoutRegion] = field(
        default_factory=list
    )

    likely_multi_column: bool = False
    column_count: int = 1
    likely_table: bool = False
    qr_code_count: int = 0
    logo_count: int = 0
    image_region_count: int = 0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def regions_by_type(
        self,
        region_type: str,
    ) -> list[LayoutRegion]:
        return [
            region
            for region in self.regions
            if region.region_type == region_type
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "likely_multi_column": (
                self.likely_multi_column
            ),
            "column_count": self.column_count,
            "likely_table": self.likely_table,
            "qr_code_count": (
                self.qr_code_count
            ),
            "logo_count": self.logo_count,
            "image_region_count": (
                self.image_region_count
            ),
            "regions": [
                region.to_dict()
                for region in self.regions
            ],
            "metadata": dict(self.metadata),
        }