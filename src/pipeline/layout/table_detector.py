from __future__ import annotations

import cv2
import numpy as np

from .models import (
    BoundingBox,
    LayoutRegion,
)


class TableRegionDetector:
    """
    Detect table-like line structures.
    """

    def detect(
        self,
        image: np.ndarray,
    ) -> list[LayoutRegion]:
        grayscale = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        inverted = cv2.bitwise_not(
            grayscale
        )

        _, binary = cv2.threshold(
            inverted,
            0,
            255,
            cv2.THRESH_BINARY
            | cv2.THRESH_OTSU,
        )

        height, width = binary.shape

        horizontal_kernel_width = max(
            width // 30,
            20,
        )

        vertical_kernel_height = max(
            height // 30,
            20,
        )

        horizontal = cv2.morphologyEx(
            binary,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (
                    horizontal_kernel_width,
                    1,
                ),
            ),
        )

        vertical = cv2.morphologyEx(
            binary,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (
                    1,
                    vertical_kernel_height,
                ),
            ),
        )

        table_mask = cv2.bitwise_or(
            horizontal,
            vertical,
        )

        table_mask = cv2.dilate(
            table_mask,
            cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (7, 7),
            ),
            iterations=2,
        )

        contours, _ = cv2.findContours(
            table_mask,
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

            if area_ratio < 0.01:
                continue

            regions.append(
                LayoutRegion(
                    region_type="table",
                    bounding_box=BoundingBox(
                        x=x,
                        y=y,
                        width=region_width,
                        height=region_height,
                    ),
                    confidence=min(
                        0.60
                        + area_ratio,
                        0.95,
                    ),
                    metadata={
                        "area_ratio": round(
                            area_ratio,
                            4,
                        ),
                    },
                )
            )

        return regions