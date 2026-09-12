from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

LEARNING_MARKER = "ADAPTIVE_LEARNING_CANDIDATE:"
_STRATEGY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,80}$")
_SENSITIVE_FRAGMENTS = (
    "authorization:",
    "bearer ",
    "api_key",
    "api-key",
    "oauth token",
    "secret=",
    "password=",
    "sk-",
)


@dataclass(frozen=True)
class ProblemSolvingStrategy:
    id: str
    title: str
    triggers: tuple[str, ...]
    guidance: tuple[str, ...]
    safety: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    status: str = "validated"

    def relevance(self, text: str) -> int:
        normalized = text.casefold()
        return sum(1 for trigger in self.triggers if trigger.casefold() in normalized)


class ProblemSolvingLearningStore:
    """Append-only, sanitized runtime evidence for reusable problem-solving tactics.

    Raw prompts, source code, model reasoning, credentials and arbitrary worker
    output are never stored. Only a small explicit strategy signal emitted by an
    accepted Work Unit is eligible for persistence.

    Repeated observations are advisory experience. They do not silently rewrite
    permanent policy or the validated repository knowledge catalog.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    @classmethod
    def from_env(cls) -> "ProblemSolvingLearningStore":
        override = os.environ.get("ADAPTIVE_PROBLEM_SOLVING_LOG", "").strip()
        if override:
            return cls(Path(override).expanduser())
        state_home = os.environ.get("XDG_STATE_HOME", "").strip()
        root = Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state"
        return cls(root / "adaptive-ai-orchestrator" / "problem-solving-candidates.jsonl")

    def record_worker_signal(
        self,
        output: str,
        *,
        orchestration_id: str,
        work_unit_id: str,
    ) -> bool:
        signal = self._extract_signal(output)
        if signal is None:
            return False
        return self.record(
            strategy_id=signal["strategy_id"],
            trigger=signal["trigger"],
            action=signal["action"],
            result=signal["result"],
            orchestration_id=orchestration_id,
            work_unit_id=work_unit_id,
            source="accepted-worker-result",
        )

    def record(
        self,
        *,
        strategy_id: str,
        trigger: str,
        action: str,
        result: str,
        orchestration_id: str,
        work_unit_id: str,
        source: str,
    ) -> bool:
        payload = {
            "strategy_id": strategy_id.strip(),
            "trigger": trigger.strip(),
            "action": action.strip(),
            "result": result.strip(),
            "orchestration_id": orchestration_id.strip(),
            "work_unit_id": work_unit_id.strip(),
            "source": source.strip(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if not self._is_safe_payload(payload):
            return False
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
                handle.write("\n")
        except OSError:
            return False
        return True

    def repeated_guidance(
        self,
        text: str,
        *,
        min_distinct_orchestrations: int = 2,
        limit: int = 2,
    ) -> tuple[str, ...]:
        records = self._read_records()
        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        for record in records:
            grouped[record["strategy_id"]].append(record)

        normalized = text.casefold()
        eligible: list[tuple[int, str]] = []
        for strategy_id, items in grouped.items():
            distinct = {item["orchestration_id"] for item in items}
            if len(distinct) < min_distinct_orchestrations:
                continue
            latest = items[-1]
            relevance = 0
            for field in ("trigger", "action"):
                value = latest[field].casefold()
                if value and (value in normalized or any(
                    token and token in normalized
                    for token in re.split(r"\W+", value)
                    if len(token) >= 6
                )):
                    relevance += 1
            if relevance == 0:
                continue
            eligible.append(
                (
                    len(distinct),
                    (
                        f"[provisional repeated experience: {strategy_id}] "
                        f"When {latest['trigger']}, prefer: {latest['action']}. "
                        f"Observed result: {latest['result']}."
                    ),
                )
            )

        eligible.sort(key=lambda item: item[0], reverse=True)
        return tuple(item[1] for item in eligible[:limit])

    def _read_records(self) -> list[dict[str, str]]:
        if not self.path.is_file():
            return []
        records: list[dict[str, str]] = []
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        for line in lines:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(item, dict) or not self._is_safe_payload(item):
                continue
            records.append({key: str(value) for key, value in item.items()})
        return records

    @classmethod
    def _extract_signal(cls, output: str) -> dict[str, str] | None:
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line.startswith(LEARNING_MARKER):
                continue
            candidate = line[len(LEARNING_MARKER):].strip()
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                return None
            if not isinstance(payload, dict):
                return None
            required = ("strategy_id", "trigger", "action", "result")
            if set(payload) != set(required):
                return None
            if any(not isinstance(payload[key], str) for key in required):
                return None
            return {key: payload[key].strip() for key in required}
        return None

    @classmethod
    def _is_safe_payload(cls, payload: dict) -> bool:
        required = (
            "strategy_id",
            "trigger",
            "action",
            "result",
            "orchestration_id",
            "work_unit_id",
            "source",
        )
        if any(not isinstance(payload.get(key), str) or not payload[key].strip() for key in required):
            return False
        strategy_id = payload["strategy_id"].strip()
        if not _STRATEGY_ID_RE.fullmatch(strategy_id):
            return False
        for key in ("trigger", "action", "result"):
            value = payload[key].strip()
            if len(value) > 500 or "\n" in value or "\r" in value:
                return False
            lowered = value.casefold()
            if any(fragment in lowered for fragment in _SENSITIVE_FRAGMENTS):
                return False
        for key in ("orchestration_id", "work_unit_id", "source"):
            if len(payload[key]) > 200:
                return False
        return True


class ProblemSolvingKnowledgeBase:
    """Validated repository knowledge plus conservative repeated runtime experience."""

    def __init__(
        self,
        strategies: Iterable[ProblemSolvingStrategy] = (),
        *,
        learning_store: ProblemSolvingLearningStore | None = None,
    ) -> None:
        self._strategies = tuple(strategies)
        self.learning_store = learning_store or ProblemSolvingLearningStore.from_env()

    @classmethod
    def load_default(
        cls,
        *,
        learning_store: ProblemSolvingLearningStore | None = None,
    ) -> "ProblemSolvingKnowledgeBase":
        override = os.environ.get("ADAPTIVE_PROBLEM_SOLVING_KNOWLEDGE", "").strip()
        if override:
            path = Path(override).expanduser()
        else:
            path = Path(__file__).resolve().parents[2] / "knowledge" / "problem-solving-strategies.json"
        return cls.load(path, learning_store=learning_store)

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        learning_store: ProblemSolvingLearningStore | None = None,
    ) -> "ProblemSolvingKnowledgeBase":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls(learning_store=learning_store)

        entries = payload.get("strategies", []) if isinstance(payload, dict) else []
        strategies: list[ProblemSolvingStrategy] = []
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("status") != "validated":
                continue
            try:
                strategy = ProblemSolvingStrategy(
                    id=str(entry["id"]).strip(),
                    title=str(entry["title"]).strip(),
                    triggers=cls._strings(entry.get("triggers", [])),
                    guidance=cls._strings(entry.get("guidance", [])),
                    safety=cls._strings(entry.get("safety", [])),
                    evidence=cls._strings(entry.get("evidence", [])),
                    status="validated",
                )
            except (KeyError, TypeError, ValueError):
                continue
            if not strategy.id or not strategy.guidance:
                continue
            strategies.append(strategy)
        return cls(strategies, learning_store=learning_store)

    def render_guidance(self, text: str, *, limit: int = 4) -> str:
        ranked = [
            (strategy.relevance(text), strategy)
            for strategy in self._strategies
            if strategy.relevance(text) > 0
        ]
        ranked.sort(key=lambda item: (-item[0], item[1].id))
        lines: list[str] = []
        for _, strategy in ranked[:limit]:
            lines.append(f"- VALIDATED STRATEGY [{strategy.id}]: {strategy.title}")
            lines.extend(f"  * {item}" for item in strategy.guidance)
            lines.extend(f"  * Safety: {item}" for item in strategy.safety)

        provisional = self.learning_store.repeated_guidance(text)
        if provisional:
            lines.append("- PROVISIONAL REPEATED EXPERIENCE (advisory, not permanent policy):")
            lines.extend(f"  * {item}" for item in provisional)

        if not lines:
            return ""
        return "ADAPTIVE EXPERIENCE GUIDANCE:\n" + "\n".join(lines)

    def record_planner_recovery(
        self,
        *,
        error: str,
        result: str,
    ) -> bool:
        return self.learning_store.record(
            strategy_id="simplify-after-structured-planning-failure",
            trigger=error[:500],
            action="Retry planning once with exactly one smallest safe Work Unit and preserve schema validation.",
            result=result[:500],
            orchestration_id=f"planner-recovery:{datetime.now(timezone.utc).timestamp()}",
            work_unit_id="planning",
            source="deterministic-planner-recovery",
        )

    @staticmethod
    def _strings(value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            raise TypeError("expected list")
        result = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
        if len(result) != len(value):
            raise ValueError("list contains non-string or blank item")
        return result
