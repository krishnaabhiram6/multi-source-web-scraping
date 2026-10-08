# AI_USAGE.md

An honest record of how AI tools helped on this assignment, what was reviewed, what was
fixed, and how the final code was verified.

---

## 1. AI Tools Used

| Tool | Role |
|------|------|
| **opencode** (AI coding assistant, powered by GLM-5.2) | Project scaffolding, drafting scraper/cleaning/validation/dedup code, writing tests, debugging the encoding and fingerprint bugs, drafting documentation |
| **Browser Developer Tools (F12)** | Manual confirmation of HTML selectors on both sites (not AI, but used alongside AI suggestions) |

---

## 2. What Each Tool Was Used For

- **opencode — initial exploration & selectors:** I used it to fetch and parse both sites
  to confirm the selectors from the reference document against the live HTML
  (`article.product_pod`, `p.price_color`, `p.star-rating`, `div.quote`, `span.text`, etc.).
- **opencode — code generation:** Drafted `base_scraper.py` (resilient session + pagination),
  the two source scrapers, the cleaning functions, validation, deduplication, `main.py`
  orchestration, and the three test files.
- **opencode — debugging:** Diagnosed two real bugs found during testing (see section 5).
- **opencode — documentation:** Drafted this file and `README.md`.

---

## 3. Representative Prompts

A few real prompts used during the session (paraphrased for length):

1. *"Build a Python ETL pipeline that scrapes books.toscrape.com and quotes.toscrape.com,
   follows the 'next' link for pagination, cleans the data, validates it, removes
   duplicates, and writes final_dataset.csv + summary_report.json + a log file. Use the
   project structure from the reference document."*

2. *"Inspect both sites' actual HTML and confirm the selectors for title, price, rating,
   author, tags, link, and the next-page button."*

3. *"My `clean_price('£51.77')` is returning a replacement character instead of £. The price
   byte is 0xA3. Why does forcing utf-8 break it, and what's the right fix?"*

4. *"My duplicate-detection test for quotes is failing — two quotes with the same first 50
   characters produce different fingerprints. The identities look identical when printed.
   Find the bug."*

5. *"Run the full pipeline and verify the summary JSON reconciles with the CSV row count."*

---

## 4. Which Parts of the Code Were AI-Assisted

- **All modules** were drafted by the AI assistant, then reviewed line-by-line and corrected.
- The two non-obvious bug fixes (encoding, fingerprint source-key matching) were found by
  the AI's diagnostics **after** the initial draft failed tests — see section 5.
- The unit tests were AI-drafted and then I verified each assertion against the documented
  behavior.

---

## 5. Important Changes Made After Reviewing AI Output

Two genuine bugs in the AI's initial draft were caught by testing and fixed:

### Bug 1 — `apparent_encoding` broke the `£` symbol
- **AI's first draft** set `response.encoding = response.apparent_encoding` on every
  response, following the reference doc's "set encoding to utf-8" tip.
- **Problem:** Books to Scrape declares **no** charset, so the `£` is the single byte
  `0xA3` (ISO-8859-1). The `apparent_encoding` detector mis-guesses **UTF-8** for that page,
  so `0xA3` decodes to the replacement character `�` and the `£` is lost.
- **Fix:** Use the server-declared encoding (requests already defaults to ISO-8859-1 when
  no charset is given — which decodes `£` correctly). Removed the `apparent_encoding`
  override. As a safety net, `clean_price` extracts the number with a regex, so the price is
  recovered even if the currency symbol is mangled.
- **Lesson:** The reference doc's "set utf-8" tip is site-specific advice, not a universal
  rule. I verified the actual bytes before deciding.

### Bug 2 — Dedup source-key never matched, so the first-50-chars rule was never used
- **AI's first draft** compared `_normalize(source) == "quotestoscrape"` to pick the
  quotes fingerprint rule. But `_normalize` keeps spaces, so
  `_normalize("Quotes to Scrape") == "quotes to scrape"`, which never equals
  `"quotestoscrape"`. The code fell through to the else branch and used the **full** quote
  text instead of the first 50 characters.
- **Problem:** The quote dedup test failed because two quotes with the same first 50 chars
  but different tails produced different fingerprints.
- **Fix:** Added a `_source_key()` helper that strips spaces (`"quotes to scrape"` →
  `"quotestoscrape"`) so the per-source rule is correctly selected. Re-verified the test.

### Other changes after review
- **Fragile default-URL lookup:** `main.py` first used
  `BooksScraper.__init__.__defaults__[0]` to read the start URL. I replaced this with an
  explicit `DEFAULT_START_URL` import — clearer and robust if defaults change.
- **CSS selector quoting:** `a[href^=/author/]` (no quotes) is invalid in soupsieve and
  raised `SelectorSyntaxError`. Fixed to `a[href^="/author/"]` (quoted), per the reference
  doc.
- **`clean_price` comma handling:** First draft treated `,` as a European decimal
  separator (`"1.234,56"` → `1234.56`). Books to Scrape uses `£51.77` with `,` only as a
  thousands separator, so I changed it to strip commas before extracting the number
  (`"£1,234.56"` → `1234.56`). Removed the unrealistic European test case.

---

## 6. Incorrect / Incomplete AI Suggestions Discovered

1. **"Set `response.encoding = 'utf-8'` to fix the `Â£` issue."** This is the *opposite* of
   what Books to Scrape needs (it needs ISO-8859-1). Blindly following it breaks the `£`.
   Confirmed by inspecting the raw bytes (`0xA3`).

2. **`a[href^=/author/]` as a CSS selector.** Without quotes this is malformed and soupsieve
   raises an error. Must be `a[href^="/author/"]`.

3. **Using `__init__.__defaults__` to read module-level constants.** Worked, but fragile and
   opaque. Replaced with an explicit import.

4. **Initial dedup test assumed the first-50-chars rule was being applied.** It wasn't
   (Bug 2). The test correctly *exposed* that the code and the README rule disagreed — a
   classic "mismatched rule" mistake flagged in the reference doc.

---

## 7. How the Final Solution Was Tested and Verified

1. **Unit tests (no internet):** `python -m pytest tests/ -v` → **20/20 passed**, covering
   every cleaning function, all validation rules, and the deduplication fingerprint logic
   (including deliberately duplicated sample records with case/spacing/punctuation variants).
2. **Smoke test:** Scraped 2 pages of each source and printed a cleaned record from each to
   confirm `£51.77 → 51.77`, `Three → 3`, curly quotes stripped, tags sorted.
3. **Full run:** `python main.py` scraped all 50 books pages + 10 quotes pages in ~60s.
4. **Reconciliation check:** `raw (1100) − rejected (0) − duplicates (1) = final (1099)`,
   and the CSV has exactly 1099 rows — matching `summary_report.json`.
5. **Data-quality spot check:** All 999 book prices parse as floats (range £10.00–£59.99);
   all ratings are integers 1–5; all 100 quotes have an author and sorted `;`-joined tags;
   both sources appear in the CSV.
6. **Duplicate verification:** The 1 duplicate removed was "The Star-Touched Queen",
   genuinely listed at two product URLs (`_764` and `_642`) — a real duplicate, confirming
   the logic works on live data.
7. **Log check:** `logs/scraper.log` has 188 timestamped lines (INFO for pages, the
   start/end markers).

### Fresh-environment verification

To reproduce a reviewer's experience: dependencies reinstall cleanly from
`requirements.txt` (`pip install -r requirements.txt`) and `python main.py` plus
`python -m pytest tests/` both pass from a clean install.
