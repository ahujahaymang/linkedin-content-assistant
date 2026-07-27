"""Content Orchestrator for coordinating daily content generation workflow."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from ..agents.base import ProfileContext, AgentOutput, ValidationStatus
from ..agents.content_strategy import ContentStrategyAgent, PostOption
from ..agents.drafting import DraftingAgent, LinkedInPost
from ..profiles.manager import ProfileManager
from ..memory.store import MemoryStore
from ..memory.models import MemoryEvent

logger = logging.getLogger(__name__)


@dataclass
class DailyPostResult:
    """Result of daily post generation."""
    success: bool
    post_draft: Optional[LinkedInPost]
    options_generated: int
    selected_option: Optional[PostOption]
    delivery_status: str
    error: Optional[str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "post_draft": self.post_draft.to_dict() if self.post_draft else None,
            "options_generated": self.options_generated,
            "selected_option": self.selected_option.to_dict() if self.selected_option else None,
            "delivery_status": self.delivery_status,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


class ContentOrchestrator:
    """Orchestrates the daily content generation workflow.
    
    Coordinates: TrendMonitor → ContentStrategy → Drafting → Telegram
    Enforces 1 post per day limit and manages option selection.
    """
    
    def __init__(
        self,
        profile_manager: ProfileManager,
        memory_store: MemoryStore,
        profile_store: Any,  # ProfileMemoryStore for historical data
        content_strategy_agent: ContentStrategyAgent,
        drafting_agent: DraftingAgent,
        quality_agent: Optional[Any] = None,   # QualityCritiqueAgent (optional)
        profile_evaluator: Optional[Any] = None,  # ProfileEvaluator (optional)
        trend_monitor: Optional[Any] = None,  # Will be implemented in later tasks
        telegram_bot: Optional[Any] = None     # Will be implemented in later tasks
    ):
        """Initialize Content Orchestrator with required components.
        
        Args:
            profile_manager: Profile configuration manager
            memory_store: Memory store for history and events
            profile_store: Profile-specific memory store for historical posts
            content_strategy_agent: Agent for generating post options
            drafting_agent: Agent for drafting final posts
            quality_agent: Optional agent that critiques/scores drafts for value
            trend_monitor: Optional trend monitor (stub for MVP)
            telegram_bot: Optional Telegram bot for delivery (stub for MVP)
        """
        self.profile_manager = profile_manager
        self.memory_store = memory_store
        self.profile_store = profile_store
        self.content_strategy_agent = content_strategy_agent
        self.drafting_agent = drafting_agent
        self.quality_agent = quality_agent
        self.profile_evaluator = profile_evaluator
        self.trend_monitor = trend_monitor
        self.telegram_bot = telegram_bot
    
    async def generate_daily_post(self, profile_id: str) -> DailyPostResult:
        """Generate daily post for the specified profile.
        
        This is the main workflow method that:
        1. Checks generation limit (1 post/day)
        2. Gets trending topics (if available)
        3. Generates 3 post options via ContentStrategy
        4. Selects best option
        5. Drafts final post via Drafting agent
        6. Delivers to Telegram (if available)
        
        Args:
            profile_id: Profile identifier
            
        Returns:
            DailyPostResult with generation outcome
        """
        timestamp = datetime.utcnow()
        
        try:
            logger.info(f"Starting daily post generation for profile: {profile_id}")
            
            # Step 1: Check generation limit (1 post per day) - DISABLED for manual testing
            # Scheduling will control frequency, not hard limits
            # if not await self.check_generation_limit(profile_id):
            #     logger.warning(f"Generation limit reached for profile: {profile_id}")
            #     return DailyPostResult(
            #         success=False,
            #         post_draft=None,
            #         options_generated=0,
            #         selected_option=None,
            #         delivery_status="skipped",
            #         error="Daily generation limit reached (1 post per day)",
            #         timestamp=timestamp
            #     )
            
            # Step 2: Load profile context
            profile = self.profile_manager.load_profile(profile_id)
            context = self._create_profile_context(profile)
            
            # Step 3: Get trending topics
            trending_topics = await self._get_trending_topics(profile_id)
            logger.info(f"Retrieved {len(trending_topics)} trending topics")
            
            # Step 4: Generate 3 post options via ContentStrategy (with trending articles)
            # Load (and auto-refresh if stale) the profile strategy brief so
            # option generation is grounded in an up-to-date assessment.
            strategy_brief = await self._maybe_refresh_strategy_brief(profile)

            logger.info("Generating content strategy options...")
            strategy_output = await self.content_strategy_agent.execute(
                context, 
                self.profile_store,  # Use profile_store for real posted history
                trending_articles=trending_topics,
                strategy_brief=strategy_brief
            )
            
            # Validate strategy output
            validation = self.content_strategy_agent.validate_output(strategy_output)
            if validation.status == ValidationStatus.INVALID:
                error_msg = f"Content strategy validation failed: {', '.join(validation.errors)}"
                logger.error(error_msg)
                return DailyPostResult(
                    success=False,
                    post_draft=None,
                    options_generated=0,
                    selected_option=None,
                    delivery_status="failed",
                    error=error_msg,
                    timestamp=timestamp
                )
            
            # Extract post options
            post_options = strategy_output.content.get("post_options", [])
            logger.info(f"Generated {len(post_options)} post options")
            
            # Log first option to debug article_reference
            if post_options:
                logger.info(f"First option keys: {list(post_options[0].keys())}")
                logger.info(f"First option article_reference: {post_options[0].get('article_reference', 'KEY_MISSING')}")
            
            # Store all options in memory
            await self._store_post_options(profile_id, post_options, strategy_output)
            
            # Step 5: Select best option
            selected_option = await self.select_best_option(post_options, profile)
            logger.info(f"Selected option with theme: {selected_option.get('content_theme', 'unknown')}")
            logger.info(f"Selected option article_reference: {selected_option.get('article_reference', 'None')}")
            
            # Step 6: Draft final post (with duplicate + quality guards)
            logger.info("Drafting final post...")
            drafting_output = await self._draft_and_refine(
                context,
                selected_option,
                profile_id
            )
            
            # Validate drafting output
            validation = self.drafting_agent.validate_output(drafting_output)
            if validation.status == ValidationStatus.INVALID:
                error_msg = f"Drafting validation failed: {', '.join(validation.errors)}"
                logger.error(error_msg)
                return DailyPostResult(
                    success=False,
                    post_draft=None,
                    options_generated=len(post_options),
                    selected_option=None,
                    delivery_status="failed",
                    error=error_msg,
                    timestamp=timestamp
                )
            
            # Extract LinkedIn post
            linkedin_post_dict = drafting_output.content.get("linkedin_post", {})
            linkedin_post = self._dict_to_linkedin_post(linkedin_post_dict)
            
            # Store draft in memory
            await self._store_post_draft(profile_id, linkedin_post, selected_option, drafting_output)
            
            # Step 7: Deliver to Telegram (with the article that was actually used in the post)
            # Extract the article reference from the selected option
            article_ref = selected_option.get('article_reference')
            trending_article = None
            
            if article_ref and trending_topics:
                # Find the matching trending article by URL
                article_url = article_ref.get('url') if isinstance(article_ref, dict) else None
                if article_url:
                    for topic in trending_topics:
                        if topic.get('article') and topic['article'].url == article_url:
                            trending_article = topic['article']
                            break
            
            delivery_success = await self.deliver_to_telegram(linkedin_post, profile_id, trending_article)
            delivery_status = "delivered" if delivery_success else "delivery_pending"
            
            logger.info(f"Daily post generation completed successfully for profile: {profile_id}")
            
            return DailyPostResult(
                success=True,
                post_draft=linkedin_post,
                options_generated=len(post_options),
                selected_option=self._dict_to_post_option(selected_option),
                delivery_status=delivery_status,
                error=None,
                timestamp=timestamp
            )
            
        except Exception as e:
            logger.error(f"Daily post generation failed for profile {profile_id}: {e}", exc_info=True)
            return DailyPostResult(
                success=False,
                post_draft=None,
                options_generated=0,
                selected_option=None,
                delivery_status="failed",
                error=str(e),
                timestamp=timestamp
            )
    
    # Strategy brief is auto-refreshed when older than this many days, or after
    # this many new posts have been added since it was last generated.
    BRIEF_MAX_AGE_DAYS = 14
    BRIEF_REFRESH_AFTER_NEW_POSTS = 5

    async def _maybe_refresh_strategy_brief(self, profile: Any) -> Optional[Dict[str, Any]]:
        """Return the profile strategy brief, regenerating it if stale.

        The brief is auto-refreshed when it is missing, older than
        ``BRIEF_MAX_AGE_DAYS``, or when enough new posts have accumulated since
        it was last generated. This keeps content grounded in a current
        assessment without any manual step.
        """
        profile_id = profile.profile_id

        if not hasattr(self.profile_store, 'get_strategy_brief'):
            return None

        brief = self.profile_store.get_strategy_brief(profile_id)

        # Without an evaluator we can only use whatever is cached.
        if not self.profile_evaluator:
            if brief:
                logger.info("Loaded cached strategy brief (no evaluator to refresh)")
            return brief

        reason = self._brief_refresh_reason(brief, profile_id)
        if not reason:
            logger.info("Strategy brief is current")
            return brief

        logger.info(f"Auto-refreshing strategy brief ({reason})")
        try:
            return await self.profile_evaluator.evaluate(
                profile, self.profile_store, refresh=True
            )
        except Exception as e:
            logger.warning(f"Strategy brief refresh failed, using existing: {e}")
            return brief

    def _brief_refresh_reason(
        self, brief: Optional[Dict[str, Any]], profile_id: str
    ) -> Optional[str]:
        """Return a human-readable reason to refresh the brief, or None."""
        if not brief:
            return "no brief yet"

        # New posts since last evaluation
        try:
            current_posts = self.profile_store.get_post_count(profile_id)
            evaluated = int(brief.get("posts_evaluated", 0) or 0)
            if current_posts - evaluated >= self.BRIEF_REFRESH_AFTER_NEW_POSTS:
                return f"{current_posts - evaluated} new posts since last evaluation"
        except Exception:
            pass

        # Age of the brief
        generated_at = brief.get("generated_at")
        if generated_at:
            try:
                age = datetime.utcnow() - datetime.fromisoformat(generated_at)
                if age > timedelta(days=self.BRIEF_MAX_AGE_DAYS):
                    return f"brief is {age.days} days old"
            except (ValueError, TypeError):
                pass

        return None

    async def regenerate_post(
        self,
        profile_id: str,
        content_idea: Dict[str, Any]
    ) -> Optional[LinkedInPost]:
        """Regenerate a post from a previously used content idea.

        Reuses the same drafting + quality + duplicate-guard pipeline as fresh
        generation, so a regenerated post gets the same value/uniqueness checks.

        Args:
            profile_id: Profile identifier
            content_idea: The content idea (selected option) to re-draft from

        Returns:
            A new LinkedInPost, or None if generation failed
        """
        profile = self.profile_manager.load_profile(profile_id)
        if not profile:
            logger.error(f"Cannot regenerate: profile '{profile_id}' not found")
            return None

        context = self._create_profile_context(profile)

        drafting_output = await self._draft_and_refine(
            context,
            content_idea or {},
            profile_id
        )
        if drafting_output is None:
            return None

        validation = self.drafting_agent.validate_output(drafting_output)
        if validation.status == ValidationStatus.INVALID:
            logger.error(f"Regenerated draft invalid: {', '.join(validation.errors)}")
            return None

        linkedin_post_dict = drafting_output.content.get("linkedin_post", {})
        return self._dict_to_linkedin_post(linkedin_post_dict)

    async def check_generation_limit(self, profile_id: str) -> bool:
        """Check if generation limit (1 post per day) has been reached.
        
        Args:
            profile_id: Profile identifier
            
        Returns:
            True if generation is allowed, False if limit reached
        """
        try:
            # Get events from the last 24 hours
            now = datetime.utcnow()
            yesterday = now - timedelta(days=1)
            
            # Query memory store for post_draft events in the last 24 hours
            recent_events = self.memory_store.get_events(
                profile_id=profile_id,
                event_type="post_draft",
                start_time=yesterday,
                end_time=now
            )
            
            # Check if any posts were generated in the last 24 hours
            if len(recent_events) >= 1:
                logger.info(f"Generation limit reached: {len(recent_events)} post(s) in last 24 hours")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking generation limit: {e}")
            # Fail safe: allow generation if check fails
            return True
    
    async def select_best_option(
        self, 
        options: List[Dict[str, Any]], 
        profile: Any
    ) -> Dict[str, Any]:
        """Select the best post option from generated options.
        
        Selection criteria:
        1. Profile alignment score
        2. Audience relevance
        3. Engagement potential
        4. Theme diversity (avoid recent themes)
        
        Args:
            options: List of post option dictionaries
            profile: Profile configuration
            
        Returns:
            Selected post option dictionary
        """
        if not options:
            raise ValueError("No options provided for selection")
        
        if len(options) == 1:
            return options[0]
        
        try:
            # Get recent post themes to avoid repetition
            recent_themes = await self._get_recent_themes(profile.profile_id, limit=10)
            
            # Score each option
            scored_options = []
            for option in options:
                score = self._calculate_option_score(option, profile, recent_themes)
                scored_options.append((score, option))
            
            # Sort by score (descending) and select best
            scored_options.sort(key=lambda x: x[0], reverse=True)
            best_option = scored_options[0][1]
            
            logger.info(f"Selected option with score: {scored_options[0][0]:.2f}")
            return best_option
            
        except Exception as e:
            logger.warning(f"Error in option selection, using first option: {e}")
            return options[0]
    
    async def deliver_to_telegram(
        self, 
        post: LinkedInPost, 
        profile_id: str,
        trending_article: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Deliver post draft to Telegram for manual posting.
        
        Args:
            post: LinkedIn post to deliver
            profile_id: Profile identifier
            trending_article: Optional trending article reference
            
        Returns:
            True if delivery successful, False otherwise
        """
        try:
            logger.info(f"deliver_to_telegram called, telegram_bot type: {type(self.telegram_bot)}")
            if self.telegram_bot is None:
                logger.info("Telegram bot not configured - skipping delivery")
                # Store delivery event as pending
                await self._store_delivery_event(profile_id, post, "pending", "Telegram not configured")
                return False
            
            logger.info(f"Delivering post to Telegram for profile: {profile_id}")
            
            # Send post draft via Telegram (with optional article reference)
            success = await self.telegram_bot.send_post_draft(post, profile_id, trending_article)
            
            if success:
                logger.info(f"Successfully delivered post to Telegram for profile: {profile_id}")
                await self._store_delivery_event(profile_id, post, "delivered", None)
                
                # Add draft to pending queue for /posted command (with content_idea for regeneration)
                content_idea = {
                    "angle": getattr(trending_article, 'suggested_angle', '') if trending_article else '',
                    "hook": '',  # Not stored separately
                    "target_audience": '',  # From profile
                    "content_theme": trending_article.title if trending_article else '',
                    "estimated_engagement": '',
                    "article_reference": trending_article.to_dict() if trending_article else None
                }
                
                self.profile_store.add_pending_draft(
                    profile_id,
                    post.content,
                    post.hashtags,
                    content_idea=content_idea
                )
            else:
                logger.warning(f"Failed to deliver post to Telegram for profile: {profile_id}")
                await self._store_delivery_event(profile_id, post, "failed", "Delivery returned False")
            
            return success
            
        except Exception as e:
            logger.error(f"Telegram delivery failed: {e}")
            await self._store_delivery_event(profile_id, post, "failed", str(e))
            return False
    
    def _create_profile_context(self, profile: Any) -> ProfileContext:
        """Create ProfileContext from profile configuration."""
        return ProfileContext(
            profile_id=profile.profile_id,
            identity=profile.identity.model_dump(),
            behavior=profile.behavior.model_dump(),
            version=profile.version,
            last_updated=profile.last_updated
        )
    
    async def _get_trending_topics(self, profile_id: str) -> List[Dict[str, Any]]:
        """Get trending topics and rank them by relevance to profile.
        
        Args:
            profile_id: Profile identifier
            
        Returns:
            List of ranked trending articles with relevance scores
        """
        try:
            from ..trends.scanner import TrendScanner
            from ..trends.ranker import TrendRanker
            
            # Load profile for ranking
            profile = self.profile_manager.load_profile(profile_id)
            profile_dict = {
                "name": profile.name,
                "title": profile.identity.headline,
                "focus_areas": profile.identity.primary_domains,
                "target_audience": profile.identity.target_audience
            }
            
            # Scan trending articles
            logger.info("Scanning trending tech articles...")
            async with TrendScanner(max_articles=10) as scanner:
                articles = await scanner.scan_all_sources()
            
            if not articles:
                logger.warning("No trending articles found")
                return []
            
            logger.info(f"Found {len(articles)} trending articles")
            
            # Rank articles by relevance to profile
            logger.info("Ranking articles by relevance to profile...")
            ranker = TrendRanker(self.content_strategy_agent.llm_factory)
            ranked_articles = await ranker.rank_articles(articles, profile_dict, top_n=3)
            
            logger.info(f"Selected top {len(ranked_articles)} relevant articles")
            
            return ranked_articles
            
        except Exception as e:
            logger.error(f"Failed to get trending topics: {e}", exc_info=True)
            return []
    
    async def _store_post_options(
        self, 
        profile_id: str, 
        options: List[Dict[str, Any]], 
        strategy_output: AgentOutput
    ) -> None:
        """Store all generated post options in memory."""
        try:
            event = MemoryEvent(
                profile_id=profile_id,
                event_type="content_strategy",
                content={
                    "post_options": options,
                    "reasoning": strategy_output.content.get("reasoning", ""),
                    "profile_alignment": strategy_output.content.get("profile_alignment", {}),
                    "options_count": len(options)
                },
                metrics=strategy_output.metadata,
                timestamp=datetime.utcnow()
            )
            self.memory_store.store_event(event)
            logger.debug(f"Stored {len(options)} post options in memory")
        except Exception as e:
            logger.error(f"Failed to store post options: {e}")
    
    async def _store_post_draft(
        self,
        profile_id: str,
        post: LinkedInPost,
        selected_option: Dict[str, Any],
        drafting_output: AgentOutput
    ) -> None:
        """Store generated post draft in memory."""
        try:
            event = MemoryEvent(
                profile_id=profile_id,
                event_type="post_draft",
                content={
                    "post_content": post.content,
                    "hashtags": post.hashtags,
                    "call_to_action": post.call_to_action,
                    "theme": selected_option.get("content_theme", ""),
                    "tone": post.tone_analysis.get("formality", "professional"),
                    "length": post.estimated_length,
                    "selected_option": selected_option,
                    "quality_critique": drafting_output.metadata.get("quality_critique"),
                    "history_similarity": drafting_output.metadata.get("history_similarity")
                },
                metrics={
                    **drafting_output.metadata,
                    "confidence_score": drafting_output.confidence_score
                },
                timestamp=datetime.utcnow()
            )
            self.memory_store.store_event(event)
            logger.debug("Stored post draft in memory")
        except Exception as e:
            logger.error(f"Failed to store post draft: {e}")
    
    async def _store_delivery_event(
        self,
        profile_id: str,
        post: LinkedInPost,
        status: str,
        error: Optional[str]
    ) -> None:
        """Store delivery event in memory."""
        try:
            event = MemoryEvent(
                profile_id=profile_id,
                event_type="post_delivery",
                content={
                    "post_content": post.content[:100] + "...",  # Store preview
                    "delivery_status": status,
                    "error": error
                },
                metrics={
                    "post_length": post.estimated_length,
                    "hashtag_count": len(post.hashtags)
                },
                timestamp=datetime.utcnow()
            )
            self.memory_store.store_event(event)
            logger.debug(f"Stored delivery event with status: {status}")
        except Exception as e:
            logger.error(f"Failed to store delivery event: {e}")
    
    async def _get_recent_themes(self, profile_id: str, limit: int = 10) -> List[str]:
        """Get recent post themes to avoid repetition."""
        try:
            recent_events = self.memory_store.get_events(
                profile_id=profile_id,
                event_type="post_draft",
                limit=limit
            )
            
            themes = []
            for event in recent_events:
                if hasattr(event, 'content') and isinstance(event.content, dict):
                    theme = event.content.get('theme', '')
                    if theme:
                        themes.append(theme)
            
            return themes
        except Exception as e:
            logger.warning(f"Failed to get recent themes: {e}")
            return []
    
    def _calculate_option_score(
        self,
        option: Dict[str, Any],
        profile: Any,
        recent_themes: List[str]
    ) -> float:
        """Calculate score for a post option.
        
        Scoring criteria:
        - Theme novelty (not in recent themes): 0.4
        - Angle quality (length and detail): 0.3
        - Hook quality: 0.2
        - Target audience match: 0.1
        """
        score = 0.0
        
        # Theme novelty (avoid recent themes)
        theme = option.get('content_theme', '')
        if theme and theme not in recent_themes:
            score += 0.4
        elif theme:
            # Partial credit if theme is different enough
            similarity = max(
                self._calculate_similarity(theme, recent_theme)
                for recent_theme in recent_themes
            ) if recent_themes else 0.0
            score += 0.4 * (1.0 - similarity)
        
        # Angle quality
        angle = option.get('angle', '')
        if len(angle) >= 50:  # Detailed angle
            score += 0.3
        elif len(angle) >= 20:  # Moderate angle
            score += 0.15
        
        # Hook quality
        hook = option.get('hook', '')
        if len(hook) >= 20:  # Strong hook
            score += 0.2
        elif len(hook) >= 10:  # Moderate hook
            score += 0.1
        
        # Target audience match
        target_audience = option.get('target_audience', '')
        profile_audience = profile.identity.target_audience if hasattr(profile, 'identity') else ''
        if target_audience and profile_audience:
            if target_audience.lower() in profile_audience.lower() or \
               profile_audience.lower() in target_audience.lower():
                score += 0.1
        
        return score
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple word-based similarity between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

    # Jaccard word-overlap above this is treated as a near-duplicate of an
    # existing post. Distinct topics typically score < 0.3; reworded versions
    # of the same post score higher.
    DUPLICATE_THRESHOLD = 0.5

    def _max_similarity_to_history(
        self,
        content: str,
        history_contents: List[str]
    ) -> tuple:
        """Return (max_similarity, most_similar_preview) vs a list of post bodies."""
        max_sim = 0.0
        preview = ""
        for prev in history_contents:
            if not prev:
                continue
            sim = self._calculate_similarity(content, prev)
            if sim > max_sim:
                max_sim = sim
                preview = prev
        return max_sim, preview

    async def _draft_and_refine(
        self,
        context: ProfileContext,
        selected_option: Dict[str, Any],
        profile_id: str,
        max_attempts: int = 3
    ) -> AgentOutput:
        """Draft a post, then refine it until it is both unique and high-value.

        Two guards run on each draft:
        1. Duplication - programmatic word-overlap against recent posted content
           (prompt-based avoidance alone is unreliable).
        2. Quality - an LLM critique that scores the draft for specificity,
           authenticity and insight density, rejecting generic "fluff".

        If either guard fails, the concrete feedback is fed back into the
        drafting agent and the post is re-drafted (bounded by ``max_attempts``).
        The best attempt seen is returned if no attempt fully passes.
        """
        # Recent posted content (newest first) to compare against
        history_contents: List[str] = []
        if hasattr(self.profile_store, 'get_historical_posts'):
            recent = self.profile_store.get_historical_posts(profile_id, limit=15)
            history_contents = [p.get('content', '') for p in recent if p.get('content')]

        from ..agents.delivery_style import select_delivery_style

        option = dict(selected_option)
        best_output: Optional[AgentOutput] = None
        best_rank: tuple = (-1.0,)  # higher is better
        last_style_signature: Optional[str] = None

        for attempt in range(1, max_attempts + 1):
            # Vary the delivery style each attempt so retries/regenerations
            # differ in tone and how they connect to the author.
            delivery_style = select_delivery_style(avoid_signature=last_style_signature)
            last_style_signature = delivery_style.signature

            drafting_output = await self.drafting_agent.execute(
                context,
                self.profile_store,
                option,
                delivery_style=delivery_style
            )

            linkedin_post = drafting_output.content.get("linkedin_post", {})
            post_content = linkedin_post.get("content", "")
            hashtags = linkedin_post.get("hashtags", [])

            # Guard 1: duplication
            sim, preview = self._max_similarity_to_history(post_content, history_contents)
            is_duplicate = sim >= self.DUPLICATE_THRESHOLD

            # Guard 2: quality critique
            critique = await self._critique_draft(context, post_content, hashtags)
            quality_score = critique.get("overall_score", self._quality_pass_threshold())
            quality_ok = critique.get("passes", True)

            logger.info(
                f"Draft attempt {attempt}/{max_attempts} [{delivery_style.describe()}]: "
                f"similarity={sim:.2f} (dup={is_duplicate}), "
                f"quality={quality_score:.1f} (ok={quality_ok})"
            )

            # Attach critique to the output so it can be stored/inspected
            drafting_output.metadata["quality_critique"] = critique
            drafting_output.metadata["history_similarity"] = round(sim, 3)

            # Rank attempts so we can keep the best if none fully passes.
            # Prefer non-duplicates, then higher quality.
            rank = (0.0 if is_duplicate else 1.0, quality_score)
            if rank > best_rank:
                best_rank = rank
                best_output = drafting_output

            if not is_duplicate and quality_ok:
                logger.info(f"Draft accepted on attempt {attempt}")
                return drafting_output

            # Build combined revision feedback for the next attempt
            option['additional_context'] = self._build_revision_feedback(
                base_context=selected_option.get('additional_context'),
                is_duplicate=is_duplicate,
                duplicate_preview=preview if is_duplicate else "",
                critique=critique if not quality_ok else None,
            )

        logger.warning(
            f"Draft did not fully pass after {max_attempts} attempts "
            f"(best rank={best_rank}); delivering best available version"
        )
        return best_output

    async def _critique_draft(
        self,
        context: ProfileContext,
        post_content: str,
        hashtags: List[str]
    ) -> Dict[str, Any]:
        """Run the quality critique agent, failing open if unavailable."""
        if not self.quality_agent:
            return {"overall_score": self._quality_pass_threshold(), "passes": True}
        try:
            output = await self.quality_agent.execute(
                context,
                self.profile_store,
                post_content=post_content,
                hashtags=hashtags,
            )
            return output.content
        except Exception as e:
            logger.warning(f"Quality critique failed, accepting draft by default: {e}")
            return {"overall_score": self._quality_pass_threshold(), "passes": True}

    def _quality_pass_threshold(self) -> float:
        """Threshold above which a draft is considered good enough."""
        return getattr(self.quality_agent, "PASS_THRESHOLD", 72.0) if self.quality_agent else 0.0

    def _build_revision_feedback(
        self,
        base_context: Optional[str],
        is_duplicate: bool,
        duplicate_preview: str,
        critique: Optional[Dict[str, Any]],
    ) -> str:
        """Compose an actionable revision note for a re-draft."""
        parts: List[str] = []
        if base_context:
            parts.append(base_context)

        if is_duplicate and duplicate_preview:
            parts.append(
                "AVOID DUPLICATION: A previously published post is very similar to "
                "this draft:\n"
                f"\"{duplicate_preview[:250]}...\"\n"
                "Choose a clearly different angle, topic, or example."
            )

        if critique:
            guidance = critique.get("revision_guidance", "")
            issues = critique.get("issues", []) or []
            note = ["IMPROVE QUALITY: This draft was judged too generic or low-value."]
            if issues:
                note.append("Specific problems to fix:")
                note.extend(f"- {issue}" for issue in issues[:5])
            if guidance:
                note.append(f"Editor guidance: {guidance}")
            note.append(
                "Rewrite with a concrete first-hand example, a specific number or "
                "situation, and a non-obvious takeaway. Cut generic advice and buzzwords."
            )
            parts.append("\n".join(note))

        return "\n\n".join(parts).strip()
    
    def _dict_to_post_option(self, option_dict: Dict[str, Any]) -> PostOption:
        """Convert dictionary to PostOption dataclass."""
        return PostOption(
            angle=option_dict.get('angle', ''),
            hook=option_dict.get('hook', ''),
            target_audience=option_dict.get('target_audience', ''),
            content_theme=option_dict.get('content_theme', ''),
            estimated_engagement=option_dict.get('estimated_engagement', '')
        )
    
    def _dict_to_linkedin_post(self, post_dict: Dict[str, Any]) -> LinkedInPost:
        """Convert dictionary to LinkedInPost dataclass."""
        return LinkedInPost(
            content=post_dict.get('content', ''),
            hashtags=post_dict.get('hashtags', []),
            call_to_action=post_dict.get('call_to_action'),
            estimated_length=post_dict.get('estimated_length', 0),
            tone_analysis=post_dict.get('tone_analysis', {}),
            formatting_notes=post_dict.get('formatting_notes', []),
            article_reference=post_dict.get('article_reference')
        )
