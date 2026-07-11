"""Bulk content generation at scale.

Generates hundreds to thousands of SEO-optimized articles from a template + dataset.
Uses Claude batch API for cost efficiency + parallel processing.
Handles variable substitution, AI enhancement, and scheduling.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from app.agents.schema_agent import SchemaAgent
from app.clients.llm import llm_client

logger = logging.getLogger("omnirank.bulk_content")


@dataclass
class ContentTemplate:
    """Article template with {{variable}} placeholders."""
    name: str
    title_template: str
    slug_template: str
    meta_template: str
    h1_template: str
    body_template: str  # Markdown with {{variables}} and {{ai:prompt}}
    tags: list[str] = field(default_factory=list)


@dataclass
class ContentRow:
    """Single row from CSV — becomes one article."""
    data: dict[str, str]
    variables: list[str]
    ai_prompt: str | None = None  # {{ai:...}} content extracted


@dataclass
class GeneratedArticle:
    """Output: complete, ready-to-publish article."""
    slug: str
    title: str
    meta_description: str
    h1: str
    body: str  # Markdown
    word_count: int
    reading_time_minutes: int
    variables_used: dict[str, str]
    ai_enhanced: bool = False
    errors: list[str] = field(default_factory=list)


class BulkContentAgent:
    """Orchestrates bulk article generation."""

    def __init__(self):
        self.schema_agent = SchemaAgent()
        self.llm = llm_client

    def parse_template(self, template_str: str) -> ContentTemplate:
        """Parse YAML/JSON template definition."""
        try:
            config = json.loads(template_str)
            return ContentTemplate(**config)
        except Exception as exc:
            logger.error("Failed to parse template: %s", exc)
            raise

    def extract_variables(self, text: str) -> list[str]:
        """Find all {{variable}} placeholders."""
        import re
        return re.findall(r"\{\{(\w+)(?::[^}]*)?\}\}", text)

    def substitute_variables(self, text: str, data: dict[str, str]) -> str:
        """Replace {{variable}} with data values."""
        result = text
        for var, value in data.items():
            result = result.replace(f"{{{{{var}}}}}", value or "")
        return result

    def extract_ai_sections(self, body_template: str) -> dict[str, str]:
        """Extract {{ai:...}} sections for Claude processing."""
        import re
        ai_prompts = {}
        for match in re.finditer(r"\{\{ai:([^}]+)\}\}", body_template):
            key = f"ai_{len(ai_prompts)}"
            prompt = match.group(1)
            ai_prompts[key] = prompt
        return ai_prompts

    async def generate_article(
        self,
        template: ContentTemplate,
        row: ContentRow,
        enhance_with_ai: bool = True,
    ) -> GeneratedArticle:
        """Generate a single article from template + row data."""
        article = GeneratedArticle(
            slug="",
            title="",
            meta_description="",
            h1="",
            body="",
            word_count=0,
            reading_time_minutes=0,
            variables_used=row.data.copy(),
        )

        try:
            # Substitute base variables
            article.slug = self.substitute_variables(template.slug_template, row.data)
            article.title = self.substitute_variables(template.title_template, row.data)
            article.meta_description = self.substitute_variables(
                template.meta_template, row.data
            )
            article.h1 = self.substitute_variables(template.h1_template, row.data)
            body = self.substitute_variables(template.body_template, row.data)

            # AI enhancement of {{ai:...}} sections
            if enhance_with_ai and "{{ai:" in body:
                ai_sections = self.extract_ai_sections(template.body_template)
                for key, prompt in ai_sections.items():
                    # Substitute variables in the AI prompt
                    substituted_prompt = self.substitute_variables(prompt, row.data)
                    # Call Claude to generate the section
                    enhanced = await self._call_claude_for_section(substituted_prompt)
                    body = body.replace(f"{{{{ai:{prompt}}}}}", enhanced)
                    article.ai_enhanced = True

            article.body = body
            article.word_count = len(body.split())
            article.reading_time_minutes = max(1, article.word_count // 200)

        except Exception as exc:
            logger.error("Article generation error: %s", exc)
            article.errors.append(str(exc))

        return article

    async def _call_claude_for_section(self, prompt: str) -> str:
        """Call Claude API to generate a content section."""
        try:
            response = await self.llm.agenerate_text(
                prompt,
                model="claude-opus-4-8",
                max_tokens=1000,
            )
            return response.strip()
        except Exception as exc:
            logger.warning("Claude call failed for section: %s", exc)
            return f"[Failed to generate: {exc}]"

    async def generate_batch(
        self,
        template: ContentTemplate,
        rows: list[ContentRow],
        enhance_with_ai: bool = True,
        max_parallel: int = 10,
    ) -> list[GeneratedArticle]:
        """Generate multiple articles in parallel batches."""
        articles = []

        # Process in batches to respect rate limits
        for i in range(0, len(rows), max_parallel):
            batch = rows[i : i + max_parallel]
            import asyncio
            batch_results = await asyncio.gather(
                *[
                    self.generate_article(template, row, enhance_with_ai)
                    for row in batch
                ]
            )
            articles.extend(batch_results)
            logger.info("Processed batch: %d/%d articles", len(articles), len(rows))

        return articles

    def export_articles(
        self, articles: list[GeneratedArticle], format: str = "json"
    ) -> str:
        """Export generated articles in various formats."""
        if format == "json":
            return json.dumps(
                [
                    {
                        "slug": a.slug,
                        "title": a.title,
                        "meta_description": a.meta_description,
                        "h1": a.h1,
                        "body": a.body,
                        "word_count": a.word_count,
                        "reading_time_minutes": a.reading_time_minutes,
                        "variables": a.variables_used,
                        "ai_enhanced": a.ai_enhanced,
                        "errors": a.errors,
                    }
                    for a in articles
                ],
                indent=2,
            )
        elif format == "csv":
            import csv
            from io import StringIO

            output = StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "slug",
                    "title",
                    "meta_description",
                    "h1",
                    "word_count",
                    "reading_time_minutes",
                ],
            )
            writer.writeheader()
            for a in articles:
                writer.writerow(
                    {
                        "slug": a.slug,
                        "title": a.title,
                        "meta_description": a.meta_description,
                        "h1": a.h1,
                        "word_count": a.word_count,
                        "reading_time_minutes": a.reading_time_minutes,
                    }
                )
            return output.getvalue()
        elif format == "markdown":
            return "\n\n---\n\n".join(
                f"# {a.title}\n\n__{a.meta_description}__\n\n{a.body}"
                for a in articles
            )

        return ""
