from application.model_routing_policy import ModelRoutingPolicy
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage


def make_task(
    objective: str,
    *,
    task_id: str = "project:o:wave:1:wu:attempt-number:1",
    context: tuple[str, ...] = (),
    skills: tuple[str, ...] = (),
    model: str | None = None,
    provider: str | None = None,
    thinking: str | None = None,
) -> TaskPackage:
    return TaskPackage(
        task_id=task_id,
        work_unit_id="wu-001",
        objective=objective,
        context=context,
        configuration=ResourceConfiguration(
            agent="sgfp",
            skills=skills,
            model=model,
            provider=provider,
            thinking=thinking,
            runtime="openclaw",
        ),
        expected_output=("result",),
        acceptance_criteria=("runtime-completed",),
    )


def test_planner_uses_k3_low() -> None:
    policy = ModelRoutingPolicy()
    task = make_task(
        "You are the planning layer of Adaptive AI Orchestrator.",
        skills=(
            "engineering-lifecycle",
            "project-discovery",
            "work-decomposition",
        ),
    )

    decision = policy.select(task)

    assert decision.model == "moonshot/kimi-k3"
    assert decision.provider == "moonshot"
    assert decision.tier == "strong"
    assert decision.thinking == "max"
    assert decision.thinking_reason == "orchestrator-max-reasoning"
    assert decision.attempt == 1


def test_systemic_architecture_analysis_and_synthesis_use_k3_low() -> None:
    policy = ModelRoutingPolicy()

    for objective in (
        "Definir a arquitetura da aplicação e decisões estruturais.",
        "Realizar análise gerencial de riscos do projeto.",
        "Analisar o manifesto do projeto e produzir síntese gerencial.",
    ):
        decision = policy.select(make_task(objective))
        assert decision.model == "moonshot/kimi-k3"
        assert decision.provider == "moonshot"
        assert decision.tier == "strong"
        assert decision.thinking == "max"


def test_critical_systemic_architecture_uses_k3_high() -> None:
    policy = ModelRoutingPolicy()
    decision = policy.select(
        make_task(
            "Definir security architecture para uma decisão crítica e sistêmica."
        )
    )

    assert decision.model == "moonshot/kimi-k3"
    assert decision.tier == "strong"
    assert decision.reason == "critical-systemic-orchestration"
    assert decision.thinking == "max"
    assert decision.thinking_reason == "critical-systemic-max-reasoning"


def test_code_review_and_code_level_architecture_use_k27() -> None:
    policy = ModelRoutingPolicy()

    for objective in (
        "Perform code review for the backend implementation.",
        "Revisar arquitetura aplicada ao código dos services e repositories.",
    ):
        decision = policy.select(make_task(objective))
        assert decision.model == "moonshot/kimi-k2.7-code"
        assert decision.provider == "moonshot"
        assert decision.tier == "code-specialist"
        assert decision.thinking is None


def test_routine_code_first_attempt_uses_luna_medium() -> None:
    policy = ModelRoutingPolicy()
    decision = policy.select(
        make_task("Implementar o repository PHP para persistência de categorias.")
    )

    assert decision.model == "openai/gpt-5.6-luna"
    assert decision.tier == "economy"
    assert decision.reason == "routine-code-or-test-first-attempt"
    assert decision.thinking == "medium"
    assert decision.thinking_reason == "routine-code-medium-reasoning"


def test_complex_code_first_attempt_uses_kimi() -> None:
    policy = ModelRoutingPolicy()
    decision = policy.select(
        make_task(
            "Implementar transferência financeira com transação, rollback, "
            "autorização e consistência de saldo."
        )
    )

    assert decision.model == "moonshot/kimi-k2.7-code"
    assert decision.tier == "code-specialist"
    assert decision.reason == "complex-code-or-test-first-attempt"
    assert decision.thinking is None


def test_routine_non_code_work_uses_luna_medium() -> None:
    policy = ModelRoutingPolicy()
    decision = policy.select(make_task("Organizar os nomes dos arquivos de saída."))

    assert decision.model == "openai/gpt-5.6-luna"
    assert decision.tier == "economy"
    assert decision.reason == "routine-or-mechanical-work"
    assert decision.thinking == "medium"


def test_code_retry_escalates_to_kimi_with_provider_native_thinking() -> None:
    policy = ModelRoutingPolicy()
    decision = policy.select(
        make_task(
            "Implementar o service PHP de categorias.",
            task_id="project:o:wave:2:wu:attempt-number:2",
            context=("Revision feedback from previous attempt: tests failed",),
        )
    )

    assert decision.model == "moonshot/kimi-k2.7-code"
    assert decision.tier == "code-specialist"
    assert decision.thinking is None
    assert decision.thinking_reason == "provider-native-code-specialist-reasoning"
    assert decision.escalated_from == "openai/gpt-5.6-luna"
    assert decision.attempt == 2


