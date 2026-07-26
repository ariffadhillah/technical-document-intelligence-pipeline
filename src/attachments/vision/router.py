from __future__ import annotations

from dataclasses import dataclass, field

from ..ocr.models import OCRPage
from .models import (
    VisionDecision,
    VisionPriority,
    VisionReason,
)
from .scorer import VisionPageScorer


@dataclass(slots=True)
class VisionRouterConfig:
    """
    Vision routing configuration.
    """

    enabled: bool = True

    default_provider: str = "openai"

    default_model: str = "vision-default"

    force_image_types: set[str] = field(
        default_factory=lambda: {
            "wiring",
            "drawing",
            "table",
            "photo",
        }
    )

    high_priority_threshold: float = 0.35

    critical_priority_threshold: float = 0.15

    vision_threshold: float = 0.60


class VisionRouter:
    """
    Decide whether a page should use Vision.
    """

    def __init__(
        self,
        config: VisionRouterConfig | None = None,
        scorer: VisionPageScorer | None = None,
    ) -> None:
        self.config = config or VisionRouterConfig()

        self.scorer = scorer or VisionPageScorer(
            vision_threshold=(
                self.config.vision_threshold
            )
        )

    def route(
        self,
        page: OCRPage,
        *,
        image_type: str | None = None,
        force_vision: bool = False,
        provider: str | None = None,
        model: str | None = None,
    ) -> VisionDecision:
        score = self.scorer.evaluate(page)

        reasons = list(score.reasons)

        use_vision = score.needs_vision

        normalized_image_type = (
            image_type.strip().lower()
            if image_type
            else None
        )

        if (
            normalized_image_type
            in self.config.force_image_types
        ):
            use_vision = True

            reason = self._image_type_reason(
                normalized_image_type
            )

            if reason not in reasons:
                reasons.append(reason)

        if force_vision:
            use_vision = True

            if VisionReason.MANUAL_OVERRIDE not in reasons:
                reasons.append(
                    VisionReason.MANUAL_OVERRIDE
                )

        if not self.config.enabled and not force_vision:
            use_vision = False

        priority = self._determine_priority(
            score.quality_score,
            use_vision=use_vision,
        )



        selected_provider = (
            provider or self.config.default_provider
            if use_vision
            else None
        )

        selected_model = (
            model or self.config.default_model
            if use_vision
            else None
        )

        return VisionDecision(
            page_number=page.page_number,
            use_vision=use_vision,
            provider=selected_provider,
            model=selected_model,
            priority=priority,
            reasons=reasons,
            score=score,
            metadata={
                "image_type": normalized_image_type,
                "router_enabled": self.config.enabled,
                "force_vision": force_vision,
            },
        )


    def route_pages(
        self,
        pages: list[OCRPage],
        *,
        image_types: dict[int, str] | None = None,
    ) -> list[VisionDecision]:
        image_types = image_types or {}

        return [
            self.route(
                page,
                image_type=image_types.get(
                    page.page_number
                ),
            )
            for page in pages
        ]

    def failed_pages_only(
        self,
        pages: list[OCRPage],
        *,
        image_types: dict[int, str] | None = None,
    ) -> list[OCRPage]:
        decisions = self.route_pages(
            pages,
            image_types=image_types,
        )

        failed_page_numbers = {
            decision.page_number
            for decision in decisions
            if decision.use_vision
        }

        return [
            page
            for page in pages
            if page.page_number in failed_page_numbers
        ]

    def _determine_priority(
        self,
        quality_score: float,
        *,
        use_vision: bool,
    ) -> VisionPriority:
        if not use_vision:
            return VisionPriority.LOW

        if (
            quality_score
            <= self.config.critical_priority_threshold
        ):
            return VisionPriority.CRITICAL

        if (
            quality_score
            <= self.config.high_priority_threshold
        ):
            return VisionPriority.HIGH

        return VisionPriority.NORMAL

    @staticmethod
    def _image_type_reason(
        image_type: str,
    ) -> VisionReason:
        mapping = {
            "wiring": VisionReason.DIAGRAM_CONTENT,
            "drawing": VisionReason.DRAWING_CONTENT,
            "table": VisionReason.TABLE_CONTENT,
            "photo": VisionReason.PHOTO_CONTENT,
        }

        return mapping.get(
            image_type,
            VisionReason.LOW_OCR_QUALITY,
        )