"""Unit tests for memory store functionality."""

import pytest
from datetime import datetime, timedelta
import tempfile
import os
from pathlib import Path

from linkedin_content_assistant.memory import (
    MemoryEvent,
    MemoryEntry,
    MemoryStore,
    InMemoryStore,
    create_memory_store,
    MemoryContextRetriever
)


class TestMemoryEvent:
    """Test MemoryEvent model."""
    
    def test_memory_event_creation(self):
        """Test creating a memory event."""
        event = MemoryEvent(
            timestamp=datetime.now(),
            event_type="post_draft",
            content={"text": "Test post"},
            metrics={"likes": 10},
            profile_id="test-profile"
        )
        
        assert event.id is not None
        assert event.event_type == "post_draft"
        assert event.content["text"] == "Test post"
        assert event.metrics["likes"] == 10
        assert event.profile_id == "test-profile"
    
    def test_memory_event_to_dict(self):
        """Test converting memory event to dictionary."""
        timestamp = datetime.now()
        event = MemoryEvent(
            timestamp=timestamp,
            event_type="post_draft",
            content={"text": "Test post"},
            metrics={"likes": 10},
            profile_id="test-profile"
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_type"] == "post_draft"
        assert event_dict["content"]["text"] == "Test post"
        assert event_dict["timestamp"] == timestamp.isoformat()
    
    def test_memory_event_from_dict(self):
        """Test creating memory event from dictionary."""
        timestamp = datetime.now()
        event_dict = {
            "id": "test-id",
            "timestamp": timestamp.isoformat(),
            "event_type": "post_draft",
            "content": {"text": "Test post"},
            "metrics": {"likes": 10},
            "profile_id": "test-profile"
        }
        
        event = MemoryEvent.from_dict(event_dict)
        
        assert event.id == "test-id"
        assert event.event_type == "post_draft"
        assert event.content["text"] == "Test post"
        assert isinstance(event.timestamp, datetime)
    
    def test_memory_event_json_serialization(self):
        """Test JSON serialization round-trip."""
        event = MemoryEvent(
            timestamp=datetime.now(),
            event_type="post_draft",
            content={"text": "Test post"},
            metrics={"likes": 10},
            profile_id="test-profile"
        )
        
        json_str = event.to_json()
        restored_event = MemoryEvent.from_json(json_str)
        
        assert restored_event.event_type == event.event_type
        assert restored_event.content == event.content
        assert restored_event.profile_id == event.profile_id


class TestMemoryEntry:
    """Test MemoryEntry model."""
    
    def test_memory_entry_creation(self):
        """Test creating a memory entry."""
        entry = MemoryEntry(
            id="test-id",
            profile_id="test-profile",
            event_type="post_draft",
            content={"text": "Test post"},
            metrics={"likes": 10},
            timestamp=datetime.now(),
            tags=["test", "draft"]
        )
        
        assert entry.id == "test-id"
        assert entry.tags == ["test", "draft"]
    
    def test_memory_entry_from_memory_event(self):
        """Test creating memory entry from memory event."""
        event = MemoryEvent(
            timestamp=datetime.now(),
            event_type="post_draft",
            content={"text": "Test post"},
            metrics={"likes": 10},
            profile_id="test-profile"
        )
        
        entry = MemoryEntry.from_memory_event(event, tags=["test"])
        
        assert entry.id == event.id
        assert entry.event_type == event.event_type
        assert entry.tags == ["test"]
    
    def test_memory_entry_to_context(self):
        """Test converting memory entry to context string."""
        entry = MemoryEntry(
            id="test-id",
            profile_id="test-profile",
            event_type="post_draft",
            content={"text": "Test post"},
            metrics={"likes": 10},
            timestamp=datetime.now(),
            tags=["test"]
        )
        
        context = entry.to_context()
        
        assert "Event: post_draft" in context
        assert "Test post" in context
        assert "likes" in context
        assert "Tags: test" in context


class TestInMemoryStore:
    """Test InMemoryStore implementation."""
    
    def test_store_and_retrieve_event(self):
        """Test storing and retrieving an event."""
        store = InMemoryStore()
        
        event = MemoryEvent(
            timestamp=datetime.now(),
            event_type="post_draft",
            content={"text": "Test post"},
            metrics={"likes": 10},
            profile_id="test-profile"
        )
        
        store.store_event(event)
        retrieved = store.get_event_by_id(event.id)
        
        assert retrieved is not None
        assert retrieved.id == event.id
        assert retrieved.content == event.content
    
    def test_get_events_by_profile(self):
        """Test retrieving events by profile ID."""
        store = InMemoryStore()
        
        event1 = MemoryEvent(
            timestamp=datetime.now(),
            event_type="post_draft",
            content={"text": "Post 1"},
            metrics=None,
            profile_id="profile-1"
        )
        
        event2 = MemoryEvent(
            timestamp=datetime.now(),
            event_type="post_draft",
            content={"text": "Post 2"},
            metrics=None,
            profile_id="profile-2"
        )
        
        store.store_event(event1)
        store.store_event(event2)
        
        profile1_events = store.get_events(profile_id="profile-1")
        
        assert len(profile1_events) == 1
        assert profile1_events[0].profile_id == "profile-1"
    
    def test_get_events_by_type(self):
        """Test retrieving events by event type."""
        store = InMemoryStore()
        
        event1 = MemoryEvent(
            timestamp=datetime.now(),
            event_type="post_draft",
            content={"text": "Draft"},
            metrics=None,
            profile_id="test-profile"
        )
        
        event2 = MemoryEvent(
            timestamp=datetime.now(),
            event_type="post_published",
            content={"text": "Published"},
            metrics={"likes": 10},
            profile_id="test-profile"
        )
        
        store.store_event(event1)
        store.store_event(event2)
        
        draft_events = store.get_events(event_type="post_draft")
        
        assert len(draft_events) == 1
        assert draft_events[0].event_type == "post_draft"
    
    def test_get_events_with_time_range(self):
        """Test retrieving events within a time range."""
        store = InMemoryStore()
        
        now = datetime.now()
        old_event = MemoryEvent(
            timestamp=now - timedelta(days=5),
            event_type="post_draft",
            content={"text": "Old post"},
            metrics=None,
            profile_id="test-profile"
        )
        
        recent_event = MemoryEvent(
            timestamp=now,
            event_type="post_draft",
            content={"text": "Recent post"},
            metrics=None,
            profile_id="test-profile"
        )
        
        store.store_event(old_event)
        store.store_event(recent_event)
        
        recent_events = store.get_events(
            start_time=now - timedelta(days=1)
        )
        
        assert len(recent_events) == 1
        assert recent_events[0].content["text"] == "Recent post"
    
    def test_get_events_with_limit(self):
        """Test retrieving events with limit."""
        store = InMemoryStore()
        
        for i in range(5):
            event = MemoryEvent(
                timestamp=datetime.now(),
                event_type="post_draft",
                content={"text": f"Post {i}"},
                metrics=None,
                profile_id="test-profile"
            )
            store.store_event(event)
        
        limited_events = store.get_events(limit=3)
        
        assert len(limited_events) == 3
    
    def test_delete_event(self):
        """Test deleting an event."""
        store = InMemoryStore()
        
        event = MemoryEvent(
            timestamp=datetime.now(),
            event_type="post_draft",
            content={"text": "Test post"},
            metrics=None,
            profile_id="test-profile"
        )
        
        store.store_event(event)
        assert store.get_event_by_id(event.id) is not None
        
        deleted = store.delete_event(event.id)
        assert deleted is True
        assert store.get_event_by_id(event.id) is None
    
    def test_clear_profile_events(self):
        """Test clearing all events for a profile."""
        store = InMemoryStore()
        
        for i in range(3):
            event = MemoryEvent(
                timestamp=datetime.now(),
                event_type="post_draft",
                content={"text": f"Post {i}"},
                metrics=None,
                profile_id="test-profile"
            )
            store.store_event(event)
        
        deleted_count = store.clear_profile_events("test-profile")
        
        assert deleted_count == 3
        assert len(store.get_events(profile_id="test-profile")) == 0
    
    def test_persistence_to_file(self):
        """Test persisting events to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence_file = os.path.join(tmpdir, "memory", "events.json")
            
            # Create store and add event
            store = InMemoryStore(persistence_file=persistence_file)
            event = MemoryEvent(
                timestamp=datetime.now(),
                event_type="post_draft",
                content={"text": "Test post"},
                metrics={"likes": 10},
                profile_id="test-profile"
            )
            store.store_event(event)
            
            # Create new store with same file
            store2 = InMemoryStore(persistence_file=persistence_file)
            
            # Verify event was loaded
            retrieved = store2.get_event_by_id(event.id)
            assert retrieved is not None
            assert retrieved.content["text"] == "Test post"


class TestMemoryContextRetriever:
    """Test MemoryContextRetriever functionality."""
    
    def test_get_agent_context_recent(self):
        """Test getting recent context for agents."""
        store = InMemoryStore()
        retriever = MemoryContextRetriever(store)
        
        for i in range(5):
            event = MemoryEvent(
                timestamp=datetime.now(),
                event_type="post_draft",
                content={"text": f"Post {i}"},
                metrics=None,
                profile_id="test-profile"
            )
            store.store_event(event)
        
        context = retriever.get_agent_context(
            profile_id="test-profile",
            context_type="recent",
            limit=3
        )
        
        assert "test-profile" in context
        assert "Total Events: 3" in context
    
    def test_get_performance_metrics(self):
        """Test getting performance metrics."""
        store = InMemoryStore()
        retriever = MemoryContextRetriever(store)
        
        event = MemoryEvent(
            timestamp=datetime.now(),
            event_type="post",
            content={"text": "Test post"},
            metrics={"likes": 10, "comments": 5, "shares": 2},
            profile_id="test-profile"
        )
        store.store_event(event)
        
        metrics = retriever.get_performance_metrics(
            profile_id="test-profile",
            event_type="post",
            days_back=30
        )
        
        assert metrics["total_events"] == 1
        assert metrics["total_likes"] == 10
        assert metrics["total_comments"] == 5
        assert metrics["total_shares"] == 2
        assert metrics["avg_engagement"] == 17.0
    
    def test_search_similar_content(self):
        """Test searching for similar content."""
        store = InMemoryStore()
        retriever = MemoryContextRetriever(store)
        
        event1 = MemoryEvent(
            timestamp=datetime.now(),
            event_type="post",
            content={"text": "Post about Python programming"},
            metrics=None,
            profile_id="test-profile"
        )
        
        event2 = MemoryEvent(
            timestamp=datetime.now(),
            event_type="post",
            content={"text": "Post about JavaScript"},
            metrics=None,
            profile_id="test-profile"
        )
        
        store.store_event(event1)
        store.store_event(event2)
        
        results = retriever.search_similar_content(
            profile_id="test-profile",
            content_keywords=["Python"],
            event_type="post"
        )
        
        assert len(results) == 1
        assert "Python" in results[0].content["text"]


class TestMemoryStoreFactory:
    """Test memory store factory function."""
    
    def test_create_in_memory_store(self):
        """Test creating in-memory store via factory."""
        store = create_memory_store(store_type="in_memory")
        
        assert isinstance(store, InMemoryStore)
    
    def test_create_unknown_store_type(self):
        """Test creating unknown store type raises error."""
        with pytest.raises(ValueError, match="Unknown store type"):
            create_memory_store(store_type="unknown")
