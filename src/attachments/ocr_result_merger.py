from pathlib import Path
import json


def load_json(file_path: Path) -> dict:
    """
    Membaca sebuah file JSON.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"File JSON tidak ditemukan: {file_path}"
        )

    return json.loads(
        file_path.read_text(encoding="utf-8")
    )


def save_json(
    data: dict,
    output_path: Path,
) -> None:
    """
    Menyimpan data sebagai JSON.
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


def load_ocr_results(
    ocr_directory: Path,
) -> dict[str, dict]:
    """
    Membaca seluruh hasil OCR dan mengindeksnya
    berdasarkan nama file gambar asli.
    """

    if not ocr_directory.exists():
        raise FileNotFoundError(
            f"Folder OCR tidak ditemukan: {ocr_directory}"
        )

    ocr_results = {}

    for json_path in sorted(
        ocr_directory.glob("*_ocr.json")
    ):
        result = load_json(json_path)

        filename = result.get("filename")

        if not filename:
            continue

        ocr_results[filename] = result

    return ocr_results


def build_ocr_metadata(
    ocr_result: dict,
) -> dict:
    """
    Mengambil hanya field OCR yang diperlukan
    untuk disematkan ke thread.
    """

    return {
        "engine": ocr_result.get("ocr_engine"),
        "language": ocr_result.get("ocr_language"),
        "confidence": ocr_result.get("ocr_confidence"),
        "character_count": ocr_result.get(
            "character_count",
            0,
        ),
        "word_count": ocr_result.get(
            "word_count",
            0,
        ),
        "has_extracted_text": ocr_result.get(
            "has_extracted_text",
            False,
        ),
        "processing_status": ocr_result.get(
            "processing_status",
        ),
        "raw_text": ocr_result.get(
            "extracted_text",
            "",
        ),
    }


def enrich_attachment(
    attachment: dict,
    attachments_directory: Path,
    ocr_results: dict[str, dict],
) -> dict:
    """
    Menghubungkan satu attachment dengan file lokal
    dan hasil OCR-nya.
    """

    enriched_attachment = attachment.copy()

    filename = attachment.get("filename", "")

    local_path = (
        attachments_directory
        / filename
    )

    file_exists = local_path.exists()

    enriched_attachment["file_status"] = (
        "available"
        if file_exists
        else "missing"
    )

    enriched_attachment["local_path"] = (
        str(local_path)
        if file_exists
        else None
    )

    ocr_result = ocr_results.get(filename)

    if ocr_result:
        enriched_attachment["ocr"] = (
            build_ocr_metadata(ocr_result)
        )

    elif file_exists:
        enriched_attachment["ocr"] = {
            "processing_status": "not_processed",
            "raw_text": "",
        }

    else:
        enriched_attachment["ocr"] = {
            "processing_status": "file_missing",
            "raw_text": "",
        }

    return enriched_attachment


def merge_ocr_with_thread(
    thread_data: dict,
    attachments_directory: Path,
    ocr_results: dict[str, dict],
) -> dict:
    """
    Menambahkan data OCR ke seluruh attachment thread.
    """

    merged_posts = []

    for post in thread_data.get("posts", []):
        merged_post = post.copy()

        merged_post["attachments"] = [
            enrich_attachment(
                attachment=attachment,
                attachments_directory=(
                    attachments_directory
                ),
                ocr_results=ocr_results,
            )
            for attachment in post.get(
                "attachments",
                [],
            )
        ]

        merged_posts.append(merged_post)

    merged_thread = {
        "metadata": thread_data.get(
            "metadata",
            {},
        ).copy(),
        "posts": merged_posts,
    }

    merged_thread["metadata"][
        "processing_status"
    ] = "ocr_merged"

    return merged_thread


def calculate_summary(
    merged_thread: dict,
) -> dict:
    """
    Menghitung ringkasan attachment dan OCR.
    """

    attachments = [
        attachment
        for post in merged_thread.get("posts", [])
        for attachment in post.get(
            "attachments",
            [],
        )
    ]

    available_files = sum(
        attachment.get("file_status")
        == "available"
        for attachment in attachments
    )

    missing_files = sum(
        attachment.get("file_status")
        == "missing"
        for attachment in attachments
    )

    ocr_completed = sum(
        attachment.get("ocr", {}).get(
            "processing_status"
        )
        == "ocr_completed"
        for attachment in attachments
    )

    ocr_empty = sum(
        attachment.get("ocr", {}).get(
            "processing_status"
        )
        == "ocr_empty"
        for attachment in attachments
    )

    return {
        "posts": len(
            merged_thread.get("posts", [])
        ),
        "attachments": len(attachments),
        "available_files": available_files,
        "missing_files": missing_files,
        "ocr_completed": ocr_completed,
        "ocr_empty": ocr_empty,
    }


def print_summary(
    summary: dict,
    output_path: Path,
) -> None:
    """
    Menampilkan ringkasan proses merger.
    """

    print("=" * 70)
    print("OCR RESULT MERGER")
    print("=" * 70)

    print(
        f"Posts              : "
        f"{summary['posts']}"
    )
    print(
        f"Attachments        : "
        f"{summary['attachments']}"
    )
    print(
        f"Available files    : "
        f"{summary['available_files']}"
    )
    print(
        f"Missing files      : "
        f"{summary['missing_files']}"
    )
    print(
        f"OCR completed      : "
        f"{summary['ocr_completed']}"
    )
    print(
        f"OCR empty          : "
        f"{summary['ocr_empty']}"
    )
    print(
        f"Output file        : "
        f"{output_path}"
    )
    print("Status             : success")


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]

    cleaned_thread_path = (
        project_root
        / "output"
        / "cleaned"
        / "thread_6260_cleaned.json"
    )

    attachments_directory = (
        project_root
        / "data"
        / "raw"
        / "attachments"
    )

    ocr_directory = (
        project_root
        / "output"
        / "attachments"
        / "ocr"
    )

    output_path = (
        project_root
        / "output"
        / "merged"
        / "thread_6260_ocr_merged.json"
    )

    thread_data = load_json(
        cleaned_thread_path
    )

    ocr_results = load_ocr_results(
        ocr_directory
    )

    merged_thread = merge_ocr_with_thread(
        thread_data=thread_data,
        attachments_directory=(
            attachments_directory
        ),
        ocr_results=ocr_results,
    )

    save_json(
        data=merged_thread,
        output_path=output_path,
    )

    summary = calculate_summary(
        merged_thread
    )

    print_summary(
        summary=summary,
        output_path=output_path,
    )


if __name__ == "__main__":
    main()