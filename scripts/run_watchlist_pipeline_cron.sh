#!/bin/zsh
set -euo pipefail

REPO_DIR="/Users/michaelmiaoair/Documents/GitHub/retail-agent"
PYTHON_BIN="$REPO_DIR/.venv/bin/python"
LOG_FILE="$REPO_DIR/logs/watchlist_cron.log"

cd "$REPO_DIR"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] Starting weekly watchlist pipeline"
  "$PYTHON_BIN" scripts/run_watchlist_pipeline.py
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] Finished weekly watchlist pipeline"
} >> "$LOG_FILE" 2>&1
