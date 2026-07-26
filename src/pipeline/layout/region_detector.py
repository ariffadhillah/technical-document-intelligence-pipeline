from __future__ import annotations

import cv2
import numpy as np

from .models import (
    BoundingBox,
    LayoutRegion,
)


class StructuralRegionDetector:
    """
    Detect broad structural page regions.

    This is heuristic and deterministic.
    """

    def __init__(
        self,
        *,
        minimum_region_area_ratio: float = 0.01,
    ) -> None:
        self.minimum_region_area_ratio = (
            minimum_region_area_ratio
        )

    def detect(
        self,
        image: np.ndarray,
    ) -> list[LayoutRegion]:
        height, width = image.shape[:2]

        regions: list[LayoutRegion] = []

        regions.extend(
            self._detect_header_footer(
                image=image,
                width=width,
                height=height,
            )
        )

        regions.extend(
            self._detect_sidebars(
                image=image,
                width=width,
                height=height,
            )
        )

        regions.extend(
            self._detect_image_regions(
                image=image,
                width=width,
                height=height,
            )
        )

        return self._remove_duplicates(
            regions
        )

    def _detect_header_footer(
        self,
        *,
        image: np.ndarray,
        width: int,
        height: int,
    ) -> list[LayoutRegion]:
        grayscale = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        header_height = max(
            int(height * 0.16),
            1,
        )

        footer_start = int(
            height * 0.84
        )

        regions: list[LayoutRegion] = []

        header = grayscale[
            0:header_height,
            :,
        ]

        footer = grayscale[
            footer_start:height,
            :,
        ]

        if self._region_has_content(header):
            regions.append(
                LayoutRegion(
                    region_type="header",
                    bounding_box=BoundingBox(
                        x=0,
                        y=0,
                        width=width,
                        height=header_height,
                    ),
                    confidence=0.65,
                )
            )

        if self._region_has_content(footer):
            regions.append(
                LayoutRegion(
                    region_type="footer",
                    bounding_box=BoundingBox(
                        x=0,
                        y=footer_start,
                        width=width,
                        height=(
                            height - footer_start
                        ),
                    ),
                    confidence=0.65,
                )
            )

        return regions

    def _detect_sidebars(
        self,
        *,
        image: np.ndarray,
        width: int,
        height: int,
    ) -> list[LayoutRegion]:
        grayscale = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        sidebar_width = max(
            int(width * 0.15),
            1,
        )

        left = grayscale[
            :,
            0:sidebar_width,
        ]

        right_start = int(
            width * 0.85
        )

        right = grayscale[
            :,
            right_start:width,
        ]

        regions: list[LayoutRegion] = []

        if self._region_has_content(left):
            regions.append(
                LayoutRegion(
                    region_type="sidebar",
                    bounding_box=BoundingBox(
                        x=0,
                        y=0,
                        width=sidebar_width,
                        height=height,
                    ),
                    confidence=0.55,
                    metadata={
                        "side": "left",
                    },
                )
            )

        if self._region_has_content(right):
            regions.append(
                LayoutRegion(
                    region_type="sidebar",
                    bounding_box=BoundingBox(
                        x=right_start,
                        y=0,
                        width=(
                            width - right_start
                        ),
                        height=height,
                    ),
                    confidence=0.55,
                    metadata={
                        "side": "right",
                    },
                )
            )

        return regions

    def _detect_image_regions(
        self,
        *,
        image: np.ndarray,
        width: int,
        height: int,
    ) -> list[LayoutRegion]:
        grayscale = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        blurred = cv2.GaussianBlur(
            grayscale,
            (5, 5),
            0,
        )

        edges = cv2.Canny(
            blurred,
            60,
            160,
        )

        closed = cv2.morphologyEx(
            edges,
            cv2.MORPH_CLOSE,
            cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (15, 15),
            ),
        )

        contours, _ = cv2.findContours(
            closed,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        page_area = width * height

        regions: list[LayoutRegion] = []

        for contour in contours:
            x, y, region_width, region_height = (
                cv2.boundingRect(contour)
            )

            area_ratio = (
                region_width
                * region_height
                / max(page_area, 1)
            )

            if (
                area_ratio
                < self.minimum_region_area_ratio
            ):
                continue

            if region_width < 40:
                continue

            if region_height < 40:
                continue

            crop = image[
                y:y + region_height,
                x:x + region_width,
            ]

            color_variance = float(
                np.mean(
                    [
                        np.var(channel)
                        for channel
                        in cv2.split(crop)
                    ]
                )
            )

            if color_variance < 250:
                continue

            regions.append(
                LayoutRegion(
                    region_type="image",
                    bounding_box=BoundingBox(
                        x=x,
                        y=y,
                        width=region_width,
                        height=region_height,
                    ),
                    confidence=min(
                        0.50
                        + area_ratio,
                        0.90,
                    ),
                    metadata={
                        "area_ratio": round(
                            area_ratio,
                            4,
                        ),
                        "color_variance": round(
                            color_variance,
                            2,
                        ),
                    },
                )
            )

        return regions

    @staticmethod
    def _region_has_content(
        region: np.ndarray,
    ) -> bool:
        if region.size == 0:
            return False

        standard_deviation = float(
            np.std(region)
        )

        dark_ratio = float(
            np.count_nonzero(region < 220)
        ) / float(region.size)

        return (
            standard_deviation >= 18
            and dark_ratio >= 0.015
        )

    @staticmethod
    def _remove_duplicates(
        regions: list[LayoutRegion],
    ) -> list[LayoutRegion]:
        unique: list[LayoutRegion] = []

        for region in regions:
            duplicate = False

            for existing in unique:
                if (
                    existing.region_type
                    != region.region_type
                ):
                    continue

                if (
                    StructuralRegionDetector
                    ._intersection_over_union(
                        existing.bounding_box,
                        region.bounding_box,
                    )
                    >= 0.80
                ):
                    duplicate = True
                    break

            if not duplicate:
                unique.append(region)

        return unique

    @staticmethod
    def _intersection_over_union(
        first: BoundingBox,
        second: BoundingBox,
    ) -> float:
        x_left = max(first.x, second.x)
        y_top = max(first.y, second.y)

        x_right = min(
            first.x + first.width,
            second.x + second.width,
        )

        y_bottom = min(
            first.y + first.height,
            second.y + second.height,
        )

        if (
            x_right <= x_left
            or y_bottom <= y_top
        ):
            return 0.0

        intersection = (
            x_right - x_left
        ) * (
            y_bottom - y_top
        )

        union = (
            first.area
            + second.area
            - intersection
        )

        if union <= 0:
            return 0.0

        return intersection / union