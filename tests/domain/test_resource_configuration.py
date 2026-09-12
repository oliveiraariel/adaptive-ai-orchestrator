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
        auth_profile="provider:oauth-work",
        thinking="high",
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
    assert configuration.auth_profile == "provider:oauth-work"
    assert configuration.thinking == "high"
    assert configuration.tools == ("git",)
    assert configuration.runtime == "openclaw"
    assert configuration.policy_constraints == ("no-external-write",)


def test_model_auth_profile_and_thinking_are_optional() -> None:
    configuration = ResourceConfiguration(agent="agent-001")

    assert configuration.model is None
    assert configuration.auth_profile is None
    assert configuration.thinking is None


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


def test_blank_optional_auth_profile_is_rejected() -> None:
    with pytest.raises(ResourceConfigurationError):
        ResourceConfiguration(
            agent="agent-001",
            auth_profile="   ",
        )


def test_blank_optional_thinking_is_rejected() -> None:
    with pytest.raises(ResourceConfigurationError):
        ResourceConfiguration(
            agent="agent-001",
            thinking="   ",
        )


def test_blank_optional_runtime_is_rejected() -> None:
    with pytest.raises(ResourceConfigurationError):
        ResourceConfiguration(
            agent="agent-001",
            runtime="   ",
        )
