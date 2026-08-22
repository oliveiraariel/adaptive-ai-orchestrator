from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_final_project_structure_is_present() -> None:
    expected_paths = (
        REPO_ROOT / "specifications" / "orchestrator",
        REPO_ROOT / "docs" / "architecture",
        REPO_ROOT / "docs" / "process",
        REPO_ROOT / "src" / "domain",
        REPO_ROOT / "src" / "application",
        REPO_ROOT / "src" / "infrastructure",
        REPO_ROOT / "tests" / "domain",
        REPO_ROOT / "tests" / "application",
        REPO_ROOT / "tests" / "infrastructure",
        REPO_ROOT / "tests" / "system",
        REPO_ROOT / "tests" / "architecture",
    )

    missing = [str(path) for path in expected_paths if not path.is_dir()]

    assert missing == []


def test_final_validation_artifacts_are_present() -> None:
    expected_files = (
        REPO_ROOT / "tests" / "system" / "test_end_to_end_orchestrator.py",
        REPO_ROOT / "tests" / "system" / "test_evaluation_replanning_vertical_slice.py",
        REPO_ROOT / "tests" / "architecture" / "test_architecture_verification.py",
        REPO_ROOT / "tests" / "architecture" / "test_traceability_verification.py",
        REPO_ROOT / "tests" / "application" / "test_recover_execution.py",
        REPO_ROOT / "scripts" / "validate.py",
    )

    missing = [str(path) for path in expected_files if not path.is_file()]

    assert missing == []


def test_final_operating_model_artifacts_are_documented() -> None:
    architecture = REPO_ROOT / "docs" / "architecture"
    process = REPO_ROOT / "docs" / "process"

    architecture_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in architecture.glob("*.md")
    )
    process_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in process.glob("*.md")
    )

    assert "Orchestrator" in architecture_text
    assert "traceab" in (architecture_text + process_text).lower()
    assert "Specification-Driven Development" in process_text
