from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class VisualLayoutAnalysis:
    """
    Visual analysis result for one image or rendered page.
    """

    page_number: int
    page_type: str
    visual_complexity: str
    visual_complexity_score: float

    text_region_count: int
    text_area_ratio: float
    edge_density: float
    color_variance: float

    likely_document: bool
    likely_photo: bool
    likely_screenshot: bool
    likely_table: bool
    likely_mixed_content: bool

    vision_recommended: bool
    vision_reasons: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "page_type": self.page_type,
            "visual_complexity": (
                self.visual_complexity
            ),
            "visual_complexity_score": (
                self.visual_complexity_score
            ),
            "text_region_count": (
                self.text_region_count
            ),
            "text_area_ratio": (
                self.text_area_ratio
            ),
            "edge_density": self.edge_density,
            "color_variance": (
                self.color_variance
            ),
            "likely_document": (
                self.likely_document
            ),
            "likely_photo": self.likely_photo,
            "likely_screenshot": (
                self.likely_screenshot
            ),
            "likely_table": self.likely_table,
            "likely_mixed_content": (
                self.likely_mixed_content
            ),
            "vision_recommended": (
                self.vision_recommended
            ),
            "vision_reasons": list(
                self.vision_reasons
            ),
            "metadata": dict(self.metadata),
        }


