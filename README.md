# Multi-Source Web Scraping & Data Consolidation

A Python ETL pipeline that scrapes **Books to Scrape** and **Quotes to Scrape**, cleans and
validates the records, removes duplicates, and writes one consolidated CSV plus a
summary report. One command runs the whole job:

```
python main.py
```

---

## 1. Project Overview

Real web data is rarely tidy: sources use different structures, values arrive messy
(`£51.77`, the word `Three`, stray whitespace), and networks fail. This project practices
the three problems you meet in almost every data job by implementing a small
**Extract → Transform → Load** pipeline:

- **Extract** — two source scrapers with dynamic pagination and resilient HTTP.
- **Transform** — small pure cleaning functions, rule-based validation, fingerprint deduplication.
- **Load** — one standardized CSV and a JSON summary that reconciles.

Each stage does one job and knows nothing about the others, so each can be tested and
fixed independently.

---

## 2. Python Version

- **Python 3.11.0** (any 3.10–3.12 works)
- Check with: `python --version`

---

## 3. Installation & Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the pipeline
python main.py
```

After the run finishes, three artifacts exist:

| File | Contents |
|------|----------|
| `output/final_dataset.csv` | One row per unique, valid record from both sites |
| `output/summary_report.json` | Counts per source: scraped, cleaned, rejected, duplicates, final, run time |
| `logs/scraper.log` | Timestamped record of every request, page, warning, and error |

### Run the unit tests (no internet required)

```bash
python -m pytest tests/ -v
```

---

## 4. Dependencies

Pinned to the exact versions used in development (`requirements.txt`):

| Library | Version | Purpose |
|--------|---------|---------|
| requests | 2.34.2 | Downloads the HTML of each page |
| beautifulsoup4 | 4.15.0 | Searches the HTML for the pieces we want |
| lxml | 6.1.3 | Fast parser engine used by BeautifulSoup |
| pytest | 8.1.0 | Runs the unit tests |

Standard-library modules used: `csv`, `json`, `logging`, `re`, `urllib.parse`, `time`,
`pathlib`, `hashlib`, `datetime`, `collections`, `sys`.

---

## 5. Project Structure

```
realis_assignment/
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py      # Shared HTTP: session, retries, backoff, pagination loop
│   ├── books_scraper.py      # Books to Scrape selectors + parsing
│   └── quotes_scraper.py     # Quotes to Scrape selectors + parsing
├── processing/
│   ├── __init__.py
│   ├── cleaning.py           # Pure functions: clean_text, clean_price, clean_rating...
│   ├── validation.py         # Rule checks returning a list of reasons
│   └── deduplication.py      # Fingerprint building + unique/duplicate split
├── tests/
│   ├── test_cleaning.py
│   ├── test_validation.py
│   └── test_deduplication.py
├── output/                   # Generated at runtime (final_dataset.csv, summary_report.json)
├── logs/                     # Generated at runtime (scraper.log)
├── main.py                   # The only file you run: orchestrates all stages
├── requirements.txt
├── README.md
└── AI_USAGE.md
```

**Rule of thumb:** if a function touches the internet, it lives in `scrapers/`. If it only
transforms data, it lives in `processing/`. If it connects the stages, it lives in `main.py`.

---

## 6. How Pagination Works

Both scrapers use **dynamic "next"-link pagination**, never hard-coded page numbers:

1. Start at the source's first page.
2. Parse the page with BeautifulSoup.
3. Look for `li.next > a`. If found, `urljoin(current_url, href)` builds the next full URL.
4. Repeat until there is no `next` link.
5. A 0.5-second pause is inserted between requests to avoid overloading the server.

This means the scraper keeps working if the site gains or loses pages. A hard-coded
`range(1, 51)` would break silently if the page count changed.

---

## 7. Source Exploration — HTML Selectors

The sites were inspected with browser Developer Tools (F12) before coding.

| Field | Books to Scrape | Quotes to Scrape |
|-------|-----------------|------------------|
| One record | `article.product_pod` | `div.quote` |
| Main text | `h3 > a` (full title in the `title` attribute; visible text is cut off with `...`) | `span.text` (wrapped in curly quotes `“…”`) |
| Price | `p.price_color` (e.g. `£51.77`) | — |
| Rating | 2nd class on `p.star-rating` (e.g. `Three`) | — |
| Author | — | `small.author` |
| Tags | — | `a.tag` (zero or more) |
| Link | `h3 > a[href]` (relative) | `a[href^="/author/"]` (author page, relative) |
| Next page | `li.next > a` | `li.next > a` |

---

## 8. Data Model (Common Schema)

Both sources are normalized into one table with 10 columns. Cells are left **empty**
(`None`) where a field does not apply — no fake values are invented.

| Column | Books to Scrape | Quotes to Scrape |
|--------|-----------------|------------------|
| `source` | `Books to Scrape` | `Quotes to Scrape` |
| `source_url` | Book detail page URL | **Author page URL** (documented choice) |
| `name_or_title` | Book title | Quote text (curly quotes stripped) |
| `category` | *(empty — see Known Limitations)* | `Quotes` (fixed label) |
| `price` | Number, e.g. `51.77` | empty |
| `rating` | Integer 1–5 | empty |
| `author` | empty | Author name |
| `tags` | empty | `tag1;tag2;...` (lowercased, sorted, `;`-joined) |
| `description` | *(empty — see Known Limitations)* | empty |
| `scraped_at` | UTC ISO timestamp | UTC ISO timestamp |

**`source_url` choice for quotes:** the quote's author-page URL is stored (e.g.
`https://quotes.toscrape.com/author/Albert-Einstein`). The listing page URL where the
quote appeared is not unique per quote, so the author URL is a more identifying link.

