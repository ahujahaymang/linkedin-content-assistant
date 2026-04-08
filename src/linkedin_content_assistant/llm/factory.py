"""LLM factory for creating and managing LLM clients with fallback support."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Type

from .base import (
    BaseLLMClient, LLMProvider, LLMResponse, LLMError,
    RateLimitError, AuthenticationError, ModelNotFoundError
)
from .config import LLMConfig, ProviderConfig
from .providers import BedrockClaudeClient, OpenAIClient, AnthropicClient

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating and managing LLM clients with fallback support."""
    
    # Provider class mapping
    _PROVIDER_CLASSES: Dict[LLMProvider, Type[BaseLLMClient]] = {
        LLMProvider.BEDROCK_CLAUDE: BedrockClaudeClient,
        LLMProvider.OPENAI: OpenAIClient,
        LLMProvider.ANTHROPIC: AnthropicClient,
    }
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._clients: Dict[str, BaseLLMClient] = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize all configured clients."""
        for provider_config in self.config.get_all_providers():
            try:
                client = self._create_client(provider_config)
                if client.validate_config():
                    client_key = f"{provider_config.provider.value}_{provider_config.model}"
                    self._clients[client_key] = client
                    logger.info(f"Initialized LLM client: {client_key}")
                else:
                    logger.warning(f"Invalid configuration for {provider_config.provider}")
            except Exception as e:
                logger.error(f"Failed to initialize {provider_config.provider}: {e}")
    
    def _create_client(self, provider_config: ProviderConfig) -> BaseLLMClient:
        """Create a client for the specified provider."""
        provider_class = self._PROVIDER_CLASSES.get(provider_config.provider)
        if not provider_class:
            raise LLMError(f"Unsupported provider: {provider_config.provider}")
        
        # Convert ProviderConfig to dict for client initialization
        config_dict = provider_config.model_dump()
        return provider_class(provider_config.provider, config_dict)
    
    def get_client(self, provider: Optional[LLMProvider] = None, model: Optional[str] = None) -> BaseLLMClient:
        """Get a specific client or the primary client."""
        if provider and model:
            client_key = f"{provider.value}_{model}"
            if client_key in self._clients:
                return self._clients[client_key]
            raise LLMError(f"Client not found: {client_key}")
        
        # Return primary client
        primary = self.config.primary_provider
        primary_key = f"{primary.provider.value}_{primary.model}"
        if primary_key in self._clients:
            return self._clients[primary_key]
        
        raise LLMError("No primary client available")
    
    def get_available_clients(self) -> List[str]:
        """Get list of available client keys."""
        return list(self._clients.keys())
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response with automatic fallback support."""
        return await self.generate_with_system("", prompt, **kwargs)
    
    async def generate_with_system(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        """Generate response with system prompt and automatic fallback support."""
        providers = self.config.get_all_providers()
        last_error = None
        
        for i, provider_config in enumerate(providers):
            client_key = f"{provider_config.provider.value}_{provider_config.model}"
            
            if client_key not in self._clients:
                logger.warning(f"Client {client_key} not available, skipping")
                continue
            
            client = self._clients[client_key]
            is_primary = i == 0
            
            try:
                logger.info(f"Attempting generation with {client_key}")
                
                # Add retry logic for each provider
                for attempt in range(provider_config.retry_attempts):
                    try:
                        response = await client.generate_with_system(
                            system_prompt, user_prompt, **kwargs
                        )
                        
                        if not is_primary:
                            logger.warning(f"Used fallback provider: {client_key}")
                        
                        return response
                        
                    except (RateLimitError, ModelNotFoundError, AuthenticationError) as e:
                        # These errors should trigger fallback immediately
                        if self._should_fallback(e):
                            logger.warning(f"Fallback triggered by {type(e).__name__}: {e}")
                            break
                        else:
                            # For other errors, retry with delay
                            if attempt < provider_config.retry_attempts - 1:
                                delay = provider_config.retry_delay * (2 ** attempt)  # Exponential backoff
                                logger.info(f"Retrying {client_key} in {delay}s (attempt {attempt + 1})")
                                await asyncio.sleep(delay)
                            else:
                                raise
                    
                    except Exception as e:
                        # For unexpected errors, retry with delay
                        if attempt < provider_config.retry_attempts - 1:
                            delay = provider_config.retry_delay * (2 ** attempt)
                            logger.info(f"Retrying {client_key} in {delay}s due to error: {e}")
                            await asyncio.sleep(delay)
                        else:
                            raise LLMError(
                                f"Failed after {provider_config.retry_attempts} attempts",
                                provider=provider_config.provider,
                                original_error=e
                            )
            
            except Exception as e:
                last_error = e
                logger.error(f"Provider {client_key} failed: {e}")
                
                # If fallback is disabled or this is the last provider, raise the error
                if not self.config.enable_fallback or i == len(providers) - 1:
                    raise
                
                continue
        
        # If we get here, all providers failed
        raise LLMError(
            "All LLM providers failed",
            original_error=last_error
        )
    
    def _should_fallback(self, error: Exception) -> bool:
        """Determine if an error should trigger fallback."""
        if not self.config.enable_fallback:
            return False
        
        error_type = type(error).__name__.lower()
        for fallback_error in self.config.fallback_on_errors:
            if fallback_error.lower() in error_type:
                return True
        
        return False
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of all configured providers."""
        health_status = {}
        
        for client_key, client in self._clients.items():
            try:
                # Simple validation check
                is_healthy = client.validate_config()
                health_status[client_key] = is_healthy
            except Exception as e:
                logger.error(f"Health check failed for {client_key}: {e}")
                health_status[client_key] = False
        
        return health_status
    
    @classmethod
    def create_default(cls) -> 'LLMFactory':
        """Create factory with default configuration."""
        return cls(LLMConfig.default_config())
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'LLMFactory':
        """Create factory from configuration dictionary."""
        config = LLMConfig.from_dict(config_dict)
        return cls(config)
