"""Scraper for https://books.toscrape.com/ — book listings with dynamic pagination."""

import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

SOURCE_NAME = "Books to Scrape"
DEFAULT_START_URL = "https://books.toscrape.com/catalogue/page-1.html"

_WORD_TO_IGNORE = {"star-rating"}


class BooksScraper(BaseScraper):
    name = SOURCE_NAME

    def __init__(self, session, start_url=DEFAULT_START_URL, pause=0.5, max_pages=None):
        super().__init__(session, start_url, pause, max_pages)

    def parse_page(self, soup, page_url):
        records = []
        for pod in soup.select("article.product_pod"):
            try:
                records.append(self._parse_pod(pod, page_url))
            except Exception as exc:
                logger.warning("%s: skipped a bad product pod: %s", SOURCE_NAME, exc)
        next_el = soup.select_one("li.next > a")
        next_href = next_el.get("href") if next_el else None
        return records, next_href

    def _parse_pod(self, pod, page_url):
        title_el = pod.select_one("h3 > a")
        title = title_el.get("title") if title_el else None
        if not title and title_el:
            title = title_el.get_text(strip=True)
        href = title_el.get("href") if title_el else None
        detail_url = urljoin(page_url, href) if href else page_url

        price_el = pod.select_one("p.price_color")
        price_text = price_el.get_text(strip=True) if price_el else None

        rating_el = pod.select_one("p.star-rating")
        rating_word = None
        if rating_el:
            classes = rating_el.get("class", []) or []
            rating_word = next(
                (c for c in classes if c.lower() not in _WORD_TO_IGNORE), None
            )

        availability_el = pod.select_one("p.instock.availability")
        availability = (
            availability_el.get_text(strip=True) if availability_el else None
        )

        return {
            "source": SOURCE_NAME,
            "source_url": detail_url,
            "name_or_title": title,
            "category": None,
            "price": price_text,
            "rating": rating_word,
            "author": None,
            "tags": None,
            "description": None,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }
