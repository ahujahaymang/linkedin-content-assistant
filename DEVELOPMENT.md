# Development Guide

This guide provides detailed information for developers working on the LinkedIn Content Assistant project.

## Project Overview

The LinkedIn Content Assistant is a Python-based system that generates authentic LinkedIn posts using AI while maintaining human control through a Telegram delivery workflow. The system is designed with safety, modularity, and component reuse as core principles.

## Architecture

### Component Layers

1. **Content Generation Layer** (`src/linkedin_content_assistant/agents/`)
   - Content Strategy Agent: Generates diverse post options
   - Drafting Agent: Creates polished LinkedIn posts
   - Style Learner: Analyzes writing patterns

2. **Trend Monitoring Layer**
   - Feed Scanner: Monitors LinkedIn for trending content (read-only)
   - Web Scraper: Tracks tech news from web sources
   - Trend Monitor: Aggregates trends from multiple sources

3. **Orchestration Layer**
   - Content Orchestrator: Coordinates daily content generation
   - Daily Scheduler: Triggers generation at configured times

4. **Delivery Layer** (`src/linkedin_content_assistant/delivery/`)
   - Telegram Bot: Delivers drafts to user for manual posting

5. **Storage Layer**
   - Profile Store: Manages profile configurations
   - Memory Store: Stores post history and trends

6. **LLM Layer** (`src/linkedin_content_assistant/llm/`)
   - LLM Factory: Routes requests to configured providers
   - Provider implementations: Bedrock, OpenAI, Anthropic

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip and virtualenv
- Git
- Telegram bot token (for testing delivery)
- LLM provider credentials (AWS, OpenAI, or Anthropic)

### Initial Setup

```bash
# Clone and navigate to project
cd PersonalPOC/linkedInblogger

# Run setup script
make setup

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Development Workflow

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Install in development mode:**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Make changes to code**

4. **Run tests:**
   ```bash
   make test           # All tests
   make test-unit      # Unit tests only
   make test-property  # Property-based tests
   ```

5. **Check code quality:**
   ```bash
   make format         # Format with black
   make lint           # Lint with ruff
   make type-check     # Type check with mypy
   make check          # All quality checks
   ```

## Testing Strategy

### Test Types

1. **Unit Tests** (`tests/unit/`)
   - Test individual components in isolation
   - Use mocks for external dependencies
   - Fast execution, high coverage
   - Mark with `@pytest.mark.unit`

2. **Integration Tests** (`tests/integration/`)
   - Test component interactions
   - May use real external services (with mocks as fallback)
   - Slower execution, validates workflows
   - Mark with `@pytest.mark.integration`

3. **Property-Based Tests** (`tests/property/`)
   - Test universal properties across all inputs
   - Use Hypothesis for random input generation
   - Validates correctness properties from design doc
   - Mark with `@pytest.mark.property`

### Running Tests

```bash
# All tests
pytest

# Specific test types
pytest -m unit
pytest -m integration
pytest -m property

# Specific test file
pytest tests/unit/test_profile_store.py

# With coverage
pytest --cov=src/linkedin_content_assistant --cov-report=html

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf
```

### Writing Tests

**Unit Test Example:**
```python
import pytest
from linkedin_content_assistant.profiles import ProfileManager

@pytest.mark.unit
def test_profile_creation(test_profiles_dir):
    """Test creating a new profile"""
    manager = ProfileManager(test_profiles_dir)
    profile = manager.create_profile(
        profile_id="test",
        name="Test Profile",
        # ... other fields
    )
    assert profile.profile_id == "test"
    assert profile.version == 1
```

**Property Test Example:**
```python
from hypothesis import given, strategies as st
import pytest

@pytest.mark.property
@given(profile_id=st.text(min_size=1, max_size=50))
def test_property_profile_id_validation(profile_id):
    """
    Feature: linkedin-content-assistant, Property 2: Profile Data Validation
    
    For any profile data missing required fields, the Profile_Store 
    should reject storage and raise a validation error.
    """
    # Test implementation
    pass
```

## Code Style

### Formatting

- **Line length:** 100 characters
- **Formatter:** Black
- **Import sorting:** Ruff (isort rules)

Run: `make format`

### Linting

- **Linter:** Ruff
- **Rules:** pycodestyle, pyflakes, flake8-bugbear, pyupgrade

Run: `make lint`

### Type Checking

- **Type checker:** mypy
- **Configuration:** See `pyproject.toml`

Run: `make type-check`

## Component Development

### Adding a New Component

1. Create component directory: `src/linkedin_content_assistant/my_component/`
2. Add `__init__.py` with public API
3. Implement component logic
4. Add unit tests: `tests/unit/test_my_component.py`
5. Add property tests if applicable: `tests/property/test_my_component_properties.py`
6. Update documentation

### Component Reuse from AIManager

Many components are reused from `AIManager/linkedin_ai_manager/`:

1. Copy component directory to `src/linkedin_content_assistant/`
2. Update imports to match new package structure
3. Adapt as needed (e.g., remove posting functionality)
4. Add tests to verify functionality
5. Document any changes from original

## Configuration Management

### Environment Variables

Stored in `.env` (not committed):
- Credentials (Telegram, AWS, OpenAI, Anthropic)
- Sensitive configuration

### YAML Configuration

Stored in `config/config.yaml`:
- System behavior settings
- Component configurations
- Non-sensitive parameters

### Profile Configurations

Stored in `profiles/*.yaml`:
- Individual profile settings
- Identity and behavior configuration
- Human-editable format

## Debugging

### Enable Debug Logging

```python
# In .env
LOG_LEVEL=DEBUG
```

### Run with Debugger

```bash
# Using pytest with pdb
pytest --pdb

# Using Python debugger
python -m pdb src/linkedin_content_assistant/main.py
```

### Common Issues

**Import Errors:**
- Ensure virtual environment is activated
- Run `pip install -e .` to install package in development mode

**Test Failures:**
- Check test fixtures in `tests/conftest.py`
- Verify test data directories exist
- Check for missing dependencies

**Configuration Errors:**
- Verify `.env` file exists and has correct values
- Check `config/config.yaml` syntax
- Validate profile YAML files

## Contributing

### Before Committing

1. Run all tests: `make test`
2. Run quality checks: `make check`
3. Update documentation if needed
4. Add tests for new functionality

### Commit Messages

Follow conventional commits format:
```
feat: Add web scraper component
fix: Correct profile version increment logic
docs: Update development guide
test: Add property tests for style learner
refactor: Simplify LLM provider routing
```

## Resources

- **Spec Files:** `.kiro/specs/linkedin-content-assistant/`
  - `requirements.md`: Detailed requirements
  - `design.md`: Architecture and design decisions
  - `tasks.md`: Implementation plan

- **AIManager Source:** `AIManager/linkedin_ai_manager/`
  - Reference for reusable components
  - Original implementations

- **Documentation:**
  - `README.md`: Project overview
  - `DEVELOPMENT.md`: This file
  - `CONFIGURATION.md`: Configuration guide (to be created)
  - `USAGE.md`: Usage guide (to be created)

## Next Steps

See `.kiro/specs/linkedin-content-assistant/tasks.md` for the complete implementation plan. Current phase is Task 1 (Project Setup), which is now complete.

Next task: Task 2 - Copy and adapt reusable components from AIManager.
