import pytest

from domain.dependency import (
    Dependency,
    DependencyError,
    DependencyStatus,
    DependencyType,
)


def test_dependency_starts_blocked_when_required() -> None:
    dependency = Dependency(
        source_id="wu-001",
        target_id="wu-002",
    )

    assert dependency.status is DependencyStatus.BLOCKED
    assert dependency.is_blocking


def test_dependency_can_be_satisfied() -> None:
    dependency = Dependency(
        source_id="wu-001",
        target_id="wu-002",
    )

    dependency.satisfy()

    assert dependency.is_satisfied
    assert not dependency.is_blocking


def test_dependency_can_be_blocked_again() -> None:
    dependency = Dependency(
        source_id="wu-001",
        target_id="wu-002",
    )
    dependency.satisfy()

    dependency.block()

    assert dependency.status is DependencyStatus.BLOCKED
    assert dependency.is_blocking


def test_optional_satisfied_dependency_is_not_blocking() -> None:
    dependency = Dependency(
        source_id="wu-001",
        target_id="wu-002",
        required=False,
    )

    assert not dependency.is_blocking


def test_completion_type_is_default() -> None:
    dependency = Dependency(
        source_id="wu-001",
        target_id="wu-002",
    )

    assert dependency.type is DependencyType.COMPLETION


def test_self_dependency_is_rejected() -> None:
    with pytest.raises(DependencyError):
        Dependency(
            source_id="wu-001",
            target_id="wu-001",
        )


def test_empty_source_is_rejected() -> None:
    with pytest.raises(DependencyError):
        Dependency(
            source_id="",
            target_id="wu-002",
        )


def test_empty_target_is_rejected() -> None:
    with pytest.raises(DependencyError):
        Dependency(
            source_id="wu-001",
            target_id="",
        )
