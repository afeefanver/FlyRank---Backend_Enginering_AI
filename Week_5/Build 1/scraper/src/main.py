import argparse
import json
import time
from datetime import datetime, timezone

from pydantic import ValidationError

from src import config
from src.fetcher import FetchError, Fetcher, fetched_at
from src.models import Book
from src.normalize import parse_price
from src.parser import ParseError, dedupe_urls, parse_book, parse_catalogue

BAD_URL = "https://books.toscrape.com/catalogue/this-book-does-not-exist_9999/index.html"


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--inject-bad", action="store_true",
                        help="add one made-up book URL to prove a bad page doesn't kill the run")
    args = parser.parse_args()

    started = time.monotonic()
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    fetcher = Fetcher()

    pages_seen, pairs = discover(fetcher)
    unique = dedupe_urls(pairs)
    print(f"catalogue_pages={pages_seen} discovered={len(pairs)} unique_urls={len(unique)}")

    if args.inject_bad:
        unique.append((BAD_URL, config.START_URL))

    books, errors, failed_pages = [], [], []
    for url, source_page in unique:
        try:
            content = fetcher.get(url)
            raw = parse_book(content, url, source_page, fetched_at(url))
            raw["price_gbp"] = parse_price(raw["price_text"])
            books.append(Book(**raw).model_dump())
        except ValidationError as exc:
            errors.append({"url": url, "reason": exc.errors(include_url=False, include_context=False)})
        except (FetchError, ParseError) as exc:
            failed_pages.append({"url": url, "reason": str(exc)})
            print(f"FAILED    {url} ({exc})")

    books.sort(key=lambda b: b["product_url"])
    (config.OUTPUT_DIR / "books.json").write_text(
        json.dumps(books, indent=2, ensure_ascii=False), encoding="utf-8")
    (config.OUTPUT_DIR / "errors.json").write_text(
        json.dumps(errors, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    report = {
        "started_at": started_at,
        "duration_seconds": round(time.monotonic() - started, 2),
        "pages_fetched": fetcher.stats["pages_fetched"],
        "cache_hits": fetcher.stats["cache_hits"],
        "valid_records": len(books),
        "invalid_records": len(errors),
        "failed_pages": len(failed_pages),
        "failed_details": failed_pages,
    }
    (config.OUTPUT_DIR / "run-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
