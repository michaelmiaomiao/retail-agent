from datetime import date
from pathlib import Path


def _render_item_lines(items: list[dict], limit: int | None = None) -> list[str]:
    if not items:
        return ["- None"]

    shown = items if limit is None else items[:limit]
    lines = [f"- {item.get('title_en', 'Unknown')} ({item.get('url', '')})" for item in shown]
    remaining = len(items) - len(shown)
    if remaining > 0:
        lines.append(f"- ... and {remaining} more")
    return lines


def render_wsl_report(diff_payload: dict, today: str | None = None) -> str:
    report_date = today or date.today().isoformat()
    comparison = diff_payload.get("comparison", {})
    counts = comparison.get("counts", {})
    fetch_error = (diff_payload.get("fetch_error") or "").strip()

    lines = [
        f"# Costco While Supplies Last Weekly Snapshot ({report_date})",
        "",
        f"Current items: **{counts.get('current', 0)}**",
        f"New this week: **{counts.get('new', 0)}**",
        f"Removed this week: **{counts.get('removed', 0)}**",
        f"Still active: **{counts.get('still_active', 0)}**",
    ]

    if fetch_error:
        lines.extend(
            [
                "",
                "## Fetch status",
                f"- Fetch completed with warning: `{fetch_error}`",
                "- Debug artifacts were preserved under `data/raw/`.",
            ]
        )

    lines.extend(
        [
            "",
            "## New this week",
            *_render_item_lines(comparison.get("new_items", [])),
            "",
            "## Removed this week",
            *_render_item_lines(comparison.get("removed_items", [])),
            "",
            "## Still active",
            *_render_item_lines(comparison.get("still_active", []), limit=15),
            "",
        ]
    )

    return "\n".join(lines)


def render_compact_telegram_summary(
    watchlist_records: list[dict], diff_payload: dict, today: str | None = None
) -> str:
    report_date = today or date.today().isoformat()
    comparison = diff_payload.get("comparison", {})
    counts = comparison.get("counts", {})
    new_items = comparison.get("new_items", [])
    removed_items = comparison.get("removed_items", [])

    lines = [
        f"Costco retail update ({report_date})",
        f"Watchlist tracked: {len(watchlist_records)}",
        (
            "WSL snapshot: "
            f"{counts.get('current', 0)} active | "
            f"{counts.get('new', 0)} new | "
            f"{counts.get('removed', 0)} removed"
        ),
    ]

    if new_items:
        lines.append("")
        lines.append("New this week:")
        for item in new_items[:8]:
            lines.append(f"- {item.get('title_en', 'Unknown')}")
        extra = len(new_items) - min(len(new_items), 8)
        if extra > 0:
            lines.append(f"- ... and {extra} more")
    elif removed_items:
        lines.append("")
        lines.append("No new WSL items this run.")
        lines.append(f"Removed this week: {len(removed_items)}")
    else:
        lines.append("")
        lines.append("No WSL assortment change detected this run.")

    fetch_error = (diff_payload.get("fetch_error") or "").strip()
    if fetch_error:
        lines.append("")
        lines.append(f"Fetch warning: {fetch_error.splitlines()[0]}")

    return "\n".join(lines).strip()


def write_report(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return path
