from dataclasses import dataclass

from domain.project import Project, ProjectId
from domain.work_unit import WorkUnit, WorkUnitId
from infrastructure.project_state_repository import ProjectStateRepository


@dataclass(frozen=True)
class InitializeProjectCommand:
    project_id: str
    identity: str


@dataclass(frozen=True)
class CreateWorkUnitCommand:
    work_unit_id: str
    objective: str


class InitializeProject:
    """Application use case for initializing a project."""

    def __init__(self, repository: ProjectStateRepository) -> None:
        self._repository = repository

    def execute(self, command: InitializeProjectCommand) -> Project:
        project = Project(
            id=ProjectId(command.project_id),
            identity=command.identity,
        )
        project.activate()
        self._repository.save(project)
        return project


class CreateWorkUnit:
    """Application use case for creating and attaching a Work Unit."""

    def __init__(self, repository: ProjectStateRepository) -> None:
        self._repository = repository

    def execute(
        self,
        project_id: ProjectId,
        command: CreateWorkUnitCommand,
    ) -> WorkUnit:
        project = self._repository.get(project_id)

        if project is None:
            raise ValueError(f"Project '{project_id.value}' was not found.")

        work_unit = WorkUnit(
            id=WorkUnitId(command.work_unit_id),
            objective=command.objective,
        )

        project.work_unit_ids = (*project.work_unit_ids, work_unit.id.value)
        self._repository.save(project)

        return work_unit


class ReadProject:
    """Application use case for retrieving project state."""

    def __init__(self, repository: ProjectStateRepository) -> None:
        self._repository = repository

    def execute(self, project_id: ProjectId) -> Project | None:
        return self._repository.get(project_id)
