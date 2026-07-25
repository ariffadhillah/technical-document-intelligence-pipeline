from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.processors.structured_output_validator import (
    StructuredOutputValidationError,
    StructuredOutputValidator,
)


DEFAULT_INPUT = (
    PROJECT_ROOT
    / "data"
    / "samples"
    / "thread_6260_structured_sample.json"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a structured technical knowledge "
            "JSON document."
        )
    )

    parser.add_argument(
        "input_path",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT,
        help=(
            "Path to structured JSON. Defaults to the "
            "thread 6260 sample."
        ),
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    input_path = arguments.input_path.resolve()

    print("=" * 72)
    print("STRUCTURED TECHNICAL OUTPUT VALIDATOR")
    print("=" * 72)
    print(f"Input: {input_path}")

    validator = StructuredOutputValidator()

    try:
        document = validator.validate_file(
            input_path=input_path
        )

    except (
        FileNotFoundError,
        StructuredOutputValidationError,
    ) as error:
        print()
        print("[FAILED]")
        print(error)
        return 1

    print()
    print("[OK] Structured document is valid")
    print(f"Document ID       : {document.document_id}")
    print(f"Title             : {document.title}")
    print(f"Vehicles          : {len(document.vehicles)}")
    print(f"Engines           : {len(document.engines)}")
    print(
        "Transmissions     : "
        f"{len(document.transmissions)}"
    )
    print(
        "Specifications    : "
        f"{len(document.technical_specifications)}"
    )
    print(
        "Maintenance tasks : "
        f"{len(document.maintenance_tasks)}"
    )
    print(
        "Ready to render   : "
        f"{document.processing.ready_for_rendering}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())