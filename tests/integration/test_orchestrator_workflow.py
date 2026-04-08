"""Integration test for Content Orchestrator workflow."""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from linkedin_content_assistant.orchestration.orchestrator import ContentOrchestrator, DailyPostResult
from linkedin_content_assistant.profiles.manager import ProfileManager
from linkedin_content_assistant.profiles.models import ProfileConfig, IdentityConfig, BehaviorConfig, PostingWindow
from linkedin_content_assistant.memory.store import InMemoryStore
from linkedin_content_assistant.agents.content_strategy import ContentStrategyAgent
from linkedin_content_assistant.agents.drafting import DraftingAgent
from linkedin_content_assistant.llm.factory import LLMFactory
from linkedin_content_assistant.llm.config import LLMConfig, ProviderConfig, LLMProvider


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    temp_dir = tempfile.mkdtemp()
    profiles_dir = Path(temp_dir) / "profiles"
    memory_dir = Path(temp_dir) / "memory"
    
    profiles_dir.mkdir(parents=True)
    memory_dir.mkdir(parents=True)
    
    yield {
        "profiles": str(profiles_dir),
        "memory": str(memory_dir / "test.json")
    }
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_profile(temp_dirs):
    """Create a test profile."""
    profile = ProfileConfig(
        profile_id="test-profile",
        name="Test Profile",
        description="Test profile for orchestrator",
        version=1,
        enabled=True,
        created_at=datetime.utcnow(),
        last_updated=datetime.utcnow(),
        identity=IdentityConfig(
            headline="Senior Software Engineer | Cloud Architecture",
            seniority="senior",
            primary_domains=["Cloud Computing", "Software Architecture"],
            target_audience="Software engineers and tech leaders",
            positioning="Practical insights on building scalable systems",
            excluded_topics=["Politics", "Religion"]
        ),
        behavior=BehaviorConfig(
            active_topics=["AWS", "System Design", "Team Leadership"],
            hook_patterns=["Personal experience", "Practical tip"],
            posting_windows=[PostingWindow(start_hour=9, end_hour=11)],
            emoji_frequency="moderate",
            comment_depth="detailed",
            vocabulary_bias="professional",
            engagement_style="thoughtful"
        )
    )
    
    # Save profile
    profile_manager = ProfileManager(temp_dirs["profiles"])
    profile_manager.create_profile(profile)
    
    return profile


@pytest.fixture
def orchestrator(temp_dirs):
    """Create orchestrator with all components."""
    profile_manager = ProfileManager(temp_dirs["profiles"])
    memory_store = InMemoryStore(temp_dirs["memory"])
    
    # Create LLM factory (with mock config)
    llm_config = LLMConfig(
        primary_provider=ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-west-2"
        ),
        fallback_providers=[],
        enable_fallback=False
    )
    llm_factory = LLMFactory(llm_config)
    
    # Initialize agents
    content_strategy_agent = ContentStrategyAgent(llm_factory)
    drafting_agent = DraftingAgent(llm_factory)
    
    # Create orchestrator
    return ContentOrchestrator(
        profile_manager=profile_manager,
        memory_store=memory_store,
        content_strategy_agent=content_strategy_agent,
        drafting_agent=drafting_agent,
        trend_monitor=None,
        telegram_bot=None
    )


