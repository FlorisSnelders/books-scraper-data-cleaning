# Books Scraper + Data Cleaning

A small, end-to-end Python project: scrape **every product** from a website, then turn the messy raw data into a **clean, validated CSV and Excel file**, with a report that shows exactly what was fixed.

The target is [books.toscrape.com](https://books.toscrape.com), a sandbox site built for scraping practice.

## What it does

| Step | Script | Output |
|---|---|---|
| 1. Scrape | `scrape.py` | Walks all 50 catalogue pages, visits all 1,000 product pages and saves title, price, star rating, availability, category, product URL and UPC **exactly as scraped** to `data/raw_books.csv` |
| 2. Clean | `clean.py` | Fixes the data and writes `data/clean_books.csv`, a formatted `data/clean_books.xlsx` and `cleaning_report.md` |
| | `main.py` | Runs both steps |

**Polite scraping:** clear User-Agent, a random 0.5–1 s pause before every request, automatic retries with exponential backoff on connection errors and 429/5xx responses, and a 15 s timeout. A page that still fails is logged and skipped, so one bad page never crashes the run.

**Cleaning:**

- Repairs broken characters (mojibake such as `Â£` instead of `£`)
- Trims stray whitespace and newlines
- `price` becomes a number, with a separate `currency` column (`GBP`)
- `star_rating` becomes an integer 1–5 (`"Three"` → `3`)
- `availability` becomes the number in stock (`"In stock (22 available)"` → `22`)
- Column names become consistent `snake_case`
- Removes duplicates and rows with missing or unparseable values
- Validates the result (no missing values, unique UPCs, prices above 0, ratings 1–5) and **refuses to write output that fails**
- Logs every fix and how many rows it affected

**Excel output:** styled header row, frozen top row, autofilter on every column, column widths fitted to the content, prices shown with two decimals.

## How to run

Requires Python 3.11+.

```bash
pip install -r requirements.txt
python main.py
pytest
```

The full scrape takes about 15 minutes because of the deliberate pause between requests. `python clean.py` re-runs only the cleaning step (about a second).

## Sample output

From a real run on 25 October 2026. All output files are committed in [`data/`](data/), and the full report is in [`cleaning_report.md`](cleaning_report.md).

- **1,000 books** scraped from 50 catalogue pages in 15 min 15 s, **0 failed pages**
- **1,000 clean rows** delivered. Nothing had to be removed: the checks found no duplicates and no missing values
- 50 categories, prices £10.00 to £59.99, 1 to 22 copies in stock

**One book, before and after:**

| Field | Raw (`data/raw_books.csv`) | Clean (`data/clean_books.csv`) |
|---|---|---|
| title | `'The White Cat and the Monk: A Retelling of the Poem â\x80\x9cPangur BÃ¡nâ\x80\x9d'` | The White Cat and the Monk: A Retelling of the Poem “Pangur Bán” |
| price | `'Â£58.08'` | 58.08 |
| currency | *(not a column)* | GBP |
| star_rating | `'Four'` | 4 |
| availability | `'\n\n    \n        In stock (15 available)\n    \n'` | 15 |
| category | `'\nChildrens\n'` | Childrens |

**Issues found** (from `cleaning_report.md`):

| Issue | Rows affected |
|---|---:|
| Broken characters in `title` (e.g. `Shakespeareâ\x80\x99s` → `Shakespeare’s`) | 9 |
| Broken currency symbol in `price` (`Â£` → `£`) | 1,000 |
| Stray whitespace/newlines in `availability` | 1,000 |
| Stray whitespace/newlines in `category` | 1,000 |
| `price` text → number + `currency` column | 1,000 |
| `star_rating` word → integer 1–5 | 1,000 |
| `availability` text → number in stock | 1,000 |
| Duplicates / rows with missing values | 0 |

The report also flags one title, *The Star-Touched Queen*, that appears twice with different UPCs and prices. These are separate listings on the site, so both rows are kept.

**Console output of the cleaning step:**

```
02:20:50 INFO    [clean] Loaded 1000 raw rows from raw_books.csv
02:20:50 INFO    [clean] Encoding artifacts in `title`                         9 rows
02:20:50 INFO    [clean] Encoding artifacts in `price`                      1000 rows
02:20:50 INFO    [clean] Stray whitespace/newlines in `availability`        1000 rows
02:20:50 INFO    [clean] Stray whitespace/newlines in `category`            1000 rows
02:20:50 INFO    [clean] Currency symbol split into `currency` column       1000 rows
02:20:50 INFO    [clean] `price` converted from text to number              1000 rows
02:20:50 INFO    [clean] `star_rating` converted from word to 1-5           1000 rows
02:20:50 INFO    [clean] `availability` converted to number in stock        1000 rows
02:20:50 INFO    [clean] Exact duplicate rows removed                          0 rows
02:20:50 INFO    [clean] Rows with missing/unparseable values removed          0 rows
02:20:50 INFO    [clean] Duplicate UPCs removed                                0 rows
02:20:50 INFO    [clean] All validation checks passed
02:20:51 INFO    [clean] Saved 1000 clean rows to clean_books.csv, clean_books.xlsx and cleaning_report.md
```

## Output columns

| Column | Type | Example | Description |
|---|---|---|---|
| `title` | text | `A Light in the Attic` | Book title |
| `category` | text | `Poetry` | Category from the breadcrumb |
| `price` | decimal | `51.77` | Price, without currency symbol |
| `currency` | text | `GBP` | ISO currency code |
| `star_rating` | integer | `3` | Rating from 1 to 5 |
| `availability` | integer | `22` | Number of copies in stock |
| `upc` | text | `a897fe39b1053632` | Unique product code (from the product page) |
| `product_page_url` | text | `https://books.toscrape.com/catalogue/...` | Link to the product page |

## Project structure

```
├── scrape.py              # step 1: collect the raw data
├── clean.py               # step 2: clean, validate, write CSV/Excel/report
├── main.py                # runs both steps
├── tests/
│   └── test_clean.py      # pytest tests for the cleaning functions
├── data/
│   ├── raw_books.csv      # exactly as scraped
│   ├── clean_books.csv    # clean data
│   └── clean_books.xlsx   # clean data, formatted for Excel
├── cleaning_report.md     # what was fixed, with before/after examples
├── requirements.txt
└── pytest.ini
```

## How I'd adapt this for your site

The scraper and the cleaner are separate on purpose: the raw file is an exact record of what the site returned, so every cleaning rule can be checked, changed and re-run without scraping again.

- **Your fields:** every selector lives in two small functions (`get_book_urls` and `parse_book` in `scrape.py`). I map the fields you need to your page structure; the rest of the pipeline stays the same.
- **Your pagination:** "next" buttons, numbered pages, "load more" buttons or infinite scroll. Many sites load their data from a hidden JSON API; when that exists I use it, because it is faster and more reliable than parsing HTML.
- **JavaScript-heavy sites:** if the data only appears after JavaScript runs and there is no API, I switch the fetch step to Playwright and keep everything else.
- **Your cleaning rules:** local number formats (`1.299,00 €`), dates, units, category mapping, and validation rules that match your business (required fields, allowed price ranges).
- **Larger jobs:** for tens of thousands of pages I add resume-on-restart, incremental saving and a request rate agreed with you.
- **Your delivery format:** CSV, Excel, Google Sheets, a database or JSON, once or on a schedule, optionally with a "what changed since last run" report.
- **Responsible scraping:** I check robots.txt and the terms of service, keep the request rate low, and don't collect personal data or scrape behind logins without permission.

## Notes

- **The encoding issue is real, not staged.** The site doesn't declare a character set, so `requests` decodes the UTF-8 pages as ISO-8859-1 and `£` arrives as `Â£`. The scraper keeps this as-is so the raw file is honest; `clean.py` repairs it.
- The CSV files are written as UTF-8 with a BOM so they open correctly in Excel.
- `python scrape.py` or `python clean.py` runs a single step.
