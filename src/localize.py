from __future__ import annotations

from pathlib import Path
from typing import Any

from io_utils import read_json, write_yaml
from llm_utils import LLMClient
from prompts import build_localization_prompt
from classify import build_correlation_summary


def get_i18n_dir(correlation_dir: Path) -> Path:
    return correlation_dir / "i18n"


def _fallback_event_description(language: str, rule_name: str, variant: int) -> str:
    if language == "en":
        if variant == 1:
            return (
                "Process {subject.process.name} accessed browser credential files "
                "under account {subject.account.id} on host {event_src.host}"
            )
        return (
            "Suspicious access to browser password store files was detected on host {event_src.host}"
        )

    if variant == 1:
        return (
            "Процесс {subject.process.name} получил доступ к файлам хранилища паролей браузера "
            "от имени учетной записи {subject.account.id} на узле {event_src.host}"
        )
    return (
        "Обнаружен подозрительный доступ к файлам хранилища паролей браузера на узле {event_src.host}"
    )


def _fallback_description(language: str, rule_name: str) -> str:
    if language == "en":
        return "The rule detects suspicious access to browser password store files."
    return "Правило обнаруживает подозрительный доступ к файлам хранилища паролей браузера."


def _validate_i18n_yaml(data: dict[str, Any], rule_name: str, language: str) -> dict[str, Any]:
    description = data.get("Description")
    if not isinstance(description, str) or not description.strip():
        description = _fallback_description(language, rule_name)

    raw_items = data.get("EventDescriptions")
    if not isinstance(raw_items, list):
        raw_items = []

    cleaned_items = []
    for idx, item in enumerate(raw_items[:2], start=1):
        if not isinstance(item, dict):
            continue

        localization_id = f"corrname_{rule_name}" if idx == 1 else f"corrname_{rule_name}_{idx}"
        event_description = item.get("EventDescription")

        if not isinstance(event_description, str) or not event_description.strip():
            event_description = _fallback_event_description(language, rule_name, idx)

        cleaned_items.append(
            {
                "LocalizationId": localization_id,
                "EventDescription": event_description,
            }
        )

    while len(cleaned_items) < 2:
        idx = len(cleaned_items) + 1
        localization_id = f"corrname_{rule_name}" if idx == 1 else f"corrname_{rule_name}_{idx}"
        cleaned_items.append(
            {
                "LocalizationId": localization_id,
                "EventDescription": _fallback_event_description(language, rule_name, idx),
            }
        )

    return {
        "Description": description,
        "EventDescriptions": cleaned_items[:2],
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

    yaml_en = _validate_i18n_yaml(yaml_en, rule_name, "en")
    yaml_ru = _validate_i18n_yaml(yaml_ru, rule_name, "ru")

    en_path = i18n_dir / "i18n_en.yaml"
    ru_path = i18n_dir / "i18n_ru.yaml"

    write_yaml(en_path, yaml_en)
    write_yaml(ru_path, yaml_ru)

    return en_path, ru_path
