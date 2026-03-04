import json
from pathlib import Path
from datetime import date

IN_FILE = Path("data/processed/products_latest.json")
OUT_DIR = Path("reports/weekly")

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    products = json.loads(IN_FILE.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    out = OUT_DIR / f"{today}.md"

    lines = []
    lines.append(f"# Weekly Retail Report — {today}\n")
    lines.append(f"Items parsed: **{len(products)}**\n")

    for p in products:
        title = p.get("title", "Unknown")
        src = p.get("source_file", "")
        lines.append(f"- **{title}**  \n  _{src}_")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Saved:", out)

if __name__ == "__main__":
    main()
