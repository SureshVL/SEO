from __future__ import annotations

import re

from app.schemas.orchestrator import ContentQueueItem
from app.schemas.research import ResearchResponse


class ContentAgent:
    """Generate Position-Zero oriented content artifacts from research gaps."""

    def build_content_queue(self, research: ResearchResponse, keyword: str) -> list[ContentQueueItem]:
        title = f"{keyword.title()} Guide: Answering Top Questions"
        slug = self._slugify(f"{keyword}-featured-snippet-guide")

        faq_lines: list[str] = []
        for question in research.gap_analysis.missing_questions[:5]:
            faq_lines.append(f"### {question}")
            faq_lines.append("Provide a concise, evidence-backed answer in 40-60 words.")
            faq_lines.append("")

        sections = "\n".join([f"- {h}" for h in research.gap_analysis.heading_gaps[:8]])
        entities = ", ".join(research.gap_analysis.missing_entities[:10])

        body = (
            f"## Why this page will rank for {keyword}\n"
            "This draft is generated from competitor gap analysis and optimized for snippet clarity.\n\n"
            "## Missing topical sections to include\n"
            f"{sections or '- Add benchmark-aligned sections from competitor headings.'}\n\n"
            "## Entity coverage checklist\n"
            f"{entities or 'No entity gaps detected.'}\n\n"
            "## FAQ block for Position Zero\n"
            f"{chr(10).join(faq_lines) if faq_lines else 'Add 3-5 direct question/answer pairs.'}\n"
        )

        return [
            ContentQueueItem(
                title=title,
                slug=slug,
                body_markdown=body,
                target_keyword=keyword,
            )
        ]

    @staticmethod
    def _slugify(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
