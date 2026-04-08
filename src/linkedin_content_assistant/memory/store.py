"""Memory store interface and implementations."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json
import os
from pathlib import Path
import threading
from .models import MemoryEvent, MemoryEntry


class MemoryStore(ABC):
    """Abstract interface for memory storage."""
    
    @abstractmethod
    def store_event(self, event: MemoryEvent) -> None:
        """Store a memory event."""
        pass
    
    @abstractmethod
    def get_events(
        self,
        profile_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[MemoryEvent]:
        """Retrieve memory events with optional filtering."""
        pass
    
    @abstractmethod
    def get_event_by_id(self, event_id: str) -> Optional[MemoryEvent]:
        """Get a specific event by ID."""
        pass
    
    @abstractmethod
    def delete_event(self, event_id: str) -> bool:
        """Delete an event by ID."""
        pass
    
    @abstractmethod
    def clear_profile_events(self, profile_id: str) -> int:
        """Clear all events for a profile. Returns count of deleted events."""
        pass


class InMemoryStore(MemoryStore):
    """In-memory implementation of MemoryStore with file persistence."""
    
    def __init__(self, persistence_file: Optional[str] = None):
        """Initialize the in-memory store.
        
        Args:
            persistence_file: Optional file path for persistence
        """
        self._events: Dict[str, MemoryEvent] = {}
        self._lock = threading.RLock()
        self._persistence_file = persistence_file
        
        # Load from file if it exists
        if self._persistence_file and os.path.exists(self._persistence_file):
            self._load_from_file()
    
    def store_event(self, event: MemoryEvent) -> None:
        """Store a memory event."""
        with self._lock:
            self._events[event.id] = event
            self._persist_to_file()
    
    def get_events(
        self,
        profile_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[MemoryEvent]:
        """Retrieve memory events with optional filtering."""
        with self._lock:
            events = list(self._events.values())
            
            # Apply filters
            if profile_id:
                events = [e for e in events if e.profile_id == profile_id]
            
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            
            if start_time:
                events = [e for e in events if e.timestamp >= start_time]
            
            if end_time:
                events = [e for e in events if e.timestamp <= end_time]
            
            # Sort by timestamp (newest first)
            events.sort(key=lambda e: e.timestamp, reverse=True)
            
            # Apply limit
            if limit:
                events = events[:limit]
            
            return events
    
    def get_event_by_id(self, event_id: str) -> Optional[MemoryEvent]:
        """Get a specific event by ID."""
        with self._lock:
            return self._events.get(event_id)
    
    def delete_event(self, event_id: str) -> bool:
        """Delete an event by ID."""
        with self._lock:
            if event_id in self._events:
                del self._events[event_id]
                self._persist_to_file()
                return True
            return False
    
    def clear_profile_events(self, profile_id: str) -> int:
        """Clear all events for a profile. Returns count of deleted events."""
        with self._lock:
            events_to_delete = [
                event_id for event_id, event in self._events.items()
                if event.profile_id == profile_id
            ]
            
            for event_id in events_to_delete:
                del self._events[event_id]
            
            if events_to_delete:
                self._persist_to_file()
            
            return len(events_to_delete)
    
    def _persist_to_file(self) -> None:
        """Persist events to file."""
        if not self._persistence_file:
            return
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self._persistence_file), exist_ok=True)
        
        # Convert events to serializable format
        events_data = [event.to_dict() for event in self._events.values()]
        
        # Write to file
        with open(self._persistence_file, 'w') as f:
            json.dump(events_data, f, indent=2)
    
    def _load_from_file(self) -> None:
        """Load events from file."""
        if not self._persistence_file or not os.path.exists(self._persistence_file):
            return
        
        try:
            with open(self._persistence_file, 'r') as f:
                events_data = json.load(f)
            
            # Convert back to MemoryEvent objects
            for event_data in events_data:
                event = MemoryEvent.from_dict(event_data)
                self._events[event.id] = event
                
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Log error but don't fail - start with empty store
            print(f"Warning: Could not load memory store from {self._persistence_file}: {e}")
            self._events = {}


def create_memory_store(store_type: str = "in_memory", **kwargs) -> MemoryStore:
    """Factory function to create memory store instances.
    
    Args:
        store_type: Type of store to create ("in_memory")
        **kwargs: Additional arguments for store initialization
    
    Returns:
        MemoryStore instance
    """
    if store_type == "in_memory":
        return InMemoryStore(**kwargs)
    else:
        raise ValueError(f"Unknown store type: {store_type}")


class MemoryContextRetriever:
    """Helper class for retrieving memory context for agents."""
    
    def __init__(self, memory_store: MemoryStore):
        """Initialize with a memory store instance."""
        self.memory_store = memory_store
    
    def get_agent_context(
        self,
        profile_id: str,
        context_type: str = "recent",
        limit: int = 10,
        event_types: Optional[List[str]] = None,
        time_window_hours: Optional[int] = None
    ) -> str:
        """Get formatted context for agents.
        
        Args:
            profile_id: Profile to get context for
            context_type: Type of context ("recent", "relevant", "all")
            limit: Maximum number of events to include
            event_types: Optional list of event types to filter by
            time_window_hours: Optional time window in hours
        
        Returns:
            Formatted context string for agents
        """
        # Calculate time window if specified
        start_time = None
        if time_window_hours:
            start_time = datetime.now() - timedelta(hours=time_window_hours)
        
        # Get events based on context type
        if context_type == "recent":
            events = self._get_recent_context(profile_id, limit, event_types, start_time)
        elif context_type == "relevant":
            events = self._get_relevant_context(profile_id, limit, event_types, start_time)
        else:  # "all"
            events = self.memory_store.get_events(
                profile_id=profile_id,
                start_time=start_time,
                limit=limit
            )
            if event_types:
                events = [e for e in events if e.event_type in event_types]
        
        # Convert to context format
        return self._format_context(events, profile_id)
    
    def get_performance_metrics(
        self,
        profile_id: str,
        event_type: str = "post",
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get performance metrics for profile evolution.
        
        Args:
            profile_id: Profile to analyze
            event_type: Type of events to analyze
            days_back: Number of days to look back
        
        Returns:
            Dictionary of performance metrics
        """
        start_time = datetime.now() - timedelta(days=days_back)
        events = self.memory_store.get_events(
            profile_id=profile_id,
            event_type=event_type,
            start_time=start_time
        )
        
        if not events:
            return {"total_events": 0, "avg_engagement": 0}
        
        # Calculate metrics
        total_events = len(events)
        total_likes = sum(e.metrics.get("likes", 0) for e in events if e.metrics)
        total_comments = sum(e.metrics.get("comments", 0) for e in events if e.metrics)
        total_shares = sum(e.metrics.get("shares", 0) for e in events if e.metrics)
        
        avg_likes = total_likes / total_events if total_events > 0 else 0
        avg_comments = total_comments / total_events if total_events > 0 else 0
        avg_shares = total_shares / total_events if total_events > 0 else 0
        
        # Calculate engagement rate
        total_engagement = total_likes + total_comments + total_shares
        avg_engagement = total_engagement / total_events if total_events > 0 else 0
        
        return {
            "total_events": total_events,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "avg_likes": avg_likes,
            "avg_comments": avg_comments,
            "avg_shares": avg_shares,
            "avg_engagement": avg_engagement,
            "time_period_days": days_back
        }
    
    def get_content_patterns(
        self,
        profile_id: str,
        event_type: str = "post",
        limit: int = 50
    ) -> Dict[str, Any]:
        """Analyze content patterns for strategy optimization.
        
        Args:
            profile_id: Profile to analyze
            event_type: Type of events to analyze
            limit: Maximum number of events to analyze
        
        Returns:
            Dictionary of content patterns
        """
        events = self.memory_store.get_events(
            profile_id=profile_id,
            event_type=event_type,
            limit=limit
        )
        
        if not events:
            return {"patterns": [], "top_topics": [], "best_performing": []}
        
        # Analyze posting times
        posting_hours = [e.timestamp.hour for e in events]
        hour_counts = {}
        for hour in posting_hours:
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        best_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Find best performing content
        events_with_metrics = [e for e in events if e.metrics]
        if events_with_metrics:
            # Sort by total engagement
            best_performing = sorted(
                events_with_metrics,
                key=lambda e: (
                    e.metrics.get("likes", 0) + 
                    e.metrics.get("comments", 0) + 
                    e.metrics.get("shares", 0)
                ),
                reverse=True
            )[:5]
        else:
            best_performing = []
        
        return {
            "total_analyzed": len(events),
            "best_posting_hours": [{"hour": h, "count": c} for h, c in best_hours],
            "best_performing_content": [
                {
                    "content": e.content,
                    "metrics": e.metrics,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in best_performing
            ]
        }
    
    def search_similar_content(
        self,
        profile_id: str,
        content_keywords: List[str],
        event_type: str = "post",
        limit: int = 10
    ) -> List[MemoryEvent]:
        """Search for similar content based on keywords.
        
        Args:
            profile_id: Profile to search within
            content_keywords: Keywords to search for
            event_type: Type of events to search
            limit: Maximum number of results
        
        Returns:
            List of matching events
        """
        events = self.memory_store.get_events(
            profile_id=profile_id,
            event_type=event_type
        )
        
        # Simple keyword matching (could be enhanced with NLP)
        matching_events = []
        for event in events:
            content_text = str(event.content).lower()
            if any(keyword.lower() in content_text for keyword in content_keywords):
                matching_events.append(event)
        
        # Sort by timestamp (newest first) and limit
        matching_events.sort(key=lambda e: e.timestamp, reverse=True)
        return matching_events[:limit]
    
    def _get_recent_context(
        self,
        profile_id: str,
        limit: int,
        event_types: Optional[List[str]],
        start_time: Optional[datetime]
    ) -> List[MemoryEvent]:
        """Get recent events for context."""
        events = self.memory_store.get_events(
            profile_id=profile_id,
            start_time=start_time,
            limit=limit
        )
        
        if event_types:
            events = [e for e in events if e.event_type in event_types]
        
        return events
    
    def _get_relevant_context(
        self,
        profile_id: str,
        limit: int,
        event_types: Optional[List[str]],
        start_time: Optional[datetime]
    ) -> List[MemoryEvent]:
        """Get relevant events for context (prioritizes high-engagement content)."""
        events = self.memory_store.get_events(
            profile_id=profile_id,
            start_time=start_time
        )
        
        if event_types:
            events = [e for e in events if e.event_type in event_types]
        
        # Sort by engagement (likes + comments + shares)
        def get_engagement_score(event):
            if not event.metrics:
                return 0
            return (
                event.metrics.get("likes", 0) +
                event.metrics.get("comments", 0) +
                event.metrics.get("shares", 0)
            )
        
        events.sort(key=get_engagement_score, reverse=True)
        return events[:limit]
    
    def _format_context(self, events: List[MemoryEvent], profile_id: str) -> str:
        """Format events into context string for agents."""
        if not events:
            return f"No memory context available for profile {profile_id}"
        
        context_parts = [
            f"Memory Context for Profile: {profile_id}",
            f"Total Events: {len(events)}",
            "=" * 50
        ]
        
        for i, event in enumerate(events, 1):
            entry = MemoryEntry.from_memory_event(event)
            context_parts.append(f"\n--- Event {i} ---")
            context_parts.append(entry.to_context())
        
        return "\n".join(context_parts)
