import json
import re
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
HISTORY_DIR = PROCESSED_DIR / "history"

RAW_CARDS = RAW_DIR / "wsl_cards_latest.json"
RAW_HTML = RAW_DIR / "wsl_latest.html"
OUT_LATEST = PROCESSED_DIR / "wsl_latest.json"


_TRANSLATION_DICTIONARY = {
    "while supplies last": "售完为止",
    "online only": "仅限线上",
    "limited time": "限时",
    "set": "套装",
    "pack": "包装",
    "wireless": "无线",
    "stainless steel": "不锈钢",
    "laptop": "笔记本电脑",
    "smart tv": "智能电视",
    "vacuum": "吸尘器",
    "chair": "椅子",
    "table": "桌子",
    "sofa": "沙发",
    "coffee": "咖啡",
    "chicken": "鸡肉",
    "beef": "牛肉",
    "rice": "米",
}


def translate_title(title_en: str) -> str:
    """Simple resilient translator stub; replace with real service later."""
    text = (title_en or "").strip()
    if not text:
        return ""

    try:
        lowered = text.lower()
        translated = text

        # Longer phrases first to reduce collisions.
        for en, zh in sorted(_TRANSLATION_DICTIONARY.items(), key=lambda kv: len(kv[0]), reverse=True):
            pattern = re.compile(re.escape(en), flags=re.IGNORECASE)
            if pattern.search(lowered):
                translated = pattern.sub(zh, translated)
                lowered = translated.lower()

        return translated
    except Exception:
        return text


def load_items_from_raw_json() -> list[dict]:
    if not RAW_CARDS.exists():
        return []

    payload = json.loads(RAW_CARDS.read_text(encoding="utf-8"))
    items = payload.get("items", []) if isinstance(payload, dict) else []

    out: list[dict] = []
    for item in items:
        title = (item.get("title_en") or "").strip()
        url = (item.get("url") or "").strip()
        if title and url:
            out.append({"title_en": title, "url": url})

    return out


def load_items_from_html() -> list[dict]:
    if not RAW_HTML.exists():
        return []

    html = RAW_HTML.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")

    out: list[dict] = []
    seen: set[str] = set()

    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        title = " ".join(a.get_text(" ", strip=True).split())

        if not href or not title:
            continue

        if "costco.com" not in href and not href.startswith("/"):
            continue

        if "/product" not in href and "/p/" not in href and ".product." not in href:
            continue

        if href.startswith("/"):
            href = f"https://www.costco.com{href}"

        href = href.split("?")[0].rstrip("/")
        key = f"{title}||{href}"
        if key in seen:
            continue
        seen.add(key)

        out.append({"title_en": title, "url": href})

    return out


def build_records(items: list[dict]) -> list[dict]:
    records = []
    for item in items:
        title_en = item["title_en"].strip()
        url = item["url"].strip()
        title_zh = translate_title(title_en) or title_en

        records.append(
            {
                "title_en": title_en,
                "title_zh": title_zh,
                "url": url,
                "source": "costco_wsl",
            }
        )

    # Deterministic output for cleaner history diffs.
    records.sort(key=lambda x: (x["title_en"].lower(), x["url"]))
    return records


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    items = load_items_from_raw_json()
    if not items:
        items = load_items_from_html()

    records = build_records(items)

    OUT_LATEST.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    today = date.today().isoformat()
    history_path = HISTORY_DIR / f"wsl_{today}.json"
    history_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved latest: {OUT_LATEST}")
    print(f"Saved history: {history_path}")
    print(f"Items parsed: {len(records)}")


if __name__ == "__main__":
    main()
