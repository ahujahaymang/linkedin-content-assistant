"""
Basic setup verification tests
"""
import pytest
import sys
from pathlib import Path


def test_python_version():
    """Verify Python version is 3.10 or higher"""
    assert sys.version_info >= (3, 10), "Python 3.10 or higher is required"


def test_project_structure():
    """Verify basic project structure exists"""
    project_root = Path(__file__).parent.parent
    
    # Check main directories
    assert (project_root / "src").exists(), "src/ directory should exist"
    assert (project_root / "tests").exists(), "tests/ directory should exist"
    assert (project_root / "profiles").exists(), "profiles/ directory should exist"
    assert (project_root / "data").exists(), "data/ directory should exist"
    assert (project_root / "config").exists(), "config/ directory should exist"
    
    # Check configuration files
    assert (project_root / "requirements.txt").exists(), "requirements.txt should exist"
    assert (project_root / "pytest.ini").exists(), "pytest.ini should exist"
    assert (project_root / "pyproject.toml").exists(), "pyproject.toml should exist"
    assert (project_root / ".env.example").exists(), ".env.example should exist"
    assert (project_root / "README.md").exists(), "README.md should exist"


def test_imports():
    """Verify core dependencies can be imported"""
    try:
        import pydantic
        import aiohttp
        import yaml
        import pytest
        import hypothesis
    except ImportError as e:
        pytest.fail(f"Failed to import required dependency: {e}")


def test_package_importable():
    """Verify the main package can be imported"""
    try:
        import linkedin_content_assistant
        assert hasattr(linkedin_content_assistant, "__version__")
    except ImportError as e:
        pytest.fail(f"Failed to import linkedin_content_assistant: {e}")


@pytest.mark.unit
def test_fixtures_available(sample_profile_data, sample_post_content):
    """Verify test fixtures are available"""
    assert sample_profile_data is not None
    assert "profile_id" in sample_profile_data
    assert sample_post_content is not None
    assert len(sample_post_content) > 0
