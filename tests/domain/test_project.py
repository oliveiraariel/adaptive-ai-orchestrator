import pytest

from domain.project import (
    Project,
    ProjectId,
    ProjectStateError,
    ProjectStatus,
)


def make_project() -> Project:
    return Project(
        id=ProjectId("project-001"),
        identity="Adaptive AI Orchestrator",
    )


def test_project_requires_identity() -> None:
    with pytest.raises(ProjectStateError):
        Project(id=ProjectId("project-001"), identity="")


def test_project_starts_initializing() -> None:
    project = make_project()

    assert project.status is ProjectStatus.INITIALIZING


def test_project_can_be_activated() -> None:
    project = make_project()

    project.activate()

    assert project.status is ProjectStatus.ACTIVE


def test_project_can_be_suspended_from_active() -> None:
    project = make_project()
    project.activate()

    project.suspend()

    assert project.status is ProjectStatus.SUSPENDED


def test_project_can_be_reactivated_after_suspension() -> None:
    project = make_project()
    project.activate()
    project.suspend()

    project.activate()

    assert project.status is ProjectStatus.ACTIVE


def test_completed_project_cannot_be_blocked() -> None:
    project = make_project()
    project.activate()
    project.complete()

    with pytest.raises(ProjectStateError):
        project.block()
