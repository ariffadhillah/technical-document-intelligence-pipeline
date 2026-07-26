from __future__ import annotations

VISION_SYSTEM_PROMPT = """
You are a production-grade Document Intelligence system.

Your task is to analyze ONE document page.

Your response MUST be valid JSON only.

Do not explain anything.

Do not wrap the JSON inside markdown.

Do not return comments.

Always return every field.

Missing values should be null or empty arrays.

The OCR text should preserve line breaks whenever possible.
""".strip()


VISION_OUTPUT_SCHEMA = """
{
  "document_type": "...",
  "page_type": "...",
  "language": "...",
  "title": "...",
  "summary": "...",
  "ocr_text": "...",
  "keywords": [],
  "entities": [],
  "tables": [],
  "figures": [],
  "warnings": [],
  "confidence": 0.0
}
""".strip()