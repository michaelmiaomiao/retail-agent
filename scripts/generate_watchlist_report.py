import json
from datetime import date
from pathlib import Path

IN_FILE = Path("data/processed/watchlist_latest.json")
OUT_DIR = Path("reports/weekly")


def main() -> None:
    if not IN_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {IN_FILE}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    items = json.loads(IN_FILE.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    out = OUT_DIR / f"{today}-watchlist.md"

    lines = []
    lines.append(f"# Costco Watchlist Weekly Snapshot ({today})")
    lines.append("")
    lines.append(f"Total items: **{len(items)}**")
    lines.append("")

    for item in items:
        en = item.get("title_en", "Unknown")
        zh = item.get("title_zh", en)
        url = item.get("url", "")

        lines.append(f"- 中文: **{zh}**")
        lines.append(f"  English: {en}")
        lines.append(f"  URL: {url}")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
