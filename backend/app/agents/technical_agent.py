from __future__ import annotations

from dataclasses import dataclass

from app.schemas.research import ResearchResponse


@dataclass
class TechnicalAction:
    category: str
    action: str
    impact: str


class TechnicalAgent:
    """Generate deterministic technical remediation actions from research output."""

    def execute(self, actions: list[TechnicalAction]) -> list[dict[str, str]]:
        return [{"category": a.category, "status": "queued", "action": a.action} for a in actions]

    def audit(self, research: ResearchResponse) -> list[TechnicalAction]:
        actions: list[TechnicalAction] = [
            TechnicalAction(
                category="core_web_vitals",
                action="Compress and lazy-load below-the-fold images; target LCP < 2.5s.",
                impact="high",
            ),
            TechnicalAction(
                category="internal_linking",
                action="Add contextual links from top-traffic pages to new snippet sections.",
                impact="medium",
            ),
            TechnicalAction(
                category="broken_link_outreach",
                action="Find broken links on competitor-referring pages and pitch replacement content.",
                impact="high",
            ),
        ]

        if research.gap_analysis.heading_gaps:
            actions.append(
                TechnicalAction(
                    category="information_architecture",
                    action="Add missing H2 sections and include FAQ schema markup for snippet capture.",
                    impact="high",
                )
            )

        return actions
