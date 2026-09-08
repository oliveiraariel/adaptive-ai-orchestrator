# Orchestrator Development Continuity — v0.8

**Projeto:** Adaptive AI Orchestrator  
**Registro:** estado operacional após o fechamento de repositório da capacidade multiagente v0.4  
**Fase:** 3 em andamento  
**Próximo Work Unit:** `WU-055 — Runtime Event Monitoring`

## 1. Objetivo deste registro

Preservar o ponto de continuidade após a introdução da camada superior de project orchestration multiagente, sem reescrever ou apagar os snapshots operacionais anteriores.

As especificações e arquitetura continuam normativas; este documento registra o estado operacional comprovado.

## 2. Estado concluído

O Adaptive possui, no estado atual do repositório:

- Domain/Application/Infrastructure boundaries existentes;
- planejamento e Work Units;
- Agent/Skill analysis e resource selection;
- delegation, evaluation e replanning governados;
- runtime boundary e OpenClaw adapter;
- CLI single-unit `run`;
- CLI project-level `orchestrate`;
- `ProjectExecutionPlan` validado como Work Graph;
- Ready Frontier dinâmica;
- scheduler contínuo com concorrência limitada;
- workers lógicos efêmeros em sessões/executions independentes;
- claims e identidades por tentativa;
- dependências e fan-in baseados em resultados aceitos;
- bounded additive replanning;
- política de autoridade e HUMAN_ACTION;
- write-scope safety no checkout compartilhado;
- bridge OpenClaw em modo multiagente;
- prompts globais atualizados;
- integração documental correspondente no SGFP.

## 3. Mudança arquitetural v0.4

Antes, o entrypoint inbound comprovado executava uma Work Unit governada por vez.

Agora existe uma camada superior:

```text
broad objective
→ planning
→ Work Graph
→ Ready Frontier
→ bounded dispatch
→ parallel workers
→ first result returned
→ evaluation/finalization
→ dependency advancement
→ frontier recomputation
→ continuous slot replenishment
→ fan-in / bounded replan
```

O scheduler não exige que todos os workers de uma geração terminem antes de iniciar uma Work Unit que se tornou READY.

## 4. Paralelismo suportado

A decisão de paralelizar é derivada do grafo, política, segurança e orçamento de concorrência — não do nome da camada.

Assim, são válidos quando independentes:

```text
backend + backend
frontend + frontend
backend + frontend
implementation + tests/review
research + architecture
```

A quantidade de workers é dinâmica. O código e os testes exercitam 1, 2 e 6 workers e o contrato suporta outros valores dentro do bound configurado. `max_concurrency` é teto, não objetivo de utilização.

## 5. Economicidade

O Adaptive deve preferir a menor combinação útil de trabalho e skills:

- não criar workers apenas para preencher slots;
- não duplicar discovery conhecido;
- não enviar contexto irrelevante;
- selecionar o menor conjunto compatível de skills;
- limitar dependency-result context;
- fazer fan-in somente quando existe convergência real.

## 6. Segurança e autoridade

### 6.1 Side effects

O planner não pode ampliar a autoridade concedida pelo caller.

### 6.2 Escrita

`filesystem.write` exige `write_paths` explícitos, literais e relativos ao repositório.

No checkout compartilhado, writers com ownership sobreposto são serializados.

A v0.4 não reivindica isolamento automático por managed worktree/container. Projetos com política mais rigorosa devem manter writers serializados até o runtime fornecer e comprovar o isolamento exigido.

### 6.3 Humano

`HUMAN_ACTION` não é delegada ao runtime autônomo.

## 7. Replanning e retries

Retries são limitados e cada tentativa recebe identidade distinta.

Replanning é aditivo, limitado e revalida o grafo. Um sinal de replan não autoriza um worker a criar trabalho fora da governança do Adaptive.

## 8. Evidência de validação v0.4

Merge principal:

`f90a2f02f6217549837dc6d4b1f14c6abebc9f34`

Evidência em `main`:

```text
Orchestrator Validation: PASS
Bootstrap Validation:    PASS
pytest:                  284 passed
```

A CI foi corrigida para instalar o extra Gateway e falhar corretamente quando pytest falhar (`pipefail`). Portanto, somente os runs posteriores a essa correção são aceitos como evidência do gate v0.4.

Ariel Agent Skills também foi atualizado para o modo project-level multiagente e seu workflow `Validate skills` passou em `main`.

## 9. Evidência funcional automatizada relevante

A suíte inclui, entre outros cenários:

- contrato desbloqueando backend + frontend em paralelo e posterior fan-in;
- slot liberado sendo reutilizado antes de outro worker independente terminar;
- seis Work Units independentes com `max_concurrency=6`;
- writers disjuntos executando em paralelo;
- writers com path ownership sobreposto sendo serializados;
- write sem autorização bloqueado antes do runtime;
- retries com ids distintos além da segunda tentativa;
- HUMAN_ACTION não delegada;
- bounded replan adicionando trabalho necessário.

## 10. Deployment E2E pendente

O que não pode ser provado pelo GitHub é o estado da instalação local do usuário: Gateway, credenciais, provider/model, bridge carregada e concorrência real no runtime instalado.

A prova local restante é:

```bash
adaptive-openclaw-update
adaptive-openclaw-verify --e2e
```

O verify atual contém:

1. round trip single Work Unit;
2. project mode com três workers paralelos e fan-in;
3. OpenClaw inbound → bridge → Adaptive project mode → workers → Adaptive → OpenClaw.

## 11. O que permanece aberto no projeto

```text
WU-055 Runtime Event Monitoring
WU-056 Durable Execution / Recovery Integration
WU-057 Operational Acceptance
production telemetry
production security hardening
production deployment
managed-worktree/runtime isolation integration para writers paralelos mais fortes
```

O Adaptive ainda não deve ser classificado como production-ready.

## 12. Próximo ponto exato de retomada

Depois do E2E local de implantação, ou em paralelo quando a tarefa for puramente de repositório e não depender desse ambiente, o próximo Work Unit oficial continua sendo:

```text
WU-055 — Runtime Event Monitoring
```

Objetivo macro:

```text
runtime lifecycle events
→ normalization
→ correlation run/session/Work Unit
→ telemetry/evidence
→ reconnect/reconciliation semantics
```

## 13. Relação com snapshots anteriores

`docs/process/ORCHESTRATOR-NEW-CHAT-CONTEXT.md` e `docs/process/ORCHESTRATOR-DEVELOPMENT-CONTINUITY.md` registram o estado v0.7 anterior ao fechamento multiagente v0.4.

Eles permanecem úteis para histórico, mas este v0.8 e o gate `MULTIAGENT-PROJECT-EXECUTION-v0.4-GATE.md` devem prevalecer para o estado operacional posterior ao merge v0.4.