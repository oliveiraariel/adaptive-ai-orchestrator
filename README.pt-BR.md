# Adaptive AI Orchestrator — Português (Brasil)

[English](README.md) | **Português (Brasil)**

**Orquestração multiagente para planejar, executar, avaliar, recuperar e aprender durante projetos de aplicações de software.**

O **Adaptive AI Orchestrator** é um sistema de software — não um único agente, uma única Skill ou apenas um roteador de modelos — que fornece uma camada estruturada de coordenação entre desenvolvedores, agentes de IA, Skills, modelos, ferramentas e runtimes externos.

> **Status de desenvolvimento:** desenvolvimento ativo  
> **Status de produção:** ainda não pronto para produção

## Visão geral

Entre suas responsabilidades estão:

- análise de contexto, objetivos, requisitos e restrições;
- decomposição de trabalho em Work Units e Work Graph;
- coordenação multiagente e paralelismo orientado por dependências;
- seleção de Skills, modelos e recursos;
- avaliação independente de resultados;
- replanejamento e recuperação persistente;
- **Recovery Loop** para retrabalho, busca de solução, reteste e aprendizagem automática;
- continuidade, evidências e observabilidade;
- diagnóstico de runtime/provider e aprendizagem operacional.

O desenvolvedor continua sendo a autoridade final para decisões importantes do projeto. O Orchestrator permanece a autoridade central de execução; subsistemas como o Recovery Loop são coordenados por ele e não o substituem.

## Fluxo de alto nível

```text
Projeto
→ Análise de contexto
→ Planejamento / Work Graph
→ Ready Frontier
→ Delegação paralela segura
→ Workers independentes
→ Avaliação
→ Fan-in / dependências
→ Replanejamento / Recovery Loop quando necessário
→ Reteste
→ Aprendizagem validada
→ Continuidade e evidências
```

## Mapa da documentação

A organização documental separa apresentação, contexto operacional atual, arquitetura, processo e histórico. Assim, novas funcionalidades não devem empurrar a descrição principal do projeto para baixo no README.

- `README.md` / `README.pt-BR.md` — páginas estáveis de apresentação do projeto;
- `CONTEXT.md` — ponto atual de retomada para humanos e agentes de IA;
- `PROJECT-KNOWLEDGE-MANIFEST.yaml` — mapa de autoridade e recuperação do conhecimento;
- `docs/architecture/` — arquitetura canônica e contratos de subsistemas;
- [`docs/architecture/RECOVERY-LOOP.md`](docs/architecture/RECOVERY-LOOP.md) — documento canônico do Recovery Loop;
- `docs/process/` — governança, continuidade, gates e processo de execução;
- `docs/prompts/` — prompts operacionais;
- `docs/runbooks/`, `docs/incidents/` e `docs/reviews/` — diagnóstico, evidência de campo e revisões;
- `knowledge/` — conhecimento operacional reutilizável e governado;
- `specifications/` — especificações normativas do projeto e protocolos.

A regra de apresentação é: **uma nova capacidade deve atualizar seu documento canônico e receber apenas um resumo/link no README**, em vez de criar uma nova seção detalhada antes da visão geral.

## Recovery Loop

**Recovery Loop** é o nome curto canônico de **Adaptive Persistent Recovery & Learning Lifecycle**.

É o subsistema coordenado pelo Orchestrator para tratamento persistente de retrabalho, conflitos técnicos, `RETURNED`, esgotamento de estratégias, novas tentativas, retestes e aprendizagem automática. Uma tarefa normal não precisa ser solicitada “pelo Recovery Loop”: o Orchestrator deve ativá-lo proativamente quando a evidência de execução indicar necessidade.

Documento principal: [`docs/architecture/RECOVERY-LOOP.md`](docs/architecture/RECOVERY-LOOP.md).

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

O Adaptive utiliza Work Graph, Ready Frontier, workers independentes, avaliação contínua e fan-in para explorar paralelismo útil sem transformar o número de workers em objetivo.

O `max_concurrency` é um teto, não uma meta. Dependências reais, segurança de escrita, qualidade de resultado e custo de coordenação prevalecem sobre maximizar paralelismo.

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

- `docs/architecture/RECOVERY-LOOP.md` — Recovery Loop;
- `docs/architecture/ADAPTIVE-MESSAGE-EXCHANGE-PROTOCOL.md` — AMEP v1;
- `docs/runtime-intelligence.md` — diagnóstico de runtime/provider;
- `docs/problem-solving-learning.md` — aprendizado orientado por experiência;
- `docs/prompts/` — prompts operacionais.

Esta página em português existe como ponto de entrada acessível e resumido. A documentação normativa permanece nos arquivos técnicos correspondentes.
