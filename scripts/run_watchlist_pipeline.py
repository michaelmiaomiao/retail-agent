import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

STEPS = [
    [PYTHON, "scripts/fetch_products.py"],
    [PYTHON, "scripts/parse_products.py"],
    [PYTHON, "scripts/parse_watchlist.py"],
    [PYTHON, "scripts/generate_watchlist_report.py"],
    [PYTHON, "scripts/send_report_telegram.py"],
]


def main() -> None:
    for step in STEPS:
        pretty = " ".join(step)
        print(f"\\n>>> Running: {pretty}")
        result = subprocess.run(step, cwd=ROOT)
        if result.returncode != 0:
            raise SystemExit(result.returncode)

    print("\\nWatchlist pipeline completed.")


if __name__ == "__main__":
    main()
