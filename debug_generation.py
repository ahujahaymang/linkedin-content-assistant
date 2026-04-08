#!/usr/bin/env python3
"""Debug script to see actual generation output."""

import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from linkedin_content_assistant.config.config import load_config
from linkedin_content_assistant.profiles.manager import ProfileManager
from linkedin_content_assistant.memory.store import InMemoryStore
from linkedin_content_assistant.llm.factory import LLMFactory
from linkedin_content_assistant.agents.content_strategy import ContentStrategyAgent
from linkedin_content_assistant.main import _create_llm_config

async def main():
    # Load config
    config = load_config()
    
    # Initialize components
    profile_manager = ProfileManager(Path(config.profiles.directory))
    memory_store = InMemoryStore(Path(config.memory.directory))
    llm_config = _create_llm_config(config)
    llm_factory = LLMFactory(llm_config)
    
    # Create agent
    agent = ContentStrategyAgent(llm_factory)
    
    # Load profile
    profile = profile_manager.load_profile("example-senior-engineer")
    context = profile.to_context()
    
    print("\n=== EXECUTING CONTENT STRATEGY AGENT ===\n")
    
    try:
        output = await agent.execute(context, memory_store)
        
        print("\n=== AGENT OUTPUT ===")
        print(f"Agent Type: {output.agent_type}")
        print(f"Requires Approval: {output.requires_approval}")
        print(f"Confidence Score: {output.confidence_score}")
        print(f"\nContent Keys: {list(output.content.keys())}")
        
        if "post_options" in output.content:
            print(f"\nNumber of post_options: {len(output.content['post_options'])}")
            for i, option in enumerate(output.content['post_options'], 1):
                print(f"\n--- Option {i} ---")
                print(f"Keys: {list(option.keys())}")
                for key, value in option.items():
                    print(f"  {key}: {value[:100] if isinstance(value, str) and len(value) > 100 else value}")
        
        # Validate
        print("\n=== VALIDATION ===")
        validation = agent.validate_output(output)
        print(f"Status: {validation.status}")
        print(f"Errors: {validation.errors}")
        print(f"Warnings: {validation.warnings}")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
