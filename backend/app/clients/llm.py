"""Unified LLM provider.

Switch between Claude and Gemini via LLM_PROVIDER env var.
Both clients expose the same interface: complete(), complete_json(), route_model().

Usage:
    from app.clients.llm import get_llm_client
    client = get_llm_client()  # returns ClaudeClient or GeminiClient
    resp = client.complete(messages=[...], system="...")
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger("omnirank.llm")


def get_llm_client():
    """Get the configured LLM client based on LLM_PROVIDER env var.

    Priority:
    1. If LLM_PROVIDER=gemini and GEMINI_API_KEY is set → GeminiClient
    2. If LLM_PROVIDER=claude and ANTHROPIC_API_KEY is set → ClaudeClient
    3. If neither specified, try Claude first, then Gemini
    4. Returns None if no API keys configured
    """
    provider = settings.llm_provider.lower()

    if provider == "gemini":
        if settings.gemini_api_key:
            from app.clients.gemini_client import GeminiClient
            logger.info("Using Gemini as LLM provider")
            return GeminiClient(api_key=settings.gemini_api_key)
        logger.warning("LLM_PROVIDER=gemini but GEMINI_API_KEY not set")

    if provider == "claude":
        if settings.anthropic_api_key:
            from app.clients.claude_client import ClaudeClient
            logger.info("Using Claude as LLM provider")
            return ClaudeClient(api_key=settings.anthropic_api_key)
        logger.warning("LLM_PROVIDER=claude but ANTHROPIC_API_KEY not set")

    # Auto-detect: try Claude first (better quality), then Gemini (free)
    if provider == "auto" or provider not in ("claude", "gemini"):
        if settings.anthropic_api_key:
            from app.clients.claude_client import ClaudeClient
            logger.info("Auto-detected Claude as LLM provider")
            return ClaudeClient(api_key=settings.anthropic_api_key)
        if settings.gemini_api_key:
            from app.clients.gemini_client import GeminiClient
            logger.info("Auto-detected Gemini as LLM provider (free tier)")
            return GeminiClient(api_key=settings.gemini_api_key)

    logger.warning("No LLM API key configured — AI features disabled")
    return None
