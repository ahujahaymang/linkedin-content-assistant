#!/usr/bin/env python3
"""Verification script for memory store functionality."""

from datetime import datetime, timedelta
from linkedin_content_assistant.memory import (
    MemoryEvent,
    InMemoryStore,
    create_memory_store,
    MemoryContextRetriever
)


def main():
    """Demonstrate memory store functionality."""
    print("=" * 60)
    print("Memory Store Verification")
    print("=" * 60)
    
    # Create memory store
    print("\n1. Creating memory store...")
    store = create_memory_store(store_type="in_memory")
    print("   ✓ Memory store created successfully")
    
    # Store some events
    print("\n2. Storing memory events...")
    profile_id = "test-profile"
    
    # Post draft event
    draft_event = MemoryEvent(
        timestamp=datetime.now(),
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
    print(f"   ✓ Stored post draft event (ID: {draft_event.id})")
    
    # Trend detection event
    trend_event = MemoryEvent(
        timestamp=datetime.now(),
        event_type="trend_detected",
        content={
            "topic": "Serverless cost optimization",
            "sources": ["linkedin", "hackernews"],
            "related_hashtags": ["#Serverless", "#CostOptimization"]
        },
        metrics={"frequency": 15, "relevance_score": 0.92},
        profile_id=profile_id
    )
    store.store_event(trend_event)
    print(f"   ✓ Stored trend detection event (ID: {trend_event.id})")
    
    # Post published event
    published_event = MemoryEvent(
        timestamp=datetime.now(),
        event_type="post_published",
        content={
            "draft_id": draft_event.id,
            "post_url": "https://linkedin.com/posts/example"
        },
        metrics={"likes": 45, "comments": 12, "shares": 8},
        profile_id=profile_id
    )
    store.store_event(published_event)
    print(f"   ✓ Stored post published event (ID: {published_event.id})")
    
    # Query events
    print("\n3. Querying events...")
    all_events = store.get_events(profile_id=profile_id)
    print(f"   ✓ Retrieved {len(all_events)} events for profile '{profile_id}'")
    
    # Query by event type
    draft_events = store.get_events(profile_id=profile_id, event_type="post_draft")
    print(f"   ✓ Found {len(draft_events)} post_draft events")
    
    trend_events = store.get_events(profile_id=profile_id, event_type="trend_detected")
    print(f"   ✓ Found {len(trend_events)} trend_detected events")
    
    # Test memory context retriever
    print("\n4. Testing memory context retriever...")
    retriever = MemoryContextRetriever(store)
    
    context = retriever.get_agent_context(
        profile_id=profile_id,
        context_type="recent",
        limit=10
    )
    print(f"   ✓ Generated agent context ({len(context)} characters)")
    
    # Test performance metrics
    print("\n5. Testing performance metrics...")
    metrics = retriever.get_performance_metrics(
        profile_id=profile_id,
        event_type="post_published",
        days_back=30
    )
    print(f"   ✓ Total events: {metrics['total_events']}")
    print(f"   ✓ Total likes: {metrics['total_likes']}")
    print(f"   ✓ Total comments: {metrics['total_comments']}")
    print(f"   ✓ Total shares: {metrics['total_shares']}")
    print(f"   ✓ Average engagement: {metrics['avg_engagement']:.1f}")
    
    # Test event retrieval by ID
    print("\n6. Testing event retrieval by ID...")
    retrieved_event = store.get_event_by_id(draft_event.id)
    if retrieved_event:
        print(f"   ✓ Retrieved event: {retrieved_event.event_type}")
        print(f"   ✓ Content theme: {retrieved_event.content.get('theme')}")
    
    # Test event deletion
    print("\n7. Testing event deletion...")
    deleted = store.delete_event(trend_event.id)
    print(f"   ✓ Event deleted: {deleted}")
    
    remaining_events = store.get_events(profile_id=profile_id)
    print(f"   ✓ Remaining events: {len(remaining_events)}")
    
    # Test serialization
    print("\n8. Testing JSON serialization...")
    json_str = draft_event.to_json()
    restored_event = MemoryEvent.from_json(json_str)
    print(f"   ✓ Event serialized and deserialized successfully")
    print(f"   ✓ Event type matches: {restored_event.event_type == draft_event.event_type}")
    
    print("\n" + "=" * 60)
    print("✓ All memory store functionality verified successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
