# A9: The Polite Scraper

Download three catalogue pages from the Books to Scrape sandbox, visit all 60 book pages, turn messy HTML into clean, validated JSON, survive a broken page, and finish with an honest run report.

**Assumptions in this guide (change them if they're wrong):**

- Python lane: `requests`, Beautiful Soup (`beautifulsoup4`) and Pydantic v2.
- You work in a `scraper/` folder inside your internship repo.
- The only site you touch is `books.toscrape.com`, a sandbox built for scraping practice.

If you use Node, keep the stages, the file names and the checkpoints, and swap in `fetch`, Cheerio and Zod. Tell me and I'll write that version.

---

## The pipeline

```
classify -> fetch (+cache) -> extract -> normalize -> validate -> store -> report
```

Each step produces proof you can look at: a README note, a saved HTML file, raw fields, clean numbers, a schema check, `books.json`, and `run-report.json`.

## Target layout

```
scraper/
├── src/
│   ├── __init__.py
│   ├── config.py       # constants: user-agent, delay, timeout, URLs
│   ├── fetcher.py      # polite fetching, cache, retry-once
│   ├── parser.py       # HTML -> raw fields
│   ├── normalize.py    # "£51.77" -> 51.77
│   ├── models.py       # Pydantic schema
│   └── main.py         # runs the whole pipeline
├── tests/
│   └── test_parser.py  # optional stretch: 5 unit tests
├── cache/              # saved HTML (git-ignored)
├── output/             # books.json, errors.json, run-report.json
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Stage 0: Check before you collect

1. Create the folder and the empty files:

```bash
mkdir -p scraper/src scraper/tests scraper/output && cd scraper
touch README.md .gitignore src/__init__.py
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install requests beautifulsoup4 pydantic pytest
pip freeze > requirements.txt
```

2. `.gitignore`:

```
.venv/
__pycache__/
*.pyc
cache/
```

3. Open https://toscrape.com in your browser and read what the site says about itself. It states that Books to Scrape is a sandbox for practising scraping. That is your permission.

4. Request the robots file **once** and write down exactly what happened:

```bash
curl -i https://books.toscrape.com/robots.txt
```

If the file is missing, write "no robots file found". A missing file is not permission. It is just a missing file. The permission comes from the sandbox statement.

5. Add this to your README (fill in the robots result with what you actually saw):

```markdown
## Target classification

- **Site:** https://books.toscrape.com, a sandbox built for scraping practice.
- **Scope:** the first 3 catalogue pages (60 books) and each book's detail page.
- **Data collected:** title, URL, price, availability, star rating, description.
- **robots.txt:** [what you saw, e.g. "request returned 404, no robots file found"]
- **Why this is appropriate:** the site exists so people can practise scraping on it.

I will not reuse this code on another site without checking its rules and terms first.
```

**Checkpoint:** the README names the target, the three-page scope, the robots result, and that last sentence.

```bash
git add . && git commit -m "Stage 0: classify scraping target"
```

---

## Stage 1: Fetch once, cache once

### `src/config.py`

```python
from pathlib import Path

BASE_URL = "https://books.toscrape.com/"
START_URL = "https://books.toscrape.com/catalogue/page-1.html"
CATALOGUE_PAGES = 3

# Honest identity: replace the link with your real repo URL
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/YOUR-USERNAME/YOUR-REPO)"

TIMEOUT_SECONDS = 10
MIN_DELAY_SECONDS = 0.6   # the rule is at least 0.5 s between real requests
RETRY_WAIT_SECONDS = 2

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT / "output"
```

### `src/fetcher.py`

```python
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from src import config


class FetchError(Exception):
    pass


def cache_path(url: str) -> Path:
    # "/catalogue/page-1.html" -> cache/catalogue-page-1.html
    name = urlparse(url).path.strip("/").replace("/", "-")
    return config.CACHE_DIR / name


