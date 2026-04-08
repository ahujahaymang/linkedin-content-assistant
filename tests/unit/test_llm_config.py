"""Unit tests for LLM configuration."""

import pytest
from linkedin_content_assistant.llm import LLMConfig, ProviderConfig, LLMProvider


class TestProviderConfig:
    """Test ProviderConfig validation and creation."""
    
    def test_valid_provider_config(self):
        """Test creating a valid provider configuration."""
        config = ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1",
            max_tokens=4000,
            temperature=0.7
        )
        
        assert config.provider == LLMProvider.BEDROCK_CLAUDE
        assert config.model == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert config.region == "us-east-1"
        assert config.max_tokens == 4000
        assert config.temperature == 0.7
    
    def test_provider_config_defaults(self):
        """Test provider configuration with default values."""
        config = ProviderConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4"
        )
        
        assert config.max_tokens == 4000
        assert config.temperature == 0.7
        assert config.timeout == 30
        assert config.retry_attempts == 3
        assert config.retry_delay == 1.0
    
    def test_invalid_temperature(self):
        """Test that invalid temperature raises validation error."""
        with pytest.raises(ValueError):
            ProviderConfig(
                provider=LLMProvider.OPENAI,
                model="gpt-4",
                temperature=3.0  # Invalid: > 2.0
            )
    
    def test_invalid_max_tokens(self):
        """Test that invalid max_tokens raises validation error."""
        with pytest.raises(ValueError):
            ProviderConfig(
                provider=LLMProvider.OPENAI,
                model="gpt-4",
                max_tokens=0  # Invalid: < 1
            )


class TestLLMConfig:
    """Test LLMConfig validation and creation."""
    
    def test_valid_llm_config(self):
        """Test creating a valid LLM configuration."""
        primary = ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0"
        )
        fallback = ProviderConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4"
        )
        
        config = LLMConfig(
            primary_provider=primary,
            fallback_providers=[fallback],
            enable_fallback=True
        )
        
        assert config.primary_provider == primary
        assert len(config.fallback_providers) == 1
        assert config.fallback_providers[0] == fallback
        assert config.enable_fallback is True
    
    def test_get_all_providers(self):
        """Test getting all providers in order."""
        primary = ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0"
        )
        fallback1 = ProviderConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4"
        )
        fallback2 = ProviderConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-sonnet-20240229"
        )
        
        config = LLMConfig(
            primary_provider=primary,
            fallback_providers=[fallback1, fallback2]
        )
        
        all_providers = config.get_all_providers()
        assert len(all_providers) == 3
        assert all_providers[0] == primary
        assert all_providers[1] == fallback1
        assert all_providers[2] == fallback2
    
    def test_duplicate_provider_validation(self):
        """Test that duplicate primary and fallback provider raises error."""
        primary = ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0"
        )
        fallback = ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0"
        )
        
        with pytest.raises(ValueError, match="cannot be the same as primary"):
            LLMConfig(
                primary_provider=primary,
                fallback_providers=[fallback]
            )
    
    def test_default_config(self):
        """Test creating default configuration."""
        config = LLMConfig.default_config()
        
        assert config.primary_provider.provider == LLMProvider.BEDROCK_CLAUDE
        assert config.primary_provider.model == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert len(config.fallback_providers) == 1
        assert config.fallback_providers[0].provider == LLMProvider.OPENAI
        assert config.enable_fallback is True
    
    def test_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            "primary_provider": {
                "provider": "bedrock_claude",
                "model": "anthropic.claude-3-sonnet-20240229-v1:0",
                "region": "us-east-1"
            },
            "fallback_providers": [
                {
                    "provider": "openai",
                    "model": "gpt-4",
                    "api_key": "test-key"
                }
            ],
            "enable_fallback": True
        }
        
        config = LLMConfig.from_dict(config_dict)
        
        assert config.primary_provider.provider == LLMProvider.BEDROCK_CLAUDE
        assert config.primary_provider.model == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert len(config.fallback_providers) == 1
        assert config.fallback_providers[0].provider == LLMProvider.OPENAI
    
    def test_fallback_on_errors_default(self):
        """Test default fallback error types."""
        config = LLMConfig.default_config()
        
        assert "rate_limit" in config.fallback_on_errors
        assert "model_not_found" in config.fallback_on_errors
        assert "timeout" in config.fallback_on_errors
