from typing import Protocol

from domain.execution_claim import ExecutionClaim


class ClaimRegistry(Protocol):
    """Concurrency-control seam for exclusive Work Unit ownership."""

    def acquire(self, *, work_unit_id: str, claimant_id: str) -> ExecutionClaim | None:
        """Acquire exclusive ownership or return None when already claimed."""
        ...

    def get(self, work_unit_id: str) -> ExecutionClaim | None:
        """Return the active claim for a Work Unit, when any."""
        ...

    def bind_execution(
        self,
        claim: ExecutionClaim,
        *,
        execution_id: str,
    ) -> ExecutionClaim:
        """Associate an acquired claim with the accepted runtime execution."""
        ...

    def release(self, claim: ExecutionClaim) -> None:
        """Release a claim when execution did not start or has completed."""
        ...
