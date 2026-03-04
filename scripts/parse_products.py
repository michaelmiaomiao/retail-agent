import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Optional

RAW_DIR = Path("data/raw")
OUT_FILE = Path("data/processed/products_latest.json")


def extract_price(html: str) -> Optional[str]:
    """
    Costco PDP price is usually embedded in Next.js payload (self.__next_f.push)
    and/or productDetailsData JSON, not JSON-LD.
    We'll look for common price keys and pick the most plausible USD price.
    """

    def fmt(x: float) -> str:
        return f"${x:.2f}"

    def is_reasonable(x: float) -> bool:
        # Adjust if needed. This avoids $1.03, $0.99, etc.
        return 5.0 <= x <= 10000.0

    candidates: list[float] = []

    # --- A) Prefer explicit "displayPrice" (often already like "$23.99") ---
    for s in re.findall(r'"displayPrice"\s*:\s*"\$([0-9]{1,4}(?:,[0-9]{3})*(?:\.[0-9]{2})?)"', html):
        try:
            p = float(s.replace(",", ""))
            if is_reasonable(p):
                candidates.append(p)
        except:
            pass

    # --- B) "price" fields near USD currency markers in embedded JSON blobs ---
    # Example patterns observed: "priceCurrency":"USD"... "price":"23.99"
    for m in re.finditer(
        r'"priceCurrency"\s*:\s*"USD".{0,300}?"price"\s*:\s*"?(\d+(?:\.\d+)?)"?',
        html,
        flags=re.DOTALL,
    ):
        try:
            p = float(m.group(1))
            if is_reasonable(p):
                candidates.append(p)
        except:
            pass

    # --- C) Costco sometimes uses "value" + "currencyCode" around price objects ---
    for m in re.finditer(
        r'"currencyCode"\s*:\s*"USD".{0,200}?"value"\s*:\s*"?(\d+(?:\.\d+)?)"?',
        html,
        flags=re.DOTALL,
    ):
        try:
            p = float(m.group(1))
            if is_reasonable(p):
                candidates.append(p)
        except:
            pass

    # --- D) Fallback: any "$xx.xx" token BUT ONLY if it appears close to "USD" or "display" or "Price" ---
    # This reduces the chance of grabbing random marketing numbers.
    for m in re.finditer(r'\$([0-9]{1,4}(?:,[0-9]{3})*(?:\.[0-9]{2})?)', html):
        try:
            p = float(m.group(1).replace(",", ""))
        except:
            continue
        if not is_reasonable(p):
            continue

        window = html[max(0, m.start() - 200) : m.end() + 200].lower()
        if ("usd" in window) or ("displayprice" in window) or ("price" in window):
            candidates.append(p)

    if not candidates:
        return None

    # Heuristic: Costco PDP real price is usually the "median-ish" or most frequent,
    # not the max/min. We'll pick the most common rounded-to-cent value.
    from collections import Counter
    c = Counter([round(x, 2) for x in candidates])
    best, _ = c.most_common(1)[0]
    return fmt(best)


def extract_url(soup):

    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})

    for s in scripts:

        txt = s.get_text()

        if '"@type":"Product"' in txt:

            m = re.search(r'"url":"([^"]+)"', txt)

            if m:
                return m.group(1)

    return "unknown"


def parse_file(path):

    html = path.read_text(encoding="utf-8", errors="ignore")

    soup = BeautifulSoup(html, "lxml")

    title = soup.title.get_text(strip=True) if soup.title else "unknown"

    url = extract_url(soup)

    price = extract_price(html)

    return {
        "source_file": str(path),
        "title": title,
        "url": url,
        "currency": "USD",
        "price": price,
    }


def main():

    items = []

    for f in RAW_DIR.glob("page_*.html"):

        print("Parsing:", f)

        items.append(parse_file(f))

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    OUT_FILE.write_text(json.dumps(items, indent=2))

    print("Saved:", OUT_FILE)


if __name__ == "__main__":
    main()