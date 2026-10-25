"""
Run the whole pipeline: scrape books.toscrape.com, then clean the result.

Run:  python main.py
"""

import logging

import clean
import scrape


def main() -> None:
    rows = scrape.run()
    if rows == 0:
        raise SystemExit("Nothing was scraped, so there is nothing to clean. See the log above.")
    clean.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s", datefmt="%H:%M:%S")
    main()
