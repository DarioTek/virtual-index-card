#!/bin/bash

# Timestamp function for logging
timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

echo "Start Current timestamp: $(timestamp)"

# Project-wide timezone policy: always run in New York market time.
export TZ="America/New_York"

# Navigate to your project root directory (update this path to where your project lives)
PROJECT_DIR="/home/dariotek/Python/virtual_index_card"
cd "$PROJECT_DIR" || { echo "[ERROR] Project directory not found: $PROJECT_DIR"; exit 1; }

# Ensure logs directory exists
mkdir -p "$PROJECT_DIR/logs"

# Set the database path and run uvicorn in the background using nohup
# Note: --reload is typically used for development; remove it if running in production.
echo "Starting Virtual Index Card app..."
export VIC_DATABASE_PATH="./data/virtual-index-card.sqlite3"

nohup uv run uvicorn virtual_index_card.app:app --host 0.0.0.0 --port 10001 > "$PROJECT_DIR/logs/virtual_index_card.log" 2>&1 &

echo "Virtual Index Card started in the background. Check logs at $PROJECT_DIR/logs/virtual_index_card.log"
echo "End Current timestamp: $(timestamp)"

# To stop the process, use pgrep to return the PID:
# pgrep -f "virtual_index_card.app:app"
# Then use: kill <PID>