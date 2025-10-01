"""Command-line interface for LAS Dice."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import click

from .core import tindex
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


def main() -> None:
    """Entry point for console scripts."""
    cli()


if __name__ == "__main__":
    main()
