"""Verify Content Strategy Agent structure without requiring LLM calls."""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from linkedin_content_assistant.agents import (
    ContentStrategyAgent,
    PostOption,
    ContentStrategyOutput,
    ProfileContext,
    AgentType,
    ValidationStatus,
    AgentOutput
)


def test_agent_imports():
    """Test that all agent classes can be imported."""
    print("1. Testing agent imports...")
    try:
        assert ContentStrategyAgent is not None
        assert PostOption is not None
        assert ContentStrategyOutput is not None
        assert ProfileContext is not None
        assert AgentType is not None
        print("   ✓ All agent classes imported successfully")
        return True
    except Exception as e:
        print(f"   ✗ Import failed: {e}")
        return False


def test_post_option_creation():
    """Test PostOption data class."""
    print("\n2. Testing PostOption creation...")
    try:
        option = PostOption(
            angle="Test angle",
            hook="Test hook",
            target_audience="Test audience",
            content_theme="Test theme",
            estimated_engagement="discussion"
        )
        
        assert option.angle == "Test angle"
        assert option.hook == "Test hook"
        
        # Test to_dict
        option_dict = option.to_dict()
        assert isinstance(option_dict, dict)
        assert option_dict["angle"] == "Test angle"
        
        print("   ✓ PostOption creation and serialization works")
        return True
    except Exception as e:
        print(f"   ✗ PostOption test failed: {e}")
        return False


def test_content_strategy_output():
    """Test ContentStrategyOutput data class."""
    print("\n3. Testing ContentStrategyOutput...")
    try:
        options = [
            PostOption("angle1", "hook1", "audience1", "theme1", "discussion"),
            PostOption("angle2", "hook2", "audience2", "theme2", "shares"),
            PostOption("angle3", "hook3", "audience3", "theme3", "reactions")
        ]
        
        output = ContentStrategyOutput(
            post_options=options,
            reasoning="Test reasoning",
            profile_alignment={"test": "alignment"}
        )
        
        assert len(output.post_options) == 3
        assert output.reasoning == "Test reasoning"
        
        # Test to_dict
        output_dict = output.to_dict()
        assert isinstance(output_dict, dict)
        assert len(output_dict["post_options"]) == 3
        
        print("   ✓ ContentStrategyOutput creation and serialization works")
        return True
    except Exception as e:
        print(f"   ✗ ContentStrategyOutput test failed: {e}")
        return False


def test_profile_context():
    """Test ProfileContext creation."""
    print("\n4. Testing ProfileContext...")
    try:
        context = ProfileContext(
            profile_id="test-profile",
            identity={
                "headline": "Test Headline",
                "seniority": "senior",
                "primary_domains": ["Domain1", "Domain2"]
            },
            behavior={
                "active_topics": ["Topic1", "Topic2"],
                "vocabulary_bias": "professional"
            },
            version=1,
            last_updated=datetime.now()
        )
        
        assert context.profile_id == "test-profile"
        assert context.get_identity_field("headline") == "Test Headline"
        assert context.get_behavior_field("vocabulary_bias") == "professional"
        
        print("   ✓ ProfileContext creation and field access works")
        return True
    except Exception as e:
        print(f"   ✗ ProfileContext test failed: {e}")
        return False


def test_agent_validation():
    """Test agent output validation without LLM."""
    print("\n5. Testing agent output validation...")
    try:
        # Create mock agent output
        output = AgentOutput(
            agent_type=AgentType.CONTENT_STRATEGY,
            content={
                "post_options": [
                    {
                        "angle": "Test angle 1",
                        "hook": "Test hook 1",
                        "target_audience": "Test audience 1",
                        "content_theme": "Test theme 1",
                        "estimated_engagement": "discussion"
                    },
                    {
                        "angle": "Test angle 2",
                        "hook": "Test hook 2",
                        "target_audience": "Test audience 2",
                        "content_theme": "Test theme 2",
                        "estimated_engagement": "shares"
                    },
                    {
                        "angle": "Test angle 3",
                        "hook": "Test hook 3",
                        "target_audience": "Test audience 3",
                        "content_theme": "Test theme 3",
                        "estimated_engagement": "reactions"
                    }
                ],
                "reasoning": "Test reasoning for validation",
                "profile_alignment": {
                    "positioning_match": "Good match",
                    "audience_relevance": "Highly relevant",
                    "domain_expertise": "Strong expertise"
                }
            },
            metadata={"test": "metadata"},
            requires_approval=True,
            confidence_score=0.85
        )
        
        # Create a mock agent for validation (without LLM factory)
        from linkedin_content_assistant.agents.content_strategy import ContentStrategyAgent
        from linkedin_content_assistant.llm.factory import LLMFactory
        from linkedin_content_assistant.llm.config import LLMConfig, ProviderConfig
        from linkedin_content_assistant.llm.base import LLMProvider
        
        # Create minimal config
        config = LLMConfig(
            primary_provider=ProviderConfig(
                provider=LLMProvider.BEDROCK_CLAUDE,
                model="test-model"
            ),
            fallback_providers=[],
            enable_fallback=False
        )
        
        agent = ContentStrategyAgent(LLMFactory(config))
        
        # Validate the output
        validation = agent.validate_output(output)
        
        assert validation is not None
        assert validation.status == ValidationStatus.REQUIRES_APPROVAL
        assert len(validation.errors) == 0
        
        print(f"   ✓ Agent validation works")
        print(f"     - Status: {validation.status.value}")
        print(f"     - Errors: {len(validation.errors)}")
        print(f"     - Warnings: {len(validation.warnings)}")
        return True
    except Exception as e:
        print(f"   ✗ Validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_required_context_fields():
    """Test that agent specifies required context fields."""
    print("\n6. Testing required context fields...")
    try:
        from linkedin_content_assistant.llm.factory import LLMFactory
        from linkedin_content_assistant.llm.config import LLMConfig, ProviderConfig
        from linkedin_content_assistant.llm.base import LLMProvider
        
        config = LLMConfig(
            primary_provider=ProviderConfig(
                provider=LLMProvider.BEDROCK_CLAUDE,
                model="test-model"
            ),
            fallback_providers=[],
            enable_fallback=False
        )
        
        agent = ContentStrategyAgent(LLMFactory(config))
        required_fields = agent.get_required_context_fields()
        
        assert isinstance(required_fields, list)
        assert len(required_fields) > 0
        assert "identity.headline" in required_fields
        assert "behavior.vocabulary_bias" in required_fields
        
        print(f"   ✓ Agent specifies {len(required_fields)} required context fields")
        print(f"     - Fields: {', '.join(required_fields[:3])}...")
        return True
    except Exception as e:
        print(f"   ✗ Required fields test failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Content Strategy Agent Structure Verification")
    print("=" * 60)
    
    tests = [
        test_agent_imports,
        test_post_option_creation,
        test_content_strategy_output,
        test_profile_context,
        test_agent_validation,
        test_required_context_fields
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✓ All {total} tests passed!")
        print("=" * 60)
        return 0
    else:
        print(f"✗ {passed}/{total} tests passed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
