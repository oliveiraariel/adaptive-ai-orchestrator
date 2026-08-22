import pytest

from domain.result_package import (
    ResultPackage,
    ResultPackageError,
    ResultPackageStatus,
)


def test_result_package_requires_task_id() -> None:
    with pytest.raises(ResultPackageError):
        ResultPackage(
            task_id="",
            status=ResultPackageStatus.FAILED,
        )


def test_succeeded_result_requires_result() -> None:
    with pytest.raises(ResultPackageError):
        ResultPackage(
            task_id="task-001",
            status=ResultPackageStatus.SUCCEEDED,
        )


def test_partial_result_requires_result_or_artifact() -> None:
    with pytest.raises(ResultPackageError):
        ResultPackage(
            task_id="task-001",
            status=ResultPackageStatus.PARTIAL,
        )


def test_failed_result_can_exist_without_result_body() -> None:
    package = ResultPackage(
        task_id="task-001",
        status=ResultPackageStatus.FAILED,
        discovered_issues=("runtime-error",),
    )

    assert package.status is ResultPackageStatus.FAILED
    assert package.result is None
    assert package.discovered_issues == ("runtime-error",)


def test_partial_result_can_be_supported_by_artifacts() -> None:
    package = ResultPackage(
        task_id="task-001",
        status=ResultPackageStatus.PARTIAL,
        artifacts=("partial-output.txt",),
    )

    assert package.status is ResultPackageStatus.PARTIAL
    assert package.artifacts == ("partial-output.txt",)


def test_result_package_preserves_execution_findings() -> None:
    package = ResultPackage(
        task_id="task-001",
        status=ResultPackageStatus.SUCCEEDED,
        result={"output": "done"},
        artifacts=("implementation.diff",),
        decisions=("decision-001",),
        assumptions=("assumption-001",),
        evidence=("test-report-001",),
        discovered_dependencies=("wu-002",),
        discovered_issues=("minor-warning",),
        uncertainty=("runtime-latency-estimate",),
        recommendations=("review-result",),
        metadata=("runtime=openclaw",),
    )

    assert package.result == {"output": "done"}
    assert package.artifacts == ("implementation.diff",)
    assert package.decisions == ("decision-001",)
    assert package.assumptions == ("assumption-001",)
    assert package.evidence == ("test-report-001",)
    assert package.discovered_dependencies == ("wu-002",)
    assert package.discovered_issues == ("minor-warning",)
    assert package.uncertainty == ("runtime-latency-estimate",)
    assert package.recommendations == ("review-result",)
    assert package.metadata == ("runtime=openclaw",)
