"""LinkedIn Post History Importer.

This module handles importing historical LinkedIn posts and analyzing
writing patterns for style learning.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter

from ..memory.profile_store import ProfileMemoryStore

logger = logging.getLogger(__name__)


class HistoryImporter:
    """Import and analyze historical LinkedIn posts."""
    
    def __init__(self, profile_store: ProfileMemoryStore):
        """Initialize history importer.
        
        Args:
            profile_store: Profile memory store for persisting posts
        """
        self.profile_store = profile_store
    
    def import_from_file(self, file_path: str, profile_id: str) -> Dict[str, Any]:
        """Import posts from JSON file.
        
        Args:
            file_path: Path to JSON file with posts
            profile_id: Profile ID to associate posts with
            
        Returns:
            Import summary with statistics
        """
        logger.info(f"Importing post history from: {file_path}")
        
        try:
            # Load JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            posts = data.get('posts', [])
            if not posts:
                raise ValueError("No posts found in file")
            
            logger.info(f"Found {len(posts)} posts in file")
            
            # Import each post
            imported_count = 0
            skipped_count = 0
            
            for post in posts:
                if self._import_post(post, profile_id):
                    imported_count += 1
                else:
                    skipped_count += 1
            
            # Analyze writing style
            style_analysis = self._analyze_writing_style(posts, profile_id)
            
            # Store style analysis
            self._store_style_analysis(profile_id, style_analysis)
            
            summary = {
                "success": True,
                "total_posts": len(posts),
                "imported": imported_count,
                "skipped": skipped_count,
                "style_analysis": style_analysis
            }
            
            logger.info(f"Import complete: {imported_count} imported, {skipped_count} skipped")
            return summary
            
        except Exception as e:
            logger.error(f"Import failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _import_post(self, post: Dict[str, Any], profile_id: str) -> bool:
        """Import a single post into profile store.
        
        Args:
            post: Post data dictionary
            profile_id: Profile ID
            
        Returns:
            True if imported successfully
        """
        try:
            content = post.get('content', '').strip()
            if not content or len(content) < 10:
                return False
            
            # Store post directly in profile store
            self.profile_store.store_historical_post(profile_id, post)
            return True
            
        except Exception as e:
            logger.warning(f"Failed to import post: {e}")
            return False
    
    def _analyze_writing_style(self, posts: List[Dict[str, Any]], profile_id: str) -> Dict[str, Any]:
        """Analyze writing patterns from historical posts.
        
        Args:
            posts: List of post dictionaries
            profile_id: Profile ID
            
        Returns:
            Style analysis dictionary
        """
        logger.info("Analyzing writing style...")
        
        # Extract all content
        contents = [p.get('content', '') for p in posts if p.get('content')]
        
        if not contents:
            return {}
        
        # Analyze patterns
        analysis = {
            "total_posts_analyzed": len(contents),
            "avg_post_length": sum(len(c) for c in contents) / len(contents),
            "length_distribution": self._analyze_length_distribution(contents),
            "common_opening_patterns": self._extract_opening_patterns(contents),
            "common_hashtags": self._extract_common_hashtags(posts),
            "emoji_usage": self._analyze_emoji_usage(contents),
            "sentence_patterns": self._analyze_sentence_patterns(contents),
            "vocabulary_preferences": self._analyze_vocabulary(contents)
        }
        
        logger.info("Style analysis complete")
        return analysis
    
    def _analyze_length_distribution(self, contents: List[str]) -> Dict[str, int]:
        """Analyze post length distribution."""
        lengths = [len(c) for c in contents]
        return {
            "min": min(lengths),
            "max": max(lengths),
            "median": sorted(lengths)[len(lengths) // 2],
            "short_posts": sum(1 for l in lengths if l < 500),
            "medium_posts": sum(1 for l in lengths if 500 <= l < 1500),
            "long_posts": sum(1 for l in lengths if l >= 1500)
        }
    
    def _extract_opening_patterns(self, contents: List[str], top_n: int = 10) -> List[str]:
        """Extract common opening patterns."""
        openings = []
        for content in contents:
            # Get first sentence or first 100 chars
            first_line = content.split('\n')[0][:100]
            if first_line:
                openings.append(first_line)
        
        # Find common patterns (simplified - just return unique openings)
        return list(set(openings))[:top_n]
    
    def _extract_common_hashtags(self, posts: List[Dict[str, Any]], top_n: int = 20) -> List[Dict[str, Any]]:
        """Extract most common hashtags."""
        all_hashtags = []
        for post in posts:
            all_hashtags.extend(post.get('hashtags', []))
        
        hashtag_counts = Counter(all_hashtags)
        return [
            {"hashtag": tag, "count": count}
            for tag, count in hashtag_counts.most_common(top_n)
        ]
    
    def _analyze_emoji_usage(self, contents: List[str]) -> Dict[str, Any]:
        """Analyze emoji usage patterns."""
        emoji_count = 0
        posts_with_emoji = 0
        
        for content in contents:
            has_emoji = any(ord(c) > 127 for c in content if not c.isalnum())
            if has_emoji:
                posts_with_emoji += 1
                # Simple emoji count (not perfect but good enough)
                emoji_count += sum(1 for c in content if ord(c) > 127 and not c.isalnum())
        
        return {
            "posts_with_emoji": posts_with_emoji,
            "emoji_frequency": posts_with_emoji / len(contents) if contents else 0,
            "avg_emoji_per_post": emoji_count / len(contents) if contents else 0
        }
    
    def _analyze_sentence_patterns(self, contents: List[str]) -> Dict[str, Any]:
        """Analyze sentence structure patterns."""
        all_sentences = []
        for content in contents:
            # Simple sentence split
            sentences = [s.strip() for s in content.replace('!', '.').replace('?', '.').split('.') if s.strip()]
            all_sentences.extend(sentences)
        
        if not all_sentences:
            return {}
        
        sentence_lengths = [len(s.split()) for s in all_sentences]
        
        return {
            "avg_sentence_length": sum(sentence_lengths) / len(sentence_lengths),
            "short_sentences": sum(1 for l in sentence_lengths if l < 10),
            "medium_sentences": sum(1 for l in sentence_lengths if 10 <= l < 20),
            "long_sentences": sum(1 for l in sentence_lengths if l >= 20)
        }
    
    def _analyze_vocabulary(self, contents: List[str]) -> Dict[str, Any]:
        """Analyze vocabulary preferences."""
        all_words = []
        for content in contents:
            words = content.lower().split()
            all_words.extend([w.strip('.,!?;:') for w in words if len(w) > 3])
        
        word_counts = Counter(all_words)
        
        # Remove common stop words
        stop_words = {'that', 'this', 'with', 'from', 'have', 'been', 'were', 'they', 'what', 'when', 'where', 'which', 'their', 'there', 'about', 'would', 'could', 'should'}
        filtered_words = {w: c for w, c in word_counts.items() if w not in stop_words}
        
        return {
            "unique_words": len(word_counts),
            "total_words": len(all_words),
            "common_words": [
                {"word": word, "count": count}
                for word, count in Counter(filtered_words).most_common(30)
            ]
        }
    
    def _store_style_analysis(self, profile_id: str, analysis: Dict[str, Any]) -> None:
        """Store style analysis in profile store."""
        try:
            self.profile_store.store_style_analysis(profile_id, analysis)
            logger.info("Style analysis stored in profile store")
        except Exception as e:
            logger.error(f"Failed to store style analysis: {e}")
    
    def _parse_engagement(self, value: str) -> int:
        """Parse engagement count from string."""
        try:
            # Handle formats like "1.2K", "500", etc.
            value = value.strip().replace(',', '')
            if 'K' in value.upper():
                return int(float(value.upper().replace('K', '')) * 1000)
            return int(value) if value.isdigit() else 0
        except:
            return 0
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp from various formats."""
        try:
            # Try ISO format first
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            # Fallback to current time if parsing fails
            return datetime.utcnow()
    
    def get_style_summary(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get style analysis summary for a profile.
        
        Args:
            profile_id: Profile ID
            
        Returns:
            Style analysis dictionary or None
        """
        try:
            return self.profile_store.get_style_analysis(profile_id)
        except Exception as e:
            logger.error(f"Failed to get style summary: {e}")
            return None
