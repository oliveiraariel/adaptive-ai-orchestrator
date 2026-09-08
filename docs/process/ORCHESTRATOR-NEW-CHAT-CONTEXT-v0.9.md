# Orchestrator New Chat Context — v0.9

**Projeto:** Adaptive AI Orchestrator  
**Status:** Fase 3 em andamento  
**Capacidade atual:** multiagent project execution v0.4 implementada, validada em CI e comprovada no ambiente Linux/OpenClaw instalado, inclusive com o verifier semântico corrigido  
**Próximo Work Unit oficial:** `WU-055 — Runtime Event Monitoring`

## 1. Finalidade

Este é o contexto operacional curto após o fechamento do E2E multiagente instalado e o hardening do bootstrap derivado dos erros encontrados durante essa prova.

Ele complementa, e não substitui, as fontes normativas do projeto.

## 2. Ordem de leitura para retomada

1. `CONTEXT.md`
2. `docs/process/MULTIAGENT-PROJECT-EXECUTION-v0.4-DEPLOYMENT-E2E.md`
3. `docs/process/MULTIAGENT-PROJECT-EXECUTION-v0.4-GATE.md`
4. `docs/process/ORCHESTRATOR-NEW-CHAT-CONTEXT-v0.9.md`
5. `docs/process/ORCHESTRATOR-DEVELOPMENT-CONTINUITY-v0.9.md`
6. `PROJECT-KNOWLEDGE-MANIFEST.yaml`
7. documentos normativos/arquiteturais necessários à tarefa
8. plano/gate da Fase 3 quando a tarefa atingir WU-055 ou posteriores

v0.8 e anteriores permanecem snapshots históricos.

## 3. Estado consolidado

Está comprovado:

- `adaptive-orchestrator run` para uma Work Unit governada;
- `adaptive-orchestrator orchestrate` para Work Graph multiagente;
- Ready Frontier dinâmica e scheduler continuamente reabastecido;
- fan-out/fan-in por resultados aceitos;
- paralelismo lateral backend/backend, frontend/frontend e backend/frontend quando seguro;
- escalabilidade testada em CI até seis Work Units independentes;
- 284 testes no gate v0.4 original;
- 289 testes no `main` pós-hardening do bootstrap;
- Ariel Agent Skills alinhado ao project mode;
- OpenClaw Gateway real operacional no Linux Mint do usuário;
- E2E 1: Adaptive → OpenClaw → Adaptive — PASS;
- E2E 2: Adaptive → 3 workers OpenClaw paralelos → fan-in → Adaptive — PASS;
- E2E 3: OpenClaw → bridge → Adaptive → 3 workers → fan-in → OpenClaw — PASS;
- reexecução final com `adaptive-openclaw-verify --quick` usando o verifier corrigido — PASS, com `fan_in_present=true`, `max_parallelism_observed=3`, `ok=true` e `status_completed=true`.

## 4. Incidentes aprendidos e incorporados

Dois problemas de bootstrap/test harness foram descobertos sem invalidar o runtime:

1. os launchers existiam em `~/.local/bin`, mas o shell ativo não possuía esse diretório no PATH;
2. o E2E inbound foi marcado como erro porque o agente escreveu `Max parallelism observed: 3` em vez do literal `max_parallelism_observed`.

O bootstrap foi endurecido para:

- persistir `~/.local/bin` nos arquivos de startup do shell;
- instalar recovery launchers antes do último E2E;
- usar `/skill adaptive-orchestrator-bridge` no teste inbound;
- consultar `chat.history` como segunda fonte de evidência;
- validar `COMPLETED + parallelism >= 3 + fan-in marker` semanticamente;
- possuir regressão automatizada para output machine-style e humanized;
- fazer o updater atual auto-reparar launchers e registro de PATH após sincronizar o repositório;
- documentar a transição única em que um updater antigo pode baixar código novo, mas não executar retroativamente a nova lógica dentro do processo Bash já iniciado;
- classificar falha por camada antes de reinstalar componentes.

## 5. Limites que permanecem

A v0.4 continua não reivindicando:

- produção pronta;
- durable execution/recovery completo;
- observabilidade operacional final;
- managed-worktree/container isolation automático para todos os writers paralelos.

`max_concurrency` continua sendo teto, não meta; economicidade de tokens/contexto prevalece sobre fan-out artificial.

## 6. Próximo gate oficial

```text
WU-055 Runtime Event Monitoring
        ↓
WU-056 Durable Execution / Recovery Integration
        ↓
WU-057 Operational Acceptance
        ↓
Production Hardening
```

## 7. Regra de retomada

Ao retomar desenvolvimento, não repita o bootstrap/E2E por padrão apenas para redescobrir fatos já provados. Reexecute quando houver mudança de runtime, bridge, Gateway, scheduler, bootstrap ou ambiente que materialmente possa invalidar a evidência.

Para problemas de instalação/recuperação, leia `bootstrap/TROUBLESHOOTING.md` e `bootstrap/RECOVERY-PROMPT.md` antes de improvisar correções.
