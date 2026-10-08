"""Unit tests for processing/validation.py — no internet required."""

from processing.validation import validate_record


def _valid_quote():
    return {
        "source": "Quotes to Scrape",
        "source_url": "https://quotes.toscrape.com/author/Albert-Einstein",
        "name_or_title": "The world as we have created it",
        "price": None,
        "rating": None,
        "author": "Albert Einstein",
    }


def _valid_book():
    return {
        "source": "Books to Scrape",
        "source_url": "https://books.toscrape.com/catalogue/a_1/index.html",
        "name_or_title": "A Light in the Attic",
        "price": 51.77,
        "rating": 3,
    }


def test_valid_records_have_no_reasons():
    assert validate_record(_valid_book()) == []
    assert validate_record(_valid_quote()) == []


def test_unknown_source_rejected():
    rec = _valid_book()
    rec["source"] = "Unknown Site"
    assert "unknown_source" in validate_record(rec)


def test_missing_name_rejected():
    rec = _valid_book()
    rec["name_or_title"] = "   "
    reasons = validate_record(rec)
    assert "missing_name_or_title" in reasons


def test_invalid_url_rejected():
    rec = _valid_quote()
    rec["source_url"] = "ftp://x"
    assert "invalid_source_url" in validate_record(rec)


def test_negative_price_rejected():
    rec = _valid_book()
    rec["price"] = -5
    assert "invalid_price" in validate_record(rec)


def test_non_numeric_price_rejected():
    rec = _valid_book()
    rec["price"] = "abc"
    assert "invalid_price" in validate_record(rec)


def test_rating_out_of_range_rejected():
    rec = _valid_book()
    rec["rating"] = 6
    assert "invalid_rating" in validate_record(rec)


def test_empty_price_and_rating_are_allowed():
    rec = _valid_quote()
    rec["price"] = None
    rec["rating"] = None
    assert validate_record(rec) == []
