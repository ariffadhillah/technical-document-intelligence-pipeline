from pathlib import Path

from src.parsers.thread_parser import parse_thread


REQUIRED_METADATA_FIELDS = [
    "thread_id",
    "thread_title",
    "forum_section",
    "source_url",
    "source_language",
    "post_count",
]


def validate_metadata(metadata: dict) -> list[str]:
    """
    Memeriksa metadata wajib pada thread.
    """

    errors = []

    for field in REQUIRED_METADATA_FIELDS:
        value = metadata.get(field)

        if value is None or value == "":
            errors.append(f"Metadata wajib tidak tersedia: {field}")

    return errors


def validate_post_count(metadata: dict, posts: list[dict]) -> list[str]:
    """
    Memastikan jumlah post hasil parser sesuai dengan metadata.
    """

    errors = []

    expected_post_count = metadata.get("post_count")
    parsed_post_count = len(posts)

    if expected_post_count != parsed_post_count:
        errors.append(
            "Jumlah post tidak sesuai: "
            f"metadata={expected_post_count}, "
            f"parsed={parsed_post_count}"
        )

    return errors


def validate_duplicate_post_ids(posts: list[dict]) -> list[str]:
    """
    Memastikan tidak ada post ID yang duplikat.
    """

    errors = []
    seen_post_ids = set()

    for post in posts:
        post_id = post.get("post_id")

        if post_id in seen_post_ids:
            errors.append(f"Post ID duplikat ditemukan: {post_id}")

        seen_post_ids.add(post_id)

    return errors


def validate_post_fields(posts: list[dict]) -> list[str]:
    """
    Memastikan setiap post memiliki field penting.
    """

    errors = []

    for post in posts:
        post_id = post.get("post_id", "unknown")

        if not post.get("post_id"):
            errors.append("Post ditemukan tanpa post_id")

        if not post.get("author"):
            errors.append(f"Author kosong pada post: {post_id}")

        if not post.get("date"):
            errors.append(f"Tanggal kosong pada post: {post_id}")

        if not post.get("body"):
            errors.append(f"Body kosong pada post: {post_id}")

    return errors


def validate_thread(thread_data: dict) -> dict:
    """
    Menjalankan seluruh validasi thread.
    """

    metadata = thread_data["metadata"]
    posts = thread_data["posts"]

    errors = []

    errors.extend(validate_metadata(metadata))
    errors.extend(validate_post_count(metadata, posts))
    errors.extend(validate_duplicate_post_ids(posts))
    errors.extend(validate_post_fields(posts))

    result = {
        "status": "passed" if not errors else "failed",
        "thread_id": metadata.get("thread_id"),
        "expected_posts": metadata.get("post_count"),
        "parsed_posts": len(posts),
        "total_errors": len(errors),
        "errors": errors,
    }

    return result


def print_validation_result(result: dict) -> None:
    """
    Menampilkan hasil validasi ke terminal.
    """

    print("=" * 70)
    print("RAW THREAD VALIDATION")
    print("=" * 70)

    print(f"Status          : {result['status']}")
    print(f"Thread ID       : {result['thread_id']}")
    print(f"Expected posts  : {result['expected_posts']}")
    print(f"Parsed posts    : {result['parsed_posts']}")
    print(f"Total errors    : {result['total_errors']}")

    if result["errors"]:
        print("\nValidation errors:")

        for error in result["errors"]:
            print(f"- {error}")

    else:
        print("\nTidak ditemukan masalah pada data mentah.")


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]

    thread_file = (
        project_root
        / "data"
        / "raw"
        / "text_logs"
        / "thread_6260.md"
    )

    thread_data = parse_thread(thread_file)

    validation_result = validate_thread(thread_data)

    print_validation_result(validation_result)


if __name__ == "__main__":
    main()