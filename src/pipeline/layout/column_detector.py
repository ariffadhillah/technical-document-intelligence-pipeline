from __future__ import annotations

import cv2
import numpy as np

from .models import (
    BoundingBox,
    LayoutRegion,
)


class ColumnRegionDetector:
    """
    Detect likely document columns using vertical
    whitespace projection.
    """

    def __init__(
        self,
        *,
        minimum_gap_ratio: float = 0.025,
        minimum_column_ratio: float = 0.18,
    ) -> None:
        self.minimum_gap_ratio = (
            minimum_gap_ratio
        )
        self.minimum_column_ratio = (
            minimum_column_ratio
        )

    def detect(
        self,
        image: np.ndarray,
    ) -> tuple[
        list[LayoutRegion],
        int,
    ]:
        height, width = image.shape[:2]

        grayscale = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        _, binary = cv2.threshold(
            grayscale,
            0,
            255,
            cv2.THRESH_BINARY_INV
            | cv2.THRESH_OTSU,
        )

        projection = np.sum(
            binary > 0,
            axis=0,
        )

        low_content_threshold = max(
            int(height * 0.015),
            1,
        )

        whitespace_mask = (
            projection
            <= low_content_threshold
        )

        gaps = self._continuous_ranges(
            whitespace_mask
        )

        minimum_gap_width = max(
            int(width * self.minimum_gap_ratio),
            5,
        )

        meaningful_gaps = [
            (start, end)
            for start, end in gaps
            if (
                end - start
                >= minimum_gap_width
            )
            and start > width * 0.08
            and end < width * 0.92
        ]

        boundaries = [0]

        boundaries.extend(
            int((start + end) / 2)
            for start, end in meaningful_gaps
        )

        boundaries.append(width)

        regions: list[LayoutRegion] = []

        minimum_column_width = (
            width
            * self.minimum_column_ratio
        )

        for index in range(
            len(boundaries) - 1
        ):
            start = boundaries[index]
            end = boundaries[index + 1]

            column_width = end - start

            if (
                column_width
                < minimum_column_width
            ):
                continue

            regions.append(
                LayoutRegion(
                    region_type="column",
                    bounding_box=BoundingBox(
                        x=start,
                        y=0,
                        width=column_width,
                        height=height,
                    ),
                    confidence=0.70,
                    metadata={
                        "column_index": (
                            len(regions) + 1
                        ),
                    },
                )
            )

        column_count = max(
            len(regions),
            1,
        )

        return regions, column_count

    @staticmethod
    def _continuous_ranges(
        mask: np.ndarray,
    ) -> list[tuple[int, int]]:
        ranges: list[
            tuple[int, int]
        ] = []

        start: int | None = None

        for index, enabled in enumerate(mask):
            if enabled and start is None:
                start = index

            if not enabled and start is not None:
                ranges.append(
                    (start, index)
                )
                start = None

        if start is not None:
            ranges.append(
                (start, len(mask))
            )

        return ranges