from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STOP_PROMPT = ROOT / "docs" / "prompts" / "PARAR-E-FAZER-HANDOFF.md"
CONTINUE_PROMPT = ROOT / "docs" / "prompts" / "CONTINUAR-PROJETO.md"
README = ROOT / "docs" / "prompts" / "README.md"


def test_stop_prompt_requires_single_canonical_handoff():
    text = STOP_PROMPT.read_text(encoding="utf-8")
    assert "HANDOFF.md" in text
    assert "HANDOFF-YYYY-MM-DD-HHMM-<ESCOPO>.md" in text
    assert "atualize `HANDOFF.md` no lugar" in text
    assert "não gere um novo handoff datado" in text
    assert "migre" in text


def test_continue_prompt_reads_canonical_handoff_before_history():
    text = CONTINUE_PROMPT.read_text(encoding="utf-8")
    assert "use `HANDOFF.md` na raiz do projeto" in text
    assert "snapshots históricos" in text
    assert "Não determine o handoff atual apenas ordenando nomes" in text


def test_prompt_readme_documents_same_handoff_contract():
    text = README.read_text(encoding="utf-8")
    assert "Padrão obrigatório de handoff" in text
    assert "HANDOFF.md" in text
    assert "docs/governanca/handoffs/HANDOFF-YYYY-MM-DD-HHMM-<ESCOPO>.md" in text
