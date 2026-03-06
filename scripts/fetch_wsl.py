import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

WSL_URL = "https://www.costco.com/s?keyword=whilesupplieslast&COSTID=WSL_Homepage"
FALLBACK_URLS = [
    WSL_URL,
    "https://www.costco.com/s?keyword=while%20supplies%20last",
]
RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)


# Broad selector set to handle Costco DOM variation on listing pages.
PRODUCT_LINK_SELECTORS = [
    "a[data-testid='productTile-link']",
    "div.product-tile-set a[href*='/p/']",
    "a[href*='.product.']",
    "a[href*='/wcsstore/']",
    "a[href*='costco.com/']",
]


def normalize_url(url: str) -> str:
    if not url:
        return ""
    return urljoin("https://www.costco.com", url.split("?")[0]).rstrip("/")


def extract_cards(page) -> list[dict]:
    cards: list[dict] = []

    script = """
() => {
  const selectors = arguments[0];
  const out = [];
  const seen = new Set();

  for (const sel of selectors) {
    const nodes = document.querySelectorAll(sel);
    for (const n of nodes) {
      const href = n.getAttribute('href') || '';
      const txt = (n.textContent || '').trim().replace(/\\s+/g, ' ');
      if (!href || !txt) continue;
      const key = href + '||' + txt;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({ title_en: txt, url: href });
    }
  }
  return out;
}
"""

    raw_cards = page.evaluate(script, PRODUCT_LINK_SELECTORS)

    seen_urls: set[str] = set()
    for c in raw_cards:
        title = (c.get("title_en") or "").strip()
        url = normalize_url((c.get("url") or "").strip())

        if not title or not url:
            continue

        if "costco.com" not in url:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)
        cards.append({"title_en": title, "url": url})

    return cards


def main() -> None:
    now = datetime.now()
    stamp = now.strftime("%Y%m%d_%H%M%S")
    fetch_error = ""

    html_latest = RAW_DIR / "wsl_latest.html"
    cards_latest = RAW_DIR / "wsl_cards_latest.json"
    html_snapshot = RAW_DIR / f"wsl_{stamp}.html"
    cards_snapshot = RAW_DIR / f"wsl_cards_{stamp}.json"

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright is not installed. Run: pip install playwright && playwright install chromium")
        raise

    with sync_playwright() as p:
        html = ""
        cards: list[dict] = []
        last_error = None

        browser_types = [("chromium", p.chromium)]

        for browser_name, browser_type in browser_types:
            browser = browser_type.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
                ),
                locale="en-US",
            )
            page = context.new_page()

            try:
                for url in FALLBACK_URLS:
                    print(f"[{browser_name}] Opening: {url}")
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                    except Exception as exc:
                        last_error = exc
                        continue

                    # Wait for either products or a stable idle state, then scroll once to trigger lazy rendering.
                    try:
                        page.wait_for_selector(", ".join(PRODUCT_LINK_SELECTORS), timeout=30_000)
                    except Exception:
                        pass

                    page.mouse.wheel(0, 4000)
                    page.wait_for_timeout(2_000)

                    html = page.content()
                    cards = extract_cards(page)
                    if cards:
                        break

                if html:
                    print(f"[{browser_name}] Page captured. Extracted {len(cards)} items.")
                    break
            except Exception as exc:
                last_error = exc
            finally:
                browser.close()

        if not html:
            fetch_error = str(last_error) if last_error else "unknown_error"
            html = (
                "<html><body><h1>WSL fetch failed</h1>"
                f"<p>{fetch_error}</p></body></html>"
            )
            cards = []

    html_latest.write_text(html, encoding="utf-8")
    html_snapshot.write_text(html, encoding="utf-8")

    cards_payload = {
        "source": "costco_wsl",
        "url": WSL_URL,
        "fetched_at": now.isoformat(timespec="seconds"),
        "items": cards,
    }
    if fetch_error:
        cards_payload["fetch_error"] = fetch_error

    cards_latest.write_text(json.dumps(cards_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    cards_snapshot.write_text(json.dumps(cards_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved HTML: {html_latest}")
    print(f"Saved HTML snapshot: {html_snapshot}")
    print(f"Saved cards: {cards_latest}")
    print(f"Saved cards snapshot: {cards_snapshot}")
    print(f"Items extracted: {len(cards)}")
    if fetch_error:
        print(f"WARNING: fetch fallback used due to error: {fetch_error}")


if __name__ == "__main__":
    main()
