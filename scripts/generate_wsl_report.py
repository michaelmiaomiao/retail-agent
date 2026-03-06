import json
from datetime import date
from pathlib import Path

IN_FILE = Path("data/processed/wsl_latest.json")
OUT_DIR = Path("reports/weekly")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not IN_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {IN_FILE}")

    items = json.loads(IN_FILE.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    out = OUT_DIR / f"{today}-wsl.md"

    lines = []
    lines.append(f"# Costco While Supplies Last Weekly Snapshot ({today})")
    lines.append("")
    lines.append(f"Total items: **{len(items)}**")
    lines.append("")

    for item in items:
        en = item.get("title_en", "") or "Unknown"
        zh = item.get("title_zh", "") or en
        url = item.get("url", "") or ""

        lines.append(f"- EN: **{en}**")
        lines.append(f"  ZH: {zh}")
        lines.append(f"  URL: {url}")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
