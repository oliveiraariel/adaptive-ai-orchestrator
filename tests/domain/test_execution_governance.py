import pytest

from domain.context_strategy import (
    ContextPolicy,
    ContextPolicyError,
    ContextStrategy,
)
from domain.delegation_context import (
    DelegationContext,
    DelegationContextError,
)
from domain.execution_policy import (
    AutonomyClass,
    ExecutionPolicy,
    PolicyDecision,
)


def test_autonomous_read_only_policy_allows_execution() -> None:
    policy = ExecutionPolicy()

    assert policy.decide(human_approved=False) is PolicyDecision.ALLOW


def test_human_approval_policy_blocks_until_approved() -> None:
    policy = ExecutionPolicy(autonomy=AutonomyClass.HUMAN_APPROVAL_REQUIRED)

    assert policy.decide(human_approved=False) is PolicyDecision.REQUIRE_HUMAN_APPROVAL
    assert policy.decide(human_approved=True) is PolicyDecision.ALLOW


def test_human_execution_and_forbidden_work_cannot_be_agent_delegated() -> None:
    human = ExecutionPolicy(autonomy=AutonomyClass.HUMAN_EXECUTION_REQUIRED)
    forbidden = ExecutionPolicy(autonomy=AutonomyClass.FORBIDDEN)

    assert human.decide(human_approved=True) is PolicyDecision.REQUIRE_HUMAN_EXECUTION
    assert forbidden.decide(human_approved=True) is PolicyDecision.DENY


def test_unapproved_side_effect_or_denied_tool_is_denied() -> None:
    policy = ExecutionPolicy(
        allowed_side_effects=("write-worktree",),
        denied_tools=("production-shell",),
    )

    assert (
        policy.decide(
            human_approved=True,
            requested_side_effects=("push-production",),
        )
        is PolicyDecision.DENY
    )
    assert (
        policy.decide(
            human_approved=True,
            requested_tools=("production-shell",),
        )
        is PolicyDecision.DENY
    )


def test_autonomous_with_review_declares_independent_review_requirement() -> None:
    policy = ExecutionPolicy(autonomy=AutonomyClass.AUTONOMOUS_WITH_REVIEW)

    assert policy.independent_review_required is True
    assert policy.decide(human_approved=False) is PolicyDecision.ALLOW


def test_delegation_lineage_is_bounded_and_cycle_safe() -> None:
    root = DelegationContext.root("task-root", max_depth=2)
    child = root.child(parent_task_id="task-root", child_task_id="task-child")
    grandchild = child.child(
        parent_task_id="task-child",
        child_task_id="task-grandchild",
    )

    assert child.depth == 1
    assert grandchild.depth == 2
    assert grandchild.ancestry == (
        "task-root",
        "task-child",
        "task-grandchild",
    )

    with pytest.raises(DelegationContextError):
        grandchild.child(
            parent_task_id="task-grandchild",
            child_task_id="task-too-deep",
        )

    with pytest.raises(DelegationContextError):
        child.child(parent_task_id="task-child", child_task_id="task-root")


def test_delegation_child_must_continue_current_lineage_tip() -> None:
    root = DelegationContext.root("task-root")

    with pytest.raises(DelegationContextError):
        root.child(parent_task_id="wrong-parent", child_task_id="task-child")


def test_pointer_context_requires_pointer() -> None:
    with pytest.raises(ContextPolicyError):
        ContextPolicy(strategy=ContextStrategy.POINTERS)


def test_pointer_context_can_transfer_references_without_inline_copy() -> None:
    policy = ContextPolicy(
        strategy=ContextStrategy.POINTERS,
        pointers=("specs/feature.md", "docs/adr/0001.md"),
    )

    assert policy.strategy is ContextStrategy.POINTERS
    assert policy.pointers == ("specs/feature.md", "docs/adr/0001.md")


def test_sensitive_context_requires_explicit_redaction() -> None:
    with pytest.raises(ContextPolicyError):
        ContextPolicy(contains_sensitive_data=True)

    policy = ContextPolicy(
        strategy=ContextStrategy.HYBRID,
        pointers=("docs/context.md",),
        contains_sensitive_data=True,
        redaction_applied=True,
    )

    assert policy.redaction_applied is True
