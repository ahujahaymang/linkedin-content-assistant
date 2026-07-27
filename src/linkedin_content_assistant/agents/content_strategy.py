"""Content Strategy Agent for generating LinkedIn post ideas."""

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
class PostOption:
    """A single post option with angle, hook, and target audience."""
    angle: str
    hook: str
    target_audience: str
    content_theme: str
    estimated_engagement: str
    article_reference: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "angle": self.angle,
            "hook": self.hook,
            "target_audience": self.target_audience,
            "content_theme": self.content_theme,
            "estimated_engagement": self.estimated_engagement,
            "article_reference": self.article_reference
        }


@dataclass
class ContentStrategyOutput:
    """Output from Content Strategy Agent."""
    post_options: List[PostOption]
    reasoning: str
    profile_alignment: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "post_options": [option.to_dict() for option in self.post_options],
            "reasoning": self.reasoning,
            "profile_alignment": self.profile_alignment
        }


class ContentStrategyAgent(StatelessAgentMixin, LinkedInAgent):
    """Agent that generates 3 post options with angle, hook, and target audience."""
    
    def __init__(self, llm_factory: LLMFactory):
        super().__init__(AgentType.CONTENT_STRATEGY)
        self.llm_factory = llm_factory
    
    async def execute(
        self,
        context: ProfileContext,
        memory: Any,
        trending_articles: List[Dict[str, Any]] = None,
        strategy_brief: Optional[Dict[str, Any]] = None,
    ) -> AgentOutput:
        """Generate 3 post options aligned with profile context.
        
        Args:
            context: Profile-specific context and configuration
            memory: Memory store for retrieving relevant history
            trending_articles: Optional list of ranked trending articles
            strategy_brief: Optional profile strategy brief to ground options
            
        Returns:
            AgentOutput with 3 post options and metadata
        """
        try:
            # Get recent content history from memory
            recent_content = self._get_recent_content_history(memory, context.profile_id)
            
            # Build system prompt for content strategy
            system_prompt = self._build_system_prompt(context)
            
            # Build user prompt with context, history, trends, and strategy brief
            user_prompt = self._build_user_prompt(
                context, recent_content, trending_articles, strategy_brief
            )
            
            # Generate content strategy using LLM
            response = await self.llm_factory.generate_with_system(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=1500
            )
            
            # Parse and validate response
            strategy_output = self._parse_response(response.content)
            
            # Create agent output
            agent_output = AgentOutput(
                agent_type=self.agent_type,
                content=strategy_output.to_dict(),
                metadata={
                    "llm_provider": response.provider.value,
                    "llm_model": response.model,
                    "profile_id": context.profile_id,
                    "profile_version": context.version,
                    "content_history_count": len(recent_content),
                    "trending_articles_count": len(trending_articles) if trending_articles else 0
                },
                requires_approval=True,
                confidence_score=self._calculate_confidence_score(strategy_output, context)
            )
            
            return agent_output
            
        except Exception as e:
            logger.error(f"Content Strategy Agent execution failed: {e}")
            raise
    
    def validate_output(self, output: AgentOutput) -> ValidationResult:
        """Validate content strategy output against policies and constraints.
        
        Args:
            output: Agent output to validate
            
        Returns:
            ValidationResult with status and any errors/warnings
        """
        errors = []
        warnings = []
        
        try:
            content = output.content
            
            logger.debug(f"Validating content with keys: {list(content.keys())}")
            
            # Validate structure
            if "post_options" not in content:
                errors.append("Missing post_options in output")
                return ValidationResult(ValidationStatus.INVALID, errors, warnings)
            
            post_options = content["post_options"]
            logger.debug(f"Found {len(post_options)} post options")
            
            # Validate number of options
            if len(post_options) != 3:
                errors.append(f"Expected 3 post options, got {len(post_options)}")
            
            # Validate each post option
            for i, option in enumerate(post_options):
                logger.debug(f"Validating option {i}: keys={list(option.keys())}")
                option_errors = self._validate_post_option(option, i)
                if option_errors:
                    logger.debug(f"Option {i} errors: {option_errors}")
                errors.extend(option_errors)
            
            # Check for duplicate angles or hooks
            angles = [opt.get("angle", "") for opt in post_options]
            hooks = [opt.get("hook", "") for opt in post_options]
            
            if len(set(angles)) != len(angles):
                warnings.append("Duplicate angles detected in post options")
            
            if len(set(hooks)) != len(hooks):
                warnings.append("Duplicate hooks detected in post options")
            
            # Determine validation status
            if errors:
                logger.error(f"Validation failed with {len(errors)} errors: {errors}")
                status = ValidationStatus.INVALID
            else:
                logger.info("Validation passed - requires approval")
                status = ValidationStatus.REQUIRES_APPROVAL
            
            return ValidationResult(status, errors, warnings)
            
        except Exception as e:
            logger.error(f"Validation exception: {str(e)}", exc_info=True)
            errors.append(f"Validation error: {str(e)}")
            return ValidationResult(ValidationStatus.INVALID, errors, warnings)
    
    def get_required_context_fields(self) -> List[str]:
        """Get list of required context fields for content strategy."""
        return [
            "identity.headline",
            "identity.seniority", 
            "identity.primary_domains",
            "identity.target_audience",
            "identity.excluded_topics",
            "identity.positioning",
            "behavior.active_topics",
            "behavior.hook_patterns",
            "behavior.vocabulary_bias"
        ]
    
    def get_memory_query_params(self, context: ProfileContext) -> Dict[str, Any]:
        """Get parameters for querying relevant content history."""
        return {
            "profile_id": context.profile_id,
            "event_type": "post",
            "limit": 10,  # Last 10 posts for context
            "order_by": "timestamp",
            "order": "desc"
        }
    
    def _get_recent_content_history(self, memory: Any, profile_id: str) -> List[Dict[str, Any]]:
        """Get recent posted content so option generation avoids repeating themes."""
        try:
            # Prefer real posted history (most recent first) from ProfileMemoryStore
            if hasattr(memory, 'get_historical_posts'):
                posts = memory.get_historical_posts(profile_id, limit=10)
                logger.info(f"Retrieved {len(posts)} recent posts for strategy context")
                return posts
            logger.warning("Memory store does not support get_historical_posts")
            return []
        except Exception as e:
            logger.warning(f"Failed to retrieve content history: {e}")
            return []
    
    def _build_system_prompt(self, context: ProfileContext) -> str:
        """Build system prompt for content strategy generation."""
        identity = context.identity
        behavior = context.behavior
        
        return f"""You are a LinkedIn Content Strategy AI that generates post ideas for professionals.

PROFILE CONTEXT:
- Professional Identity: {identity.get('headline', 'Professional')}
- Seniority Level: {identity.get('seniority', 'Unknown')}
- Primary Domains: {', '.join(identity.get('primary_domains', []))}
- Target Audience: {identity.get('target_audience', 'Professional network')}
- Professional Positioning: {identity.get('positioning', 'Industry professional')}
- Excluded Topics: {', '.join(identity.get('excluded_topics', []))}

BEHAVIORAL PREFERENCES:
- Active Topics: {', '.join(behavior.get('active_topics', []))}
- Preferred Hook Patterns: {', '.join(behavior.get('hook_patterns', []))}
- Vocabulary Style: {behavior.get('vocabulary_bias', 'professional')}

TASK: Generate exactly 3 diverse post options that align with this professional profile.

REQUIREMENTS:
1. Each post option must have a unique angle and approach
2. Content must align with the professional positioning and domains
3. Avoid all excluded topics completely
4. Target the specified audience appropriately
5. Use the preferred vocabulary style and hook patterns when possible
6. Ensure content is authentic to the seniority level and expertise

OUTPUT FORMAT: Return a valid JSON object with this exact structure:
{{
    "post_options": [
        {{
            "angle": "The unique perspective or approach for this post",
            "hook": "The opening hook to grab attention",
            "target_audience": "Specific audience segment this targets",
            "content_theme": "The main theme or topic category",
            "estimated_engagement": "Expected engagement type (discussion/shares/reactions)",
            "article_reference": {{"title": "Article title", "url": "Article URL"}} or null
        }},
        // ... 2 more options
    ],
    "reasoning": "Brief explanation of why these options align with the profile",
    "profile_alignment": {{
        "positioning_match": "How options align with professional positioning",
        "audience_relevance": "Why these will resonate with target audience",
        "domain_expertise": "How options showcase domain knowledge"
    }}
}}

EXAMPLE with article reference:
{{
    "post_options": [
        {{
            "angle": "How this trend impacts our daily work",
            "hook": "Everyone's talking about X, but here's what matters",
            "target_audience": "Senior engineers",
            "content_theme": "Technical trends",
            "estimated_engagement": "discussion",
            "article_reference": {{"title": "The Future of AI Coding", "url": "https://example.com/article"}}
        }}
    ]
}}

EXAMPLE without article reference:
{{
    "post_options": [
        {{
            "angle": "Lessons from production incident",
            "hook": "Last week our system went down",
            "target_audience": "Engineering leaders",
            "content_theme": "Reliability",
            "estimated_engagement": "shares",
            "article_reference": null
        }}
    ]
}}"""
    
    def _build_user_prompt(self, context: ProfileContext, recent_content: List[Dict[str, Any]], trending_articles: List[Dict[str, Any]] = None, strategy_brief: Optional[Dict[str, Any]] = None) -> str:
        """Build user prompt with context, recent content history, and trending articles."""
        prompt = "Generate 3 diverse LinkedIn post options for this professional profile."

        # Ground options in the profile strategy brief when available
        if strategy_brief:
            try:
                from ..profiles.evaluator import ProfileEvaluator
                brief_text = ProfileEvaluator.brief_to_prompt_context(strategy_brief)
                if brief_text:
                    prompt += f"\n\n{brief_text}\n"
            except Exception as e:
                logger.warning(f"Failed to render strategy brief: {e}")
        
        # Add trending articles if available
        if trending_articles:
            prompt += "\n\n=== TRENDING TECH ARTICLES ===\n"
            prompt += "Consider these trending articles for inspiration. Pick the MOST relevant one and create a post that:\n"
            prompt += "- Shares your unique perspective based on your experience\n"
            prompt += "- Adds value beyond just summarizing the article\n"
            prompt += "- Connects the trend to practical lessons or insights\n"
            prompt += "- IMPORTANT: If a post option is based on an article, include the article_reference field with title and URL\n\n"
            
            for i, ranked_article in enumerate(trending_articles, 1):
                article = ranked_article.get('article')
                if article:
                    prompt += f"[Article {i}]\n"
                    prompt += f"Title: {article.title}\n"
                    prompt += f"Source: {article.source}\n"
                    prompt += f"URL: {article.url}\n"
                    if article.summary:
                        prompt += f"Summary: {article.summary}\n"
                    prompt += f"Relevance Score: {ranked_article.get('relevance_score', 0)}/100\n"
                    prompt += f"Why Relevant: {ranked_article.get('reasoning', 'N/A')}\n"
                    prompt += f"Suggested Angle: {ranked_article.get('content_angle', 'N/A')}\n\n"
            
            prompt += "NOTE: At least ONE of the 3 post options should be based on a trending article.\n"
            prompt += "For article-based posts, set article_reference to {{\"title\": \"<article title>\", \"url\": \"<article url>\"}}.\n"
            prompt += "For non-article posts, set article_reference to null.\n"
            prompt += "\nCRITICAL: ALL 3 post options MUST include the article_reference field (either with article data or null).\n"
        
        if recent_content:
            recent_themes = []
            for content in recent_content[:5]:  # Last 5 posts
                if isinstance(content, dict) and 'theme' in content:
                    recent_themes.append(content['theme'])
                elif isinstance(content, dict) and 'content' in content:
                    # Extract theme from content if available
                    recent_themes.append(content.get('content', '')[:50] + "...")
            
            if recent_themes:
                prompt += f"\n\nRECENT CONTENT THEMES (avoid repetition):\n"
                for i, theme in enumerate(recent_themes, 1):
                    prompt += f"{i}. {theme}\n"
        
        prompt += "\n\nEnsure the 3 options are diverse in angle, hook style, and content approach."
        prompt += "\nReturn only the JSON response with no additional text."
        
        return prompt
    
    async def _generate_strategy(self, system_prompt: str, user_prompt: str) -> Any:
        """Generate content strategy using LLM with async support."""
        try:
            response = await self.llm_factory.generate_with_system(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,  # Some creativity for diverse options
                max_tokens=1500   # Sufficient for 3 detailed options
            )
            return response
        except LLMError as e:
            logger.error(f"LLM generation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during LLM generation: {e}")
            raise LLMError(f"Content strategy generation failed: {e}")
    
    def _generate_strategy_sync(self, system_prompt: str, user_prompt: str) -> Any:
        """Generate content strategy using LLM with sync support."""
        try:
            # For sync version, we need to await the async call properly
            # Since we're in an async context (orchestrator.generate_daily_post is async),
            # we should just call the async version directly
            import asyncio
            
            # Get the current event loop
            try:
                loop = asyncio.get_running_loop()
                # Create a task and run it
                task = loop.create_task(self.llm_factory.generate_with_system(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.7,
                    max_tokens=1500
                ))
                # Wait for the task to complete
                response = loop.run_until_complete(task)
            except RuntimeError:
                # No running loop, create one
                response = asyncio.run(self.llm_factory.generate_with_system(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.7,
                    max_tokens=1500
                ))
            return response
        except LLMError as e:
            logger.error(f"LLM generation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during LLM generation: {e}")
            raise LLMError(f"Content strategy generation failed: {e}")
    
    def _parse_response(self, response_content: str) -> ContentStrategyOutput:
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
            if "post_options" not in data:
                raise ValueError("Missing post_options in response")
            
            # Parse post options
            post_options = []
            for option_data in data["post_options"]:
                post_option = PostOption(
                    angle=option_data.get("angle", ""),
                    hook=option_data.get("hook", ""),
                    target_audience=option_data.get("target_audience", ""),
                    content_theme=option_data.get("content_theme", ""),
                    estimated_engagement=option_data.get("estimated_engagement", ""),
                    article_reference=option_data.get("article_reference")
                )
                post_options.append(post_option)
            
            return ContentStrategyOutput(
                post_options=post_options,
                reasoning=data.get("reasoning", ""),
                profile_alignment=data.get("profile_alignment", {})
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {response_content}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            raise ValueError(f"Response parsing failed: {e}")
    
    def _validate_post_option(self, option: Dict[str, Any], index: int) -> List[str]:
        """Validate a single post option."""
        errors = []
        required_fields = ["angle", "hook", "target_audience", "content_theme", "estimated_engagement"]
        
        for field in required_fields:
            if field not in option or not option[field]:
                errors.append(f"Post option {index + 1}: Missing or empty {field}")
        
        # Validate field lengths
        if option.get("angle") and len(option["angle"]) < 10:
            errors.append(f"Post option {index + 1}: Angle too short (minimum 10 characters)")
        
        if option.get("hook") and len(option["hook"]) < 5:
            errors.append(f"Post option {index + 1}: Hook too short (minimum 5 characters)")
        
        return errors
    
    def _calculate_confidence_score(self, strategy_output: ContentStrategyOutput, context: ProfileContext) -> float:
        """Calculate confidence score based on output quality and profile alignment."""
        score = 0.0
        
        # Base score for having 3 options
        if len(strategy_output.post_options) == 3:
            score += 0.3
        
        # Score for content quality
        for option in strategy_output.post_options:
            if len(option.angle) >= 20:  # Detailed angle
                score += 0.1
            if len(option.hook) >= 10:   # Substantial hook
                score += 0.1
            if option.target_audience:   # Has target audience
                score += 0.05
        
        # Score for profile alignment
        if strategy_output.profile_alignment:
            score += 0.2
        
        # Score for reasoning quality
        if len(strategy_output.reasoning) >= 50:
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
