from __future__ import annotations

import logging
from pathlib import Path

import fitz

from .models import RenderedPage

logger = logging.getLogger(__name__)


class PDFRenderer:
    """
    Render PDF pages into high-resolution PNG images.

    Features
    --------
    - Render all pages
    - Configurable DPI
    - Lossless PNG output
    - Create output directory automatically
    """

    DEFAULT_DPI = 400

    def render(
        self,
        pdf_path: Path,
        output_dir: Path,
        dpi: int | None = None,
    ) -> list[RenderedPage]:

        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)

        dpi = dpi or self.DEFAULT_DPI

        output_dir.mkdir(parents=True, exist_ok=True)

        document = fitz.open(pdf_path)

        rendered_pages: list[RenderedPage] = []

        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)

        try:

            for page_index, page in enumerate(document):

                pix = page.get_pixmap(
                    matrix=matrix,
                    alpha=False,
                )

                image_path = (
                    output_dir /
                    f"page_{page_index + 1:03d}.png"
                )

                pix.save(image_path)

                rendered_pages.append(
                    RenderedPage(
                        page_number=page_index + 1,
                        image_path=image_path,
                        dpi=dpi,
                        width=pix.width,
                        height=pix.height,
                    )
                )

                logger.info(
                    "Rendered page %s -> %s",
                    page_index + 1,
                    image_path.name,
                )

            return rendered_pages

        finally:

            document.close()