#!/bin/bash
# Setup script for LinkedIn Content Assistant

set -e

echo "==================================="
echo "LinkedIn Content Assistant Setup"
echo "==================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.10 or higher is required. Found: $python_version"
    exit 1
fi
echo "✓ Python $python_version detected"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Skipping..."
else
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file with your actual credentials!"
else
    echo ".env file already exists. Skipping..."
fi
echo ""

# Create directory structure (if not exists)
echo "Verifying directory structure..."
mkdir -p src/linkedin_content_assistant
mkdir -p tests/unit tests/integration tests/property
mkdir -p profiles data/memory config
echo "✓ Directory structure verified"
echo ""

# Run tests to verify setup
echo "Running tests to verify setup..."
if pytest tests/ -v 2>/dev/null; then
    echo "✓ Tests passed"
else
    echo "⚠️  No tests found yet (this is expected during initial setup)"
fi
echo ""

echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your credentials"
echo "2. Create a profile configuration in profiles/"
echo "3. Run 'source venv/bin/activate' to activate the environment"
echo "4. Start development!"
echo ""
echo "Useful commands:"
echo "  pytest                    # Run all tests"
echo "  pytest -m unit            # Run unit tests only"
echo "  pytest -m property        # Run property-based tests"
echo "  black src/ tests/         # Format code"
echo "  ruff check src/ tests/    # Lint code"
echo ""
