# retail-agent

Costco-focused retail intelligence agent: track a watchlist of Costco items, parse prices/specs, and generate weekly deal reports.

## V1
- Input: `data/watchlist.csv` (Costco product / promo URLs)
- Fetch: save raw pages to `data/raw/`
- Parse: write structured outputs to `data/processed/`
- Report: weekly Markdown in `reports/weekly/`

## Run (placeholder)
python3 scripts/fetch_products.py
python3 scripts/parse_products.py
python3 scripts/generate_report.py
