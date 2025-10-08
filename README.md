# LAS Dice

LAS Dice clips large LAS/LAZ collections against polygon footprints using PDAL. The CLI focuses on Windows-first workflows but keeps outputs portable.

## Quick start
1. `conda env update -n las_dice -f environment.yml`
2. `conda activate las_dice`
3. `pdal --version`
4. `python -c "import pdal, geopandas"`

## Guided workflow
- `python -m las_dice.cli init` walks through the required inputs (polygon data, LAS roots, output directory, etc.) and saves them into `las_dice_config.json`.
- `python -m las_dice.cli run` uses the saved configuration to build a tile index (with PDAL `--fast_boundary` by default), validates it, runs a dry-run preview if configured, and clips polygons with rich progress updates.
- Re-run `python -m las_dice.cli run --execute` at any time; existing outputs are skipped unless `--overwrite` is provided.

## Advanced commands
- `python -m las_dice.cli build-tindex ... --fast-boundary` builds the PDAL tile index directly.
- `python -m las_dice.cli validate-tindex ...` prints tindex metadata, CRS, and sample paths.
- `python -m las_dice.cli clip ...` runs the clipper manually for advanced use cases.

## Environment notes
- Use the provided `environment.yml` with `conda-forge` to install PDAL/GDAL stack on Windows 11.
- PDAL tile indexing is fastest with `--fast-boundary`, which the `run` workflow uses automatically.
- Windows users should allow Conda to resolve `pdal`, `gdal`, and `python-pdal` from `conda-forge` to ensure binary compatibility.

## CRS policy
- Polygon inputs must declare a CRS; undefined CRS is treated as an error.
- Output LAS/LAZ inherit the CRS from the input LAS sources (no reprojection yet).
- Mixed CRS among LAS sources is considered a fatal error and must be resolved upstream.

## Tile index safety
- Always write the PDAL tile index to a separate GeoPackage from source polygons.
- The CLI refuses to overwrite an existing tindex unless `--overwrite` is provided.
- Keep original polygon data read-only or under version control.

