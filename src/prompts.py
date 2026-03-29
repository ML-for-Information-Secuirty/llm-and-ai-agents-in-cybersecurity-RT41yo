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
- Use a compact structure similar to the few-shot examples.
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


def build_classification_prompt(
    correlation_summary: dict[str, Any],
    classification_examples: list[dict[str, Any]],
) -> str:
    example_texts = []

    for idx, ex in enumerate(classification_examples[:6], start=1):
        example_texts.append(
            f"Example {idx}\n"
            f"Rule name: {ex.get('rule_name')}\n"
            f"MITRE category dir: {ex.get('category_dir')}\n"
            f"Importance: {ex.get('importance')}\n"
            f"Tactic candidates: {ex.get('tactic_candidates')}\n"
            f"Technique ID candidates: {ex.get('technique_id_candidates')}\n"
            f"Description: {ex.get('description_en')}\n"
        )

    examples_text = "\n".join(example_texts)

    return f"""
You are classifying a Windows correlation rule into MITRE ATT&CK tactic, technique, and importance.

Rules:
- Analyze the whole correlation, not a single event.
- Return exactly one tactic, one technique, and one importance.
- Importance must be one of: low, medium, high.
- Use official MITRE ATT&CK names in English.
- If you choose a sub-technique, write it in this exact format:
  "Parent Technique: Sub-technique"
- Example:
  "Credentials from Password Stores: Credentials from Web Browsers"
- Do not return ATT&CK IDs.
- Do not output explanations.
- Do not output markdown.
- Output only valid JSON.

Expected JSON format:
{{
  "tactic": "...",
  "technique": "...",
  "importance": "low|medium|high"
}}

Few-shot training hints:
{examples_text}

Correlation summary:
{_compact_json(correlation_summary)}
""".strip()


def build_localization_prompt(
    language: str,
    correlation_summary: dict[str, Any],
    answers: dict[str, Any],
    localization_examples: list[dict[str, Any]],
) -> str:
    assert language in {"en", "ru"}

    example_texts = []
    for idx, ex in enumerate(localization_examples[:3], start=1):
        key = "i18n_en" if language == "en" else "i18n_ru"
        example_texts.append(
            f"Example {idx}\n"
            f"Rule name: {ex.get('rule_name')}\n"
            f"Category dir: {ex.get('category_dir')}\n"
            f"YAML:\n{_compact_json(ex.get(key))}\n"
        )

    examples_text = "\n".join(example_texts)

    language_rule = (
        "Write all texts in English."
        if language == "en"
        else "Write all texts in Russian."
    )

    return f"""
You are generating a SIEM localization YAML for a correlation rule.

Rules:
- Output only valid YAML.
- Do not output markdown.
- Preserve a compact structure similar to the few-shot examples.
- The YAML must contain:
  - Description
  - EventDescriptions
- EventDescriptions must be a list with 1 or 2 items.
- Each item must contain:
  - LocalizationId
  - EventDescription
- Use placeholders like:
  - {{subject.account.id}}
  - {{event_src.host}}
  - {{object.process.cmdline}}
  - {{object.name}}
  when appropriate.
- Keep the text concise, technical, and SOC-friendly.
- Reflect the meaning of the correlation, not a single raw event.
- Tactic/technique names do not have to be copied into the text verbatim unless natural.
- {language_rule}

Expected YAML structure:
Description: "..."
EventDescriptions:
  - LocalizationId: "..."
    EventDescription: "..."

Few-shot examples:
{examples_text}

Answers JSON:
{_compact_json(answers)}

Correlation summary:
{_compact_json(correlation_summary)}
""".strip()
