# Technical and Organization Intelligence Extraction Request

Analyze the supplied source and produce one structured technical intelligence
record.

## Document Identity

- Document ID: {{DOCUMENT_ID}}
- Document Type: {{DOCUMENT_TYPE}}
- Title: {{TITLE}}
- Source Language: {{SOURCE_LANGUAGE}}
- Output Language: {{OUTPUT_LANGUAGE}}

## Source Metadata

{{SOURCE_METADATA}}

## Required JSON Schema

The returned JSON object must conform exactly to this schema:

{{JSON_SCHEMA}}

## Extraction Scope

Extract, when supported by the source:

- concise technical summary
- topics and system categories
- organizations and organization relationships
- company contact information
- products, services, capabilities, and represented brands
- commercial example prices when supported by the schema
- vehicles and vehicle variants
- engines and engine specifications
- transmissions and driveline systems
- parts and product identifiers
- technical specifications and measurements
- maintenance, inspection, repair, installation, and modification tasks
- diagnostic findings and recommendations
- warnings and unresolved technical discussion
- traceable technical references

Do not add information merely because it commonly occurs in this kind of
document.

Set:

- `processing.schema_version` to `2.0.0`
- `processing.source_stage` to `content_aggregated`
- `processing.output_stage` to `structured_knowledge`
- `processing.ready_for_rendering` to `true` only when the output is
  sufficiently structured and grounded
- `translation_quality.source_language` to the supplied source language
- `translation_quality.target_language` to the supplied output language
- `translation_quality.translated` according to whether descriptive prose was
  translated

The `translated_markdown_content` field may remain null during extraction.

## Source Document

{{DOCUMENT_CONTENT}}