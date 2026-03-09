import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

WSL_SOURCE = "costco_wsl"

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


def normalize_url(url: str) -> str:
    if not url:
        return ""
    return urljoin("https://www.costco.com", url.split("?")[0]).rstrip("/")


def clean_title(title: str) -> str:
    text = " ".join((title or "").replace("| Costco", "").split())
    return text.strip()


def canonicalize_title(title: str) -> str:
    text = clean_title(title).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def translate_title(title_en: str) -> str:
    text = clean_title(title_en)
    if not text:
        return ""

    try:
        lowered = text.lower()
        translated = text
        for en, zh in sorted(_TRANSLATION_DICTIONARY.items(), key=lambda kv: len(kv[0]), reverse=True):
            pattern = re.compile(re.escape(en), flags=re.IGNORECASE)
            if pattern.search(lowered):
                translated = pattern.sub(zh, translated)
                lowered = translated.lower()
        return translated
    except Exception:
        return text


def extract_product_id(url: str) -> str:
    match = re.search(r"/(\d+)$", normalize_url(url))
    return match.group(1) if match else ""


def make_item_key(title: str, url: str) -> str:
    product_id = extract_product_id(url)
    if product_id:
        return f"id:{product_id}"
    normalized_url = normalize_url(url)
    normalized_title = canonicalize_title(title)
    return f"url:{normalized_url}::title:{normalized_title}"


def dedupe_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()

    for item in items:
        title = clean_title(item.get("title_en", ""))
        url = normalize_url(item.get("url", ""))
        if not title or not url:
            continue

        key = make_item_key(title, url)
        if key in seen:
            continue

        seen.add(key)
        deduped.append({"title_en": title, "url": url})

    deduped.sort(key=lambda value: (canonicalize_title(value["title_en"]), value["url"]))
    return deduped


def parse_wsl_html(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html or "", "lxml")
    items: list[dict[str, str]] = []

    for anchor in soup.select("a[href]"):
        href = normalize_url(anchor.get("href") or "")
        title = clean_title(anchor.get_text(" ", strip=True))

        if not href or not title:
            continue

        if "costco.com" not in href:
            continue

        if "/product/" not in href and "/p/" not in href and ".product." not in href:
            continue

        items.append({"title_en": title, "url": href})

    return dedupe_items(items)


def load_items_from_raw_json(path: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    if not path.exists():
        return [], {}

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return [], {}

    raw_items = payload.get("items", [])
    items: list[dict[str, str]] = []
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            items.append(
                {
                    "title_en": item.get("title_en", "") or "",
                    "url": item.get("url", "") or "",
                }
            )

    return dedupe_items(items), payload


def build_records(items: list[dict[str, str]]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for item in dedupe_items(items):
        title_en = clean_title(item["title_en"])
        url = normalize_url(item["url"])
        records.append(
            {
                "title_en": title_en,
                "title_zh": translate_title(title_en) or title_en,
                "url": url,
                "source": WSL_SOURCE,
                "key": make_item_key(title_en, url),
            }
        )
    return records


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []

    records: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        title_en = clean_title(item.get("title_en", ""))
        url = normalize_url(item.get("url", ""))
        if not title_en or not url:
            continue
        record = {
            "title_en": title_en,
            "title_zh": item.get("title_zh") or translate_title(title_en) or title_en,
            "url": url,
            "source": item.get("source") or WSL_SOURCE,
            "key": item.get("key") or make_item_key(title_en, url),
        }
        records.append(record)

    return dedupe_records(records)


def dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        key = record.get("key") or make_item_key(record.get("title_en", ""), record.get("url", ""))
        if not key or key in seen:
            continue
        normalized = dict(record)
        normalized["title_en"] = clean_title(normalized.get("title_en", ""))
        normalized["url"] = normalize_url(normalized.get("url", ""))
        normalized["key"] = key
        deduped.append(normalized)
        seen.add(key)

    deduped.sort(key=lambda value: (canonicalize_title(value["title_en"]), value["url"]))
    return deduped


def load_previous_snapshot(history_dir: Path, current_snapshot: Path) -> tuple[Path | None, list[dict[str, Any]]]:
    candidates = sorted(history_dir.glob("wsl_*.json"))
    previous_candidates = [path for path in candidates if path != current_snapshot]
    if not previous_candidates:
        return None, []

    previous_path = previous_candidates[-1]
    return previous_path, load_records(previous_path)


def diff_records(
    current_records: list[dict[str, Any]], previous_records: list[dict[str, Any]]
) -> dict[str, Any]:
    current_map = {record["key"]: record for record in dedupe_records(current_records)}
    previous_map = {record["key"]: record for record in dedupe_records(previous_records)}

    new_keys = sorted(set(current_map) - set(previous_map))
    removed_keys = sorted(set(previous_map) - set(current_map))
    still_keys = sorted(set(current_map) & set(previous_map))

    return {
        "new_items": [current_map[key] for key in new_keys],
        "removed_items": [previous_map[key] for key in removed_keys],
        "still_active": [current_map[key] for key in still_keys],
        "counts": {
            "current": len(current_map),
            "previous": len(previous_map),
            "new": len(new_keys),
            "removed": len(removed_keys),
            "still_active": len(still_keys),
        },
    }
