from pathlib import Path

from data_utils import unpack_zip
from llm_utils import LLMClient
from normalize import normalize_one_event
from training_data import (
    get_classification_examples,
    get_localization_examples,
    get_normalization_examples,
    load_taxonomy_fields,
)

ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = ROOT / "work"

WINDOWS_ZIP = ROOT / "windows_correlation_rules.zip"
MACOS_ZIP = ROOT / "macos_correlation_rules.zip"
TAXONOMY_ZIP = ROOT / "taxonomy_fields.zip"

WINDOWS_DIR = WORK_DIR / "windows_correlation_rules"
MACOS_DIR = WORK_DIR / "macos_correlation_rules"
TAXONOMY_DIR = WORK_DIR / "taxonomy_fields"


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

    sample_event = windows_root / "correlation_1" / "tests" / "events_1_1.json"
    print(f"\nNormalizing sample event: {sample_event}")

    llm = LLMClient()
    out_path = normalize_one_event(
        event_path=sample_event,
        taxonomy=taxonomy,
        normalization_examples=normalization_examples,
        llm=llm,
    )

    print(f"Saved normalized file to: {out_path}")


if __name__ == "__main__":
    main()
