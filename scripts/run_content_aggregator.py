from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.aggregators.content_aggregator import (
    ContentAggregator,
)
 

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "merged"
)

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "aggregated"
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_json(
    payload: dict[str, Any],
    output_path: Path,
) -> None:
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


def main() -> int:
    print("=" * 72)
    print("CONTENT AGGREGATION STAGE")
    print("=" * 72)

    input_files = sorted(
        INPUT_DIRECTORY.glob(
            "thread_*_content_merged.json"
        )
    )

    if not input_files:
        print(
            "No merged thread files found in:"
        )
        print(INPUT_DIRECTORY)
        return 1

    aggregator = ContentAggregator()

    successful = 0
    failed = 0

    print(f"Documents found: {len(input_files)}")

    for position, input_path in enumerate(
        input_files,
        start=1,
    ):
        try:
            thread_data = load_json(input_path)
            aggregated = aggregator.aggregate(
                thread_data
            )

            document_id = aggregated["document_id"]

            output_path = (
                OUTPUT_DIRECTORY
                / f"{document_id}_aggregated.json"
            )

            save_json(
                payload=aggregated,
                output_path=output_path,
            )

            statistics = aggregated["statistics"]

            print(
                f"\n[{position}/{len(input_files)}] "
                f"{document_id}"
            )
            print(
                f"    Posts       : "
                f"{statistics['post_count']}"
            )
            print(
                f"    Attachments : "
                f"{statistics['attachment_count']}"
            )
            print(
                f"    Forum chars : "
                f"{statistics['forum_character_count']}"
            )
            print(
                f"    OCR chars   : "
                f"{statistics['ocr_character_count']}"
            )
            print(
                f"    PDF chars   : "
                f"{statistics['pdf_character_count']}"
            )
            print(
                f"    Total chars : "
                f"{statistics['combined_character_count']}"
            )
            print(f"    [OK] {output_path}")

            successful += 1

        except Exception as error:
            print(
                f"\n[FAILED] {input_path.name}: "
                f"{error}"
            )
            failed += 1

    print("\n" + "=" * 72)
    print("AGGREGATION SUMMARY")
    print("=" * 72)
    print(f"Successful : {successful}")
    print(f"Failed     : {failed}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())