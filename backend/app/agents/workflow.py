from __future__ import annotations

from dataclasses import dataclass

from app.agents.research_agent import AlgorithmicReverseEngineerAgent
from app.schemas.research import ResearchRequest, ResearchResponse


@dataclass
class WorkflowResult:
    attempts: int
    final_score: float
    passed_threshold: bool
    response: ResearchResponse


class SEOAutonomousLoop:
    """LangGraph-style iterative loop (deterministic phase-1 implementation).

    In later phases, each iteration can call Content/Technical/ASO agents to refine output.
    """

    def __init__(self, research_agent: AlgorithmicReverseEngineerAgent, threshold: float = 95.0, max_iters: int = 3):
        self.research_agent = research_agent
        self.threshold = threshold
        self.max_iters = max_iters

    def run(self, request: ResearchRequest) -> WorkflowResult:
        latest = self.research_agent.run(request)
        attempts = 1

        while latest.seo_score < self.threshold and attempts < self.max_iters:
            # Phase-1 loop: rerun research for refreshed competitor snapshots.
            # Future phase: apply recommendations via content/technical agents between loops.
            latest = self.research_agent.run(request)
            attempts += 1

        return WorkflowResult(
            attempts=attempts,
            final_score=latest.seo_score,
            passed_threshold=latest.seo_score >= self.threshold,
            response=latest,
        )
