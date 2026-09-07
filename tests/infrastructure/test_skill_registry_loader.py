import json

import pytest

from infrastructure.skill_registry_loader import (
    SkillRegistryError,
    load_skill_profiles,
)


def write_registry(tmp_path, skills):
    path = tmp_path / "skills.json"
    path.write_text(
        json.dumps({"schema_version": 1, "skills": skills}),
        encoding="utf-8",
    )
    return path


def test_loads_portable_registry_into_skill_profiles(tmp_path) -> None:
    path = write_registry(
        tmp_path,
        [
            {
                "id": "code-review",
                "purpose": "independent code review",
                "capabilities": ["review.code"],
                "inputs": ["diff", "specification"],
                "outputs": ["verdict"],
                "dependencies": [],
                "compatible_agents": [],
                "compatible_models": [],
                "compatible_runtimes": [],
                "version": "0.1.0",
                "evidence": ["code-review/SKILL.md"],
            }
        ],
    )

    profiles = load_skill_profiles(path)

    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.id.value == "code-review"
    assert profile.capabilities == ("review.code",)
    assert profile.accepts_runtime("openclaw")
    assert profile.accepts_model("any-model")
    assert profile.version == "0.1.0"


def test_rejects_duplicate_skill_ids(tmp_path) -> None:
    entry = {
        "id": "testing",
        "purpose": "test software",
        "capabilities": ["testing.software"],
    }
    path = write_registry(tmp_path, [entry, entry])

    with pytest.raises(SkillRegistryError, match="Duplicate skill id"):
        load_skill_profiles(path)


def test_rejects_skill_without_capability(tmp_path) -> None:
    path = write_registry(
        tmp_path,
        [{"id": "empty", "purpose": "does nothing", "capabilities": []}],
    )

    with pytest.raises(SkillRegistryError, match="must provide a capability"):
        load_skill_profiles(path)


def test_rejects_runtime_specific_field_with_wrong_shape(tmp_path) -> None:
    path = write_registry(
        tmp_path,
        [
            {
                "id": "testing",
                "purpose": "test software",
                "capabilities": ["testing.software"],
                "compatible_runtimes": "openclaw",
            }
        ],
    )

    with pytest.raises(SkillRegistryError, match="list of strings"):
        load_skill_profiles(path)
