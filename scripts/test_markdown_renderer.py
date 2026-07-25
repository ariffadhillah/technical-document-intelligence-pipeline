from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.renderers import TechnicalMarkdownRenderer


SAMPLE_INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "samples"
    / "thread_6260_structured_sample.json"
)

TEST_OUTPUT_PATH = (
    PROJECT_ROOT
    / "output"
    / "rendered"
    / "thread_6260"
    / "technical_manual.md"
)


REQUIRED_CONTENT = (
    "# Kat 1A1.1 6x6",
    "## Executive Summary",
    "## Vehicle Information",
    "MAN KAT 1A1.1",
    "## Engine",
    "D2866 LFGO4",
    "## Transmission",
    "ZF WSK 400",
    "## Technical Specifications",
    "## Maintenance and Workshop Tasks",
    "## Safety and Technical Warnings",
    "## Recommendations",
    "## Technical References",
)


def main() -> int:
    print("=" * 72)
    print("MARKDOWN RENDERER TEST")
    print("=" * 72)

    renderer = TechnicalMarkdownRenderer(
        include_evidence=True,
        include_empty_sections=False,
        include_processing_metadata=True,
    )

    rendered_path = renderer.render_file(
        input_path=SAMPLE_INPUT_PATH,
        output_path=TEST_OUTPUT_PATH,
    )

    markdown = rendered_path.read_text(
        encoding="utf-8"
    )

    missing_content = [
        required
        for required in REQUIRED_CONTENT
        if required not in markdown
    ]

    if missing_content:
        print("[FAILED]")
        print(
            "The rendered document is missing "
            "required content:"
        )

        for item in missing_content:
            print(f" - {item}")

        return 1

    print(f"Input  : {SAMPLE_INPUT_PATH}")
    print(f"Output : {rendered_path}")
    print(f"Lines  : {len(markdown.splitlines())}")
    print(f"Chars  : {len(markdown)}")
    print()
    print("[OK] Markdown renderer is working")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())