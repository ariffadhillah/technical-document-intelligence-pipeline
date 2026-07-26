# main.py integration patch

## 1. Add imports

from src.renderers import RenderingStageRunner
from src.rag import RAGStageRunner

## 2. Add output directories

RENDERED_OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "rendered"
)

RAG_OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "rag"
)

## 3. Extend process_thread parameters

rendering_stage_runner: RenderingStageRunner | None = None,
rag_stage_runner: RAGStageRunner | None = None,

## 4. Before `if should_run_ai`, initialize

rendering_result: dict[str, Any] | None = None
rag_result: dict[str, Any] | None = None

## 5. Immediately after AI result is returned and `ai_result = result.to_dict()`

validated_document = (
    rendering_stage_runner.load_validated_document(
        Path(result.validated_response_path)
    )
    if rendering_stage_runner is not None
    else None
)

if (
    validated_document is not None
    and rendering_stage_runner is not None
):
    rendered = rendering_stage_runner.run(
        document=validated_document,
    )
    rendering_result = rendered.to_dict()
    print(
        "    [OK] Rendered outputs created "
        f"({rendered.markdown_path})"
    )

if (
    validated_document is not None
    and rag_stage_runner is not None
):
    rag = rag_stage_runner.run(
        document=validated_document,
    )
    rag_result = rag.to_dict()
    print(
        "    [OK] RAG chunks created "
        f"(chunks={rag.chunk_count})"
    )

## 6. Add to process_thread return payload

"rendering": rendering_result,
"rag": rag_result,

## 7. In main(), initialize runners once

rendering_stage_runner = RenderingStageRunner(
    output_directory=RENDERED_OUTPUT_DIRECTORY,
)

rag_stage_runner = RAGStageRunner(
    output_directory=RAG_OUTPUT_DIRECTORY,
)

## 8. Pass runners into process_thread()

rendering_stage_runner=rendering_stage_runner,
rag_stage_runner=rag_stage_runner,

## 9. Add manifest totals

rendered_results = [
    result["rendering"]
    for result in results
    if result.get("rendering") is not None
]

rag_results = [
    result["rag"]
    for result in results
    if result.get("rag") is not None
]

"rendered_documents": len(rendered_results),
"rag_documents": len(rag_results),
"rag_chunks": sum(
    item["chunk_count"]
    for item in rag_results
),

## Important

The current AIStageResult does not expose `validated_document`.
Therefore the integration intentionally reloads and validates
`05_validated_response.json` through:

RenderingStageRunner.load_validated_document(...)

This avoids modifying the stable AI stage for now.
