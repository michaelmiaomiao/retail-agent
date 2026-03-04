import csv
import hashlib
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

WATCHLIST = "data/watchlist.csv"
RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

def safe_name(url: str) -> str:
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return f"page_{h}.html"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
})

retries = Retry(
    total=2,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
session.mount("https://", HTTPAdapter(max_retries=retries))
session.mount("http://", HTTPAdapter(max_retries=retries))

with open(WATCHLIST, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = [r for r in reader if r.get("url")]

for row in rows:
    url = row["url"].strip()
    print(f"Fetching: {url}", flush=True)

    try:
        r = session.get(url, timeout=(5, 20), allow_redirects=True)
        print(f"Status: {r.status_code}  bytes={len(r.content)}", flush=True)

        path = RAW_DIR / safe_name(url)
        path.write_bytes(r.content)
        print(f"Saved: {path}", flush=True)

    except requests.exceptions.Timeout:
        print("ERROR: timeout (connect 5s / read 20s).", flush=True)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", flush=True)

    time.sleep(1)
