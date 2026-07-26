from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import cv2
import numpy as np

from .exceptions import OCRProcessingError
from .models import OCRPage


class BaseOCREngine(ABC):
    """
    Base interface for every OCR engine.

    Implementations may include:

        - Tesseract
        - PaddleOCR
        - EasyOCR
        - docTR
        - Vision API
    """

    engine_name: str = "base"

    @abstractmethod
    def process_image(
        self,
        image: np.ndarray,
        *,
        page_number: int = 1,
        source_path: str | Path | None = None,
        language: str | None = None,
    ) -> OCRPage:
        """
        Process one image and return a structured OCR page.
        """

    def process_file(
        self,
        image_path: str | Path,
        *,
        page_number: int = 1,
        language: str | None = None,
    ) -> OCRPage:
        """
        Load an image from disk and run OCR.
        """

        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(path)

        image = cv2.imread(str(path))

        if image is None:
            raise OCRProcessingError(
                f"Unable to read image: {path}"
            )

        return self.process_image(
            image,
            page_number=page_number,
            source_path=path,
            language=language,
        )

    def is_available(self) -> bool:
        """
        Return whether the OCR engine is available.
        """

        return True

    def get_version(self) -> str | None:
        """
        Return engine version when available.
        """

        return None