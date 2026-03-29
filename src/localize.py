from __future__ import annotations

from pathlib import Path
from typing import Any

from io_utils import read_json, write_yaml
from llm_utils import LLMClient
from prompts import build_localization_prompt
from classify import build_correlation_summary


def get_i18n_dir(correlation_dir: Path) -> Path:
    return correlation_dir / "i18n"


def _validate_i18n_yaml(data: dict[str, Any], rule_name: str) -> dict[str, Any]:
    description = data.get("Description")
    if not isinstance(description, str) or not description.strip():
        description = f"Correlation rule {rule_name} detects suspicious activity."

    event_descriptions = data.get("EventDescriptions")
    if not isinstance(event_descriptions, list) or not event_descriptions:
        event_descriptions = [
            {
                "LocalizationId": f"corrname_{rule_name}",
                "EventDescription": f"Correlation rule {rule_name} detected suspicious activity on host {{event_src.host}}",
            }
        ]

    cleaned_items = []
    for idx, item in enumerate(event_descriptions[:2], start=1):
        if not isinstance(item, dict):
            continue

        localization_id = item.get("LocalizationId")
        event_description = item.get("EventDescription")

        if not isinstance(localization_id, str) or not localization_id.strip():
            localization_id = f"corrname_{rule_name}" if idx == 1 else f"corrname_{rule_name}_{idx}"

        if not isinstance(event_description, str) or not event_description.strip():
            event_description = f"Correlation rule {rule_name} detected suspicious activity on host {{event_src.host}}"

        cleaned_items.append(
            {
                "LocalizationId": localization_id,
                "EventDescription": event_description,
            }
        )

    if not cleaned_items:
        cleaned_items = [
            {
                "LocalizationId": f"corrname_{rule_name}",
                "EventDescription": f"Correlation rule {rule_name} detected suspicious activity on host {{event_src.host}}",
            }
        ]

    return {
        "Description": description,
        "EventDescriptions": cleaned_items,
    }


def generate_localizations(
    correlation_dir: Path,
    localization_examples: list[dict[str, Any]],
    llm: LLMClient,
) -> tuple[Path, Path]:
    answers = read_json(correlation_dir / "answers.json")
    summary = build_correlation_summary(correlation_dir)

    rule_name = correlation_dir.name
    i18n_dir = get_i18n_dir(correlation_dir)
    i18n_dir.mkdir(parents=True, exist_ok=True)

    prompt_en = build_localization_prompt(
        language="en",
        correlation_summary=summary,
        answers=answers,
        localization_examples=localization_examples,
    )
    prompt_ru = build_localization_prompt(
        language="ru",
        correlation_summary=summary,
        answers=answers,
        localization_examples=localization_examples,
    )

    yaml_en = llm.generate_yaml(prompt_en)
    yaml_ru = llm.generate_yaml(prompt_ru)

    yaml_en = _validate_i18n_yaml(yaml_en, rule_name)
    yaml_ru = _validate_i18n_yaml(yaml_ru, rule_name)

    en_path = i18n_dir / "i18n_en.yaml"
    ru_path = i18n_dir / "i18n_ru.yaml"

    write_yaml(en_path, yaml_en)
    write_yaml(ru_path, yaml_ru)

    return en_path, ru_path
