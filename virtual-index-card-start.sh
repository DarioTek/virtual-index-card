#!/bin/bash

# Timestamp function for logging
timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

echo "Start Current timestamp: $(timestamp)"

# Project-wide timezone policy: always run in New York market time.
export TZ="America/New_York"

# Navigate to your project root directory (update this path to where your project lives)
PROJECT_DIR="/mnt/ssd/git/virtual-index-card"
cd "$PROJECT_DIR" || { echo "[ERROR] Project directory not found: $PROJECT_DIR"; exit 1; }

# Ensure logs directory exists
mkdir -p "$PROJECT_DIR/logs"

# Set the database path and run Gunicorn with Uvicorn workers in the background
echo "Starting Virtual Index Card app with Gunicorn..."
export VIC_DATABASE_PATH="./data/virtual-index-card.sqlite3"

# Note: Ensure 'gunicorn' is added to your project dependencies (pyproject.toml)
nohup uv run gunicorn virtual_index_card.app:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:10001 \
  --pid "$PROJECT_DIR/gunicorn.pid" \
  > "$PROJECT_DIR/logs/virtual_index_card.log" 2>&1 &

echo "Virtual Index Card started in the background via Gunicorn. Check logs at $PROJECT_DIR/logs/virtual_index_card.log"
echo "End Current timestamp: $(timestamp)"

# To stop the process, use pgrep to return the PID:
# pgrep -f "gunicorn.*virtual_index_card.app:app"
# Then use: kill <PID>
#
# kill "$(cat $PROJECT_DIR/gunicorn.pid)"