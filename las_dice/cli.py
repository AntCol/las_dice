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


def _prompt_las_roots() -> List[Path]:
    roots: List[Path] = []
    click.echo("Enter LAS/LAZ root directories (blank to finish):")
    while True:
        value = click.prompt("Root", default="", show_default=False)
        if not value:
            break
        path = Path(value).expanduser()
        if not path.exists() or not path.is_dir():
            click.echo("  ! Directory does not exist; try again.")
            continue
        roots.append(path)
    if not roots:
        raise click.ClickException("At least one LAS root directory is required.")
    return roots


def _run_wizard(config_path: Path) -> config_io.RunConfig:
    click.echo("LAS Dice setup wizard")
    click.echo("---------------------")
    polygons_path: Path = click.prompt(
        "Polygon dataset path",
        type=click.Path(exists=True, dir_okay=False, path_type=Path),
    )
    layer_value = click.prompt(
        "Polygon layer (blank for default)", default="", show_default=False
    )
    polygons_layer = layer_value or None
    las_roots = _prompt_las_roots()
    suggested_tindex = polygons_path.parent / "las_tindex.gpkg"
    tindex_path: Path = click.prompt(
        "Tile index output path",
        default=str(suggested_tindex),
        type=click.Path(dir_okay=False, writable=True, path_type=Path),
    )
    tindex_layer = click.prompt(
        "Tile index layer name",
        default=tindex.TINDEX_LAYER,
    )
    output_dir: Path = click.prompt(
        "Output directory",
        type=click.Path(path_type=Path),
        default=str(polygons_path.parent / "clipped_outputs"),
    )
    name_field = click.prompt(
        "Polygon attribute for naming (blank for default)",
        default="",
        show_default=False,
    )
    suffix = click.prompt(
        "Optional suffix to append (blank for none)", default="", show_default=False
    )
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
        name_field=name_field or None,
        suffix=suffix or None,
        fast_boundary=fast_boundary,
    )
    saved = config_io.save_config(config, config_path)
    log_info(f"Configuration saved to {saved}")
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
    base_getter = build_name_getter(options)

    def wrapper(polygon_id: int) -> str:
        attrs = poly_gdf.iloc[polygon_id].to_dict()
        attrs.setdefault("polygon_id", polygon_id)
        return base_getter(attrs)

    return wrapper



def _plan_outputs(
    poly_gdf,
    matches: Sequence[paths.PolygonSources],
    outdir: Path,
    name_builder,
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
) -> List[dict]:
    results: List[dict] = []
    if not planned:
        return results

    with progress_tracker("Clipping polygons", total=len(planned)) as advance:
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
            )
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    for line in tindex.describe_tindex(config.tindex_path, config.tindex_layer):
        log_info(line)

    try:
        poly_gdf, _, _, _ = polygons.read_polygons(config.polygons, config.polygons_layer)
        tindex_gdf = tindex.read_tindex(config.tindex_path, config.tindex_layer)
        matches = paths.match_polygons_with_empty_reports(poly_gdf, tindex_gdf)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    name_wrapper = _build_name_wrapper(poly_gdf, config.name_field, config.suffix)
    planned, empties = _plan_outputs(poly_gdf, matches, config.output_dir, name_wrapper)

    for pid in empties:
        log_info(f"Polygon {pid}: no intersecting LAS files")

    results = _execute_clips(planned, poly_gdf, config.output_dir)
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

    results = _execute_clips(planned, poly_gdf, outdir)
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
