from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
DOMAIN_ROOT = SRC_ROOT / "domain"
APPLICATION_ROOT = SRC_ROOT / "application"
INFRASTRUCTURE_ROOT = SRC_ROOT / "infrastructure"


def _imports(path: Path) -> str:
    if not path.exists():
        return ""
    return "\n".join(
        file.read_text(encoding="utf-8")
        for file in path.rglob("*.py")
    )


def test_expected_architecture_directories_exist() -> None:
    assert DOMAIN_ROOT.is_dir()
    assert APPLICATION_ROOT.is_dir()
    assert INFRASTRUCTURE_ROOT.is_dir()


def test_domain_does_not_import_application_or_infrastructure() -> None:
    domain_source = _imports(DOMAIN_ROOT)

    assert "from application" not in domain_source
    assert "import application" not in domain_source
    assert "from infrastructure" not in domain_source
    assert "import infrastructure" not in domain_source


def test_application_does_not_import_concrete_openclaw_adapter() -> None:
    application_source = _imports(APPLICATION_ROOT)

    assert "from infrastructure.openclaw_adapter" not in application_source
    assert "import infrastructure.openclaw_adapter" not in application_source


def test_domain_does_not_reference_runtime_specific_symbols() -> None:
    domain_source = _imports(DOMAIN_ROOT)

    forbidden = (
        "OpenClawClient",
        "OpenClawAdapter",
        "Hermes",
        "boto3",
        "sqlalchemy",
        "psycopg",
    )

    for symbol in forbidden:
        assert symbol not in domain_source


def test_runtime_adapter_isolated_in_infrastructure() -> None:
    adapter = INFRASTRUCTURE_ROOT / "openclaw_adapter.py"

    assert adapter.exists()

    source = adapter.read_text(encoding="utf-8")

    assert "AgentRuntime" in source
    assert "OpenClawClient" in source


def test_application_uses_internal_runtime_port() -> None:
    delegate = APPLICATION_ROOT / "delegate_work.py"

    assert delegate.exists()

    source = delegate.read_text(encoding="utf-8")

    assert "AgentRuntime" in source
    assert "OpenClawAdapter" not in source


def test_application_and_domain_do_not_depend_on_external_sdk_contracts() -> None:
    internal_source = _imports(DOMAIN_ROOT) + "\n" + _imports(APPLICATION_ROOT)

    forbidden = (
        "requests",
        "httpx",
        "openai",
        "anthropic",
        "mcp",
    )

    for module_name in forbidden:
        assert f"import {module_name}" not in internal_source
        assert f"from {module_name}" not in internal_source
