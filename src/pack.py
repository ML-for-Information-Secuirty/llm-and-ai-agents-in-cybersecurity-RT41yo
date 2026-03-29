from __future__ import annotations

import shutil
from pathlib import Path


def build_zip_from_dir(src_dir: Path, out_zip_without_suffix: Path) -> Path:
    out_zip_without_suffix.parent.mkdir(parents=True, exist_ok=True)
    zip_path = shutil.make_archive(
        base_name=str(out_zip_without_suffix),
        format="zip",
        root_dir=str(src_dir.parent),
        base_dir=src_dir.name,
    )
    return Path(zip_path)
