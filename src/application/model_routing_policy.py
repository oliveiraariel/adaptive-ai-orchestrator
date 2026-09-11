from __future__ import annotations

import os
import re
from dataclasses import dataclass

from domain.task_package import TaskPackage


@dataclass(frozen=True)
class ModelRoutingDecision:
    model: str
    provider: str
    tier: str
    reason: str
    attempt: int
    thinking: str | None
    thinking_reason: str
    escalated_from: str | None = None


@dataclass(frozen=True)
class ModelRoutingPolicy:
    """Deterministic role-aware routing for Adaptive/OpenClaw.

    Active policy:
    - Kimi K3 handles orchestration, project discovery, planning, governance,
      synthesis and systemic/high-level architecture;
    - Kimi K2.7 Code handles code-specialist work, code-level architecture,
      complex implementation, review, retries and remediation;
    - GPT-5.6 Luna handles routine/mechanical work and routine first-pass code;
    - K3 defaults to low reasoning and escalates to high only for explicitly
      critical systemic work;
    - Luna runs at medium reasoning;
    - K2.7 Code keeps provider-native reasoning;
    - GPT-5.6 Sol is excluded from automatic routing.
    """

    strong_model: str = "kimi/k3"
    economy_model: str = "openai/gpt-5.6-luna"
    code_specialist_model: str = "moonshot/kimi-k2.7-code"
    strong_thinking: str = "low"
    critical_thinking: str = "high"
    code_thinking: str = "medium"
    routine_thinking: str = "medium"
    disabled_models: tuple[str, ...] = ("openai/gpt-5.6-sol",)

    @classmethod
    def from_env(cls) -> "ModelRoutingPolicy":
        disabled = os.environ.get(
            "ADAPTIVE_DISABLED_MODELS",
            "openai/gpt-5.6-sol",
        )
        disabled_models = tuple(
            item.strip()
            for item in disabled.split(",")
            if item.strip()
        )
        return cls(
            strong_model=os.environ.get(
                "ADAPTIVE_STRONG_MODEL",
                "kimi/k3",
            ),
            economy_model=os.environ.get(
                "ADAPTIVE_ECONOMY_MODEL",
                "openai/gpt-5.6-luna",
            ),
            code_specialist_model=os.environ.get(
                "ADAPTIVE_CODE_SPECIALIST_MODEL",
                "moonshot/kimi-k2.7-code",
            ),
            strong_thinking=os.environ.get(
                "ADAPTIVE_STRONG_THINKING",
                "low",
            ),
            critical_thinking=os.environ.get(
                "ADAPTIVE_CRITICAL_THINKING",
                "high",
            ),
            code_thinking=os.environ.get(
                "ADAPTIVE_CODE_THINKING",
                "medium",
            ),
            routine_thinking=os.environ.get(
                "ADAPTIVE_ROUTINE_THINKING",
                "medium",
            ),
            disabled_models=disabled_models,
        )

    def select(self, task: TaskPackage) -> ModelRoutingDecision:
        configuration = task.configuration
        assert configuration is not None
        attempt = self._attempt_number(task)
        primary_text = self._primary_text(task)
        all_text = self._all_text(task)
        strong_responsibility = self._is_strong_responsibility(
            primary_text,
            configuration.skills,
        )
        code_specialist_responsibility = self._is_code_specialist_responsibility(
            primary_text,
            all_text,
        )
        critical_systemic = (
            strong_responsibility
            and self._is_critical_systemic_work(all_text)
        )
        code_or_test = self._is_code_or_test_work(primary_text, all_text)
        complex_code = code_or_test and self._is_complex_code_work(all_text)
        remedial = self._is_remedial_work(all_text)

        explicit_model = configuration.model
        if explicit_model and not self.is_disabled(explicit_model):
            thinking, thinking_reason = self._thinking_for_explicit_model(
                explicit_model,
                requested=configuration.thinking,
                strong_responsibility=strong_responsibility,
                code_or_test=code_or_test,
            )
            return ModelRoutingDecision(
                model=explicit_model,
                provider=configuration.provider or self._provider(explicit_model),
                tier="explicit",
                reason="explicit-model-override",
                attempt=attempt,
                thinking=thinking,
                thinking_reason=thinking_reason,
            )

        if code_specialist_responsibility:
            return self._decision(
                self.code_specialist_model,
                tier="code-specialist",
                reason="code-review-or-code-level-architecture",
                attempt=attempt,
                thinking=None,
                thinking_reason="provider-native-code-specialist-reasoning",
            )

        if strong_responsibility:
            return self._decision(
                self.strong_model,
                tier="strong",
                reason=(
                    "critical-systemic-orchestration"
                    if critical_systemic
                    else "orchestration-planning-or-systemic-architecture"
                ),
                attempt=attempt,
                thinking=(
                    self.critical_thinking
                    if critical_systemic
                    else self.strong_thinking
                ),
                thinking_reason=(
                    "critical-systemic-high-reasoning"
                    if critical_systemic
                    else "orchestrator-low-reasoning"
                ),
            )

        if code_or_test and (attempt >= 2 or remedial):
            reason = (
                "code-or-test-retry-after-prior-attempt"
                if attempt >= 2
                else "explicit-code-remediation"
            )
            return self._decision(
                self.code_specialist_model,
                tier="code-specialist",
                reason=reason,
                attempt=attempt,
                thinking=None,
                thinking_reason="provider-native-code-specialist-reasoning",
                escalated_from=self.economy_model,
            )

        if complex_code:
            return self._decision(
                self.code_specialist_model,
                tier="code-specialist",
                reason="complex-code-or-test-first-attempt",
                attempt=attempt,
                thinking=None,
                thinking_reason="provider-native-code-specialist-reasoning",
            )

        if code_or_test:
            return self._decision(
                self.economy_model,
                tier="economy",
                reason="routine-code-or-test-first-attempt",
                attempt=attempt,
                thinking=self.code_thinking,
                thinking_reason="routine-code-medium-reasoning",
            )

        return self._decision(
            self.economy_model,
            tier="economy",
            reason="routine-or-mechanical-work",
            attempt=attempt,
            thinking=self.routine_thinking,
            thinking_reason="routine-non-code-medium-reasoning",
        )

    def fallback_for(
        self,
        decision: ModelRoutingDecision,
        *,
        failure_reason: str,
    ) -> ModelRoutingDecision | None:
        """Return the next role-compatible model for operational failover.

        Routine Luna work falls back to K2.7 Code. K3 orchestration falls back
        to K2.7 Code. Direct K2.7 Code work falls back to Luna. Disabled models
        are never selected as fallback candidates.
        """
        normalized = decision.model.strip().casefold()
        economy = self.economy_model.strip().casefold()
        strong = self.strong_model.strip().casefold()
        specialist = self.code_specialist_model.strip().casefold()

        if normalized == economy:
            target = self.code_specialist_model
        elif normalized == strong:
            target = self.code_specialist_model
        elif normalized == specialist:
            target = self.economy_model
        else:
            return None

        if target.strip().casefold() == normalized or self.is_disabled(target):
            return None

        if self._uses_provider_native_thinking(target):
            thinking = None
            thinking_reason = "provider-native-code-specialist-reasoning"
        elif target.strip().casefold() == strong:
            thinking = self.strong_thinking
            thinking_reason = "operational-fallback-orchestrator-low-reasoning"
        else:
            thinking = self.routine_thinking
            thinking_reason = "operational-fallback-medium-reasoning"
        return ModelRoutingDecision(
            model=target,
            provider=self._provider(target),
            tier="fallback",
            reason=f"operational-fallback-after-{failure_reason}",
            attempt=decision.attempt,
            thinking=thinking,
            thinking_reason=thinking_reason,
            escalated_from=decision.model,
        )

    def is_disabled(self, model: str) -> bool:
        normalized = model.strip().casefold()
        return normalized in {
            item.strip().casefold()
            for item in self.disabled_models
        }

    def _decision(
        self,
        model: str,
        *,
        tier: str,
        reason: str,
        attempt: int,
        thinking: str | None,
        thinking_reason: str,
        escalated_from: str | None = None,
    ) -> ModelRoutingDecision:
        if self.is_disabled(model):
            raise ValueError(f"Adaptive model routing selected disabled model: {model}")
        if self._uses_provider_native_thinking(model):
            thinking = None
            thinking_reason = "provider-native-code-specialist-reasoning"

        return ModelRoutingDecision(
            model=model,
            provider=self._provider(model),
            tier=tier,
            reason=reason,
            attempt=attempt,
            thinking=thinking,
            thinking_reason=thinking_reason,
            escalated_from=escalated_from,
        )

    def _thinking_for_explicit_model(
        self,
        model: str,
        *,
        requested: str | None,
        strong_responsibility: bool,
        code_or_test: bool,
    ) -> tuple[str | None, str]:
        if self._uses_provider_native_thinking(model):
            return None, "provider-native-code-specialist-reasoning"
        if requested is not None:
            return requested, "explicit-thinking-override"
        if model.strip().casefold() == self.strong_model.strip().casefold():
            return self.strong_thinking, "orchestrator-model-low-reasoning"
        if model.strip().casefold() == self.economy_model.strip().casefold():
            return self.routine_thinking, "economy-model-medium-reasoning"
        if strong_responsibility:
            return self.strong_thinking, "strong-responsibility-model-policy"
        if code_or_test:
            return self.code_thinking, "routine-code-medium-reasoning"
        return self.routine_thinking, "routine-non-code-medium-reasoning"

    @staticmethod
    def _uses_provider_native_thinking(model: str) -> bool:
        normalized = model.strip().casefold()
        return normalized in {
            "moonshot/kimi-k2.7-code",
            "moonshot/kimi-k2.7-code-highspeed",
        }

    @staticmethod
    def _provider(model: str) -> str:
        normalized = model.strip()
        if "/" in normalized:
            return normalized.split("/", 1)[0]
        return "openai"

    @staticmethod
    def _attempt_number(task: TaskPackage) -> int:
        match = re.search(r"attempt-number:(\d+)", task.task_id)
        if match:
            return max(1, int(match.group(1)))

        if "REVISION_REQUIRED" in task.task_id or any(
            "Revision feedback from previous attempt" in item
            for item in task.context
        ):
            return 2

        return 1

    @staticmethod
    def _primary_text(task: TaskPackage) -> str:
        configuration = task.configuration
        assert configuration is not None
        role_context = tuple(
            item
            for item in task.context
            if item.lower().startswith("logical worker role:")
        )
        return "\n".join(
            (
                task.objective,
                task.scope,
                *role_context,
                *configuration.skills,
            )
        ).casefold()

    @staticmethod
    def _all_text(task: TaskPackage) -> str:
        configuration = task.configuration
        assert configuration is not None
        return "\n".join(
            (
                task.objective,
                task.scope,
                *task.context,
                *task.constraints,
                *task.expected_output,
                *task.acceptance_criteria,
                *configuration.skills,
                *configuration.tools,
            )
        ).casefold()

    @staticmethod
    def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
        return any(term in text for term in terms)

    @classmethod
    def _is_strong_responsibility(
        cls,
        text: str,
        skills: tuple[str, ...],
    ) -> bool:
        normalized_skills = {item.casefold() for item in skills}
        planner_skill_set = {
            "engineering-lifecycle",
            "project-discovery",
            "work-decomposition",
        }
        if planner_skill_set.issubset(normalized_skills):
            return True

        strong_terms = (
            "planning layer",
            "replanning layer",
            "architecture",
            "architect",
            "arquitetura",
            "arquiteto",
            "governance",
            "governança",
            "management",
            "manager",
            "managerial",
            "gerencial",
            "gestor",
            "strategy",
            "strategic",
            "estratég",
            "decision",
            "decisão",
            "analysis",
            "analytical",
            "analyze",
            "analyser",
            "analyzer",
            "análise",
            "analisar",
            "analis",
            "analítico",
            "analítica",
            "security architecture",
            "segurança",
            "audit",
            "auditoria",
            "high-stakes",
            "high stakes",
            "critical decision",
            "critical analysis",
            "critical review",
            "decisão crítica",
            "análise crítica",
            "revisão crítica",
            "criticidade alta",
        )
        return cls._contains_any(text, strong_terms)

    @classmethod
    def _is_code_specialist_responsibility(
        cls,
        primary_text: str,
        all_text: str,
    ) -> bool:
        terms = (
            "code review",
            "review code",
            "reviewer",
            "revisão de código",
            "revisor de código",
            "security code review",
            "implementation review",
            "revisão da implementação",
            "code architecture",
            "implementation architecture",
            "architecture applied to code",
            "arquitetura aplicada ao código",
            "arquitetura aplicada ao codigo",
            "refactor architecture",
            "refatoração arquitetural do código",
            "refatoracao arquitetural do codigo",
        )
        return cls._contains_any(primary_text, terms) or cls._contains_any(
            all_text,
            terms,
        )

    @classmethod
    def _is_critical_systemic_work(cls, text: str) -> bool:
        terms = (
            "high-stakes",
            "high stakes",
            "critical decision",
            "critical analysis",
            "decisão crítica",
            "análise crítica",
            "criticidade alta",
            "security architecture",
            "arquitetura de segurança",
            "system-wide",
            "system wide",
            "sistêmic",
            "cross-cutting architecture",
            "arquitetura transversal",
        )
        return cls._contains_any(text, terms)

    @classmethod
    def _is_code_or_test_work(cls, primary_text: str, all_text: str) -> bool:
        terms = (
            "implement",
            "implementation",
            "implementar",
            "implementação",
            "coding",
            "code generation",
            "código",
            "endpoint",
            "controller",
            "service",
            "repository",
            "refactor",
            "refator",
            "unit test",
            "integration test",
            "teste unitário",
            "teste de integração",
            "test suite",
            "pytest",
            "phpunit",
            "php",
            "python",
            "javascript",
            "typescript",
            "sql",
            "html",
            "css",
            "api rest",
            "rest api",
        )
        return cls._contains_any(primary_text, terms) or cls._contains_any(all_text, terms)

    @classmethod
    def _is_complex_code_work(cls, text: str) -> bool:
        terms = (
            "atomic",
            "atomicidade",
            "transaction",
            "transação",
            "rollback",
            "concurrency",
            "concorrência",
            "authorization",
            "autorização",
            "authentication",
            "autenticação",
            "security",
            "segurança",
            "financial consistency",
            "consistência financeira",
            "saldo",
            "transferência",
            "transferencia",
            "migration",
            "migração",
            "cross-cutting",
            "multi-file",
            "multiple files",
            "múltiplos arquivos",
            "state machine",
            "distributed",
            "idempotency",
            "idempotência",
        )
        return cls._contains_any(text, terms)

    @classmethod
    def _is_remedial_work(cls, text: str) -> bool:
        terms = (
            "fix failing",
            "fix failure",
            "fix bug",
            "repair",
            "remediation",
            "remediação",
            "corrigir falha",
            "corrigir erro",
            "corrigir teste",
            "correção de código",
            "failing test",
            "test failure",
            "tests failing",
            "testes falhando",
            "refactor",
            "refator",
            "clean code",
            "single responsibility",
            "single-responsibility",
            "solid principle",
            "solid principles",
            "review rejected",
            "revisão rejeitou",
            "correções solicitadas",
        )
        return cls._contains_any(text, terms)
