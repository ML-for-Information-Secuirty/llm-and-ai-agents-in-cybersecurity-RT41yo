from __future__ import annotations

import json
from pathlib import Path

from data_utils import find_files_by_name, print_tree, unpack_zip
from io_utils import read_json, read_text, read_yaml


ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = ROOT / "work"

WINDOWS_ZIP = ROOT / "windows_correlation_rules.zip"
MACOS_ZIP = ROOT / "macos_correlation_rules.zip"
TAXONOMY_ZIP = ROOT / "taxonomy_fields.zip"

WINDOWS_DIR = WORK_DIR / "windows_correlation_rules"
MACOS_DIR = WORK_DIR / "macos_correlation_rules"
TAXONOMY_DIR = WORK_DIR / "taxonomy_fields"


def preview_json(path: Path, max_chars: int = 2000) -> None:
    print(f"\n[json preview] {path}")
    data = read_json(path)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    print(text[:max_chars])
    if len(text) > max_chars:
        print("... [truncated]")


def preview_yaml(path: Path, max_chars: int = 2000) -> None:
    print(f"\n[yaml preview] {path}")
    data = read_yaml(path)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    print(text[:max_chars])
    if len(text) > max_chars:
        print("... [truncated]")


def preview_text(path: Path, max_chars: int = 2000) -> None:
    print(f"\n[text preview] {path}")
    text = read_text(path)
    print(text[:max_chars])
    if len(text) > max_chars:
        print("... [truncated]")


def inspect_windows() -> None:
    print("\n================ WINDOWS DATASET ================")
    print_tree(WINDOWS_DIR, max_depth=3, max_items=120)

    correlation_dirs = [p for p in sorted(WINDOWS_DIR.rglob("correlation_*")) if p.is_dir()]
    print(f"\nFound correlation dirs: {len(correlation_dirs)}")

    if correlation_dirs:
        sample_corr = correlation_dirs[0]
        print(f"\nSample correlation dir: {sample_corr}")
        print_tree(sample_corr, max_depth=3, max_items=50)

        event_files = find_files_by_name(sample_corr, "events_*.json")
        print(f"\nEvent files in sample correlation: {len(event_files)}")
        for p in event_files[:5]:
            print(" -", p.name)

        if event_files:
            preview_json(event_files[0])


def inspect_macos() -> None:
    print("\n================ MACOS DATASET ================")
    print_tree(MACOS_DIR, max_depth=3, max_items=120)

    rule_files = find_files_by_name(MACOS_DIR, "rule.co")
    answers_files = find_files_by_name(MACOS_DIR, "answers.json")
    norm_files = find_files_by_name(MACOS_DIR, "norm_fields_*.json")
    i18n_en_files = find_files_by_name(MACOS_DIR, "i18n_en.yaml")
    i18n_ru_files = find_files_by_name(MACOS_DIR, "i18n_ru.yaml")

    print(f"\nrule.co files: {len(rule_files)}")
    print(f"answers.json files: {len(answers_files)}")
    print(f"norm_fields files: {len(norm_files)}")
    print(f"i18n_en.yaml files: {len(i18n_en_files)}")
    print(f"i18n_ru.yaml files: {len(i18n_ru_files)}")

    if rule_files:
        preview_text(rule_files[0])

    if answers_files:
        preview_json(answers_files[0])

    if norm_files:
        preview_json(norm_files[0])

    if i18n_en_files:
        preview_yaml(i18n_en_files[0])

    if i18n_ru_files:
        preview_yaml(i18n_ru_files[0])


def inspect_taxonomy() -> None:
    print("\n================ TAXONOMY ================")
    print_tree(TAXONOMY_DIR, max_depth=3, max_items=80)

    yaml_files = sorted(TAXONOMY_DIR.rglob("*.yaml")) + sorted(TAXONOMY_DIR.rglob("*.yml"))
    print(f"\nTaxonomy yaml files: {len(yaml_files)}")

    for p in yaml_files[:5]:
        print(" -", p)

    if yaml_files:
        preview_yaml(yaml_files[0])


def main() -> None:
    print("[1/4] Unpacking archives...")

    if WINDOWS_ZIP.exists():
        unpack_zip(WINDOWS_ZIP, WINDOWS_DIR)
    else:
        print(f"Missing: {WINDOWS_ZIP}")

    if MACOS_ZIP.exists():
        unpack_zip(MACOS_ZIP, MACOS_DIR)
    else:
        print(f"Missing: {MACOS_ZIP}")

    if TAXONOMY_ZIP.exists():
        unpack_zip(TAXONOMY_ZIP, TAXONOMY_DIR)
    else:
        print(f"Missing: {TAXONOMY_ZIP}")

    print("[2/4] Inspecting windows dataset...")
    inspect_windows()

    print("[3/4] Inspecting macos dataset...")
    inspect_macos()

    print("[4/4] Inspecting taxonomy...")
    inspect_taxonomy()


if __name__ == "__main__":
    main()
