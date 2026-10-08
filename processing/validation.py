"""Validation rules. Returns a list of reasons; empty list means valid."""

ALLOWED_SOURCES = {"Books to Scrape", "Quotes to Scrape"}


def _is_blank(value):
    return value is None or str(value).strip() == ""


def validate_record(record):
    reasons = []

    source = record.get("source")
    if source not in ALLOWED_SOURCES:
        reasons.append("unknown_source")

    if _is_blank(record.get("name_or_title")):
        reasons.append("missing_name_or_title")

    url = record.get("source_url")
    if _is_blank(url) or not str(url).startswith(("http://", "https://")):
        reasons.append("invalid_source_url")

    price = record.get("price")
    if not _is_blank(price):
        try:
            if float(price) < 0:
                reasons.append("invalid_price")
        except (TypeError, ValueError):
            reasons.append("invalid_price")

    rating = record.get("rating")
    if not _is_blank(rating):
        try:
            rating_int = int(rating)
            if rating_int < 1 or rating_int > 5:
                reasons.append("invalid_rating")
        except (TypeError, ValueError):
            reasons.append("invalid_rating")

    return reasons
