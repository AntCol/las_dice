# LAS Dice

LAS Dice clips large LAS/LAZ collections against polygon footprints using PDAL. The CLI focuses on Windows-first workflows but keeps outputs portable.

## Quick start
1. `conda env update -n las_dice -f environment.yml`
2. `conda activate las_dice`
3. `pdal --version`
4. `python -c "import pdal, geopandas"`

## Guided workflow
- `python las_dice.py` launches the interactive wizard, saves a fresh configuration (JSON), builds the PDAL tile index with fast boundaries, validates it, and clips polygons with progress updates. Outputs that already exist are skipped automatically.
- `python -m las_dice.cli run --config my_project.json` does the same but lets you pick a custom config path.
- `python -m las_dice.cli init` runs only the wizard, saving inputs for later.

## Advanced commands
- `python -m las_dice.cli build-tindex ... --fast-boundary` builds the PDAL tile index directly.
- `python -m las_dice.cli validate-tindex ...` prints tile index metadata.
- `python -m las_dice.cli clip ...` clips against custom inputs.

## Environment notes
- Use the provided `environment.yml` with `conda-forge` to install PDAL/GDAL stack on Windows 11.
- PDAL tile indexing is fastest with `--fast-boundary`, which the guided workflow uses automatically.
- Windows users should allow Conda to resolve `pdal`, `gdal`, and `python-pdal` from `conda-forge` to ensure binary compatibility.

## CRS policy
- Polygon inputs must declare a CRS; undefined CRS is treated as an error.
- Output LAS/LAZ inherit the CRS from the input LAS sources (no reprojection yet).
- Mixed CRS among LAS sources is considered a fatal error and must be resolved upstream.

## Tile index safety
- Always write the PDAL tile index to a separate GeoPackage from source polygons.
- The CLI refuses to overwrite an existing tindex unless `--overwrite` is provided (the guided workflow overwrites intentionally to refresh the index).
- Keep original polygon data read-only or under version control.
