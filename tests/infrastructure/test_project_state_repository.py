from domain.project import Project, ProjectId, ProjectStatus
from infrastructure.project_state_repository import InMemoryProjectStateRepository


def make_project() -> Project:
    project = Project(
        id=ProjectId("project-001"),
        identity="Adaptive AI Orchestrator",
    )
    project.activate()
    return project


def test_repository_returns_none_when_project_does_not_exist() -> None:
    repository = InMemoryProjectStateRepository()

    assert repository.get(ProjectId("missing")) is None


def test_repository_saves_and_loads_project() -> None:
    repository = InMemoryProjectStateRepository()
    project = make_project()

    repository.save(project)

    loaded = repository.get(project.id)

    assert loaded is project
    assert loaded.status is ProjectStatus.ACTIVE


def test_repository_replaces_existing_project_state() -> None:
    repository = InMemoryProjectStateRepository()
    project = make_project()

    repository.save(project)
    project.suspend()
    repository.save(project)

    loaded = repository.get(project.id)

    assert loaded is project
    assert loaded.status is ProjectStatus.SUSPENDED


def test_repositories_are_isolated() -> None:
    first = InMemoryProjectStateRepository()
    second = InMemoryProjectStateRepository()
    project = make_project()

    first.save(project)

    assert first.get(project.id) is project
    assert second.get(project.id) is None
