"""ETL entry point: scrape -> clean -> validate -> deduplicate -> write.

Run with:  python main.py
"""

import csv
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from processing.cleaning import clean_record
from processing.deduplication import deduplicate
from processing.validation import validate_record
from scrapers.base_scraper import create_session
from scrapers.books_scraper import BooksScraper, DEFAULT_START_URL as BOOKS_START_URL
from scrapers.quotes_scraper import QuotesScraper, DEFAULT_START_URL as QUOTES_START_URL

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"
CSV_PATH = OUTPUT_DIR / "final_dataset.csv"
SUMMARY_PATH = OUTPUT_DIR / "summary_report.json"
LOG_PATH = LOGS_DIR / "scraper.log"

COLUMNS = [
    "source",
    "source_url",
    "name_or_title",
    "category",
    "price",
    "rating",
    "author",
    "tags",
    "description",
    "scraped_at",
]


def setup_logging():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    root.addHandler(console_handler)


logger = logging.getLogger("main")


def run_scraping(session):
    raw = {}
    for source_name, scraper_cls, start_url in (
        ("Books to Scrape", BooksScraper, BOOKS_START_URL),
        ("Quotes to Scrape", QuotesScraper, QUOTES_START_URL),
    ):
        try:
            scraper = scraper_cls(session, start_url=start_url)
            raw[source_name] = scraper.scrape()
        except Exception as exc:
            logger.error("%s scraping crashed: %s. Continuing with empty set.", source_name, exc)
            raw[source_name] = []
    return raw


def run_cleaning(raw_by_source):
    cleaned = {}
    for source_name, records in raw_by_source.items():
        cleaned[source_name] = [clean_record(r) for r in records]
        logger.info("Cleaned %d records for %s", len(cleaned[source_name]), source_name)
    return cleaned


def run_validation(cleaned_by_source):
    valid = []
    rejected_reasons = Counter()
    rejected_by_source = Counter()
    for source_name, records in cleaned_by_source.items():
        for record in records:
            reasons = validate_record(record)
            if reasons:
                reason_text = ";".join(reasons)
                rejected_reasons[reason_text] += 1
                rejected_by_source[source_name] += 1
                logger.warning(
                    "Rejected %s record: %s | reasons=%s",
                    source_name,
                    record.get("source_url"),
                    reason_text,
                )
            else:
                valid.append(record)
    return valid, rejected_reasons, rejected_by_source


def write_csv(records):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = {col: ("" if record.get(col) is None else record.get(col)) for col in COLUMNS}
            writer.writerow(row)
    logger.info("Wrote %d rows to %s", len(records), CSV_PATH)


def write_summary(summary):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    logger.info("Wrote summary report to %s", SUMMARY_PATH)


def main():
    setup_logging()
    start_time = time.time()
    start_iso = datetime.now(timezone.utc).isoformat()
    logger.info("=== ETL run started at %s ===", start_iso)

    session = create_session()

    raw_by_source = run_scraping(session)
    cleaned_by_source = run_cleaning(raw_by_source)
    valid_records, rejected_reasons, rejected_by_source = run_validation(cleaned_by_source)
    unique_records, duplicates = deduplicate(valid_records)

    write_csv(unique_records)

    end_time = time.time()
    end_iso = datetime.now(timezone.utc).isoformat()
    duration = round(end_time - start_time, 2)

    summary = {
        "raw_records_per_source": {
            src: len(raw_by_source.get(src, [])) for src in raw_by_source
        },
        "cleaned_records_per_source": {
            src: len(cleaned_by_source.get(src, [])) for src in cleaned_by_source
        },
        "rejected_records_per_source": dict(rejected_by_source),
        "rejected_reasons": dict(rejected_reasons),
        "duplicates_found": len(duplicates),
        "final_record_count": len(unique_records),
        "start_time": start_iso,
        "end_time": end_iso,
        "duration_seconds": duration,
    }
    write_summary(summary)

    raw_total = sum(summary["raw_records_per_source"].values())
    logger.info(
        "=== ETL run finished in %ss | raw=%d valid_after_dedup=%d rejected=%d duplicates=%d ===",
        duration,
        raw_total,
        len(unique_records),
        sum(rejected_by_source.values()),
        len(duplicates),
    )


if __name__ == "__main__":
    main()
