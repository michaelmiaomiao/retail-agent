from bs4 import BeautifulSoup
from pathlib import Path
import json

RAW_DIR = Path("data/raw")
OUT_FILE = Path("data/processed/products_latest.json")

products = []

for html_file in RAW_DIR.glob("*.html"):
    print("Parsing:", html_file)

    html = html_file.read_text(encoding="utf8")

    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("title")

    title = title_tag.text if title_tag else "Unknown"

    products.append(
        {
            "source_file": str(html_file),
            "title": title,
            "url": "unknown"
        }
    )

OUT_FILE.parent.mkdir(exist_ok=True)

with open(OUT_FILE, "w") as f:
    json.dump(products, f, indent=2)

print("Saved:", OUT_FILE)