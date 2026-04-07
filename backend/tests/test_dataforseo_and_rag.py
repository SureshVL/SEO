"""Tests for DataForSEO client and RAG pipeline."""

from app.clients.dataforseo_client import (
    BacklinkProfile, CompetitorDomain, DataForSEOClient, KeywordMetrics,
)
from app.services.rag import EmbeddingService, RAGPipeline


def test_backlink_profile_dataclass():
    p = BacklinkProfile(total_backlinks=100, referring_domains=50, domain_rank=45.2)
    assert p.total_backlinks == 100
    assert p.referring_domains == 50
    assert p.dofollow_ratio == 0


def test_keyword_metrics_dataclass():
    m = KeywordMetrics(keyword="seo tools", search_volume=5400, cpc=2.5, difficulty=65)
    assert m.keyword == "seo tools"
    assert m.search_volume == 5400
    assert m.intent == ""


def test_competitor_domain_dataclass():
    c = CompetitorDomain(domain="competitor.com", common_keywords=150, total_traffic=10000)
    assert c.domain == "competitor.com"
    assert c.overlap_percentage == 0


def test_dataforseo_client_disabled_without_creds():
    client = DataForSEOClient(login="", password="")
    assert not client.enabled


def test_dataforseo_cost_tracking():
    client = DataForSEOClient(login="", password="")
    summary = client.get_cost_summary()
    assert summary["total_cost_usd"] == 0
    assert summary["total_requests"] == 0


def test_rag_pipeline_disabled_without_config():
    pipeline = RAGPipeline()
    assert not pipeline.enabled


def test_rag_retrieve_returns_empty_without_config():
    pipeline = RAGPipeline()
    results = pipeline.retrieve_similar("test query")
    assert results == []


def test_rag_store_returns_false_without_config():
    pipeline = RAGPipeline()
    result = pipeline.store_analysis("proj1", "example.com", "seo", "research", "content")
    assert result is False


def test_rag_enrich_returns_original_without_history():
    pipeline = RAGPipeline()
    prompt = "Analyze this website"
    enriched = pipeline.enrich_prompt_with_history("example.com", "seo", prompt)
    assert enriched == prompt  # No history = unchanged
