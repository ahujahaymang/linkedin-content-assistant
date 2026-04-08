"""Drafting Agent for converting content ideas into LinkedIn-ready posts."""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .base import (
    LinkedInAgent, AgentType, AgentOutput, ValidationResult, 
    ValidationStatus, ProfileContext, StatelessAgentMixin
)
from ..llm.factory import LLMFactory
from ..llm.base import LLMError

logger = logging.getLogger(__name__)


@dataclass
class ContentIdea:
    """Input content idea for drafting."""
    angle: str
    hook: str
    target_audience: str
    content_theme: str
    estimated_engagement: str
    additional_context: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentIdea':
        """Create ContentIdea from dictionary."""
        return cls(
            angle=data.get("angle", ""),
            hook=data.get("hook", ""),
            target_audience=data.get("target_audience", ""),
            content_theme=data.get("content_theme", ""),
            estimated_engagement=data.get("estimated_engagement", ""),
            additional_context=data.get("additional_context")
        )


@dataclass
class LinkedInPost:
    """A LinkedIn-ready post with formatting and metadata."""
    content: str
    hashtags: List[str]
    call_to_action: Optional[str]
    estimated_length: int
    tone_analysis: Dict[str, Any]
    formatting_notes: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "content": self.content,
            "hashtags": self.hashtags,
            "call_to_action": self.call_to_action,
            "estimated_length": self.estimated_length,
            "tone_analysis": self.tone_analysis,
            "formatting_notes": self.formatting_notes
        }


@dataclass
class DraftingOutput:
    """Output from Drafting Agent."""
    linkedin_post: LinkedInPost
    content_idea_used: ContentIdea
    tone_compliance: Dict[str, Any]
    formatting_applied: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "linkedin_post": self.linkedin_post.to_dict(),
            "content_idea_used": {
                "angle": self.content_idea_used.angle,
                "hook": self.content_idea_used.hook,
                "target_audience": self.content_idea_used.target_audience,
                "content_theme": self.content_idea_used.content_theme,
                "estimated_engagement": self.content_idea_used.estimated_engagement
            },
            "tone_compliance": self.tone_compliance,
            "formatting_applied": self.formatting_applied
        }


