"""Duplicate detection via normalized fingerprints."""

import hashlib
import re

_BOOKS_KEY = "bookstoscrape"
_QUOTES_KEY = "quotestoscrape"
_PUNCT_RE = re.compile(r"[^\w\s]")
_WS_RE = re.compile(r"\s+")


def _normalize(value):
    text = str(value).lower()
    text = _PUNCT_RE.sub("", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def _source_key(record):
    return _normalize(record.get("source", "")).replace(" ", "")


def build_fingerprint(record):
    key = _source_key(record)
    if key == _BOOKS_KEY:
        identity = key + "|" + _normalize(record.get("name_or_title", ""))
    elif key == _QUOTES_KEY:
        quote_part = _normalize(record.get("name_or_title", ""))[:50]
        identity = key + "|" + _normalize(record.get("author", "")) + "|" + quote_part
    else:
        identity = key + "|" + _normalize(record.get("name_or_title", ""))
    return hashlib.md5(identity.encode("utf-8")).hexdigest()


def deduplicate(records):
    seen = set()
    unique = []
    duplicates = []
    for record in records:
        fingerprint = build_fingerprint(record)
        if fingerprint in seen:
            duplicates.append(record)
        else:
            seen.add(fingerprint)
            unique.append(record)
    return unique, duplicates
