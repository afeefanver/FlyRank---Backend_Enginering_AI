import pytest

from src.normalize import parse_price
from src.parser import ParseError, dedupe_urls, parse_book, parse_catalogue

PAGE = "https://books.toscrape.com/catalogue/page-1.html"


def book_html(description=True, extra_space=False):
    desc = (
        '<div id="product_description"></div><p>A good book.</p>' if description else ""
    )
    title = "  Test   Book  " if extra_space else "Test Book"
    return f"""
    <div class="product_main">
      <h1>{title}</h1>
      <p class="price_color">£12.50</p>
      <p class="availability">In stock (3 available)</p>
      <p class="star-rating Four"></p>
    </div>{desc}""".encode()


def test_price_normalization():
    assert parse_price("£51.77") == 51.77
    assert parse_price("") is None


def test_relative_to_absolute_urls():
    html = b'<article class="product_pod"><h3><a href="a-book_1/index.html"></a></h3></article>'
    urls, nxt = parse_catalogue(html, PAGE)
    assert urls == ["https://books.toscrape.com/catalogue/a-book_1/index.html"]
    assert nxt is None


def test_missing_description_is_none():
    raw = parse_book(book_html(description=False), "https://x/b", PAGE, "2026-01-01T00:00:00Z")
    assert raw["description"] is None


def test_duplicate_urls_removed():
    pairs = [("https://x/a", PAGE), ("https://x/a", PAGE), ("https://x/b", PAGE)]
    assert len(dedupe_urls(pairs)) == 2


def test_extra_whitespace_cleaned():
    raw = parse_book(book_html(extra_space=True), "https://x/b", PAGE, "2026-01-01T00:00:00Z")
    assert raw["title"] == "Test Book"


def test_missing_product_area_raises():
    # one malformed fixture: no div.product_main -> the parser must raise, not guess
    html = b"<html><body><p>nothing useful here</p></body></html>"
    with pytest.raises(ParseError):
        parse_book(html, "https://x/b", PAGE, "2026-01-01T00:00:00Z")