class DraftingAgent(StatelessAgentMixin, LinkedInAgent):
    """Agent that converts content ideas into LinkedIn-ready posts."""
    
    def __init__(self, llm_factory: LLMFactory):
        super().__init__(AgentType.DRAFTING)
        self.llm_factory = llm_factory
    
    async def execute(self, context: ProfileContext, memory: Any, content_idea: Dict[str, Any]) -> AgentOutput:
        """Convert content idea into LinkedIn-ready post.
        
        Args:
            context: Profile-specific context and configuration
            memory: Memory store for retrieving relevant history
            content_idea: Content idea to convert into post
            
        Returns:
            AgentOutput with LinkedIn-ready post and metadata
        """
        try:
            # Parse content idea
            idea = ContentIdea.from_dict(content_idea)
            
            # Get recent posts to avoid repetition
            recent_posts = self._get_recent_posts(memory, context.profile_id)
            
            # Build system prompt for drafting
            system_prompt = self._build_system_prompt(context)
            
            # Build user prompt with content idea and constraints
            user_prompt = self._build_user_prompt(idea, context, recent_posts)
            
            # Generate LinkedIn post using LLM
            response = await self.llm_factory.generate_with_system(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8,
                max_tokens=2000
            )
            
            # Parse and validate response
            drafting_output = self._parse_response(response.content, idea)
            
            # Create agent output
            agent_output = AgentOutput(
                agent_type=self.agent_type,
                content=drafting_output.to_dict(),
                metadata={
                    "llm_provider": response.provider.value,
                    "llm_model": response.model,
                    "profile_id": context.profile_id,
                    "profile_version": context.version,
                    "content_theme": idea.content_theme,
                    "target_audience": idea.target_audience,
                    "recent_posts_count": len(recent_posts)
                },
                requires_approval=True,
                confidence_score=self._calculate_confidence_score(drafting_output, context)
            )
            
            return agent_output
            
        except Exception as e:
            logger.error(f"Drafting Agent execution failed: {e}")
            raise
    
    def validate_output(self, output: AgentOutput) -> ValidationResult:
        """Validate drafting output against policies and constraints.
        
        Args:
            output: Agent output to validate
            
        Returns:
            ValidationResult with status and any errors/warnings
        """
        errors = []
        warnings = []
        
        try:
            content = output.content
            
            # Validate structure
            if "linkedin_post" not in content:
                errors.append("Missing linkedin_post in output")
                return ValidationResult(ValidationStatus.INVALID, errors, warnings)
            
            linkedin_post = content["linkedin_post"]
            
            # Validate post content
            post_errors = self._validate_linkedin_post(linkedin_post)
            errors.extend(post_errors)
            
            # Validate tone compliance
            if "tone_compliance" in content:
                tone_warnings = self._validate_tone_compliance(content["tone_compliance"])
                warnings.extend(tone_warnings)
            
            # Check post length
            post_content = linkedin_post.get("content", "")
            if len(post_content) > 3000:  # LinkedIn limit
                errors.append("Post content exceeds LinkedIn character limit (3000)")
            elif len(post_content) > 1300:  # Optimal length
                warnings.append("Post content is longer than optimal length (1300 characters)")
            
            # Check for excessive hashtags
            hashtags = linkedin_post.get("hashtags", [])
            if len(hashtags) > 5:
                warnings.append("More than 5 hashtags may reduce engagement")
            
            # Determine validation status
            if errors:
                status = ValidationStatus.INVALID
            else:
                status = ValidationStatus.REQUIRES_APPROVAL
            
            return ValidationResult(status, errors, warnings)
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return ValidationResult(ValidationStatus.INVALID, errors, warnings)
    
    def get_required_context_fields(self) -> List[str]:
        """Get list of required context fields for drafting."""
        return [
            "identity.headline",
            "identity.seniority", 
            "identity.primary_domains",
            "identity.target_audience",
            "identity.excluded_topics",
            "identity.positioning",
            "behavior.vocabulary_bias",
            "behavior.emoji_frequency",
            "behavior.comment_depth"
        ]
    
    def get_memory_query_params(self, context: ProfileContext) -> Dict[str, Any]:
        """Get parameters for querying relevant post history."""
        return {
            "profile_id": context.profile_id,
            "event_type": "post",
            "limit": 5,  # Last 5 posts to avoid repetition
            "order_by": "timestamp",
            "order": "desc"
        }
    
    def _get_recent_posts(self, memory: Any, profile_id: str) -> List[Dict[str, Any]]:
        """Get recent posts from memory store."""
        try:
            if hasattr(memory, 'query_events'):
                events = memory.query_events(
                    profile_id=profile_id,
                    event_type="post",
                    limit=5
                )
                return [event.content for event in events if hasattr(event, 'content')]
            else:
                logger.warning("Memory store does not support query_events")
                return []
        except Exception as e:
            logger.warning(f"Failed to retrieve recent posts: {e}")
            return []
    
    def _build_system_prompt(self, context: ProfileContext) -> str:
        """Build system prompt for post drafting."""
        identity = context.identity
        behavior = context.behavior
        
        return f"""You are a LinkedIn Content Drafting AI that converts content ideas into engaging, professional LinkedIn posts.

PROFILE CONTEXT:
- Professional Identity: {identity.get('headline', 'Professional')}
- Seniority Level: {identity.get('seniority', 'Unknown')}
- Primary Domains: {', '.join(identity.get('primary_domains', []))}
- Target Audience: {identity.get('target_audience', 'Professional network')}
- Professional Positioning: {identity.get('positioning', 'Industry professional')}
- Excluded Topics: {', '.join(identity.get('excluded_topics', []))}

TONE AND STYLE RULES:
- Vocabulary Style: {behavior.get('vocabulary_bias', 'professional')}
- Emoji Usage: {behavior.get('emoji_frequency', 'moderate')}
- Detail Level: {behavior.get('comment_depth', 'detailed')}

LINKEDIN POST REQUIREMENTS:
1. Start with an engaging hook that matches the provided angle
2. Develop the content with authentic insights and expertise
3. Use appropriate formatting (line breaks, bullet points if needed)
4. Include relevant hashtags (3-5 maximum)
5. End with a call-to-action or engaging question
6. Stay within 1300 characters for optimal engagement
7. Maintain professional tone while being personable
8. Avoid generic corporate speak
9. Include personal insights or experiences when appropriate
10. Ensure content aligns with professional positioning

FORMATTING GUIDELINES (LINKEDIN-FRIENDLY):
- Use line breaks for readability (double line breaks between sections)
- DO NOT use markdown formatting like **bold** or *italic* - LinkedIn doesn't support it
- Use emojis sparingly for emphasis (✅ ❌ 💡 🚀 ⚡ 📊 etc.)
- Use bullet points with symbols: • → ✓ ➜ ▸ for lists
- Use CAPS for emphasis on single words only (not entire sentences)
- Use numbers for ordered lists: 1. 2. 3.
- Keep paragraphs short (2-3 sentences max)
- Avoid excessive punctuation or ALL CAPS sentences

OUTPUT FORMAT: Return a valid JSON object with this exact structure:
{{
    "linkedin_post": {{
        "content": "The complete LinkedIn post content with proper formatting",
        "hashtags": ["hashtag1", "hashtag2", "hashtag3"],
        "call_to_action": "The specific call-to-action or question",
        "estimated_length": 1250,
        "tone_analysis": {{
            "formality": "professional-casual",
            "engagement_style": "conversational",
            "expertise_level": "senior"
        }},
        "formatting_notes": ["Used line breaks for readability", "Included personal insight", "No markdown formatting"]
    }},
    "tone_compliance": {{
        "vocabulary_match": "Matches technical vocabulary preference",
        "emoji_usage": "Moderate emoji usage as requested",
        "detail_level": "Detailed explanation provided"
    }},
    "formatting_applied": ["Line breaks", "Emoji emphasis", "Bullet points with symbols", "Hashtag optimization"]
}}

CRITICAL: The post content must be copy-paste ready for LinkedIn. Do NOT use markdown syntax like **bold** or *italic*. Use plain text with emojis, symbols, and line breaks only."""
    
    def _build_user_prompt(self, idea: ContentIdea, context: ProfileContext, recent_posts: List[Dict[str, Any]]) -> str:
        """Build user prompt with content idea and constraints."""
        prompt = f"""Convert this content idea into a LinkedIn post:

CONTENT IDEA:
- Angle: {idea.angle}
- Hook: {idea.hook}
- Target Audience: {idea.target_audience}
- Content Theme: {idea.content_theme}
- Expected Engagement: {idea.estimated_engagement}"""
        
        if idea.additional_context:
            prompt += f"\n- Additional Context: {idea.additional_context}"
        
        if recent_posts:
            recent_themes = []
            for post in recent_posts[:3]:  # Last 3 posts
                if isinstance(post, dict):
                    if 'theme' in post:
                        recent_themes.append(post['theme'])
                    elif 'content' in post:
                        # Extract first line as theme
                        content_lines = post['content'].split('\n')
                        if content_lines:
                            recent_themes.append(content_lines[0][:100] + "...")
            
            if recent_themes:
                prompt += f"\n\nRECENT POSTS (avoid repetition):\n"
                for i, theme in enumerate(recent_themes, 1):
                    prompt += f"{i}. {theme}\n"
        
        prompt += f"""

REQUIREMENTS:
1. Use the provided hook as inspiration for the opening
2. Develop the angle into a full post with insights
3. Target the specified audience appropriately
4. Ensure content is authentic to the professional profile
5. Avoid repeating themes from recent posts
6. Include actionable insights or thought-provoking questions
7. Make it engaging for {idea.estimated_engagement} type of interaction

Return only the JSON response with no additional text."""
        
        return prompt
    
    def _generate_post(self, system_prompt: str, user_prompt: str) -> Any:
        """Generate LinkedIn post using LLM."""
        try:
            import asyncio
            if asyncio.iscoroutinefunction(self.llm_factory.generate_with_system):
                # Check if we're already in an event loop
                try:
                    loop = asyncio.get_running_loop()
                    # We're in an event loop, use sync version
                    response = self._generate_post_sync(system_prompt, user_prompt)
                except RuntimeError:
                    # No event loop, use asyncio.run
                    response = asyncio.run(self._generate_post_async(system_prompt, user_prompt))
            else:
                response = self._generate_post_sync(system_prompt, user_prompt)
            return response
        except LLMError as e:
            logger.error(f"LLM generation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during LLM generation: {e}")
            raise LLMError(f"Post drafting failed: {e}")
    
    async def _generate_post_async(self, system_prompt: str, user_prompt: str) -> Any:
        """Generate post using async LLM."""
        return await self.llm_factory.generate_with_system(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.8,  # More creativity for engaging posts
            max_tokens=2000   # Sufficient for detailed post and metadata
        )
    
    def _generate_post_sync(self, system_prompt: str, user_prompt: str) -> Any:
        """Generate post using sync LLM."""
        if hasattr(self.llm_factory, 'generate_with_system_sync'):
            return self.llm_factory.generate_with_system_sync(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8,
                max_tokens=2000
            )
        else:
            import asyncio
            return asyncio.run(self.llm_factory.generate_with_system(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8,
                max_tokens=2000
            ))
    
    def _parse_response(self, response_content: str, original_idea: ContentIdea) -> DraftingOutput:
        """Parse LLM response into structured output."""
        try:
            # Clean response content
            content = response_content.strip()
            
            # Remove any markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            # Parse JSON
            data = json.loads(content)
            
            # Validate required fields
            if "linkedin_post" not in data:
                raise ValueError("Missing linkedin_post in response")
            
            post_data = data["linkedin_post"]
            
            # Normalize hashtags to ensure they start with #
            hashtags = post_data.get("hashtags", [])
            normalized_hashtags = []
            for tag in hashtags:
                if isinstance(tag, str):
                    # Add # prefix if missing
                    if not tag.startswith('#'):
                        normalized_hashtags.append(f"#{tag}")
                    else:
                        normalized_hashtags.append(tag)
            
            # Create LinkedIn post
            linkedin_post = LinkedInPost(
                content=post_data.get("content", ""),
                hashtags=normalized_hashtags,
                call_to_action=post_data.get("call_to_action"),
                estimated_length=post_data.get("estimated_length", len(post_data.get("content", ""))),
                tone_analysis=post_data.get("tone_analysis", {}),
                formatting_notes=post_data.get("formatting_notes", [])
            )
            
            return DraftingOutput(
                linkedin_post=linkedin_post,
                content_idea_used=original_idea,
                tone_compliance=data.get("tone_compliance", {}),
                formatting_applied=data.get("formatting_applied", [])
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {response_content}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            raise ValueError(f"Response parsing failed: {e}")
    
    def _validate_linkedin_post(self, post: Dict[str, Any]) -> List[str]:
        """Validate LinkedIn post structure and content."""
        errors = []
        required_fields = ["content", "hashtags", "estimated_length"]
        
        for field in required_fields:
            if field not in post:
                errors.append(f"Missing required field: {field}")
        
        # Validate content
        content = post.get("content", "")
        if not content or len(content.strip()) < 50:
            errors.append("Post content is too short (minimum 50 characters)")
        
        # Validate hashtags
        hashtags = post.get("hashtags", [])
        if not isinstance(hashtags, list):
            errors.append("Hashtags must be a list")
        else:
            for hashtag in hashtags:
                if not isinstance(hashtag, str) or not hashtag.startswith('#'):
                    errors.append(f"Invalid hashtag format: {hashtag}")
        
        # Validate estimated length
        estimated_length = post.get("estimated_length", 0)
        actual_length = len(content)
        if abs(estimated_length - actual_length) > 100:
            errors.append(f"Estimated length ({estimated_length}) differs significantly from actual length ({actual_length})")
        
        return errors
    
    def _validate_tone_compliance(self, tone_compliance: Dict[str, Any]) -> List[str]:
        """Validate tone compliance and return warnings."""
        warnings = []
        
        # Check for tone compliance issues
        for key, value in tone_compliance.items():
            if isinstance(value, str) and "not" in value.lower():
                warnings.append(f"Potential tone compliance issue: {key} - {value}")
        
        return warnings
    
    def _calculate_confidence_score(self, drafting_output: DraftingOutput, context: ProfileContext) -> float:
        """Calculate confidence score based on output quality and compliance."""
        score = 0.0
        
        post = drafting_output.linkedin_post
        
        # Base score for having content
        if post.content and len(post.content) >= 100:
            score += 0.3
        
        # Score for optimal length
        content_length = len(post.content)
        if 500 <= content_length <= 1300:  # Optimal range
            score += 0.2
        elif content_length <= 3000:  # Within LinkedIn limits
            score += 0.1
        
        # Score for hashtags
        if 3 <= len(post.hashtags) <= 5:  # Optimal hashtag count
            score += 0.1
        elif len(post.hashtags) > 0:
            score += 0.05
        
        # Score for call to action
        if post.call_to_action:
            score += 0.1
        
        # Score for tone analysis
        if post.tone_analysis:
            score += 0.1
        
        # Score for formatting notes
        if post.formatting_notes:
            score += 0.1
        
        # Score for tone compliance
        if drafting_output.tone_compliance:
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
