import json
import re
from datetime import date
from pathlib import Path

IN_FILE = Path("data/processed/products_latest.json")
OUT_FILE = Path("data/processed/watchlist_latest.json")
HISTORY_DIR = Path("data/processed/history")

_TRANSLATIONS = {
    "kirkland signature": "柯克兰",
    "baby wipes": "婴儿湿巾",
    "fragrance free": "无香型",
    "crest": "佳洁士",
    "mouthwash": "漱口水",
    "advanced": "高级",
    "kleenex": "舒洁",
    "facial tissue": "面巾纸",
    "trusted care": "柔护系列",
    "paper towels": "厨房纸巾",
    "bath tissue": "卷纸",
    "charmin": "舒洁棉柔",
    "cottonelle": "棉柔乐",
    "flushable wipes": "可冲散湿厕纸",
    "fresh care": "清新护理",
    "2-ply": "2层",
    "3-pack": "3包装",
    "10-pack": "10包装",
    "30-rolls": "30卷",
    "12 individually wrapped rolls": "12卷独立包装",
    "560 wipes": "560片",
    "900-count": "900片",
}


def translate_title(title_en: str) -> str:
    text = (title_en or "").replace("| Costco", "").strip()
    if not text:
        return ""

    translated = text
    lowered = translated.lower()

    # Longer phrase first to reduce overlap.
    for en, zh in sorted(_TRANSLATIONS.items(), key=lambda kv: len(kv[0]), reverse=True):
        pattern = re.compile(re.escape(en), flags=re.IGNORECASE)
        if pattern.search(lowered):
            translated = pattern.sub(zh, translated)
            lowered = translated.lower()

    return translated


def normalize_record(item: dict) -> dict:
    title_en = (item.get("title") or "").strip()
    url = (item.get("url") or "").strip()

    if not title_en or not url:
        return {}

    title_zh = translate_title(title_en) or title_en

    return {
        "title_en": title_en,
        "title_zh": title_zh,
        "url": url,
        "source": "costco_watchlist",
    }


def main() -> None:
    if not IN_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {IN_FILE}")

    products = json.loads(IN_FILE.read_text(encoding="utf-8"))

    records = []
    seen = set()
    for item in products:
        r = normalize_record(item)
        if not r:
            continue
        key = (r["title_en"], r["url"])
        if key in seen:
            continue
        seen.add(key)
        records.append(r)

    records.sort(key=lambda x: x["title_en"].lower())

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    OUT_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    today = date.today().isoformat()
    hist = HISTORY_DIR / f"watchlist_{today}.json"
    hist.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Saved latest: {OUT_FILE}")
    print(f"Saved history: {hist}")
    print(f"Items parsed: {len(records)}")


if __name__ == "__main__":
    main()
