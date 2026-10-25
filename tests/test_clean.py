"""Tests for the cleaning functions in clean.py. Run with: pytest"""

import pandas as pd
import pytest

from clean import (
    clean_books,
    fix_encoding,
    normalize_whitespace,
    parse_availability,
    parse_currency,
    parse_price,
    parse_rating,
    to_snake_case,
)


def test_fix_encoding_repairs_mojibake():
    assert fix_encoding("Â£51.77") == "£51.77"
    assert fix_encoding("Itâ\x80\x99s") == "It’s"


@pytest.mark.parametrize("text", ["A Light in the Attic", "Café", "It’s", ""])
def test_fix_encoding_leaves_clean_text_alone(text):
    assert fix_encoding(text) == text


def test_normalize_whitespace():
    assert normalize_whitespace("\n\n    \n        In stock (22 available)\n    \n") == "In stock (22 available)"
    assert normalize_whitespace("  Too   many\tspaces ") == "Too many spaces"


@pytest.mark.parametrize("text, expected", [("£51.77", 51.77), ("$1,299.00", 1299.0), ("€5", 5.0), ("free", None)])
def test_parse_price(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize("text, expected", [("£51.77", "GBP"), ("$10.00", "USD"), ("€5", "EUR"), ("51.77", None)])
def test_parse_currency(text, expected):
    assert parse_currency(text) == expected


@pytest.mark.parametrize("text, expected", [("One", 1), ("Three", 3), ("five", 5), (" Four ", 4), ("Zero", None), ("", None)])
def test_parse_rating(text, expected):
    assert parse_rating(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [("In stock (22 available)", 22), ("In stock (1 available)", 1), ("Out of stock", 0), ("In stock", None)],
)
def test_parse_availability(text, expected):
    assert parse_availability(text) == expected


@pytest.mark.parametrize(
    "name, expected",
    [("Product Page URL", "product_page_url"), ("Star Rating", "star_rating"), ("UPC", "upc"), (" Title ", "title")],
)
def test_to_snake_case(name, expected):
    assert to_snake_case(name) == expected


def raw_row(changes: dict | None = None) -> dict:
    """One row shaped like scrape.py's output (messy, as scraped), with optional changes."""
    row = {
        "Title": "A Light in the Attic",
        "Price": "Â£51.77",
        "Star Rating": "Three",
        "Availability": "\n\n    \n        In stock (22 available)\n    \n",
        "Category": "\nPoetry\n",
        "Product Page URL": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        "UPC": "a897fe39b1053632",
    }
    return row | (changes or {})


def test_clean_books_end_to_end():
    raw = pd.DataFrame([
        raw_row(),
        raw_row(),  # exact duplicate -> removed
        raw_row({"Title": "Itâ\x80\x99s Only the Himalayas", "UPC": "b2", "Star Rating": "Two"}),
        raw_row({"UPC": "c3", "Star Rating": ""}),  # missing rating -> removed
    ])

    clean, issues = clean_books(raw)

    assert list(clean.columns) == [
        "title", "category", "price", "currency", "star_rating", "availability", "upc", "product_page_url",
    ]
    assert list(clean["upc"]) == ["a897fe39b1053632", "b2"]
    first = clean.iloc[0]
    assert first["price"] == 51.77 and first["currency"] == "GBP"
    assert first["star_rating"] == 3 and first["availability"] == 22
    assert first["category"] == "Poetry"
    assert clean.iloc[1]["title"] == "It’s Only the Himalayas"
    assert pd.api.types.is_integer_dtype(clean["star_rating"])

    rows_affected = {issue["issue"]: issue["rows"] for issue in issues}
    assert rows_affected["Exact duplicate rows removed"] == 1
    assert rows_affected["Rows with missing/unparseable values removed"] == 1


def test_clean_books_refuses_to_deliver_empty_data():
    raw = pd.DataFrame([raw_row({"Price": "no price"})])  # unparseable -> dropped -> nothing left
    with pytest.raises(ValueError, match="Data is not empty"):
        clean_books(raw)
