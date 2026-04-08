"""Memory event data models for the LinkedIn AI Manager."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional
import json
import uuid


@dataclass
class MemoryEvent:
    """Represents a single memory event in the system."""
    
    timestamp: datetime
    event_type: str  # "post", "comment", "engagement", "profile_update"
    content: Dict[str, Any]
    metrics: Optional[Dict[str, Any]]
    profile_id: str
    id: str = None
    
    def __post_init__(self):
        """Generate ID if not provided."""
        if self.id is None:
            self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime to ISO string for JSON serialization
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEvent':
        """Create MemoryEvent from dictionary."""
        # Convert ISO string back to datetime
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MemoryEvent':
        """Create MemoryEvent from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class MemoryEntry:
    """Represents a memory entry with additional context information."""
    
    id: str
    profile_id: str
    event_type: str
    content: Dict[str, Any]
    metrics: Optional[Dict[str, Any]]
    timestamp: datetime
    tags: Optional[list] = None
    
    def __post_init__(self):
        """Initialize tags if not provided."""
        if self.tags is None:
            self.tags = []
    
    def to_context(self) -> str:
        """Convert to context string for agents."""
        context_parts = [
            f"Event: {self.event_type}",
            f"Time: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Content: {json.dumps(self.content, indent=2)}"
        ]
        
        if self.metrics:
            context_parts.append(f"Metrics: {json.dumps(self.metrics, indent=2)}")
        
        if self.tags:
            context_parts.append(f"Tags: {', '.join(self.tags)}")
        
        return "\n".join(context_parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime to ISO string for JSON serialization
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """Create MemoryEntry from dictionary."""
        # Convert ISO string back to datetime
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MemoryEntry':
        """Create MemoryEntry from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_memory_event(cls, event: MemoryEvent, tags: Optional[list] = None) -> 'MemoryEntry':
        """Create MemoryEntry from MemoryEvent."""
        return cls(
            id=event.id,
            profile_id=event.profile_id,
            event_type=event.event_type,
            content=event.content,
            metrics=event.metrics,
            timestamp=event.timestamp,
            tags=tags or []
        )
