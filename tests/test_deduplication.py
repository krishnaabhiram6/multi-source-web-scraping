"""Unit tests for processing/deduplication.py — no internet required.

The live sites contain unique items, so we deliberately duplicate sample
records here to prove the fingerprint logic catches spacing/case variants.
"""

from processing.deduplication import build_fingerprint, deduplicate


def test_fingerprint_ignores_case_and_spacing():
    a = build_fingerprint({"source": "Books to Scrape", "name_or_title": "Example Book Title"})
    b = build_fingerprint({"source": "Books to Scrape", "name_or_title": "  EXAMPLE book  title "})
    assert a == b


def test_fingerprint_ignores_punctuation():
    a = build_fingerprint({"source": "Books to Scrape", "name_or_title": "A, Book!"})
    b = build_fingerprint({"source": "Books to Scrape", "name_or_title": "a book"})
    assert a == b


def test_quote_fingerprint_uses_author_and_first_50_chars():
    a = build_fingerprint({
        "source": "Quotes to Scrape",
        "author": "Albert Einstein",
        "name_or_title": "The world as we have created it is a process of our thinking. Extra.",
    })
    b = build_fingerprint({
        "source": "Quotes to Scrape",
        "author": "albert einstein",
        "name_or_title": "The world as we have created it is a process of our thinking.",
    })
    assert a == b


def test_deduplicate_separates_duplicates_from_unique():
    records = [
        {"source": "Books to Scrape", "name_or_title": "Title One"},
        {"source": "Books to Scrape", "name_or_title": "  TITLE one "},
        {"source": "Books to Scrape", "name_or_title": "Title Two"},
        {
            "source": "Quotes to Scrape",
            "author": "Author A",
            "name_or_title": "A quote that is long enough to be meaningful here.",
        },
        {
            "source": "Quotes to Scrape",
            "author": "Author A",
            "name_or_title": "a QUOTE that is long enough to be meaningful here.",
        },
    ]
    unique, duplicates = deduplicate(records)
    assert len(unique) == 3
    assert len(duplicates) == 2


def test_different_sources_are_not_merged():
    a = build_fingerprint({"source": "Books to Scrape", "name_or_title": "Same"})
    b = build_fingerprint({"source": "Quotes to Scrape", "name_or_title": "Same"})
    assert a != b
