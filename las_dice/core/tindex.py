"""PDAL tile index helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable, List, Optional

import geopandas as gpd


TINDEX_DRIVER = "GPKG"
TINDEX_LAYER = "las_tiles"
PATH_FIELD = "filepath"


class TindexError(RuntimeError):
    """Raised when tindex operations fail."""


def _pdal_command(args: List[str]) -> None:
    try:
        subprocess.run(args, check=True)
    except subprocess.CalledProcessError as exc:  # pragma: no cover - subprocess failure
        raise TindexError(f"PDAL command failed: {' '.join(args)}") from exc


def build_tindex(
    roots: Iterable[Path | str],
    output: Path | str,
    layer: str = TINDEX_LAYER,
    driver: str = TINDEX_DRIVER,
    extra_attributes: Optional[List[str]] = None,
) -> Path:
    if extra_attributes is None:
        extra_attributes = []
    root_paths = [str(Path(root).resolve()) for root in roots]
    if not root_paths:
        raise ValueError("At least one root path is required to build a tindex")
    for root in root_paths:
        if not Path(root).exists():
            raise FileNotFoundError(f"Root directory does not exist: {root}")
    output_path = Path(output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline = {
        "pipeline": [
            {
                "type": "readers.tindex",
                "roots": root_paths,
                "out_srs": "EPSG:4326",
                "gdaldriver": driver,
                "tindex_name": layer,
                "tindex": str(output_path),
                "override_srs": "",
                "filename": PATH_FIELD,
            }
        ]
    }
    if extra_attributes:
        pipeline["pipeline"][0]["extra_attributes"] = extra_attributes
    pipeline_path = output_path.with_suffix(".json")
    pipeline_path.write_text(json.dumps(pipeline, indent=2))
    _pdal_command(["pdal", "pipeline", str(pipeline_path)])
    pipeline_path.unlink(missing_ok=True)
    return output_path


def read_tindex(path: Path | str, layer: str = TINDEX_LAYER) -> gpd.GeoDataFrame:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Tindex file not found: {resolved}")
    gdf = gpd.read_file(resolved, layer=layer)
    if gdf.empty:
        raise TindexError(f"Tile index '{resolved}' contains no records")
    if PATH_FIELD not in gdf.columns:
        raise TindexError(f"Tile index missing '{PATH_FIELD}' attribute")
    return gdf


def describe_tindex(path: Path | str, layer: str = TINDEX_LAYER) -> Iterable[str]:
    gdf = read_tindex(path, layer)
    yield f"Tindex path: {Path(path).resolve()}"
    yield f"Layer: {layer}"
    yield f"Features: {len(gdf)}"
    yield f"CRS: {gdf.crs.to_string() if gdf.crs else 'None'}"
    sample = gdf[PATH_FIELD].head(5).tolist()
    yield "Sample paths:" if sample else "No sample paths available"
    for item in sample:
        yield f"  - {item}"
