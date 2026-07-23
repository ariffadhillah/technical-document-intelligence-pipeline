from pathlib import Path
from typing import Optional
import os

import pytesseract
from PIL import Image
from pytesseract import TesseractNotFoundError


DEFAULT_TESSERACT_PATH = Path(
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def configure_tesseract() -> Path | None:
    """
    Mengatur lokasi executable Tesseract.

    Prioritas:
    1. Environment variable TESSERACT_CMD
    2. Lokasi default instalasi Windows
    3. Tesseract dari PATH sistem
    """

    environment_path = os.getenv("TESSERACT_CMD")

    if environment_path:
        executable_path = Path(environment_path)

        if not executable_path.exists():
            raise FileNotFoundError(
                "TESSERACT_CMD mengarah ke file yang "
                f"tidak ditemukan: {executable_path}"
            )

        pytesseract.pytesseract.tesseract_cmd = str(
            executable_path
        )

        return executable_path

    if DEFAULT_TESSERACT_PATH.exists():
        pytesseract.pytesseract.tesseract_cmd = str(
            DEFAULT_TESSERACT_PATH
        )

        return DEFAULT_TESSERACT_PATH

    return None


def get_available_languages() -> list[str]:
    """
    Mendapatkan daftar bahasa yang tersedia pada Tesseract.
    """

    try:
        return sorted(
            pytesseract.get_languages(config="")
        )

    except TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract OCR tidak ditemukan."
        ) from exc


def select_ocr_language(
    available_languages: list[str],
) -> str:
    """
    Memilih bahasa OCR terbaik yang tersedia.
    """

    has_german = "deu" in available_languages
    has_english = "eng" in available_languages

    if has_german and has_english:
        return "deu+eng"

    if has_german:
        return "deu"

    if has_english:
        return "eng"

    raise RuntimeError(
        "Language pack 'deu' atau 'eng' tidak tersedia."
    )


def extract_text(
    image: Image.Image,
    language: str,
) -> str:
    """
    Mengekstrak teks dari gambar.
    """

    try:
        return pytesseract.image_to_string(
            image,
            lang=language,
            config="--oem 3 --psm 6",
        )

    except TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract OCR tidak ditemukan."
        ) from exc


def calculate_confidence(
    image: Image.Image,
    language: str,
) -> Optional[float]:
    """
    Menghitung rata-rata confidence kata hasil OCR.
    """

    data = pytesseract.image_to_data(
        image,
        lang=language,
        config="--oem 3 --psm 6",
        output_type=pytesseract.Output.DICT,
    )

    confidence_values = []

    for raw_confidence in data.get("conf", []):
        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError):
            continue

        if confidence >= 0:
            confidence_values.append(confidence)

    if not confidence_values:
        return None

    return round(
        sum(confidence_values) / len(confidence_values),
        2,
    )