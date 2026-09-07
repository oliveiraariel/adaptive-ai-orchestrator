from dataclasses import dataclass, field
from typing import Tuple


class DelegationContextError(ValueError):
    """Raised when delegated execution would violate lineage invariants."""


@dataclass(frozen=True)
class DelegationContext:
    """Runtime-neutral lineage and recursion bound for delegated work."""

    root_task_id: str
    parent_task_id: str | None = None
    depth: int = 0
    max_depth: int = 2
    ancestry: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.root_task_id.strip():
            raise DelegationContextError("root_task_id must not be empty.")
        if self.parent_task_id is not None and not self.parent_task_id.strip():
            raise DelegationContextError(
                "parent_task_id must not be blank when provided."
            )
        if self.depth < 0:
            raise DelegationContextError("Delegation depth must not be negative.")
        if self.max_depth < 0:
            raise DelegationContextError("max_depth must not be negative.")
        if self.depth > self.max_depth:
            raise DelegationContextError(
                "Delegation depth cannot exceed the authorized max_depth."
            )
        if any(not task_id.strip() for task_id in self.ancestry):
            raise DelegationContextError("Delegation ancestry cannot contain blanks.")
        if len(self.ancestry) != len(set(self.ancestry)):
            raise DelegationContextError("Delegation ancestry cannot contain a cycle.")
        if self.root_task_id in self.ancestry[1:]:
            raise DelegationContextError("root_task_id cannot recur in ancestry.")

    @classmethod
    def root(cls, task_id: str, *, max_depth: int = 2) -> "DelegationContext":
        normalized = task_id.strip()
        if not normalized:
            raise DelegationContextError("Root task id must not be empty.")
        return cls(
            root_task_id=normalized,
            depth=0,
            max_depth=max_depth,
            ancestry=(normalized,),
        )

    def child(
        self,
        *,
        parent_task_id: str,
        child_task_id: str,
    ) -> "DelegationContext":
        parent = parent_task_id.strip()
        child = child_task_id.strip()
        if not parent:
            raise DelegationContextError("Parent task id must not be empty.")
        if not child:
            raise DelegationContextError("Child task id must not be empty.")

        expected_parent = self.ancestry[-1] if self.ancestry else self.root_task_id
        if parent != expected_parent:
            raise DelegationContextError(
                "Child delegation parent must match the current lineage tip."
            )
        if child == self.root_task_id or child in self.ancestry:
            raise DelegationContextError("Recursive delegation cycle detected.")

        next_depth = self.depth + 1
        if next_depth > self.max_depth:
            raise DelegationContextError(
                "Delegation would exceed the authorized max_depth."
            )

        return DelegationContext(
            root_task_id=self.root_task_id,
            parent_task_id=parent,
            depth=next_depth,
            max_depth=self.max_depth,
            ancestry=(*self.ancestry, child),
        )
