"""AI-Powered Content Generation Agent.

Generates SEO drafts, SERP-driven content briefs, and scores existing
content against the SERP competitive landscape.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from statistics import median
from typing import Any

from app.clients.claude_client import (
    HAIKU,
    SONNET,
    AIUsageAccumulator,
    ClaudeClient,
)
from app.schemas.research import ResearchResponse

logger = logging.getLogger("omnirank.content")


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class ContentDraft:
    title: str
    slug: str
    body_markdown: str
    target_keyword: str
    meta_description: str = ""
    estimated_word_count: int = 0


@dataclass
class CompetitorSummary:
    url: str
    title: str
    word_count: int
    headings: list[str] = field(default_factory=list)
    position: int | None = None


@dataclass
class ContentBrief:
    keyword: str
    target_word_count: int
    serp_median_words: int
    competitors: list[CompetitorSummary] = field(default_factory=list)
    recommended_headings: list[str] = field(default_factory=list)
    must_cover_entities: list[str] = field(default_factory=list)
    questions_to_answer: list[str] = field(default_factory=list)
    meta_title_suggestion: str = ""
    meta_description_suggestion: str = ""
    internal_links: list[dict[str, str]] = field(default_factory=list)
    ai_overview_present: bool = False
    ai_overview_snippet: str = ""
    ai_generated: bool = False


@dataclass
class ContentScore:
    keyword: str
    total: float
    word_count: int
    serp_median_words: int
    length_score: float
    heading_score: float
    entity_score: float
    question_score: float
    keyword_usage_score: float
    missing_headings: list[str] = field(default_factory=list)
    missing_entities: list[str] = field(default_factory=list)
    missing_questions: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ── Agent ─────────────────────────────────────────────────────────────────────

HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)
WORD_RE = re.compile(r"\b[\w'-]+\b")


class ContentAgent:
    """Generate production-ready SEO content drafts, briefs, and scores."""

    def __init__(
        self,
        claude_client: ClaudeClient | None = None,
        dataforseo_client=None,
        firecrawl_client=None,
    ):
        self.claude = claude_client
        self.dfs = dataforseo_client
        self.firecrawl = firecrawl_client
        self.usage = AIUsageAccumulator()

    # ── Draft generation (existing) ───────────────────────────────────────────

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
            use_cache=False,
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

    # ── Brief generation ──────────────────────────────────────────────────────

    def generate_brief(
        self,
        keyword: str,
        location_code: int = 2356,
        language_code: str = "en",
        scrape_top_n: int = 5,
        domain: str = "",
    ) -> ContentBrief:
        """Build a SERP-driven content brief for a target keyword.

        Pulls the top SERP competitors, scrapes their pages for headings and
        word count, checks for Google's AI Overview, then asks Claude for
        recommended headings / entities / questions. Falls back to a
        deterministic summary if Claude is unavailable.
        """
        competitors = self._collect_competitors(
            keyword, location_code, language_code, scrape_top_n,
        )
        word_counts = [c.word_count for c in competitors if c.word_count]
        serp_median = int(median(word_counts)) if word_counts else 1500
        target = max(serp_median, 800)

        ai_overview = {"present": False, "snippet": ""}
        if self.dfs:
            try:
                ai_overview = self.dfs.ai_overview_for_keyword(
                    keyword, domain=domain,
                    location_code=location_code, language_code=language_code,
                )
            except Exception as exc:
                logger.info("AI overview fetch failed for %s: %s", keyword, exc)

        brief = ContentBrief(
            keyword=keyword,
            target_word_count=target,
            serp_median_words=serp_median,
            competitors=competitors,
            ai_overview_present=bool(ai_overview.get("present")),
            ai_overview_snippet=ai_overview.get("snippet", "") or "",
        )

        if self.claude:
            self._enrich_brief_with_ai(brief, keyword, domain)
        else:
            self._enrich_brief_deterministic(brief)

        return brief

    def _collect_competitors(
        self,
        keyword: str,
        location_code: int,
        language_code: str,
        scrape_top_n: int,
    ) -> list[CompetitorSummary]:
        if not self.dfs:
            return []
        try:
            rows = self.dfs.serp_competitors(
                keyword, location_code=location_code, language_code=language_code,
            )
        except Exception as exc:
            logger.warning("serp_competitors failed for %s: %s", keyword, exc)
            return []

        out: list[CompetitorSummary] = []
        for row in rows[:scrape_top_n]:
            url = row.get("url", "")
            title = row.get("title", "") or ""
            position = row.get("position")
            headings: list[str] = []
            word_count = 0
            if url and self.firecrawl:
                try:
                    md = self.firecrawl.scrape_markdown(url) or ""
                    headings = self._extract_headings(md)
                    word_count = self._word_count(md)
                except Exception as exc:
                    logger.info("Firecrawl scrape failed for %s: %s", url, exc)
            out.append(CompetitorSummary(
                url=url, title=title,
                word_count=word_count, headings=headings, position=position,
            ))
        return out

    def _enrich_brief_with_ai(
        self, brief: ContentBrief, keyword: str, domain: str,
    ) -> None:
        assert self.claude is not None

        comp_blob = "\n\n".join(
            f"#{i+1} {c.url}\nTitle: {c.title}\nWords: {c.word_count}\nHeadings:\n"
            + "\n".join(f"- {h}" for h in c.headings[:15])
            for i, c in enumerate(brief.competitors)
        ) or "(no competitor data — rely on keyword semantics)"

        system = """You are an SEO content strategist. Given a target keyword and
