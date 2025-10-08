"""Logging utilities for LAS Dice."""

from __future__ import annotations

import csv
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

from rich.console import Console
from rich.progress import Progress


console = Console()


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
