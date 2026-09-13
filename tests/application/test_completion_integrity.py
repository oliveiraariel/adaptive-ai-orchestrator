from application.completion_integrity import (
    WorkerBlockerType,
    WorkerCompletionStatus,
    parse_worker_completion,
)


def test_parse_complete_footer() -> None:
    signal = parse_worker_completion(
        """
work done
ADAPTIVE_WORK_STATUS: COMPLETE
ADAPTIVE_BLOCKER_TYPE: NONE
ADAPTIVE_UNMET_CRITERIA: NONE
"""
    )

    assert signal.status is WorkerCompletionStatus.COMPLETE
    assert signal.is_terminal_success is True
    assert signal.is_genuine_blocker is False
    assert signal.unmet_criteria == ()


def test_complete_with_unmet_criteria_is_downgraded_to_partial() -> None:
    signal = parse_worker_completion(
        """
ADAPTIVE_WORK_STATUS: COMPLETE
ADAPTIVE_BLOCKER_TYPE: NONE
ADAPTIVE_UNMET_CRITERIA: update tests; run integration checks
"""
    )

    assert signal.status is WorkerCompletionStatus.PARTIAL
    assert signal.unmet_criteria == ("update tests", "run integration checks")
    assert signal.is_terminal_success is False


def test_genuine_human_blocker_is_classified() -> None:
    signal = parse_worker_completion(
        """
ADAPTIVE_WORK_STATUS: BLOCKED
ADAPTIVE_BLOCKER_TYPE: HUMAN_DECISION
ADAPTIVE_UNMET_CRITERIA: choose irreversible migration policy
"""
    )

    assert signal.status is WorkerCompletionStatus.BLOCKED
    assert signal.blocker_type is WorkerBlockerType.HUMAN_DECISION
    assert signal.is_genuine_blocker is True


def test_unclassified_blocker_is_not_genuine_stop_condition() -> None:
    signal = parse_worker_completion(
        """
ADAPTIVE_WORK_STATUS: BLOCKED
ADAPTIVE_BLOCKER_TYPE: IMPLEMENTATION
ADAPTIVE_UNMET_CRITERIA: add repository dependency
"""
    )

    assert signal.status is WorkerCompletionStatus.BLOCKED
    assert signal.blocker_type is WorkerBlockerType.UNKNOWN
    assert signal.is_genuine_blocker is False


def test_missing_footer_preserves_legacy_unknown_state() -> None:
    signal = parse_worker_completion("legacy worker output")

    assert signal.status is WorkerCompletionStatus.UNKNOWN
    assert signal.structured is False
