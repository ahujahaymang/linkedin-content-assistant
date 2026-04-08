"""Base classes for LLM integration."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    BEDROCK_CLAUDE = "bedrock_claude"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    provider: LLMProvider
    model: str
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    
    def __init__(self, message: str, provider: Optional[LLMProvider] = None, 
                 original_error: Optional[Exception] = None):
        super().__init__(message)
        self.provider = provider
        self.original_error = original_error


class RateLimitError(LLMError):
    """Raised when rate limits are exceeded."""
    pass


class AuthenticationError(LLMError):
    """Raised when authentication fails."""
    pass


class ModelNotFoundError(LLMError):
    """Raised when the specified model is not available."""
    pass


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    def __init__(self, provider: LLMProvider, config: Dict[str, Any]):
        self.provider = provider
        self.config = config
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    async def generate_with_system(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        """Generate a response with system and user prompts."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate the client configuration."""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models for this provider."""
        pass