def test_explicit_remediation_uses_kimi_even_on_first_attempt() -> None:
    policy = ModelRoutingPolicy()
    decision = policy.select(
        make_task(
            "Corrigir falha nos testes e refatorar o código para Single Responsibility."
        )
    )

    assert decision.model == "moonshot/kimi-k2.7-code"
    assert decision.tier == "code-specialist"
    assert decision.reason == "explicit-code-remediation"
    assert decision.thinking is None


def test_explicit_kimi_model_keeps_provider_native_thinking() -> None:
    policy = ModelRoutingPolicy()
    decision = policy.select(
        make_task(
            "Implement code.",
            model="moonshot/kimi-k2.7-code",
            provider="moonshot",
            thinking="high",
        )
    )

    assert decision.model == "moonshot/kimi-k2.7-code"
    assert decision.provider == "moonshot"
    assert decision.tier == "explicit"
    assert decision.reason == "explicit-model-override"
    assert decision.thinking is None


def test_sol_is_disabled_and_is_not_preserved_as_explicit_override() -> None:
    policy = ModelRoutingPolicy()
    decision = policy.select(
        make_task(
            "Implementar repository PHP simples.",
            model="openai/gpt-5.6-sol",
            provider="openai",
            thinking="high",
        )
    )

    assert policy.is_disabled("openai/gpt-5.6-sol")
    assert decision.model == "openai/gpt-5.6-luna"
    assert decision.thinking == "medium"


def test_operational_fallback_switches_luna_to_kimi() -> None:
    policy = ModelRoutingPolicy()
    primary = policy.select(
        make_task("Implementar repository PHP simples.")
    )

    fallback = policy.fallback_for(primary, failure_reason="billing")

    assert fallback is not None
    assert fallback.model == "moonshot/kimi-k2.7-code"
    assert fallback.provider == "moonshot"
    assert fallback.tier == "fallback"
    assert fallback.thinking is None
    assert fallback.escalated_from == "openai/gpt-5.6-luna"


def test_operational_fallback_switches_k3_to_k27() -> None:
    policy = ModelRoutingPolicy()
    primary = policy.select(
        make_task("Definir arquitetura da aplicação.")
    )

    fallback = policy.fallback_for(primary, failure_reason="rate_limit")

    assert fallback is not None
    assert fallback.model == "moonshot/kimi-k2.7-code"
    assert fallback.provider == "moonshot"
    assert fallback.thinking is None
    assert fallback.escalated_from == "moonshot/kimi-k3"


def test_operational_fallback_switches_k27_to_luna() -> None:
    policy = ModelRoutingPolicy()
    primary = policy.select(
        make_task(
            "Implementar transferência financeira com transação e rollback."
        )
    )

    fallback = policy.fallback_for(primary, failure_reason="rate_limit")

    assert fallback is not None
    assert fallback.model == "openai/gpt-5.6-luna"
    assert fallback.provider == "openai"
    assert fallback.thinking == "medium"
    assert fallback.escalated_from == "moonshot/kimi-k2.7-code"


def test_environment_can_override_policy_models_thinking_and_disabled_models(
    monkeypatch,
) -> None:
    monkeypatch.setenv("ADAPTIVE_STRONG_MODEL", "vendor/strong-custom")
    monkeypatch.setenv("ADAPTIVE_ECONOMY_MODEL", "vendor/economy-custom")
    monkeypatch.setenv("ADAPTIVE_CODE_SPECIALIST_MODEL", "vendor/code-custom")
    monkeypatch.setenv("ADAPTIVE_STRONG_THINKING", "low")
    monkeypatch.setenv("ADAPTIVE_CRITICAL_THINKING", "high")
    monkeypatch.setenv("ADAPTIVE_CODE_THINKING", "medium")
    monkeypatch.setenv("ADAPTIVE_ROUTINE_THINKING", "low")
    monkeypatch.setenv("ADAPTIVE_DISABLED_MODELS", "vendor/off-1,vendor/off-2")

    policy = ModelRoutingPolicy.from_env()

    assert policy.strong_model == "vendor/strong-custom"
    assert policy.economy_model == "vendor/economy-custom"
    assert policy.code_specialist_model == "vendor/code-custom"
    assert policy.strong_thinking == "low"
    assert policy.critical_thinking == "high"
    assert policy.code_thinking == "medium"
    assert policy.routine_thinking == "low"
    assert policy.disabled_models == ("vendor/off-1", "vendor/off-2")
