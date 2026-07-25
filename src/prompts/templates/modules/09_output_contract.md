# Strict Output Contract

Return exactly one valid JSON object.

Do not include:

- Markdown code fences
- introductory prose
- explanatory prose
- comments
- trailing text

The returned object must conform exactly to the supplied JSON schema.

Unknown properties are forbidden.

Use only enum values defined by the schema.

All required properties must be present.

Use null or empty arrays for unavailable optional information.

All generated descriptive prose must be in English.

The final output will be validated by strict software. Invalid JSON,
unexpected properties, missing required properties, incompatible values,
or invalid enum values may cause the complete extraction to be rejected.