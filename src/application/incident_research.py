from __future__ import annotations

from application.incident_ports import ExternalResearchRequest
from application.run_orchestration import RunOrchestration, RunOrchestrationRequest
from domain.evaluation import EvaluationVerdict
from domain.execution_policy import ExecutionPolicy


class IncidentResearchError(RuntimeError):
    pass


class RunOrchestrationExternalResearchPort:
    """Execute read-only incident research through the normal governed Work Unit path."""

    COMPLETE_MARKER = "ADAPTIVE_INCIDENT_RESEARCH_COMPLETE"

    def __init__(
        self,
        runner: RunOrchestration,
        *,
        agent: str = "main",
        tools: tuple[str, ...] = (),
    ) -> None:
        self.runner = runner
        self.agent = agent
        self.tools = tools

    def research(self, request: ExternalResearchRequest) -> tuple[str, ...]:
        result = self.runner.execute(
            RunOrchestrationRequest(
                objective=request.query,
                agent=self.agent,
                skills=("technical-research", "debugging"),
                tools=self.tools,
                scope=f"incident:{request.incident_id}",
                context=(
                    f"Incident reference: {request.incident_id}",
                    "Prefer primary vendor/runtime documentation, official issue trackers and upstream source.",
                ),
                constraints=(
                    "Research and diagnosis only. Do not modify source, configuration, credentials, deployments, or external systems.",
                    "Separate sourced fact, observed evidence, inference and recommendation.",
                    "Return source pointers and bounded findings. Do not include secrets, raw prompts or chain-of-thought.",
                    f"End the response with exactly: {self.COMPLETE_MARKER}",
                ),
                expected_output=(
                    "source-backed incident research findings",
                    self.COMPLETE_MARKER,
                ),
                acceptance_criteria=(self.COMPLETE_MARKER,),
                execution_policy=ExecutionPolicy(),
                requested_side_effects=(),
                human_approved=False,
                claimant_id=f"incident-research:{request.incident_id}",
            )
        )
        if result.verdict is not EvaluationVerdict.ACCEPTED:
            raise IncidentResearchError(
                f"Incident research was not accepted: {result.verdict.value}"
            )

        refs = [
            f"execution:{result.execution_id}",
            f"external:{result.external_id}",
        ]
        refs.extend(str(item)[:300] for item in result.evidence if str(item))
        raw = result.raw_result
        if isinstance(raw, dict):
            for key in ("result_ref", "manifest_path", "result_manifest"):
                value = raw.get(key)
                if isinstance(value, str) and value.strip():
                    refs.append(f"{key}:{value.strip()[:240]}")
        return tuple(dict.fromkeys(refs))
