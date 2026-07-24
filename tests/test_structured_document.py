from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from src.config.settings import get_settings  # noqa: E402
from src.prompts.document_prompt import (  # noqa: E402
    SYSTEM_PROMPT,
    build_document_prompt,
)
from src.providers.openai_provider import (  # noqa: E402
    OpenAIProvider,
)
from src.schemas.document_intelligence import (  # noqa: E402
    DocumentIntelligenceResult,
)


def load_json(
    file_path: Path,
) -> dict:
    """
    Load a JSON file.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"JSON file not found: {file_path}"
        )

    return json.loads(
        file_path.read_text(
            encoding="utf-8",
        )
    )


def find_attachment(
    thread_data: dict,
    target_filename: str,
) -> dict:
    """
    Find one attachment by filename.
    """

    for post in thread_data.get("posts", []):
        for attachment in post.get(
            "attachments",
            [],
        ):
            if (
                attachment.get("filename")
                == target_filename
            ):
                return attachment

    raise LookupError(
        f"Attachment not found: {target_filename}"
    )


def save_result(
    result: DocumentIntelligenceResult,
    output_path: Path,
) -> None:
    """
    Save the validated Pydantic result as JSON.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        result.model_dump_json(
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    input_path = (
        PROJECT_ROOT
        / "output"
        / "merged"
        / "thread_6260_ocr_merged.json"
    )

    output_path = (
        PROJECT_ROOT
        / "output"
        / "ai"
        / "IMG_0235_document_intelligence.json"
    )

    target_filename = "IMG_0235.jpeg"

    thread_data = load_json(
        input_path
    )

    attachment = find_attachment(
        thread_data=thread_data,
        target_filename=target_filename,
    )

    raw_ocr_text = (
        attachment
        .get("ocr", {})
        .get("raw_text", "")
    )

    if not raw_ocr_text.strip():
        raise ValueError(
            f"OCR text is empty for {target_filename}"
        )

    user_prompt = build_document_prompt(
        filename=target_filename,
        raw_ocr_text=raw_ocr_text,
    )

    settings = get_settings()

    provider = OpenAIProvider(
        settings=settings,
    )

    print("=" * 70)
    print("STRUCTURED DOCUMENT INTELLIGENCE TEST")
    print("=" * 70)
    print(f"Input file          : {target_filename}")
    print(f"Model               : {settings.openai_model}")
    print(
        f"OCR characters      : "
        f"{len(raw_ocr_text)}"
    )
    print("AI processing       : started")

    result = provider.generate_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_schema=DocumentIntelligenceResult,
    )

    save_result(
        result=result,
        output_path=output_path,
    )

    print(
        f"Document type       : "
        f"{result.document_type}"
    )
    print(
        f"Source language     : "
        f"{result.source_language}"
    )
    print(
        f"Extracted vehicle   : "
        f"{result.technical_entities.vehicle}"
    )
    print(
        f"Extracted engine    : "
        f"{result.technical_entities.engine}"
    )
    print(
        f"Correction notes    : "
        f"{len(result.correction_notes)}"
    )
    print(
        f"Warnings            : "
        f"{len(result.warnings)}"
    )
    print(f"Output file         : {output_path}")
    print("Status              : success")


if __name__ == "__main__":
    main()