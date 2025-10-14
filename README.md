# LAS Dice

LAS Dice clips large LAS/LAZ collections against polygon footprints using PDAL. It bridges gaps between misaligned LAS tiles and polygon requests while keeping outputs portable.

## Quick start
1. `conda env update -n las_dice -f environment.yml`
2. `conda activate las_dice`
3. `pdal --version`
4. `python -c "import pdal, geopandas"`

## Guided workflow
Run `python las_dice.py`. The wizard will:
- Ask for the polygon GeoPackage and list its layers; pick by number.
- Read the layer, list its attribute fields (numbered), and prompt for the naming field.
- Ask for the LAS/LAZ root directory.
- Ask where to write the tile index (directory or filename) and the layer name; index is built in the polygon CRS.
- Ask for the output directory and optional naming suffix.
- Confirm fast-boundary usage (defaults to yes).
- Build the tindex, validate, and clip polygons, showing a “Clipping LAS” progress bar. Existing outputs are skipped automatically. Clipped LAS inherit the source CRS.

The wizard writes a fresh `las_dice_config.json` each run; use `python -m las_dice.cli run --config my_project.json` if you need multiple configs.

## Advanced commands
- `python -m las_dice.cli init --config my_project.json` just captures inputs.
- `python -m las_dice.cli build-tindex <root> ... --output <file> --fast-boundary` builds a tile index directly.
- `python -m las_dice.cli validate-tindex <file>` prints index metadata.
- `python -m las_dice.cli clip ...` runs clipping with custom paths/params.

## Environment notes
- Use `environment.yml` via conda-forge on Windows 11 for PDAL/GDAL compatibility.
- Fast boundary mode (bounding boxes) is the default and recommended for large datasets.

## CRS policy
- Polygons must declare a CRS; the wizard enforces this.
- Tile index and clipped LAS/LAZ inherit the polygon CRS automatically.
- Mixed CRS among LAS sources must be fixed upstream; the run fails fast if encountered.

## Tile index safety
- Tile index is written alongside source data in a separate GeoPackage; the wizard overwrites intentionally for repeat runs.
- Keep original polygon data versioned or read-only to avoid accidental modifications.
