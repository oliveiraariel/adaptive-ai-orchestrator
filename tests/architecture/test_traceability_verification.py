from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_ROOT = REPO_ROOT / "specifications" / "orchestrator"
DOC_ROOT = REPO_ROOT / "docs"
SRC_ROOT = REPO_ROOT / "src"
TEST_ROOT = REPO_ROOT / "tests"


def _read_all_markdown(root: Path) -> str:
    if not root.exists():
        return ""

    return "\n".join(
        file.read_text(encoding="utf-8")
        for file in root.rglob("*.md")
    )


def test_orchestrator_requirements_document_exists() -> None:
    requirements = SPEC_ROOT / "ORCHESTRATOR-REQUIREMENTS.md"

    assert requirements.exists()


def test_project_definition_document_exists() -> None:
    project_definition = SPEC_ROOT / "PROJECT-DEFINITION.md"

    assert project_definition.exists()


def test_core_domain_concepts_have_implementation_files() -> None:
    expected = {
        "Project": SRC_ROOT / "domain" / "project.py",
        "WorkUnit": SRC_ROOT / "domain" / "work_unit.py",
        "Dependency": SRC_ROOT / "domain" / "dependency.py",
        "Plan": SRC_ROOT / "domain" / "plan.py",
        "AgentProfile": SRC_ROOT / "domain" / "agent_profile.py",
        "SkillProfile": SRC_ROOT / "domain" / "skill_profile.py",
        "ModelProfile": SRC_ROOT / "domain" / "model_profile.py",
        "ResourceConfiguration": SRC_ROOT / "domain" / "resource_configuration.py",
        "TaskPackage": SRC_ROOT / "domain" / "task_package.py",
        "ResultPackage": SRC_ROOT / "domain" / "result_package.py",
        "Evaluation": SRC_ROOT / "domain" / "evaluation.py",
        "LearningCandidate": SRC_ROOT / "domain" / "learning_candidate.py",
    }

    missing = [
        concept
        for concept, path in expected.items()
        if not path.exists()
    ]

    assert missing == []


def test_core_use_cases_have_implementation_files() -> None:
    expected = {
        "PlanWork": SRC_ROOT / "application" / "plan_work.py",
        "SelectResource": SRC_ROOT / "application" / "resource_selection.py",
        "DelegateWork": SRC_ROOT / "application" / "delegate_work.py",
        "EvaluateResult": SRC_ROOT / "application" / "evaluate_result.py",
        "ReplanProject": SRC_ROOT / "application" / "replan_project.py",
    }

    missing = [
        use_case
        for use_case, path in expected.items()
        if not path.exists()
    ]

    assert missing == []


def test_runtime_and_catalog_boundaries_have_implementations() -> None:
    expected = (
        SRC_ROOT / "application" / "agent_runtime.py",
        SRC_ROOT / "infrastructure" / "openclaw_adapter.py",
        SRC_ROOT / "infrastructure" / "catalogs.py",
    )

    assert all(path.exists() for path in expected)


def test_completed_work_units_have_traceability_records() -> None:
    architecture_docs = _read_all_markdown(DOC_ROOT / "architecture")

    work_unit_ids = range(1, 36)

    missing_records = [
        f"WU-{number:03d}"
        for number in work_unit_ids
        if f"WU-{number:03d}" not in architecture_docs
    ]

    # This check intentionally reports the current implementation boundary.
    # WU-035 itself must not require future closure records to exist yet.
    allowed_missing = {
        "WU-034",
        "WU-035",
    }

    assert set(missing_records).issubset(allowed_missing)


def test_implementation_tests_exist_for_completed_capability_modules() -> None:
    expected_test_files = (
        TEST_ROOT / "domain" / "test_project.py",
        TEST_ROOT / "domain" / "test_work_unit.py",
        TEST_ROOT / "domain" / "test_dependency.py",
        TEST_ROOT / "domain" / "test_plan.py",
        TEST_ROOT / "application" / "test_plan_work.py",
        TEST_ROOT / "application" / "test_resource_selection.py",
        TEST_ROOT / "application" / "test_delegate_work.py",
        TEST_ROOT / "application" / "test_evaluate_result.py",
        TEST_ROOT / "application" / "test_replan_project.py",
        TEST_ROOT / "system" / "test_end_to_end_orchestrator.py",
        TEST_ROOT / "architecture" / "test_architecture_verification.py",
    )

    missing = [str(path.relative_to(REPO_ROOT)) for path in expected_test_files if not path.exists()]

    assert missing == []


def test_traceability_document_contains_verification_language() -> None:
    architecture_docs = _read_all_markdown(DOC_ROOT / "architecture")

    assert re.search(
        r"traceab",
        architecture_docs,
        re.IGNORECASE,
    )
