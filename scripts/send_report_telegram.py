import argparse
import os
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

REPORTS_DIR = Path("reports/weekly")
MAX_MESSAGE_LEN = 4000


def get_latest_report_path(default_suffix: str = "-watchlist.md") -> Path:
    today_name = f"{date.today().isoformat()}{default_suffix}"
    today_path = REPORTS_DIR / today_name
    if today_path.exists():
        return today_path

    candidates = sorted(REPORTS_DIR.glob(f"*{default_suffix}"))
    if not candidates:
        raise FileNotFoundError(f"No report found under reports/weekly matching *{default_suffix}")
    return candidates[-1]


def split_message(text: str, max_len: int = MAX_MESSAGE_LEN) -> list[str]:
    text = text.strip()
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    buf = []
    current = 0

    for line in text.splitlines():
        line_len = len(line) + 1
        if current + line_len > max_len and buf:
            chunks.append("\n".join(buf).strip())
            buf = [line]
            current = line_len
        else:
            buf.append(line)
            current += line_len

    if buf:
        chunks.append("\n".join(buf).strip())

    return chunks


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"Telegram API HTTP {resp.status_code}: {resp.text}")

    body = resp.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram API error: {body}")


def discover_chat_id(bot_token: str) -> str:
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    resp = requests.get(url, params={"limit": 100, "timeout": 0}, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"Telegram getUpdates HTTP {resp.status_code}: {resp.text}")

    body = resp.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram getUpdates error: {body}")

    results = body.get("result") or []
    if not results:
        raise ValueError(
            "Could not auto-discover TELEGRAM_CHAT_ID. "
            "Please send a message to your bot first, then retry."
        )

    for update in reversed(results):
        msg = update.get("message") or update.get("edited_message") or {}
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is not None:
            return str(chat_id)

        callback_query = update.get("callback_query") or {}
        cb_msg = callback_query.get("message") or {}
        cb_chat = cb_msg.get("chat") or {}
        cb_chat_id = cb_chat.get("id")
        if cb_chat_id is not None:
            return str(cb_chat_id)

    raise ValueError(
        "Could not auto-discover TELEGRAM_CHAT_ID from updates. "
        "Please set TELEGRAM_CHAT_ID in .env."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a generated report to Telegram.")
    parser.add_argument("--report", help="Path to a report file to send.")
    parser.add_argument("--title", default="Costco Watchlist Report", help="Header prepended to the message.")
    parser.add_argument(
        "--suffix",
        default="-watchlist.md",
        help="Fallback suffix used to discover the latest report when --report is omitted.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv()

    bot_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()

    if not bot_token:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN in environment/.env")
    if not chat_id:
        chat_id = discover_chat_id(bot_token)
        print(f"Auto-discovered TELEGRAM_CHAT_ID: {chat_id}")

    report_path = Path(args.report) if args.report else get_latest_report_path(args.suffix)
    content = report_path.read_text(encoding="utf-8")

    header = f"{args.title}: {report_path.name}\n"
    messages = split_message(header + "\n" + content)

    for idx, msg in enumerate(messages, start=1):
        if len(messages) > 1:
            msg = f"[{idx}/{len(messages)}]\n{msg}"
        send_telegram_message(bot_token, chat_id, msg)

    print(f"Sent report: {report_path}")
    print(f"Chunks sent: {len(messages)}")


if __name__ == "__main__":
    main()
