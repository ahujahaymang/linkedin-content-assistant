"""Integration tests for LLM components."""

import pytest
from linkedin_content_assistant.llm import (
    LLMFactory, LLMConfig, ProviderConfig, LLMProvider
)


class TestLLMIntegration:
    """Test LLM integration components work together."""
    
    def test_config_to_factory_integration(self):
        """Test creating factory from config."""
        # Create config
        config = ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1",
            max_tokens=2000,
            temperature=0.75
        )
        
        llm_config = LLMConfig(
            primary_provider=config,
            enable_fallback=False
        )
        
        # Create factory from config
        factory = LLMFactory(llm_config)
        
        # Verify factory has the config
        assert factory.config == llm_config
        assert factory.config.primary_provider.provider == LLMProvider.BEDROCK_CLAUDE
        assert factory.config.primary_provider.max_tokens == 2000
        assert factory.config.primary_provider.temperature == 0.75
    
    def test_dict_to_factory_integration(self):
        """Test creating factory from dictionary."""
        config_dict = {
            "primary_provider": {
                "provider": "bedrock_claude",
                "model": "anthropic.claude-3-sonnet-20240229-v1:0",
                "region": "us-east-1",
                "max_tokens": 3000,
                "temperature": 0.8
            },
            "enable_fallback": False
        }
        
        # Create factory from dict
        factory = LLMFactory.from_dict(config_dict)
        
        # Verify configuration
        assert factory.config.primary_provider.provider == LLMProvider.BEDROCK_CLAUDE
        assert factory.config.primary_provider.max_tokens == 3000
        assert factory.config.primary_provider.temperature == 0.8
        assert factory.config.enable_fallback is False
    
    def test_multiple_providers_configuration(self):
        """Test configuring multiple providers with fallback."""
        primary = ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0"
        )
        
        fallback1 = ProviderConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4",
            api_key="dummy-key"
        )
        
        fallback2 = ProviderConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-sonnet-20240229",
            api_key="dummy-key"
        )
        
        config = LLMConfig(
            primary_provider=primary,
            fallback_providers=[fallback1, fallback2],
            enable_fallback=True
        )
        
        factory = LLMFactory(config)
        
        # Verify all providers are configured
        all_providers = factory.config.get_all_providers()
        assert len(all_providers) == 3
        assert all_providers[0].provider == LLMProvider.BEDROCK_CLAUDE
        assert all_providers[1].provider == LLMProvider.OPENAI
        assert all_providers[2].provider == LLMProvider.ANTHROPIC
    
    def test_provider_validation(self):
        """Test that provider configurations are validated."""
        # Valid config should work
        valid_config = ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            temperature=0.7,
            max_tokens=4000
        )
        
        assert valid_config.temperature == 0.7
        assert valid_config.max_tokens == 4000
        
        # Invalid temperature should raise error
        with pytest.raises(ValueError):
            ProviderConfig(
                provider=LLMProvider.BEDROCK_CLAUDE,
                model="test-model",
                temperature=5.0  # Invalid
            )
        
        # Invalid max_tokens should raise error
        with pytest.raises(ValueError):
            ProviderConfig(
                provider=LLMProvider.BEDROCK_CLAUDE,
                model="test-model",
                max_tokens=-1  # Invalid
            )
    
    def test_default_configuration(self):
        """Test default configuration is valid."""
        config = LLMConfig.default_config()
        factory = LLMFactory(config)
        
        # Verify default config
        assert config.primary_provider.provider == LLMProvider.BEDROCK_CLAUDE
        assert config.primary_provider.temperature == 0.7
        assert config.primary_provider.max_tokens == 4000
        assert config.enable_fallback is True
        assert len(config.fallback_providers) >= 1
        
        # Verify factory can be created
        assert factory.config == config
    
    def test_temperature_range_validation(self):
        """Test temperature must be between 0.0 and 2.0."""
        # Valid temperatures
        for temp in [0.0, 0.5, 0.7, 1.0, 1.5, 2.0]:
            config = ProviderConfig(
                provider=LLMProvider.BEDROCK_CLAUDE,
                model="test-model",
                temperature=temp
            )
            assert config.temperature == temp
        
        # Invalid temperatures
        for temp in [-0.1, 2.1, 3.0]:
            with pytest.raises(ValueError):
                ProviderConfig(
                    provider=LLMProvider.BEDROCK_CLAUDE,
                    model="test-model",
                    temperature=temp
                )
    
    def test_retry_configuration(self):
        """Test retry configuration is properly set."""
        config = ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="test-model",
            retry_attempts=5,
            retry_delay=2.0
        )
        
        assert config.retry_attempts == 5
        assert config.retry_delay == 2.0
        
        # Test defaults
        default_config = ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="test-model"
        )
        
        assert default_config.retry_attempts == 3
        assert default_config.retry_delay == 1.0
