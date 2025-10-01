"""Logging utilities for LAS Dice."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from rich.console import Console


console = Console()


def log_info(message: str) -> None:
    console.log(message)


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
