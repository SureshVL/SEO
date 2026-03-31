from __future__ import annotations

from app.agents.aso_agent import AsoAgent
from app.agents.content_agent import ContentAgent
from app.agents.research_agent import AlgorithmicReverseEngineerAgent
from app.agents.technical_agent import TechnicalAgent
from app.agents.workflow import SEOAutonomousLoop
from app.schemas.aso import AsoRequest
from app.schemas.orchestrator import AgentLogEntry, OrchestratorRequest, OrchestratorResponse
from app.schemas.research import ResearchRequest


class OrchestratorAgent:
    """Runs multi-agent cycle and returns consolidated actionable output."""

    def __init__(
        self,
        research_agent: AlgorithmicReverseEngineerAgent,
        aso_agent: AsoAgent | None = None,
        content_agent: ContentAgent | None = None,
        technical_agent: TechnicalAgent | None = None,
        threshold: float = 95.0,
        max_cycles: int = 3,
    ):
        self.loop = SEOAutonomousLoop(research_agent=research_agent, threshold=threshold, max_iters=max_cycles)
        self.aso_agent = aso_agent or AsoAgent()
        self.content_agent = content_agent or ContentAgent()
        self.technical_agent = technical_agent or TechnicalAgent()

    def run(self, request: OrchestratorRequest) -> OrchestratorResponse:
        logs: list[AgentLogEntry] = []
        logs.append(AgentLogEntry(step="research:start", status="ok", detail="Starting reverse-engineer cycle."))

        research_result = self.loop.run(
            ResearchRequest(
                client_url=request.client_url,
                primary_keyword=request.primary_keyword,
                target_region=request.target_region,
                locale=request.locale,
            )
        )
        logs.append(
            AgentLogEntry(
                step="research:complete",
                status="ok",
                detail=(
                    f"Completed in {research_result.attempts} cycles with score {research_result.final_score}."
                ),
            )
        )

        technical_fixes = self.technical_agent.diagnose(research_result.response)
        logs.append(AgentLogEntry(step="technical:complete", status="ok", detail=f"Generated {len(technical_fixes)} fixes."))

        content_queue = self.content_agent.build_content_queue(research_result.response, request.primary_keyword)
        logs.append(AgentLogEntry(step="content:complete", status="ok", detail=f"Queued {len(content_queue)} content assets."))

        aso_result = None
        if request.app_link and request.app_name and request.app_category:
            aso_result = self.aso_agent.run(
                AsoRequest(
                    app_link=request.app_link,
                    app_name=request.app_name,
                    category=request.app_category,
                    primary_keyword=request.primary_keyword,
                    secondary_keywords=request.secondary_keywords,
                    locales=[request.locale],
                )
            )
            logs.append(AgentLogEntry(step="aso:complete", status="ok", detail="Generated localized ASO metadata."))
        else:
            logs.append(AgentLogEntry(step="aso:skipped", status="ok", detail="No app context provided."))

        return OrchestratorResponse(
            cycles=research_result.attempts,
            final_score=research_result.final_score,
            threshold_met=research_result.passed_threshold,
            research=research_result.response,
            aso=aso_result,
            technical_fixes=technical_fixes,
            content_queue=content_queue,
            logs=logs,
        )
