"""Small, pure cleaning functions. No internet, no file I/O."""

import re
from urllib.parse import urljoin

_NON_BREAKING_SPACE = "\xa0"
_WHITESPACE_RE = re.compile(r"\s+")
_CURLY_QUOTES = "\u201c\u201d\u2018\u2019\u201e\u201f\u00ab\u00bb\ufffd"
_PRICE_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_RATING_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}


def clean_text(value):
    if value is None:
        return None
    text = str(value).replace(_NON_BREAKING_SPACE, " ")
    text = _WHITESPACE_RE.sub(" ", text)
    text = text.strip()
    return text or None


def strip_quotes(value):
    if value is None:
        return None
    text = str(value)
    text = text.strip().strip(_CURLY_QUOTES)
    return clean_text(text)


def clean_price(value):
    if value is None:
        return None
    text = clean_text(value)
    if text is None:
        return None
    match = _PRICE_NUMBER_RE.search(text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def clean_rating(value):
    if value is None:
        return None
    text = clean_text(value)
    if text is None:
        return None
    lowered = text.lower()
    for word, number in _RATING_WORDS.items():
        if word in lowered:
            return number
    digits = re.search(r"\d+", lowered)
    if digits:
        return int(digits.group())
    return None


def clean_tags(value):
    if value is None:
        return None
    if isinstance(value, str):
        items = [t.strip() for t in value.split(";")]
    else:
        items = list(value)
    cleaned = set()
    for item in items:
        tag = clean_text(item)
        if tag:
            cleaned.add(tag.lower())
    if not cleaned:
        return None
    return ";".join(sorted(cleaned))


def normalize_url(value, base=None):
    if value is None:
        return None
    text = clean_text(value)
    if text is None:
        return None
    if base and not text.startswith(("http://", "https://")):
        text = urljoin(base, text)
    if text.startswith(("http://", "https://")):
        return text
    return None


def clean_record(record):
    """Apply all cleaners to one raw record, returning a normalized dict."""
    source = clean_text(record.get("source"))
    return {
        "source": source,
        "source_url": clean_text(record.get("source_url")),
        "name_or_title": strip_quotes(record.get("name_or_title")),
        "category": clean_text(record.get("category")),
        "price": clean_price(record.get("price")),
        "rating": clean_rating(record.get("rating")),
        "author": clean_text(record.get("author")),
        "tags": clean_tags(record.get("tags")),
        "description": clean_text(record.get("description")),
        "scraped_at": clean_text(record.get("scraped_at")),
    }
