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
