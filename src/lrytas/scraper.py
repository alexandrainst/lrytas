"""Scrape articles from LSM.lv website."""

import logging
import random
import time
from pathlib import Path

import jsonlines
import requests
import tldextract
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from wordfreq import top_n_list

# random.seed(42)

logging.basicConfig(
    filename="scraper.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,lv;q=0.8",
    "DNT": "1",
    "Connection": "keep-alive",
}


class Scraper:
    """Scrape articles from lrytas.lt website."""

    def __init__(
        self,
        dataset_path: Path,
        max_articles: int,
        headless: bool = True,
        debug: bool = False,
    ) -> None:
        """Initialize the Scraper."""
        self.base_url = "https://www.lrytas.lt/search?q={}"

        self._setup_chrome_options(headless=headless)
        self.driver: webdriver.Chrome | None = None
        self.cookie_button_clicked = False
        self.debug = debug
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

        self.max_articles = max_articles
        self.dataset_path = dataset_path

        self.dataset_length = 0
        self.seen_urls: set[str] = set()
        self._get_dataset_info()

        self.words: list[str] = top_n_list("lt", 1000)
        random.shuffle(self.words)

    def scrape(self) -> None:
        """Scrape articles from lrytas.lt website."""
        track = self.dataset_length
        while self.dataset_length < self.max_articles:
            if self.dataset_length - track > 25:
                logger.info("Long sleep (track)")
                self._long_sleep()
                track = self.dataset_length

            query = self.words.pop()
            while not self._scrape(query=query):
                logger.info("Long sleep (query)")
                self._long_sleep()
                query = self.words.pop()

        logger.info(f"Done scraping {self.dataset_length} articles")

    def _scrape(self, query: str) -> bool:
        """Scrape articles by query.

        Returns:
            bool: True if the query was scraped successfully, False otherwise.
        """
        article_urls = self._get_article_urls(query=query)
        if not article_urls:
            return False
        for article_url in article_urls:
            if article_url in self.seen_urls:
                continue

            sample = self._get_article_data(article_url=article_url)
            if sample:
                self._save_sample(sample=sample)

        return True

    def _click_cookie_button(self) -> None:
        """Click the 'SUTINKU' button."""
        try:
            # Wait until the button is present and clickable
            button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "css-1wpnpbq"))
            )
            # Click the button
            button.click()
            logger.info("Clicked the 'SUTINKU' button")
        except Exception as e:
            logger.warning(f"An error occurred while clicking the button: {e}")

    def _get_article_urls(self, query: str) -> list[str] | str:
        """Get article URLs by query."""
        url = self.base_url.format(query)

        if self.driver is None:
            raise ValueError("Driver is not initialized")
        self.driver.get(url)
        self._short_sleep()
        if not self.cookie_button_clicked:
            self._click_cookie_button()
            self.cookie_button_clicked = True

        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        article_urls = []

        for h3 in soup.find_all("h3"):
            a_tag = h3.find("a")
            if a_tag and "href" in a_tag.attrs:
                link = a_tag.get("href")
                domain = tldextract.extract(link).domain
                if not domain == "lrytas":
                    article_url = "https://www.lrytas.lt" + link
                else:
                    article_url = link
                article_urls.append(article_url)

        return article_urls

    def _get_article_data(self, article_url: str) -> dict[str, str] | None:
        """Get article data by URL."""
        self._short_sleep()
        response = self.session.get(url=article_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        title = self._get_title(soup=soup)
        text = self._get_text(soup=soup)
        summary = self._get_summary(soup=soup)

        if not text or not summary:
            logger.warning(f"Missing text and/or summary for article: {article_url}")
            return None

        sample = {"url": article_url, "title": title, "summary": summary, "text": text}
        return sample

    def _get_title(self, soup: BeautifulSoup) -> str:
        """Get article title."""
        article_title = soup.select_one(
            "h1.text-2xl.lg\\:text-\\[34px\\].lg\\:leading-\\[46px\\].mb-4.lg\\:mb-8.text-black-custom"
        )
        if not article_title:
            return ""
        title = article_title.get_text(separator=" ", strip=True)
        return title

    def _get_summary(self, soup: BeautifulSoup) -> str:
        """Get article summary."""
        summary_div = soup.select_one("div.summary")
        if not summary_div:
            return ""
        summary = summary_div.get_text(separator=" ", strip=True)
        return summary

    def _get_text___(self, soup: BeautifulSoup) -> str:
        """Get article text."""
        article_body = soup.select_one(".article__body")

        if not article_body:
            return ""

        for unwanted in article_body.select(
            ".related-articles-inline, .swiper, .thumbnail"
        ):
            unwanted.decompose()

        text = article_body.get_text(separator=" ", strip=True)
        return text

    def _get_text(self, soup: BeautifulSoup) -> str:
        """Get full article content."""
        article_content_div = soup.select_one("div.max-w-full.article-content.w-full")
        if not article_content_div:
            return ""

        # Remove any unwanted elements if necessary
        for unwanted in article_content_div.select(
            ".related-articles-inline, .swiper, .thumbnail"
        ):
            unwanted.decompose()

        text = article_content_div.get_text(separator=" ", strip=True)
        return text

    def _save_sample(self, sample: dict[str, str]) -> None:
        """Save sample to dataset."""
        if not self.dataset_path.exists():
            self.dataset_path.touch()

        with jsonlines.open(self.dataset_path, mode="a") as writer:
            writer.write(sample)

        self.seen_urls.add(sample["url"])
        self.dataset_length += 1

        if self.dataset_length % 10 == 0:
            logger.info(
                f"Progress: {self.dataset_length}/{self.max_articles} articles scraped"
            )

    def _get_dataset_info(self) -> None:
        """Get dataset info."""
        if not self.dataset_path.exists():
            return

        with jsonlines.open(self.dataset_path, mode="r") as reader:
            for sample in reader:
                self.seen_urls.add(sample["url"])
                self.dataset_length += 1

    def _short_sleep(self) -> None:
        time.sleep(random.uniform(0.1, 0.15)) if self.debug else time.sleep(
            random.uniform(30, 60)
        )

    def _long_sleep(self) -> None:
        time.sleep(random.uniform(0.1, 0.15)) if self.debug else time.sleep(
            random.uniform(300, 420)
        )

    def _setup_chrome_options(self, headless: bool) -> None:
        """Setup Chrome options."""
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        user_agent = (
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.chrome_options.add_argument(user_agent)

    def __enter__(self) -> "Scraper":
        """Context manager entry."""
        self.driver = webdriver.Chrome(options=self.chrome_options)
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit - cleanup driver."""
        if self.driver:
            self.driver.quit()
