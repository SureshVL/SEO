"""Tests for content brief generation and SERP-relative content scoring."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.content_agent import (
    CompetitorSummary,
    ContentAgent,
    ContentBrief,
    ContentScore,
)


# ── Sample data ───────────────────────────────────────────────────────────────

COMPETITOR_A_MD = """# Best SEO tools in 2026

## What is an SEO tool?
An SEO tool helps marketers audit, optimize, and rank content.

## Top 10 SEO tools compared
- Ahrefs
- Semrush
- Moz

## How to choose an SEO tool
Look at budget, team size, data coverage, and integrations.

## FAQ
### Is Ahrefs better than Semrush?
Both have strengths.
"""

COMPETITOR_B_MD = """# The ultimate SEO tools guide

## Overview
A deep guide.

## Top 10 SEO tools compared
Some comparisons.

## Pricing and plans
Numbers.

## How to choose an SEO tool
Match to needs.
"""

DRAFT_GOOD = """# Best SEO tools guide

Looking for the best seo tools? Here is a complete rundown with pricing,
comparisons, and recommendations.

## What is an SEO tool?
An SEO tool helps marketers with research, rank tracking, and audits.

## Top 10 SEO tools compared
Ahrefs, Semrush, Moz, and more.

## How to choose an SEO tool
Budget, team, integrations.

## Pricing and plans
Details on costs.

