#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Log start time
echo "$(date): Starting daily generation" >> logs/cron.log

# Refresh AWS credentials
echo "$(date): Refreshing AWS credentials..." >> logs/cron.log
ada credentials update --account=271149161064 --provider=isengard --role=admin --once >> logs/cron.log 2>&1

if [ $? -ne 0 ]; then
    echo "$(date): ERROR - Failed to refresh AWS credentials" >> logs/cron.log
    exit 1
fi

echo "$(date): AWS credentials refreshed successfully" >> logs/cron.log

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run the content generation
echo "$(date): Running content generation..." >> logs/cron.log
python3 -m linkedin_content_assistant.main generate-once --profile haymang >> logs/cron.log 2>&1

if [ $? -eq 0 ]; then
    echo "$(date): Daily generation completed successfully" >> logs/cron.log
else
    echo "$(date): ERROR - Daily generation failed" >> logs/cron.log
    exit 1
fi
