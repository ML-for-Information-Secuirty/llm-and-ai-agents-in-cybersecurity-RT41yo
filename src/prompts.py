from __future__ import annotations

import json
from typing import Any


def _compact_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def build_normalization_prompt(
    raw_event: dict[str, Any],
    taxonomy_fields_en: dict[str, Any] | None,
    examples: list[dict[str, Any]],
) -> str:
    allowed_fields = []
    if isinstance(taxonomy_fields_en, dict):
        fields_block = taxonomy_fields_en.get("Fields", {})
        if isinstance(fields_block, dict):
            allowed_fields = sorted(fields_block.keys())

    examples_text_parts = []
    for idx, ex in enumerate(examples, start=1):
        examples_text_parts.append(
            f"Example {idx}\n"
            f"Raw event:\n{_compact_json(ex['event'])}\n\n"
            f"Normalized fields:\n{_compact_json(ex['norm_fields'])}"
        )
    examples_text = "\n\n".join(examples_text_parts)

    return f"""
You are normalizing a Windows security event into flat SIEM fields.

Task:
- Extract only meaningful security-relevant fields.
- Output a flat JSON object.
- Use field names from the SIEM taxonomy when possible.
- Do not invent unsupported fields unless they are obvious standard flat SIEM fields already seen in examples.
- Keep only useful fields.
- Values must be strings.
- Do not output explanations.
- Do not output markdown.
- Output only valid JSON.

Allowed SIEM field names from taxonomy:
{_compact_json(allowed_fields)}

Few-shot examples:
{examples_text}

Now normalize this raw event:
{_compact_json(raw_event)}
""".strip()
