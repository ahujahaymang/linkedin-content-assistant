"""Manual verification script for Drafting Agent."""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from linkedin_content_assistant.agents.drafting import (
    DraftingAgent, ContentIdea, LinkedInPost, DraftingOutput
)
from linkedin_content_assistant.agents.base import ProfileContext, AgentType
from linkedin_content_assistant.llm.factory import LLMFactory
from linkedin_content_assistant.llm.config import LLMConfig, ProviderConfig
from linkedin_content_assistant.llm.base import LLMProvider
from linkedin_content_assistant.profiles.models import IdentityConfig, BehaviorConfig


def test_drafting_agent_structure():
    """Test that DraftingAgent has the expected structure."""
    print("Testing Drafting Agent structure...")
    
    # Test ContentIdea
    idea_dict = {
        "angle": "Personal experience with cloud migration",
        "hook": "Last week, I migrated our entire infrastructure to AWS",
        "target_audience": "Software engineers and tech leads",
        "content_theme": "Cloud migration best practices",
        "estimated_engagement": "discussion"
    }
    
    idea = ContentIdea.from_dict(idea_dict)
    assert idea.angle == "Personal experience with cloud migration"
    assert idea.hook == "Last week, I migrated our entire infrastructure to AWS"
    print("✓ ContentIdea.from_dict() works")
    
    # Test LinkedInPost
    post = LinkedInPost(
        content="Test post content",
        hashtags=["#CloudComputing", "#AWS", "#DevOps"],
        call_to_action="What's your experience with cloud migration?",
        estimated_length=100,
        tone_analysis={"formality": "professional"},
        formatting_notes=["Line breaks", "Hashtags"]
    )
    
    post_dict = post.to_dict()
    assert post_dict["content"] == "Test post content"
    assert len(post_dict["hashtags"]) == 3
    print("✓ LinkedInPost.to_dict() works")
    
    # Test DraftingOutput
    output = DraftingOutput(
        linkedin_post=post,
        content_idea_used=idea,
        tone_compliance={"vocabulary_match": "Good"},
        formatting_applied=["Line breaks"]
    )
    
    output_dict = output.to_dict()
    assert "linkedin_post" in output_dict
    assert "content_idea_used" in output_dict
    print("✓ DraftingOutput.to_dict() works")
    
    print("\n✅ All structure tests passed!")


def test_drafting_agent_initialization():
    """Test that DraftingAgent can be initialized."""
    print("\nTesting Drafting Agent initialization...")
    
    # Create mock LLM factory with proper config
    config = LLMConfig(
        primary_provider=ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1"
        ),
        enable_fallback=False
    )
    llm_factory = LLMFactory(config)
    
    # Initialize agent
    agent = DraftingAgent(llm_factory)
    
    assert agent.agent_type == AgentType.DRAFTING
    assert agent.llm_factory is not None
    print("✓ DraftingAgent initialized successfully")
    
    # Test required context fields
    required_fields = agent.get_required_context_fields()
    assert "identity.headline" in required_fields
    assert "identity.seniority" in required_fields
    assert "behavior.vocabulary_bias" in required_fields
    print(f"✓ Required context fields: {len(required_fields)} fields")
    
    print("\n✅ Initialization tests passed!")


def test_drafting_agent_validation():
    """Test that DraftingAgent validation works."""
    print("\nTesting Drafting Agent validation...")
    
    from linkedin_content_assistant.agents.base import AgentOutput
    
    # Create mock LLM factory with proper config
    config = LLMConfig(
        primary_provider=ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1"
        ),
        enable_fallback=False
    )
    llm_factory = LLMFactory(config)
    
    agent = DraftingAgent(llm_factory)
    
    # Test valid output
    valid_output = AgentOutput(
        agent_type=AgentType.DRAFTING,
        content={
            "linkedin_post": {
                "content": "This is a test LinkedIn post with sufficient length to pass validation.",
                "hashtags": ["#Test", "#LinkedIn", "#Content"],
                "call_to_action": "What do you think?",
                "estimated_length": 70,
                "tone_analysis": {"formality": "professional"},
                "formatting_notes": ["Line breaks"]
            },
            "tone_compliance": {"vocabulary_match": "Good"},
            "formatting_applied": ["Line breaks"]
        },
        metadata={},
        requires_approval=True,
        confidence_score=0.8
    )
    
    result = agent.validate_output(valid_output)
    print(f"✓ Validation result: {result.status}")
    if result.errors:
        print(f"  Errors: {result.errors}")
    if result.warnings:
        print(f"  Warnings: {result.warnings}")
    
    # Test invalid output (missing linkedin_post)
    invalid_output = AgentOutput(
        agent_type=AgentType.DRAFTING,
        content={},
        metadata={},
        requires_approval=True,
        confidence_score=0.5
    )
    
    result = agent.validate_output(invalid_output)
    assert len(result.errors) > 0
    print(f"✓ Invalid output correctly rejected: {result.errors[0]}")
    
    print("\n✅ Validation tests passed!")


def test_prompt_building():
    """Test that prompt building methods work."""
    print("\nTesting prompt building...")
    
    # Create mock LLM factory with proper config
    config = LLMConfig(
        primary_provider=ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1"
        ),
        enable_fallback=False
    )
    llm_factory = LLMFactory(config)
    
    agent = DraftingAgent(llm_factory)
    
    # Create mock context
    identity = IdentityConfig(
        headline="Senior Software Engineer | Cloud Architecture",
        seniority="senior",
        primary_domains=["Cloud Computing", "Software Architecture"],
        target_audience="Software engineers and tech leads",
        positioning="Practical insights on building scalable systems",
        excluded_topics=["Politics", "Religion"]
    )
    
    behavior = BehaviorConfig(
        active_topics=["AWS", "Cloud Architecture"],
        hook_patterns=["Personal experience"],
        posting_windows=[],
        emoji_frequency="moderate",
        comment_depth="detailed",
        vocabulary_bias="professional"
    )
    
    context = ProfileContext(
        profile_id="test-profile",
        version=1,
        identity=identity.model_dump(),
        behavior=behavior.model_dump(),
        last_updated=datetime.now()
    )
    
    # Test system prompt building
    system_prompt = agent._build_system_prompt(context)
    assert "LinkedIn Content Drafting AI" in system_prompt
    assert "Senior Software Engineer" in system_prompt
    assert "professional" in system_prompt
    print("✓ System prompt built successfully")
    print(f"  Length: {len(system_prompt)} characters")
    
    # Test user prompt building
    idea = ContentIdea(
        angle="Personal experience with cloud migration",
        hook="Last week, I migrated our entire infrastructure",
        target_audience="Software engineers",
        content_theme="Cloud migration",
        estimated_engagement="discussion"
    )
    
    user_prompt = agent._build_user_prompt(idea, context, [])
    assert "Personal experience with cloud migration" in user_prompt
    assert "Cloud migration" in user_prompt
    print("✓ User prompt built successfully")
    print(f"  Length: {len(user_prompt)} characters")
    
    print("\n✅ Prompt building tests passed!")


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Drafting Agent Verification")
    print("=" * 60)
    
    try:
        test_drafting_agent_structure()
        test_drafting_agent_initialization()
        test_drafting_agent_validation()
        test_prompt_building()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nThe Drafting Agent has been successfully copied and verified.")
        print("Key capabilities:")
        print("  • Converts content ideas into LinkedIn posts")
        print("  • Validates post structure and content")
        print("  • Builds context-aware prompts")
        print("  • Supports style matching and formatting")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
