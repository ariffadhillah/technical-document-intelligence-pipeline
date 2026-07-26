from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Mapping

import numpy as np

from ..ocr.models import OCRPage
from .base import BaseVisionEngine
from .cache import VisionCache
from .exceptions import VisionProcessingError
from .models import (
    VisionAuditEntry,
    VisionDecision,
    VisionRequest,
    VisionResponse,
)
from .prompt import VisionPrompt
from .result import (
    VisionBatchResult,
    VisionProcessingResult,
)
from .router import VisionRouter

logger = logging.getLogger(__name__)


class VisionFallbackProcessor:
    """
    Apply Vision only to OCR pages selected by VisionRouter.

    Responsibilities
    ----------------
    1. Score and route OCR pages.
    2. Preserve pages that do not require Vision.
    3. Check Vision cache.
    4. Call the configured Vision provider.
    5. Convert Vision responses into OCRPage objects.
    6. Produce page-level audit entries.
    """

    def __init__(
        self,
        engine: BaseVisionEngine,
        *,
        router: VisionRouter | None = None,
        cache: VisionCache | None = None,
        prompt: VisionPrompt | None = None,
        fail_open: bool = True,
    ) -> None:
        self.engine = engine
        self.router = router or VisionRouter()
        self.cache = cache or VisionCache()
        self.prompt = prompt or VisionPrompt()
        self.fail_open = fail_open

    def process_page(
        self,
        *,
        image: np.ndarray,
        ocr_page: OCRPage,
        image_type: str | None = None,
        force_vision: bool = False,
    ) -> VisionProcessingResult:
        """
        Process one OCR page through the Vision fallback pipeline.
        """

        started_at = time.perf_counter()

        decision = self.router.route(
            ocr_page,
            image_type=image_type,
            force_vision=force_vision,
            provider=self.engine.get_provider_name(),
            model=self.engine.get_model_name(),
        )

        if not decision.use_vision:
            audit = self._build_audit(
                decision=decision,
                original_page=ocr_page,
                final_page=ocr_page,
                vision_used=False,
                cache_hit=False,
                processing_time=(
                    time.perf_counter() - started_at
                ),
            )

            return VisionProcessingResult(
                success=True,
                decision=decision,
                original_ocr_page=ocr_page,
                final_page=ocr_page,
                from_cache=False,
                audit=audit,
                metadata={
                    "vision_skipped": True,
                },
            )

        prompt_text = self.prompt.build(
            ocr_text=ocr_page.text,
            page_number=ocr_page.page_number,
        )

        request = VisionRequest(
            image=image,
            page_number=ocr_page.page_number,
            prompt=prompt_text,
            provider=self.engine.get_provider_name(),
            model=self.engine.get_model_name(),
            prompt_version=self.prompt.version,
            source_path=ocr_page.source_path,
            ocr_page=ocr_page,
            metadata={
                "image_type": image_type,
                "routing_reasons": [
                    reason.value
                    for reason in decision.reasons
                ],
            },
        )

        cache_key = self.cache.build_key(
            image,
            provider=request.provider,
            model=request.model,
            prompt=request.prompt,
            prompt_version=request.prompt_version,
            config={
                "image_type": image_type,
            },
        )

        cached_response = self.cache.get(cache_key)

        if cached_response is not None:
            final_page = self._response_to_page(
                response=cached_response,
                original_page=ocr_page,
                cache_hit=True,
            )

            elapsed = time.perf_counter() - started_at

            audit = self._build_audit(
                decision=decision,
                original_page=ocr_page,
                final_page=final_page,
                vision_used=True,
                cache_hit=True,
                processing_time=elapsed,
                response=cached_response,
            )

            return VisionProcessingResult(
                success=True,
                decision=decision,
                response=cached_response,
                original_ocr_page=ocr_page,
                final_page=final_page,
                from_cache=True,
                audit=audit,
                metadata={
                    "cache_key": cache_key,
                },
            )

        try:
            response = self.engine.analyze_page(request)

            self._validate_response(
                response=response,
                decision=decision,
            )

            self.cache.set(
                cache_key,
                response,
            )

            final_page = self._response_to_page(
                response=response,
                original_page=ocr_page,
                cache_hit=False,
            )

            elapsed = time.perf_counter() - started_at

            audit = self._build_audit(
                decision=decision,
                original_page=ocr_page,
                final_page=final_page,
                vision_used=True,
                cache_hit=False,
                processing_time=elapsed,
                response=response,
            )

            return VisionProcessingResult(
                success=True,
                decision=decision,
                response=response,
                original_ocr_page=ocr_page,
                final_page=final_page,
                from_cache=False,
                audit=audit,
                metadata={
                    "cache_key": cache_key,
                },
            )

        except Exception as exc:
            elapsed = time.perf_counter() - started_at

            logger.exception(
                "Vision processing failed for page %s.",
                ocr_page.page_number,
            )

            audit = self._build_audit(
                decision=decision,
                original_page=ocr_page,
                final_page=ocr_page,
                vision_used=True,
                cache_hit=False,
                processing_time=elapsed,
                error=str(exc),
            )

            if not self.fail_open:
                raise VisionProcessingError(
                    f"Vision processing failed for page "
                    f"{ocr_page.page_number}: {exc}"
                ) from exc

            return VisionProcessingResult(
                success=False,
                decision=decision,
                original_ocr_page=ocr_page,
                final_page=ocr_page,
                from_cache=False,
                error=str(exc),
                audit=audit,
                metadata={
                    "fallback_to_original_ocr": True,
                },
            )

    def process_pages(
        self,
        *,
        pages: list[OCRPage],
        images: Mapping[int, np.ndarray],
        image_types: Mapping[int, str] | None = None,
        force_pages: set[int] | None = None,
    ) -> VisionBatchResult:
        """
        Process a collection of OCR pages while retaining page order.
        """

        started_at = time.perf_counter()

        image_types = image_types or {}
        force_pages = force_pages or set()

        results: list[VisionProcessingResult] = []
        final_pages: list[OCRPage] = []
        audits: list[VisionAuditEntry] = []

        for page in sorted(
            pages,
            key=lambda item: item.page_number,
        ):
            image = images.get(page.page_number)

            if image is None:
                raise VisionProcessingError(
                    f"Image for page {page.page_number} "
                    f"is not available."
                )

            result = self.process_page(
                image=image,
                ocr_page=page,
                image_type=image_types.get(
                    page.page_number
                ),
                force_vision=(
                    page.page_number in force_pages
                ),
            )

            results.append(result)

            final_pages.append(
                result.final_page or page
            )

            if result.audit is not None:
                audits.append(result.audit)

        vision_pages = sum(
            1
            for result in results
            if result.decision.use_vision
        )

        cache_hits = sum(
            1
            for result in results
            if result.from_cache
        )

        failures = sum(
            1
            for result in results
            if not result.success
        )

        estimated_cost = sum(
            (
                result.response.estimated_cost
                if result.response is not None
                and result.response.estimated_cost is not None
                else 0.0
            )
            for result in results
        )

        return VisionBatchResult(
            pages=final_pages,
            results=results,
            audits=audits,
            total_pages=len(pages),
            vision_pages=vision_pages,
            cache_hits=cache_hits,
            failures=failures,
            processing_time=(
                time.perf_counter() - started_at
            ),
            estimated_cost=estimated_cost,
            metadata={
                "provider": self.engine.get_provider_name(),
                "model": self.engine.get_model_name(),
                "prompt_version": self.prompt.version,
            },
        )

    @staticmethod
    def _validate_response(
        *,
        response: VisionResponse,
        decision: VisionDecision,
    ) -> None:
        if response.page_number != decision.page_number:
            raise VisionProcessingError(
                "Vision response page number does not "
                "match the routed page."
            )

        if not response.text.strip():
            raise VisionProcessingError(
                f"Vision returned empty text for page "
                f"{response.page_number}."
            )

    @staticmethod
    def _response_to_page(
        *,
        response: VisionResponse,
        original_page: OCRPage,
        cache_hit: bool,
    ) -> OCRPage:
        confidence = (
            response.confidence
            if response.confidence is not None
            else original_page.confidence
        )

        quality_score = (
            response.confidence
            if response.confidence is not None
            else original_page.quality_score
        )

        metadata = dict(original_page.metadata)

        metadata.update(
            {
                "vision_used": True,
                "vision_provider": response.provider,
                "vision_model": response.model,
                "vision_cache_hit": cache_hit,
                "original_ocr_text": original_page.text,
                "original_ocr_confidence": (
                    original_page.confidence
                ),
                "original_ocr_quality": (
                    original_page.quality_score
                ),
                "vision_metadata": response.metadata,
            }
        )

        return OCRPage(
            page_number=original_page.page_number,
            paragraphs=[],
            text=response.text.strip(),
            confidence=confidence,
            quality_score=quality_score,
            language=original_page.language,
            width=original_page.width,
            height=original_page.height,
            source_path=original_page.source_path,
            engine_name=(
                f"vision:{response.provider}"
            ),
            processing_time=(
                original_page.processing_time
                + response.processing_time
            ),
            metadata=metadata,
        )

    @staticmethod
    def _build_audit(
        *,
        decision: VisionDecision,
        original_page: OCRPage,
        final_page: OCRPage,
        vision_used: bool,
        cache_hit: bool,
        processing_time: float,
        response: VisionResponse | None = None,
        error: str | None = None,
    ) -> VisionAuditEntry:
        score = decision.score

        return VisionAuditEntry(
            page_number=original_page.page_number,
            ocr_quality=(
                score.quality_score
                if score is not None
                else original_page.quality_score
            ),
            ocr_confidence=original_page.confidence,
            vision_used=vision_used,
            vision_provider=(
                response.provider
                if response is not None
                else decision.provider
                if vision_used
                else None
            ),
            vision_model=(
                response.model
                if response is not None
                else decision.model
                if vision_used
                else None
            ),
            cache_hit=cache_hit,
            retry_count=0,
            processing_time=processing_time,
            estimated_cost=(
                response.estimated_cost
                if response is not None
                else None
            ),
            final_quality=final_page.quality_score,
            reasons=[
                reason.value
                for reason in decision.reasons
            ],
            metadata={
                "success": error is None,
                "error": error,
                "original_engine": (
                    original_page.engine_name
                ),
                "final_engine": final_page.engine_name,
            },
        )