def fetched_at(url: str) -> str:
    """When the saved copy was downloaded. This is the record's provenance."""
    mtime = cache_path(url).stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Fetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = config.USER_AGENT
        self._last_request = 0.0
        self.stats = Counter()

    def get(self, url: str) -> bytes:
        path = cache_path(url)
        if path.exists():
            data = path.read_bytes()
            self.stats["cache_hits"] += 1
            print(f"CACHE HIT {url} ({len(data)} bytes)")
            return data

        data = self._fetch_with_retry(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.stats["pages_fetched"] += 1
        print(f"FETCH     {url} ({len(data)} bytes)")
        return data

    def _wait_politely(self):
        elapsed = time.monotonic() - self._last_request
        if elapsed < config.MIN_DELAY_SECONDS:
            time.sleep(config.MIN_DELAY_SECONDS - elapsed)

    def _fetch_with_retry(self, url: str) -> bytes:
        last_problem = "unknown error"
        for attempt in (1, 2):
            self._wait_politely()
            try:
                response = self.session.get(url, timeout=config.TIMEOUT_SECONDS)
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_problem = f"{type(exc).__name__}"
            else:
                self._last_request = time.monotonic()
                if response.status_code == 200:
                    return response.content
                last_problem = f"HTTP {response.status_code}"
                # 404 and 403 are final answers. Only 5xx is worth one more try.
                if response.status_code < 500:
                    raise FetchError(last_problem)
            self._last_request = time.monotonic()
            if attempt == 1:
                time.sleep(config.RETRY_WAIT_SECONDS)
        raise FetchError(last_problem)
```

Only a status `200` is ever cached or parsed. We save the raw bytes (`response.content`) and let Beautiful Soup read the encoding, so `£` doesn't turn into `Â£`.

### Try it

Create a throwaway `src/main.py` for this stage:

```python
from src import config
from src.fetcher import Fetcher

fetcher = Fetcher()
fetcher.get(config.START_URL)
```

```bash
python -m src.main     # prints FETCH ...
python -m src.main     # prints CACHE HIT ...
ls cache
```

**Checkpoint:** the first run prints `FETCH` and creates `cache/catalogue-page-1.html`. The second prints `CACHE HIT`. Neither dumps the HTML to the terminal.

```bash
git add . && git commit -m "Stage 1: fetch and cache HTML"
```

---

## Stage 2: Find all three pages

### `src/parser.py` (the discovery half)

```python
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


def dedupe_urls(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """pairs are (book_url, source_page). Keep the first sighting of each book URL."""
    seen: set[str] = set()
    unique = []
    for book_url, source_page in pairs:
        if book_url not in seen:
            seen.add(book_url)
            unique.append((book_url, source_page))
    return unique
```

Always use `urljoin` and never glue strings. Always start from `/catalogue/page-1.html`, because the home page uses different relative links.

### `src/main.py` (discovery)

```python
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
```

**Checkpoint:** it prints `catalogue_pages=3 discovered=60 unique_urls=60`. A second run prints the same numbers, with `CACHE HIT` lines.

```bash
git add . && git commit -m "Stage 2: discover three catalogue pages"
```

---

## Stage 3: Extract the raw records

Add to `src/parser.py`:

```python
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
```

A missing description stays `None`. Never invent text.

Temporary test in `src/main.py` (bottom of the `__main__` block):

```python
from src.fetcher import fetched_at
from src.parser import parse_book
import json

url, source = unique[0]
raw = parse_book(fetcher.get(url), url, source, fetched_at(url))
print(json.dumps(raw, indent=2, ensure_ascii=False))
```

**Checkpoint:** one complete raw record with all eight keys, even when a value is `null`. After you wire up the loop in the next stage, the summary shows `detail_pages=60`.

```bash
git add . && git commit -m "Stage 3: extract book details"
```

---

## Stage 4: Clean it, check it, store it

### `src/normalize.py`

```python
import re


def parse_price(price_text: str | None) -> float | None:
    """'£51.77' -> 51.77. Returns None if no number is found."""
    if not price_text:
        return None
    match = re.search(r"\d+(?:\.\d+)?", price_text)
    return float(match.group()) if match else None
```

### `src/models.py`

```python
from pydantic import BaseModel, Field, field_validator

VALID_RATINGS = {"One", "Two", "Three", "Four", "Five"}


class Book(BaseModel):
    title: str = Field(min_length=1)
    product_url: str
    price_text: str
    price_gbp: float = Field(gt=0)
    availability_text: str
    rating_text: str
    description: str | None = None        # the only optional field
    source_page: str
    fetched_at: str

    @field_validator("product_url", "source_page")
    @classmethod
    def must_be_https(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("URL must start with https://")
        return value

    @field_validator("rating_text")
    @classmethod
    def must_be_known_rating(cls, value: str) -> str:
        if value not in VALID_RATINGS:
            raise ValueError(f"unknown rating: {value}")
        return value
```

### Update `src/main.py` into the full pipeline

(Stage 5 adds the failure handling and report. This is the Stage 4 version of the loop.)

```python
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
```

The `books.json` file is overwritten on each run and keyed by canonical URL, so running twice gives the same 60 records, not 120. That property is idempotency.

**Checkpoint:**

```bash
python -m src.main
python -c "import json; b=json.load(open('output/books.json')); print(len(b), all(isinstance(x['price_gbp'], float) for x in b), all(x['product_url'].startswith('https://') for x in b))"
# expect: 60 True True

python -m src.main    # run again
python -c "import json; print(len(json.load(open('output/books.json'))))"
# still 60
```

```bash
git add . && git commit -m "Stage 4: validate normalized records"
```

---

## Stage 5: One bad page must not kill the run

Replace `main()` with a version that handles each page separately and writes a report.

```python
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
```

What this does:

- Each page sits inside its own `try`, so one failure is logged and the loop continues.
- A timeout or 5xx is retried once (in `fetcher.py`). A 404 or 403 is never retried.
- The report is written at the end of every run, so a silent failure can't hide.
- You test failure on your side only, with a made-up URL. Never test it by hammering the real site.

**Checkpoint:**

```bash
python -m src.main --inject-bad
```

The run finishes, `books.json` still has 60 records, and `output/run-report.json` shows `"failed_pages": 1`.

```bash
git add . && git commit -m "Stage 5: survive failures, report the run"
```

Keep it simple here. The production version of retries and logging is next week's assignment.

---

## Stage 6: Publish the evidence

1. Make sure `cache/` is git-ignored, but commit `output/` as one sample result.
2. Run `python -m src.main` one last time (without `--inject-bad`) so the committed report is clean.
3. Finish the README (template below).
4. Push to a public GitHub repo, then clone it fresh into another folder and run it to confirm a stranger can.

### README template

````markdown
# The Polite Scraper

A small scraping pipeline that downloads the first 3 catalogue pages of Books to Scrape,
visits all 60 book pages, and turns the messy HTML into clean, validated JSON, with a
report at the end of every run.

## Target classification

(paste your Stage 0 section here, including the robots.txt result)

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

Outputs: `output/books.json`, `output/errors.json`, `output/run-report.json`.
Language: Python 3.10+ (requests, Beautiful Soup, Pydantic).

## Record schema

| Field | Type | Notes |
|---|---|---|
| title | string | required |
| product_url | string | absolute https URL, the record's identity |
| price_text | string | original text, e.g. "£51.77" |
| price_gbp | number | cleaned value, must be > 0 |
| availability_text | string | e.g. "In stock (22 available)" |
| rating_text | string | One to Five |
| description | string or null | the only optional field |
| source_page | string | the catalogue page the link came from |
| fetched_at | string | when the saved copy was downloaded (provenance) |

## Politeness rules

- Honest user-agent that names me and links to this repo
- Timeout of 10 seconds on every request
- At least 0.6 seconds between real requests
- Status code checked before parsing; only 200 is parsed
- Pages are cached in `cache/`, so development doesn't re-request the site
- One retry for a timeout or 5xx. Never retry a 404 or 403

## Proof of a run

```json
<paste a real output/run-report.json here>
```

## Why no browser was needed

The data is already in the HTML the server sends, so a browser would only add cost.

## Limitation

[One honest limitation, e.g. "it only reads the first three pages and depends on the site's current HTML structure, so a redesign would break the selectors."]

## Ethics note

[In your own words: use an official API when one exists, never bypass logins, paywalls or
blocks, and collect only what you need.]
````

**Checkpoint:** a stranger can clone the repo, run one command, and get `books.json` and `run-report.json` in under 5 minutes. `git log --oneline` shows 7 or more stage commits.

```bash
git add . && git commit -m "Stage 6: publish scraper evidence"
git push
```

---

## Optional: unit tests (stretch)

`tests/test_parser.py` covers five things without touching the network:

```python
from src.normalize import parse_price
from src.parser import dedupe_urls, parse_book, parse_catalogue

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
```

Run them with `pytest` from the `scraper/` folder (add an empty `tests/__init__.py` or run `python -m pytest`). For the "one malformed fixture" requirement, add a sixth test that passes HTML with no `div.product_main` and expects `ParseError`.

---

## Bonus: the AI rematch

1. Write your own prompt asking an AI to build the same scraper, without copying from this guide. Specify: the target and three-page scope, the eight raw fields, the clean schema, caching, the delay, the user-agent, the timeout, the validation rule, no duplicates, what happens on a broken page, the run report, and your language.
2. Put the AI's version in `ai-version/` (or a branch).
3. Test it against your own checkpoints: does it collect all 60? Does a rerun duplicate them? Does one bad page crash it?
4. Diff it, then write an "AI vs me" README section:
   - What did it do better, and do you understand that code?
   - What did it get wrong or silently skip (no delay, no timeout, retrying a 404, `Â£` encoding, no cache)?
   - What did your prompt forget to say?
5. Improve the prompt, regenerate once, and note what changed.

```bash
git add . && git commit -m "Bonus: AI vs me"
```

---

## Final checklist

- [ ] One documented command processes exactly 3 catalogue pages and finds 60 unique book URLs
- [ ] Every detail page gives the eight raw fields plus a numeric `price_gbp`
- [ ] Records are validated before storage, and failures land in `errors.json` with a reason
- [ ] `books.json` has exactly 60 records after the first run and after a rerun
- [ ] Every real request has a user-agent, a timeout, a delay of at least 500 ms, and a status check
- [ ] The README documents the target classification and robots result
- [ ] A made-up bad URL is logged and skipped, and the run still finishes
- [ ] `run-report.json` shows counts, failures, cache hits and duration
- [ ] Public repo with 7 or more meaningful commits and a README a stranger can run in 5 minutes

## Troubleshooting

| Problem | Fix |
|---|---|
| Price shows `Â£51.77` | You decoded with the wrong encoding. Parse the raw bytes (`response.content`), as in this guide, not `response.text`. |
| Book links return 404 | You built them by gluing strings, or started from the home page. Use `urljoin` and start from `/catalogue/page-1.html`. |
| Only 20 books are found | The loop stopped after page 1. Check `li.next a` is read and `page_url` is updated. |
| `books.json` has 120 records after a rerun | You appended instead of overwriting, or didn't dedupe by `product_url`. |
| Every run hits the site again | The cache file name changes between runs, or `cache/` is created in the wrong folder. |
| `ModuleNotFoundError: src` | Run from inside `scraper/` with `python -m src.main`, and make sure `src/__init__.py` exists. |
| Description is `None` for every book | The selector points at the wrong element. The text sits in the `<p>` right after `#product_description`. |
| The injected bad URL crashes the run | You didn't catch `FetchError` per page. Keep the `try` inside the loop. |
