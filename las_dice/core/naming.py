"""Output naming helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable


INVALID_CHARS = re.compile(r"[^A-Za-z0-9_-]+")


def sanitize(value: str, default: str = "unnamed") -> str:
    cleaned = INVALID_CHARS.sub("_", value).strip("_")
    return cleaned or default


def build_name_getter(field: str | None, suffix: str | None = None) -> Callable[[dict], str]:
    def _getter(attributes: dict) -> str:
        base = attributes.get(field, "") if field else "polygon"
        stem = sanitize(str(base))
        if suffix:
            return f"{stem}_{sanitize(suffix)}"
        return stem

    return _getter


def build_output_path(name: str, outdir: Path, extension: str = ".las") -> Path:
    return outdir / f"{name}{extension}"
