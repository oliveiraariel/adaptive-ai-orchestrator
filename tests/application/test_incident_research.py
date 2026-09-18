from types import SimpleNamespace

from application.incident_ports import ExternalResearchRequest
from application.incident_research import RunOrchestrationExternalResearchPort
from domain.evaluation import EvaluationVerdict


class FakeRunner:
    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return SimpleNamespace(
            verdict=EvaluationVerdict.ACCEPTED,
            execution_id="exec-research",
            external_id="runtime-research",
            evidence=("source:https://vendor.example/docs",),
            raw_result={"result_ref": "/tmp/result/manifest.json"},
        )


def test_runtime_research_port_is_read_only_and_returns_references():
    runner = FakeRunner()
    port = RunOrchestrationExternalResearchPort(
        runner,
        tools=("web-search",),
    )
    refs = port.research(
        ExternalResearchRequest(
            incident_id="INC-1",
            query="Find authoritative evidence for a runtime transport failure.",
        )
    )

    request = runner.requests[0]
    assert request.requested_side_effects == ()
    assert request.human_approved is False
    assert request.skills == ("technical-research", "debugging")
    assert "Research and diagnosis only" in "\n".join(request.constraints)
    assert "execution:exec-research" in refs
    assert "result_ref:/tmp/result/manifest.json" in refs
