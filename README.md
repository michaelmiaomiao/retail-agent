# retail-agent

Costco-focused retail monitoring pipeline for two recurring jobs:
- watchlist tracking for specific Costco product URLs
- While Supplies Last (WSL) catalog monitoring for assortment changes week over week

The repo now has one primary entry point: `scripts/run_watchlist_pipeline.py`.

## Current architecture

### 1. Watchlist tracking
- Input: `data/watchlist.csv`
- Fetch: `scripts/fetch_products.py` saves raw PDP HTML to `data/raw/`
- Parse: `scripts/parse_products.py` and `scripts/parse_watchlist.py` write structured outputs to `data/processed/`
- Report: `scripts/generate_watchlist_report.py` writes weekly markdown to `reports/weekly/`

### 2. WSL scraping and catalog monitoring
- Fetch: `scripts/fetch_wsl.py` captures the Costco WSL listing page and preserves raw HTML / card JSON in `data/raw/`
- Parse: `scripts/parse_wsl.py` normalizes products, writes `data/processed/wsl_latest.json`, stores timestamped history snapshots in `data/processed/history/`, and computes `data/processed/wsl_diff_latest.json`
- Report: `scripts/generate_wsl_report.py` writes a concise weekly diff report showing new, removed, and still-active WSL items

### 3. Report generation
- The orchestrator also writes a combined summary report to `reports/weekly/YYYY-MM-DD-summary.md`
- WSL reports prioritize newly added items first instead of dumping the entire catalog

### 4. Telegram sending
- `scripts/send_report_telegram.py` can send either the default watchlist report or an explicit report path
- The main pipeline can send a compact summary when `--send-telegram` is enabled

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browser support for WSL scraping if needed:
```bash
playwright install chromium
```

3. Optional Telegram env vars in `.env`:
```bash
TELEGRAM_BOT_TOKEN=<bot token>
TELEGRAM_CHAT_ID=<chat id>
```

## Primary commands

Run the full pipeline:
```bash
python3 scripts/run_watchlist_pipeline.py
```

Run only the watchlist flow:
```bash
python3 scripts/run_watchlist_pipeline.py --watchlist-only
```

Run only the WSL flow:
```bash
python3 scripts/run_watchlist_pipeline.py --wsl-only
```

Preview steps without executing them:
```bash
python3 scripts/run_watchlist_pipeline.py --dry-run
```

Run the full pipeline and send a compact Telegram summary:
```bash
python3 scripts/run_watchlist_pipeline.py --send-telegram
```

Send a specific report manually:
```bash
python3 scripts/send_report_telegram.py --report reports/weekly/2026-03-08-summary.md --title "Costco Retail Update"
```

## Key outputs

- `data/raw/`: raw fetched HTML and WSL debug artifacts
- `data/processed/products_latest.json`: parsed watchlist PDP data
- `data/processed/watchlist_latest.json`: normalized watchlist records
- `data/processed/wsl_latest.json`: normalized latest WSL catalog
- `data/processed/wsl_diff_latest.json`: current-vs-previous WSL diff payload
- `data/processed/history/`: dated watchlist and WSL snapshots
- `reports/weekly/`: watchlist, WSL, and combined summary reports

## Tests

Run the current regression suite:
```bash
python3 -m unittest discover -s tests -p 'test*.py'
```

## Current limitations

- Costco page structure is unstable, especially on WSL listing pages; scraper selectors and loading behavior may need periodic maintenance.
- WSL availability is inferred from catalog presence, not confirmed inventory or purchaseability.
- Watchlist price extraction still relies on HTML heuristics and embedded JSON patterns, not a first-party API.
- Telegram sending depends on bot credentials and network availability; the pipeline does not queue retries itself.

## Maintenance intent

The current direction is to keep this repo centered on one weekly retail-monitoring pipeline, not a growing collection of disconnected scripts. Changes should favor:
- stable outputs under `data/processed/` and `reports/weekly/`
- graceful degradation when Costco fetches fail
- small helper functions that are easy to test and maintain
