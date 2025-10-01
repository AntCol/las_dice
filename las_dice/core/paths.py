"""Selection helpers linking polygons to LAS sources via tindex."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import geopandas as gpd

from .crs import CRSValidationError, ensure_consistent_las_crs
from .tindex import PATH_FIELD


@dataclass
class PolygonSources:
    polygon_id: int
    source_paths: List[Path]


class SourceSelectionError(RuntimeError):
    """Raised when source selection cannot complete."""


def _ensure_crs_match(polygons: gpd.GeoDataFrame, tindex: gpd.GeoDataFrame) -> None:
    try:
        poly_crs = polygons.crs
        las_crs = ensure_consistent_las_crs([tindex.crs])
    except CRSValidationError as exc:
        raise SourceSelectionError(str(exc)) from exc
    if poly_crs is None:
        raise SourceSelectionError("Polygon CRS is undefined; cannot intersect")
    if las_crs is None:
        raise SourceSelectionError("Tile index CRS is undefined; rebuild or annotate it")
    if poly_crs.to_string() != las_crs.to_string():
        raise SourceSelectionError(
            "Polygon and tile index CRS differ; reproject polygons to match LAS CRS"
        )


def match_polygons_to_sources(
    polygons: gpd.GeoDataFrame,
    tindex: gpd.GeoDataFrame,
) -> Sequence[PolygonSources]:
    """Return a mapping of polygon index to intersecting LAS file paths."""
    if PATH_FIELD not in tindex.columns:
        raise SourceSelectionError(f"Tile index missing required column '{PATH_FIELD}'")
    _ensure_crs_match(polygons, tindex)
    intersections = gpd.overlay(polygons.reset_index(), tindex[["geometry", PATH_FIELD]], how="intersection")
    mapping: Dict[int, List[Path]] = defaultdict(list)
    for _, row in intersections.iterrows():
        polygon_idx = row["index"]
        mapping[polygon_idx].append(Path(row[PATH_FIELD]))
    results = [
        PolygonSources(polygon_id=index, source_paths=paths)
        for index, paths in mapping.items()
    ]
    return results


def match_polygons_with_empty_reports(
    polygons: gpd.GeoDataFrame,
    tindex: gpd.GeoDataFrame,
) -> Sequence[PolygonSources]:
    """Like match_polygons_to_sources, but include polygons without hits."""
    matches = match_polygons_to_sources(polygons, tindex)
    matched_ids = {entry.polygon_id for entry in matches}
    all_results = list(matches)
    for idx in polygons.reset_index()["index"]:
        if idx not in matched_ids:
            all_results.append(PolygonSources(polygon_id=idx, source_paths=[]))
    return sorted(all_results, key=lambda entry: entry.polygon_id)
