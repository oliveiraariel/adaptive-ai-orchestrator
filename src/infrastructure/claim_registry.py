from uuid import uuid4

from application.claim_registry import ClaimRegistry
from domain.execution_claim import ExecutionClaim, ExecutionClaimError


class InMemoryClaimRegistry(ClaimRegistry):
    """Process-local claim registry for tests and single-process execution."""

    def __init__(self) -> None:
        self._claims: dict[str, ExecutionClaim] = {}

    def acquire(self, *, work_unit_id: str, claimant_id: str) -> ExecutionClaim | None:
        work_unit = work_unit_id.strip()
        claimant = claimant_id.strip()
        if not work_unit:
            raise ExecutionClaimError("work_unit_id must not be empty.")
        if not claimant:
            raise ExecutionClaimError("claimant_id must not be empty.")
        if work_unit in self._claims:
            return None

        claim = ExecutionClaim(
            claim_id=f"claim:{uuid4()}",
            work_unit_id=work_unit,
            claimant_id=claimant,
        )
        self._claims[work_unit] = claim
        return claim

    def get(self, work_unit_id: str) -> ExecutionClaim | None:
        return self._claims.get(work_unit_id)

    def bind_execution(
        self,
        claim: ExecutionClaim,
        *,
        execution_id: str,
    ) -> ExecutionClaim:
        current = self._claims.get(claim.work_unit_id)
        if current is None or current.claim_id != claim.claim_id:
            raise ExecutionClaimError("Cannot bind a claim that is not active.")

        bound = current.bind_execution(execution_id)
        self._claims[claim.work_unit_id] = bound
        return bound

    def release(self, claim: ExecutionClaim) -> None:
        current = self._claims.get(claim.work_unit_id)
        if current is None:
            return
        if current.claim_id != claim.claim_id:
            raise ExecutionClaimError(
                "Cannot release a Work Unit owned by a different claim."
            )
        del self._claims[claim.work_unit_id]
