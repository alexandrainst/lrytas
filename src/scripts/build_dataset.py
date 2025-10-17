"""Dataset building script.

Usage:
    uv run src/scripts/build_dataset.py --raw-dataset data/raw/dataset.jsonl \
        --push-to-hub=True
"""

from pathlib import Path

import click

from lrytas.dataset_builder import DatasetBuilder


@click.command()
@click.option(
    "--raw-dataset",
    type=click.Path(exists=True, path_type=Path),
    default="data/raw/dataset.jsonl",
    help="Path to the raw dataset file",
)
@click.option(
    "--push-to-hub", type=bool, default=False, help="Push the dataset to the hub"
)
def main(raw_dataset: Path, push_to_hub: bool) -> None:
    """Build train/val/test splits from raw dataset."""
    builder = DatasetBuilder(raw_dataset_path=raw_dataset)
    builder.build_dataset(push_to_hub=push_to_hub)


if __name__ == "__main__":
    main()
