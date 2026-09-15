# Adaptive AI Orchestrator — Português (Brasil)

[English](README.md) | **Português (Brasil)**

O **Adaptive AI Orchestrator** é um sistema de orquestração de IA para analisar projetos, decompor trabalho, coordenar agentes, selecionar modelos e recursos, avaliar resultados, replanejar execuções e preservar continuidade.

> **Status de desenvolvimento:** desenvolvimento ativo  
> **Status de produção:** ainda não pronto para produção

## Visão geral

O Adaptive não é um único agente, uma única skill ou apenas um roteador de modelos. Ele funciona como uma camada estruturada de coordenação entre desenvolvedores, agentes de IA, skills, modelos, ferramentas e runtimes externos.

Entre suas responsabilidades estão:

- análise de contexto e restrições;
- decomposição de trabalho em Work Units;
- coordenação multiagente;
- seleção de skills e recursos;
- controle de dependências e paralelismo;
- avaliação de resultados;
- replanejamento;
- continuidade e evidências;
- observabilidade;
- aprendizado operacional.

O desenvolvedor continua sendo a autoridade final para decisões importantes do projeto.

## Nova máquina

Em Linux Mint / Ubuntu / Debian compatível, o ponto de entrada oficial é:

```bash
curl -fsSL https://raw.githubusercontent.com/oliveiraariel/adaptive-ai-orchestrator/main/install.sh | bash
```

O bootstrap instala ou sincroniza o Adaptive, Ariel Agent Skills e OpenClaw, prepara o ambiente Python, bridge, Gateway, SecretRefs, verificações E2E e atalhos locais.

## Comunicação entre componentes — AMEP v1

O Adaptive usa o **Adaptive Message Exchange Protocol (AMEP) v1** para comunicação de payloads relevantes entre Planner, Adaptive, Workers, Evaluator, Sentinel/watchers e futuros subagentes.

Regra principal:

```text
payload completo
→ persistência atômica
→ manifest/hash
→ MESSAGE_REF compacto
→ verificação pelo destinatário
```

O histórico de chat continua útil para progresso e apresentação humana, mas não é tratado como canal autoritativo para grandes payloads de máquina.

## Execução multiagente

O fluxo de alto nível é:

```text
Projeto
→ Análise de contexto
→ Planejamento / Work Graph
→ Ready Frontier
→ Delegação paralela segura
→ Workers independentes
→ Avaliação
→ Fan-in / dependências
→ Replanejamento limitado
→ Continuidade e evidências
```

## Desenvolvimento local

Python 3.12 ou superior:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test,gateway]"
python -m pytest -q
```

## Documentação completa

O `README.md` em inglês é a referência principal de apresentação e contém a documentação técnica mais detalhada.

Pontos importantes:

- `docs/architecture/` — arquitetura;
- `docs/prompts/` — prompts operacionais;
- `docs/runtime-intelligence.md` — diagnóstico de runtime;
- `docs/problem-solving-learning.md` — aprendizado orientado por experiência;
- `docs/architecture/ADAPTIVE-MESSAGE-EXCHANGE-PROTOCOL.md` — AMEP v1.

Esta página em português existe como ponto de entrada acessível e resumido. A documentação normativa permanece nos arquivos técnicos correspondentes.
