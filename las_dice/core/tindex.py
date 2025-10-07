"""PDAL tile index helpers.""" 

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, List

import geopandas as gpd


TINDEX_DRIVER = "GPKG"
TINDEX_LAYER = "las_tiles"
PATH_FIELD = "filepath"
_CANDIDATE_COLUMNS = ("filepath", "location", "filename", "file")
_SUPPORTED_SUFFIXES = (".las", ".laz")


class TindexError(RuntimeError):
    """Raised when tindex operations fail."""


def _pdal_command(args: List[str], stdin: bytes | None = None) -> None:
    try:
        subprocess.run(
            args,
            check=True,
            capture_output=True,
            input=stdin,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover
        stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else ""
        raise TindexError(f"PDAL command failed: {' '.join(args)}\n{stderr}") from exc


def _gather_files(roots: Iterable[Path | str]) -> List[Path]:
    files: List[Path] = []
    for root in roots:
        root_path = Path(root).resolve()
        if not root_path.exists():
            raise FileNotFoundError(f"Root directory does not exist: {root_path}")
        for suffix in _SUPPORTED_SUFFIXES:
            files.extend(root_path.rglob(f"*{suffix}"))
    unique_files = sorted({path.resolve() for path in files})
    if not unique_files:
        raise TindexError("No LAS/LAZ files found under provided roots")
    return unique_files


def build_tindex(
    roots: Iterable[Path | str],
    output: Path | str,
    layer: str = TINDEX_LAYER,
    driver: str = TINDEX_DRIVER,
    *,
    overwrite: bool = False,
    fast_boundary: bool = False,
) -> Path:
    file_paths = _gather_files(roots)
    output_path = Path(output).resolve()
    if output_path.exists() and not overwrite:
        raise TindexError(
            f"Tindex destination '{output_path}' already exists. "
            "Use a different path or enable overwrite explicitly."
        )
    if output_path.exists() and overwrite:
        output_path.unlink()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stdin_bytes = "\n".join(str(path) for path in file_paths).encode("utf-8")
    args = [
        "pdal",
        "tindex",
        "create",
        "--stdin",
        "--tindex",
        str(output_path),
        "--lyr_name",
        layer,
        "--ogrdriver",
        driver,
        "--tindex_name",
        PATH_FIELD,
        "--write_absolute_path",
    ]
    if fast_boundary:
        args.append("--fast_boundary")
    _pdal_command(args, stdin=stdin_bytes)
    return output_path


def _normalize_path_column(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    for column in _CANDIDATE_COLUMNS:
        if column in gdf.columns:
            if column != PATH_FIELD:
                gdf = gdf.rename(columns={column: PATH_FIELD})
            return gdf
    raise TindexError(
        f"Tile index missing a recognizable path column (expected one of: {', '.join(_CANDIDATE_COLUMNS)})"
    )


def read_tindex(path: Path | str, layer: str = TINDEX_LAYER) -> gpd.GeoDataFrame:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Tindex file not found: {resolved}")
    gdf = gpd.read_file(resolved, layer=layer)
    if gdf.empty:
        raise TindexError(f"Tile index '{resolved}' contains no records")
    gdf = _normalize_path_column(gdf)
    if gdf.crs is None:
        raise TindexError("Tile index CRS is undefined; rebuild with CRS information")
    return gdf


def describe_tindex(path: Path | str, layer: str = TINDEX_LAYER) -> Iterable[str]:
    gdf = read_tindex(path, layer)
    yield f"Tindex path: {Path(path).resolve()}"
    yield f"Layer: {layer}"
    yield f"Features: {len(gdf)}"
    yield f"CRS: {gdf.crs.to_string()}"
    sample = gdf[PATH_FIELD].head(5).tolist()
    yield "Sample paths:" if sample else "No sample paths available"
    for item in sample:
        yield f"  - {item}"
