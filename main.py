from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.cleaners.text_cleaner import clean_thread
from src.loaders.raw_dataset_loader import load_all_threads


RAW_DIRECTORY = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIRECTORY = PROJECT_ROOT / "data" / "processed"
CLEANED_DIRECTORY = PROJECT_ROOT / "output" / "cleaned"


def save_json(
    payload: dict[str, Any],
    output_path: Path,
) -> None:
    """Atomically save formatted JSON."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = output_path.with_suffix(
        output_path.suffix + ".tmp"
    )

    temporary_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temporary_path.replace(output_path)


def process_thread(
    thread_data: dict[str, Any],
    position: int,
    total: int,
) -> dict[str, Any]:
    metadata = thread_data.get("metadata", {})
    thread_id = metadata.get("thread_id", "unknown")
    title = metadata.get("title", "Untitled thread")

    posts = thread_data.get("posts", [])
    attachment_count = sum(
        len(post.get("attachments", []))
        for post in posts
    )

    print(
        f"\n[{position}/{total}] "
        f"thread_{thread_id}"
    )
    print(f"    Title       : {title}")
    print(f"    Posts       : {len(posts)}")
    print(f"    Attachments : {attachment_count}")

    parsed_output_path = (
        PROCESSED_DIRECTORY
        / f"thread_{thread_id}_parsed.json"
    )

    save_json(
        payload=thread_data,
        output_path=parsed_output_path,
    )

    print("    [OK] Raw data loaded and normalized")

    cleaned_thread = clean_thread(thread_data)

    cleaned_output_path = (
        CLEANED_DIRECTORY
        / f"thread_{thread_id}_cleaned.json"
    )

    save_json(
        payload=cleaned_thread,
        output_path=cleaned_output_path,
    )

    print("    [OK] Text sanitization completed")
    print(f"    Output      : {cleaned_output_path}")

    return {
        "thread_id": thread_id,
        "title": title,
        "posts": len(posts),
        "attachments": attachment_count,
        "parsed_output": str(parsed_output_path),
        "cleaned_output": str(cleaned_output_path),
        "status": "success",
    }


def main() -> int:
    print("=" * 72)
    print("TECHNICAL DOCUMENT INTELLIGENCE PIPELINE")
    print("=" * 72)
    print(f"Project root : {PROJECT_ROOT}")
    print(f"Raw data     : {RAW_DIRECTORY}")

    try:
        threads = load_all_threads(
            raw_directory=RAW_DIRECTORY
        )
    except Exception as error:
        print(f"\nDataset loading failed: {error}")
        return 1

    print(f"Threads found: {len(threads)}")

    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for position, thread_data in enumerate(
        threads,
        start=1,
    ):
        try:
            result = process_thread(
                thread_data=thread_data,
                position=position,
                total=len(threads),
            )
            results.append(result)
        except Exception as error:
            thread_id = (
                thread_data
                .get("metadata", {})
                .get("thread_id", "unknown")
            )

            print(
                f"    [FAILED] thread_{thread_id}: "
                f"{error}"
            )

            failures.append(
                {
                    "thread_id": str(thread_id),
                    "error": str(error),
                }
            )

    manifest = {
        "pipeline_stage": "load_parse_and_clean",
        "thread_count": len(threads),
        "successful": len(results),
        "failed": len(failures),
        "threads": results,
        "failures": failures,
    }

    manifest_path = (
        PROJECT_ROOT
        / "output"
        / "reports"
        / "pipeline_manifest.json"
    )

    save_json(
        payload=manifest,
        output_path=manifest_path,
    )

    print("\n" + "=" * 72)
    print("PIPELINE SUMMARY")
    print("=" * 72)
    print(f"Threads discovered : {len(threads)}")
    print(f"Successful         : {len(results)}")
    print(f"Failed             : {len(failures)}")
    print(f"Manifest           : {manifest_path}")

    if failures:
        print("Status             : completed_with_errors")
        return 1

    print("Status             : success")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())