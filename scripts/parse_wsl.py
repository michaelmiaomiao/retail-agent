import json
from datetime import datetime
from pathlib import Path

from wsl_utils import build_records, diff_records, load_items_from_raw_json, load_previous_snapshot, parse_wsl_html

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
HISTORY_DIR = PROCESSED_DIR / "history"

RAW_CARDS = RAW_DIR / "wsl_cards_latest.json"
RAW_HTML = RAW_DIR / "wsl_latest.html"
OUT_LATEST = PROCESSED_DIR / "wsl_latest.json"
OUT_DIFF = PROCESSED_DIR / "wsl_diff_latest.json"


def load_items() -> tuple[list[dict[str, str]], dict]:
    items, raw_payload = load_items_from_raw_json(RAW_CARDS)
    if items:
        return items, raw_payload

    if RAW_HTML.exists():
        html = RAW_HTML.read_text(encoding="utf-8", errors="ignore")
        return parse_wsl_html(html), raw_payload

    return [], raw_payload


def snapshot_stamp(raw_payload: dict) -> str:
    fetched_at = raw_payload.get("fetched_at") if isinstance(raw_payload, dict) else None
    if fetched_at:
        try:
            parsed = datetime.fromisoformat(str(fetched_at))
            return parsed.strftime("%Y%m%d_%H%M%S")
        except ValueError:
            pass
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    items, raw_payload = load_items()
    records = build_records(items)

    OUT_LATEST.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    history_path = HISTORY_DIR / f"wsl_{snapshot_stamp(raw_payload)}.json"
    history_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    previous_path, previous_records = load_previous_snapshot(HISTORY_DIR, history_path)
    comparison = diff_records(records, previous_records)
    diff_payload = {
        "source": raw_payload.get("source") if isinstance(raw_payload, dict) else "costco_wsl",
        "url": raw_payload.get("url") if isinstance(raw_payload, dict) else "",
        "fetched_at": raw_payload.get("fetched_at") if isinstance(raw_payload, dict) else "",
        "fetch_error": raw_payload.get("fetch_error") if isinstance(raw_payload, dict) else "",
        "current_snapshot": str(history_path),
        "previous_snapshot": str(previous_path) if previous_path else "",
        "comparison": comparison,
    }
    OUT_DIFF.write_text(json.dumps(diff_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved latest: {OUT_LATEST}")
    print(f"Saved history: {history_path}")
    print(f"Saved diff: {OUT_DIFF}")
    print(f"Items parsed: {len(records)}")
    if diff_payload["fetch_error"]:
        print(f"WARNING: fetch warning preserved: {diff_payload['fetch_error']}")


if __name__ == "__main__":
    main()
