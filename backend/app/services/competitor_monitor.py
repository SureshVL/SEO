"""Competitor monitoring service.

Tracks changes in competitor pages: content updates, new entities,
ranking shifts, and generates alerts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.clients.claude_client import AIUsageAccumulator
from app.clients.http_clients import FirecrawlHTTPClient
from app.services.cache import cache_key, cache_json_get, cache_json_set

logger = logging.getLogger("omnirank.competitor")


@dataclass
class CompetitorChange:
    url: str
    change_type: str  # content_update, new_sections, entity_shift, ranking_change
    severity: str  # high, medium, low
    description: str
    detected_at: str = ""

    def __post_init__(self):
        if not self.detected_at:
            self.detected_at = datetime.now(timezone.utc).isoformat()


@dataclass
class CompetitorSnapshot:
    url: str
    word_count: int
    h2_count: int
    entity_count: int
    question_count: int
    content_hash: str
    scraped_at: str = ""

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now(timezone.utc).isoformat()


class CompetitorMonitor:
    """Monitor competitor pages for changes and generate alerts."""

    def __init__(
        self,
        firecrawl_client: FirecrawlHTTPClient,
        claude_client: ClaudeClient | None = None,
    ):
        self.firecrawl = firecrawl_client
        self.claude = claude_client
        self.usage = AIUsageAccumulator()

    def check_competitor(
        self,
        url: str,
        previous_snapshot: CompetitorSnapshot | None = None,
    ) -> tuple[CompetitorSnapshot, list[CompetitorChange]]:
        """Scrape a competitor page and detect changes from previous snapshot."""
        import hashlib
        import re
        from collections import Counter

        markdown = self.firecrawl.scrape_markdown(url)
        lines = [l.strip() for l in markdown.splitlines() if l.strip()]

        # Extract signals
        h2s = [l.replace("## ", "").strip() for l in lines if l.startswith("## ")]
        full_text = " ".join(lines)
        words = re.findall(r"[A-Za-z][A-Za-z\-']+", full_text.lower())
        entity_matches = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z0-9&]+)+)\b", markdown)
        entities = list({e for e in entity_matches})
        questions = [l for l in lines if l.endswith("?")]

        content_hash = hashlib.md5(markdown[:5000].encode()).hexdigest()

        snapshot = CompetitorSnapshot(
            url=url,
            word_count=len(words),
            h2_count=len(h2s),
            entity_count=len(entities),
            question_count=len(questions),
            content_hash=content_hash,
        )

        changes: list[CompetitorChange] = []

        if previous_snapshot:
            # Detect content changes
            if content_hash != previous_snapshot.content_hash:
                word_diff = snapshot.word_count - previous_snapshot.word_count
                if abs(word_diff) > 200:
                    changes.append(CompetitorChange(
                        url=url,
                        change_type="content_update",
                        severity="high" if abs(word_diff) > 500 else "medium",
                        description=f"Content {'expanded' if word_diff > 0 else 'reduced'} by ~{abs(word_diff)} words",
                    ))

                h2_diff = snapshot.h2_count - previous_snapshot.h2_count
                if h2_diff > 0:
                    changes.append(CompetitorChange(
                        url=url,
                        change_type="new_sections",
                        severity="medium",
                        description=f"Added {h2_diff} new section(s)",
                    ))

                entity_diff = snapshot.entity_count - previous_snapshot.entity_count
                if entity_diff > 3:
                    changes.append(CompetitorChange(
                        url=url,
                        change_type="entity_shift",
                        severity="medium",
                        description=f"Added {entity_diff} new entities — may be targeting new topics",
                    ))

            if not changes and content_hash != previous_snapshot.content_hash:
                changes.append(CompetitorChange(
                    url=url,
                    change_type="content_update",
                    severity="low",
                    description="Minor content update detected",
                ))

        return snapshot, changes

    def analyze_changes_with_ai(
        self,
        changes: list[CompetitorChange],
        keyword: str,
    ) -> str:
        """Use Claude to summarize what competitor changes mean for your strategy."""
        if not self.claude or not changes:
            return ""

        changes_text = "\n".join(
            f"- [{c.severity.upper()}] {c.url}: {c.description}" for c in changes
        )

        resp = self.claude.complete(
            messages=[{"role": "user", "content": f"""Target keyword: "{keyword}"

Recent competitor changes:
{changes_text}

In 2-3 sentences, explain what these changes mean for our SEO strategy
and what action we should take."""}],
            system="You are a concise SEO strategist. Analyze competitor changes and recommend action.",
            model=HAIKU,
            max_tokens=300,
            temperature=0.3,
        )
        self.usage.record(resp)
        return resp.content
