"""Manual verification script for Content Orchestrator."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from linkedin_content_assistant.orchestration.orchestrator import ContentOrchestrator, DailyPostResult
from linkedin_content_assistant.profiles.manager import ProfileManager
from linkedin_content_assistant.memory.store import InMemoryStore
from linkedin_content_assistant.agents.content_strategy import ContentStrategyAgent
from linkedin_content_assistant.agents.drafting import DraftingAgent
from linkedin_content_assistant.llm.factory import LLMFactory
from linkedin_content_assistant.llm.config import LLMConfig, ProviderConfig, LLMProvider


def test_orchestrator_initialization():
    """Test that orchestrator can be initialized with all components."""
    print("\n=== Testing Orchestrator Initialization ===")
    
    try:
        # Initialize components
        profile_manager = ProfileManager("./profiles")
        memory_store = InMemoryStore("./data/memory/test_orchestrator.json")
        
        # Create LLM factory (with mock config for testing)
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
        
        # Initialize orchestrator
        orchestrator = ContentOrchestrator(
            profile_manager=profile_manager,
            memory_store=memory_store,
            content_strategy_agent=content_strategy_agent,
            drafting_agent=drafting_agent,
            trend_monitor=None,  # Stub for MVP
            telegram_bot=None     # Stub for MVP
        )
        
        print("✓ Orchestrator initialized successfully")
        print(f"  - Profile Manager: {type(profile_manager).__name__}")
        print(f"  - Memory Store: {type(memory_store).__name__}")
        print(f"  - Content Strategy Agent: {type(content_strategy_agent).__name__}")
        print(f"  - Drafting Agent: {type(drafting_agent).__name__}")
        print(f"  - Trend Monitor: {'Not configured (stub)' if orchestrator.trend_monitor is None else 'Configured'}")
        print(f"  - Telegram Bot: {'Not configured (stub)' if orchestrator.telegram_bot is None else 'Configured'}")
        
        return orchestrator
        
    except Exception as e:
        print(f"✗ Orchestrator initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_check_generation_limit(orchestrator):
    """Test generation limit checking."""
    print("\n=== Testing Generation Limit Check ===")
    
    try:
        # Test with non-existent profile (should allow generation)
        can_generate = await orchestrator.check_generation_limit("test-profile")
        print(f"✓ Generation limit check completed")
        print(f"  - Can generate for new profile: {can_generate}")
        
        return True
        
    except Exception as e:
        print(f"✗ Generation limit check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_select_best_option(orchestrator):
    """Test option selection logic."""
    print("\n=== Testing Option Selection ===")
    
    try:
        # Create mock options
        options = [
            {
                "angle": "Share a personal experience about overcoming a technical challenge",
                "hook": "Last week, I faced a production issue that taught me a valuable lesson",
                "target_audience": "Software engineers and tech leads",
                "content_theme": "Problem-solving in production",
                "estimated_engagement": "discussion"
            },
            {
                "angle": "Discuss emerging trends in cloud architecture",
                "hook": "The future of cloud computing is changing faster than we think",
                "target_audience": "Cloud architects and CTOs",
                "content_theme": "Cloud architecture trends",
                "estimated_engagement": "shares"
            },
            {
                "angle": "Provide practical tips for team leadership",
                "hook": "Here are 3 things I learned about leading remote teams",
                "target_audience": "Engineering managers",
                "content_theme": "Remote team leadership",
                "estimated_engagement": "reactions"
            }
        ]
        
        # Create mock profile
        class MockProfile:
            profile_id = "test-profile"
            class identity:
                target_audience = "Software engineers and tech leaders"
        
        profile = MockProfile()
        
        # Select best option
        selected = await orchestrator.select_best_option(options, profile)
        
        print(f"✓ Option selection completed")
        print(f"  - Options evaluated: {len(options)}")
        print(f"  - Selected theme: {selected.get('content_theme', 'unknown')}")
        print(f"  - Selected angle: {selected.get('angle', 'unknown')[:60]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Option selection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_daily_post_result():
    """Test DailyPostResult dataclass."""
    print("\n=== Testing DailyPostResult ===")
    
    try:
        from datetime import datetime
        
        # Create a result
        result = DailyPostResult(
            success=True,
            post_draft=None,
            options_generated=3,
            selected_option=None,
            delivery_status="pending",
            error=None,
            timestamp=datetime.utcnow()
        )
        
        # Convert to dict
        result_dict = result.to_dict()
        
        print(f"✓ DailyPostResult created successfully")
        print(f"  - Success: {result.success}")
        print(f"  - Options generated: {result.options_generated}")
        print(f"  - Delivery status: {result.delivery_status}")
        print(f"  - Dictionary keys: {list(result_dict.keys())}")
        
        return True
        
    except Exception as e:
        print(f"✗ DailyPostResult test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Content Orchestrator Verification")
    print("=" * 60)
    
    results = []
    
    # Test 1: Initialization
    orchestrator = test_orchestrator_initialization()
    results.append(orchestrator is not None)
    
    if orchestrator:
        # Test 2: Generation limit check
        result = await test_check_generation_limit(orchestrator)
        results.append(result)
        
        # Test 3: Option selection
        result = await test_select_best_option(orchestrator)
        results.append(result)
    else:
        results.extend([False, False])
    
    # Test 4: DailyPostResult
    result = test_daily_post_result()
    results.append(result)
    
    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
    else:
        print(f"✗ {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
