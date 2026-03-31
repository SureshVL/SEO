from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.agents.research_agent import AlgorithmicReverseEngineerAgent
from app.schemas.research import ResearchRequest, ResearchResponse

RemediationHook = Callable[[ResearchResponse], None]


@dataclass
class WorkflowResult:
    attempts: int
    final_score: float
    passed_threshold: bool
    response: ResearchResponse
    trace: list[str]


class SEOAutonomousLoop:
    """LangGraph-style iterative loop with explicit state transitions."""

    def __init__(
        self,
        research_agent: AlgorithmicReverseEngineerAgent,
        threshold: float = 95.0,
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
        latest = self.research_agent.run(request)
        attempts = 1
        trace.append("research_completed")

        while latest.seo_score < self.threshold and attempts < self.max_iters:
            trace.append(f"score_below_threshold:{latest.seo_score}")
            remediation_count = 0

            if self.apply_content:
                self.apply_content(latest)
                trace.append("content_remediation_applied")
                remediation_count += 1

            if self.apply_technical:
                self.apply_technical(latest)
                trace.append("technical_remediation_applied")
                remediation_count += 1

            if self.apply_aso:
                self.apply_aso(latest)
                trace.append("aso_remediation_applied")
                remediation_count += 1

            latest = self.research_agent.run(request)
            attempts += 1
            trace.append("research_completed")

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
