"""Base agent interface and abstract classes for stateless execution."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class AgentType(Enum):
    """Types of LinkedIn agents."""
    CONTENT_STRATEGY = "content_strategy"
    DRAFTING = "drafting"
    QUALITY_CRITIQUE = "quality_critique"
    ENGAGEMENT_MONITOR = "engagement_monitor"
    FEED_SCANNER = "feed_scanner"
    PROFILE_EVOLUTION = "profile_evolution"


class ValidationStatus(Enum):
    """Validation result status."""
    VALID = "valid"
    INVALID = "invalid"
    REQUIRES_APPROVAL = "requires_approval"


@dataclass
class ProfileContext:
    """Profile context for agent execution."""
    profile_id: str
    identity: Dict[str, Any]
    behavior: Dict[str, Any]
    version: int
    last_updated: datetime
    
    def get_identity_field(self, field: str) -> Any:
        """Get immutable identity field."""
        return self.identity.get(field)
    
    def get_behavior_field(self, field: str) -> Any:
        """Get adaptive behavior field."""
        return self.behavior.get(field)


@dataclass
class AgentOutput:
    """Output from agent execution."""
    agent_type: AgentType
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    requires_approval: bool = True
    confidence_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "agent_type": self.agent_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "requires_approval": self.requires_approval,
            "confidence_score": self.confidence_score
        }


@dataclass
class ValidationResult:
    """Result of agent output validation."""
    status: ValidationStatus
    errors: List[str]
    warnings: List[str]
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.status == ValidationStatus.VALID
    
    @property
    def has_errors(self) -> bool:
        """Check if validation has errors."""
        return len(self.errors) > 0


class LinkedInAgent(ABC):
    """Abstract base class for LinkedIn agents.
    
    All agents must be stateless and receive context externally.
    This ensures MCP compatibility and profile isolation.
    """
    
    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
    
    @abstractmethod
    def execute(self, context: ProfileContext, memory: Any) -> AgentOutput:
        """Execute agent logic with externalized context.
        
        Args:
            context: Profile-specific context and configuration
            memory: Memory store for retrieving relevant history
            
        Returns:
            AgentOutput with results and metadata
            
        Raises:
            AgentError: If execution fails
        """
        pass
    
    @abstractmethod
    def validate_output(self, output: AgentOutput) -> ValidationResult:
        """Validate agent output against policies and constraints.
        
        Args:
            output: Agent output to validate
            
        Returns:
            ValidationResult with status and any errors/warnings
        """
        pass
    
    def get_required_context_fields(self) -> List[str]:
        """Get list of required context fields for this agent.
        
        Returns:
            List of required field names from ProfileContext
        """
        return []
    
    def get_memory_query_params(self, context: ProfileContext) -> Dict[str, Any]:
        """Get parameters for querying relevant memory.
        
        Args:
            context: Profile context
            
        Returns:
            Dictionary of query parameters for memory store
        """
        return {
            "profile_id": context.profile_id,
            "agent_type": self.agent_type.value
        }


class StatelessAgentMixin:
    """Mixin to enforce stateless agent behavior."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prevent instance variables that could store state
        self._locked = True
    
    def __setattr__(self, name: str, value: Any) -> None:
        """Prevent setting instance variables after initialization."""
        if hasattr(self, '_locked') and self._locked:
            if not name.startswith('_') and name not in ['agent_type', 'llm_factory']:
                raise AttributeError(
                    f"Cannot set attribute '{name}' on stateless agent. "
                    "Use externalized context instead."
                )
        super().__setattr__(name, value)
