"""Scraper for https://quotes.toscrape.com/ — quotes with dynamic pagination."""

import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

SOURCE_NAME = "Quotes to Scrape"
DEFAULT_START_URL = "https://quotes.toscrape.com/"


class QuotesScraper(BaseScraper):
    name = SOURCE_NAME

    def __init__(self, session, start_url=DEFAULT_START_URL, pause=0.5, max_pages=None):
        super().__init__(session, start_url, pause, max_pages)

    def parse_page(self, soup, page_url):
        records = []
        for quote_el in soup.select("div.quote"):
            try:
                records.append(self._parse_quote(quote_el, page_url))
            except Exception as exc:
                logger.warning("%s: skipped a bad quote block: %s", SOURCE_NAME, exc)
        next_el = soup.select_one("li.next > a")
        next_href = next_el.get("href") if next_el else None
        return records, next_href

    def _parse_quote(self, quote_el, page_url):
        text_el = quote_el.select_one("span.text")
        text = text_el.get_text(strip=True) if text_el else None

        author_el = quote_el.select_one("small.author")
        author = author_el.get_text(strip=True) if author_el else None

        tags = [a.get_text(strip=True) for a in quote_el.select("a.tag")]

        author_link = quote_el.select_one('a[href^="/author/"]')
        author_href = author_link.get("href") if author_link else None
        source_url = urljoin(page_url, author_href) if author_href else page_url

        return {
            "source": SOURCE_NAME,
            "source_url": source_url,
            "name_or_title": text,
            "category": "Quotes",
            "price": None,
            "rating": None,
            "author": author,
            "tags": tags,
            "description": None,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }
