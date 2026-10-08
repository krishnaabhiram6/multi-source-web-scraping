"""Unit tests for processing/cleaning.py — no internet required."""

from processing.cleaning import (
    clean_price,
    clean_rating,
    clean_tags,
    clean_text,
    clean_record,
    normalize_url,
    strip_quotes,
)


def test_clean_text_collapses_whitespace_and_nbsp():
    assert clean_text("  Hello \n World ") == "Hello World"
    assert clean_text("a\xa0b\tc") == "a b c"
    assert clean_text(None) is None
    assert clean_text("   ") is None


def test_strip_quotes_removes_curly_quotes():
    assert strip_quotes("\u201cHello world\u201d") == "Hello world"
    assert strip_quotes("  \u2018quote\u2019 ") == "quote"
    assert strip_quotes(None) is None


def test_clean_price_extracts_number():
    assert clean_price("\u00a351.77") == 51.77
    assert clean_price("£12.34") == 12.34
    assert clean_price("Price: 9.99") == 9.99
    assert clean_price("£1,234.56") == 1234.56
    assert clean_price("no number") is None
    assert clean_price(None) is None


def test_clean_rating_word_to_int():
    assert clean_rating("Three") == 3
    assert clean_rating("FIVE") == 5
    assert clean_rating("star-rating One") == 1
    assert clean_rating("2") == 2
    assert clean_rating("zero") is None
    assert clean_rating(None) is None


def test_clean_tags_lowercases_sorts_and_joins():
    assert clean_tags(["World", "Change", "deep-thoughts"]) == "change;deep-thoughts;world"
    assert clean_tags("B;A;C") == "a;b;c"
    assert clean_tags([]) is None
    assert clean_tags(None) is None


def test_normalize_url():
    assert normalize_url("https://books.toscrape.com/x").startswith("https://")
    assert normalize_url("/page-2.html", base="https://books.toscrape.com/") == "https://books.toscrape.com/page-2.html"
    assert normalize_url("not a url") is None
    assert normalize_url(None) is None


def test_clean_record_book():
    raw = {
        "source": "Books to Scrape",
        "source_url": "https://books.toscrape.com/catalogue/a_1/index.html",
        "name_or_title": "  A  Light ",
        "category": None,
        "price": "£51.77",
        "rating": "Three",
        "author": None,
        "tags": None,
        "description": None,
        "scraped_at": "2026-01-01T00:00:00+00:00",
    }
    cleaned = clean_record(raw)
    assert cleaned["price"] == 51.77
    assert cleaned["rating"] == 3
    assert cleaned["name_or_title"] == "A Light"
    assert cleaned["author"] is None
