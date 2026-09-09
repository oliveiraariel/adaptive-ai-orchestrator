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
    escalated_from: str | None = None


@dataclass(frozen=True)
class ModelRoutingPolicy:
    """Deterministic model-routing policy for Adaptive/OpenClaw execution.

    Policy goals:
    - reserve the strongest model for planning, architecture, governance,
      high-stakes analysis and code review;
    - use the economical model for routine/mechanical implementation work;
    - escalate code/test implementation to the code-specialist model after a
      failed/revision attempt or when the task is explicitly remedial;
    - preserve an explicitly requested model as an intentional caller override.
    """

    strong_model: str = "openai/gpt-5.6-sol"
    economy_model: str = "openai/gpt-5.6-luna"
    code_specialist_model: str = "moonshot/kimi-k2.7-code"

    @classmethod
    def from_env(cls) -> "ModelRoutingPolicy":
        return cls(
            strong_model=os.environ.get(
                "ADAPTIVE_STRONG_MODEL",
                "openai/gpt-5.6-sol",
            ),
            economy_model=os.environ.get(
                "ADAPTIVE_ECONOMY_MODEL",
                "openai/gpt-5.6-luna",
            ),
            code_specialist_model=os.environ.get(
                "ADAPTIVE_CODE_SPECIALIST_MODEL",
                "moonshot/kimi-k2.7-code",
            ),
        )

    def select(self, task: TaskPackage) -> ModelRoutingDecision:
        configuration = task.configuration
        assert configuration is not None
        attempt = self._attempt_number(task)

        if configuration.model:
            return ModelRoutingDecision(
                model=configuration.model,
                provider=configuration.provider or self._provider(configuration.model),
                tier="explicit",
                reason="explicit-model-override",
                attempt=attempt,
            )

        primary_text = self._primary_text(task)
        all_text = self._all_text(task)

        if self._is_strong_responsibility(primary_text, configuration.skills):
            return self._decision(
                self.strong_model,
                tier="strong",
                reason="analytical-managerial-high-stakes-or-review",
                attempt=attempt,
            )

        code_or_test = self._is_code_or_test_work(primary_text, all_text)
        remedial = self._is_remedial_work(all_text)

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
                escalated_from=self.economy_model,
            )

        return self._decision(
            self.economy_model,
            tier="economy",
            reason=(
                "routine-code-or-test-first-attempt"
                if code_or_test
                else "routine-or-mechanical-work"
            ),
            attempt=attempt,
        )

    def _decision(
        self,
        model: str,
        *,
        tier: str,
        reason: str,
        attempt: int,
        escalated_from: str | None = None,
    ) -> ModelRoutingDecision:
        return ModelRoutingDecision(
            model=model,
            provider=self._provider(model),
            tier=tier,
            reason=reason,
            attempt=attempt,
            escalated_from=escalated_from,
        )

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
            "code review",
            "review code",
            "reviewer",
            "revisão de código",
            "revisor de código",
            "security review",
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
