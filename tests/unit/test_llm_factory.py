"""Unit tests for LLM factory."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from linkedin_content_assistant.llm import (
    LLMFactory, LLMConfig, ProviderConfig, LLMProvider,
    LLMResponse, LLMError, RateLimitError
)


class TestLLMFactory:
    """Test LLMFactory initialization and client management."""
    
    def test_factory_initialization(self):
        """Test factory initializes with valid config."""
        config = LLMConfig.default_config()
        factory = LLMFactory(config)
        
        assert factory.config == config
        assert isinstance(factory._clients, dict)
    
    def test_get_available_clients(self):
        """Test getting list of available clients."""
        config = LLMConfig.default_config()
        
        with patch('linkedin_content_assistant.llm.factory.BedrockClaudeClient') as mock_bedrock:
            with patch('linkedin_content_assistant.llm.factory.OpenAIClient') as mock_openai:
                # Mock validate_config to return True
                mock_bedrock.return_value.validate_config.return_value = True
                mock_openai.return_value.validate_config.return_value = True
                
                factory = LLMFactory(config)
                clients = factory.get_available_clients()
                
                assert len(clients) >= 1
                assert any('bedrock_claude' in client for client in clients)
    
    def test_get_primary_client(self):
        """Test getting the primary client."""
        config = LLMConfig.default_config()
        
        with patch('linkedin_content_assistant.llm.factory.BedrockClaudeClient') as mock_bedrock:
            mock_client = Mock()
            mock_client.validate_config.return_value = True
            mock_bedrock.return_value = mock_client
            
            factory = LLMFactory(config)
            client = factory.get_client()
            
            assert client is not None
    
    def test_get_specific_client(self):
        """Test getting a specific client by provider and model."""
        primary = ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0"
        )
        config = LLMConfig(primary_provider=primary)
        
        with patch('linkedin_content_assistant.llm.factory.BedrockClaudeClient') as mock_bedrock:
            mock_client = Mock()
            mock_client.validate_config.return_value = True
            mock_bedrock.return_value = mock_client
            
            factory = LLMFactory(config)
            client = factory.get_client(
                provider=LLMProvider.BEDROCK_CLAUDE,
                model="anthropic.claude-3-sonnet-20240229-v1:0"
            )
            
            assert client is not None
    
    def test_get_nonexistent_client_raises_error(self):
        """Test that getting a non-existent client raises error."""
        config = LLMConfig.default_config()
        
        with patch('linkedin_content_assistant.llm.factory.BedrockClaudeClient') as mock_bedrock:
            mock_bedrock.return_value.validate_config.return_value = True
            
            factory = LLMFactory(config)
            
            with pytest.raises(LLMError, match="Client not found"):
                factory.get_client(
                    provider=LLMProvider.ANTHROPIC,
                    model="nonexistent-model"
                )
    
    @pytest.mark.asyncio
    async def test_generate_with_system(self):
        """Test generating response with system prompt."""
        config = LLMConfig.default_config()
        
        with patch('linkedin_content_assistant.llm.factory.BedrockClaudeClient') as mock_bedrock:
            mock_client = Mock()
            mock_client.validate_config.return_value = True
            mock_response = LLMResponse(
                content="Test response",
                provider=LLMProvider.BEDROCK_CLAUDE,
                model="anthropic.claude-3-sonnet-20240229-v1:0"
            )
            mock_client.generate_with_system = AsyncMock(return_value=mock_response)
            mock_bedrock.return_value = mock_client
            
            factory = LLMFactory(config)
            response = await factory.generate_with_system(
                system_prompt="You are a helpful assistant",
                user_prompt="Hello"
            )
            
            assert response.content == "Test response"
            assert response.provider == LLMProvider.BEDROCK_CLAUDE
    
    @pytest.mark.asyncio
    async def test_fallback_on_rate_limit(self):
        """Test fallback to secondary provider on rate limit."""
        primary = ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            retry_attempts=1
        )
        fallback = ProviderConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4",
            api_key="test-key",
            retry_attempts=1
        )
        config = LLMConfig(
            primary_provider=primary,
            fallback_providers=[fallback],
            enable_fallback=True
        )
        
        with patch('linkedin_content_assistant.llm.factory.BedrockClaudeClient') as mock_bedrock:
            with patch('linkedin_content_assistant.llm.factory.OpenAIClient') as mock_openai:
                # Primary fails with rate limit
                mock_bedrock_client = Mock()
                mock_bedrock_client.validate_config.return_value = True
                mock_bedrock_client.generate_with_system = AsyncMock(
                    side_effect=RateLimitError("Rate limit", provider=LLMProvider.BEDROCK_CLAUDE)
                )
                mock_bedrock.return_value = mock_bedrock_client
                
                # Fallback succeeds
                mock_openai_client = Mock()
                mock_openai_client.validate_config.return_value = True
                mock_response = LLMResponse(
                    content="Fallback response",
                    provider=LLMProvider.OPENAI,
                    model="gpt-4"
                )
                mock_openai_client.generate_with_system = AsyncMock(return_value=mock_response)
                mock_openai.return_value = mock_openai_client
                
                factory = LLMFactory(config)
                response = await factory.generate_with_system(
                    system_prompt="Test",
                    user_prompt="Hello"
                )
                
                assert response.content == "Fallback response"
                assert response.provider == LLMProvider.OPENAI
    
    @pytest.mark.asyncio
    async def test_all_providers_fail(self):
        """Test that error is raised when all providers fail."""
        primary = ProviderConfig(
            provider=LLMProvider.BEDROCK_CLAUDE,
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            retry_attempts=1
        )
        config = LLMConfig(
            primary_provider=primary,
            enable_fallback=False
        )
        
        with patch('linkedin_content_assistant.llm.factory.BedrockClaudeClient') as mock_bedrock:
            mock_client = Mock()
            mock_client.validate_config.return_value = True
            mock_client.generate_with_system = AsyncMock(
                side_effect=LLMError("Test error", provider=LLMProvider.BEDROCK_CLAUDE)
            )
            mock_bedrock.return_value = mock_client
            
            factory = LLMFactory(config)
            
            with pytest.raises(LLMError):
                await factory.generate_with_system(
                    system_prompt="Test",
                    user_prompt="Hello"
                )
    
    def test_health_check(self):
        """Test health check for all providers."""
        config = LLMConfig.default_config()
        
        with patch('linkedin_content_assistant.llm.factory.BedrockClaudeClient') as mock_bedrock:
            mock_client = Mock()
            mock_client.validate_config.return_value = True
            mock_bedrock.return_value = mock_client
            
            factory = LLMFactory(config)
            health = factory.health_check()
            
            assert isinstance(health, dict)
            assert len(health) >= 1
    
    def test_create_default(self):
        """Test creating factory with default config."""
        with patch('linkedin_content_assistant.llm.factory.BedrockClaudeClient') as mock_bedrock:
            mock_bedrock.return_value.validate_config.return_value = True
            
            factory = LLMFactory.create_default()
            
            assert factory.config.primary_provider.provider == LLMProvider.BEDROCK_CLAUDE
    
    def test_from_dict(self):
        """Test creating factory from dictionary."""
        config_dict = {
            "primary_provider": {
                "provider": "bedrock_claude",
                "model": "anthropic.claude-3-sonnet-20240229-v1:0"
            },
            "enable_fallback": False
        }
        
        with patch('linkedin_content_assistant.llm.factory.BedrockClaudeClient') as mock_bedrock:
            mock_bedrock.return_value.validate_config.return_value = True
            
            factory = LLMFactory.from_dict(config_dict)
            
            assert factory.config.primary_provider.provider == LLMProvider.BEDROCK_CLAUDE
            assert factory.config.enable_fallback is False
