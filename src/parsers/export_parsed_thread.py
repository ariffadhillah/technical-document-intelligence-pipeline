from pathlib import Path
import json

from src.parsers.thread_parser import parse_thread
from src.parsers.thread_validator import validate_thread


def save_parsed_thread(
    thread_data: dict,
    output_path: Path,
) -> None:
    """
    Menyimpan hasil parser ke file JSON.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            thread_data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]

    input_file = (
        project_root
        / "data"
        / "raw"
        / "text_logs"
        / "thread_6260.md"
    )

    output_file = (
        project_root
        / "data"
        / "processed"
        / "thread_6260_parsed.json"
    )

    thread_data = parse_thread(input_file)

    validation_result = validate_thread(thread_data)

    if validation_result["status"] != "passed":
        print("Export dibatalkan karena validasi gagal.")

        for error in validation_result["errors"]:
            print(f"- {error}")

        raise SystemExit(1)

    save_parsed_thread(
        thread_data,
        output_file,
    )

    print("=" * 70)
    print("PARSED THREAD EXPORT")
    print("=" * 70)

    print(f"Input file      : {input_file}")
    print(f"Output file     : {output_file}")
    print(f"Thread ID       : {thread_data['metadata'].get('thread_id')}")
    print(f"Posts exported  : {len(thread_data['posts'])}")
    print("Status          : success")


if __name__ == "__main__":
    main()