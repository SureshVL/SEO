from __future__ import annotations

from dataclasses import dataclass

from app.schemas.research import ResearchResponse


@dataclass
class ContentDraft:
    title: str
    slug: str
    body_markdown: str
    target_keyword: str


class ContentAgent:
    """Generate position-zero oriented drafts from research gaps."""

    def generate(self, research: ResearchResponse, primary_keyword: str) -> list[ContentDraft]:
        missing_questions = research.gap_analysis.missing_questions[:3]
        missing_entities = research.gap_analysis.missing_entities[:6]

        faq_block = "\n".join([f"### {q}\n- Direct answer in 40-55 words." for q in missing_questions])
        if not faq_block:
            faq_block = "### What should this page answer?\n- Add high-intent user questions and concise answers."

        entity_block = ", ".join(missing_entities) if missing_entities else "No additional entities detected"

        draft = ContentDraft(
            title=f"{primary_keyword.title()} — Complete Guide",
            slug=self._slugify(primary_keyword + " guide"),
            target_keyword=primary_keyword,
            body_markdown=(
                f"## Featured Snippet Summary\n"
                f"{primary_keyword} is improved by combining entity coverage, structured FAQs, and technical SEO hygiene.\n\n"
                f"## Entity Coverage to Add\n{entity_block}\n\n"
                f"## FAQ (Position Zero)\n{faq_block}"
            ),
        )

        return [draft]

    @staticmethod
    def _slugify(text: str) -> str:
        return "-".join(part for part in text.lower().replace("_", " ").split() if part)
