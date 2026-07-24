from pathlib import Path

import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARSER_DIR = PROJECT_ROOT / "src" / "parsers"

sys.path.append(str(PARSER_DIR))

from src.parsers.thread_parser import parse_thread


def validate_attachments(
    posts: list[dict],
    attachments_directory: Path,
) -> dict:
    """
    Memeriksa apakah attachment yang direferensikan
    oleh setiap post tersedia di folder attachments.
    """

    referenced_files = []
    existing_files = []
    missing_files = []

    for post in posts:
        post_id = post["post_id"]

        for attachment in post.get("attachments", []):
            filename = attachment["filename"]
            attachment_path = attachments_directory / filename

            reference = {
                "post_id": post_id,
                "filename": filename,
                "type": attachment["type"],
                "path": str(attachment_path),
            }

            referenced_files.append(reference)

            if attachment_path.exists():
                existing_files.append(reference)
            else:
                missing_files.append(reference)

    return {
        "status": "passed" if not missing_files else "warning",
        "total_references": len(referenced_files),
        "existing_files": len(existing_files),
        "missing_files": len(missing_files),
        "references": referenced_files,
        "missing": missing_files,
    }


def print_validation_result(result: dict) -> None:
    """
    Menampilkan hasil validasi attachment.
    """

    print("=" * 70)
    print("ATTACHMENT VALIDATION")
    print("=" * 70)

    print(f"Status            : {result['status']}")
    print(f"Total references  : {result['total_references']}")
    print(f"Existing files    : {result['existing_files']}")
    print(f"Missing files     : {result['missing_files']}")

    if result["missing"]:
        print("\nMissing attachments:")

        for item in result["missing"]:
            print(
                f"- {item['filename']} "
                f"| post: {item['post_id']} "
                f"| type: {item['type']}"
            )
    else:
        print("\nSemua attachment tersedia.")


def main() -> None:
    thread_file = (
        PROJECT_ROOT
        / "data"
        / "raw"
        / "text_logs"
        / "thread_6260.md"
    )

    attachments_directory = (
        PROJECT_ROOT
        / "data"
        / "raw"
        / "attachments"
    )

    thread_data = parse_thread(thread_file)

    result = validate_attachments(
        posts=thread_data["posts"],
        attachments_directory=attachments_directory,
    )

    print_validation_result(result)


if __name__ == "__main__":
    main()