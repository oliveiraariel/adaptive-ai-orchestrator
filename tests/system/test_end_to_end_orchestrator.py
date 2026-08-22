from application.agent_runtime import (
    AgentRuntimeResult,
    AgentRuntimeStatus,
    ExecutionReference,
)
from application.agent_skill_analysis import AgentSkillAnalysis
from application.delegate_work import DelegateWork, DelegateWorkRequest
from application.evaluate_result import EvaluateResult, EvaluateResultRequest
from application.plan_work import PlanWork, PlanWorkRequest
from application.resource_selection import (
    ResourceSelection,
    ResourceSelectionRequest,
)
from application.replan_project import ReplanProject, ReplanProjectRequest
from domain.agent_profile import AgentId, AgentProfile
from domain.dependency import Dependency
from domain.evaluation import EvaluationVerdict
from domain.model_profile import ModelId, ModelProfile
from domain.plan import PlanStatus
from domain.project import Project, ProjectId
from domain.resource_configuration import ResourceConfiguration
from domain.result_package import ResultPackage, ResultPackageStatus
from domain.skill_profile import SkillId, SkillProfile
from domain.task_package import TaskPackage
from domain.work_unit import WorkUnit, WorkUnitId, WorkUnitState
from infrastructure.catalogs import (
    InMemoryAgentCatalog,
    InMemoryModelCatalog,
    InMemorySkillCatalog,
)


class FakeRuntime:
    def submit(self, task: TaskPackage) -> ExecutionReference:
        return ExecutionReference(
            id=f"execution:{task.task_id}",
            runtime="fake-runtime",
            external_id=task.task_id,
            status=AgentRuntimeStatus.SUBMITTED,
        )

    def get_status(self, execution: ExecutionReference) -> AgentRuntimeStatus:
        return AgentRuntimeStatus.COMPLETED

    def retrieve_result(
        self,
        execution: ExecutionReference,
    ) -> AgentRuntimeResult:
        return AgentRuntimeResult(
            execution=ExecutionReference(
                id=execution.id,
                runtime=execution.runtime,
                external_id=execution.external_id,
                status=AgentRuntimeStatus.COMPLETED,
            ),
            raw_result={"tests-pass": True},
        )

    def cancel(self, execution: ExecutionReference) -> ExecutionReference:
        return execution


def make_project() -> Project:
    return Project(
        id=ProjectId("project-e2e"),
        identity="Adaptive AI Orchestrator",
        baseline="baseline-001",
    )


def make_work_unit() -> WorkUnit:
    return WorkUnit(
        id=WorkUnitId("wu-e2e"),
        objective="Execute end-to-end orchestration flow.",
        required_capabilities=("testing",),
        criteria=("tests-pass",),
        priority=10,
    )


def make_resource_selection() -> ResourceSelection:
    agents = InMemoryAgentCatalog()
    skills = InMemorySkillCatalog()
    models = InMemoryModelCatalog()

    agents.add(
        AgentProfile(
            id=AgentId("agent-e2e"),
            role="engineering-agent",
            capabilities=("testing",),
        )
    )

    skills.add(
        SkillProfile(
            id=SkillId("tdd"),
            purpose="Test-driven development",
            capabilities=("testing",),
            compatible_agents=("agent-e2e",),
            compatible_models=("model-e2e",),
            compatible_runtimes=("fake-runtime",),
        )
    )

    models.add(
        ModelProfile(
            id=ModelId("model-e2e"),
            name="E2E Model",
            version="1.0",
            provider="test-provider",
        )
    )

    return ResourceSelection(
        agent_skill_analysis=AgentSkillAnalysis(
            agent_catalog=agents,
            skill_catalog=skills,
        ),
        skill_catalog=skills,
        model_catalog=models,
    )


def test_full_orchestration_cycle() -> None:
    project = make_project()
    work_unit = make_work_unit()

    # PLAN
    plan_result = PlanWork().execute(
        PlanWorkRequest(
            project=project,
            work_units=(work_unit,),
            dependencies=(),
            version=1,
        )
    )

    assert plan_result.plan.status is PlanStatus.ACTIVE
    assert plan_result.ready_work_unit_ids == ("wu-e2e",)

    # RESOURCE SELECTION
    selection = make_resource_selection()
    selection_result = selection.execute(
        ResourceSelectionRequest(work_unit=work_unit)
    )

    configuration = selection_result.configuration
    assert configuration is not None
    assert configuration.agent == "agent-e2e"
    assert configuration.model == "model-e2e"

    # TASK PACKAGE
    task_package = TaskPackage(
        task_id="task-e2e",
        work_unit_id=work_unit.id.value,
        objective=work_unit.objective,
        configuration=configuration,
        expected_output=("implementation",),
        acceptance_criteria=("tests-pass",),
    )

    # EXECUTE / DELEGATE
    work_unit.mark_ready()

    delegation_result = DelegateWork(FakeRuntime()).execute(
        DelegateWorkRequest(
            work_unit=work_unit,
            configuration=configuration,
            task_package=task_package,
        )
    )

    assert delegation_result.execution.status is AgentRuntimeStatus.SUBMITTED
    assert work_unit.state is WorkUnitState.RUNNING

    # RESULT / EVALUATE
    work_unit.start_evaluation()

    result_package = ResultPackage(
        task_id=task_package.task_id,
        status=ResultPackageStatus.SUCCEEDED,
        result={"tests-pass": True},
        evidence=("tests-pass",),
    )

    evaluation = EvaluateResult().execute(
        EvaluateResultRequest(
            result_package=result_package,
            criteria=("tests-pass",),
            evaluator_id="evaluator-e2e",
        )
    ).evaluation

    assert evaluation.verdict is EvaluationVerdict.ACCEPTED

    # REPLAN / NEW PLAN
    revised_plan = ReplanProject(PlanWork()).execute(
        ReplanProjectRequest(
            project=project,
            current_plan=plan_result.plan,
            work_units=(work_unit,),
            dependencies=(),
            trigger="evaluation-accepted",
        )
    ).revision

    assert revised_plan.new_plan.version.value == 2
    assert revised_plan.new_plan.status is PlanStatus.ACTIVE
    assert revised_plan.new_plan.work_unit_ids == ("wu-e2e",)
