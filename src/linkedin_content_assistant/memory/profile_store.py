"""Profile-specific memory storage.

This module provides profile-isolated storage for historical posts,
style analysis, and events. Each profile gets its own directory.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import Counter

from .models import MemoryEvent
from .content_intelligence import ContentIntelligence

logger = logging.getLogger(__name__)


class ProfileMemoryStore:
    """Profile-specific memory storage with isolated directories."""
    
    def __init__(self, base_dir: str = "data/memory", llm_factory=None):
        """Initialize profile memory store.
        
        Args:
            base_dir: Base directory for all profile data
            llm_factory: Optional LLM factory for deep content analysis
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.content_intelligence = ContentIntelligence(llm_factory=llm_factory)
    
    def _get_profile_dir(self, profile_id: str) -> Path:
        """Get directory path for a profile."""
        profile_dir = self.base_dir / profile_id
        profile_dir.mkdir(parents=True, exist_ok=True)
        return profile_dir
    
    def _get_posts_file(self, profile_id: str) -> Path:
        """Get posts file path for a profile."""
        return self._get_profile_dir(profile_id) / "posts.json"
    
    def _get_style_file(self, profile_id: str) -> Path:
        """Get style analysis file path for a profile."""
        return self._get_profile_dir(profile_id) / "style_analysis.json"
    
    def _get_events_file(self, profile_id: str) -> Path:
        """Get events file path for a profile."""
        return self._get_profile_dir(profile_id) / "events.json"
    
    def _get_content_intelligence_file(self, profile_id: str) -> Path:
        """Get content intelligence file path for a profile."""
        return self._get_profile_dir(profile_id) / "content_intelligence.json"
    
    # ========== Historical Posts ==========
    
    def store_historical_post(self, profile_id: str, post: Dict[str, Any]) -> None:
        """Store a historical post for a profile.
        
        Args:
            profile_id: Profile identifier
            post: Post data dictionary
        """
        posts_file = self._get_posts_file(profile_id)
        
        # Load existing posts
        posts = self._load_posts(profile_id)
        
        # Add new post
        posts.append(post)
        
        # Save
        with open(posts_file, 'w') as f:
            json.dump(posts, f, indent=2)
        
        logger.debug(f"Stored historical post for {profile_id}")
    
    def get_historical_posts(
        self,
        profile_id: str,
        limit: Optional[int] = None,
        post_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get historical posts for a profile.
        
        Args:
            profile_id: Profile identifier
            limit: Maximum number of posts to return
            post_type: Filter by post type (article, post, repost)
        
        Returns:
            List of post dictionaries
        """
        posts = self._load_posts(profile_id)
        
        # Filter by type if specified
        if post_type:
            posts = [p for p in posts if p.get('metadata', {}).get('type') == post_type]
        
        # Apply limit
        if limit:
            posts = posts[:limit]
        
        return posts
    
    def get_post_count(self, profile_id: str) -> int:
        """Get total number of historical posts for a profile."""
        return len(self._load_posts(profile_id))
    
    def _load_posts(self, profile_id: str) -> List[Dict[str, Any]]:
        """Load posts from file."""
        posts_file = self._get_posts_file(profile_id)
        
        if not posts_file.exists():
            return []
        
        try:
            with open(posts_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load posts for {profile_id}: {e}")
            return []
    
    # ========== Style Analysis ==========
    
    def store_style_analysis(self, profile_id: str, analysis: Dict[str, Any]) -> None:
        """Store style analysis for a profile.
        
        Args:
            profile_id: Profile identifier
            analysis: Style analysis dictionary
        """
        style_file = self._get_style_file(profile_id)
        
        # Add metadata
        analysis_with_meta = {
            "profile_id": profile_id,
            "analyzed_at": datetime.utcnow().isoformat(),
            "analysis": analysis
        }
        
        with open(style_file, 'w') as f:
            json.dump(analysis_with_meta, f, indent=2)
        
        logger.info(f"Stored style analysis for {profile_id}")
    
    def get_style_analysis(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get style analysis for a profile.
        
        Args:
            profile_id: Profile identifier
        
        Returns:
            Style analysis dictionary or None
        """
        style_file = self._get_style_file(profile_id)
        
        if not style_file.exists():
            return None
        
        try:
            with open(style_file, 'r') as f:
                data = json.load(f)
                return data.get('analysis')
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load style analysis for {profile_id}: {e}")
            return None
    
    # ========== Content Intelligence ==========
    
    def analyze_content_intelligence(self, profile_id: str) -> Dict[str, Any]:
        """Analyze historical posts to extract strategic content insights.
        
        Args:
            profile_id: Profile identifier
            
        Returns:
            Content intelligence analysis
        """
        posts = self._load_posts(profile_id)
        
        if not posts:
            logger.warning(f"No posts available for content intelligence analysis: {profile_id}")
            return {"message": "No posts available"}
        
        logger.info(f"Running content intelligence analysis on {len(posts)} posts for {profile_id}")
        
        # Perform comprehensive analysis (with LLM if available)
        analysis = self.content_intelligence.analyze_content_landscape(posts, use_llm=True)
        
        # Generate strategic direction
        direction = self.content_intelligence.generate_content_direction(analysis)
        
        # Combine results
        intelligence = {
            "profile_id": profile_id,
            "analyzed_at": datetime.utcnow().isoformat(),
            "posts_analyzed": len(posts),
            "landscape_analysis": analysis,
            "strategic_direction": direction
        }
        
        # Store the analysis
        self.store_content_intelligence(profile_id, intelligence)
        
        return intelligence
    
    async def analyze_content_intelligence_async(self, profile_id: str) -> Dict[str, Any]:
        """Async version of content intelligence analysis with LLM support.
        
        Args:
            profile_id: Profile identifier
            
        Returns:
            Content intelligence analysis with LLM insights
        """
        posts = self._load_posts(profile_id)
        
        if not posts:
            logger.warning(f"No posts available for content intelligence analysis: {profile_id}")
            return {"message": "No posts available"}
        
        logger.info(f"Running async content intelligence analysis on {len(posts)} posts for {profile_id}")
        
        # Phase 1: Rule-based analysis
        analysis = {
            "total_posts_analyzed": len(posts),
            "themes": self.content_intelligence._extract_themes(posts),
            "engagement_patterns": self.content_intelligence._analyze_engagement(posts),
            "content_evolution": self.content_intelligence._track_content_evolution(posts),
            "knowledge_domains": self.content_intelligence._identify_knowledge_domains(posts),
            "audience_insights": self.content_intelligence._extract_audience_insights(posts),
            "content_gaps": self.content_intelligence._identify_content_gaps(posts),
            "successful_patterns": self.content_intelligence._identify_successful_patterns(posts),
            "key_messages": self.content_intelligence._extract_key_messages(posts),
            "content_progression": self.content_intelligence._analyze_content_progression(posts)
        }
        
        # Phase 2: LLM deep analysis
        if self.content_intelligence.llm_factory:
            logger.info("Running LLM-powered deep analysis...")
            try:
                llm_insights = await self.content_intelligence._llm_deep_analysis(posts, analysis)
                analysis["llm_insights"] = llm_insights
                logger.info("LLM deep analysis completed")
            except Exception as e:
                logger.warning(f"LLM deep analysis failed: {e}")
                analysis["llm_insights"] = {"error": str(e)}
        
        # Generate strategic direction
        direction = self.content_intelligence.generate_content_direction(analysis)
        
        # Combine results
        intelligence = {
            "profile_id": profile_id,
            "analyzed_at": datetime.utcnow().isoformat(),
            "posts_analyzed": len(posts),
            "landscape_analysis": analysis,
            "strategic_direction": direction
        }
        
        # Store the analysis
        self.store_content_intelligence(profile_id, intelligence)
        
        return intelligence
    
    def store_content_intelligence(self, profile_id: str, intelligence: Dict[str, Any]) -> None:
        """Store content intelligence analysis.
        
        Args:
            profile_id: Profile identifier
            intelligence: Content intelligence data
        """
        intelligence_file = self._get_content_intelligence_file(profile_id)
        
        with open(intelligence_file, 'w') as f:
            json.dump(intelligence, f, indent=2)
        
        logger.info(f"Stored content intelligence for {profile_id}")
    
    def get_content_intelligence(self, profile_id: str, refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get content intelligence analysis for a profile.
        
        Args:
            profile_id: Profile identifier
            refresh: If True, regenerate analysis even if cached
            
        Returns:
            Content intelligence dictionary or None
        """
        intelligence_file = self._get_content_intelligence_file(profile_id)
        
        # Check if we need to refresh or file doesn't exist
        if refresh or not intelligence_file.exists():
            logger.info(f"Generating fresh content intelligence for {profile_id}")
            return self.analyze_content_intelligence(profile_id)
        
        try:
            with open(intelligence_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load content intelligence for {profile_id}: {e}")
            # Try to regenerate
            return self.analyze_content_intelligence(profile_id)
    
    # ========== Events (Generated Posts, Feedback) ==========
    
    def store_event(self, profile_id: str, event: Dict[str, Any]) -> None:
        """Store an event for a profile.
        
        Args:
            profile_id: Profile identifier
            event: Event data dictionary
        """
        events_file = self._get_events_file(profile_id)
        
        # Load existing events
        events = self._load_events(profile_id)
        
        # Add new event
        events.append(event)
        
        # Save
        with open(events_file, 'w') as f:
            json.dump(events, f, indent=2)
        
        logger.debug(f"Stored event for {profile_id}")
    
    def get_events(
        self,
        profile_id: str,
        event_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get events for a profile.
        
        Args:
            profile_id: Profile identifier
            event_type: Filter by event type
            limit: Maximum number of events to return
        
        Returns:
            List of event dictionaries
        """
        events = self._load_events(profile_id)
        
        # Filter by type if specified
        if event_type:
            events = [e for e in events if e.get('event_type') == event_type]
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda e: e.get('timestamp', ''), reverse=True)
        
        # Apply limit
        if limit:
            events = events[:limit]
        
        return events
    
    def _load_events(self, profile_id: str) -> List[Dict[str, Any]]:
        """Load events from file."""
        events_file = self._get_events_file(profile_id)
        
        if not events_file.exists():
            return []
        
        try:
            with open(events_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load events for {profile_id}: {e}")
            return []
    
    # ========== Profile Management ==========
    
    def list_profiles(self) -> List[str]:
        """List all profiles with stored data.
        
        Returns:
            List of profile IDs
        """
        profiles = []
        for item in self.base_dir.iterdir():
            if item.is_dir():
                profiles.append(item.name)
        return sorted(profiles)
    
    def get_profile_stats(self, profile_id: str) -> Dict[str, Any]:
        """Get statistics for a profile.
        
        Args:
            profile_id: Profile identifier
        
        Returns:
            Dictionary with profile statistics
        """
        posts = self._load_posts(profile_id)
        events = self._load_events(profile_id)
        style = self.get_style_analysis(profile_id)
        
        # Count post types
        post_types = Counter(p.get('metadata', {}).get('type', 'unknown') for p in posts)
        
        return {
            "profile_id": profile_id,
            "total_posts": len(posts),
            "post_types": dict(post_types),
            "total_events": len(events),
            "has_style_analysis": style is not None,
            "style_analyzed_at": style.get('analyzed_at') if style else None
        }
    
    def delete_profile_data(self, profile_id: str) -> bool:
        """Delete all data for a profile.
        
        Args:
            profile_id: Profile identifier
        
        Returns:
            True if deleted successfully
        """
        profile_dir = self._get_profile_dir(profile_id)
        
        if not profile_dir.exists():
            return False
        
        try:
            # Delete all files in profile directory
            for file in profile_dir.iterdir():
                file.unlink()
            
            # Delete directory
            profile_dir.rmdir()
            
            logger.info(f"Deleted all data for profile {profile_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete profile data for {profile_id}: {e}")
            return False
    
    # ========== Migration Helper ==========
    
    def migrate_from_old_store(self, old_events_file: str) -> Dict[str, int]:
        """Migrate data from old single-file store to profile-specific storage.
        
        Args:
            old_events_file: Path to old events.json file
        
        Returns:
            Dictionary with migration statistics per profile
        """
        logger.info(f"Migrating data from {old_events_file}")
        
        try:
            with open(old_events_file, 'r') as f:
                old_events = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load old events file: {e}")
            return {}
        
        stats = {}
        
        for event_data in old_events:
            profile_id = event_data.get('profile_id')
            if not profile_id:
                continue
            
            event_type = event_data.get('event_type')
            
            # Migrate based on event type
            if event_type == 'historical_post':
                # Extract post data from content
                post_data = {
                    'content': event_data.get('content', {}).get('post_content', ''),
                    'hashtags': event_data.get('content', {}).get('hashtags', []),
                    'length': event_data.get('content', {}).get('length', 0),
                    'engagement': event_data.get('content', {}).get('engagement', {}),
                    'timestamp': event_data.get('content', {}).get('original_timestamp', ''),
                    'metadata': {
                        'type': 'post',
                        'has_image': False,
                        'has_video': False,
                        'has_document': False
                    }
                }
                self.store_historical_post(profile_id, post_data)
                stats[profile_id] = stats.get(profile_id, 0) + 1
            
            elif event_type == 'style_analysis':
                # Store style analysis
                self.store_style_analysis(profile_id, event_data.get('content', {}))
            
            else:
                # Store as regular event
                self.store_event(profile_id, event_data)
        
        logger.info(f"Migration complete: {stats}")
        return stats
