import json

from pydantic import ValidationError

from src import config
from src.fetcher import Fetcher, fetched_at
from src.models import Book
from src.normalize import parse_price
from src.parser import dedupe_urls, parse_book, parse_catalogue


def discover(fetcher: Fetcher):
    pairs = []
    page_url = config.START_URL
    pages_seen = 0
    while page_url and pages_seen < config.CATALOGUE_PAGES:
        content = fetcher.get(page_url)
        book_urls, next_url = parse_catalogue(content, page_url)
        pairs.extend((u, page_url) for u in book_urls)
        pages_seen += 1
        page_url = next_url
    return pages_seen, pairs


def main():
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    fetcher = Fetcher()

    pages_seen, pairs = discover(fetcher)
    unique = dedupe_urls(pairs)
    print(f"catalogue_pages={pages_seen} discovered={len(pairs)} unique_urls={len(unique)}")

    books, errors = [], []
    for url, source_page in unique:
        content = fetcher.get(url)
        raw = parse_book(content, url, source_page, fetched_at(url))
        raw["price_gbp"] = parse_price(raw["price_text"])
        try:
            books.append(Book(**raw).model_dump())
        except ValidationError as exc:
            errors.append({"url": url, "reason": exc.errors(include_url=False, include_context=False)})

    books.sort(key=lambda b: b["product_url"])          # same order every run
    (config.OUTPUT_DIR / "books.json").write_text(
        json.dumps(books, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (config.OUTPUT_DIR / "errors.json").write_text(
        json.dumps(errors, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(f"detail_pages={len(unique)} valid={len(books)} invalid={len(errors)}")


if __name__ == "__main__":
    main()
