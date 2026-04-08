"""Integration tests for memory store functionality."""

import pytest
from datetime import datetime, timedelta
import tempfile
import os

from linkedin_content_assistant.memory import (
    MemoryEvent,
    InMemoryStore,
    MemoryContextRetriever
)


class TestMemoryStoreIntegration:
    """Integration tests for memory store with realistic scenarios."""
    
    def test_post_history_tracking(self):
        """Test tracking post history for content generation."""
        store = InMemoryStore()
        
        # Simulate generating and posting content over time
        profile_id = "test-profile"
        
        # Day 1: Generate and post
        draft_event = MemoryEvent(
            timestamp=datetime.now() - timedelta(days=2),
            event_type="post_draft",
            content={
                "text": "Excited to share insights on cloud architecture...",
                "hashtags": ["#CloudComputing", "#AWS", "#Architecture"],
                "theme": "cloud_architecture"
            },
            metrics={"confidence_score": 0.85},
            profile_id=profile_id
        )
        store.store_event(draft_event)
        
        published_event = MemoryEvent(
            timestamp=datetime.now() - timedelta(days=2, hours=-2),
            event_type="post_published",
            content={
                "draft_id": draft_event.id,
                "post_url": "https://linkedin.com/posts/..."
            },
            metrics={"likes": 45, "comments": 12, "shares": 8},
            profile_id=profile_id
        )
        store.store_event(published_event)
        
        # Day 2: Generate another post
        draft_event2 = MemoryEvent(
            timestamp=datetime.now() - timedelta(days=1),
            event_type="post_draft",
            content={
                "text": "Machine learning deployment best practices...",
                "hashtags": ["#MachineLearning", "#MLOps", "#DevOps"],
                "theme": "ml_deployment"
            },
            metrics={"confidence_score": 0.92},
            profile_id=profile_id
        )
        store.store_event(draft_event2)
        
        # Query recent posts to avoid repetition
        recent_posts = store.get_events(
            profile_id=profile_id,
            event_type="post_draft",
            limit=10
        )
        
        assert len(recent_posts) == 2
        themes = [post.content.get("theme") for post in recent_posts]
        assert "cloud_architecture" in themes
        assert "ml_deployment" in themes
    
    def test_trend_monitoring_workflow(self):
        """Test storing and retrieving trending topics."""
        store = InMemoryStore()
        profile_id = "test-profile"
        
        # Store trending topics from LinkedIn
        linkedin_trend = MemoryEvent(
            timestamp=datetime.now(),
            event_type="trend_detected",
            content={
                "topic": "Serverless cost optimization",
                "sources": ["linkedin"],
                "related_hashtags": ["#Serverless", "#CostOptimization"],
                "sample_content": "Many posts discussing Lambda cost reduction..."
            },
            metrics={
                "frequency": 15,
                "relevance_score": 0.92
            },
            profile_id=profile_id
        )
        store.store_event(linkedin_trend)
        
        # Store trending topics from web
        web_trend = MemoryEvent(
            timestamp=datetime.now(),
            event_type="trend_detected",
            content={
                "topic": "Serverless cost optimization",
                "sources": ["hackernews", "techcrunch"],
                "related_hashtags": ["#Serverless"],
                "sample_content": "Articles about reducing serverless costs..."
            },
            metrics={
                "frequency": 8,
                "relevance_score": 0.88
            },
            profile_id=profile_id
        )
        store.store_event(web_trend)
        
        # Query trends for content generation
        trends = store.get_events(
            profile_id=profile_id,
            event_type="trend_detected",
            start_time=datetime.now() - timedelta(hours=24)
        )
        
        assert len(trends) == 2
        # Both trends mention the same topic
        topics = [t.content["topic"] for t in trends]
        assert all("Serverless" in topic for topic in topics)
    
    def test_engagement_metrics_analysis(self):
        """Test analyzing engagement metrics for performance tracking."""
        store = InMemoryStore()
        retriever = MemoryContextRetriever(store)
        profile_id = "test-profile"
        
        # Store multiple posts with varying engagement
        posts_data = [
            {"likes": 50, "comments": 10, "shares": 5},
            {"likes": 120, "comments": 25, "shares": 15},
            {"likes": 30, "comments": 5, "shares": 2},
            {"likes": 80, "comments": 18, "shares": 10},
        ]
        
        for i, metrics in enumerate(posts_data):
            event = MemoryEvent(
                timestamp=datetime.now() - timedelta(days=i),
                event_type="post",
                content={"text": f"Post {i}"},
                metrics=metrics,
                profile_id=profile_id
            )
            store.store_event(event)
        
        # Get performance metrics
        metrics = retriever.get_performance_metrics(
            profile_id=profile_id,
            event_type="post",
            days_back=30
        )
        
        assert metrics["total_events"] == 4
        assert metrics["total_likes"] == 280
        assert metrics["total_comments"] == 58
        assert metrics["total_shares"] == 32
        assert metrics["avg_likes"] == 70.0
        assert metrics["avg_engagement"] == 92.5  # (280 + 58 + 32) / 4
    
    def test_content_pattern_analysis(self):
        """Test analyzing content patterns for optimization."""
        store = InMemoryStore()
        retriever = MemoryContextRetriever(store)
        profile_id = "test-profile"
        
        # Store posts at different times with varying engagement
        posting_times = [9, 14, 9, 16, 9, 14]  # Hours
        for i, hour in enumerate(posting_times):
            timestamp = datetime.now().replace(hour=hour, minute=0, second=0)
            event = MemoryEvent(
                timestamp=timestamp - timedelta(days=i),
                event_type="post",
                content={"text": f"Post at {hour}:00"},
                metrics={"likes": 50 + (i * 10), "comments": 10, "shares": 5},
                profile_id=profile_id
            )
            store.store_event(event)
        
        # Analyze patterns
        patterns = retriever.get_content_patterns(
            profile_id=profile_id,
            event_type="post",
            limit=50
        )
        
        assert patterns["total_analyzed"] == 6
        assert len(patterns["best_posting_hours"]) <= 3
        # 9 AM should be the most common posting time
        best_hour = patterns["best_posting_hours"][0]["hour"]
        assert best_hour == 9
    
    def test_persistence_across_sessions(self):
        """Test that events persist across store instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence_file = os.path.join(tmpdir, "memory", "events.json")
            profile_id = "test-profile"
            
            # Session 1: Create store and add events
            store1 = InMemoryStore(persistence_file=persistence_file)
            
            for i in range(3):
                event = MemoryEvent(
                    timestamp=datetime.now() - timedelta(days=i),
                    event_type="post_draft",
                    content={"text": f"Post {i}"},
                    metrics=None,
                    profile_id=profile_id
                )
                store1.store_event(event)
            
            # Session 2: Create new store with same file
            store2 = InMemoryStore(persistence_file=persistence_file)
            
            # Verify all events were loaded
            events = store2.get_events(profile_id=profile_id)
            assert len(events) == 3
            
            # Add more events in session 2
            new_event = MemoryEvent(
                timestamp=datetime.now(),
                event_type="post_draft",
                content={"text": "New post"},
                metrics=None,
                profile_id=profile_id
            )
            store2.store_event(new_event)
            
            # Session 3: Verify all events persist
            store3 = InMemoryStore(persistence_file=persistence_file)
            all_events = store3.get_events(profile_id=profile_id)
            assert len(all_events) == 4
    
    def test_multi_profile_isolation(self):
        """Test that events for different profiles are isolated."""
        store = InMemoryStore()
        
        # Add events for profile 1
        for i in range(3):
            event = MemoryEvent(
                timestamp=datetime.now(),
                event_type="post_draft",
                content={"text": f"Profile 1 Post {i}"},
                metrics=None,
                profile_id="profile-1"
            )
            store.store_event(event)
        
        # Add events for profile 2
        for i in range(2):
            event = MemoryEvent(
                timestamp=datetime.now(),
                event_type="post_draft",
                content={"text": f"Profile 2 Post {i}"},
                metrics=None,
                profile_id="profile-2"
            )
            store.store_event(event)
        
        # Verify isolation
        profile1_events = store.get_events(profile_id="profile-1")
        profile2_events = store.get_events(profile_id="profile-2")
        
        assert len(profile1_events) == 3
        assert len(profile2_events) == 2
        assert all(e.profile_id == "profile-1" for e in profile1_events)
        assert all(e.profile_id == "profile-2" for e in profile2_events)
        
        # Clear profile 1 events
        deleted = store.clear_profile_events("profile-1")
        assert deleted == 3
        
        # Verify profile 2 events still exist
        profile2_events_after = store.get_events(profile_id="profile-2")
        assert len(profile2_events_after) == 2
