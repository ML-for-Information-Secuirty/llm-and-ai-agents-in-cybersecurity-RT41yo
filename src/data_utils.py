from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from typing import Iterable


def ensure_dir(path: str | Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def remove_dir(path: str | Path) -> None:
    path = Path(path)
    if path.exists() and path.is_dir():
        shutil.rmtree(path)


def unpack_zip(zip_path: str | Path, dst_dir: str | Path, wipe: bool = True) -> Path:
    zip_path = Path(zip_path)
    dst_dir = Path(dst_dir)

    if wipe and dst_dir.exists():
        shutil.rmtree(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dst_dir)

    return dst_dir


def list_relative_paths(base_dir: str | Path, max_items: int = 50) -> list[str]:
    base_dir = Path(base_dir)
    items: list[str] = []

    for p in sorted(base_dir.rglob("*")):
        items.append(str(p.relative_to(base_dir)))
        if len(items) >= max_items:
            break

    return items


def find_files_by_name(base_dir: str | Path, pattern: str) -> list[Path]:
    base_dir = Path(base_dir)
    return sorted(base_dir.rglob(pattern))


def print_tree(base_dir: str | Path, max_depth: int = 3, max_items: int = 200) -> None:
    base_dir = Path(base_dir)
    count = 0

    print(f"\n[tree] {base_dir}")
    for path in sorted(base_dir.rglob("*")):
        rel = path.relative_to(base_dir)
        depth = len(rel.parts)
        if depth > max_depth:
            continue

        indent = "  " * (depth - 1)
        suffix = "/" if path.is_dir() else ""
        print(f"{indent}{path.name}{suffix}")

        count += 1
        if count >= max_items:
            print("  ... (truncated)")
            break
