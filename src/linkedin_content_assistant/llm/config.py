"""LLM configuration management."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator
from .base import LLMProvider


class ProviderConfig(BaseModel):
    """Configuration for a specific LLM provider."""
    
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    region: Optional[str] = None
    endpoint: Optional[str] = None
    max_tokens: int = Field(default=4000, ge=1, le=100000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    timeout: int = Field(default=30, ge=1, le=300)
    retry_attempts: int = Field(default=3, ge=1, le=10)
    retry_delay: float = Field(default=1.0, ge=0.1, le=60.0)
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        if v not in LLMProvider:
            raise ValueError(f"Unsupported provider: {v}")
        return v


class LLMConfig(BaseModel):
    """Main LLM configuration with fallback support."""
    
    primary_provider: ProviderConfig
    fallback_providers: List[ProviderConfig] = Field(default_factory=list)
    enable_fallback: bool = Field(default=True)
    fallback_on_errors: List[str] = Field(
        default_factory=lambda: ["rate_limit", "model_not_found", "timeout"]
    )
    
    @field_validator('fallback_providers')
    @classmethod
    def validate_fallback_providers(cls, v, info):
        if info.data and 'primary_provider' in info.data:
            primary = info.data['primary_provider']
            for fallback in v:
                if fallback.provider == primary.provider and fallback.model == primary.model:
                    raise ValueError("Fallback provider cannot be the same as primary provider")
        return v
    
    def get_all_providers(self) -> List[ProviderConfig]:
        """Get all providers in order of preference."""
        return [self.primary_provider] + self.fallback_providers
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'LLMConfig':
        """Create LLMConfig from dictionary."""
        return cls(**config_dict)
    
    @classmethod
    def default_config(cls) -> 'LLMConfig':
        """Create default configuration with AWS Bedrock Claude as primary."""
        return cls(
            primary_provider=ProviderConfig(
                provider=LLMProvider.BEDROCK_CLAUDE,
                model="anthropic.claude-3-sonnet-20240229-v1:0",
                region="us-east-1",
                max_tokens=4000,
                temperature=0.7
            ),
            fallback_providers=[
                ProviderConfig(
                    provider=LLMProvider.OPENAI,
                    model="gpt-4",
                    max_tokens=4000,
                    temperature=0.7
                )
            ]
        )
