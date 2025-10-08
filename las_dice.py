"""Direct entry point for LAS Dice workflow."""

from pathlib import Path

from las_dice.cli import run_workflow
from las_dice.io.config import DEFAULT_CONFIG_NAME


if __name__ == "__main__":
    run_workflow(Path(DEFAULT_CONFIG_NAME))
