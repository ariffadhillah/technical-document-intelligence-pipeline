from __future__ import annotations

import logging

import numpy as np

from .column_detector import (
    ColumnRegionDetector,
)
from .models import PageLayoutResult
from .qr_detector import (
    QRCodeRegionDetector,
)
from .region_detector import (
    StructuralRegionDetector,
)
from .table_detector import (
    TableRegionDetector,
)

logger = logging.getLogger(__name__)


class PageLayoutAnalyzer:
    """
    Detect structural regions on a page.
    """

    def __init__(
        self,
        *,
        structural_detector: (
            StructuralRegionDetector | None
        ) = None,
        column_detector: (
            ColumnRegionDetector | None
        ) = None,
        table_detector: (
            TableRegionDetector | None
        ) = None,
        qr_detector: (
            QRCodeRegionDetector | None
        ) = None,
    ) -> None:
        self.structural_detector = (
            structural_detector
            or StructuralRegionDetector()
        )

        self.column_detector = (
            column_detector
            or ColumnRegionDetector()
        )

        self.table_detector = (
            table_detector
            or TableRegionDetector()
        )

        self.qr_detector = (
            qr_detector
            or QRCodeRegionDetector()
        )

    def analyze(
        self,
        *,
        image: np.ndarray,
        page_number: int,
    ) -> PageLayoutResult:
        if image is None or image.size == 0:
            raise ValueError(
                "Layout analysis image is empty."
            )

        height, width = image.shape[:2]

        structural_regions = (
            self.structural_detector.detect(
                image
            )
        )

        column_regions, column_count = (
            self.column_detector.detect(
                image
            )
        )

        table_regions = (
            self.table_detector.detect(
                image
            )
        )

        qr_regions = (
            self.qr_detector.detect(
                image
            )
        )

        regions = [
            *structural_regions,
            *column_regions,
            *table_regions,
            *qr_regions,
        ]

        image_region_count = sum(
            region.region_type == "image"
            for region in regions
        )

        logo_count = sum(
            region.region_type == "logo"
            for region in regions
        )

        result = PageLayoutResult(
            page_number=page_number,
            width=width,
            height=height,
            regions=regions,
            likely_multi_column=(
                column_count >= 2
            ),
            column_count=column_count,
            likely_table=bool(
                table_regions
            ),
            qr_code_count=len(
                qr_regions
            ),
            logo_count=logo_count,
            image_region_count=(
                image_region_count
            ),
            metadata={
                "analyzer": (
                    self.__class__.__name__
                ),
                "strategy": (
                    "opencv_region_detection"
                ),
            },
        )

        logger.info(
            "Page layout analysis completed: "
            "page=%s columns=%s tables=%s "
            "images=%s qr_codes=%s regions=%s",
            page_number,
            result.column_count,
            len(table_regions),
            image_region_count,
            len(qr_regions),
            len(regions),
        )

        return result