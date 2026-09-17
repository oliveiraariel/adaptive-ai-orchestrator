from domain.api_generation_policy import (
    API_GENERATION_POLICY_CONSTRAINTS,
    API_GENERATION_POLICY_MARKER,
    api_generation_policy_applies,
    enforce_api_generation_policy,
)
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage


def make_configuration() -> ResourceConfiguration:
    return ResourceConfiguration(
        agent="agent-001",
        skills=("implementation",),
        model="model-001",
        provider="provider-001",
        runtime="openclaw",
    )


def test_detects_language_neutral_api_creation() -> None:
    assert api_generation_policy_applies(
        objective="Create an API for order management in the current stack."
    )
    assert api_generation_policy_applies(
        objective="Implementar endpoints GraphQL para pedidos."
    )
    assert api_generation_policy_applies(
        objective="Add a gRPC service method without changing unrelated code."
    )


def test_detects_existing_api_contract_change() -> None:
    assert api_generation_policy_applies(
        objective="Fix the /users endpoint authorization contract."
    )
    assert api_generation_policy_applies(
        objective="Alterar o contrato de API existente para aceitar paginação."
    )


def test_does_not_treat_external_api_consumption_as_api_generation() -> None:
    assert not api_generation_policy_applies(
        objective="Integrate the external Stripe API as a client."
    )
    assert not api_generation_policy_applies(
        objective="Create an API key for the existing provider connection."
    )


def test_marker_forces_policy_when_intent_is_not_in_objective() -> None:
    assert api_generation_policy_applies(
        objective="Implement the delegated change.",
        constraints=(API_GENERATION_POLICY_MARKER,),
    )


def test_enforcement_appends_policy_once_and_preserves_existing_constraints() -> None:
    constraints = enforce_api_generation_policy(
        objective="Build a REST API for invoices.",
        constraints=("preserve-current-database",),
    )

    assert constraints[0] == "preserve-current-database"
    assert all(item in constraints for item in API_GENERATION_POLICY_CONSTRAINTS)

    repeated = enforce_api_generation_policy(
        objective="Build a REST API for invoices.",
        constraints=constraints,
    )
    assert repeated == constraints


def test_task_package_enforces_policy_at_common_execution_boundary() -> None:
    task = TaskPackage(
        task_id="task-api-001",
        work_unit_id="wu-api-001",
        objective="Create a webhook endpoint for payment notifications.",
        scope="Only the payment notification API surface.",
        constraints=("preserve-existing-consumers",),
        configuration=make_configuration(),
        expected_output=("implementation", "tests"),
        acceptance_criteria=("contract-tests-pass",),
    )

    assert task.constraints[0] == "preserve-existing-consumers"
    assert any(
        constraint.startswith(API_GENERATION_POLICY_MARKER)
        for constraint in task.constraints
    )


def test_task_package_leaves_non_api_work_unchanged() -> None:
    task = TaskPackage(
        task_id="task-doc-001",
        work_unit_id="wu-doc-001",
        objective="Update the project handoff document.",
        constraints=("preserve-history",),
        configuration=make_configuration(),
        expected_output=("documentation",),
        acceptance_criteria=("handoff-updated",),
    )

    assert task.constraints == ("preserve-history",)
