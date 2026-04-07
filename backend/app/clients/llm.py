# backend/app/clients/llm.py
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any, List
import os
from functools import lru_cache

class LLMSettings(BaseSettings):
    llm_provider: str = "auto"   # auto, claude, gemini, groq, openai, perplexity

    # API Keys
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    perplexity_api_key: Optional[str] = None

    # Default Models
    default_claude_model: str = "claude-3-5-sonnet-20241022"
    default_gemini_model: str = "gemini-2.0-flash"
    default_groq_model: str = "llama-3.3-70b-versatile"
    default_openai_model: str = "gpt-4o"
    default_perplexity_model: str = "sonar-pro"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = "ignore"


settings = LLMSettings()


class LLMClient:
    """Unified LLM Client with multiple providers"""
    
    def __init__(self):
        self.provider = self._determine_provider()

    def _determine_provider(self) -> str:
        if settings.llm_provider != "auto":
            return settings.llm_provider.lower()

        # Auto fallback order: Best quality → Fast/Cheap
        if settings.anthropic_api_key:
            return "claude"
        elif settings.gemini_api_key:
            return "gemini"
        elif settings.groq_api_key:
            return "groq"
        elif settings.openai_api_key:
            return "openai"
        elif settings.perplexity_api_key:
            return "perplexity"
        return "none"

    def complete(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        provider = kwargs.pop("provider", self.provider)
        model = kwargs.pop("model", None)
        temperature = kwargs.pop("temperature", 0.7)
        max_tokens = kwargs.pop("max_tokens", 4000)

        if provider == "claude" and settings.anthropic_api_key:
            from .claude_client import ClaudeClient
            client = ClaudeClient()
            return client.complete(messages, model or settings.default_claude_model, 
                                 temperature=temperature, max_tokens=max_tokens, **kwargs)

        elif provider == "gemini" and settings.gemini_api_key:
            from .gemini_client import GeminiClient
            client = GeminiClient()
            return client.complete(messages, model or settings.default_gemini_model, 
                                 temperature=temperature, max_tokens=max_tokens, **kwargs)

        elif provider == "groq" and settings.groq_api_key:
            from .groq_client import GroqClient
            client = GroqClient()
            return client.complete(messages, model or settings.default_groq_model, 
                                 temperature=temperature, max_tokens=max_tokens, **kwargs)

        elif provider == "openai" and settings.openai_api_key:
            from .openai_client import OpenAIClient
            client = OpenAIClient()
            return client.complete(messages, model or settings.default_openai_model, 
                                 temperature=temperature, max_tokens=max_tokens, **kwargs)

        elif provider == "perplexity" and settings.perplexity_api_key:
            from .perplexity_client import PerplexityClient
            client = PerplexityClient()
            return client.complete(messages, model or settings.default_perplexity_model, 
                                 temperature=temperature, max_tokens=max_tokens, **kwargs)

        else:
            raise Exception(f"No LLM provider available. Please set at least one API key in .env. Requested: {provider}")

    def is_enabled(self) -> bool:
        return self.provider != "none"


# Global singleton
llm_client = LLMClient()