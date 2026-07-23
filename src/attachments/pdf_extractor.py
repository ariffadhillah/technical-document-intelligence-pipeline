from pathlib import Path
from typing import Any
import json
import re

from pypdf import PdfReader


SUPPORTED_PDF_EXTENSION = ".pdf"


def clean_extracted_text(text: str) -> str:
    """
    Membersihkan teks dasar hasil ekstraksi PDF.

    Fungsi ini tidak menerjemahkan atau meringkas teks.
    """

    if not isinstance(text, str):
        return ""

    cleaned_text = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    cleaned_text = "\n".join(
        line.rstrip()
        for line in cleaned_text.splitlines()
    )

    cleaned_text = re.sub(
        r"\n{3,}",
        "\n\n",
        cleaned_text,
    )

    return cleaned_text.strip()


def classify_pdf(
    extracted_text: str,
    page_count: int,
) -> str:
    """
    Menentukan apakah PDF memiliki text layer
    atau kemungkinan merupakan scanned PDF.
    """

    character_count = len(
        extracted_text.replace("\n", "").strip()
    )

    if page_count == 0:
        return "empty_pdf"

    if character_count == 0:
        return "scanned_pdf"

    average_characters_per_page = (
        character_count / page_count
    )

    if average_characters_per_page < 30:
        return "possible_scanned_pdf"

    return "text_pdf"


def extract_page(
    page: Any,
    page_number: int,
) -> dict:
    """
    Mengekstrak teks dari satu halaman PDF.
    """

    extraction_error = None

    try:
        raw_text = page.extract_text() or ""
        cleaned_text = clean_extracted_text(raw_text)

    except Exception as exc:
        cleaned_text = ""
        extraction_error = str(exc)

    return {
        "page_number": page_number,
        "text": cleaned_text,
        "character_count": len(cleaned_text),
        "extraction_status": (
            "success"
            if cleaned_text
            else "empty"
        ),
        "error": extraction_error,
    }


def extract_pdf(pdf_path: Path) -> dict:
    """
    Membaca sebuah PDF dan menghasilkan data terstruktur.
    """

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF tidak ditemukan: {pdf_path}"
        )

    if pdf_path.suffix.lower() != SUPPORTED_PDF_EXTENSION:
        raise ValueError(
            f"File bukan PDF: {pdf_path.name}"
        )

    reader = PdfReader(str(pdf_path))

    pages = [
        extract_page(
            page=page,
            page_number=index,
        )
        for index, page in enumerate(
            reader.pages,
            start=1,
        )
    ]

    full_text = "\n\n".join(
        page["text"]
        for page in pages
        if page["text"]
    )

    full_text = clean_extracted_text(full_text)

    page_count = len(pages)

    pdf_classification = classify_pdf(
        extracted_text=full_text,
        page_count=page_count,
    )

    successful_pages = sum(
        page["extraction_status"] == "success"
        for page in pages
    )

    empty_pages = sum(
        page["extraction_status"] == "empty"
        for page in pages
    )

    return {
        "filename": pdf_path.name,
        "file_type": "pdf",
        "source_path": str(pdf_path),
        "page_count": page_count,
        "successful_pages": successful_pages,
        "empty_pages": empty_pages,
        "character_count": len(full_text),
        "pdf_classification": pdf_classification,
        "requires_ocr": pdf_classification in {
            "scanned_pdf",
            "possible_scanned_pdf",
        },
        "processing_status": "pdf_text_extracted",
        "pages": pages,
        "full_text": full_text,
    }


def save_json(
    data: dict,
    output_path: Path,
) -> None:
    """
    Menyimpan hasil ekstraksi sebagai JSON.
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


def print_extraction_summary(
    result: dict,
    output_path: Path,
) -> None:
    """
    Menampilkan ringkasan ekstraksi PDF.
    """

    print("=" * 70)
    print("PDF TEXT EXTRACTION")
    print("=" * 70)

    print(
        f"Filename           : "
        f"{result['filename']}"
    )
    print(
        f"Pages              : "
        f"{result['page_count']}"
    )
    print(
        f"Successful pages   : "
        f"{result['successful_pages']}"
    )
    print(
        f"Empty pages        : "
        f"{result['empty_pages']}"
    )
    print(
        f"Characters         : "
        f"{result['character_count']}"
    )
    print(
        f"Classification     : "
        f"{result['pdf_classification']}"
    )
    print(
        f"Requires OCR       : "
        f"{result['requires_ocr']}"
    )
    print(
        f"Output file        : "
        f"{output_path}"
    )
    print("Status             : success")


def find_first_pdf(
    attachments_directory: Path,
) -> Path:
    """
    Mencari PDF pertama dalam folder attachment.

    Ini cukup untuk sample.
    Pada versi production, semua PDF akan diproses.
    """

    pdf_files = sorted(
        file_path
        for file_path in attachments_directory.iterdir()
        if (
            file_path.is_file()
            and file_path.suffix.lower()
            == SUPPORTED_PDF_EXTENSION
        )
    )

    if not pdf_files:
        raise FileNotFoundError(
            "Tidak ada file PDF di folder: "
            f"{attachments_directory}"
        )

    return pdf_files[0]


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]

    attachments_directory = (
        project_root
        / "data"
        / "raw"
        / "attachments"
    )

    pdf_path = find_first_pdf(
        attachments_directory
    )

    output_path = (
        project_root
        / "output"
        / "attachments"
        / "pdf"
        / f"{pdf_path.stem}.json"
    )

    result = extract_pdf(pdf_path)

    save_json(
        data=result,
        output_path=output_path,
    )

    print_extraction_summary(
        result=result,
        output_path=output_path,
    )


if __name__ == "__main__":
    main()