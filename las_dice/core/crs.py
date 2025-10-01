"""Coordinate reference system helpers."""

from __future__ import annotations

from typing import Iterable, Optional

import geopandas as gpd
from pyproj import CRS


class CRSValidationError(ValueError):
    """Raised when CRS requirements are not satisfied."""


def _to_crs(crs_input: object) -> CRS:
    if crs_input is None:
        raise CRSValidationError("CRS is undefined")
    try:
        return CRS.from_user_input(crs_input)
    except Exception as exc:  # pragma: no cover - pyproj error details vary
        raise CRSValidationError(f"Invalid CRS: {crs_input}") from exc


def validate_polygon_crs(polygons: gpd.GeoDataFrame, source_hint: str | None = None) -> CRS:
    """Ensure polygon data has a defined CRS and return it as a pyproj CRS."""
    hint = f" ({source_hint})" if source_hint else ""
    if polygons.crs is None:
        raise CRSValidationError(f"Polygon data{hint} has no defined CRS")
    return _to_crs(polygons.crs)


def ensure_consistent_las_crs(crs_candidates: Iterable[object]) -> CRS:
    """Verify all LAS sources share a single CRS and return it."""
    resolved = []
    for value in crs_candidates:
        if value is None:
            raise CRSValidationError("Encountered LAS source without CRS")
        resolved.append(_to_crs(value))
    unique: set[str] = {crs.to_string() for crs in resolved}
    if not unique:
        raise CRSValidationError("No LAS CRS information was provided")
    if len(unique) > 1:
        raise CRSValidationError(
            "Mixed CRS detected across LAS sources; align inputs before clipping"
        )
    return resolved[0]


def select_output_crs(las_crs: Optional[CRS]) -> CRS:
    """Return the CRS used for outputs; currently identical to the LAS CRS."""
    if las_crs is None:
        raise CRSValidationError("LAS CRS must be known to set output CRS")
    return las_crs
