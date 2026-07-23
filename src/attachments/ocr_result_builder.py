from pathlib import Path
from typing import Optional
import json
import re


def clean_ocr_text(text: str) -> str:
    """
    Membersihkan format dasar hasil OCR.

    Fungsi ini tidak menerjemahkan atau meringkas teks.
    """

    if not isinstance(text, str):
        return ""

    cleaned_text = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\x0c", "")
    )

    cleaned_text = "\n".join(
        line.rstrip()
        for line in cleaned_text.splitlines()
    )

    cleaned_text = re.sub(
        r"[ \t]{2,}",
        " ",
        cleaned_text,
    )

    cleaned_text = re.sub(
        r"\n{3,}",
        "\n\n",
        cleaned_text,
    )

    return cleaned_text.strip()


def build_ocr_result(
    image_path: Path,
    original_dimensions: tuple[int, int],
    processed_dimensions: tuple[int, int],
    language: str,
    raw_text: str,
    confidence: Optional[float],
) -> dict:
    """
    Membuat hasil OCR dalam struktur JSON.
    """

    cleaned_text = clean_ocr_text(raw_text)

    original_width, original_height = original_dimensions
    processed_width, processed_height = processed_dimensions

    return {
        "filename": image_path.name,
        "file_type": "image",
        "source_path": str(image_path),
        "original_dimensions": {
            "width": original_width,
            "height": original_height,
        },
        "processed_dimensions": {
            "width": processed_width,
            "height": processed_height,
        },
        "ocr_engine": "tesseract",
        "ocr_language": language,
        "ocr_confidence": confidence,
        "character_count": len(cleaned_text),
        "word_count": len(cleaned_text.split()),
        "has_extracted_text": bool(cleaned_text),
        "processing_status": (
            "ocr_completed"
            if cleaned_text
            else "ocr_empty"
        ),
        "extracted_text": cleaned_text,
    }


def save_json(
    data: dict,
    output_path: Path,
) -> None:
    """
    Menyimpan hasil OCR sebagai JSON.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )