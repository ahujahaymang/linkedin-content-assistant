#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Log start time
echo "$(date): Starting daily generation" >> logs/cron.log

# Note: AWS credentials should be managed separately (e.g., via aws-vault or environment)
# No automatic credential refresh in this script

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Use virtual environment Python
PYTHON_BIN="$SCRIPT_DIR/venv/bin/python3"

if [ ! -f "$PYTHON_BIN" ]; then
    echo "$(date): ERROR - Virtual environment not found at $PYTHON_BIN" >> logs/cron.log
    exit 1
fi

# First process any pending /posted messages
echo "$(date): Processing pending Telegram messages..." >> logs/cron.log
$PYTHON_BIN -m linkedin_content_assistant.main listen --once >> logs/cron.log 2>&1

# Run the content generation
echo "$(date): Running content generation..." >> logs/cron.log
$PYTHON_BIN -m linkedin_content_assistant.main generate-once --profile haymang >> logs/cron.log 2>&1

if [ $? -eq 0 ]; then
    echo "$(date): Daily generation completed successfully" >> logs/cron.log
else
    echo "$(date): ERROR - Daily generation failed" >> logs/cron.log
    exit 1
fi
