import pytest

from domain.resource_configuration import (
    ResourceConfiguration,
    ResourceConfigurationError,
)


def make_configuration() -> ResourceConfiguration:
    return ResourceConfiguration(
        agent="agent-001",
        skills=("tdd", "code-review"),
        model="model-001",
        provider="provider-001",
        tools=("git",),
        runtime="openclaw",
        policy_constraints=("no-external-write",),
    )


def test_configuration_requires_agent() -> None:
    with pytest.raises(ResourceConfigurationError):
        ResourceConfiguration(agent="")


def test_configuration_preserves_declared_resources() -> None:
    configuration = make_configuration()

    assert configuration.agent == "agent-001"
    assert configuration.skills == ("tdd", "code-review")
    assert configuration.model == "model-001"
    assert configuration.provider == "provider-001"
    assert configuration.tools == ("git",)
    assert configuration.runtime == "openclaw"
    assert configuration.policy_constraints == ("no-external-write",)


def test_model_is_optional() -> None:
    configuration = ResourceConfiguration(agent="agent-001")

    assert configuration.model is None


def test_blank_optional_model_is_rejected() -> None:
    with pytest.raises(ResourceConfigurationError):
        ResourceConfiguration(
            agent="agent-001",
            model="   ",
        )


def test_blank_optional_provider_is_rejected() -> None:
    with pytest.raises(ResourceConfigurationError):
        ResourceConfiguration(
            agent="agent-001",
            provider="   ",
        )


def test_blank_optional_runtime_is_rejected() -> None:
    with pytest.raises(ResourceConfigurationError):
        ResourceConfiguration(
            agent="agent-001",
            runtime="   ",
        )
