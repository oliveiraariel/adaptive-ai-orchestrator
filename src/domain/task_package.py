from dataclasses import dataclass, field
from typing import Tuple
from uuid import uuid4

from domain.api_generation_policy import api_generation_policy_directives
from domain.context_strategy import ContextPolicy
from domain.delegation_context import DelegationContext
from domain.execution_policy import ExecutionPolicy
from domain.resource_configuration import ResourceConfiguration


class TaskPackageError(ValueError):
    """Raised when a TaskPackage invariant is violated."""


@dataclass(frozen=True)
class TaskPackage:
    task_id: str
    work_unit_id: str
    objective: str
    # Standalone packages receive their own correlation root; orchestrated
    # callers pass the shared run id explicitly.
    orchestration_id: str = field(default_factory=lambda: uuid4().hex)
    scope: str = ""
    context: Tuple[str, ...] = field(default_factory=tuple)
    inputs: Tuple[str, ...] = field(default_factory=tuple)
    artifacts: Tuple[str, ...] = field(default_factory=tuple)
    decisions: Tuple[str, ...] = field(default_factory=tuple)
    dependencies: Tuple[str, ...] = field(default_factory=tuple)
    constraints: Tuple[str, ...] = field(default_factory=tuple)
    configuration: ResourceConfiguration | None = None
    expected_output: Tuple[str, ...] = field(default_factory=tuple)
    acceptance_criteria: Tuple[str, ...] = field(default_factory=tuple)
    execution_policy: ExecutionPolicy = field(default_factory=ExecutionPolicy)
    delegation_context: DelegationContext | None = None
    context_policy: ContextPolicy = field(default_factory=ContextPolicy)
    requested_side_effects: Tuple[str, ...] = field(default_factory=tuple)
    request_message_type: str = "work.assignment"
    request_schema_name: str = "task-package"
    result_message_type: str = "worker.result"
    result_schema_name: str = "worker-result"
    result_content_type: str = "text/plain"

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise TaskPackageError("TaskPackage task_id must not be empty.")

        if not self.work_unit_id.strip():
            raise TaskPackageError("TaskPackage work_unit_id must not be empty.")

        if not self.objective.strip():
            raise TaskPackageError("TaskPackage objective must not be empty.")

        if not self.orchestration_id.strip():
            raise TaskPackageError(
                "TaskPackage orchestration_id must not be empty."
            )

        api_directives = api_generation_policy_directives(
            objective=self.objective,
            scope=self.scope,
            context=self.context,
            constraints=self.constraints,
        )
        if api_directives:
            existing_decisions = {item.strip() for item in self.decisions}
            object.__setattr__(
                self,
                "decisions",
                (
                    *self.decisions,
                    *(
                        directive
                        for directive in api_directives
                        if directive.strip() not in existing_decisions
                    ),
                ),
            )

        if self.configuration is None:
            raise TaskPackageError(
                "TaskPackage configuration is required before delegation."
            )

        if not self.expected_output:
            raise TaskPackageError(
                "TaskPackage must declare at least one expected output."
            )

        if not self.acceptance_criteria:
            raise TaskPackageError(
                "TaskPackage must declare at least one acceptance criterion."
            )

        if any(not effect.strip() for effect in self.requested_side_effects):
            raise TaskPackageError("Requested side effects must not contain blanks.")

        for field_name in (
            "request_message_type",
            "request_schema_name",
            "result_message_type",
            "result_schema_name",
            "result_content_type",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise TaskPackageError(f"TaskPackage {field_name} must not be empty.")
        if self.result_content_type not in {"application/json", "text/plain", "text/markdown"}:
            raise TaskPackageError("TaskPackage result_content_type is unsupported.")

        if self.delegation_context is None:
            object.__setattr__(
                self,
                "delegation_context",
                DelegationContext.root(self.task_id),
            )
