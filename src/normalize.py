from __future__ import annotations

from pathlib import Path
from typing import Any

from io_utils import read_json, write_json
from llm_utils import LLMClient
from prompts import build_normalization_prompt


def build_norm_path(event_path: Path) -> Path:
    return event_path.with_name(event_path.name.replace("events_", "norm_fields_"))


def stringify_values(data: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for k, v in data.items():
        if v is None:
            continue
        if isinstance(v, (dict, list)):
            continue
        result[str(k)] = str(v)
    return result


def normalize_one_event(
    event_path: Path,
    taxonomy: dict[str, Any],
    normalization_examples: list[dict[str, Any]],
    llm: LLMClient,
) -> Path:
    raw_event = read_json(event_path)

    prompt = build_normalization_prompt(
        raw_event=raw_event,
        taxonomy_fields_en=taxonomy.get("en"),
        examples=normalization_examples[:3],
    )

    norm_data = llm.generate_json(prompt)
    norm_data = stringify_values(norm_data)

    out_path = build_norm_path(event_path)
    write_json(out_path, norm_data)
    return out_path
