.PHONY: help setup install test test-unit test-integration test-property test-all coverage clean format lint type-check dev-install

help:
	@echo "LinkedIn Content Assistant - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Run initial setup (create venv, install deps)"
	@echo "  make install        - Install dependencies only"
	@echo "  make dev-install    - Install with development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-property  - Run property-based tests only"
	@echo "  make coverage       - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format         - Format code with black"
	@echo "  make lint           - Lint code with ruff"
	@echo "  make type-check     - Type check with mypy"
	@echo "  make check          - Run all quality checks (format, lint, type-check)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          - Remove build artifacts and cache files"

setup:
	@echo "Running setup script..."
	@bash setup.sh

install:
	pip install -r requirements.txt

dev-install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v -m unit

test-integration:
	pytest tests/integration/ -v -m integration

test-property:
	pytest tests/property/ -v -m property

test-all: test-unit test-integration test-property

coverage:
	pytest tests/ --cov=src/linkedin_content_assistant --cov-report=html --cov-report=term

format:
	black src/ tests/

lint:
	ruff check src/ tests/

type-check:
	mypy src/

check: format lint type-check
	@echo "All quality checks passed!"

clean:
	@echo "Cleaning build artifacts and cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".hypothesis" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf build/ dist/ htmlcov/ .coverage 2>/dev/null || true
	@echo "Clean complete!"
