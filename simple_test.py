#!/usr/bin/env python3
"""Simple test to see LLM response."""

import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

from linkedin_content_assistant.llm.factory import LLMFactory
from linkedin_content_assistant.llm.config import LLMConfig, ProviderConfig
from linkedin_content_assistant.llm.base import LLMProvider

async def main():
    config = LLMConfig(
        primary_provider=ProviderConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
            api_key=os.getenv('OPENAI_API_KEY'),
            max_tokens=1500,
            temperature=0.7,
            timeout=30,
            retry_attempts=3,
            retry_delay=5
        ),
        fallback_providers=[],
        enable_fallback=False
    )
    
    factory = LLMFactory(config)
    
    system_prompt = """You are a LinkedIn Content Strategy AI that generates post ideas for professionals.

PROFILE CONTEXT:
- Professional Identity: Senior Software Engineer
- Seniority Level: Senior
- Primary Domains: Software Engineering, Cloud Architecture
- Target Audience: Software engineers and tech leaders
- Professional Positioning: Technical thought leader
- Excluded Topics: Politics, Religion

BEHAVIORAL PREFERENCES:
- Active Topics: Software best practices, Cloud architecture, Team leadership
- Preferred Hook Patterns: Question-based, Story-based
- Vocabulary Style: Professional but approachable

TASK: Generate exactly 3 diverse post options that align with this professional profile.

REQUIREMENTS:
1. Each post option must have a unique angle and approach
2. Content must align with the professional positioning and domains
3. Avoid all excluded topics completely
4. Target the specified audience appropriately
5. Use the preferred vocabulary style and hook patterns when possible
6. Ensure content is authentic to the seniority level and expertise

OUTPUT FORMAT: Return a valid JSON object with this exact structure:
{
    "post_options": [
        {
            "angle": "The unique perspective or approach for this post",
            "hook": "The opening hook to grab attention",
            "target_audience": "Specific audience segment this targets",
            "content_theme": "The main theme or topic category",
            "estimated_engagement": "Expected engagement type (discussion/shares/reactions)"
        },
        // ... 2 more options
    ],
    "reasoning": "Brief explanation of why these options align with the profile",
    "profile_alignment": {
        "positioning_match": "How options align with professional positioning",
        "audience_relevance": "Why these will resonate with target audience",
        "domain_expertise": "How options showcase domain knowledge"
    }
}"""
    
    user_prompt = "Generate 3 LinkedIn post options based on the profile context above."
    
    print("Generating...")
    response = await factory.generate_with_system(system_prompt, user_prompt)
    
    print("\n=== RAW RESPONSE ===")
    print(response.content)
    print("\n=== PARSED ===")
    
    try:
        data = json.loads(response.content)
        print(f"✓ Valid JSON")
        print(f"Keys: {list(data.keys())}")
        
        if "post_options" in data:
            print(f"\nPost options: {len(data['post_options'])}")
            for i, opt in enumerate(data['post_options'], 1):
                print(f"\nOption {i}:")
                print(f"  Keys: {list(opt.keys())}")
                print(f"  Has target_audience: {'target_audience' in opt}")
                if 'target_audience' in opt:
                    print(f"  target_audience: {opt['target_audience']}")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
