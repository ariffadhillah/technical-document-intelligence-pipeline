from pathlib import Path
import json
import sys


def load_json(file_path: Path) -> dict:
    if not file_path.exists():
        raise FileNotFoundError(
            f"File tidak ditemukan: {file_path}"
        )

    return json.loads(
        file_path.read_text(encoding="utf-8")
    )


def map_posts_by_id(thread_data: dict) -> dict:
    return {
        post["post_id"]: post
        for post in thread_data.get("posts", [])
    }


def count_attachments(thread_data: dict) -> int:
    return sum(
        len(post.get("attachments", []))
        for post in thread_data.get("posts", [])
    )


def validate_cleaned_thread(
    parsed_data: dict,
    cleaned_data: dict,
) -> dict:
    errors = []
    warnings = []

    parsed_posts = map_posts_by_id(parsed_data)
    cleaned_posts = map_posts_by_id(cleaned_data)

    parsed_post_ids = set(parsed_posts)
    cleaned_post_ids = set(cleaned_posts)

    missing_posts = sorted(
        parsed_post_ids - cleaned_post_ids
    )

    unexpected_posts = sorted(
        cleaned_post_ids - parsed_post_ids
    )

    if missing_posts:
        errors.append(
            f"Post hilang setelah cleaning: {missing_posts}"
        )

    if unexpected_posts:
        errors.append(
            f"Post baru tidak dikenal: {unexpected_posts}"
        )

    parsed_attachment_count = count_attachments(
        parsed_data
    )

    cleaned_attachment_count = count_attachments(
        cleaned_data
    )

    if (
        parsed_attachment_count
        != cleaned_attachment_count
    ):
        errors.append(
            "Jumlah attachment berubah: "
            f"{parsed_attachment_count} -> "
            f"{cleaned_attachment_count}"
        )

    empty_bodies = []

    changed_identity_fields = []

    changed_attachments = []

    for post_id in sorted(
        parsed_post_ids & cleaned_post_ids
    ):
        original_post = parsed_posts[post_id]
        cleaned_post = cleaned_posts[post_id]

        if not cleaned_post.get("body", "").strip():
            empty_bodies.append(post_id)

        for field in ("post_id", "author", "date"):
            if (
                original_post.get(field)
                != cleaned_post.get(field)
            ):
                changed_identity_fields.append(
                    f"{post_id}:{field}"
                )

        if (
            original_post.get("attachments", [])
            != cleaned_post.get("attachments", [])
        ):
            changed_attachments.append(post_id)

    if empty_bodies:
        warnings.append(
            f"Body kosong: {empty_bodies}"
        )

    if changed_identity_fields:
        errors.append(
            "Metadata post berubah: "
            f"{changed_identity_fields}"
        )

    if changed_attachments:
        errors.append(
            "Attachment berubah pada post: "
            f"{changed_attachments}"
        )

    metadata_status = cleaned_data.get(
        "metadata",
        {},
    ).get("processing_status")

    if metadata_status != "cleaned":
        errors.append(
            "processing_status seharusnya "
            f"'cleaned', tetapi ditemukan "
            f"'{metadata_status}'"
        )

    return {
        "status": "success" if not errors else "failed",
        "parsed_posts": len(parsed_posts),
        "cleaned_posts": len(cleaned_posts),
        "parsed_attachments": parsed_attachment_count,
        "cleaned_attachments": cleaned_attachment_count,
        "errors": errors,
        "warnings": warnings,
    }


def print_report(result: dict) -> None:
    print("=" * 70)
    print("CLEANER VALIDATION")
    print("=" * 70)

    print(
        f"Status              : "
        f"{result['status']}"
    )
    print(
        f"Parsed posts        : "
        f"{result['parsed_posts']}"
    )
    print(
        f"Cleaned posts       : "
        f"{result['cleaned_posts']}"
    )
    print(
        f"Parsed attachments  : "
        f"{result['parsed_attachments']}"
    )
    print(
        f"Cleaned attachments : "
        f"{result['cleaned_attachments']}"
    )

    if result["errors"]:
        print("\nErrors:")

        for error in result["errors"]:
            print(f"- {error}")

    if result["warnings"]:
        print("\nWarnings:")

        for warning in result["warnings"]:
            print(f"- {warning}")

    if not result["errors"] and not result["warnings"]:
        print("\nNo validation issues found.")


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]

    parsed_file = (
        project_root
        / "data"
        / "processed"
        / "thread_6260_parsed.json"
    )

    cleaned_file = (
        project_root
        / "output"
        / "cleaned"
        / "thread_6260_cleaned.json"
    )

    parsed_data = load_json(parsed_file)
    cleaned_data = load_json(cleaned_file)

    result = validate_cleaned_thread(
        parsed_data=parsed_data,
        cleaned_data=cleaned_data,
    )

    print_report(result)

    if result["status"] != "success":
        sys.exit(1)


if __name__ == "__main__":
    main()