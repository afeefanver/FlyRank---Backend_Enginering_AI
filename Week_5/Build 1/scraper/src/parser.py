from urllib.parse import urljoin

from bs4 import BeautifulSoup


class ParseError(Exception):
    pass


def parse_catalogue(content: bytes, page_url: str) -> tuple[list[str], str | None]:
    """Return (absolute book URLs on this page, absolute URL of the next page or None)."""
    soup = BeautifulSoup(content, "html.parser")
    book_urls = [
        urljoin(page_url, a["href"])
        for a in soup.select("article.product_pod h3 a[href]")
    ]
    next_link = soup.select_one("li.next a[href]")
    next_url = urljoin(page_url, next_link["href"]) if next_link else None
    return book_urls, next_url


def _text(element) -> str | None:
    """Clean text of an element, or None if it's missing or empty."""
    if element is None:
        return None
    cleaned = " ".join(element.get_text().split())
    return cleaned or None


def parse_book(content: bytes, product_url: str, source_page: str, fetched_at: str) -> dict:
    soup = BeautifulSoup(content, "html.parser")

    # Aim at the product area, not the whole document
    main = soup.select_one("div.product_main")
    if main is None:
        raise ParseError("product area not found")

    rating_text = None
    rating_element = main.select_one("p.star-rating")
    if rating_element is not None:
        extra = [c for c in rating_element.get("class", []) if c != "star-rating"]
        rating_text = extra[0] if extra else None

    description = None
    description_heading = soup.select_one("#product_description")
    if description_heading is not None:
        description = _text(description_heading.find_next_sibling("p"))

    return {
        "title": _text(main.select_one("h1")),
        "product_url": product_url,
        "price_text": _text(main.select_one("p.price_color")),
        "availability_text": _text(main.select_one("p.availability")),
        "rating_text": rating_text,
        "description": description,        # None when the page has no description
        "source_page": source_page,
        "fetched_at": fetched_at,          # provenance: the receipt
    }


def dedupe_urls(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """pairs are (book_url, source_page). Keep the first sighting of each book URL."""
    seen: set[str] = set()
    unique = []
    for book_url, source_page in pairs:
        if book_url not in seen:
            seen.add(book_url)
            unique.append((book_url, source_page))
    return unique