---

## 9. Cleaning Approach

Cleaning is kept **separate from scraping** in `processing/cleaning.py`. Each function is
small, pure, and testable with a plain string (no internet). `clean_record()` applies them
all to one raw record.

| Function | What it does | Example |
|----------|--------------|---------|
| `clean_text` | Removes `\xa0`, collapses whitespace, strips | `"  Hello \n World "` → `"Hello World"` |
| `strip_quotes` | Strips curly quotes / smart quotes from the ends | `“Hello”` → `Hello` |
| `clean_price` | Extracts the numeric value via regex (comma = thousands) | `£51.77` → `51.77` |
| `clean_rating` | Maps word → integer (`one`..`five`), falls back to digits | `Three` → `3` |
| `clean_tags` | Lowercases, sorts, joins with `;` | `["World","change"]` → `change;world` |
| `normalize_url` | Ensures the URL is complete and starts with `http(s)://` | — |

**Encoding note:** requests uses the server-declared encoding. Books to Scrape declares no
charset (so requests defaults to ISO-8859-1, which correctly decodes the `£` byte). Quotes
to Scrape declares UTF-8, which correctly decodes the curly quotes. We deliberately do
**not** force `apparent_encoding`, because the detector mis-guesses UTF-8 for the books
page and breaks the `£`. `clean_price` also extracts digits via regex, so the number is
recovered even if the currency symbol is mangled.

---

## 10. Validation Approach

`processing/validation.py` checks one cleaned record and returns a **list of reasons**
(empty list = valid). Returning reasons (not just True/False) lets the summary report show
*why* records were rejected.

| Rule | Check |
|------|-------|
| Known source | `source` is one of the two allowed names |
| Has a name | `name_or_title` is not empty |
| Valid URL | `source_url` starts with `http://` or `https://` |
| Valid price | If present, it is a number ≥ 0 |
| Valid rating | If present, it is an integer from 1 to 5 |

Invalid records are counted by reason and logged as **WARNING**s; the program keeps running.

---

## 11. Deduplication Approach

Exact string comparison is not enough — the same record can differ in whitespace,
capitalization, or punctuation:

```
"Example Book Title"
" Example Book Title "
"EXAMPLE BOOK TITLE"
```

`processing/deduplication.py` builds a **normalized fingerprint** for each record:

1. Lowercase the identifying fields.
2. Remove punctuation (`[^\w\s]`).
3. Collapse whitespace.
4. Hash the result with MD5.

**Which fields identify a record:**

| Source | Identity fields |
|--------|-----------------|
| Books to Scrape | `source` + `name_or_title` |
| Quotes to Scrape | `source` + `author` + first 50 chars of `name_or_title` |

A record whose fingerprint is already in the seen-set is a duplicate.

**Remove or flag?** We **remove** duplicates (the second occurrence is dropped). Both
practice sites contain unique items, so flagging would add a column that is `False` for
every row. Removing keeps the final dataset clean for downstream use. This is documented
here and matched in the code. The fingerprint logic is proven by a unit test with
deliberately duplicated sample records.

---

## 12. Error-Handling Approach

| Failure | Handling |
|---------|----------|
| Transient HTTP errors (429, 500, 502, 503, 504) | Retried with exponential backoff (1s, 2s, 4s) up to 3 times |
| Timeout / connection error | Same retry, then logged as ERROR and that source stops |
| One bad record on a page | Wrapped in `try/except`, logged as WARNING, other records continue |
| One source crashes | Wrapped in its own `try/except` in `main.py`; the other source still runs |
| Missing HTML element | `select_one()` + `None` check before reading a field |
| Server overload | 0.5s pause between requests |

