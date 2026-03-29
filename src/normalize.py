from __future__ import annotations

from pathlib import Path
from typing import Any

from io_utils import read_json, write_json
from llm_utils import LLMClient
from prompts import build_normalization_prompt


ALLOWED_EXACT_FIELDS = {
    "action",
    "msgid",
    "time",
    "event_src.host",
}

ALLOWED_PREFIXES = (
    "subject.account.",
    "subject.process.",
    "subject.process.parent.",
    "object.",
    "object.process.",
)

DROP_EXACT_FIELDS = {
    "object",
    "object.id",
    "object.state",
    "labels",
    "reason",
    "datafield1",
    "datafield2",
    "datafield3",
    "datafield4",
    "datafield5",
    "datafield6",
    "datafield7",
    "datafield8",
    "event_src.title",
    "event_src.vendor",
    "event_src.provider",
    "event_src.category",
    "event_src.id",
    "category.high",
    "category.low",
    "category.generic",
}

DROP_PREFIXES = (
    "object.value",
    "object.property",
    "object.meta",
    "object.process.meta",
)


def build_norm_path(event_path: Path) -> Path:
    return event_path.with_name(event_path.name.replace("events_", "norm_fields_"))


def _is_allowed_key(key: str) -> bool:
    if key in ALLOWED_EXACT_FIELDS:
        return True
    return key.startswith(ALLOWED_PREFIXES)


def _should_drop_key(key: str) -> bool:
    if key in DROP_EXACT_FIELDS:
        return True
    return key.startswith(DROP_PREFIXES)


def _stringify_scalar(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return None
    return str(v).strip()


def _normalize_path_fields(data: dict[str, str], fullpath_key: str, path_key: str, name_key: str) -> None:
    fullpath = data.get(fullpath_key)
    if not fullpath:
        return

    fullpath = fullpath.strip()
    sep = "\\" if "\\" in fullpath else "/"

    if not data.get(name_key):
        data[name_key] = fullpath.split(sep)[-1]

    if not data.get(path_key):
        parts = fullpath.split(sep)
        if len(parts) > 1:
            data[path_key] = sep.join(parts[:-1]) + sep


def _cleanup_account_fields(data: dict[str, str]) -> None:
    for key in ["subject.account.id", "subject.account.name", "subject.account.domain", "subject.account.session_id"]:
        if key in data and not data[key].strip():
            data.pop(key, None)

    # Делаем account.id человекочитаемым, если есть account.name
    if data.get("subject.account.name"):
        data["subject.account.id"] = data["subject.account.name"]


def _cleanup_object_type(data: dict[str, str]) -> None:
    obj_type = data.get("object.type")
    if not obj_type:
        return

    t = obj_type.strip().lower()
    mapping = {
        "file": "file",
        "process": "process",
        "registry": "registry",
        "regkey": "registry",
        "key": "registry",
        "folder": "directory",
        "directory": "directory",
    }
    data["object.type"] = mapping.get(t, t)


def _normalize_action(data: dict[str, str]) -> None:
    msgid = data.get("msgid", "").strip()
    obj_type = data.get("object.type", "").strip().lower()

    # Для Windows Security 4663 это типично access к объекту
    if msgid == "4663" and obj_type == "file":
        data["action"] = "access"


def postprocess_norm_data(raw_data: dict[str, Any]) -> dict[str, str]:
    data: dict[str, str] = {}

    for k, v in raw_data.items():
        key = str(k).strip()
        if not key:
            continue

        if _should_drop_key(key):
            continue

        if not _is_allowed_key(key):
            continue

        value = _stringify_scalar(v)
        if value is None or value == "":
            continue

        data[key] = value

    _normalize_path_fields(data, "subject.process.fullpath", "subject.process.path", "subject.process.name")
    _normalize_path_fields(data, "subject.process.parent.fullpath", "subject.process.parent.path", "subject.process.parent.name")
    _normalize_path_fields(data, "object.fullpath", "object.path", "object.name")
    _normalize_path_fields(data, "object.process.fullpath", "object.process.path", "object.process.name")

    _cleanup_object_type(data)
    _cleanup_account_fields(data)
    _normalize_action(data)

    if data.get("object.type") == "process":
        if "object.process.fullpath" in data or "object.process.name" in data:
            data.pop("object.fullpath", None)
            data.pop("object.name", None)
            data.pop("object.path", None)

    if "object.fullpath" in data:
        if data.get("object.type") in {None, "", "process"}:
            if "object.process.fullpath" not in data:
                data["object.type"] = "file"

    ordered_keys = [
        "subject.account.id",
        "subject.account.name",
        "subject.account.domain",
        "subject.account.session_id",
        "subject.process.id",
        "subject.process.name",
        "subject.process.path",
        "subject.process.fullpath",
        "subject.process.cmdline",
        "subject.process.hash",
        "subject.process.parent.id",
        "subject.process.parent.name",
        "subject.process.parent.path",
        "subject.process.parent.fullpath",
        "object.type",
        "object.name",
        "object.path",
        "object.fullpath",
        "object.hash",
        "object.process.id",
        "object.process.name",
        "object.process.path",
        "object.process.fullpath",
        "object.process.cmdline",
        "object.process.hash",
        "action",
        "msgid",
        "time",
        "event_src.host",
    ]

    result: dict[str, str] = {}
    for key in ordered_keys:
        if key in data:
            result[key] = data[key]

    for key in sorted(data.keys()):
        if key not in result:
            result[key] = data[key]

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
    norm_data = postprocess_norm_data(norm_data)

    out_path = build_norm_path(event_path)
    write_json(out_path, norm_data)
    return out_path


def run_normalization_for_correlation(
    correlation_dir: Path,
    taxonomy: dict[str, Any],
    normalization_examples: list[dict[str, Any]],
    llm: LLMClient,
) -> list[Path]:
    tests_dir = correlation_dir / "tests"
    event_files = sorted(tests_dir.glob("events_*.json"))

    created_files: list[Path] = []

    for event_path in event_files:
        print(f"  normalizing: {event_path.name}")
        out_path = normalize_one_event(
            event_path=event_path,
            taxonomy=taxonomy,
            normalization_examples=normalization_examples,
            llm=llm,
        )
        created_files.append(out_path)

    return created_files
