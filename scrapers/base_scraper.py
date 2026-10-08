"""Shared HTTP layer: resilient session, retries with backoff, dynamic pagination."""

import logging
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 RealisierenScraper/1.0"
)


def create_session(user_agent=None, timeout=15, max_retries=3, backoff_base=1.0):
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent or DEFAULT_USER_AGENT})
    session.headers.update({"Accept-Language": "en-US,en;q=0.9"})
    session._timeout = timeout
    session._max_retries = max_retries
    session._backoff_base = backoff_base
    return session


def fetch(session, url):
    last_exc = None
    for attempt in range(1, session._max_retries + 1):
        try:
            response = session.get(url, timeout=session._timeout)
            if response.status_code in RETRY_STATUS_CODES:
                raise requests.HTTPError(
                    f"retryable status {response.status_code} for {url}"
                )
            response.raise_for_status()
            logger.info("OK %s (%s) in %ss", url, response.status_code, attempt)
            return response
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Attempt %d/%d failed for %s: %s",
                attempt,
                session._max_retries,
                url,
                exc,
            )
            if attempt < session._max_retries:
                delay = session._backoff_base * (2 ** (attempt - 1))
                time.sleep(delay)
    raise last_exc


class BaseScraper:
    """Drives dynamic 'next'-link pagination and per-record fault isolation."""

    name = "BaseScraper"

    def __init__(self, session, start_url, pause=0.5, max_pages=None):
        self.session = session
        self.start_url = start_url
        self.pause = pause
        self.max_pages = max_pages

    def parse_page(self, soup, page_url):
        raise NotImplementedError

    def scrape(self):
        url = self.start_url
        page_no = 0
        records = []
        while url:
            page_no += 1
            if self.max_pages and page_no > self.max_pages:
                logger.info("%s: reached max_pages=%d, stopping", self.name, self.max_pages)
                break
            logger.info("%s: page %d -> %s", self.name, page_no, url)
            try:
                response = fetch(self.session, url)
                soup = BeautifulSoup(response.text, "lxml")
                page_records, next_href = self.parse_page(soup, url)
                records.extend(page_records)
                logger.info(
                    "%s: page %d yielded %d records (total %d)",
                    self.name,
                    page_no,
                    len(page_records),
                    len(records),
                )
                url = urljoin(url, next_href) if next_href else None
                if url:
                    time.sleep(self.pause)
            except Exception as exc:
                logger.error(
                    "%s: page %s failed after retries: %s. Stopping this source.",
                    self.name,
                    url,
                    exc,
                )
                break
        logger.info("%s: finished with %d raw records", self.name, len(records))
        return records
