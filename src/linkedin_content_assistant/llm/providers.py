"""LLM provider implementations."""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any

from .base import (
    BaseLLMClient, LLMProvider, LLMResponse, LLMError, 
    RateLimitError, AuthenticationError, ModelNotFoundError
)

logger = logging.getLogger(__name__)


class BedrockClaudeClient(BaseLLMClient):
    """AWS Bedrock Claude client implementation."""
    
    def __init__(self, provider: LLMProvider, config: Dict[str, Any]):
        super().__init__(provider, config)
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Bedrock client."""
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
            
            self._client = boto3.client(
                'bedrock-runtime',
                region_name=self.config.get('region', 'us-east-1'),
                aws_access_key_id=self.config.get('aws_access_key_id'),
                aws_secret_access_key=self.config.get('aws_secret_access_key')
            )
            self._client_error = ClientError
            self._no_credentials_error = NoCredentialsError
            
        except ImportError:
            raise LLMError(
                "boto3 is required for Bedrock integration. Install with: pip install boto3",
                provider=self.provider
            )
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response using Claude via Bedrock."""
        return await self.generate_with_system("", prompt, **kwargs)
    
    async def generate_with_system(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        """Generate response with system and user prompts."""
        try:
            # Prepare the request body for Claude on Bedrock
            # Note: system prompt goes in a separate field, not in messages
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": kwargs.get('max_tokens', self.config.get('max_tokens', 4000)),
                "temperature": kwargs.get('temperature', self.config.get('temperature', 0.7)),
                "messages": [
                    {"role": "user", "content": user_prompt}
                ]
            }
            
            # Add system prompt if provided
            if system_prompt:
                body["system"] = system_prompt
            
            # Make the API call
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.invoke_model(
                    modelId=self.config['model'],
                    body=json.dumps(body),
                    contentType='application/json'
                )
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            return LLMResponse(
                content=content,
                provider=self.provider,
                model=self.config['model'],
                usage=response_body.get('usage'),
                metadata={'response_id': response.get('ResponseMetadata', {}).get('RequestId')}
            )
            
        except self._no_credentials_error as e:
            raise AuthenticationError(
                "AWS credentials not found or invalid",
                provider=self.provider,
                original_error=e
            )
        except self._client_error as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ThrottlingException':
                raise RateLimitError(
                    "Rate limit exceeded for Bedrock",
                    provider=self.provider,
                    original_error=e
                )
            elif error_code == 'ValidationException':
                raise ModelNotFoundError(
                    f"Model {self.config['model']} not found or not accessible",
                    provider=self.provider,
                    original_error=e
                )
            else:
                raise LLMError(
                    f"Bedrock API error: {e}",
                    provider=self.provider,
                    original_error=e
                )
        except Exception as e:
            raise LLMError(
                f"Unexpected error in Bedrock client: {e}",
                provider=self.provider,
                original_error=e
            )
    
    def validate_config(self) -> bool:
        """Validate Bedrock configuration."""
        required_fields = ['model']
        for field in required_fields:
            if field not in self.config:
                return False
        return True
    
    def get_available_models(self) -> List[str]:
        """Get available Claude models on Bedrock."""
        return [
            "anthropic.claude-3-sonnet-20240229-v1:0",
            "anthropic.claude-3-haiku-20240307-v1:0",
            "anthropic.claude-v2:1",
            "anthropic.claude-v2",
            "anthropic.claude-instant-v1"
        ]


