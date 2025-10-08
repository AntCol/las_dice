"""Configuration handling for LAS Dice."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_CONFIG_NAME = "las_dice_config.json"


@dataclass
class RunConfig:
    polygons: Path
    polygons_layer: Optional[str]
    las_roots: List[Path]
    tindex_path: Path
    tindex_layer: str
    output_dir: Path
    name_field: Optional[str]
    suffix: Optional[str] = None
    fast_boundary: bool = True
    overwrite: bool = False
    dry_run: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunConfig":
        return cls(
            polygons=Path(data["polygons"]),
            polygons_layer=data.get("polygons_layer"),
            las_roots=[Path(item) for item in data.get("las_roots", [])],
            tindex_path=Path(data["tindex_path"]),
            tindex_layer=data.get("tindex_layer", "las_tiles"),
            output_dir=Path(data["output_dir"]),
            name_field=data.get("name_field"),
            suffix=data.get("suffix"),
            fast_boundary=data.get("fast_boundary", True),
            overwrite=data.get("overwrite", False),
            dry_run=data.get("dry_run", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["polygons"] = str(self.polygons)
        result["las_roots"] = [str(item) for item in self.las_roots]
        result["tindex_path"] = str(self.tindex_path)
        result["output_dir"] = str(self.output_dir)
        return result


def load_config(path: Path | None = None) -> RunConfig:
    config_path = Path(path or DEFAULT_CONFIG_NAME)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return RunConfig.from_dict(raw)


def save_config(config: RunConfig, path: Path | None = None) -> Path:
    config_path = Path(path or DEFAULT_CONFIG_NAME)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as handle:
        json.dump(config.to_dict(), handle, indent=2)
    return config_path
