"""Polygon input helpers for LAS Dice."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import geopandas as gpd
from fiona import listlayers

AttributeFields = List[str]
ReadResult = Tuple[gpd.GeoDataFrame, Optional[str], int, AttributeFields]

SUPPORTED_EXTENSIONS: Tuple[str, ...] = (".gpkg", ".shp")


def list_layers(path: Path | str) -> List[str]:
    candidate = Path(path).expanduser().resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"Polygon source not found: {candidate}")
    if candidate.suffix.lower() != ".gpkg":
        raise ValueError("Layer listing is only supported for GeoPackage files")
    return listlayers(candidate)


def _normalize_path(path: Path | str) -> Path:
    candidate = Path(path).expanduser().resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"Polygon source not found: {candidate}")
    if candidate.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported polygon format '{candidate.suffix}'. "
            "Supported: .gpkg, .shp"
        )
    return candidate


def _read_file(path: Path, layer: Optional[str]) -> gpd.GeoDataFrame:
    if path.suffix.lower() == ".gpkg":
        return gpd.read_file(path, layer=layer)
    if layer is not None:
        raise ValueError("Shapefile sources do not support layer selection")
    return gpd.read_file(path)


def list_attribute_fields(gdf: gpd.GeoDataFrame) -> AttributeFields:
    geometry_name = gdf.geometry.name if gdf.geometry is not None else "geometry"
    return [name for name in gdf.columns if name != geometry_name]


def read_polygons(path: Path | str, layer: Optional[str] = None) -> ReadResult:
    normalized = _normalize_path(path)
    geodata = _read_file(normalized, layer)
    if geodata.empty:
        raise ValueError(f"Polygon source '{normalized}' contains no features")
    crs_text = geodata.crs.to_string() if geodata.crs else None
    fields = list_attribute_fields(geodata)
    return geodata, crs_text, len(geodata), fields


def describe_fields(path: Path | str, layer: Optional[str] = None) -> Iterable[str]:
    geodata, crs_text, feature_count, fields = read_polygons(path, layer)
    yield f"Path: {Path(path).resolve()}"
    if layer:
        yield f"Layer: {layer}"
    yield f"Features: {feature_count}"
    yield f"CRS: {crs_text or 'None (undefined)'}"
    if fields:
        yield "Fields:"
        for name in fields:
            yield f"  - {name}"
    else:
        yield "Fields: <none>"


