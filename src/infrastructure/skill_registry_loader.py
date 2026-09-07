from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from domain.skill_profile import SkillId, SkillProfile


class SkillRegistryError(ValueError):
    """Raised when an external portable skill registry is invalid."""


def _tuple_of_strings(entry: dict[str, Any], field: str) -> tuple[str, ...]:
    value = entry.get(field, [])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SkillRegistryError(f"Skill field '{field}' must be a list of strings.")
    return tuple(value)


def load_skill_profiles(path: str | Path) -> tuple[SkillProfile, ...]:
    """Load a runtime-neutral skill registry into domain SkillProfile objects.

    The registry contract intentionally mirrors SkillProfile and carries no
    provider-specific execution mechanics. Runtime adapters remain responsible
    for locating and invoking the actual skill implementation.
    """

    registry_path = Path(path)
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SkillRegistryError(f"Cannot load skill registry: {exc}") from exc

    if payload.get("schema_version") != 1:
        raise SkillRegistryError("Unsupported skill registry schema_version.")

    entries = payload.get("skills")
    if not isinstance(entries, list):
        raise SkillRegistryError("Skill registry must contain a skills list.")

    profiles: list[SkillProfile] = []
    seen_ids: set[str] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            raise SkillRegistryError("Each skill registry entry must be an object.")

        skill_id = entry.get("id")
        purpose = entry.get("purpose")
        version = entry.get("version", "1.0")

        if not isinstance(skill_id, str) or not skill_id.strip():
            raise SkillRegistryError("Each skill registry entry requires a non-empty id.")
        if skill_id in seen_ids:
            raise SkillRegistryError(f"Duplicate skill id '{skill_id}'.")
        if not isinstance(purpose, str) or not purpose.strip():
            raise SkillRegistryError(f"Skill '{skill_id}' requires a non-empty purpose.")
        if not isinstance(version, str) or not version.strip():
            raise SkillRegistryError(f"Skill '{skill_id}' requires a non-empty version.")

        capabilities = _tuple_of_strings(entry, "capabilities")
        if not capabilities:
            raise SkillRegistryError(f"Skill '{skill_id}' must provide a capability.")

        profile = SkillProfile(
            id=SkillId(skill_id),
            purpose=purpose,
            capabilities=capabilities,
            inputs=_tuple_of_strings(entry, "inputs"),
            outputs=_tuple_of_strings(entry, "outputs"),
            dependencies=_tuple_of_strings(entry, "dependencies"),
            compatible_agents=_tuple_of_strings(entry, "compatible_agents"),
            compatible_models=_tuple_of_strings(entry, "compatible_models"),
            compatible_runtimes=_tuple_of_strings(entry, "compatible_runtimes"),
            version=version,
            evidence=_tuple_of_strings(entry, "evidence"),
        )
        profiles.append(profile)
        seen_ids.add(skill_id)

    return tuple(profiles)
