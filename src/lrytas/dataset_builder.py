"""Dataset builder."""

import logging
from pathlib import Path

import datasets
import jsonlines

logging.basicConfig(
    filename="dataset_builder.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DatasetBuilder:
    """Dataset builder.

    Attributes:
        raw_dataset_path: Path to the raw dataset.
    """

    def __init__(self, raw_dataset_path: Path) -> None:
        """Initialize dataset builder."""
        self.raw_dataset_path = raw_dataset_path

    def build_dataset(self, push_to_hub: bool = False) -> None:
        """Build dataset.

        Args:
            push_to_hub: Whether to push the dataset to the hub.
        """
        samples = self._read_raw_dataset()
        samples = self._ignore_duplicates(samples)

        if push_to_hub:
            # Create individual Dataset objects for each split
            train_dataset = datasets.Dataset.from_list(samples)
            # Create a DatasetDict with the splits
            dataset_dict = datasets.DatasetDict({"train": train_dataset})

            # Push to hub
            dataset_dict.push_to_hub("alexandrainst/lrytas-summarization", private=True)

    def _read_raw_dataset(self) -> list:
        """Read raw dataset."""
        with jsonlines.open(self.raw_dataset_path, mode="r") as reader:
            return list(reader)

    def _write_split(self, filename: str, samples: list) -> None:
        out_path = Path("data/final") / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
        with jsonlines.open(out_path, mode="w") as writer:
            writer.write_all(samples)

    def _ignore_duplicates(self, samples: list) -> list:
        """Remove duplicate samples based on title."""
        seen_titles = set()
        unique_samples = []

        for sample in samples:
            title = sample.get("title", "").strip()  # Use .get() to avoid KeyError
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_samples.append(sample)

        logger.info(
            f"Removed {len(samples) - len(unique_samples)} duplicates. "
            f"Kept {len(unique_samples)} unique samples."
        )
        return unique_samples
