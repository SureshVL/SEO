"""RAG (Retrieval-Augmented Generation) pipeline.

Stores SEO intelligence as embeddings in Supabase pgvector.
Retrieves relevant past analyses to improve future recommendations.

Over time, this creates a flywheel: every client run feeds data back
into the vector DB, making the system smarter for similar domains/niches.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("omnirank.rag")


class EmbeddingService:
    """Generate embeddings using Gemini's embedding model (free) or OpenAI."""

    def __init__(self):
        self.gemini_key = settings.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def embed(self, text: str) -> list[float] | None:
        """Generate 768-dim embedding via Gemini embedding model."""
        if not self.gemini_key:
            return None

        try:
            url = f"{self.base_url}/models/text-embedding-004:embedContent?key={self.gemini_key}"
            payload = {
                "model": "models/text-embedding-004",
                "content": {"parts": [{"text": text[:8000]}]},
            }
            with httpx.Client(timeout=15) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("embedding", {}).get("values", [])
        except Exception as exc:
            logger.warning("Embedding generation failed: %s", exc)
            return None


class RAGPipeline:
    """Store and retrieve SEO intelligence using pgvector."""

    def __init__(self):
        self.embedder = EmbeddingService()
        self.supabase_url = settings.supabase_url
        self.supabase_key = settings.supabase_service_role_key

        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase not configured — RAG disabled")

    @property
    def enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_key and self.embedder.gemini_key)

    def _headers(self) -> dict:
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

    def store_analysis(
        self,
        project_id: str,
        domain: str,
        keyword: str,
        analysis_type: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Store an SEO analysis with its embedding for future retrieval."""
        if not self.enabled:
            return False

        # Create embedding from the analysis content
        embed_text = f"Domain: {domain}. Keyword: {keyword}. Type: {analysis_type}. {content[:2000]}"
        embedding = self.embedder.embed(embed_text)
        if not embedding:
            return False

        payload = {
            "project_id": project_id if project_id else None,
            "source_url": domain,
            "scraped_content": content[:10000],
            "entity_maps": metadata or {},
            "backlink_profiles": {"keyword": keyword, "type": analysis_type},
            "embedding": embedding,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            base = self.supabase_url.rstrip("/") + "/rest/v1"
            with httpx.Client(timeout=15) as client:
                resp = client.post(
                    f"{base}/competitor_intel",
                    headers=self._headers(),
                    json=payload,
                )
                # Don't raise on error — just log
                if resp.status_code >= 400:
                    logger.warning("RAG store failed (%d): %s", resp.status_code, resp.text[:200])
                    return False
                return True
        except Exception as exc:
            logger.warning("RAG store error: %s", exc)
            return False

    def retrieve_similar(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> list[dict]:
        """Find similar past analyses using vector similarity search."""
        if not self.enabled:
            return []

        embedding = self.embedder.embed(query)
        if not embedding:
            return []

        # Use Supabase RPC for vector similarity search
        try:
            base = self.supabase_url.rstrip("/") + "/rest/v1"
            # Use the pgvector <=> operator via RPC
            rpc_payload = {
                "query_embedding": embedding,
                "match_threshold": similarity_threshold,
                "match_count": limit,
            }

            with httpx.Client(timeout=15) as client:
                resp = client.post(
                    f"{base}/rpc/match_competitor_intel",
                    headers=self._headers(),
                    json=rpc_payload,
                )
                if resp.status_code == 200:
                    return resp.json()
                # If RPC doesn't exist yet, fall back to basic text search
                logger.info("Vector search RPC not available, using text fallback")
                return []
        except Exception as exc:
            logger.warning("RAG retrieve error: %s", exc)
            return []

    def enrich_prompt_with_history(
        self,
        domain: str,
        keyword: str,
        base_prompt: str,
    ) -> str:
        """Add relevant historical context to an AI prompt."""
        query = f"SEO analysis for {domain} targeting {keyword}"
        past = self.retrieve_similar(query, limit=3)

        if not past:
            return base_prompt

        history_block = "\n\n--- RELEVANT PAST ANALYSES ---\n"
        for i, item in enumerate(past):
            content = item.get("scraped_content", "")[:500]
            meta = item.get("entity_maps", {})
            history_block += f"\nPast analysis {i+1}: {content}\nMetadata: {json.dumps(meta)[:200]}\n"

        return base_prompt + history_block


# ── Supabase migration for vector search RPC ──
# Run this in Supabase SQL Editor to enable vector similarity search:
VECTOR_SEARCH_MIGRATION = """
CREATE OR REPLACE FUNCTION match_competitor_intel(
    query_embedding vector(768),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id uuid,
    project_id uuid,
    source_url text,
    scraped_content text,
    entity_maps jsonb,
    backlink_profiles jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ci.id,
        ci.project_id,
        ci.source_url,
        ci.scraped_content,
        ci.entity_maps,
        ci.backlink_profiles,
        1 - (ci.embedding <=> query_embedding) AS similarity
    FROM public.competitor_intel ci
    WHERE ci.embedding IS NOT NULL
    AND 1 - (ci.embedding <=> query_embedding) > match_threshold
    ORDER BY ci.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""
