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
