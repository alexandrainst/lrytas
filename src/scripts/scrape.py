"""Main script.

Usage:
    uv run src/scripts/scrape.py \
        --dataset-path data/raw/dataset.jsonl \
        --max-articles 5000
"""

from pathlib import Path

import click

from lrytas import Scraper


@click.command()
@click.option(
    "--dataset-path",
    type=click.Path(path_type=Path),
    default="data/raw/dataset.jsonl",
    help="Path where the scraped dataset will be saved",
)
@click.option(
    "--max-articles", type=int, default=10, help="Maximum number of articles to scrape"
)
@click.option(
    "--headless", type=bool, default=True, help="Run the scraper in headless mode"
)
@click.option("--debug", is_flag=True, default=False, help="Enable debug mode")
def main(dataset_path: Path, max_articles: int, headless: bool, debug: bool) -> None:
    """Scrape articles from lrytas.lt website."""
    with Scraper(
        dataset_path=dataset_path,
        max_articles=max_articles,
        headless=headless,
        debug=debug,
    ) as scraper:
        scraper.scrape()


if __name__ == "__main__":
    main()
