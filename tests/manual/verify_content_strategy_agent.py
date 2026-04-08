"""Manual verification script for Content Strategy Agent."""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from linkedin_content_assistant.agents import (
    ContentStrategyAgent,
    ProfileContext,
    AgentType
)
from linkedin_content_assistant.llm.factory import LLMFactory
from linkedin_content_assistant.llm.config import LLMConfig, ProviderConfig
from linkedin_content_assistant.llm.base import LLMProvider
from linkedin_content_assistant.memory.store import InMemoryStore


def create_test_profile_context() -> ProfileContext:
    """Create a test profile context."""
    return ProfileContext(
        profile_id="test-profile",
        identity={
            "headline": "Senior Software Engineer | Cloud Architecture | AI/ML",
            "seniority": "senior",
            "primary_domains": ["Cloud Computing", "Machine Learning", "Software Architecture"],
            "target_audience": "Software engineers and tech leaders",
            "positioning": "Practical insights on building scalable systems",
            "excluded_topics": ["Politics", "Religion"]
        },
        behavior={
            "active_topics": ["AWS architecture", "ML deployment", "Team leadership"],
            "hook_patterns": ["Personal experience", "Contrarian take", "Practical tip"],
            "vocabulary_bias": "professional"
        },
        version=1,
        last_updated=datetime.now()
    )


def main():
    """Test Content Strategy Agent execution."""
    print("=" * 60)
    print("Content Strategy Agent Verification")
    print("=" * 60)
    
    # Initialize LLM Factory
    print("\n1. Initializing LLM Factory...")
    try:
        # Create LLM configuration
        primary_config = ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-west-2"
        )
        
        llm_config = LLMConfig(
            primary_provider=primary_config,
            fallback_providers=[],
            enable_fallback=False
        )
        
        llm_factory = LLMFactory(llm_config)
        print("   ✓ LLM Factory initialized")
    except Exception as e:
        print(f"   ✗ Failed to initialize LLM Factory: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Initialize Memory Store
    print("\n2. Initializing Memory Store...")
    try:
        memory_store = InMemoryStore()
        print("   ✓ Memory Store initialized")
    except Exception as e:
        print(f"   ✗ Failed to initialize Memory Store: {e}")
        return 1
    
    # Initialize Content Strategy Agent
    print("\n3. Initializing Content Strategy Agent...")
    try:
        agent = ContentStrategyAgent(llm_factory)
        print(f"   ✓ Agent initialized with type: {agent.agent_type.value}")
    except Exception as e:
        print(f"   ✗ Failed to initialize agent: {e}")
        return 1
    
    # Create test profile context
    print("\n4. Creating test profile context...")
    try:
        context = create_test_profile_context()
        print(f"   ✓ Profile context created for: {context.profile_id}")
        print(f"     - Headline: {context.identity['headline']}")
        print(f"     - Domains: {', '.join(context.identity['primary_domains'])}")
    except Exception as e:
        print(f"   ✗ Failed to create profile context: {e}")
        return 1
    
    # Execute agent
    print("\n5. Executing Content Strategy Agent...")
    print("   (This will call the LLM to generate 3 post options)")
    try:
        output = agent.execute(context, memory_store)
        print(f"   ✓ Agent execution completed")
        print(f"     - Confidence Score: {output.confidence_score:.2f}")
        print(f"     - Requires Approval: {output.requires_approval}")
        print(f"     - LLM Provider: {output.metadata.get('llm_provider')}")
        print(f"     - LLM Model: {output.metadata.get('llm_model')}")
    except Exception as e:
        print(f"   ✗ Agent execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Validate output
    print("\n6. Validating agent output...")
    try:
        validation = agent.validate_output(output)
        print(f"   ✓ Validation completed")
        print(f"     - Status: {validation.status.value}")
        print(f"     - Errors: {len(validation.errors)}")
        print(f"     - Warnings: {len(validation.warnings)}")
        
        if validation.errors:
            print("\n   Errors:")
            for error in validation.errors:
                print(f"     - {error}")
        
        if validation.warnings:
            print("\n   Warnings:")
            for warning in validation.warnings:
                print(f"     - {warning}")
    except Exception as e:
        print(f"   ✗ Validation failed: {e}")
        return 1
    
    # Display post options
    print("\n7. Generated Post Options:")
    print("-" * 60)
    try:
        content = output.content
        post_options = content.get("post_options", [])
        
        for i, option in enumerate(post_options, 1):
            print(f"\n   Option {i}:")
            print(f"   - Angle: {option.get('angle', 'N/A')}")
            print(f"   - Hook: {option.get('hook', 'N/A')}")
            print(f"   - Target Audience: {option.get('target_audience', 'N/A')}")
            print(f"   - Content Theme: {option.get('content_theme', 'N/A')}")
            print(f"   - Estimated Engagement: {option.get('estimated_engagement', 'N/A')}")
        
        print(f"\n   Reasoning: {content.get('reasoning', 'N/A')}")
        
        profile_alignment = content.get('profile_alignment', {})
        if profile_alignment:
            print("\n   Profile Alignment:")
            for key, value in profile_alignment.items():
                print(f"   - {key}: {value}")
    except Exception as e:
        print(f"   ✗ Failed to display post options: {e}")
        return 1
    
    print("\n" + "=" * 60)
    print("✓ Content Strategy Agent verification completed successfully!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
