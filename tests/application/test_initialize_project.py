from domain.project import ProjectId, ProjectStatus
from infrastructure.project_state_repository import InMemoryProjectStateRepository

from application.initialize_project import (
    CreateWorkUnit,
    CreateWorkUnitCommand,
    InitializeProject,
    InitializeProjectCommand,
    ReadProject,
)


def make_application():
    repository = InMemoryProjectStateRepository()

    return (
        repository,
        InitializeProject(repository),
        CreateWorkUnit(repository),
        ReadProject(repository),
    )


def test_initialize_create_store_read_flow() -> None:
    (
        repository,
        initialize_project,
        create_work_unit,
        read_project,
    ) = make_application()

    project = initialize_project.execute(
        InitializeProjectCommand(
            project_id="project-001",
            identity="Adaptive AI Orchestrator",
        )
    )

    assert project.status is ProjectStatus.ACTIVE
    assert repository.get(project.id) is project

    work_unit = create_work_unit.execute(
        project.id,
        CreateWorkUnitCommand(
            work_unit_id="wu-001",
            objective="Prove the first vertical slice",
        ),
    )

    loaded = read_project.execute(ProjectId("project-001"))

    assert loaded is project
    assert work_unit.id.value == "wu-001"
    assert loaded.work_unit_ids == ("wu-001",)


def test_create_work_unit_requires_existing_project() -> None:
    _, _, create_work_unit, _ = make_application()

    try:
        create_work_unit.execute(
            ProjectId("missing"),
            CreateWorkUnitCommand(
                work_unit_id="wu-001",
                objective="This should fail",
            ),
        )
    except ValueError as exc:
        assert "Project 'missing' was not found." in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing project.")


def test_read_project_returns_none_for_unknown_project() -> None:
    _, _, _, read_project = make_application()

    assert read_project.execute(ProjectId("missing")) is None
