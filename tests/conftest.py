"""
Shared pytest fixtures and configuration for all tests
"""
import pytest
from pathlib import Path
from typing import Dict, Any


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test data"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "memory").mkdir()
    return data_dir


@pytest.fixture
def test_profiles_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test profiles"""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    return profiles_dir


@pytest.fixture
def test_config_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test configuration"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_profile_data() -> Dict[str, Any]:
    """Provide sample profile data for testing"""
    return {
        "profile_id": "test-profile",
        "name": "Test Profile",
        "description": "Test profile for unit tests",
        "version": 1,
        "enabled": True,
        "identity": {
            "headline": "Senior Software Engineer | Cloud Architecture | AI/ML",
            "seniority": "senior",
            "primary_domains": ["Cloud Computing", "Machine Learning"],
            "target_audience": "Software engineers and tech leaders",
            "positioning": "Practical insights on building scalable systems",
            "excluded_topics": ["Politics", "Religion"]
        },
        "behavior": {
            "active_topics": ["AWS architecture", "ML deployment"],
            "hook_patterns": ["Personal story", "Practical tip"],
            "posting_windows": [
                {"start_hour": 9, "end_hour": 11},
                {"start_hour": 14, "end_hour": 16}
            ],
            "emoji_frequency": "moderate",
            "comment_depth": "detailed",
            "vocabulary_bias": "professional",
            "engagement_style": "thoughtful"
        }
    }


@pytest.fixture
def sample_post_content() -> str:
    """Provide sample LinkedIn post content for testing"""
    return """
Just deployed a new microservice architecture that reduced our API latency by 40%. 
Here's what made the difference:

1. Switched from REST to gRPC for internal communication
2. Implemented connection pooling with proper timeout handling
3. Added circuit breakers to prevent cascade failures

The key insight? Most performance issues aren't about the code - they're about how services talk to each other.

What's your experience with microservice performance optimization?

#SoftwareEngineering #CloudArchitecture #Performance
    """.strip()


@pytest.fixture
def sample_feed_posts() -> list:
    """Provide sample LinkedIn feed posts for testing"""
    return [
        {
            "id": "post-1",
            "author": "John Doe",
            "content": "Excited to share our new AI model...",
            "timestamp": "2024-01-15T10:00:00Z",
            "engagement_metrics": {"likes": 150, "comments": 25, "shares": 10},
            "hashtags": ["#AI", "#MachineLearning"],
            "post_type": "article"
        },
        {
            "id": "post-2",
            "author": "Jane Smith",
            "content": "5 tips for better code reviews...",
            "timestamp": "2024-01-15T11:00:00Z",
            "engagement_metrics": {"likes": 80, "comments": 15, "shares": 5},
            "hashtags": ["#CodeReview", "#SoftwareEngineering"],
            "post_type": "text"
        }
    ]


@pytest.fixture
def sample_news_items() -> list:
    """Provide sample web news items for testing"""
    return [
        {
            "title": "New AWS Service Announced",
            "summary": "AWS announces a new serverless computing service...",
            "url": "https://example.com/news/aws-service",
            "source": "TechCrunch",
            "published_date": "2024-01-15T09:00:00Z",
            "topics": ["Cloud Computing", "AWS"],
            "relevance_score": 0.85
        },
        {
            "title": "Machine Learning Breakthrough",
            "summary": "Researchers achieve new milestone in ML efficiency...",
            "url": "https://example.com/news/ml-breakthrough",
            "source": "Hacker News",
            "published_date": "2024-01-15T08:00:00Z",
            "topics": ["Machine Learning", "AI"],
            "relevance_score": 0.92
        }
    ]


# Hypothesis profiles for property-based testing
from hypothesis import settings, Verbosity

settings.register_profile("default", max_examples=100, deadline=None)
settings.register_profile("ci", max_examples=50, deadline=5000)
settings.register_profile("dev", max_examples=200, verbosity=Verbosity.verbose)
settings.register_profile("debug", max_examples=10, verbosity=Verbosity.verbose)

# Load the appropriate profile
import os
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))
