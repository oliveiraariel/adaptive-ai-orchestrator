"""Named, immutable-at-dispatch execution profiles for Adaptive projects.

Profiles are opt-in.  The original policy is used when no profile is selected.
Only routing hints and scheduler budgets are stored here: never credentials,
permission elevations, side-effect grants or automatic owner takeovers.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import re
import tempfile

from application.model_routing_policy import ModelRoutingPolicy


class ExecutionProfileError(ValueError):
    """An invalid profile or profile registry must fail before dispatch."""


_NAME = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_MODEL = re.compile(r"^[A-Za-z0-9_.:-]+/[A-Za-z0-9_.:/-]+$")
_THINKING = frozenset({"low", "medium", "high", "xhigh"})
_FIELDS = frozenset({
    "name", "planner_model", "planner_thinking", "worker_model",
    "worker_thinking", "concurrency_mode", "max_concurrency",
    "worker_stall_overflow_slots", "direct_takeover",
})


@dataclass(frozen=True)
class ExecutionProfile:
    name: str
    planner_model: str | None = None
    planner_thinking: str | None = None
    worker_model: str | None = None
    worker_thinking: str | None = None
    concurrency_mode: str | None = None
    max_concurrency: int | None = None
    worker_stall_overflow_slots: int | None = None
    direct_takeover: str = "manual"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _NAME.fullmatch(self.name):
            raise ExecutionProfileError("Invalid profile name.")
        for role in ("planner", "worker"):
            model = getattr(self, f"{role}_model")
            thinking = getattr(self, f"{role}_thinking")
            if model is not None and (
                not isinstance(model, str) or not _MODEL.fullmatch(model)
            ):
                raise ExecutionProfileError(f"Invalid {role} model.")
            if thinking is not None and thinking not in _THINKING:
                raise ExecutionProfileError(f"Invalid {role} thinking level.")
            if thinking is not None and model is None:
                raise ExecutionProfileError(
                    f"{role} thinking requires an explicit {role} model."
                )
        if self.concurrency_mode not in (None, "AUTO", "FIXED"):
            raise ExecutionProfileError("Concurrency mode must be AUTO or FIXED.")
        if self.max_concurrency is not None and (
            type(self.max_concurrency) is not int
            or not 1 <= self.max_concurrency <= 32
        ):
            raise ExecutionProfileError("Concurrency limit must be between 1 and 32.")
        if self.worker_stall_overflow_slots is not None and (
            type(self.worker_stall_overflow_slots) is not int
            or not 0 <= self.worker_stall_overflow_slots <= 8
        ):
            raise ExecutionProfileError("Overflow slots must be between 0 and 8.")
        if self.concurrency_mode == "FIXED" and self.worker_stall_overflow_slots not in (None, 0):
            raise ExecutionProfileError("FIXED profiles cannot request overflow slots.")
        if self.direct_takeover != "manual":
            raise ExecutionProfileError(
                "Direct takeover requires a separate per-Work-Unit authorization."
            )

    def to_dict(self) -> dict:
        return {field: getattr(self, field) for field in sorted(_FIELDS)}

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionProfile":
        if not isinstance(data, dict) or set(data) != _FIELDS:
            raise ExecutionProfileError("Profile must contain exactly the declared fields.")
        return cls(**data)

    def routing_policy(self, role: str) -> ModelRoutingPolicy:
        """Return a per-runtime policy. Never mutate process-wide environment."""
        if role not in ("planner", "worker"):
            raise ExecutionProfileError("Unknown execution role.")
        policy = ModelRoutingPolicy.from_env()
        model = getattr(self, f"{role}_model")
        if model is None:
            return policy
        if policy.is_disabled(model):
            raise ExecutionProfileError(f"Profile model is disabled: {model}")
        if model.startswith("openai/") and not policy.economy_auth_profile:
            raise ExecutionProfileError(
                "An OpenAI execution profile requires ADAPTIVE_OPENAI_OAUTH_PROFILE."
            )
        if model.startswith("moonshot/") and not policy.kimi_enabled:
            raise ExecutionProfileError("Moonshot routing is disabled.")
        return replace(
            policy,
            pinned_model=model,
            pinned_thinking=getattr(self, f"{role}_thinking"),
        )


BUILTIN_PROFILES = {
    "original": ExecutionProfile(name="original"),
    "economy-serial": ExecutionProfile(
        name="economy-serial",
        planner_model="openai/gpt-5.6-luna", planner_thinking="medium",
        worker_model="openai/gpt-5.6-luna", worker_thinking="low",
        concurrency_mode="FIXED", max_concurrency=1,
        worker_stall_overflow_slots=0,
    ),
    "quality-parallel": ExecutionProfile(
        name="quality-parallel",
        planner_model="moonshot/kimi-k2.7-code",
        worker_model="moonshot/kimi-k2.7-code",
        concurrency_mode="AUTO", max_concurrency=8,
        worker_stall_overflow_slots=1,
    ),
    "governed-direct": ExecutionProfile(
        name="governed-direct", concurrency_mode="FIXED",
        max_concurrency=1, worker_stall_overflow_slots=0,
    ),
}


def registry_path() -> Path:
    raw = os.environ.get("ADAPTIVE_EXECUTION_PROFILES_FILE")
    return Path(raw).expanduser() if raw else (
        Path.home() / ".config/adaptive-ai-orchestrator/execution-profiles.json"
    )


def custom_profiles(path: Path | None = None) -> dict[str, ExecutionProfile]:
    target = path or registry_path()
    if not target.exists():
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutionProfileError("Cannot read execution profile registry.") from exc
    if not isinstance(data, dict) or set(data) != {"version", "profiles"} or data["version"] != 1 or not isinstance(data["profiles"], dict):
        raise ExecutionProfileError("Unsupported execution profile registry schema.")
    result = {}
    for name, payload in data["profiles"].items():
        profile = ExecutionProfile.from_dict(payload)
        if name != profile.name or name in BUILTIN_PROFILES:
            raise ExecutionProfileError("Invalid or shadowed profile entry.")
        result[name] = profile
    return result


def get_profile(name: str | None, path: Path | None = None) -> ExecutionProfile:
    key = name or "original"
    if key in BUILTIN_PROFILES:
        return BUILTIN_PROFILES[key]
    profiles = custom_profiles(path)
    if key not in profiles:
        raise ExecutionProfileError(f"Unknown execution profile: {key}")
    return profiles[key]


def list_profiles(path: Path | None = None) -> dict[str, ExecutionProfile]:
    return {**BUILTIN_PROFILES, **custom_profiles(path)}


def _write_registry(profiles: dict[str, ExecutionProfile], target: Path) -> None:
    """Atomic replacement with restricted permissions; only metadata, no secrets."""
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".execution-profiles-", dir=target.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({
                "version": 1,
                "profiles": {name: profile.to_dict() for name, profile in sorted(profiles.items())},
            }, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_profile(profile: ExecutionProfile, path: Path | None = None) -> None:
    if profile.name in BUILTIN_PROFILES:
        raise ExecutionProfileError("Built-in profiles cannot be modified.")
    target = path or registry_path()
    profiles = custom_profiles(target)
    profiles[profile.name] = profile
    _write_registry(profiles, target)


def delete_profile(name: str, path: Path | None = None) -> None:
    if name in BUILTIN_PROFILES:
        raise ExecutionProfileError("Built-in profiles cannot be deleted.")
    target = path or registry_path()
    profiles = custom_profiles(target)
    if name not in profiles:
        raise ExecutionProfileError(f"Unknown execution profile: {name}")
    del profiles[name]
    _write_registry(profiles, target)
