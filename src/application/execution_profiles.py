"""Named, immutable-at-dispatch execution profiles for Adaptive projects.

Named profiles never mutate their definitions when selected. Operator policy
may choose a durable default for NEW projects; an explicit per-run override is
authorized separately. Existing project snapshots remain authoritative.
Never store credentials, side-effect grants, or automatic owner takeovers.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

from application.model_routing_policy import ModelRoutingPolicy


class ExecutionProfileError(ValueError):
    """An invalid profile or profile registry must fail before dispatch."""


_NAME = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_MODEL = re.compile(r"^[A-Za-z0-9_.:-]+/[A-Za-z0-9_.:/-]+$")
_THINKING = frozenset({"low", "medium", "high", "xhigh"})
_BASE_FIELDS = frozenset({
    "name", "planner_model", "planner_thinking", "worker_model",
    "worker_thinking", "concurrency_mode", "max_concurrency",
    "worker_stall_overflow_slots", "direct_takeover",
})
_EXTRA_FIELDS = frozenset({
    "planner_fallback_models", "worker_fallback_models",
    "quality_direct_fallback", "direct_owner_mode",
})
_FIELDS = _BASE_FIELDS | _EXTRA_FIELDS


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
    planner_fallback_models: tuple[str, ...] = ()
    worker_fallback_models: tuple[str, ...] = ()
    quality_direct_fallback: bool = False
    direct_owner_mode: bool = False

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
        for role in ("planner", "worker"):
            fallbacks = getattr(self, f"{role}_fallback_models")
            if not isinstance(fallbacks, (list, tuple)) or any(
                not isinstance(value, str) or not _MODEL.fullmatch(value)
                for value in fallbacks
            ):
                raise ExecutionProfileError(f"Invalid {role} fallback models.")
            if len(set(fallbacks)) != len(fallbacks):
                raise ExecutionProfileError(f"Duplicate {role} fallback models.")
            if getattr(self, f"{role}_model") in fallbacks:
                raise ExecutionProfileError("Primary model cannot also be its fallback.")
        if type(self.quality_direct_fallback) is not bool or type(self.direct_owner_mode) is not bool:
            raise ExecutionProfileError("Fallback and direct execution flags must be boolean.")
        if self.direct_owner_mode and self.quality_direct_fallback:
            raise ExecutionProfileError("Direct-owner mode cannot recursively fall back to itself.")
        if self.direct_owner_mode and (
            self.planner_model != self.worker_model
            or self.planner_thinking != self.worker_thinking
            or self.planner_fallback_models or self.worker_fallback_models
        ):
            raise ExecutionProfileError(
                "Direct-owner execution must retain the coordinator model, thinking and no LLM swap."
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
        if not isinstance(data, dict) or not _BASE_FIELDS.issubset(data) or not set(data).issubset(_FIELDS):
            raise ExecutionProfileError("Profile is missing required fields or has unknown fields.")
        normalized = dict(data)
        for field in ("planner_fallback_models", "worker_fallback_models"):
            if field in normalized and isinstance(normalized[field], list):
                normalized[field] = tuple(normalized[field])
        return cls(**normalized)

    def routing_policy(self, role: str) -> ModelRoutingPolicy:
        """Return a per-runtime policy. Never mutate process-wide environment."""
        if role not in ("planner", "worker"):
            raise ExecutionProfileError("Unknown execution role.")
        policy = ModelRoutingPolicy.from_env()
        model = getattr(self, f"{role}_model")
        if model is None:
            return policy
        # Selecting the explicitly named K3 preset is a manual opt-in to a
        # premium model. Remove this single model from the automatic exclusion
        # list in this role's isolated policy object; never alter environment.
        manual_k3 = model == "moonshot/kimi-k3" and self.name in (
            "kimi-k3-k27", "kimi-k3-k2-7"
        )
        if policy.is_disabled(model) and not manual_k3:
            raise ExecutionProfileError(f"Profile model is disabled: {model}")
        if manual_k3:
            policy = replace(policy, disabled_models=tuple(
                entry for entry in policy.disabled_models if entry.casefold() != model.casefold()
            ))
        if model.startswith("openai/") and not policy.economy_auth_profile:
            raise ExecutionProfileError(
                "An OpenAI execution profile requires ADAPTIVE_OPENAI_OAUTH_PROFILE."
            )
        if model.startswith("moonshot/") and not policy.kimi_enabled:
            raise ExecutionProfileError("Moonshot routing is disabled.")
        fallbacks = tuple(getattr(self, f"{role}_fallback_models"))
        for fallback in fallbacks:
            if policy.is_disabled(fallback):
                raise ExecutionProfileError(f"Fallback model is disabled: {fallback}")
            if fallback.startswith("openai/") and not policy.economy_auth_profile:
                raise ExecutionProfileError(
                    "OpenAI fallback requires ADAPTIVE_OPENAI_OAUTH_PROFILE."
                )
        return replace(
            policy,
            pinned_model=model,
            pinned_thinking=getattr(self, f"{role}_thinking"),
            pinned_fallback_models=fallbacks,
        )


BUILTIN_PROFILES = {
    "original": ExecutionProfile(name="original"),
    "gpt-terra-medium-low": ExecutionProfile(
        name="gpt-terra-medium-low",
        planner_model="openai/gpt-5.6-terra", planner_thinking="medium",
        worker_model="openai/gpt-5.6-terra", worker_thinking="low",
        planner_fallback_models=("moonshot/kimi-k2.7-code",),
        worker_fallback_models=("moonshot/kimi-k2.7-code",),
        quality_direct_fallback=True,
        concurrency_mode="AUTO", max_concurrency=8,
        worker_stall_overflow_slots=1,
    ),
    "gpt-luna-medium-low": ExecutionProfile(
        name="gpt-luna-medium-low",
        planner_model="openai/gpt-5.6-luna", planner_thinking="medium",
        worker_model="openai/gpt-5.6-luna", worker_thinking="low",
        quality_direct_fallback=True,
        concurrency_mode="FIXED", max_concurrency=1,
        worker_stall_overflow_slots=0,
    ),
    "gpt-fallback-direto": ExecutionProfile(
        name="gpt-fallback-direto",
        planner_model="openai/gpt-5.6-terra", planner_thinking="medium",
        worker_model="openai/gpt-5.6-terra", worker_thinking="medium",
        direct_owner_mode=True,
        concurrency_mode="FIXED", max_concurrency=1,
        worker_stall_overflow_slots=0,
    ),
    "kimi-k3-k27": ExecutionProfile(
        name="kimi-k3-k27",
        planner_model="moonshot/kimi-k3",
        worker_model="moonshot/kimi-k2.7-code",
        planner_fallback_models=("openai/gpt-5.6-terra",),
        worker_fallback_models=("openai/gpt-5.6-terra",),
        quality_direct_fallback=True,
        concurrency_mode="AUTO", max_concurrency=8,
        worker_stall_overflow_slots=1,
    ),
    # Compatible aliases for snapshots prepared before the user refined policy.
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

# Per-operator policy is intentionally separate from the immutable built-in
# definitions and custom-profile registry. Unconfigured installations retain
# the historical "original" default without changing any existing project.
_POLICY_VERSION = 1

# Agent roles are operator policy, not profile content.  Keeping this beside
# profile selection gives the CLI one authoritative pre-admission resolver.
_AGENT_ROLE_POLICY_VERSION = 1
_AGENT_ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


@dataclass(frozen=True)
class ExecutionProfileSelectionPolicy:
    default_profile: str = "original"
    require_authorized_override: bool = False
    actor: str = "legacy"
    reason: str = "Unconfigured installation preserves original routing"


def selection_policy_path() -> Path:
    raw = os.environ.get("ADAPTIVE_EXECUTION_PROFILE_SELECTION_FILE")
    return Path(raw).expanduser() if raw else (
        Path.home() / ".config/adaptive-ai-orchestrator/execution-profile-selection.json"
    )


def load_selection_policy(path: Path | None = None) -> ExecutionProfileSelectionPolicy:
    target = path if path is not None else selection_policy_path()
    if not target.exists():
        return ExecutionProfileSelectionPolicy()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutionProfileError("Cannot read execution profile selection policy.") from exc
    if (
        not isinstance(data, dict)
        or set(data) != {"version", "default_profile", "require_authorized_override", "actor", "reason"}
        or type(data["version"]) is not int
        or data["version"] != _POLICY_VERSION
        or type(data["require_authorized_override"]) is not bool
        or not isinstance(data["default_profile"], str)
        or not _NAME.fullmatch(data["default_profile"])
        or data["require_authorized_override"] is not True
        or not isinstance(data["actor"], str)
        or not data["actor"].strip()
        or not isinstance(data["reason"], str)
        or not data["reason"].strip()
    ):
        raise ExecutionProfileError("Invalid execution profile selection policy.")
    profile = get_profile(data["default_profile"])
    return ExecutionProfileSelectionPolicy(
        default_profile=profile.name,
        require_authorized_override=True,
        actor=data["actor"],
        reason=data["reason"],
    )


def set_default_execution_profile(
    name: str, *, authorized: bool, actor: str, reason: str,
    path: Path | None = None,
) -> ExecutionProfileSelectionPolicy:
    """Operator-attested durable default; never mutate a profile's definition."""
    if not authorized or not isinstance(actor, str) or not actor.strip() or not isinstance(reason, str) or not reason.strip():
        raise ExecutionProfileError("Setting a default profile requires explicit operator authorization, actor and reason.")
    profile = get_profile(name)
    target = path if path is not None else selection_policy_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": _POLICY_VERSION,
        "default_profile": profile.name,
        "require_authorized_override": True,
        "actor": actor.strip(),
        "reason": reason.strip(),
    }
    fd, temporary = tempfile.mkstemp(prefix=".execution-profile-selection-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            os.fchmod(output.fileno(), 0o600)
            json.dump(payload, output, ensure_ascii=False, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return load_selection_policy(target)


def select_new_project_profile(
    requested: str | None, *,
    override_authorized: bool = False,
    override_actor: str | None = None,
    override_reason: str | None = None,
    policy_path: Path | None = None,
) -> ExecutionProfile:
    """A locked default applies unless an operator explicitly authorizes a change.

    Flags attest authorization; CLI cannot cryptographically identify a human.
    A trusted OpenClaw bridge must obtain the actual human instruction before
    forwarding an override. Existing project resume never calls this function.
    """
    policy = load_selection_policy(policy_path)
    chosen = requested or policy.default_profile
    if chosen != policy.default_profile and policy.require_authorized_override:
        if not (
            override_authorized
            and isinstance(override_actor, str) and override_actor.strip()
            and isinstance(override_reason, str) and override_reason.strip()
        ):
            raise ExecutionProfileError(
                "An alternate execution profile requires explicit human authorization: "
                "--authorize-profile-override, --profile-override-actor and --profile-override-reason."
            )
    return get_profile(chosen)


@dataclass(frozen=True)
class AgentRoleSelectionPolicy:
    planner_agent: str
    worker_agent: str
    actor: str
    reason: str


def agent_role_policy_path() -> Path:
    raw = os.environ.get("ADAPTIVE_AGENT_ROLE_SELECTION_FILE")
    return Path(raw).expanduser() if raw else (
        Path.home() / ".config/adaptive-ai-orchestrator/agent-role-selection.json"
    )


def openclaw_config_path() -> Path:
    raw = os.environ.get("OPENCLAW_CONFIG_PATH")
    if raw:
        return Path(raw).expanduser()
    raw = os.environ.get("ADAPTIVE_OPENCLAW_CONFIG_FILE")
    return Path(raw).expanduser() if raw else Path.home() / ".openclaw/openclaw.json"


def _validate_agent_id(value: object, field: str) -> str:
    if not isinstance(value, str) or not _AGENT_ID.fullmatch(value):
        raise ExecutionProfileError(f"Invalid {field} agent id.")
    return value


def _openclaw_agents_timeout() -> float:
    raw = os.environ.get("ADAPTIVE_OPENCLAW_AGENTS_TIMEOUT", "15")
    try:
        value = float(raw)
    except ValueError as exc:
        raise ExecutionProfileError(
            "ADAPTIVE_OPENCLAW_AGENTS_TIMEOUT must be a finite positive number."
        ) from exc
    if not math.isfinite(value) or value <= 0:
        raise ExecutionProfileError(
            "ADAPTIVE_OPENCLAW_AGENTS_TIMEOUT must be a finite positive number."
        )
    return min(value, 60.0)


def eligible_openclaw_agents(path: Path | None = None) -> frozenset[str]:
    target = path or openclaw_config_path()
    command = shlex.split(
        os.environ.get("ADAPTIVE_OPENCLAW_AGENTS_COMMAND", "openclaw agents list --json")
    )
    if not command:
        raise ExecutionProfileError("Cannot validate agent identities: OpenClaw agent-list command is empty.")
    environment = os.environ.copy()
    environment["OPENCLAW_CONFIG_PATH"] = str(target)
    try:
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True,
            env=environment, timeout=_openclaw_agents_timeout(),
        )
    except subprocess.TimeoutExpired as exc:
        raise ExecutionProfileError(
            f"OpenClaw agent-list interface timed out after {_openclaw_agents_timeout():g} seconds."
        ) from exc
    except OSError as exc:
        raise ExecutionProfileError(
            "Cannot validate agent identities through OpenClaw's authoritative agent-list interface."
        ) from exc
    if completed.returncode != 0:
        raise ExecutionProfileError(
            "Cannot validate agent identities through OpenClaw's authoritative agent-list interface."
        )
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ExecutionProfileError("OpenClaw agent-list interface returned invalid JSON.") from exc
    entries = data.get("agents") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise ExecutionProfileError("OpenClaw agent-list interface returned no agent list.")
    eligible = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        agent_id = entry.get("id") or entry.get("agentId")
        if not isinstance(agent_id, str) or not _AGENT_ID.fullmatch(agent_id):
            continue
        if entry.get("enabled", True) is not False and entry.get("eligible", True) is not False:
            eligible.add(agent_id)
    return frozenset(eligible)


def load_agent_role_policy(path: Path | None = None) -> AgentRoleSelectionPolicy:
    target = path or agent_role_policy_path()
    if not target.exists():
        raise ExecutionProfileError(
            "Agent role defaults are not configured. Configure planner and worker "
            "with `agent-roles set-default` before using a quality fallback profile."
        )
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutionProfileError("Cannot read agent role selection policy.") from exc
    if (
        not isinstance(data, dict)
        or set(data) != {"version", "planner_agent", "worker_agent", "actor", "reason"}
        or data["version"] != _AGENT_ROLE_POLICY_VERSION
        or not isinstance(data.get("actor"), str) or not data["actor"].strip()
        or not isinstance(data.get("reason"), str) or not data["reason"].strip()
    ):
        raise ExecutionProfileError("Invalid agent role selection policy.")
    return AgentRoleSelectionPolicy(
        planner_agent=_validate_agent_id(data["planner_agent"], "planner"),
        worker_agent=_validate_agent_id(data["worker_agent"], "worker"),
        actor=data["actor"].strip(), reason=data["reason"].strip(),
    )


def set_default_agent_roles(
    planner_agent: str, worker_agent: str, *, authorized: bool, actor: str,
    reason: str, path: Path | None = None,
) -> AgentRoleSelectionPolicy:
    if not authorized or not isinstance(actor, str) or not actor.strip() or not isinstance(reason, str) or not reason.strip():
        raise ExecutionProfileError("Setting agent role defaults requires explicit operator authorization, actor and reason.")
    planner = _validate_agent_id(planner_agent, "planner")
    worker = _validate_agent_id(worker_agent, "worker")
    eligible = eligible_openclaw_agents()
    missing = sorted({planner, worker} - eligible)
    if missing:
        raise ExecutionProfileError(f"Configured agent(s) do not exist or are ineligible: {', '.join(missing)}.")
    target = path or agent_role_policy_path()
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = {"version": _AGENT_ROLE_POLICY_VERSION, "planner_agent": planner,
               "worker_agent": worker, "actor": actor.strip(), "reason": reason.strip()}
    fd, temporary = tempfile.mkstemp(prefix=".agent-role-selection-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            os.fchmod(output.fileno(), 0o600)
            json.dump(payload, output, ensure_ascii=False, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return load_agent_role_policy(target)


def resolve_project_agents(
    profile: ExecutionProfile, *, requested_worker: str | None,
    requested_planner: str | None, policy_path: Path | None = None,
    config_path: Path | None = None,
) -> tuple[str, str | None]:
    """Resolve and validate roles before any project admission side effect."""
    if not profile.quality_direct_fallback and not (requested_worker or requested_planner):
        return "main", None
    if requested_worker and requested_planner:
        worker, planner = requested_worker, requested_planner
    elif not profile.quality_direct_fallback:
        worker, planner = requested_worker or "main", requested_planner
    else:
        policy = load_agent_role_policy(policy_path)
        worker = requested_worker or policy.worker_agent
        planner = requested_planner or policy.planner_agent
    eligible = eligible_openclaw_agents(config_path)
    missing = sorted({worker, planner} - eligible)
    if missing:
        raise ExecutionProfileError(
            f"Requested/configured agent(s) do not exist or are ineligible: {', '.join(missing)}."
        )
    if worker == planner:
        raise ExecutionProfileError(
            "Quality-driven fallback direto requires distinct planner and worker agents."
        )
    return worker, planner
