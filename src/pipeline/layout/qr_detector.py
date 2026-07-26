from __future__ import annotations

import cv2
import numpy as np

from .models import (
    BoundingBox,
    LayoutRegion,
)


class QRCodeRegionDetector:
    """
    Detect QR codes using OpenCV.
    """

    def __init__(self) -> None:
        self.detector = cv2.QRCodeDetector()

    def detect(
        self,
        image: np.ndarray,
    ) -> list[LayoutRegion]:
        regions: list[LayoutRegion] = []

        try:
            detected, decoded_info, points, _ = (
                self.detector.detectAndDecodeMulti(
                    image
                )
            )
        except cv2.error:
            detected = False
            decoded_info = ()
            points = None

        if detected and points is not None:
            for index, polygon in enumerate(points):
                x, y, width, height = (
                    cv2.boundingRect(
                        polygon.astype(
                            np.float32
                        )
                    )
                )

                decoded_value = (
                    decoded_info[index]
                    if index < len(decoded_info)
                    else ""
                )

                regions.append(
                    LayoutRegion(
                        region_type="qr_code",
                        bounding_box=BoundingBox(
                            x=x,
                            y=y,
                            width=width,
                            height=height,
                        ),
                        confidence=0.95,
                        metadata={
                            "decoded_value": (
                                decoded_value
                            ),
                        },
                    )
                )

        if regions:
            return regions

        decoded_value, points, _ = (
            self.detector.detectAndDecode(
                image
            )
        )

        if points is None:
            return []

        polygon = points.astype(
            np.float32
        )

        x, y, width, height = (
            cv2.boundingRect(polygon)
        )

        return [
            LayoutRegion(
                region_type="qr_code",
                bounding_box=BoundingBox(
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                ),
                confidence=0.90,
                metadata={
                    "decoded_value": decoded_value,
                },
            )
        ]