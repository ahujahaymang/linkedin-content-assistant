#!/usr/bin/env python3
"""Test script to see raw LLM output."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from linkedin_content_assistant.llm.factory import LLMFactory
from linkedin_content_assistant.llm.config import LLMConfig, ProviderConfig
from linkedin_content_assistant.llm.base import LLMProvider

async def main():
    # Create LLM config
    config = LLMConfig(
        primary_provider=ProviderConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
            api_key=os.getenv('OPENAI_API_KEY'),
            max_tokens=4000,
            temperature=0.75,
            timeout=30,
            retry_attempts=3,
            retry_delay=5
        ),
        fallback_providers=[],
        enable_fallback=False
    )
    
    # Create factory
    factory = LLMFactory(config)
    
    # Test prompt
    system_prompt = "You are a helpful assistant that generates JSON responses."
    user_prompt = """Generate 3 LinkedIn post options in JSON format with this structure:
{
  "post_options": [
    {
      "content_theme": "string",
      "angle": "string",
      "hook": "string",
      "key_points": ["string"],
      "call_to_action": "string",
      "estimated_engagement": "string"
    }
  ]
}"""
    
    # Generate
    print("Sending request to LLM...")
    response = await factory.generate_with_system(system_prompt, user_prompt)
    
    print("\n=== RAW LLM RESPONSE ===")
    print(response.content)
    print("\n=== END RESPONSE ===")
    
    # Try to parse as JSON
    import json
    try:
        parsed = json.loads(response.content)
        print("\n✓ Response is valid JSON")
        print(f"Keys: {list(parsed.keys())}")
        if "post_options" in parsed:
            print(f"Number of post_options: {len(parsed['post_options'])}")
    except json.JSONDecodeError as e:
        print(f"\n✗ Response is NOT valid JSON: {e}")

if __name__ == "__main__":
    asyncio.run(main())
