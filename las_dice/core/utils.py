"""Utility helpers for LAS Dice."""

from __future__ import annotations

import csv
import json
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

from rich.console import Console
from rich.progress import Progress


console = Console()


@dataclass
class NamingOptions:
    field: str | None
    suffix: str | None


def sanitize(value: str, default: str = "unnamed") -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value).strip("_")
    return cleaned or default


def build_name_getter(options: NamingOptions) -> Callable[[dict], str]:
    def _getter(attributes: dict) -> str:
        base = attributes.get(options.field, "") if options.field else "polygon"
        stem = sanitize(str(base))
        if options.suffix:
            return f"{stem}_{sanitize(options.suffix)}"
        return stem

    return _getter


def build_output_path(name: str, outdir: Path, extension: str = ".las") -> Path:
    return outdir / f"{name}{extension}"


def log_info(message: str) -> None:
    console.log(message)


@contextmanager
def status(message: str):
    with console.status(message):
        yield


@contextmanager
def progress_tracker(task_description: str, total: int) -> Callable[[int], None]:
    with Progress(console=console) as progress:
        task_id = progress.add_task(task_description, total=total)

        def advance(step: int = 1) -> None:
            progress.advance(task_id, step)

        yield advance


def write_csv_log(path: Path, rows: Sequence[Mapping[str, object]], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl_log(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row))
            handle.write("\n")
