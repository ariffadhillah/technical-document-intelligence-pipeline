from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .exceptions import OCRCacheError
from .models import OCRPage

logger = logging.getLogger(__name__)


class OCRCache:
    """
    File-based JSON cache for OCR page results.
    """

    def __init__(
        self,
        cache_dir: str | Path = "output/cache/ocr",
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
        engine_name: str,
        language: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> str:

        success, encoded = cv2.imencode(
            ".png",
            image,
        )

        if not success:
            raise OCRCacheError(
                "Unable to encode image for cache key."
            )

        payload = {
            "engine_name": engine_name,
            "language": language,
            "config": config or {},
        }

        hasher = hashlib.sha256()

        hasher.update(encoded.tobytes())

        hasher.update(
            json.dumps(
                payload,
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            ).encode("utf-8")
        )

        return hasher.hexdigest()

    def get(
        self,
        cache_key: str,
    ) -> OCRPage | None:

        if not self.enabled:
            return None

        path = self._cache_path(cache_key)

        if not path.exists():
            return None

        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            return OCRPage.from_dict(data)

        except (
            OSError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as exc:
            logger.warning(
                "Unable to read OCR cache %s: %s",
                path,
                exc,
            )

            return None

    def set(
        self,
        cache_key: str,
        page: OCRPage,
    ) -> None:

        if not self.enabled:
            return

        path = self._cache_path(cache_key)

        temporary_path = path.with_suffix(
            ".tmp"
        )

        try:
            temporary_path.write_text(
                json.dumps(
                    page.to_dict(),
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

            temporary_path.replace(path)

        except OSError as exc:
            raise OCRCacheError(
                f"Unable to write OCR cache: {path}"
            ) from exc

    def delete(
        self,
        cache_key: str,
    ) -> None:

        path = self._cache_path(cache_key)

        if path.exists():
            path.unlink()

    def clear(self) -> int:
        """
        Remove all cached OCR JSON files.

        Returns the number of removed files.
        """

        removed = 0

        if not self.cache_dir.exists():
            return removed

        for path in self.cache_dir.glob("*.json"):
            path.unlink()

            removed += 1

        return removed

    def _cache_path(
        self,
        cache_key: str,
    ) -> Path:

        return self.cache_dir / f"{cache_key}.json"