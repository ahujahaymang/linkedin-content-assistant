"""Data models for trending content."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TrendingArticle:
    """Represents a trending article or post."""
    
    title: str
    url: str
    source: str  # "hackernews", "linkedin", "techcrunch", etc.
    summary: Optional[str] = None
    score: Optional[int] = None  # Upvotes, likes, etc.
    published_at: Optional[datetime] = None
    author: Optional[str] = None
    tags: list[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "summary": self.summary,
            "score": self.score,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "author": self.author,
            "tags": self.tags
        }
