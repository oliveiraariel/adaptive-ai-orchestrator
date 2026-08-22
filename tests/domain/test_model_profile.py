import pytest

from domain.model_profile import ModelId, ModelProfile, ModelProfileError


def make_model() -> ModelProfile:
    return ModelProfile(
        id=ModelId("model-001"),
        name="Example Model",
        version="1.0",
        provider="example-provider",
        capabilities=("reasoning", "coding"),
        context=128000,
        cost="medium",
        latency="low",
        availability="available",
        restrictions=("no-local-execution",),
        evidence=("model-catalog-001",),
    )


def test_model_requires_id() -> None:
    with pytest.raises(ModelProfileError):
        ModelId("")


def test_model_requires_name() -> None:
    with pytest.raises(ModelProfileError):
        ModelProfile(
            id=ModelId("model-001"),
            name="",
            version="1.0",
            provider="provider",
        )


def test_model_requires_version() -> None:
    with pytest.raises(ModelProfileError):
        ModelProfile(
            id=ModelId("model-001"),
            name="Example",
            version="",
            provider="provider",
        )


def test_model_requires_provider() -> None:
    with pytest.raises(ModelProfileError):
        ModelProfile(
            id=ModelId("model-001"),
            name="Example",
            version="1.0",
            provider="",
        )


def test_negative_context_is_rejected() -> None:
    with pytest.raises(ModelProfileError):
        ModelProfile(
            id=ModelId("model-001"),
            name="Example",
            version="1.0",
            provider="provider",
            context=-1,
        )


def test_model_profile_preserves_declared_fields() -> None:
    model = make_model()

    assert model.name == "Example Model"
    assert model.version == "1.0"
    assert model.provider == "example-provider"
    assert model.capabilities == ("reasoning", "coding")
    assert model.context == 128000
    assert model.cost == "medium"
    assert model.latency == "low"
    assert model.availability == "available"
    assert model.restrictions == ("no-local-execution",)
    assert model.evidence == ("model-catalog-001",)


def test_model_reports_supported_capabilities() -> None:
    model = make_model()

    assert model.supports_capability("reasoning")
    assert model.supports_capability("coding")
    assert not model.supports_capability("vision")


def test_model_reports_restrictions() -> None:
    model = make_model()

    assert model.has_restriction("no-local-execution")
    assert not model.has_restriction("requires-gpu")
