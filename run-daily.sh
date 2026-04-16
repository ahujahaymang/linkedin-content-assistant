#!/bin/bash

# Daily LinkedIn Content Assistant Script
# Generates a post, sends to Telegram, and listens for feedback

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "LinkedIn Content Assistant - Daily Run"
echo "========================================"
echo ""

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "ERROR: .env file not found"
    exit 1
fi

# Use venv Python
PYTHON="$SCRIPT_DIR/venv/bin/python3"

if [ ! -f "$PYTHON" ]; then
    echo "ERROR: Virtual environment not found at $SCRIPT_DIR/venv"
    echo "Please run: python3 -m venv venv && ./venv/bin/pip install -e ."
    exit 1
fi

# Profile to use (default: haymang, or pass as first argument)
PROFILE="${1:-haymang}"

echo "Profile: $PROFILE"
echo "Time: $(date)"
echo ""

# Step 1: Generate a post
echo "Step 1: Generating post..."
echo "----------------------------------------"
$PYTHON -m linkedin_content_assistant.main generate-once --profile "$PROFILE"

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Post generation failed"
    exit 1
fi

echo ""
echo "✓ Post generated and sent to Telegram"
echo ""

# Step 2: Start listener for feedback
echo "Step 2: Waiting for your feedback..."
echo "----------------------------------------"
echo "The listener will wait for /posted or /skip"
echo "and will automatically exit after processing"
echo ""
echo "Press Ctrl+C to stop manually"
echo ""

$PYTHON -m linkedin_content_assistant.main listen --profile "$PROFILE"

EXIT_CODE=$?

echo ""
echo "========================================"
echo "Daily run complete!"
echo "Time: $(date)"
echo "========================================"

exit $EXIT_CODE
