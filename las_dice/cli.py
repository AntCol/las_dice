"""Command-line interface for LAS Dice."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import click

from .core import clipper, logging_utils, naming, paths, tindex
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


@cli.command(name="build-tindex")
@click.argument("roots", nargs=-1, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--output", required=True, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--layer", default=tindex.TINDEX_LAYER, show_default=True)
@click.option("--driver", default=tindex.TINDEX_DRIVER, show_default=True)
def build_tindex_cmd(
    roots: Tuple[Path, ...],
    output: Path,
    layer: str,
    driver: str,
) -> None:
    """Build a PDAL tile index from LAS/LAZ roots."""
    if not roots:
        raise click.UsageError("Provide at least one root directory")
    try:
        result = tindex.build_tindex(roots, output, layer, driver)
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
@click.option("--polygons", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--layer", help="Layer name for GeoPackage polygon source.")
@click.option("--name-field", help="Polygon attribute to use for output naming.")
@click.option("--tindex", "tindex_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--tindex-layer", default=tindex.TINDEX_LAYER, show_default=True)
@click.option("--outdir", required=True, type=click.Path(file_okay=False, path_type=Path))
@click.option("--suffix", help="Optional suffix for output names.")
@click.option("--dry-run", is_flag=True, help="Plan without running PDAL.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing outputs.")
def clip_cmd(
    polygons_path: Path,
    layer: Optional[str],
    name_field: Optional[str],
    tindex_path: Path,
    tindex_layer: str,
    outdir: Path,
    suffix: Optional[str],
    dry_run: bool,
    overwrite: bool,
) -> None:
    try:
        poly_gdf, _, _, _ = polygons.read_polygons(polygons_path, layer)
        tindex_gdf = tindex.read_tindex(tindex_path, tindex_layer)
        matches = paths.match_polygons_with_empty_reports(poly_gdf, tindex_gdf)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    name_getter = naming.build_name_getter(name_field, suffix)

    def make_output_name(polygon_id: int) -> str:
        attrs = poly_gdf.iloc[polygon_id].to_dict()
        attrs.setdefault("polygon_id", polygon_id)
        return name_getter(attrs)

    planned_outputs = []
    for record in matches:
        name = make_output_name(record.polygon_id)
        output_path = naming.build_output_path(name, outdir)
        planned_outputs.append((record, output_path))

    if dry_run:
        for record, output_path in planned_outputs:
            logging_utils.log_info(
                f"Polygon {record.polygon_id}: {len(record.source_paths)} sources -> {output_path}"
            )
        return

    produced = []
    for record, output_path in planned_outputs:
        if output_path.exists() and not overwrite:
            raise click.ClickException(
                f"Output exists: {output_path}. Use --overwrite to replace it."
            )
        if not record.source_paths:
            logging_utils.log_info(
                f"Polygon {record.polygon_id}: no intersecting LAS files; skipping"
            )
            continue
        try:
            clipper.clip_polygons(
                polygons=poly_gdf.geometry,
                polygon_records=[record],
                output_dir=outdir,
                name_builder=lambda _: output_path.name,
            )
        except Exception as exc:  # pragma: no cover
            raise click.ClickException(str(exc)) from exc
        produced.append(output_path)
        logging_utils.log_info(
            f"Polygon {record.polygon_id}: wrote {output_path} from {len(record.source_paths)} sources"
        )

    logging_utils.log_info(f"Completed clipping {len(produced)} polygon(s)")


def main() -> None:
    """Entry point for console scripts."""
    cli()


if __name__ == "__main__":
    main()
