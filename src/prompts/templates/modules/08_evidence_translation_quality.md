# Evidence, Translation, and Quality Rules

Every important extracted fact should include the strongest available
evidence.

Evidence types:

- `forum_post`
  Information originating from forum discussion text.

- `pdf_text`
  Information extracted from a PDF text layer.

- `ocr`
  Information extracted by optical character recognition.

- `vision_summary`
  Information derived from visual analysis.

- `metadata`
  Information obtained from source or attachment metadata.

Prefer evidence containing:

- post ID
- attachment filename
- source URL
- short supporting quotation

Use direct quotations when they clearly support the extracted claim.
Quotations may remain in the original language.

Do not attach unrelated evidence merely because it belongs to the same
document.

## Confidence

Use `high` when the value is directly and clearly stated.

Use `medium` when the value is strongly supported but assembled from multiple
nearby facts.

Use `low` when the value is incomplete, ambiguous, OCR-damaged, or indirectly
stated.

## Translation quality

The protected token count and preserved token count are quality metadata,
not estimates of ordinary translated words.

Protected tokens include identifiable technical strings such as:

- model codes
- part numbers
- engine codes
- transmission codes
- URLs
- email addresses
- telephone numbers
- document identifiers

`preserved_token_count` must never exceed `protected_token_count`.

When accurate counts cannot be established, use zero for both counts and add
a validation warning rather than guessing.

Do not claim perfect fidelity when the source contains substantial OCR damage
or unresolved ambiguity.