from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.processors.structured_output_validator import (
    StructuredOutputValidationError,
    StructuredOutputValidator,
)
from src.prompts import (
    PromptBuilderError,
    TechnicalPromptBuilder,
)
from src.providers import (
    ProviderError,
    ProviderFactory,
    ProviderMessage,
    ProviderRequest,
)
from src.schemas.technical_knowledge import (
    StructuredTechnicalDocument,
)


DEFAULT_INPUT_PATH = (
    PROJECT_ROOT
    / "output"
    / "aggregated"
    / "thread_6260_aggregated.json"
)

DEFAULT_MOCK_RESPONSE_PATH = (
    PROJECT_ROOT
    / "data"
    / "samples"
    / "thread_6260_structured_sample.json"
)

DEFAULT_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "ai"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the technical extraction pipeline "
            "using the offline MockProvider."
        )
    )

    parser.add_argument(
        "input_path",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=(
            "Path to an aggregated JSON document."
        ),
    )

    parser.add_argument(
        "--mock-response",
        type=Path,
        default=DEFAULT_MOCK_RESPONSE_PATH,
        help=(
            "Path to the predefined structured "
            "mock response."
        ),
    )

    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help=(
            "Base output directory for AI artifacts."
        ),
    )

    parser.add_argument(
        "--model",
        default="mock-technical-extraction-v1",
        help="Mock model identifier.",
    )

    return parser.parse_args()


def atomic_write_json(
    output_path: Path,
    payload: dict[str, Any],
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
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary_path.replace(output_path)


def atomic_write_text(
    output_path: Path,
    content: str,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = output_path.with_suffix(
        output_path.suffix + ".tmp"
    )

    temporary_path.write_text(
        content,
        encoding="utf-8",
    )

    temporary_path.replace(output_path)


def build_provider_request(
    *,
    system_prompt: str,
    user_prompt: str,
    document_id: str,
    prompt_version: str,
    model: str,
) -> ProviderRequest:
    json_schema = (
        StructuredTechnicalDocument.model_json_schema()
    )

    return ProviderRequest(
        messages=(
            ProviderMessage(
                role="system",
                content=system_prompt,
            ),
            ProviderMessage(
                role="user",
                content=user_prompt,
            ),
        ),
        model=model,
        temperature=0.0,
        max_output_tokens=16000,
        timeout_seconds=60,
        response_format="json_schema",
        json_schema=json_schema,
        metadata={
            "document_id": document_id,
            "prompt_version": prompt_version,
            "pipeline_mode": "mock",
        },
    )


def main() -> int:
    arguments = parse_arguments()

    input_path = arguments.input_path.resolve()
    mock_response_path = (
        arguments.mock_response.resolve()
    )
    output_base = (
        arguments.output_directory.resolve()
    )

    print("=" * 72)
    print("MOCK TECHNICAL AI PIPELINE")
    print("=" * 72)

    try:
        prompt_builder = TechnicalPromptBuilder()

        prompt = prompt_builder.build_from_file(
            input_path=input_path
        )

        document_output_directory = (
            output_base / prompt.document_id
        )

        document_output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        prompt_paths = (
            prompt_builder.save_prompt_bundle(
                prompt=prompt,
                output_directory=(
                    document_output_directory
                ),
            )
        )

        request = build_provider_request(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
            document_id=prompt.document_id,
            prompt_version=prompt.prompt_version,
            model=arguments.model,
        )

        provider = ProviderFactory.create(
            "mock",
            response_file=mock_response_path,
        )

        request_path = (
            document_output_directory
            / "03_provider_request.json"
        )

        atomic_write_json(
            output_path=request_path,
            payload=request.to_dict(),
        )

        response = provider.generate(request)

        raw_response_path = (
            document_output_directory
            / "04_raw_response.json"
        )

        try:
            raw_payload = json.loads(
                response.raw_text
            )

        except json.JSONDecodeError:
            raw_payload = {
                "raw_text": response.raw_text,
            }

        atomic_write_json(
            output_path=raw_response_path,
            payload=raw_payload,
        )

        validator = StructuredOutputValidator()

        validated_document = (
            validator.validate_json_text(
                response.raw_text
            )
        )

        validated_path = (
            document_output_directory
            / "05_validated_response.json"
        )

        validator.save_validated_document(
            document=validated_document,
            output_path=validated_path,
        )

        provider_metadata_path = (
            document_output_directory
            / "06_provider_metadata.json"
        )

        provider_metadata = response.to_dict(
            include_raw_response=False
        )

        # The complete model output is already stored in
        # 04_raw_response.json, so it should not be duplicated
        # inside operational metadata.
        provider_metadata.pop(
            "raw_text",
            None,
        )

        provider_metadata["request"] = {
            "document_id": prompt.document_id,
            "prompt_name": prompt.prompt_name,
            "prompt_version": (
                prompt.prompt_version
            ),
            "system_prompt_sha256": (
                prompt.system_prompt_sha256
            ),
            "user_prompt_sha256": (
                prompt.user_prompt_sha256
            ),
            "source_content_sha256": (
                prompt.source_content_sha256
            ),
        }

        atomic_write_json(
            output_path=provider_metadata_path,
            payload=provider_metadata,
        )

        numbered_system_prompt_path = (
            document_output_directory
            / "01_system_prompt.md"
        )

        numbered_user_prompt_path = (
            document_output_directory
            / "02_user_prompt.md"
        )

        atomic_write_text(
            output_path=numbered_system_prompt_path,
            content=prompt.system_prompt + "\n",
        )

        atomic_write_text(
            output_path=numbered_user_prompt_path,
            content=prompt.user_prompt + "\n",
        )

    except (
        FileNotFoundError,
        OSError,
        PromptBuilderError,
        ProviderError,
        StructuredOutputValidationError,
        ValueError,
    ) as error:
        print()
        print("[FAILED]")
        print(error)
        return 1

    print(f"Input document     : {input_path}")
    print(
        f"Document ID        : "
        f"{prompt.document_id}"
    )
    print(
        f"Prompt version     : "
        f"{prompt.prompt_version}"
    )
    print(
        f"Provider           : "
        f"{response.provider}"
    )
    print(
        f"Model              : "
        f"{response.model}"
    )
    print(
        f"Input tokens       : "
        f"{response.usage.input_tokens}"
    )
    print(
        f"Output tokens      : "
        f"{response.usage.output_tokens}"
    )
    print(
        f"Total tokens       : "
        f"{response.usage.total_tokens}"
    )
    print(
        f"Duration           : "
        f"{response.duration_seconds} seconds"
    )

    print()
    print("[OK] Mock AI pipeline completed")
    print(
        f"System prompt      : "
        f"{numbered_system_prompt_path}"
    )
    print(
        f"User prompt        : "
        f"{numbered_user_prompt_path}"
    )
    print(
        f"Provider request   : "
        f"{request_path}"
    )
    print(
        f"Raw response       : "
        f"{raw_response_path}"
    )
    print(
        f"Validated response : "
        f"{validated_path}"
    )
    print(
        f"Provider metadata  : "
        f"{provider_metadata_path}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())