"""PDAL clipping pipelines."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable, List

from geopandas import GeoSeries
from shapely import to_wkt as shapely_to_wkt

from .paths import PolygonSources


class ClippingError(RuntimeError):
    """Raised when PDAL clipping fails."""


def _ensure_output_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _geometry_to_wkt(geometry) -> str:
    try:
        return shapely_to_wkt(geometry, rounding_precision=8)
    except Exception as exc:  # pragma: no cover
        raise ClippingError("Failed to serialize polygon geometry to WKT") from exc


def _build_pipeline(
    input_files: List[Path],
    polygon_wkt: str,
    output_path: Path,
    forward_vlrs: bool = True,
) -> dict:
    readers = [
        {
            "type": "readers.las",
            "filename": str(path),
            "nosrs": "true",
        }
        for path in input_files
    ]
    filters = [
        {
            "type": "filters.crop",
            "polygon": polygon_wkt,
        }
    ]
    writer = {
        "type": "writers.las",
        "filename": str(output_path),
        "forward": "all" if forward_vlrs else "scale",
        "scale_x": 0.01,
        "scale_y": 0.01,
        "scale_z": 0.01,
    }
    return {"pipeline": readers + filters + [writer]}


def _run_pipeline(pipeline: dict) -> None:
    pipeline_json = json.dumps(pipeline)
    process = subprocess.run(
        ["pdal", "pipeline", "--stdin"],
        input=pipeline_json.encode("utf-8"),
        check=False,
        capture_output=True,
    )
    if process.returncode != 0:
        raise ClippingError(process.stderr.decode("utf-8"))


def clip_polygons(
    polygons: GeoSeries,
    polygon_records: Iterable[PolygonSources],
    output_dir: Path,
    name_builder,
    forward_vlrs: bool = True,
) -> List[Path]:
    """Clip LAS/LAZ files per polygon, returning produced output paths."""
    output_paths: List[Path] = []
    for record in polygon_records:
        if not record.source_paths:
            continue
        geometry = polygons.iloc[record.polygon_id]
        polygon_wkt = _geometry_to_wkt(geometry)
        output_path = output_dir / name_builder(record.polygon_id)
        _ensure_output_dir(output_path)
        pipeline = _build_pipeline(record.source_paths, polygon_wkt, output_path, forward_vlrs)
        _run_pipeline(pipeline)
        output_paths.append(output_path)
    return output_paths
