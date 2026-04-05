"""SEO Autonomous Loop — iterative research + remediation workflow.

Removes the fake +1.5 score inflation and re-runs research properly
after each remediation cycle.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from app.agents.research_agent import AlgorithmicReverseEngineerAgent
from app.schemas.research import ResearchRequest, ResearchResponse

logger = logging.getLogger("omnirank.workflow")

RemediationHook = Callable[[ResearchResponse], None]


@dataclass
class WorkflowResult:
    attempts: int
    final_score: float
    passed_threshold: bool
    response: ResearchResponse
    trace: list[str]


class SEOAutonomousLoop:
    """Iterative loop: research → remediate → re-evaluate until threshold or max iterations."""

    def __init__(
        self,
        research_agent: AlgorithmicReverseEngineerAgent,
        threshold: float = 85.0,
        max_iters: int = 3,
        apply_content: RemediationHook | None = None,
        apply_technical: RemediationHook | None = None,
        apply_aso: RemediationHook | None = None,
    ):
        self.research_agent = research_agent
        self.threshold = threshold
        self.max_iters = max_iters
        self.apply_content = apply_content
        self.apply_technical = apply_technical
        self.apply_aso = apply_aso

    def run(self, request: ResearchRequest) -> WorkflowResult:
        trace: list[str] = ["input_intake"]

        # Initial research pass
        latest = self.research_agent.run(request)
        attempts = 1
        trace.append(f"research_completed:score={latest.seo_score}")
        logger.info("Research pass %d: score=%.2f (threshold=%.2f)", attempts, latest.seo_score, self.threshold)

        while latest.seo_score < self.threshold and attempts < self.max_iters:
            trace.append(f"score_below_threshold:{latest.seo_score}")

            # Apply remediation hooks (these modify external state — CMS, content queue, etc.)
            if self.apply_content:
                try:
                    self.apply_content(latest)
                    trace.append("content_remediation_applied")
                except Exception as exc:
                    logger.error("Content remediation failed: %s", exc)
                    trace.append(f"content_remediation_failed:{exc}")

            if self.apply_technical:
                try:
                    self.apply_technical(latest)
                    trace.append("technical_remediation_applied")
                except Exception as exc:
                    logger.error("Technical remediation failed: %s", exc)
                    trace.append(f"technical_remediation_failed:{exc}")

            if self.apply_aso:
                try:
                    self.apply_aso(latest)
                    trace.append("aso_remediation_applied")
                except Exception as exc:
                    logger.error("ASO remediation failed: %s", exc)
                    trace.append(f"aso_remediation_failed:{exc}")

            # Re-run research to get updated score
            # NOTE: The score will only change if the underlying page content has actually changed.
            # In a real-time flow, remediations push content to CMS → page updates → re-crawl shows new score.
            # For async jobs, the re-evaluation may show the same score until content is deployed.
            latest = self.research_agent.run(request)
            attempts += 1
            trace.append(f"research_completed:score={latest.seo_score}")
            logger.info("Research pass %d: score=%.2f", attempts, latest.seo_score)

        if latest.seo_score >= self.threshold:
            trace.append("threshold_achieved")
        else:
            trace.append("max_iterations_reached")

        return WorkflowResult(
            attempts=attempts,
            final_score=latest.seo_score,
            passed_threshold=latest.seo_score >= self.threshold,
            response=latest,
            trace=trace,
        )
