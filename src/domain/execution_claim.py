from dataclasses import dataclass


class ExecutionClaimError(ValueError):
    """Raised when execution-claim invariants are violated."""


@dataclass(frozen=True)
class ExecutionClaim:
    """Exclusive ownership of one Work Unit during delegated execution."""

    claim_id: str
    work_unit_id: str
    claimant_id: str
    execution_id: str | None = None

    def __post_init__(self) -> None:
        if not self.claim_id.strip():
            raise ExecutionClaimError("claim_id must not be empty.")
        if not self.work_unit_id.strip():
            raise ExecutionClaimError("work_unit_id must not be empty.")
        if not self.claimant_id.strip():
            raise ExecutionClaimError("claimant_id must not be empty.")
        if self.execution_id is not None and not self.execution_id.strip():
            raise ExecutionClaimError(
                "execution_id must not be blank when provided."
            )

    def bind_execution(self, execution_id: str) -> "ExecutionClaim":
        normalized = execution_id.strip()
        if not normalized:
            raise ExecutionClaimError("execution_id must not be empty.")
        if self.execution_id is not None and self.execution_id != normalized:
            raise ExecutionClaimError(
                "A claim already bound to one execution cannot be rebound."
            )
        return ExecutionClaim(
            claim_id=self.claim_id,
            work_unit_id=self.work_unit_id,
            claimant_id=self.claimant_id,
            execution_id=normalized,
        )
