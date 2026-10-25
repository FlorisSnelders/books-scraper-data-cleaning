"""
Scrape every book from https://books.toscrape.com and save the raw data.

The scraper walks all catalogue pages, visits each product page and writes
data/raw_books.csv. It deliberately does NO cleaning: every value is stored
exactly as the page returned it (whitespace, currency symbols, encoding
problems and all). Cleaning is a separate step in clean.py, so the raw file
stays an honest record of the source.

Run:  python scrape.py
"""

import csv
import logging
import random
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

START_URL = "https://books.toscrape.com/catalogue/page-1.html"
RAW_CSV = Path(__file__).resolve().parent / "data" / "raw_books.csv"

# Identify the scraper honestly so the site owner knows what is visiting
USER_AGENT = "BooksScraperDemo/1.0 (portfolio project; Python requests)"
DELAY_SECONDS = (0.5, 1.0)  # random pause before every request
TIMEOUT_SECONDS = 15

COLUMNS = ["Title", "Price", "Star Rating", "Availability", "Category", "Product Page URL", "UPC"]

log = logging.getLogger("scrape")


def make_session() -> requests.Session:
    """Create a session that sends our User-Agent and retries failed requests.

    Connection errors and 429/5xx responses are retried up to 3 times with
    exponential backoff (a Retry-After header from the server is respected).
    """
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    for prefix in ("http://", "https://"):
        session.mount(prefix, HTTPAdapter(max_retries=retries))
    return session


def fetch(session: requests.Session, url: str) -> BeautifulSoup | None:
    """Politely download a page and parse it. Returns None if it fails."""
    time.sleep(random.uniform(*DELAY_SECONDS))
    try:
        response = session.get(url, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        log.error("Giving up on %s: %s", url, exc)
        return None
    # The server sends no charset, so requests decodes the UTF-8 page as
    # ISO-8859-1 and "£" arrives as "Â£". This is a common real-world problem;
    # we keep it in the raw data and fix it in clean.py.
    return BeautifulSoup(response.text, "html.parser")


def get_book_urls(session: requests.Session) -> list[str]:
    """Follow the "next" button through the catalogue, collecting product URLs."""
    urls: list[str] = []
    page_url: str | None = START_URL
    while page_url:
        soup = fetch(session, page_url)
        if soup is None:
            log.warning("Stopping pagination early: could not load %s", page_url)
            break
        links = soup.select("article.product_pod h3 a")
        urls += [urljoin(page_url, a["href"]) for a in links]
        log.info("Catalogue %s: %d books (%d total)", page_url.rsplit("/", 1)[-1], len(links), len(urls))
        next_link = soup.select_one("li.next a")
        page_url = urljoin(page_url, next_link["href"]) if next_link else None
    return urls


def raw_text(soup: BeautifulSoup, selector: str) -> str:
    """Text of the first element matching `selector`, untouched ("" if missing)."""
    element = soup.select_one(selector)
    return element.get_text() if element else ""


def parse_book(soup: BeautifulSoup, url: str) -> dict[str, str]:
    """Extract one book's fields from its product page, without cleaning them."""
    # The star rating only exists as a CSS class: <p class="star-rating Three">
    rating = soup.select_one("div.product_main p.star-rating")
    # The breadcrumb is: Home > Books > <Category> > <Title>
    breadcrumb = soup.select("ul.breadcrumb li")
    # The "Product Information" table holds UPC, prices, tax, availability, ...
    info = {row.th.get_text(): row.td.get_text() for row in soup.select("table.table-striped tr")}

    return {
        "Title": raw_text(soup, "div.product_main h1"),
        "Price": raw_text(soup, "div.product_main p.price_color"),
        "Star Rating": rating["class"][-1] if rating else "",
        "Availability": raw_text(soup, "div.product_main p.availability"),
        "Category": breadcrumb[2].get_text() if len(breadcrumb) > 2 else "",
        "Product Page URL": url,
        "UPC": info.get("UPC", ""),
    }


def run(output: Path = RAW_CSV) -> int:
    """Scrape every book and write the raw CSV. Returns the number of rows saved."""
    log.info("Starting at %s as %r", START_URL, USER_AGENT)
    session = make_session()
    urls = get_book_urls(session)
    log.info("Found %d book pages, visiting each one...", len(urls))

    books = []
    for i, url in enumerate(urls, start=1):
        soup = fetch(session, url)
        if soup is not None:
            try:
                books.append(parse_book(soup, url))
            except Exception:  # one odd page layout shouldn't stop the whole run
                log.exception("Could not parse %s", url)
        if i % 100 == 0 or i == len(urls):
            log.info("Progress: %d/%d book pages", i, len(urls))

    output.parent.mkdir(parents=True, exist_ok=True)
    # "utf-8-sig" adds a BOM so Excel opens the file with the right encoding
    with output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(books)

    log.info("Saved %d rows to %s (%d pages failed)", len(books), output.name, len(urls) - len(books))
    return len(books)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s", datefmt="%H:%M:%S")
    run()
