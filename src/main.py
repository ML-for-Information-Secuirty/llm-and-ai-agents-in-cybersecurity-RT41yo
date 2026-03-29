from pathlib import Path

from data_utils import unpack_zip
from llm_utils import LLMClient
from normalize import run_normalization_for_correlation
from classify import classify_correlation
from localize import generate_localizations
from pack import build_zip_from_dir
from training_data import (
    get_classification_examples,
    get_localization_examples,
    get_normalization_examples,
    load_taxonomy_fields,
)

ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = ROOT / "work"
OUTPUT_DIR = ROOT / "output"

WINDOWS_ZIP = ROOT / "windows_correlation_rules.zip"
MACOS_ZIP = ROOT / "macos_correlation_rules.zip"
TAXONOMY_ZIP = ROOT / "taxonomy_fields.zip"

WINDOWS_DIR = WORK_DIR / "windows_correlation_rules"
MACOS_DIR = WORK_DIR / "macos_correlation_rules"
TAXONOMY_DIR = WORK_DIR / "taxonomy_fields"


def list_correlation_dirs(windows_root: Path) -> list[Path]:
    return sorted(
        p for p in windows_root.glob("correlation_*")
        if p.is_dir()
    )


def main() -> None:
    unpack_zip(WINDOWS_ZIP, WINDOWS_DIR)
    unpack_zip(MACOS_ZIP, MACOS_DIR)
    unpack_zip(TAXONOMY_ZIP, TAXONOMY_DIR)

    macos_root = MACOS_DIR / "macos_correlation_rules"
    windows_root = WINDOWS_DIR / "windows_correlation_rules"
    taxonomy = load_taxonomy_fields(TAXONOMY_DIR)

    normalization_examples = get_normalization_examples(macos_root)
    classification_examples = get_classification_examples(macos_root)
    localization_examples = get_localization_examples(macos_root)

    print(f"normalization_examples: {len(normalization_examples)}")
    print(f"classification_examples: {len(classification_examples)}")
    print(f"localization_examples: {len(localization_examples)}")
    print(f"taxonomy loaded: {taxonomy['en'] is not None and taxonomy['ru'] is not None}")

    correlation_dirs = list_correlation_dirs(windows_root)
    print(f"total correlations: {len(correlation_dirs)}")

    llm = LLMClient()

    for idx, correlation_dir in enumerate(correlation_dirs, start=1):
        print(f"\n[{idx}/{len(correlation_dirs)}] Processing {correlation_dir.name}")

        created_files = run_normalization_for_correlation(
            correlation_dir=correlation_dir,
            taxonomy=taxonomy,
            normalization_examples=normalization_examples,
            llm=llm,
        )
        print(f"  norm files: {len(created_files)}")

        answers_path = classify_correlation(
            correlation_dir=correlation_dir,
            classification_examples=classification_examples,
            llm=llm,
        )
        print(f"  answers: {answers_path.name}")

        en_path, ru_path = generate_localizations(
            correlation_dir=correlation_dir,
            localization_examples=localization_examples,
            llm=llm,
        )
        print(f"  i18n: {en_path.name}, {ru_path.name}")

    out_zip = build_zip_from_dir(
        src_dir=windows_root,
        out_zip_without_suffix=OUTPUT_DIR / "windows_correlation_rules",
    )
    print(f"\nBuilt archive: {out_zip}")


if __name__ == "__main__":
    main()