Logging writes to both the console and `logs/scraper.log`:
- **INFO** for each page fetch and page yield
- **WARNING** for each rejected record and each skipped bad element
- **ERROR** for each failed page/source

---

## 13. Output Description

### `output/final_dataset.csv`
UTF-8, fixed column order, one row per unique valid record. Empty cells for inapplicable
fields. Prices are numeric, ratings are integers 1–5, tags are `;`-joined.

### `output/summary_report.json`
```json
{
  "raw_records_per_source":       {"Books to Scrape": 1000, "Quotes to Scrape": 100},
  "cleaned_records_per_source":   {"Books to Scrape": 1000, "Quotes to Scrape": 100},
  "rejected_records_per_source":  {},
  "rejected_reasons":             {},
  "duplicates_found":             1,
  "final_record_count":           1099,
  "start_time":                   "2026-10-07T10:04:31.342440+00:00",
  "end_time":                     "2026-10-07T10:05:31.435093+00:00",
  "duration_seconds":             60.09
}
```

**Reconciliation:** `raw (1100) − rejected (0) − duplicates (1) = final (1099)`. The JSON
final count equals the CSV row count.

### `logs/scraper.log`
Timestamped lines for every request, page change, warning, and error.

---

## 14. Sample Run Results

| Metric | Books | Quotes | Total |
|--------|------:|-------:|------:|
| Raw records | 1000 | 100 | 1100 |
| Cleaned | 1000 | 100 | 1100 |
| Rejected | 0 | 0 | 0 |
| Duplicates removed | 1 | 0 | 1 |
| **Final** | **999** | **100** | **1099** |

The 1 duplicate was the book **"The Star-Touched Queen"**, which is genuinely listed at two
different product URLs (`the-star-touched-queen_764` and `the-star-touched-queen_642`) with
identical price and rating — a real duplicate on the source site, correctly caught by the
fingerprint logic.

---

## 15. Assumptions

1. The two practice sites are static, server-rendered HTML, so `requests` + `BeautifulSoup`
   is sufficient (no JavaScript rendering needed — Selenium/Playwright would only add overhead).
2. A 0.5-second pause is polite for these low-traffic practice sites.
3. The "next" link is the authoritative pagination signal (more robust than guessing page counts).
4. For quotes, the author-page URL is stored as `source_url` because the listing page URL is
   not unique per quote.
5. A fixed label `Quotes` is used as the `category` for quotes so the column is never empty
   for that source (documented, not invented data).
6. Book `category` and `description` are left empty (see Known Limitations).

---

## 16. Known Limitations

1. **Book `category` and `description` are empty.** The book *listing* pages do not show
   these fields; they live on each book's detail page. Fetching ~1000 extra detail pages
   would roughly double the run time and request count. Per the assignment guidance ("Do
   not guess values"), these cells are left empty rather than fabricated. The scraper could
   be extended to visit each detail page while keeping the 0.5s pause.
2. **Title-only dedup for books.** Two genuinely *different* books that happen to share a
   title would be merged. In this run the only duplicate caught was a true duplicate (same
   book at two URLs). Including `source_url` in the fingerprint would prevent merging
   distinct books but would also let true duplicates through.
3. **No incremental/checkpoint resume.** A full run re-scrapes everything. Production would
   add checkpointing (see *What would change for production* below).
4. **Sequential scraping.** Books then quotes, ~60s total. Parallel/async scraping would
   speed this up but adds complexity; the 0.5s pause would need per-domain rate limiting.

---

## 17. Interview Talking Points

- **Why Requests + BeautifulSoup?** Both sites are plain server-rendered HTML. A browser
  tool (Selenium/Playwright) would add overhead for no benefit. `requests` downloads the
  HTML; `BeautifulSoup` with `lxml` parses it quickly.
- **How does pagination work?** Follow `li.next > a`, `urljoin` the relative href, repeat
  until no next link — never hard-code page numbers.
- **How are failed requests handled?** Retry 429/5xx with exponential backoff (1s/2s/4s),
  up to 3 attempts; then log ERROR and stop that source; the other source still runs.
- **How does duplicate detection work?** Normalize (lowercase, strip punctuation, collapse
  spaces) the identifying fields, MD5-hash, and track seen fingerprints.
- **What would change for production?** Add checkpoint/resume, per-domain rate limiting,
  async fetching, detail-page enrichment for books, a database sink (Postgres/Mongo),
  configurable settings via env vars, and a data-quality report.

---

## 18. AI Usage Summary

AI tools were used to scaffold the project, draft boilerplate, and debug. Every line was
reviewed, tested, and corrected where needed. See **AI_USAGE.md** for the full honest record.
