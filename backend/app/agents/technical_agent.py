from __future__ import annotations

from app.schemas.orchestrator import TechnicalFix
from app.schemas.research import ResearchResponse


class TechnicalAgent:
    """Generate technical SEO action list based on simple heuristics."""

    def diagnose(self, research: ResearchResponse) -> list[TechnicalFix]:
        fixes: list[TechnicalFix] = []

        if research.client_profile.word_count < 900:
            fixes.append(
                TechnicalFix(
                    issue="Thin content depth vs competitors",
                    recommendation="Increase main content depth and add structured subsection anchors.",
                    priority="high",
                )
            )

        if research.gap_analysis.missing_questions:
            fixes.append(
                TechnicalFix(
                    issue="Insufficient snippet-targeted FAQ coverage",
                    recommendation="Inject FAQ schema and concise Q/A pairs under each strategic heading.",
                    priority="high",
                )
            )

        if research.gap_analysis.density_gap > 0.5:
            fixes.append(
                TechnicalFix(
                    issue="Primary keyword underrepresented",
                    recommendation="Increase natural keyword occurrences in H2 intros and image alt text.",
                    priority="medium",
                )
            )

        if not fixes:
            fixes.append(
                TechnicalFix(
                    issue="No high-priority technical blockers inferred",
                    recommendation="Proceed with CWV audit and link graph optimization next.",
                    priority="low",
                )
            )

        return fixes