class VisualLayoutAnalyzer:
    """
    Analyze the visual structure of a page before OCR
    and Vision routing.

    This implementation is deterministic and does not
    call an external AI provider.
    """

    def __init__(
        self,
        *,
        minimum_text_region_area: int = 80,
        document_text_ratio: float = 0.025,
        photo_color_variance: float = 900.0,
        complex_score_threshold: float = 0.55,
    ) -> None:
        self.minimum_text_region_area = (
            minimum_text_region_area
        )
        self.document_text_ratio = (
            document_text_ratio
        )
        self.photo_color_variance = (
            photo_color_variance
        )
        self.complex_score_threshold = (
            complex_score_threshold
        )

    def analyze(
        self,
        *,
        image: np.ndarray,
        page_number: int,
    ) -> VisualLayoutAnalysis:
        self._validate_image(image)

        height, width = image.shape[:2]

        grayscale = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        text_regions = self._detect_text_regions(
            grayscale
        )

        text_region_count = len(text_regions)

        text_area = sum(
            region_width * region_height
            for (
                _,
                _,
                region_width,
                region_height,
            ) in text_regions
        )

        image_area = max(
            width * height,
            1,
        )

        text_area_ratio = (
            text_area / image_area
        )

        edge_density = self._edge_density(
            grayscale
        )

        color_variance = (
            self._color_variance(image)
        )

        likely_table = self._likely_table(
            grayscale=grayscale,
            text_region_count=(
                text_region_count
            ),
        )

        likely_screenshot = (
            self._likely_screenshot(
                image=image,
                text_area_ratio=(
                    text_area_ratio
                ),
                edge_density=edge_density,
            )
        )

        likely_document = (
            self._likely_document(
                image=image,
                text_area_ratio=(
                    text_area_ratio
                ),
                text_region_count=(
                    text_region_count
                ),
                color_variance=(
                    color_variance
                ),
            )
        )

        likely_photo = self._likely_photo(
            color_variance=color_variance,
            text_area_ratio=text_area_ratio,
            likely_document=(
                likely_document
            ),
        )

        likely_mixed_content = (
            self._likely_mixed_content(
                likely_photo=likely_photo,
                likely_document=(
                    likely_document
                ),
                text_area_ratio=(
                    text_area_ratio
                ),
                color_variance=(
                    color_variance
                ),
            )
        )

        page_type = self._classify_page_type(
            likely_document=(
                likely_document
            ),
            likely_photo=likely_photo,
            likely_screenshot=(
                likely_screenshot
            ),
            likely_mixed_content=(
                likely_mixed_content
            ),
            text_area_ratio=text_area_ratio,
        )

        complexity_score = (
            self._complexity_score(
                text_region_count=(
                    text_region_count
                ),
                text_area_ratio=(
                    text_area_ratio
                ),
                edge_density=edge_density,
                likely_table=likely_table,
                likely_screenshot=(
                    likely_screenshot
                ),
                likely_mixed_content=(
                    likely_mixed_content
                ),
            )
        )

        visual_complexity = (
            self._complexity_label(
                complexity_score
            )
        )

        vision_reasons = (
            self._build_vision_reasons(
                page_type=page_type,
                likely_table=likely_table,
                likely_screenshot=(
                    likely_screenshot
                ),
                likely_mixed_content=(
                    likely_mixed_content
                ),
                complexity_score=(
                    complexity_score
                ),
            )
        )

        result = VisualLayoutAnalysis(
            page_number=page_number,
            page_type=page_type,
            visual_complexity=(
                visual_complexity
            ),
            visual_complexity_score=round(
                complexity_score,
                4,
            ),
            text_region_count=(
                text_region_count
            ),
            text_area_ratio=round(
                text_area_ratio,
                6,
            ),
            edge_density=round(
                edge_density,
                6,
            ),
            color_variance=round(
                color_variance,
                2,
            ),
            likely_document=(
                likely_document
            ),
            likely_photo=likely_photo,
            likely_screenshot=(
                likely_screenshot
            ),
            likely_table=likely_table,
            likely_mixed_content=(
                likely_mixed_content
            ),
            vision_recommended=bool(
                vision_reasons
            ),
            vision_reasons=vision_reasons,
            metadata={
                "width": width,
                "height": height,
                "analyzer": (
                    self.__class__.__name__
                ),
                "strategy": (
                    "opencv_visual_heuristics"
                ),
            },
        )

        logger.info(
            "Visual layout analysis completed: "
            "page=%s type=%s complexity=%s "
            "text_regions=%s vision=%s",
            page_number,
            page_type,
            visual_complexity,
            text_region_count,
            result.vision_recommended,
        )

        return result

    def _detect_text_regions(
        self,
        grayscale: np.ndarray,
    ) -> list[tuple[int, int, int, int]]:
        blurred = cv2.GaussianBlur(
            grayscale,
            (3, 3),
            0,
        )

        gradient = cv2.morphologyEx(
            blurred,
            cv2.MORPH_GRADIENT,
            cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (3, 3),
            ),
        )

        _, binary = cv2.threshold(
            gradient,
            0,
            255,
            cv2.THRESH_BINARY
            | cv2.THRESH_OTSU,
        )

        connected = cv2.morphologyEx(
            binary,
            cv2.MORPH_CLOSE,
            cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (15, 3),
            ),
        )

        contours, _ = cv2.findContours(
            connected,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        regions: list[
            tuple[int, int, int, int]
        ] = []

        for contour in contours:
            x, y, width, height = (
                cv2.boundingRect(contour)
            )

            area = width * height

            if (
                area
                < self.minimum_text_region_area
            ):
                continue

            if width < 8 or height < 4:
                continue

            regions.append(
                (x, y, width, height)
            )

        return regions

    @staticmethod
    def _edge_density(
        grayscale: np.ndarray,
    ) -> float:
        edges = cv2.Canny(
            grayscale,
            80,
            180,
        )

        return float(
            np.count_nonzero(edges)
        ) / float(edges.size)

    @staticmethod
    def _color_variance(
        image: np.ndarray,
    ) -> float:
        channels = cv2.split(image)

        variances = [
            float(np.var(channel))
            for channel in channels
        ]

        return sum(variances) / len(
            variances
        )

    @staticmethod
    def _background_whiteness(
        image: np.ndarray,
    ) -> float:
        grayscale = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        bright_pixels = np.count_nonzero(
            grayscale >= 235
        )

        return bright_pixels / grayscale.size

    def _likely_document(
        self,
        *,
        image: np.ndarray,
        text_area_ratio: float,
        text_region_count: int,
        color_variance: float,
    ) -> bool:
        whiteness = (
            self._background_whiteness(image)
        )

        return (
            whiteness >= 0.45
            and text_region_count >= 5
            and text_area_ratio
            >= self.document_text_ratio
            and color_variance
            < self.photo_color_variance
        )

    @staticmethod
    def _likely_photo(
        *,
        color_variance: float,
        text_area_ratio: float,
        likely_document: bool,
    ) -> bool:
        return (
            not likely_document
            and color_variance >= 700.0
            and text_area_ratio < 0.08
        )

    @staticmethod
    def _likely_mixed_content(
        *,
        likely_photo: bool,
        likely_document: bool,
        text_area_ratio: float,
        color_variance: float,
    ) -> bool:
        return (
            (
                likely_photo
                or likely_document
            )
            and text_area_ratio >= 0.015
            and color_variance >= 450.0
        )

    def _likely_screenshot(
        self,
        *,
        image: np.ndarray,
        text_area_ratio: float,
        edge_density: float,
    ) -> bool:
        whiteness = (
            self._background_whiteness(image)
        )

        return (
            whiteness >= 0.55
            and text_area_ratio >= 0.015
            and edge_density < 0.12
        )

    @staticmethod
    def _likely_table(
        *,
        grayscale: np.ndarray,
        text_region_count: int,
    ) -> bool:
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

        horizontal_kernel = (
            cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (40, 1),
            )
        )

        vertical_kernel = (
            cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (1, 30),
            )
        )

        horizontal = cv2.morphologyEx(
            binary,
            cv2.MORPH_OPEN,
            horizontal_kernel,
        )

        vertical = cv2.morphologyEx(
            binary,
            cv2.MORPH_OPEN,
            vertical_kernel,
        )

        line_pixels = (
            np.count_nonzero(horizontal)
            + np.count_nonzero(vertical)
        )

        line_ratio = (
            line_pixels / binary.size
        )

        return (
            line_ratio >= 0.004
            and text_region_count >= 5
        )

    @staticmethod
    def _classify_page_type(
        *,
        likely_document: bool,
        likely_photo: bool,
        likely_screenshot: bool,
        likely_mixed_content: bool,
        text_area_ratio: float,
    ) -> str:
        if likely_screenshot:
            return "screenshot"

        if likely_mixed_content:
            return "mixed_content"

        if likely_document:
            return "document_page"

        if (
            likely_photo
            and text_area_ratio >= 0.005
        ):
            return "photo_with_labels"

        if likely_photo:
            return "photo"

        return "unknown"

    @staticmethod
    def _complexity_score(
        *,
        text_region_count: int,
        text_area_ratio: float,
        edge_density: float,
        likely_table: bool,
        likely_screenshot: bool,
        likely_mixed_content: bool,
    ) -> float:
        score = 0.0

        score += min(
            text_region_count / 80.0,
            0.25,
        )

        score += min(
            text_area_ratio * 2.0,
            0.20,
        )

        score += min(
            edge_density * 1.5,
            0.20,
        )

        if likely_table:
            score += 0.20

        if likely_screenshot:
            score += 0.15

        if likely_mixed_content:
            score += 0.25

        return min(score, 1.0)

    @staticmethod
    def _complexity_label(
        score: float,
    ) -> str:
        if score >= 0.70:
            return "high"

        if score >= 0.40:
            return "medium"

        return "low"

    def _build_vision_reasons(
        self,
        *,
        page_type: str,
        likely_table: bool,
        likely_screenshot: bool,
        likely_mixed_content: bool,
        complexity_score: float,
    ) -> list[str]:
        reasons: list[str] = []

        if page_type == "photo":
            reasons.append(
                "visual_photo_content"
            )

        if page_type == "photo_with_labels":
            reasons.append(
                "photo_with_embedded_labels"
            )

        if likely_table:
            reasons.append(
                "visual_table_structure"
            )

        if likely_screenshot:
            reasons.append(
                "screenshot_layout"
            )

        if likely_mixed_content:
            reasons.append(
                "mixed_visual_and_text_content"
            )

        if (
            complexity_score
            >= self.complex_score_threshold
        ):
            reasons.append(
                "high_visual_complexity"
            )

        return reasons

    @staticmethod
    def _validate_image(
        image: np.ndarray,
    ) -> None:
        if image is None:
            raise ValueError(
                "Visual layout image is missing."
            )

        if image.size == 0:
            raise ValueError(
                "Visual layout image is empty."
            )