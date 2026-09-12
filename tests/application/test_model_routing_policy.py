from application.model_routing_policy import ModelRoutingPolicy
from domain.resource_configuration import ResourceConfiguration
from domain.task_package import TaskPackage


OAUTH_PROFILE = "openai:oauth-test"


def policy() -> ModelRoutingPolicy:
    return ModelRoutingPolicy(economy_auth_profile=OAUTH_PROFILE)


def make_task(
    objective: str,
    *,
    task_id: str = "project:o:wave:1:wu:attempt-number:1",
    context: tuple[str, ...] = (),
    skills: tuple[str, ...] = (),
    model: str | None = None,
    provider: str | None = None,
    auth_profile: str | None = None,
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
            auth_profile=auth_profile,
            thinking=thinking,
            runtime="openclaw",
        ),
        expected_output=("result",),
        acceptance_criteria=("runtime-completed",),
    )


def test_planner_uses_k27_provider_native() -> None:
    decision = policy().select(
        make_task(
            "You are the planning layer of Adaptive AI Orchestrator.",
            skills=(
                "engineering-lifecycle",
                "project-discovery",
                "work-decomposition",
            ),
        )
    )

    assert decision.model == "moonshot/kimi-k2.7-code"
    assert decision.provider == "moonshot"
    assert decision.auth_profile == "moonshot:api-key"
    assert decision.tier == "strong"
    assert decision.thinking is None
    assert decision.thinking_reason == "provider-native-code-specialist-reasoning"
    assert decision.attempt == 1


def test_systemic_architecture_analysis_and_synthesis_use_k27() -> None:
    routing = policy()

    for objective in (
        "Definir a arquitetura da aplicação e decisões estruturais.",
        "Realizar análise gerencial de riscos do projeto.",
        "Analisar o manifesto do projeto e produzir síntese gerencial.",
    ):
        decision = routing.select(make_task(objective))
        assert decision.model == "moonshot/kimi-k2.7-code"
        assert decision.provider == "moonshot"
        assert decision.tier == "strong"
        assert decision.thinking is None


def test_critical_systemic_work_uses_k27_not_k3_or_sol() -> None:
    routing = policy()
    decision = routing.select(
        make_task(
            "Definir security architecture para uma decisão crítica e sistêmica."
        )
    )

    assert decision.model == "moonshot/kimi-k2.7-code"
    assert decision.reason == "critical-systemic-orchestration"
    assert decision.thinking is None
    assert routing.is_disabled("moonshot/kimi-k3")
    assert routing.is_disabled("openai/gpt-5.6-sol")


def test_code_review_and_code_level_architecture_use_k27() -> None:
    routing = policy()

    for objective in (
        "Perform code review for the backend implementation.",
        "Revisar arquitetura aplicada ao código dos services e repositories.",
    ):
        decision = routing.select(make_task(objective))
        assert decision.model == "moonshot/kimi-k2.7-code"
        assert decision.provider == "moonshot"
        assert decision.tier == "code-specialist"
        assert decision.thinking is None


def test_routine_code_first_attempt_uses_luna_low_oauth() -> None:
    decision = policy().select(
        make_task("Implementar o repository PHP para persistência de categorias.")
    )

    assert decision.model == "openai/gpt-5.6-luna"
    assert decision.provider == "openai"
    assert decision.auth_profile == OAUTH_PROFILE
    assert decision.tier == "economy"
    assert decision.reason == "routine-code-or-test-first-attempt"
    assert decision.thinking == "low"
    assert decision.thinking_reason == "routine-code-low-reasoning"


def test_complex_code_first_attempt_uses_k27() -> None:
    decision = policy().select(
        make_task(
            "Implementar transferência financeira com transação, rollback, "
            "autorização e consistência de saldo."
        )
    )

    assert decision.model == "moonshot/kimi-k2.7-code"
    assert decision.tier == "code-specialist"
    assert decision.reason == "complex-code-or-test-first-attempt"
    assert decision.thinking is None


def test_routine_non_code_work_uses_luna_low_oauth() -> None:
    decision = policy().select(
        make_task("Organizar os nomes dos arquivos de saída.")
    )

    assert decision.model == "openai/gpt-5.6-luna"
    assert decision.auth_profile == OAUTH_PROFILE
    assert decision.tier == "economy"
    assert decision.reason == "routine-or-mechanical-work"
    assert decision.thinking == "low"


