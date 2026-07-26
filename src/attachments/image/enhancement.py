from __future__ import annotations

import cv2
import numpy as np


class ImageEnhancer:
    """
    Image enhancement pipeline for OCR.

    Every step can be enabled/disabled independently.

    Pipeline

        RGB
          │
          ▼
      Grayscale
          │
          ▼
       Denoise
          │
          ▼
        CLAHE
          │
          ▼
     Adaptive Threshold
          │
          ▼
       Morphology
          │
          ▼
        Sharpen
    """

    def grayscale(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        if len(image.shape) == 2:
            return image

        return cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

    def denoise(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        return cv2.fastNlMeansDenoising(
            image,
            None,
            h=10,
            templateWindowSize=7,
            searchWindowSize=21,
        )

    def clahe(
        self,
        image: np.ndarray,
        clip_limit: float = 2.0,
        grid_size: tuple[int, int] = (8, 8),
    ) -> np.ndarray:

        clahe = cv2.createCLAHE(
            clipLimit=clip_limit,
            tileGridSize=grid_size,
        )

        return clahe.apply(image)

    def adaptive_threshold(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        return cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            15,
        )

    def otsu_threshold(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        _, threshold = cv2.threshold(
            image,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )

        return threshold

    def morphology(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        kernel = np.ones((2, 2), np.uint8)

        return cv2.morphologyEx(
            image,
            cv2.MORPH_CLOSE,
            kernel,
        )

    def sharpen(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        kernel = np.array(
            [
                [0, -1, 0],
                [-1, 5, -1],
                [0, -1, 0],
            ],
            dtype=np.float32,
        )

        return cv2.filter2D(
            image,
            -1,
            kernel,
        )

    def resize(
        self,
        image: np.ndarray,
        scale: float = 2.0,
    ) -> np.ndarray:

        return cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )

    def enhance(
        self,
        image: np.ndarray,
    ) -> np.ndarray:
        """
        Default enhancement pipeline.
        """

        image = self.grayscale(image)

        image = self.denoise(image)

        image = self.clahe(image)

        image = self.adaptive_threshold(image)

        image = self.morphology(image)

        image = self.sharpen(image)

        return image