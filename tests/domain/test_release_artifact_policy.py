from domain.api_generation_policy import API_GENERATION_POLICY_MARKER
from domain.release_artifact_policy import (
    RELEASE_ARTIFACT_POLICY_DIRECTIVES,
    RELEASE_ARTIFACT_POLICY_MARKER,
    enforce_release_artifact_policy,
    release_artifact_policy_applies,
)
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage


def make_configuration() -> ResourceConfiguration:
    return ResourceConfiguration(
        agent="agent-001",
        skills=("integration-release",),
        model="model-001",
        provider="provider-001",
        runtime="openclaw",
    )


def test_detects_fresh_zip_and_installable_artifact_creation() -> None:
    assert release_artifact_policy_applies(
        objective="Generate a fresh ZIP package for WordPress plugin retest."
    )
    assert release_artifact_policy_applies(
        objective="Gere um novo pacote ZIP do plugin para reteste."
    )
    assert release_artifact_policy_applies(
        objective="Build an installable release artifact for environmental validation."
    )


def test_does_not_treat_inspection_or_installation_as_packaging() -> None:
    assert not release_artifact_policy_applies(
        objective="Inspect the existing ZIP and report its SHA-256."
    )
    assert not release_artifact_policy_applies(
        objective="Install the existing plugin ZIP in WordPress."
    )


def test_marker_forces_packaging_policy() -> None:
    assert release_artifact_policy_applies(
        objective="Prepare the requested deliverable.",
        constraints=(RELEASE_ARTIFACT_POLICY_MARKER,),
    )


def test_enforcement_appends_policy_once_and_preserves_constraints() -> None:
    constraints = enforce_release_artifact_policy(
        objective="Create a release ZIP for retest.",
        constraints=("preserve-current-wip",),
    )

    assert constraints[0] == "preserve-current-wip"
    assert all(item in constraints for item in RELEASE_ARTIFACT_POLICY_DIRECTIVES)

    repeated = enforce_release_artifact_policy(
        objective="Create a release ZIP for retest.",
        constraints=constraints,
    )
    assert repeated == constraints


def test_task_package_injects_packaging_governance_without_changing_routing_constraints() -> None:
    task = TaskPackage(
        task_id="task-package-001",
        work_unit_id="wu-package-001",
        objective="Gere um novo ZIP instalável para reteste ambiental.",
        decisions=("preserve-authoritative-wip",),
        constraints=("do-not-deploy",),
        configuration=make_configuration(),
        expected_output=("release artifact", "verification evidence"),
        acceptance_criteria=("artifact-integrity-verified",),
    )

    assert task.constraints == ("do-not-deploy",)
    assert task.decisions[0] == "preserve-authoritative-wip"
    assert all(item in task.decisions for item in RELEASE_ARTIFACT_POLICY_DIRECTIVES)
    assert any(
        decision.startswith(RELEASE_ARTIFACT_POLICY_MARKER)
        for decision in task.decisions
    )


def test_api_plugin_package_receives_both_runtime_policies() -> None:
    task = TaskPackage(
        task_id="task-api-package",
        work_unit_id="wu-api-package",
        objective="Create a ZIP package for the REST API plugin release retest.",
        configuration=make_configuration(),
        expected_output=("installable package",),
        acceptance_criteria=("package-ready",),
    )

    assert any(
        decision.startswith(API_GENERATION_POLICY_MARKER)
        for decision in task.decisions
    )
    assert any(
        decision.startswith(RELEASE_ARTIFACT_POLICY_MARKER)
        for decision in task.decisions
    )


def test_non_packaging_work_is_unchanged() -> None:
    task = TaskPackage(
        task_id="task-doc-001",
        work_unit_id="wu-doc-001",
        objective="Update the project handoff document.",
        decisions=("keep-history",),
        constraints=("preserve-history",),
        configuration=make_configuration(),
        expected_output=("documentation",),
        acceptance_criteria=("handoff-updated",),
    )

    assert task.decisions == ("keep-history",)
    assert task.constraints == ("preserve-history",)
