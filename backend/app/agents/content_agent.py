"""AI-Powered Content Generation Agent.

Uses Claude to generate real, optimized SEO content from research gaps
instead of returning template strings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.clients.claude_client import HAIKU, SONNET, AIUsageAccumulator, ClaudeClient
from app.schemas.research import ResearchResponse

logger = logging.getLogger("omnirank.content")


@dataclass
class ContentDraft:
    title: str
    slug: str
    body_markdown: str
    target_keyword: str
    meta_description: str = ""
    estimated_word_count: int = 0


class ContentAgent:
    """Generate production-ready SEO content drafts using Claude."""

    def __init__(self, claude_client: ClaudeClient | None = None):
        self.claude = claude_client
        self.usage = AIUsageAccumulator()

    def generate(self, research: ResearchResponse, primary_keyword: str) -> list[ContentDraft]:
        if self.claude:
            return self._ai_generate(research, primary_keyword)
        return self._fallback_generate(research, primary_keyword)

    def _ai_generate(self, research: ResearchResponse, keyword: str) -> list[ContentDraft]:
        assert self.claude is not None

        missing_q = research.gap_analysis.missing_questions[:6]
        missing_e = research.gap_analysis.missing_entities[:10]
        heading_gaps = research.gap_analysis.heading_gaps[:8]
        avg_words = int(research.raw_metrics.get("avg_competitor_word_count", 1500))

        system = """You are an expert SEO content writer. Generate a comprehensive, 
well-structured article optimized for the target keyword. The content must:

1. Be genuinely useful and informative (not keyword-stuffed)
2. Include all required entities naturally woven into the content
3. Answer the provided questions in dedicated FAQ sections
4. Use proper heading hierarchy (H2, H3)
5. Include a meta description (150-160 chars)
6. Target the specified word count
7. Use a conversational but authoritative tone
8. Include internal linking suggestions as [INTERNAL_LINK: anchor text -> /suggested-path]
9. Include schema markup suggestions as comments

Respond ONLY with valid JSON:
{
  "title": "<SEO-optimized title with keyword>",
  "slug": "<url-friendly-slug>",
  "meta_description": "<150-160 char meta description>",
  "body_markdown": "<full article in markdown>",
  "word_count": <estimated word count>
}"""

        user_msg = f"""Target keyword: "{keyword}"
Target word count: {max(avg_words, 1200)} words minimum

ENTITIES TO INCLUDE NATURALLY:
{', '.join(missing_e) if missing_e else 'No specific entities required'}

QUESTIONS TO ANSWER (include as FAQ or inline):
{chr(10).join(f'- {q}' for q in missing_q) if missing_q else 'No specific questions'}

HEADING GAPS TO COVER:
{chr(10).join(f'- {h}' for h in heading_gaps) if heading_gaps else 'No specific headings required'}

COMPETITOR CONTEXT:
- Average competitor word count: {avg_words}
- Client current word count: {research.client_profile.word_count}
- Keyword density gap: {research.gap_analysis.density_gap}%

Write a complete, publication-ready article."""

        parsed, resp = self.claude.complete_json(
            messages=[{"role": "user", "content": user_msg}],
            system=system,
            model=SONNET,
            max_tokens=8192,
            temperature=0.4,
            use_cache=False,  # Content should always be fresh
        )
        self.usage.record(resp)

        draft = ContentDraft(
            title=parsed.get("title", f"{keyword.title()} — Complete Guide"),
            slug=parsed.get("slug", self._slugify(keyword + " guide")),
            body_markdown=parsed.get("body_markdown", "Content generation failed."),
            target_keyword=keyword,
            meta_description=parsed.get("meta_description", ""),
            estimated_word_count=parsed.get("word_count", 0),
        )

        return [draft]

    def generate_meta(self, page_content: str, keyword: str) -> dict[str, str]:
        """Generate optimized meta title and description for existing content."""
        if not self.claude:
            return {
                "title": f"{keyword.title()} | OMNI-RANK",
                "description": f"Learn about {keyword} with our comprehensive guide.",
            }

        system = """Generate an SEO-optimized meta title (50-60 chars) and meta description 
(150-160 chars) for this page content. Include the target keyword naturally.
Respond ONLY with JSON: {"title": "...", "description": "..."}"""

        parsed, resp = self.claude.complete_json(
            messages=[{"role": "user", "content": f"Keyword: {keyword}\n\nContent:\n{page_content[:2000]}"}],
            system=system,
            model=HAIKU,
            max_tokens=256,
        )
        self.usage.record(resp)
        return {"title": parsed.get("title", ""), "description": parsed.get("description", "")}

    def rewrite_section(self, content: str, keyword: str, instruction: str) -> str:
        """AI-powered section rewrite with specific instructions."""
        if not self.claude:
            return content

        resp = self.claude.complete(
            messages=[{"role": "user", "content": f"""Rewrite this content section.
Keyword: "{keyword}"
Instruction: {instruction}

Original content:
{content}

Write the improved version only, no preamble."""}],
            system="You are an expert SEO content editor. Rewrite content to be more engaging, better optimized, and higher quality.",
            model=SONNET,
            max_tokens=4096,
            temperature=0.3,
        )
        self.usage.record(resp)
        return resp.content

    def _fallback_generate(self, research: ResearchResponse, keyword: str) -> list[ContentDraft]:
        """Deterministic fallback when Claude is unavailable."""
        missing_q = research.gap_analysis.missing_questions[:3]
        missing_e = research.gap_analysis.missing_entities[:6]
        faq = "\n".join([f"### {q}\n- Direct answer in 40-55 words." for q in missing_q])
        if not faq:
            faq = "### What should this page answer?\n- Add high-intent user questions."
        entity_block = ", ".join(missing_e) if missing_e else "No additional entities"

        return [ContentDraft(
            title=f"{keyword.title()} — Complete Guide",
            slug=self._slugify(keyword + " guide"),
            target_keyword=keyword,
            body_markdown=(
                f"## Featured Snippet Summary\n{keyword} overview.\n\n"
                f"## Entity Coverage\n{entity_block}\n\n"
                f"## FAQ\n{faq}"
            ),
        )]

    @staticmethod
    def _slugify(text: str) -> str:
        return "-".join(p for p in text.lower().replace("_", " ").split() if p)
