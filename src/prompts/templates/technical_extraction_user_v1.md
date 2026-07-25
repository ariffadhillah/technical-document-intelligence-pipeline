# Technical Knowledge Extraction Request

Analyze the supplied technical document and produce a structured technical
knowledge record.

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

## Extraction Requirements

Extract, when supported by the source:

- a concise technical summary;
- topics and system categories;
- vehicles and vehicle variants;
- engines and engine specifications;
- transmissions and driveline systems;
- manufacturers, organizations, suppliers, workshops, people, and locations;
- supplier or fabricator contact information;
- technical specifications and physical measurements;
- part names, manufacturer part numbers, and alternative references;
- maintenance, inspection, repair, installation, and modification tasks;
- diagnostic symptoms, possible causes, and recommended actions;
- safety, compatibility, legal, operational, and modification warnings;
- technical recommendations;
- technical references and document identifiers.

Do not add entities merely because they commonly occur in this type of
equipment. Extract only what is supported by the supplied material.

Set:

- `processing.schema_version` to `1.0.0`;
- `processing.source_stage` to `content_aggregated`;
- `processing.output_stage` to `structured_knowledge`;
- `processing.ready_for_rendering` to `true` only when the document is
  sufficiently structured and translated for downstream rendering;
- `translation_quality.source_language` to the supplied source language;
- `translation_quality.target_language` to the supplied output language;
- `translation_quality.translated` according to whether source prose was
  translated.

The `translated_markdown_content` field may be null during this extraction
stage. A later renderer can produce the final Markdown document.

## Source Document

{{DOCUMENT_CONTENT}}