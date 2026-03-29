from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from io_utils import read_json, read_text, read_yaml


def _safe_read_json(path: Path) -> Any | None:
    try:
        return read_json(path)
    except Exception:
        return None


def _safe_read_yaml(path: Path) -> Any | None:
    try:
        return read_yaml(path)
    except Exception:
        return None


def _safe_read_text(path: Path) -> str | None:
    try:
        return read_text(path)
    except Exception:
        return None


def find_rule_dirs(macos_root: Path) -> list[Path]:
    return sorted(rule_file.parent for rule_file in macos_root.rglob("rule.co"))


def extract_importance_from_rule(rule_text: str | None) -> str | None:
    if not rule_text:
        return None
    m = re.search(r'\$importance\s*=\s*"([^"]+)"', rule_text)
    return m.group(1) if m else None


def extract_attack_from_metainfo(metainfo: dict[str, Any] | None) -> dict[str, Any]:
    result = {
        "tactic_candidates": [],
        "technique_id_candidates": [],
    }

    if not isinstance(metainfo, dict):
        return result

    attack = (
        metainfo.get("ContentRelations", {})
        .get("Implements", {})
        .get("ATTACK", {})
    )

    if not isinstance(attack, dict):
        return result

    for tactic_key, technique_ids in attack.items():
        result["tactic_candidates"].append(tactic_key)
        if isinstance(technique_ids, list):
            result["technique_id_candidates"].extend(technique_ids)

    result["tactic_candidates"] = sorted(set(result["tactic_candidates"]))
    result["technique_id_candidates"] = sorted(set(result["technique_id_candidates"]))
    return result


def load_taxonomy_fields(taxonomy_root: Path) -> dict[str, Any]:
    en = _safe_read_yaml(taxonomy_root / "taxonomy_fields" / "i18n_en.yaml")
    ru = _safe_read_yaml(taxonomy_root / "taxonomy_fields" / "i18n_ru.yaml")
    return {"en": en, "ru": ru}


def get_normalization_examples(macos_root: Path, limit_rules: int = 5, limit_pairs_per_rule: int = 2) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []

    for rule_dir in find_rule_dirs(macos_root)[:limit_rules]:
        tests_dir = rule_dir / "tests"
        norm_files = sorted(tests_dir.glob("norm_fields_*.json"))[:limit_pairs_per_rule]

        for norm_path in norm_files:
            suffix = norm_path.name.replace("norm_fields_", "")
            event_path = tests_dir / f"events_{suffix}"

            event_data = _safe_read_json(event_path)
            norm_data = _safe_read_json(norm_path)

            if event_data is None or norm_data is None:
                continue

            examples.append(
                {
                    "rule_name": rule_dir.name,
                    "category_dir": rule_dir.parent.name,
                    "event": event_data,
                    "norm_fields": norm_data,
                }
            )

    return examples


def get_classification_examples(macos_root: Path, limit_rules: int = 8) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []

    for rule_dir in find_rule_dirs(macos_root)[:limit_rules]:
        metainfo = _safe_read_yaml(rule_dir / "metainfo.yaml")
        rule_text = _safe_read_text(rule_dir / "rule.co")
        i18n_en = _safe_read_yaml(rule_dir / "i18n" / "i18n_en.yaml")

        attack = extract_attack_from_metainfo(metainfo)
        importance = extract_importance_from_rule(rule_text)

        examples.append(
            {
                "rule_name": rule_dir.name,
                "category_dir": rule_dir.parent.name,
                "importance": importance,
                "tactic_candidates": attack["tactic_candidates"],
                "technique_id_candidates": attack["technique_id_candidates"],
                "description_en": (i18n_en or {}).get("Description") if isinstance(i18n_en, dict) else None,
            }
        )

    return examples


def get_localization_examples(macos_root: Path, limit_rules: int = 4) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []

    for rule_dir in find_rule_dirs(macos_root)[:limit_rules]:
        i18n_en = _safe_read_yaml(rule_dir / "i18n" / "i18n_en.yaml")
        i18n_ru = _safe_read_yaml(rule_dir / "i18n" / "i18n_ru.yaml")

        examples.append(
            {
                "rule_name": rule_dir.name,
                "category_dir": rule_dir.parent.name,
                "i18n_en": i18n_en,
                "i18n_ru": i18n_ru,
            }
        )

    return examples
