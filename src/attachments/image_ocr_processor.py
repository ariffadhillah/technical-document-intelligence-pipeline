from pathlib import Path

from src.attachments.image_loader import (
    find_images,
    load_image,
)
from src.attachments.image_preprocessor import (
    preprocess_image,
)
from src.attachments.ocr_engine import (
    calculate_confidence,
    configure_tesseract,
    extract_text,
    get_available_languages,
    select_ocr_language,
)
from src.attachments.ocr_result_builder import (
    build_ocr_result,
    save_json,
)

def process_image(
    image_path: Path,
    output_directory: Path,
    language: str,
) -> dict:
    """
    Menjalankan seluruh alur OCR untuk satu gambar.
    """

    source_image = load_image(image_path)

    try:
        original_dimensions = source_image.size

        processed_image = preprocess_image(
            source_image
        )

        try:
            processed_dimensions = (
                processed_image.size
            )

            raw_text = extract_text(
                image=processed_image,
                language=language,
            )

            confidence = calculate_confidence(
                image=processed_image,
                language=language,
            )

        finally:
            processed_image.close()

    finally:
        source_image.close()

    result = build_ocr_result(
        image_path=image_path,
        original_dimensions=original_dimensions,
        processed_dimensions=processed_dimensions,
        language=language,
        raw_text=raw_text,
        confidence=confidence,
    )

    output_path = (
        output_directory
        / f"{image_path.stem}_ocr.json"
    )

    save_json(
        data=result,
        output_path=output_path,
    )

    return result


def process_all_images(
    attachments_directory: Path,
    output_directory: Path,
) -> list[dict]:
    """
    Menjalankan OCR untuk seluruh gambar yang tersedia.
    """

    configure_tesseract()

    available_languages = get_available_languages()

    language = select_ocr_language(
        available_languages
    )

    image_files = find_images(
        attachments_directory
    )

    if not image_files:
        raise FileNotFoundError(
            "Tidak ada gambar dalam folder attachment: "
            f"{attachments_directory}"
        )

    print(
        "Available languages : "
        f"{', '.join(available_languages)}"
    )
    print(f"Selected language   : {language}")
    print()

    results = []

    for image_path in image_files:
        print(f"Processing: {image_path.name}")

        try:
            result = process_image(
                image_path=image_path,
                output_directory=output_directory,
                language=language,
            )

        except Exception as exc:
            result = {
                "filename": image_path.name,
                "processing_status": "failed",
                "error": str(exc),
            }

        results.append(result)

    return results


def print_summary(
    results: list[dict],
    output_directory: Path,
) -> None:
    completed_results = [
        result
        for result in results
        if result.get("processing_status")
        == "ocr_completed"
    ]

    empty_results = [
        result
        for result in results
        if result.get("processing_status")
        == "ocr_empty"
    ]

    failed_results = [
        result
        for result in results
        if result.get("processing_status")
        == "failed"
    ]

    print()
    print("=" * 70)
    print("IMAGE OCR PROCESSING")
    print("=" * 70)

    print(f"Images discovered : {len(results)}")
    print(f"OCR completed     : {len(completed_results)}")
    print(f"OCR empty         : {len(empty_results)}")
    print(f"Failed            : {len(failed_results)}")
    print(f"Output directory  : {output_directory}")

    if completed_results:
        print("\nOCR results:")

        for result in completed_results:
            print(
                f"- {result['filename']} | "
                f"characters: {result['character_count']} | "
                f"confidence: {result['ocr_confidence']}"
            )

    if empty_results:
        print("\nNo text detected:")

        for result in empty_results:
            print(f"- {result['filename']}")

    if failed_results:
        print("\nFailed images:")

        for result in failed_results:
            print(
                f"- {result['filename']} | "
                f"{result.get('error')}"
            )

    print("\nStatus            : completed")


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]

    attachments_directory = (
        project_root
        / "data"
        / "raw"
        / "attachments"
    )

    output_directory = (
        project_root
        / "output"
        / "attachments"
        / "ocr"
    )

    results = process_all_images(
        attachments_directory=attachments_directory,
        output_directory=output_directory,
    )

    print_summary(
        results=results,
        output_directory=output_directory,
    )


if __name__ == "__main__":
    main()