class TestOrchestratorWorkflow:
    """Test Content Orchestrator workflow."""
    
    @pytest.mark.asyncio
    async def test_check_generation_limit_allows_first_post(self, orchestrator, test_profile):
        """Test that generation limit allows first post of the day."""
        can_generate = await orchestrator.check_generation_limit(test_profile.profile_id)
        assert can_generate is True
    
    @pytest.mark.asyncio
    async def test_check_generation_limit_blocks_second_post(self, orchestrator, test_profile):
        """Test that generation limit blocks second post in same day."""
        from linkedin_content_assistant.memory.models import MemoryEvent
        
        # Store a post_draft event from today
        event = MemoryEvent(
            profile_id=test_profile.profile_id,
            event_type="post_draft",
            content={"test": "data"},
            metrics={},
            timestamp=datetime.utcnow()
        )
        orchestrator.memory_store.store_event(event)
        
        # Check limit - should be blocked
        can_generate = await orchestrator.check_generation_limit(test_profile.profile_id)
        assert can_generate is False
    
    @pytest.mark.asyncio
    async def test_select_best_option_with_single_option(self, orchestrator, test_profile):
        """Test option selection with single option."""
        options = [{
            "angle": "Test angle",
            "hook": "Test hook",
            "target_audience": "Test audience",
            "content_theme": "Test theme",
            "estimated_engagement": "discussion"
        }]
        
        selected = await orchestrator.select_best_option(options, test_profile)
        assert selected == options[0]
    
    @pytest.mark.asyncio
    async def test_select_best_option_with_multiple_options(self, orchestrator, test_profile):
        """Test option selection with multiple options."""
        options = [
            {
                "angle": "Short angle",
                "hook": "Short",
                "target_audience": "Engineers",
                "content_theme": "Theme 1",
                "estimated_engagement": "discussion"
            },
            {
                "angle": "This is a much longer and more detailed angle that should score higher",
                "hook": "This is a longer hook with more detail",
                "target_audience": "Software engineers and tech leaders",
                "content_theme": "Theme 2",
                "estimated_engagement": "shares"
            },
            {
                "angle": "Medium length angle here",
                "hook": "Medium hook",
                "target_audience": "Developers",
                "content_theme": "Theme 3",
                "estimated_engagement": "reactions"
            }
        ]
        
        selected = await orchestrator.select_best_option(options, test_profile)
        
        # Should select option with better quality (longer angle, better hook, audience match)
        assert selected is not None
        assert "angle" in selected
    
    @pytest.mark.asyncio
    async def test_select_best_option_avoids_recent_themes(self, orchestrator, test_profile):
        """Test that option selection avoids recent themes."""
        from linkedin_content_assistant.memory.models import MemoryEvent
        
        # Store recent post with theme
        event = MemoryEvent(
            profile_id=test_profile.profile_id,
            event_type="post_draft",
            content={"theme": "AWS Lambda best practices"},
            metrics={},
            timestamp=datetime.utcnow()
        )
        orchestrator.memory_store.store_event(event)
        
        options = [
            {
                "angle": "Detailed angle about AWS Lambda",
                "hook": "Great hook",
                "target_audience": "Software engineers",
                "content_theme": "AWS Lambda best practices",  # Same as recent
                "estimated_engagement": "discussion"
            },
            {
                "angle": "Detailed angle about Kubernetes",
                "hook": "Great hook",
                "target_audience": "Software engineers",
                "content_theme": "Kubernetes deployment",  # Different theme
                "estimated_engagement": "discussion"
            }
        ]
        
        selected = await orchestrator.select_best_option(options, test_profile)
        
        # Should prefer the option with different theme
        assert selected["content_theme"] == "Kubernetes deployment"
    
    def test_daily_post_result_creation(self):
        """Test DailyPostResult dataclass creation."""
        result = DailyPostResult(
            success=True,
            post_draft=None,
            options_generated=3,
            selected_option=None,
            delivery_status="delivered",
            error=None,
            timestamp=datetime.utcnow()
        )
        
        assert result.success is True
        assert result.options_generated == 3
        assert result.delivery_status == "delivered"
        assert result.error is None
    
    def test_daily_post_result_to_dict(self):
        """Test DailyPostResult conversion to dictionary."""
        result = DailyPostResult(
            success=False,
            post_draft=None,
            options_generated=0,
            selected_option=None,
            delivery_status="failed",
            error="Test error",
            timestamp=datetime.utcnow()
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["success"] is False
        assert result_dict["error"] == "Test error"
        assert result_dict["delivery_status"] == "failed"
        assert "timestamp" in result_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
