"""Command-line interface for LAS Dice."""

from __future__ import annotations

from pathlib import Path

import click

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


def main() -> None:
    """Entry point for console scripts."""
    cli()


if __name__ == "__main__":
    main()
