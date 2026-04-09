"""Trend scanner for fetching trending tech content."""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional
import aiohttp
from bs4 import BeautifulSoup

from .models import TrendingArticle

logger = logging.getLogger(__name__)


class TrendScanner:
    """Scans multiple sources for trending tech content."""
    
    def __init__(self, max_articles: int = 10):
        """Initialize trend scanner.
        
        Args:
            max_articles: Maximum articles to fetch per source
        """
        self.max_articles = max_articles
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Mozilla/5.0 (compatible; LinkedInContentAssistant/1.0)'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def scan_all_sources(self) -> List[TrendingArticle]:
        """Scan all configured sources for trending content.
        
        Returns:
            List of trending articles from all sources
        """
        articles = []
        
        # Fetch from all sources concurrently
        tasks = [
            self.scan_hackernews(),
            self.scan_techcrunch(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error scanning source: {result}")
            elif isinstance(result, list):
                articles.extend(result)
        
        logger.info(f"Scanned {len(articles)} trending articles from all sources")
        return articles
    
    async def scan_hackernews(self) -> List[TrendingArticle]:
        """Scan Hacker News for trending tech stories.
        
        Returns:
            List of trending articles from HN
        """
        try:
            # Fetch top stories from HN API
            url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"HN API returned {response.status}")
                    return []
                
                story_ids = await response.json()
                story_ids = story_ids[:self.max_articles]
            
            # Fetch details for each story
            articles = []
            for story_id in story_ids:
                try:
                    story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    async with self.session.get(story_url) as response:
                        if response.status == 200:
                            story = await response.json()
                            
                            # Skip if no URL (Ask HN, etc.)
                            if not story.get('url'):
                                continue
                            
                            article = TrendingArticle(
                                title=story.get('title', ''),
                                url=story.get('url', ''),
                                source="hackernews",
                                score=story.get('score', 0),
                                published_at=datetime.fromtimestamp(story.get('time', 0)) if story.get('time') else None,
                                author=story.get('by'),
                                tags=[]
                            )
                            articles.append(article)
                except Exception as e:
                    logger.debug(f"Error fetching HN story {story_id}: {e}")
                    continue
            
            logger.info(f"Fetched {len(articles)} articles from Hacker News")
            return articles
            
        except Exception as e:
            logger.error(f"Error scanning Hacker News: {e}")
            return []
    
    async def scan_techcrunch(self) -> List[TrendingArticle]:
        """Scan TechCrunch for latest tech news.
        
        Returns:
            List of articles from TechCrunch
        """
        try:
            url = "https://techcrunch.com/"
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"TechCrunch returned {response.status}")
                    return []
                
                html = await response.text()
            
            soup = BeautifulSoup(html, 'html.parser')
            articles = []
            
            # Find article elements (TechCrunch structure)
            article_elements = soup.find_all('article', limit=self.max_articles)
            
            for elem in article_elements:
                try:
                    # Extract title and link
                    title_elem = elem.find('h2') or elem.find('h3')
                    if not title_elem:
                        continue
                    
                    link_elem = title_elem.find('a')
                    if not link_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url = link_elem.get('href', '')
                    
                    # Extract summary if available
                    summary_elem = elem.find('p')
                    summary = summary_elem.get_text(strip=True) if summary_elem else None
                    
                    article = TrendingArticle(
                        title=title,
                        url=url,
                        source="techcrunch",
                        summary=summary,
                        tags=[]
                    )
                    articles.append(article)
                    
                except Exception as e:
                    logger.debug(f"Error parsing TechCrunch article: {e}")
                    continue
            
            logger.info(f"Fetched {len(articles)} articles from TechCrunch")
            return articles
            
        except Exception as e:
            logger.error(f"Error scanning TechCrunch: {e}")
            return []
    
    async def fetch_article_content(self, article: TrendingArticle) -> Optional[str]:
        """Fetch and extract main content from an article URL.
        
        Args:
            article: Article to fetch content for
            
        Returns:
            Extracted article content or None
        """
        try:
            async with self.session.get(article.url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # Try to find main content
            main_content = (
                soup.find('article') or
                soup.find('main') or
                soup.find('div', class_='content') or
                soup.find('div', class_='post-content')
            )
            
            if main_content:
                # Extract text from paragraphs
                paragraphs = main_content.find_all('p')
                content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs[:5])  # First 5 paragraphs
                return content[:2000]  # Limit to 2000 chars
            
            return None
            
        except Exception as e:
            logger.debug(f"Error fetching article content: {e}")
            return None
