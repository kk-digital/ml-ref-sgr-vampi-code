"""Provider abstractions for different LLM APIs."""

import os
from abc import ABC, abstractmethod
from typing import Any, Optional

from openai import AsyncOpenAI

from .models import ModelConfig, ProviderType


class BaseProvider(ABC):
    """Base class for LLM providers."""
    
    def __init__(self, model_config: ModelConfig):
        self.model_config = model_config
        self.client: Optional[AsyncOpenAI] = None
    
    @abstractmethod
    def get_client(self) -> AsyncOpenAI:
        """Get the OpenAI-compatible client for this provider."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name to use in API calls."""
        pass
    
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on token usage."""
        input_cost = (prompt_tokens / 1_000_000) * self.model_config.input_price_per_million
        output_cost = (completion_tokens / 1_000_000) * self.model_config.output_price_per_million
        return input_cost + output_cost
    
    def extract_usage(self, response: Any) -> dict:
        """Extract token usage from API response.
        
        Returns dict with: prompt_tokens, completion_tokens, total_tokens, thinking_tokens
        """
        usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "thinking_tokens": 0,
        }
        
        if hasattr(response, "usage") and response.usage:
            usage["prompt_tokens"] = getattr(response.usage, "prompt_tokens", 0) or 0
            usage["completion_tokens"] = getattr(response.usage, "completion_tokens", 0) or 0
            usage["total_tokens"] = getattr(response.usage, "total_tokens", 0) or 0
            
            # Check for thinking/reasoning tokens (varies by provider)
            if hasattr(response.usage, "completion_tokens_details"):
                details = response.usage.completion_tokens_details
                if details and hasattr(details, "reasoning_tokens"):
                    usage["thinking_tokens"] = details.reasoning_tokens or 0
        
        return usage


class OpenRouterProvider(BaseProvider):
    """Provider for OpenRouter API."""
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(self, model_config: ModelConfig):
        super().__init__(model_config)
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
    
    def get_client(self) -> AsyncOpenAI:
        if self.client is None:
            self.client = AsyncOpenAI(
                base_url=self.BASE_URL,
                api_key=self.api_key,
                default_headers={
                    "HTTP-Referer": "https://github.com/vamplabAI/sgr-vampi-code",
                    "X-Title": "SGR Vampi Code Benchmark",
                }
            )
        return self.client
    
    def get_model_name(self) -> str:
        return self.model_config.name
    
    def extract_usage(self, response: Any) -> dict:
        """Extract usage from OpenRouter response."""
        usage = super().extract_usage(response)
        
        # OpenRouter may include additional usage info
        if hasattr(response, "usage") and response.usage:
            # Check for native_tokens_prompt/completion (OpenRouter specific)
            if hasattr(response.usage, "native_tokens_prompt"):
                usage["prompt_tokens"] = response.usage.native_tokens_prompt or usage["prompt_tokens"]
            if hasattr(response.usage, "native_tokens_completion"):
                usage["completion_tokens"] = response.usage.native_tokens_completion or usage["completion_tokens"]
        
        return usage


class CerebrasProvider(BaseProvider):
    """Provider for Cerebras API."""
    
    BASE_URL = "https://api.cerebras.ai/v1"
    
    def __init__(self, model_config: ModelConfig):
        super().__init__(model_config)
        self.api_key = os.getenv("CEREBRAS_API_KEY")
        if not self.api_key:
            raise ValueError("CEREBRAS_API_KEY environment variable not set")
    
    def get_client(self) -> AsyncOpenAI:
        if self.client is None:
            self.client = AsyncOpenAI(
                base_url=self.BASE_URL,
                api_key=self.api_key,
            )
        return self.client
    
    def get_model_name(self) -> str:
        return self.model_config.name


def get_provider(model_config: ModelConfig) -> BaseProvider:
    """Factory function to get the appropriate provider for a model config."""
    providers = {
        ProviderType.OPENROUTER: OpenRouterProvider,
        ProviderType.CEREBRAS: CerebrasProvider,
    }
    
    provider_class = providers.get(model_config.provider)
    if provider_class is None:
        raise ValueError(f"Unknown provider type: {model_config.provider}")
    
    return provider_class(model_config)


# Default model configurations with pricing
# NOTE: Use real model names from provider documentation
DEFAULT_MODELS = [
    # OpenRouter models (real models that exist)
    ModelConfig(
        name="anthropic/claude-sonnet-4",
        provider=ProviderType.OPENROUTER,
        display_name="Claude Sonnet 4",
        input_price_per_million=3.0,
        output_price_per_million=15.0,
    ),
    ModelConfig(
        name="openai/gpt-4o-mini",
        provider=ProviderType.OPENROUTER,
        display_name="GPT-4o Mini",
        input_price_per_million=0.15,
        output_price_per_million=0.60,
    ),
    ModelConfig(
        name="google/gemini-2.0-flash-001",
        provider=ProviderType.OPENROUTER,
        display_name="Gemini 2.0 Flash",
        input_price_per_million=0.10,
        output_price_per_million=0.40,
    ),
    # Cerebras models (real models from Cerebras API)
    ModelConfig(
        name="llama3.1-8b",
        provider=ProviderType.CEREBRAS,
        display_name="Llama 3.1 8B (Cerebras)",
        input_price_per_million=0.0,
        output_price_per_million=0.0,
    ),
    ModelConfig(
        name="zai-glm-4.6",
        provider=ProviderType.CEREBRAS,
        display_name="GLM 4.6 (Cerebras)",
        input_price_per_million=0.0,
        output_price_per_million=0.0,
    ),
]
