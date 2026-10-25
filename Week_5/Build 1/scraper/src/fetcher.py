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