## FAQ
### Is Ahrefs better than Semrush?
Depends on your use case.
""" + ("The best seo tools space keeps growing. " * 60)

DRAFT_THIN = "# SEO tools\n\nQuick blurb about tools."


# ── Helpers ───────────────────────────────────────────────────────────────────

class TestAgentHelpers:
    def test_extract_headings(self):
        out = ContentAgent._extract_headings(COMPETITOR_A_MD)
        assert "Best SEO tools in 2026" in out
        assert "What is an SEO tool?" in out
        assert "Top 10 SEO tools compared" in out
        # FAQ H3 also captured
        assert "Is Ahrefs better than Semrush?" in out

    def test_extract_headings_empty(self):
        assert ContentAgent._extract_headings("") == []
        assert ContentAgent._extract_headings("no headings here") == []

    def test_word_count(self):
        assert ContentAgent._word_count("one two three") == 3
        assert ContentAgent._word_count("") == 0
        # punctuation doesn't add to count
        assert ContentAgent._word_count("hi, there!") == 2

    def test_slugify(self):
        assert ContentAgent._slugify("Best SEO Tools Guide") == "best-seo-tools-guide"


# ── Length scoring ────────────────────────────────────────────────────────────

class TestLengthScore:
    def test_full_credit_at_median(self):
        assert ContentAgent._length_score(1500, 1500) == 20.0

    def test_full_credit_above_median(self):
        assert ContentAgent._length_score(2500, 1500) == 20.0

    def test_zero_at_quarter_median(self):
        assert ContentAgent._length_score(375, 1500) == 0.0

    def test_scales_linearly(self):
        # at 0.625 ratio: (0.625 - 0.25) / 0.75 * 20 = 10
        assert ContentAgent._length_score(937, 1500) == pytest.approx(10.0, abs=0.2)

    def test_zero_median_uses_threshold(self):
        assert ContentAgent._length_score(400, 0) == 20.0
        assert ContentAgent._length_score(100, 0) == 0.0


# ── Heading / entity / question scoring ───────────────────────────────────────

class TestCoverageScoring:
    def test_heading_score_all_covered(self):
        score, missing = ContentAgent._heading_score(
            ["Top 10 Tools", "How to Choose"],
            ["top 10 tools compared", "how to choose an seo tool"],
        )
        assert score == 25.0
        assert missing == []

    def test_heading_score_partial(self):
        score, missing = ContentAgent._heading_score(
            ["Top 10 Tools", "Pricing Plans", "Migration Guide"],
            ["top 10 tools compared"],
        )
        # 1 of 3 covered → 25/3
        assert score == pytest.approx(25 / 3, abs=0.2)
        assert "Pricing Plans" in missing
        assert "Migration Guide" in missing

    def test_heading_score_no_recommended(self):
        assert ContentAgent._heading_score([], ["anything"]) == (25.0, [])

    def test_entity_score_all_present(self):
        score, missing = ContentAgent._entity_score(
            ["ahrefs", "semrush"], "we compared ahrefs and semrush side by side",
        )
        assert score == 25.0
        assert missing == []

    def test_entity_score_partial(self):
        score, missing = ContentAgent._entity_score(
            ["ahrefs", "semrush", "moz", "ubersuggest"],
            "we compared ahrefs and semrush",
        )
        # 2 of 4 → 12.5
        assert score == 12.5
        assert "moz" in missing
        assert "ubersuggest" in missing

    def test_question_score_answered_when_words_present(self):
        score, missing = ContentAgent._question_score(
            ["What is an SEO tool?"],
            "our seo tool guide covers what these tools can do",
        )
        # words: what, seo, tool → all 3 present → covered
        assert score == 15.0
        assert missing == []

    def test_question_score_marks_missing_when_words_absent(self):
        score, missing = ContentAgent._question_score(
            ["How do you integrate Salesforce with HubSpot?"],
            "a totally unrelated page about cooking",
        )
        assert score == 0.0
        assert missing == ["How do you integrate Salesforce with HubSpot?"]


# ── Keyword usage ─────────────────────────────────────────────────────────────

class TestKeywordUsage:
    def test_full_credit_when_everywhere(self):
        md = "# Best SEO Tools\n\nIntro to best seo tools. " + ("More best seo tools. " * 10)
        score = ContentAgent._keyword_usage_score(
            "best seo tools", md, "https://x.com/best-seo-tools",
        )
        assert score == 15.0

    def test_no_credit_when_missing(self):
        md = "# Nothing\n\nTotally off topic article."
        score = ContentAgent._keyword_usage_score("widgets", md, "https://x.com/other")
        assert score == 0.0

    def test_empty_markdown(self):
        assert ContentAgent._keyword_usage_score("any", "", "https://x.com") == 0.0


# ── Brief generation ──────────────────────────────────────────────────────────

class TestGenerateBrief:
    def _build_agent(self, ai=False) -> ContentAgent:
        dfs = MagicMock()
        dfs.serp_competitors.return_value = [
            {"url": "https://a.com/x", "title": "A guide", "position": 1},
            {"url": "https://b.com/y", "title": "B guide", "position": 2},
        ]
        dfs.ai_overview_for_keyword.return_value = {
            "present": True, "snippet": "Short AI answer.",
            "citations": [], "domain_cited": False, "domain_position": None,
        }
        firecrawl = MagicMock()
        firecrawl.scrape_markdown.side_effect = [COMPETITOR_A_MD, COMPETITOR_B_MD]
        claude = None
        if ai:
            claude = MagicMock()
            claude.complete_json.return_value = (
                {
                    "recommended_headings": ["What is an SEO tool", "Top 10 tools", "Pricing"],
                    "must_cover_entities": ["Ahrefs", "Semrush", "Moz"],
                    "questions_to_answer": ["Which SEO tool is best?"],
                    "meta_title_suggestion": "Best SEO tools — Complete 2026 guide",
                    "meta_description_suggestion": "Compare the best SEO tools for 2026.",
                    "internal_links": [
                        {"anchor": "keyword research", "path": "/blog/keyword-research"},
                    ],
                },
                MagicMock(content="", model="", input_tokens=10, output_tokens=10,
                         cost_usd=0.0, cached=False, latency_ms=0),
            )
        return ContentAgent(
            claude_client=claude, dataforseo_client=dfs, firecrawl_client=firecrawl,
        )

    def test_deterministic_brief_without_claude(self):
        agent = self._build_agent(ai=False)
        brief = agent.generate_brief("best seo tools", scrape_top_n=2)

        assert brief.keyword == "best seo tools"
        assert len(brief.competitors) == 2
        assert brief.competitors[0].word_count > 0
        # Headings most common across competitors should be top of recommended
        assert any("top 10 seo tools" in h.lower() for h in brief.recommended_headings)
        # AI overview populated from dfs stub
        assert brief.ai_overview_present is True
        assert brief.ai_overview_snippet == "Short AI answer."
        # Target word count = max(median, 800)
        assert brief.target_word_count >= 800
        assert brief.ai_generated is False

    def test_ai_enriched_brief_uses_claude_output(self):
        agent = self._build_agent(ai=True)
        brief = agent.generate_brief("best seo tools", scrape_top_n=2)

        assert brief.ai_generated is True
        assert "Top 10 tools" in brief.recommended_headings
        # Entities lowercased
        assert "ahrefs" in brief.must_cover_entities
        assert brief.meta_title_suggestion.startswith("Best SEO tools")
        assert brief.internal_links[0]["anchor"] == "keyword research"

    def test_brief_survives_firecrawl_failure(self):
        agent = self._build_agent(ai=False)
        agent.firecrawl.scrape_markdown.side_effect = Exception("network down")
        brief = agent.generate_brief("any keyword", scrape_top_n=2)
        # Competitors still listed (from SERP) but no headings
        assert len(brief.competitors) == 2
        assert all(c.word_count == 0 for c in brief.competitors)
        # Falls back to default target when no word counts available
        assert brief.target_word_count == 1500

    def test_brief_without_dataforseo_returns_empty_competitors(self):
        agent = ContentAgent()
        brief = agent.generate_brief("any")
        assert brief.competitors == []
        assert brief.serp_median_words == 1500


# ── Scoring end-to-end ────────────────────────────────────────────────────────

class TestScoreContent:
    def _brief(self) -> ContentBrief:
        return ContentBrief(
            keyword="best seo tools",
            target_word_count=1500,
            serp_median_words=1500,
            recommended_headings=[
                "What is an SEO tool",
                "Top 10 tools compared",
                "How to choose an SEO tool",
                "Pricing and plans",
            ],
            must_cover_entities=["ahrefs", "semrush", "moz"],
            questions_to_answer=["Is Ahrefs better than Semrush?"],
        )

    def test_good_draft_scores_high(self):
        agent = ContentAgent()
        score = agent.score_content(
            keyword="best seo tools",
            markdown=DRAFT_GOOD,
            brief=self._brief(),
        )
        assert isinstance(score, ContentScore)
        assert score.total >= 70
        assert score.length_score > 0
        assert score.heading_score >= 20  # most headings covered
        assert score.keyword_usage_score >= 9

    def test_thin_draft_scores_low(self):
        agent = ContentAgent()
        score = agent.score_content(
            keyword="best seo tools",
            markdown=DRAFT_THIN,
            brief=self._brief(),
        )
        assert score.total < 40
        assert score.length_score < 10
        # thin draft missing most of the recommended headings
        assert len(score.missing_headings) >= 3
        assert len(score.recommendations) > 0

    def test_score_fetches_url_when_markdown_absent(self):
        agent = ContentAgent(firecrawl_client=MagicMock())
        agent.firecrawl.scrape_markdown.return_value = DRAFT_GOOD
        score = agent.score_content(
            keyword="best seo tools",
            url="https://yoursite.com/post",
            brief=self._brief(),
        )
        agent.firecrawl.scrape_markdown.assert_called_once_with(
            "https://yoursite.com/post",
        )
        assert score.word_count > 100

    def test_score_generates_brief_if_none_provided(self):
        agent = ContentAgent()
        with patch.object(agent, "generate_brief") as mock_brief:
            mock_brief.return_value = self._brief()
            agent.score_content(keyword="kw", markdown=DRAFT_THIN)
            mock_brief.assert_called_once_with("kw")

    def test_recommendations_include_actionable_items(self):
        agent = ContentAgent()
        score = agent.score_content(
            keyword="best seo tools",
            markdown=DRAFT_THIN,
            brief=self._brief(),
        )
        assert any("Expand content" in r for r in score.recommendations)


# ── Route integration ─────────────────────────────────────────────────────────

class TestContentRoutes:
    @pytest.fixture
    def client(self, monkeypatch):
        from app import main
        monkeypatch.setattr(main.settings, "orchestrator_api_key", "test-key", raising=False)
        return TestClient(main.app)

    def test_brief_route_returns_serialized_brief(self, client, monkeypatch):
        from app import main

        fake_brief = ContentBrief(
            keyword="best seo tools",
            target_word_count=2000,
            serp_median_words=1800,
            competitors=[
                CompetitorSummary(
                    url="https://a.com", title="A", word_count=1800,
                    headings=["Intro", "Top 10"], position=1,
                ),
            ],
            recommended_headings=["Top 10 tools"],
            must_cover_entities=["ahrefs"],
            questions_to_answer=["Is Ahrefs better?"],
            meta_title_suggestion="Best SEO tools",
            meta_description_suggestion="Compare.",
            ai_overview_present=True,
            ai_overview_snippet="Short",
            ai_generated=True,
        )
        fake_agent = MagicMock()
        fake_agent.generate_brief.return_value = fake_brief
        monkeypatch.setattr(main, "_build_content_agent", lambda: fake_agent)

        r = client.post(
            "/content/brief",
            json={"keyword": "best seo tools", "domain": "example.com"},
            headers={"X-API-KEY": "test-key"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["keyword"] == "best seo tools"
        assert body["target_word_count"] == 2000
        assert body["competitors"][0]["url"] == "https://a.com"
        assert body["ai_overview_present"] is True

    def test_score_route_rejects_missing_content(self, client, monkeypatch):
        from app import main
        monkeypatch.setattr(main, "_build_content_agent", lambda: MagicMock())
        r = client.post(
            "/content/score",
            json={"keyword": "x"},
            headers={"X-API-KEY": "test-key"},
        )
        assert r.status_code == 400

    def test_score_route_with_inline_brief_and_markdown(self, client, monkeypatch):
        from app import main
        fake_score = ContentScore(
            keyword="x", total=75.5, word_count=1500, serp_median_words=1500,
            length_score=20.0, heading_score=20.0, entity_score=20.0,
            question_score=10.5, keyword_usage_score=5.0,
            recommendations=["add a FAQ"],
        )
        fake_agent = MagicMock()
        fake_agent.score_content.return_value = fake_score
        monkeypatch.setattr(main, "_build_content_agent", lambda: fake_agent)

        payload = {
            "keyword": "x",
            "markdown": "# test\n\nbody",
            "brief": {
                "keyword": "x",
                "target_word_count": 1500,
                "serp_median_words": 1500,
                "competitors": [],
                "recommended_headings": [],
                "must_cover_entities": [],
                "questions_to_answer": [],
            },
        }
        r = client.post(
            "/content/score",
            json=payload,
            headers={"X-API-KEY": "test-key"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 75.5
        assert body["breakdown"]["length"] == 20.0
        assert body["recommendations"] == ["add a FAQ"]

    def test_brief_route_requires_auth(self, client):
        r = client.post(
            "/content/brief",
            json={"keyword": "x"},
        )
        assert r.status_code in (401, 403)
