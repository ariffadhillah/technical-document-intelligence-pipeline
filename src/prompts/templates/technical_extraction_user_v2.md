# Technical Intelligence Extraction

Produce one structured technical intelligence record from the supplied source.

## Document

- Document ID: {{DOCUMENT_ID}}
- Document Type: {{DOCUMENT_TYPE}}
- Title: {{TITLE}}
- Source Language: {{SOURCE_LANGUAGE}}
- Output Language: {{OUTPUT_LANGUAGE}}

## Source Metadata

{{SOURCE_METADATA}}

## Instructions

Return exactly one JSON object conforming to the response schema supplied by the API.

Extract only information explicitly supported by the source.

Use English for generated descriptive text while preserving names, identifiers,
contact details, URLs, model codes, part numbers, and quoted evidence exactly.

Use null or empty arrays when information is unavailable.

Do not include Markdown, explanations, comments, or text outside the JSON object.

## Source Document

{{DOCUMENT_CONTENT}}