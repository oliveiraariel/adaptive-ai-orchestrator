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


def test_planner_uses_strong_model_with_high_thinking() -> None:
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

    assert decision.model == "openai/gpt-5.6-sol"
    assert decision.tier == "strong"
    assert decision.thinking == "high"
    assert decision.attempt == 1


def test_architecture_analysis_and_code_review_use_sol_high() -> None:
    policy = ModelRoutingPolicy()

    for objective in (
        "Definir a arquitetura da aplicação e decisões estruturais.",
        "Realizar análise gerencial de riscos do projeto.",
        "Analisar o manifesto do projeto e produzir síntese gerencial.",
        "Perform code review for the backend implementation.",
    ):
        decision = policy.select(make_task(objective))
        assert decision.model == "openai/gpt-5.6-sol"
        assert decision.tier == "strong"
        assert decision.thinking == "high"


def test_routine_code_first_attempt_uses_luna_high() -> None:
    policy = ModelRoutingPolicy()
    decision = policy.select(
        make_task("Implementar o repository PHP para persistência de categorias.")
    )

    assert decision.model == "openai/gpt-5.6-luna"
    assert decision.tier == "economy"
    assert decision.reason == "routine-code-or-test-first-attempt"
    assert decision.thinking == "high"
    assert decision.thinking_reason == "code-or-test-high-reasoning"


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
    assert decision.thinking_reason == "provider-native-code-specialist-reasoning"


def test_explicit_openai_thinking_override_is_preserved() -> None:
    policy = ModelRoutingPolicy()
    decision = policy.select(
        make_task(
            "Implement code.",
            model="openai/gpt-5.6-sol",
            provider="openai",
            thinking="xhigh",
        )
    )

    assert decision.model == "openai/gpt-5.6-sol"
    assert decision.thinking == "xhigh"
    assert decision.thinking_reason == "explicit-thinking-override"


def test_explicit_openai_coding_model_without_thinking_gets_high() -> None:
    policy = ModelRoutingPolicy()
    decision = policy.select(
        make_task(
            "Implement code.",
            model="openai/gpt-5.6-sol",
            provider="openai",
        )
    )

    assert decision.model == "openai/gpt-5.6-sol"
    assert decision.thinking == "high"
    assert decision.thinking_reason == "code-or-test-high-reasoning"


def test_environment_can_override_policy_models_and_thinking(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVE_STRONG_MODEL", "openai/strong-custom")
    monkeypatch.setenv("ADAPTIVE_ECONOMY_MODEL", "openai/economy-custom")
    monkeypatch.setenv("ADAPTIVE_CODE_SPECIALIST_MODEL", "vendor/code-custom")
    monkeypatch.setenv("ADAPTIVE_STRONG_THINKING", "xhigh")
    monkeypatch.setenv("ADAPTIVE_CODE_THINKING", "xhigh")
    monkeypatch.setenv("ADAPTIVE_ROUTINE_THINKING", "low")

    policy = ModelRoutingPolicy.from_env()

    assert policy.strong_model == "openai/strong-custom"
    assert policy.economy_model == "openai/economy-custom"
    assert policy.code_specialist_model == "vendor/code-custom"
    assert policy.strong_thinking == "xhigh"
    assert policy.code_thinking == "xhigh"
    assert policy.routine_thinking == "low"