class OpenAIClient(BaseLLMClient):
    """OpenAI client implementation."""
    
    def __init__(self, provider: LLMProvider, config: Dict[str, Any]):
        super().__init__(provider, config)
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the OpenAI client."""
        try:
            import openai
            
            api_key = self.config.get('api_key')
            if not api_key:
                raise AuthenticationError(
                    "OpenAI API key is required",
                    provider=self.provider
                )
            
            self._client = openai.AsyncOpenAI(api_key=api_key)
            self._openai_error = openai.OpenAIError
            self._rate_limit_error = openai.RateLimitError
            self._auth_error = openai.AuthenticationError
            
        except ImportError:
            raise LLMError(
                "openai is required for OpenAI integration. Install with: pip install openai",
                provider=self.provider
            )
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response using OpenAI."""
        return await self.generate_with_system("", prompt, **kwargs)
    
    async def generate_with_system(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        """Generate response with system and user prompts."""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})
            
            response = await self._client.chat.completions.create(
                model=self.config['model'],
                messages=messages,
                max_tokens=kwargs.get('max_tokens', self.config.get('max_tokens', 4000)),
                temperature=kwargs.get('temperature', self.config.get('temperature', 0.7)),
                timeout=self.config.get('timeout', 30)
            )
            
            content = response.choices[0].message.content
            
            return LLMResponse(
                content=content,
                provider=self.provider,
                model=self.config['model'],
                usage=response.usage.dict() if response.usage else None,
                metadata={'response_id': response.id}
            )
            
        except self._auth_error as e:
            raise AuthenticationError(
                "OpenAI authentication failed",
                provider=self.provider,
                original_error=e
            )
        except self._rate_limit_error as e:
            raise RateLimitError(
                "OpenAI rate limit exceeded",
                provider=self.provider,
                original_error=e
            )
        except self._openai_error as e:
            if "model" in str(e).lower():
                raise ModelNotFoundError(
                    f"OpenAI model {self.config['model']} not found",
                    provider=self.provider,
                    original_error=e
                )
            else:
                raise LLMError(
                    f"OpenAI API error: {e}",
                    provider=self.provider,
                    original_error=e
                )
        except Exception as e:
            raise LLMError(
                f"Unexpected error in OpenAI client: {e}",
                provider=self.provider,
                original_error=e
            )
    
    def validate_config(self) -> bool:
        """Validate OpenAI configuration."""
        required_fields = ['model', 'api_key']
        for field in required_fields:
            if field not in self.config:
                return False
        return True
    
    def get_available_models(self) -> List[str]:
        """Get available OpenAI models."""
        return [
            "gpt-4",
            "gpt-4-turbo-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k"
        ]


class AnthropicClient(BaseLLMClient):
    """Direct Anthropic client implementation."""
    
    def __init__(self, provider: LLMProvider, config: Dict[str, Any]):
        super().__init__(provider, config)
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Anthropic client."""
        try:
            import anthropic
            
            api_key = self.config.get('api_key')
            if not api_key:
                raise AuthenticationError(
                    "Anthropic API key is required",
                    provider=self.provider
                )
            
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
            self._anthropic_error = anthropic.AnthropicError
            self._rate_limit_error = anthropic.RateLimitError
            self._auth_error = anthropic.AuthenticationError
            
        except ImportError:
            raise LLMError(
                "anthropic is required for Anthropic integration. Install with: pip install anthropic",
                provider=self.provider
            )
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response using Anthropic."""
        return await self.generate_with_system("", prompt, **kwargs)
    
    async def generate_with_system(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        """Generate response with system and user prompts."""
        try:
            response = await self._client.messages.create(
                model=self.config['model'],
                system=system_prompt if system_prompt else None,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=kwargs.get('max_tokens', self.config.get('max_tokens', 4000)),
                temperature=kwargs.get('temperature', self.config.get('temperature', 0.7))
            )
            
            content = response.content[0].text
            
            return LLMResponse(
                content=content,
                provider=self.provider,
                model=self.config['model'],
                usage=response.usage.dict() if response.usage else None,
                metadata={'response_id': response.id}
            )
            
        except self._auth_error as e:
            raise AuthenticationError(
                "Anthropic authentication failed",
                provider=self.provider,
                original_error=e
            )
        except self._rate_limit_error as e:
            raise RateLimitError(
                "Anthropic rate limit exceeded",
                provider=self.provider,
                original_error=e
            )
        except self._anthropic_error as e:
            if "model" in str(e).lower():
                raise ModelNotFoundError(
                    f"Anthropic model {self.config['model']} not found",
                    provider=self.provider,
                    original_error=e
                )
            else:
                raise LLMError(
                    f"Anthropic API error: {e}",
                    provider=self.provider,
                    original_error=e
                )
        except Exception as e:
            raise LLMError(
                f"Unexpected error in Anthropic client: {e}",
                provider=self.provider,
                original_error=e
            )
    
    def validate_config(self) -> bool:
        """Validate Anthropic configuration."""
        required_fields = ['model', 'api_key']
        for field in required_fields:
            if field not in self.config:
                return False
        return True
    
    def get_available_models(self) -> List[str]:
        """Get available Anthropic models."""
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        ]
