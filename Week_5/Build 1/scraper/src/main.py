from src import config
from src.fetcher import Fetcher
from src.parser import dedupe_urls, parse_catalogue


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


if __name__ == "__main__":
    fetcher = Fetcher()
    pages_seen, pairs = discover(fetcher)
    unique = dedupe_urls(pairs)
    print(f"catalogue_pages={pages_seen} discovered={len(pairs)} unique_urls={len(unique)}")

    from src.fetcher import fetched_at
    from src.parser import parse_book
    import json

    url, source = unique[0]
    raw = parse_book(fetcher.get(url), url, source, fetched_at(url))
    print(json.dumps(raw, indent=2, ensure_ascii=False))
