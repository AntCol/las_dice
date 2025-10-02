# LAS Dice

Short overview goes here.

## Getting started

1. `conda env update -n las_dice -f environment.yml`
2. `conda activate las_dice`
3. `pdal --version`
4. `python -c "import pdal, geopandas"`

## Environment notes

- Use the provided `environment.yml` with `conda-forge` to install PDAL/GDAL stack on Windows 11.
- Windows users should allow Conda to resolve `pdal`, `gdal`, and `python-pdal` from `conda-forge` to ensure binary compatibility.
- Initial solve can be slow; accept the suggested package plan and keep the `las_dice` environment isolated.
## CRS policy

- Polygon inputs must declare a CRS; undefined CRS is treated as an error.
- Output LAS/LAZ files inherit the CRS from the input LAS sources (no reprojection yet).
- Mixed CRS among LAS sources is considered a fatal error and must be resolved upstream.

## Tile index safety
- Always write the PDAL tile index to a separate GeoPackage from source polygons.
- The CLI now refuses to overwrite an existing tindex unless `--overwrite` is provided.
- Keep original polygon data read-only or under version control.
