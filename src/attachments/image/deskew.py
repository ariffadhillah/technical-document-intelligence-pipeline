from __future__ import annotations

import cv2
import numpy as np


class DeskewProcessor:
    """
    Automatically straighten scanned documents.
    """

    def deskew(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        gray = cv2.bitwise_not(gray)

        thresh = cv2.threshold(
            gray,
            0,
            255,
            cv2.THRESH_BINARY | cv2.THRESH_OTSU,
        )[1]

        coords = np.column_stack(
            np.where(thresh > 0)
        )

        angle = cv2.minAreaRect(
            coords
        )[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        h, w = image.shape[:2]

        center = (w // 2, h // 2)

        matrix = cv2.getRotationMatrix2D(
            center,
            angle,
            1.0,
        )

        return cv2.warpAffine(
            image,
            matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )