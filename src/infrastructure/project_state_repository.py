from domain.project import Project, ProjectId


class ProjectStateRepository:
    """Minimal repository contract for Project state."""

    def save(self, project: Project) -> None:
        raise NotImplementedError

    def get(self, project_id: ProjectId) -> Project | None:
        raise NotImplementedError


class InMemoryProjectStateRepository(ProjectStateRepository):
    """In-memory adapter used by the initial implementation slices."""

    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}

    def save(self, project: Project) -> None:
        self._projects[project.id.value] = project

    def get(self, project_id: ProjectId) -> Project | None:
        return self._projects.get(project_id.value)
