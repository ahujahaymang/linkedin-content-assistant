#!/bin/bash
set -e

echo "Setting up daily content generation at 7 AM PST..."

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Project directory: $PROJECT_DIR"

# Create a wrapper script that will be called by cron
WRAPPER_SCRIPT="$PROJECT_DIR/run-daily-generation.sh"

cat > "$WRAPPER_SCRIPT" << 'EOF'
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
EOF

chmod +x "$WRAPPER_SCRIPT"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Create the cron job
# 7 AM PST = 15:00 UTC (PST is UTC-8, but during PDT it's UTC-7)
# We'll use 15:00 UTC which is 7 AM PST / 8 AM PDT
CRON_TIME="0 15 * * *"  # 7 AM PST (15:00 UTC)
CRON_JOB="$CRON_TIME $WRAPPER_SCRIPT"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$WRAPPER_SCRIPT"; then
    echo "Cron job already exists. Updating..."
    # Remove old job and add new one
    (crontab -l 2>/dev/null | grep -v "$WRAPPER_SCRIPT"; echo "$CRON_JOB") | crontab -
else
    echo "Adding new cron job..."
    # Add new job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
fi

echo ""
echo "✓ Cron job configured successfully!"
echo ""
echo "Schedule: Daily at 7:00 AM PST (15:00 UTC)"
echo "Command: $WRAPPER_SCRIPT"
echo "Logs: $PROJECT_DIR/logs/cron.log"
echo ""
echo "The script will:"
echo "  1. Refresh AWS credentials (ada credentials update)"
echo "  2. Generate daily post"
echo "  3. Send to Telegram"
echo ""
echo "To view current cron jobs:"
echo "  crontab -l"
echo ""
echo "To view logs:"
echo "  tail -f $PROJECT_DIR/logs/cron.log"
echo ""
echo "To test the script manually:"
echo "  $WRAPPER_SCRIPT"
echo ""
