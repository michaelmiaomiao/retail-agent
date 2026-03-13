import json
from datetime import date
from pathlib import Path

from report_utils import render_wsl_report, write_report
from wsl_utils import diff_records, load_records

IN_DIFF = Path("data/processed/wsl_diff_latest.json")
IN_LATEST = Path("data/processed/wsl_latest.json")
OUT_DIR = Path("reports/weekly")


def fallback_diff_payload() -> dict:
    records = load_records(IN_LATEST)
    return {
        "fetch_error": "",
        "comparison": diff_records(records, []),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if IN_DIFF.exists():
        diff_payload = json.loads(IN_DIFF.read_text(encoding="utf-8"))
    elif IN_LATEST.exists():
        diff_payload = fallback_diff_payload()
    else:
        raise FileNotFoundError(f"Missing input file: {IN_DIFF} or {IN_LATEST}")

    today = date.today().isoformat()
    out = OUT_DIR / f"{today}-wsl.md"
    content = render_wsl_report(diff_payload, today=today)
    write_report(out, content)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
