from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .exceptions import VisionCacheError
from .models import VisionResponse

logger = logging.getLogger(__name__)


class VisionCache:
    """
    File-based cache for Vision provider results.
    """

    def __init__(
        self,
        cache_dir: str | Path = "output/cache/vision",
        *,
        enabled: bool = True,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.enabled = enabled

        if self.enabled:
            self.cache_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

    def build_key(
        self,
        image: np.ndarray,
        *,
        provider: str,
        model: str,
        prompt: str,
        prompt_version: str,
        config: dict[str, Any] | None = None,
    ) -> str:
        success, encoded = cv2.imencode(
            ".png",
            image,
        )

        if not success:
            raise VisionCacheError(
                "Unable to encode image for Vision cache."
            )

        metadata = {
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "prompt_version": prompt_version,
            "config": config or {},
        }

        hasher = hashlib.sha256()

        hasher.update(encoded.tobytes())

        hasher.update(
            json.dumps(
                metadata,
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            ).encode("utf-8")
        )

        return hasher.hexdigest()

    def get(
        self,
        cache_key: str,
    ) -> VisionResponse | None:
        if not self.enabled:
            return None

        path = self._path(cache_key)

        if not path.exists():
            return None

        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )

            return self._response_from_dict(data)

        except (
            OSError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            logger.warning(
                "Unable to load Vision cache %s: %s",
                path,
                exc,
            )

            return None

    def set(
        self,
        cache_key: str,
        response: VisionResponse,
    ) -> None:
        if not self.enabled:
            return

        path = self._path(cache_key)

        temporary_path = path.with_suffix(".tmp")

        try:
            temporary_path.write_text(
                json.dumps(
                    self._response_to_dict(response),
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

            temporary_path.replace(path)

        except OSError as exc:
            raise VisionCacheError(
                f"Unable to write Vision cache: {path}"
            ) from exc

    def clear(self) -> int:
        if not self.cache_dir.exists():
            return 0

        removed = 0

        for path in self.cache_dir.glob("*.json"):
            path.unlink()
            removed += 1

        return removed

    def _path(
        self,
        cache_key: str,
    ) -> Path:
        return self.cache_dir / f"{cache_key}.json"

    @staticmethod
    def _response_to_dict(
        response: VisionResponse,
    ) -> dict[str, Any]:
        return {
            "page_number": response.page_number,
            "text": response.text,
            "provider": response.provider,
            "model": response.model,
            "confidence": response.confidence,
            "processing_time": response.processing_time,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "estimated_cost": response.estimated_cost,
            "metadata": response.metadata,
        }

    @staticmethod
    def _response_from_dict(
        data: dict[str, Any],
    ) -> VisionResponse:
        return VisionResponse(
            page_number=int(data["page_number"]),
            text=str(data.get("text", "")),
            provider=str(data.get("provider", "")),
            model=str(data.get("model", "")),
            confidence=(
                float(data["confidence"])
                if data.get("confidence") is not None
                else None
            ),
            processing_time=float(
                data.get("processing_time", 0.0)
            ),
            input_tokens=data.get("input_tokens"),
            output_tokens=data.get("output_tokens"),
            estimated_cost=(
                float(data["estimated_cost"])
                if data.get("estimated_cost")
                is not None
                else None
            ),
            metadata=data.get("metadata", {}),
        )