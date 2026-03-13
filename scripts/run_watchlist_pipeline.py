import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from report_utils import render_compact_telegram_summary, write_report

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
REPORTS_DIR = ROOT / "reports/weekly"
WATCHLIST_LATEST = ROOT / "data/processed/watchlist_latest.json"
WSL_DIFF_LATEST = ROOT / "data/processed/wsl_diff_latest.json"

WATCHLIST_STEPS = [
    ("fetch_watchlist", [PYTHON, "scripts/fetch_products.py"]),
    ("parse_products", [PYTHON, "scripts/parse_products.py"]),
    ("parse_watchlist", [PYTHON, "scripts/parse_watchlist.py"]),
    ("report_watchlist", [PYTHON, "scripts/generate_watchlist_report.py"]),
]
WSL_STEPS = [
    ("fetch_wsl", [PYTHON, "scripts/fetch_wsl.py"]),
    ("parse_wsl", [PYTHON, "scripts/parse_wsl.py"]),
    ("report_wsl", [PYTHON, "scripts/generate_wsl_report.py"]),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Costco retail-agent pipeline.")
    parser.add_argument("--watchlist-only", action="store_true", help="Run only the watchlist flow.")
    parser.add_argument("--wsl-only", action="store_true", help="Run only the While Supplies Last flow.")
    parser.add_argument("--send-telegram", action="store_true", help="Send the compact summary to Telegram.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned steps without running them.")
    args = parser.parse_args()
    if args.watchlist_only and args.wsl_only:
        parser.error("Choose either --watchlist-only or --wsl-only, not both.")
    return args


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def should_run_watchlist(args: argparse.Namespace) -> bool:
    return not args.wsl_only


def should_run_wsl(args: argparse.Namespace) -> bool:
    return not args.watchlist_only


def build_summary_report(today: str) -> Path:
    watchlist_records = load_json(WATCHLIST_LATEST, [])
    wsl_diff = load_json(WSL_DIFF_LATEST, {"comparison": {"counts": {}}})
    counts = wsl_diff.get("comparison", {}).get("counts", {})

    lines = [
        f"# Costco Retail Weekly Summary ({today})",
        "",
        "## Watchlist",
        f"- Tracked items: **{len(watchlist_records)}**",
        "- Source: `data/processed/watchlist_latest.json`",
        "",
        "## While Supplies Last",
        f"- Current items: **{counts.get('current', 0)}**",
        f"- New this week: **{counts.get('new', 0)}**",
        f"- Removed this week: **{counts.get('removed', 0)}**",
        f"- Still active: **{counts.get('still_active', 0)}**",
    ]

    for section_title, key in [
        ("New this week", "new_items"),
        ("Removed this week", "removed_items"),
    ]:
        items = wsl_diff.get("comparison", {}).get(key, [])
        lines.append("")
        lines.append(f"## {section_title}")
        if items:
            for item in items[:12]:
                lines.append(f"- {item.get('title_en', 'Unknown')} ({item.get('url', '')})")
            remaining = len(items) - min(len(items), 12)
            if remaining > 0:
                lines.append(f"- ... and {remaining} more")
        else:
            lines.append("- None")

    fetch_error = (wsl_diff.get("fetch_error") or "").strip()
    if fetch_error:
        lines.extend(["", "## Fetch status", f"- Warning: `{fetch_error}`"])

    summary_path = REPORTS_DIR / f"{today}-summary.md"
    return write_report(summary_path, "\n".join(lines))


def run_steps(selected_steps: list[tuple[str, list[str]]], dry_run: bool) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for name, step in selected_steps:
        pretty = " ".join(step)
        print(f"\n>>> {name}: {pretty}")
        if dry_run:
            results.append({"name": name, "status": "planned", "command": pretty})
            continue

        result = subprocess.run(step, cwd=ROOT)
        status = "ok" if result.returncode == 0 else f"failed({result.returncode})"
        results.append({"name": name, "status": status, "command": pretty})
        if result.returncode != 0:
            raise SystemExit(result.returncode)
    return results


def send_summary_to_telegram(summary_path: Path, dry_run: bool) -> dict[str, str]:
    compact_summary = render_compact_telegram_summary(
        load_json(WATCHLIST_LATEST, []),
        load_json(WSL_DIFF_LATEST, {"comparison": {"counts": {}}}),
    )
    compact_path = summary_path.with_name(summary_path.stem + "-telegram.txt")
    compact_path.write_text(compact_summary + "\n", encoding="utf-8")

    command = [
        PYTHON,
        "scripts/send_report_telegram.py",
        "--report",
        str(compact_path.relative_to(ROOT)),
        "--title",
        "Costco Retail Update",
    ]
    pretty = " ".join(command)
    print(f"\n>>> send_telegram: {pretty}")
    if dry_run:
        return {"name": "send_telegram", "status": "planned", "command": pretty}

    result = subprocess.run(command, cwd=ROOT)
    status = "ok" if result.returncode == 0 else f"failed({result.returncode})"
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return {"name": "send_telegram", "status": status, "command": pretty}


def print_summary(results: list[dict[str, str]], summary_path: Optional[Path]) -> None:
    print("\n=== Pipeline summary ===")
    for result in results:
        print(f"- {result['name']}: {result['status']}")
    if summary_path:
        print(f"- summary_report: {summary_path.relative_to(ROOT)}")
    print(f"- reports_dir: {REPORTS_DIR.relative_to(ROOT)}")


def main() -> None:
    args = parse_args()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    selected_steps: list[tuple[str, list[str]]] = []
    if should_run_watchlist(args):
        selected_steps.extend(WATCHLIST_STEPS)
    if should_run_wsl(args):
        selected_steps.extend(WSL_STEPS)

    results = run_steps(selected_steps, dry_run=args.dry_run)

    summary_path = None
    if not args.dry_run:
        summary_path = build_summary_report(date.today().isoformat())
        print(f"\nSaved summary: {summary_path.relative_to(ROOT)}")
    else:
        planned_summary = REPORTS_DIR / f"{date.today().isoformat()}-summary.md"
        print(f"\nPlanned summary: {planned_summary.relative_to(ROOT)}")

    if args.send_telegram:
        if summary_path is None:
            summary_path = REPORTS_DIR / f"{date.today().isoformat()}-summary.md"
        results.append(send_summary_to_telegram(summary_path, dry_run=args.dry_run))

    print_summary(results, summary_path)


if __name__ == "__main__":
    main()