def test_code_retry_escalates_to_k27_with_provider_native_thinking() -> None:
    decision = policy().select(
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


def test_explicit_remediation_uses_k27_even_on_first_attempt() -> None:
    decision = policy().select(
        make_task(
            "Corrigir falha nos testes e refatorar o código para Single Responsibility."
        )
    )

    assert decision.model == "moonshot/kimi-k2.7-code"
    assert decision.tier == "code-specialist"
    assert decision.reason == "explicit-code-remediation"
    assert decision.thinking is None


def test_explicit_k27_model_keeps_provider_native_thinking_and_auth_profile() -> None:
    decision = policy().select(
        make_task(
            "Implement code.",
            model="moonshot/kimi-k2.7-code",
            provider="moonshot",
            auth_profile="moonshot:custom",
            thinking="high",
        )
    )

    assert decision.model == "moonshot/kimi-k2.7-code"
    assert decision.provider == "moonshot"
    assert decision.auth_profile == "moonshot:custom"
    assert decision.tier == "explicit"
    assert decision.reason == "explicit-model-override"
    assert decision.thinking is None


def test_k3_and_sol_are_disabled_and_fall_back_to_luna_for_routine_work() -> None:
    routing = policy()

    for premium_model in ("moonshot/kimi-k3", "openai/gpt-5.6-sol"):
        decision = routing.select(
            make_task(
                "Organizar documentação simples.",
                model=premium_model,
                provider=premium_model.split("/", 1)[0],
                thinking="high",
            )
        )
        assert routing.is_disabled(premium_model)
        assert decision.model == "openai/gpt-5.6-luna"
        assert decision.auth_profile == OAUTH_PROFILE
        assert decision.thinking == "low"


def test_operational_fallback_switches_k27_to_luna_low_oauth() -> None:
    routing = policy()
    primary = routing.select(
        make_task(
            "Implementar transferência financeira com transação e rollback."
        )
    )

    fallback = routing.fallback_for(primary, failure_reason="billing")

    assert fallback is not None
    assert fallback.model == "openai/gpt-5.6-luna"
    assert fallback.provider == "openai"
    assert fallback.auth_profile == OAUTH_PROFILE
    assert fallback.tier == "fallback"
    assert fallback.thinking == "low"
    assert fallback.escalated_from == "moonshot/kimi-k2.7-code"


def test_luna_does_not_auto_escalate_to_paid_kimi() -> None:
    routing = policy()
    primary = routing.select(make_task("Organizar documentação simples."))

    fallback = routing.fallback_for(primary, failure_reason="quota")

    assert fallback is None


def test_environment_can_override_policy_models_thinking_auth_and_disabled_models(
    monkeypatch,
) -> None:
    monkeypatch.setenv("ADAPTIVE_STRONG_MODEL", "vendor/strong-custom")
    monkeypatch.setenv("ADAPTIVE_ECONOMY_MODEL", "vendor/economy-custom")
    monkeypatch.setenv("ADAPTIVE_CODE_SPECIALIST_MODEL", "vendor/code-custom")
    monkeypatch.setenv("ADAPTIVE_STRONG_THINKING", "minimal")
    monkeypatch.setenv("ADAPTIVE_CRITICAL_THINKING", "low")
    monkeypatch.setenv("ADAPTIVE_CODE_THINKING", "minimal")
    monkeypatch.setenv("ADAPTIVE_ROUTINE_THINKING", "low")
    monkeypatch.setenv("ADAPTIVE_OPENAI_OAUTH_PROFILE", "openai:oauth-custom")
    monkeypatch.setenv("ADAPTIVE_KIMI_AUTH_PROFILE", "moonshot:kimi-custom")
    monkeypatch.setenv("ADAPTIVE_DISABLED_MODELS", "vendor/off-1,vendor/off-2")
    monkeypatch.setenv("ADAPTIVE_KIMI_ENABLED", "false")

    routing = ModelRoutingPolicy.from_env()

    assert routing.strong_model == "vendor/strong-custom"
    assert routing.economy_model == "vendor/economy-custom"
    assert routing.code_specialist_model == "vendor/code-custom"
    assert routing.strong_thinking == "minimal"
    assert routing.critical_thinking == "low"
    assert routing.code_thinking == "minimal"
    assert routing.routine_thinking == "low"
    assert routing.economy_auth_profile == "openai:oauth-custom"
    assert routing.code_specialist_auth_profile == "moonshot:kimi-custom"
    assert routing.kimi_enabled is False
    assert routing.disabled_models == ("vendor/off-1", "vendor/off-2")


def test_kimi_disabled_routes_high_complexity_directly_to_luna_low_oauth() -> None:
    routing = ModelRoutingPolicy(
        economy_auth_profile=OAUTH_PROFILE,
        kimi_enabled=False,
    )

    for objective in (
        "Definir arquitetura sistêmica da aplicação.",
        "Implementar transferência financeira com transação e rollback.",
        "Perform code review for the backend implementation.",
    ):
        decision = routing.select(make_task(objective))
        assert decision.model == "openai/gpt-5.6-luna"
        assert decision.provider == "openai"
        assert decision.auth_profile == OAUTH_PROFILE
        assert decision.tier == "economy-fallback"
        assert decision.thinking == "low"
        assert decision.reason.startswith("kimi-disabled-")
        assert decision.thinking_reason == "high-complexity-luna-low-kimi-disabled"
        assert decision.escalated_from == "moonshot/kimi-k2.7-code"


def test_kimi_disabled_still_allows_explicit_manual_k27_override() -> None:
    routing = ModelRoutingPolicy(
        economy_auth_profile=OAUTH_PROFILE,
        kimi_enabled=False,
    )

    decision = routing.select(
        make_task(
            "Manual K2.7 diagnostic.",
            model="moonshot/kimi-k2.7-code",
            provider="moonshot",
        )
    )

    assert decision.model == "moonshot/kimi-k2.7-code"
    assert decision.tier == "explicit"
    assert decision.thinking is None


def test_environment_can_disable_kimi_automatic_routing(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVE_KIMI_ENABLED", "0")
    routing = ModelRoutingPolicy.from_env()

    assert routing.kimi_enabled is False


def test_environment_rejects_invalid_kimi_enabled_value(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVE_KIMI_ENABLED", "sometimes")

    try:
        ModelRoutingPolicy.from_env()
    except ValueError as exc:
        assert "ADAPTIVE_KIMI_ENABLED" in str(exc)
    else:
        raise AssertionError("Expected invalid Kimi availability flag to fail.")
