from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from domain.work_unit import WorkUnitKind


class ProjectExecutionPlanError(ValueError):
    """Raised when a generated project execution plan is not safe to execute."""


@dataclass(frozen=True)
class PlannedDependency:
    source_id: str
    target_id: str
    required: bool = True
    condition: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.target_id.strip():
            raise ProjectExecutionPlanError(
                "Planned dependency endpoints must not be blank."
            )
        if self.source_id == self.target_id:
            raise ProjectExecutionPlanError(
                "A planned dependency cannot target itself."
            )


@dataclass(frozen=True)
class PlannedWorkUnit:
    id: str
    objective: str
    role: str = "worker"
    scope: str = ""
    kind: WorkUnitKind = WorkUnitKind.EXECUTION
    required_capabilities: Tuple[str, ...] = field(default_factory=tuple)
    requested_skills: Tuple[str, ...] = field(default_factory=tuple)
    tools: Tuple[str, ...] = field(default_factory=tuple)
    inputs: Tuple[str, ...] = field(default_factory=tuple)
    expected_output: Tuple[str, ...] = ("agent response",)
    acceptance_criteria: Tuple[str, ...] = ("runtime-completed",)
    requested_side_effects: Tuple[str, ...] = field(default_factory=tuple)
    write_paths: Tuple[str, ...] = field(default_factory=tuple)
    priority: int = 0
    criticality: int = 0
    parallel_safe: bool = True

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ProjectExecutionPlanError("Planned Work Unit id must not be blank.")
        if not self.objective.strip():
            raise ProjectExecutionPlanError(
                f"Planned Work Unit '{self.id}' objective must not be blank."
            )
        if not self.role.strip():
            raise ProjectExecutionPlanError(
                f"Planned Work Unit '{self.id}' role must not be blank."
            )
        if not self.expected_output:
            raise ProjectExecutionPlanError(
                f"Planned Work Unit '{self.id}' must declare expected output."
            )
        if not self.acceptance_criteria:
            raise ProjectExecutionPlanError(
                f"Planned Work Unit '{self.id}' must declare acceptance criteria."
            )
        if self.priority < 0 or self.criticality < 0:
            raise ProjectExecutionPlanError(
                f"Planned Work Unit '{self.id}' priority/criticality must be non-negative."
            )
        string_fields = (
            self.required_capabilities,
            self.requested_skills,
            self.tools,
            self.inputs,
            self.expected_output,
            self.acceptance_criteria,
            self.requested_side_effects,
            self.write_paths,
        )
        if any(not item.strip() for items in string_fields for item in items):
            raise ProjectExecutionPlanError(
                f"Planned Work Unit '{self.id}' contains a blank list item."
            )

        if "filesystem.write" in self.requested_side_effects and not self.write_paths:
            raise ProjectExecutionPlanError(
                f"Planned Work Unit '{self.id}' requests filesystem.write but "
                "declares no repository-relative write_paths."
            )

        for path in self.write_paths:
            self._validate_write_path(path)

    def _validate_write_path(self, path: str) -> None:
        normalized = path.strip().replace("\\", "/")
        if normalized.startswith("/") or normalized.startswith("~"):
            raise ProjectExecutionPlanError(
                f"Planned Work Unit '{self.id}' write path '{path}' must be "
                "repository-relative."
            )
        if len(normalized) >= 2 and normalized[1] == ":" and normalized[0].isalpha():
            raise ProjectExecutionPlanError(
                f"Planned Work Unit '{self.id}' write path '{path}' must not "
                "contain an absolute drive prefix."
            )
        parts = tuple(part for part in normalized.split("/") if part not in {"", "."})
        if ".." in parts:
            raise ProjectExecutionPlanError(
                f"Planned Work Unit '{self.id}' write path '{path}' must not "
                "escape the repository with '..'."
            )
        if any(character in normalized for character in ("*", "?", "[", "]")):
            raise ProjectExecutionPlanError(
                f"Planned Work Unit '{self.id}' write path '{path}' must be a "
                "literal path prefix, not a glob."
            )


@dataclass(frozen=True)
class ProjectExecutionPlan:
    summary: str
    work_units: Tuple[PlannedWorkUnit, ...]
    dependencies: Tuple[PlannedDependency, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise ProjectExecutionPlanError("Project execution plan summary must not be blank.")
        if not self.work_units:
            raise ProjectExecutionPlanError(
                "Project execution plan must contain at least one Work Unit."
            )

        ids = [item.id for item in self.work_units]
        if len(ids) != len(set(ids)):
            raise ProjectExecutionPlanError("Planned Work Unit ids must be unique.")

        known = set(ids)
        for dependency in self.dependencies:
            if dependency.source_id not in known:
                raise ProjectExecutionPlanError(
                    f"Unknown dependency source '{dependency.source_id}'."
                )
            if dependency.target_id not in known:
                raise ProjectExecutionPlanError(
                    f"Unknown dependency target '{dependency.target_id}'."
                )

        self._ensure_required_dependencies_are_acyclic(known)

    def _ensure_required_dependencies_are_acyclic(self, ids: set[str]) -> None:
        outgoing = {work_unit_id: [] for work_unit_id in ids}
        indegree = {work_unit_id: 0 for work_unit_id in ids}

        for dependency in self.dependencies:
            if not dependency.required:
                continue
            outgoing[dependency.source_id].append(dependency.target_id)
            indegree[dependency.target_id] += 1

        frontier = [item for item, degree in indegree.items() if degree == 0]
        visited = 0
        while frontier:
            current = frontier.pop()
            visited += 1
            for target in outgoing[current]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    frontier.append(target)

        if visited != len(ids):
            raise ProjectExecutionPlanError(
                "Required project Work Unit dependency graph must be acyclic."
            )
