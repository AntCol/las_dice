"""Command-line interface for LAS Dice."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import click

from .core import clipper, paths, tindex
from .core.utils import (
    NamingOptions,
    build_name_getter,
    build_output_path,
    log_info,
    progress_tracker,
    status,
)
from .io import config as config_io
from .io import polygons


def _clean_path(value: str) -> Path:
    """Trim surrounding quotes/whitespace and expanduser."""
    return Path(value.strip(" '\"")).expanduser()

@click.group()
def cli() -> None:
    """Manage LAS Dice operations."""


@cli.command(name="list-fields")
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--layer", help="Layer name for GeoPackage sources.")
def list_fields(source: Path, layer: str | None) -> None:
    """List attribute fields available in a polygon dataset."""
    try:
        for line in polygons.describe_fields(source, layer):
            click.echo(line)
    except Exception as exc:  # pragma: no cover
        raise click.ClickException(str(exc)) from exc


def _prompt_las_root() -> Path:
    value = click.prompt("LAS/LAZ root directory")
    path = _clean_path(value)
    if not path.exists() or not path.is_dir():
        raise click.ClickException(f"LAS root directory not found: {path}")
    return path


def _run_wizard(config_path: Path) -> config_io.RunConfig:
    click.echo("LAS Dice setup wizard")
    click.echo("---------------------")
    polygons_input = click.prompt("Polygon dataset path")
    polygons_path = _clean_path(polygons_input)
    if not polygons_path.exists() or not polygons_path.is_file():
        raise click.ClickException(f"Polygon dataset not found: {polygons_path}")

    polygons_layer: Optional[str] = None
    layers: List[str] = []
    if polygons_path.suffix.lower() == ".gpkg":
        try:
            layers = polygons.list_layers(polygons_path)
        except Exception as exc:
            log_info(f"Failed to list GPKG layers: {exc}")
    if layers:
        click.echo("Available layers:")
        for idx, layer_name in enumerate(layers, start=1):
            click.echo(f"  [{idx}] {layer_name}")
        layer_index = click.prompt("Select layer number", type=int, default=1)
        if layer_index < 1 or layer_index > len(layers):
            raise click.ClickException("Layer selection out of range")
        polygons_layer = layers[layer_index - 1]
    elif polygons_path.suffix.lower() == ".gpkg":
        layer_value = click.prompt(
            "Polygon layer name (blank for none)", default="", show_default=False
        )
        polygons_layer = layer_value or None

    try:
        preview_gdf, _, _, fields = polygons.read_polygons(
            polygons_path, polygons_layer
        )
    except Exception as exc:
        raise click.ClickException(f"Failed to read polygons: {exc}")

    polygon_crs = (
        preview_gdf.crs.to_string() if preview_gdf.crs is not None else None
    )
    if polygon_crs is None:
        raise click.ClickException("Polygon dataset has no defined CRS.")

    if fields:
        click.echo("Available fields:")
        for idx, field_name in enumerate(fields, start=1):
            click.echo(f"  [{idx}] {field_name}")
    else:
        click.echo("No non-geometry fields detected.")

    if fields:
        field_index = click.prompt(
            "Select field number for naming", type=int, default=1
        )
        if field_index < 1 or field_index > len(fields):
            raise click.ClickException("Naming field selection out of range")
        name_field = fields[field_index - 1]
    else:
        name_field = None

    las_root = _prompt_las_root()
    las_roots = [las_root]

    suggested_tindex = polygons_path.parent / "las_tindex.gpkg"

    tindex_input = click.prompt("Tile index output path", default=str(suggested_tindex))
    tindex_path = _clean_path(tindex_input)
    if tindex_path.exists() and tindex_path.is_dir():
        tindex_path = tindex_path / suggested_tindex.name
    if tindex_path.suffix.lower() not in {".gpkg", ".shp"}:
        tindex_path = tindex_path.with_suffix(".gpkg")
    tindex_layer = click.prompt(
        "Tile index layer name", default=tindex.TINDEX_LAYER
    )

    output_input = click.prompt(
        "Output directory", default=str(polygons_path.parent / "clipped_outputs")
    )
    output_dir = _clean_path(output_input)
    output_dir.mkdir(parents=True, exist_ok=True)

    suffix_value = click.prompt(
        "Optional suffix to append (blank for none)", default="", show_default=False
    )
    suffix = suffix_value or None

    fast_boundary = click.confirm(
        "Use fast boundary (recommended for large datasets)?", default=True
    )

    config = config_io.RunConfig(
        polygons=polygons_path,
        polygons_layer=polygons_layer,
        las_roots=las_roots,
        tindex_path=tindex_path,
        tindex_layer=tindex_layer,
        output_dir=output_dir,
        name_field=name_field,
        suffix=suffix,
        fast_boundary=fast_boundary,
        target_srs=polygon_crs,
    )
    config_io.save_config(config, config_path)
    return config


def _summarise_results(results: List[dict]) -> None:
    written = len([row for row in results if row["status"] == "written"])
    skipped = len([row for row in results if row["status"] == "exists"])
    errors = [row for row in results if row["status"] == "error"]
    log_info(
        f"Run summary: {written} written, {skipped} skipped (already existed), {len(errors)} errors"
    )
    if errors:
        log_info("Errored polygons:")
        for row in errors:
            log_info(f"  Polygon {row['polygon_id']} -> {row['output']}: {row['error']}")


def _build_name_wrapper(poly_gdf, name_field: Optional[str], suffix: Optional[str]):
    options = NamingOptions(field=name_field, suffix=suffix)
    getter = build_name_getter(options)

    def wrapper(polygon_id: int) -> str:
        attrs = poly_gdf.iloc[polygon_id].to_dict()
        attrs.setdefault("polygon_id", polygon_id)
        return getter(attrs)

    return wrapper


def _plan_outputs(
    poly_gdf, matches: Sequence[paths.PolygonSources], outdir: Path, name_builder
) -> Tuple[List[Tuple[paths.PolygonSources, Path]], List[int]]:
    planned: List[Tuple[paths.PolygonSources, Path]] = []
    empties: List[int] = []
    for record in matches:
        if not record.source_paths:
            empties.append(record.polygon_id)
            continue
        name = name_builder(record.polygon_id)
        output_path = build_output_path(name, outdir)
        planned.append((record, output_path))
    return planned, empties


def _execute_clips(
    planned: Sequence[Tuple[paths.PolygonSources, Path]],
    poly_gdf,
    outdir: Path,
    output_srs: Optional[str],
) -> List[dict]:
    results: List[dict] = []
    if not planned:
        return results

    with progress_tracker("Clipping LAS", total=len(planned)) as advance:
        for record, output_path in planned:
            if output_path.exists():
                log_info(
                    f"Polygon {record.polygon_id}: output exists ({output_path}); skipping"
                )
                results.append(
                    {
                        "polygon_id": record.polygon_id,
                        "output": str(output_path),
                        "sources": len(record.source_paths),
                        "status": "exists",
                    }
                )
                advance()
                continue
            try:
                clipper.clip_polygons(
                    polygons=poly_gdf.geometry,
                    polygon_records=[record],
                    output_dir=outdir,
                    name_builder=lambda _: output_path.name,
                    output_srs=output_srs,
                )
            except Exception as exc:  # pragma: no cover
                log_info(f"Polygon {record.polygon_id}: ERROR {exc}")
                results.append(
                    {
                        "polygon_id": record.polygon_id,
                        "output": str(output_path),
                        "sources": len(record.source_paths),
                        "status": "error",
                        "error": str(exc),
                    }
                )
                advance()
                continue
            log_info(
                f"Polygon {record.polygon_id}: wrote {output_path} from {len(record.source_paths)} sources"
            )
            results.append(
                {
                    "polygon_id": record.polygon_id,
                    "output": str(output_path),
                    "sources": len(record.source_paths),
                    "status": "written",
                }
            )
            advance()
    return results

def run_workflow(config_path: Path) -> None:
    """Run the full LAS Dice workflow after collecting configuration interactively."""
    config = _run_wizard(config_path)

    log_info("Starting LAS Dice workflow")
    try:
        with status("Building tile index..."):
            tindex.build_tindex(
                config.las_roots,
                config.tindex_path,
                config.tindex_layer,
                tindex.TINDEX_DRIVER,
                overwrite=True,
                fast_boundary=config.fast_boundary,
                target_srs=config.target_srs,
            )
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    for line in tindex.describe_tindex(config.tindex_path, config.tindex_layer):
        log_info(line)

    try:
        poly_gdf, _, _, fields = polygons.read_polygons(config.polygons, config.polygons_layer)
        tindex_gdf = tindex.read_tindex(config.tindex_path, config.tindex_layer)
        matches = paths.match_polygons_with_empty_reports(poly_gdf, tindex_gdf)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    name_wrapper = _build_name_wrapper(poly_gdf, config.name_field, config.suffix)
    planned, empties = _plan_outputs(poly_gdf, matches, config.output_dir, name_wrapper)

    for pid in empties:
        log_info(f"Polygon {pid}: no intersecting LAS files")

    results = _execute_clips(planned, poly_gdf, config.output_dir, output_srs=config.target_srs)
    _summarise_results(results)
    config_io.save_config(config, config_path)
    log_info("Workflow completed")


@cli.command(name="init")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=config_io.DEFAULT_CONFIG_NAME,
    help="Configuration file to save.",
)
def init_cmd(config_path: Path) -> None:
    """Interactive wizard to capture project configuration."""
    _run_wizard(config_path)


@cli.command(name="build-tindex")
@click.argument("roots", nargs=-1, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--output", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--layer", default=tindex.TINDEX_LAYER, show_default=True)
@click.option("--driver", default=tindex.TINDEX_DRIVER, show_default=True)
@click.option("--overwrite", is_flag=True, help="Allow overwriting an existing tindex file.")
@click.option("--fast-boundary", is_flag=True, help="Use PDAL fast boundary (bbox) instead of convex hull.")
def build_tindex_cmd(
    roots: Tuple[Path, ...],
    output: Path,
    layer: str,
    driver: str,
    overwrite: bool,
    fast_boundary: bool,
) -> None:
    """Build a PDAL tile index from LAS/LAZ roots."""
    if not roots:
        raise click.UsageError("Provide at least one root directory")
    if output.exists() and not overwrite:
        raise click.ClickException(
            "Tindex destination already exists. Use --overwrite or choose a new file."
        )
    if output.exists() and overwrite:
        log_info(f"Overwriting existing tindex: {output}")
    try:
        with status("Building tile index..."):
            result = tindex.build_tindex(
                roots, output, layer, driver, overwrite=overwrite, fast_boundary=fast_boundary
            )
    except Exception as exc:  # pragma: no cover
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Tile index written to {result}")


@cli.command(name="validate-tindex")
@click.argument("tindex_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--layer", default=tindex.TINDEX_LAYER, show_default=True)
def validate_tindex_cmd(tindex_path: Path, layer: str) -> None:
    """Report summary details for an existing tile index."""
    try:
        for line in tindex.describe_tindex(tindex_path, layer):
            click.echo(line)
    except Exception as exc:  # pragma: no cover
        raise click.ClickException(str(exc)) from exc


@cli.command(name="clip")
@click.option("--polygons", "polygons_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--layer", help="Layer name for GeoPackage polygon source.")
@click.option("--name-field", help="Polygon attribute to use for output naming.")
@click.option("--tindex", "tindex_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--tindex-layer", default=tindex.TINDEX_LAYER, show_default=True)
@click.option("--outdir", required=True, type=click.Path(file_okay=False, path_type=Path))
@click.option("--suffix", help="Optional suffix for output names.")
def clip_cmd(
    polygons_path: Path,
    layer: Optional[str],
    name_field: Optional[str],
    tindex_path: Path,
    tindex_layer: str,
    outdir: Path,
    suffix: Optional[str],
) -> None:
    try:
        poly_gdf, _, _, _ = polygons.read_polygons(polygons_path, layer)
        tindex_gdf = tindex.read_tindex(tindex_path, tindex_layer)
        matches = paths.match_polygons_with_empty_reports(poly_gdf, tindex_gdf)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    name_wrapper = _build_name_wrapper(poly_gdf, name_field, suffix)
    planned, empties = _plan_outputs(poly_gdf, matches, outdir, name_wrapper)

    for pid in empties:
        log_info(f"Polygon {pid}: no intersecting LAS files")

    results = _execute_clips(planned, poly_gdf, outdir, output_srs=poly_crs)
    _summarise_results(results)


@cli.command(name="run")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=config_io.DEFAULT_CONFIG_NAME,
    help="Configuration file to save.",
)
def run_cmd(config_path: Path) -> None:
    """Execute full workflow using a fresh configuration."""
    run_workflow(config_path)


def main() -> None:
    """Entry point for console scripts."""
    cli()


if __name__ == "__main__":
    main()









