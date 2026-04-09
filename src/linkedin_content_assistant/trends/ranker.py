"""Trend ranker for selecting most relevant articles."""

import json
import logging
from typing import List, Optional, Dict, Any

from .models import TrendingArticle

logger = logging.getLogger(__name__)


class TrendRanker:
    """Ranks trending articles by relevance to user profile."""
    
    def __init__(self, llm_factory):
        """Initialize trend ranker.
        
        Args:
            llm_factory: LLM factory for generating rankings
        """
        self.llm_factory = llm_factory
    
    async def rank_articles(
        self,
        articles: List[TrendingArticle],
        profile: Dict[str, Any],
        top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """Rank articles by relevance to user profile.
        
        Args:
            articles: List of trending articles
            profile: User profile data
            top_n: Number of top articles to return
            
        Returns:
            List of ranked articles with relevance scores and reasoning
        """
        if not articles:
            logger.warning("No articles to rank")
            return []
        
        # Build prompt for LLM
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(articles, profile, top_n)
        
        try:
            # Get LLM ranking
            response = await self.llm_factory.generate_with_system(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3  # Lower temperature for more consistent ranking
            )
            
            # Parse response
            ranked = self._parse_ranking_response(response.content, articles)
            
            logger.info(f"Ranked {len(ranked)} articles by relevance")
            return ranked[:top_n]
            
        except Exception as e:
            logger.error(f"Error ranking articles: {e}")
            # Fallback: return top articles by score
            return self._fallback_ranking(articles, top_n)
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for article ranking."""
        return """You are an expert content strategist analyzing trending tech articles for LinkedIn content creation.

Your task is to rank articles by their relevance to the user's professional profile and content strategy.

Consider:
- Alignment with user's expertise and focus areas
- Potential for unique insights based on user's experience
- Engagement potential on LinkedIn
- Timeliness and relevance to current tech discussions
- Opportunity to add value beyond the original article

Respond with a JSON array of ranked articles."""
    
    def _build_user_prompt(
        self,
        articles: List[TrendingArticle],
        profile: Dict[str, Any],
        top_n: int
    ) -> str:
        """Build user prompt with articles and profile."""
        # Format profile
        profile_summary = f"""
USER PROFILE:
Name: {profile.get('name', 'Unknown')}
Title: {profile.get('title', 'Unknown')}
Focus Areas: {', '.join(profile.get('focus_areas', []))}
Target Audience: {profile.get('target_audience', 'Unknown')}
"""
        
        # Format articles
        articles_text = "\n\n".join([
            f"[{i+1}] {article.title}\n"
            f"Source: {article.source}\n"
            f"URL: {article.url}\n"
            f"Score: {article.score or 'N/A'}\n"
            f"Summary: {article.summary or 'No summary available'}"
            for i, article in enumerate(articles)
        ])
        
        return f"""{profile_summary}

TRENDING ARTICLES:
{articles_text}

Rank the top {top_n} articles by relevance to this user's profile and content strategy.

For each article, provide:
1. Article number (1-{len(articles)})
2. Relevance score (0-100)
3. Brief reasoning (why it's relevant, what unique angle the user could bring)
4. Suggested content angle (how to approach this topic)

Respond in JSON format:
[
  {{
    "article_number": 1,
    "relevance_score": 85,
    "reasoning": "...",
    "content_angle": "..."
  }}
]"""
    
    def _parse_ranking_response(
        self,
        response: str,
        articles: List[TrendingArticle]
    ) -> List[Dict[str, Any]]:
        """Parse LLM ranking response."""
        try:
            # Extract JSON from response
            start = response.find('[')
            end = response.rfind(']') + 1
            
            if start == -1 or end == 0:
                raise ValueError("No JSON array found in response")
            
            json_str = response[start:end]
            rankings = json.loads(json_str)
            
            # Combine with article data
            ranked_articles = []
            for ranking in rankings:
                article_num = ranking.get('article_number', 0) - 1
                
                if 0 <= article_num < len(articles):
                    article = articles[article_num]
                    ranked_articles.append({
                        "article": article,
                        "relevance_score": ranking.get('relevance_score', 0),
                        "reasoning": ranking.get('reasoning', ''),
                        "content_angle": ranking.get('content_angle', '')
                    })
            
            # Sort by relevance score
            ranked_articles.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return ranked_articles
            
        except Exception as e:
            logger.error(f"Error parsing ranking response: {e}")
            raise
    
    def _fallback_ranking(
        self,
        articles: List[TrendingArticle],
        top_n: int
    ) -> List[Dict[str, Any]]:
        """Fallback ranking based on article scores."""
        # Sort by score (if available)
        sorted_articles = sorted(
            articles,
            key=lambda a: a.score or 0,
            reverse=True
        )
        
        return [
            {
                "article": article,
                "relevance_score": 50,  # Default score
                "reasoning": "Ranked by popularity score",
                "content_angle": "Share insights based on your experience"
            }
            for article in sorted_articles[:top_n]
        ]
