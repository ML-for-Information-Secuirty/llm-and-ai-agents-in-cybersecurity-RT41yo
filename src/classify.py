from __future__ import annotations

from pathlib import Path
from typing import Any

from io_utils import read_json, write_json
from llm_utils import LLMClient
from prompts import build_classification_prompt


TACTIC_ID_TO_NAME = {
    "credential-access": "Credential Access",
    "defense-evasion": "Defense Evasion",
    "discovery": "Discovery",
    "execution": "Execution",
    "persistence": "Persistence",
    "privilege-escalation": "Privilege Escalation",
}

TECHNIQUE_ID_TO_NAME = {
    "T1555": "Credentials from Password Stores",
    "T1555.001": "Credentials from Password Stores: Keychain",
    "T1555.003": "Credentials from Password Stores: Credentials from Web Browsers",
    "T1555.004": "Credentials from Password Stores: Windows Credential Manager",
}


def get_answers_path(correlation_dir: Path) -> Path:
    return correlation_dir / "answers.json"


def _short_event_view(norm_data: dict[str, Any]) -> dict[str, Any]:
    keep_keys = [
        "subject.account.id",
        "subject.account.name",
        "subject.account.domain",
        "subject.process.id",
        "subject.process.name",
        "subject.process.fullpath",
        "subject.process.cmdline",
        "subject.process.parent.id",
        "subject.process.parent.name",
        "subject.process.parent.fullpath",
        "object.type",
        "object.name",
        "object.path",
        "object.fullpath",
        "object.process.id",
        "object.process.name",
        "object.process.fullpath",
        "object.process.cmdline",
        "action",
        "msgid",
        "time",
        "event_src.host",
    ]
    return {k: norm_data[k] for k in keep_keys if k in norm_data}


def build_correlation_summary(correlation_dir: Path) -> dict[str, Any]:
    tests_dir = correlation_dir / "tests"
    norm_files = sorted(tests_dir.glob("norm_fields_*.json"))

    event_summaries = []
    users = set()
    process_names = set()
    file_paths = set()
    file_names = set()
    object_process_names = set()
    actions = set()
    hosts = set()
    msgids = set()

    for norm_path in norm_files:
        data = read_json(norm_path)
        event_summaries.append(
            {
                "file": norm_path.name,
                "fields": _short_event_view(data),
            }
        )

        for key in ["subject.account.id", "subject.account.name"]:
            if data.get(key):
                users.add(data[key])

        if data.get("subject.process.name"):
            process_names.add(data["subject.process.name"])

        if data.get("object.process.name"):
            object_process_names.add(data["object.process.name"])

        if data.get("object.fullpath"):
            file_paths.add(data["object.fullpath"])

        if data.get("object.name"):
            file_names.add(data["object.name"])

        if data.get("action"):
            actions.add(data["action"])

        if data.get("event_src.host"):
            hosts.add(data["event_src.host"])

        if data.get("msgid"):
            msgids.add(data["msgid"])

    lower_paths = [p.lower() for p in file_paths]
    lower_names = [n.lower() for n in file_names]

    hints = {
        "browser_password_store_access": any(
            x.endswith("key4.db") or x.endswith("logins.json") or x.endswith("login data")
            for x in lower_paths + lower_names
        ),
        "possible_windows_credential_manager": any(
            "credential" in x and "vault" in x for x in lower_paths + lower_names
        ),
    }

    return {
        "correlation": correlation_dir.name,
        "num_events": len(norm_files),
        "users": sorted(users),
        "subject_process_names": sorted(process_names),
        "object_process_names": sorted(object_process_names),
        "object_file_paths": sorted(file_paths),
        "object_file_names": sorted(file_names),
        "actions": sorted(actions),
        "msgids": sorted(msgids),
        "hosts": sorted(hosts),
        "hints": hints,
        "events": event_summaries,
    }


def _normalize_tactic_name(value: str) -> str:
    v = value.strip()
    return TACTIC_ID_TO_NAME.get(v, v)


def _normalize_technique_name(value: str) -> str:
    v = value.strip()
    return TECHNIQUE_ID_TO_NAME.get(v, v)


def _fallback_answers_from_summary(summary: dict[str, Any]) -> dict[str, str]:
    hints = summary.get("hints", {}) or {}

    if hints.get("browser_password_store_access"):
        return {
            "tactic": "Credential Access",
            "technique": "Credentials from Password Stores: Credentials from Web Browsers",
            "importance": "high",
        }

    if hints.get("possible_windows_credential_manager"):
        return {
            "tactic": "Credential Access",
            "technique": "Credentials from Password Stores: Windows Credential Manager",
            "importance": "high",
        }

    return {
        "tactic": "Credential Access",
        "technique": "Credentials from Password Stores",
        "importance": "medium",
    }


def _validate_answers(data: dict[str, Any], summary: dict[str, Any]) -> dict[str, str]:
    fallback = _fallback_answers_from_summary(summary)

    tactic = _normalize_tactic_name(str(data.get("tactic", "")).strip())
    technique = _normalize_technique_name(str(data.get("technique", "")).strip())
    importance = str(data.get("importance", "")).strip().lower()

    if importance not in {"low", "medium", "high"}:
        importance = fallback["importance"]

    if not tactic:
        tactic = fallback["tactic"]

    if not technique:
        technique = fallback["technique"]

    return {
        "tactic": tactic,
        "technique": technique,
        "importance": importance,
    }


def classify_correlation(
    correlation_dir: Path,
    classification_examples: list[dict[str, Any]],
    llm: LLMClient,
) -> Path:
    summary = build_correlation_summary(correlation_dir)

    prompt = build_classification_prompt(
        correlation_summary=summary,
        classification_examples=classification_examples,
    )

    raw_answer = llm.generate_json(prompt)
    answers = _validate_answers(raw_answer, summary)

    out_path = get_answers_path(correlation_dir)
    write_json(out_path, answers)
    return out_path
