import pytest

from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage, TaskPackageError


def make_configuration() -> ResourceConfiguration:
    return ResourceConfiguration(
        agent="agent-001",
        skills=("tdd",),
        model="model-001",
        provider="provider-001",
        runtime="openclaw",
    )


def make_task() -> TaskPackage:
    return TaskPackage(
        task_id="task-001",
        work_unit_id="wu-001",
        objective="Implement the requested Work Unit.",
        scope="Only the requested domain behavior.",
        context=("project-baseline",),
        inputs=("work-unit-definition",),
        artifacts=("specification.md",),
        decisions=("decision-001",),
        dependencies=("wu-000",),
        constraints=("do-not-change-public-contract",),
        configuration=make_configuration(),
        expected_output=("implementation", "tests"),
        acceptance_criteria=("all-tests-pass",),
    )


def test_task_package_requires_task_id() -> None:
    with pytest.raises(TaskPackageError):
        TaskPackage(
            task_id="",
            work_unit_id="wu-001",
            objective="Implement.",
        )


def test_task_package_requires_work_unit_id() -> None:
    with pytest.raises(TaskPackageError):
        TaskPackage(
            task_id="task-001",
            work_unit_id="",
            objective="Implement.",
        )


def test_task_package_requires_objective() -> None:
    with pytest.raises(TaskPackageError):
        TaskPackage(
            task_id="task-001",
            work_unit_id="wu-001",
            objective="",
        )


def test_task_package_requires_configuration() -> None:
    with pytest.raises(TaskPackageError):
        TaskPackage(
            task_id="task-001",
            work_unit_id="wu-001",
            objective="Implement.",
            expected_output=("code",),
            acceptance_criteria=("tests-pass",),
        )


def test_task_package_requires_expected_output() -> None:
    with pytest.raises(TaskPackageError):
        TaskPackage(
            task_id="task-001",
            work_unit_id="wu-001",
            objective="Implement.",
            configuration=make_configuration(),
            acceptance_criteria=("tests-pass",),
        )


def test_task_package_requires_acceptance_criteria() -> None:
    with pytest.raises(TaskPackageError):
        TaskPackage(
            task_id="task-001",
            work_unit_id="wu-001",
            objective="Implement.",
            configuration=make_configuration(),
            expected_output=("code",),
        )


def test_task_package_preserves_execution_contract() -> None:
    task = make_task()

    assert task.task_id == "task-001"
    assert task.work_unit_id == "wu-001"
    assert task.objective == "Implement the requested Work Unit."
    assert task.scope == "Only the requested domain behavior."
    assert task.context == ("project-baseline",)
    assert task.inputs == ("work-unit-definition",)
    assert task.artifacts == ("specification.md",)
    assert task.decisions == ("decision-001",)
    assert task.dependencies == ("wu-000",)
    assert task.constraints == ("do-not-change-public-contract",)
    assert task.configuration is not None
    assert task.expected_output == ("implementation", "tests")
    assert task.acceptance_criteria == ("all-tests-pass",)