summaries of the top SERP competitors, produce a ready-to-write content brief.

Respond ONLY with valid JSON matching this shape:
{
  "recommended_headings": ["H2 Topic 1", "H2 Topic 2", ...],   // 6-10 items, concrete H2s
  "must_cover_entities": ["entity", "brand", "concept", ...],  // 8-15 items, lowercase
  "questions_to_answer": ["natural question 1?", ...],         // 5-8 PAA-style questions
  "meta_title_suggestion": "<55-60 char SEO title>",
  "meta_description_suggestion": "<150-160 char meta description>",
  "internal_links": [{"anchor": "anchor text", "path": "/suggested-slug"}]  // 3-5 items
}"""

        user = f"""Target keyword: "{keyword}"
Brand domain (if any): {domain or "n/a"}
SERP median word count: {brief.serp_median_words}
AI Overview present: {brief.ai_overview_present}
AI Overview snippet: {brief.ai_overview_snippet[:300]}

Top competitors:
{comp_blob}

Produce the brief."""

        parsed, resp = self.claude.complete_json(
            messages=[{"role": "user", "content": user}],
            system=system,
            model=SONNET,
            max_tokens=2000,
            temperature=0.3,
            use_cache=True,
        )
        self.usage.record(resp)

        brief.recommended_headings = list(parsed.get("recommended_headings", []))[:12]
        brief.must_cover_entities = [
            str(e).lower() for e in parsed.get("must_cover_entities", [])
        ][:20]
        brief.questions_to_answer = list(parsed.get("questions_to_answer", []))[:10]
        brief.meta_title_suggestion = str(parsed.get("meta_title_suggestion", ""))[:120]
        brief.meta_description_suggestion = str(parsed.get("meta_description_suggestion", ""))[:240]
        il = parsed.get("internal_links", [])
        if isinstance(il, list):
            brief.internal_links = [
                {"anchor": str(x.get("anchor", "")), "path": str(x.get("path", ""))}
                for x in il if isinstance(x, dict)
            ][:6]
        brief.ai_generated = True

    def _enrich_brief_deterministic(self, brief: ContentBrief) -> None:
        heading_counter: Counter[str] = Counter()
        for c in brief.competitors:
            for h in c.headings:
                heading_counter[h.strip().lower()] += 1
        brief.recommended_headings = [
            h.title() for h, _ in heading_counter.most_common(8)
        ]
        brief.questions_to_answer = [
            h.title() + "?" for h in brief.recommended_headings if h.endswith("?")
        ][:5]
        brief.meta_title_suggestion = f"{brief.keyword.title()} — Complete Guide"
        brief.meta_description_suggestion = (
            f"Everything you need to know about {brief.keyword}: definitions, "
            "best practices, and practical steps."
        )[:240]

    # ── Content scoring ───────────────────────────────────────────────────────

    def score_content(
        self,
        keyword: str,
        url: str = "",
        markdown: str = "",
        brief: ContentBrief | None = None,
    ) -> ContentScore:
        """Score `markdown` (or the content fetched from `url`) 0-100 against
        the SERP competitors captured in `brief`.
        """
        if brief is None:
            brief = self.generate_brief(keyword)

        if not markdown and url:
            markdown = self._fetch_markdown(url)

        word_count = self._word_count(markdown)
        headings = [h.lower() for h in self._extract_headings(markdown)]
        text_lower = markdown.lower()

        length_score = self._length_score(word_count, brief.serp_median_words)
        heading_score, missing_headings = self._heading_score(
            brief.recommended_headings, headings,
        )
        entity_score, missing_entities = self._entity_score(
            brief.must_cover_entities, text_lower,
        )
        question_score, missing_questions = self._question_score(
            brief.questions_to_answer, text_lower,
        )
        keyword_score = self._keyword_usage_score(keyword, markdown, url)

        total = round(
            length_score + heading_score + entity_score
            + question_score + keyword_score,
            1,
        )

        recs: list[str] = []
        if length_score < 15:
            recs.append(
                f"Expand content to ~{brief.target_word_count} words "
                f"(currently {word_count}, SERP median {brief.serp_median_words})."
            )
        if missing_headings:
            recs.append(
                "Add sections for: " + ", ".join(missing_headings[:5])
            )
        if missing_entities:
            recs.append(
                "Naturally weave in: " + ", ".join(missing_entities[:8])
            )
        if missing_questions:
            recs.append(
                "Answer: " + "; ".join(missing_questions[:3])
            )
        if keyword_score < 10:
            recs.append(
                f"Use the exact keyword '{keyword}' in the title, H1, "
                "and the first 100 words."
            )

        return ContentScore(
            keyword=keyword,
            total=total,
            word_count=word_count,
            serp_median_words=brief.serp_median_words,
            length_score=round(length_score, 1),
            heading_score=round(heading_score, 1),
            entity_score=round(entity_score, 1),
            question_score=round(question_score, 1),
            keyword_usage_score=round(keyword_score, 1),
            missing_headings=missing_headings,
            missing_entities=missing_entities,
            missing_questions=missing_questions,
            recommendations=recs,
        )

    def _fetch_markdown(self, url: str) -> str:
        if self.firecrawl:
            try:
                return self.firecrawl.scrape_markdown(url) or ""
            except Exception as exc:
                logger.warning("Firecrawl scrape failed for %s: %s", url, exc)
        return ""

    @staticmethod
    def _length_score(word_count: int, median_words: int) -> float:
        """20 pts at ≥median, scaled down to 0 at 25% of median."""
        if median_words <= 0:
            return 20.0 if word_count > 300 else 0.0
        ratio = word_count / median_words
        if ratio >= 1.0:
            return 20.0
        if ratio <= 0.25:
            return 0.0
        # Linear from 0 (at 0.25) to 20 (at 1.0)
        return round((ratio - 0.25) / 0.75 * 20.0, 2)

    @staticmethod
    def _heading_score(
        recommended: list[str], headings_lower: list[str],
    ) -> tuple[float, list[str]]:
        """25 pts. Fuzzy match: headline counted as covered if any recommended
        keyword phrase (lowercase, ≥3 chars) appears in any heading."""
        if not recommended:
            return 25.0, []
        covered, missing = [], []
        for r in recommended:
            token = r.lower().strip()
            tokens = [t for t in re.split(r"[^\w]+", token) if len(t) >= 4]
            if not tokens:
                tokens = [token]
            hit = any(
                all(t in h for t in tokens[:2]) for h in headings_lower
            )
            (covered if hit else missing).append(r)
        score = len(covered) / len(recommended) * 25.0
        return score, missing

    @staticmethod
    def _entity_score(
        entities: list[str], text_lower: str,
    ) -> tuple[float, list[str]]:
        """25 pts based on fraction of required entities present."""
        if not entities:
            return 25.0, []
        missing = [e for e in entities if e not in text_lower]
        covered = len(entities) - len(missing)
        return covered / len(entities) * 25.0, missing

    @staticmethod
    def _question_score(
        questions: list[str], text_lower: str,
    ) -> tuple[float, list[str]]:
        """15 pts. A question counts as answered if ≥60% of its content words
        (length ≥4) appear in the page."""
        if not questions:
            return 15.0, []
        missing = []
        for q in questions:
            words = [w for w in re.findall(r"\b[\w']+\b", q.lower()) if len(w) >= 4]
            if not words:
                continue
            hits = sum(1 for w in words if w in text_lower)
            if hits / len(words) < 0.6:
                missing.append(q)
        covered = len(questions) - len(missing)
        return covered / len(questions) * 15.0, missing

    @staticmethod
    def _keyword_usage_score(keyword: str, markdown: str, url: str) -> float:
        """15 pts. Five checks worth 3 pts each."""
        if not keyword or not markdown:
            return 0.0
        kw = keyword.lower()
        lines = markdown.splitlines()
        first_heading = next(
            (l.lstrip("#").strip().lower() for l in lines if l.startswith("#")),
            "",
        )
        first_line = next(
            (l.strip().lower() for l in lines if l.strip()), "",
        )
        first_100_words = " ".join(
            WORD_RE.findall(markdown.lower())[:100]
        )
        checks = [
            kw in first_line,                          # approximates title
            kw in first_heading,                       # H1/H2
            kw in first_100_words,                     # intro usage
            kw.replace(" ", "-") in (url or "").lower(),  # URL slug
            markdown.lower().count(kw) >= 2,           # at least twice total
        ]
        return sum(3.0 for c in checks if c)

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_headings(markdown: str) -> list[str]:
        if not markdown:
            return []
        return [m.group(2).strip() for m in HEADING_RE.finditer(markdown)]

    @staticmethod
    def _word_count(markdown: str) -> int:
        return len(WORD_RE.findall(markdown or ""))

    @staticmethod
    def _slugify(text: str) -> str:
        return "-".join(p for p in text.lower().replace("_", " ").split() if p)
