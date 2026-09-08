# Orchestrator Development Continuity — v0.9

**Projeto:** Adaptive AI Orchestrator  
**Registro:** estado operacional após o E2E multiagente real no Linux Mint e hardening do bootstrap  
**Fase:** 3 em andamento  
**Próximo Work Unit:** `WU-055 — Runtime Event Monitoring`

## 1. Objetivo deste registro

Preservar a continuidade depois que a capacidade v0.4 deixou de ser apenas repository/CI validated e passou também pelo fluxo real instalado OpenClaw ↔ bridge ↔ Adaptive ↔ workers.

## 2. Capability comprovada

O Adaptive possui e comprovou no ambiente instalado:

```text
OpenClaw
→ adaptive-orchestrator-bridge
→ Adaptive project mode
→ validated Work Graph
→ Ready Frontier
→ 3 workers reais paralelos no Gateway
→ accepted results
→ fan-in
→ Adaptive
→ OpenClaw response
```

O E2E direto Adaptive também comprovou três sessões paralelas e fan-in.

## 3. Evidência local

O update local instalou Adaptive `0.4.0`, executou a suíte e registrou:

```text
284 passed
16 skills
19 capabilities
```

O Gateway OpenClaw `2026.9.2 (3928bad)` estava `running`, com `Read probe: ok` e listening em loopback.

Resultados:

```text
E2E 1 — single Work Unit round trip: PASS
E2E 2 — 3 parallel workers + fan-in: PASS
E2E 3 — inbound bridge + project mode + parallel workers + fan-in: PASS
```

A evidência completa está em `MULTIAGENT-PROJECT-EXECUTION-v0.4-DEPLOYMENT-E2E.md`.

## 4. Falso negativo encontrado no E2E 3

O test harness antigo exigia a substring exata `max_parallelism_observed`.

O agente retornou:

```text
Max parallelism observed: 3
```

junto com:

```text
Project status: COMPLETED
Fan-in: ADAPTIVE_MULTIAGENT_FANIN_OK
All results were accepted.
```

A sessão estava `done`; portanto o erro era de assertion/presentation, não do runtime.

## 5. Hardening implementado

O bootstrap passa a ter:

- `bootstrap/lib/e2e_evidence.py` para evidência semântica;
- testes de regressão para machine-style e humanized output;
- `/skill adaptive-orchestrator-bridge` como entrypoint inbound automatizado;
- `chat.history` como fonte complementar de evidência;
- exigência semântica `COMPLETED + max_parallelism >= 3 + fan-in marker`;
- diagnostic session key quando a evidência for insuficiente;
- `bootstrap/TROUBLESHOOTING.md` com classificação de falhas;
- recovery prompt atualizado.

## 6. Hardening de launchers/PATH

Foi observado que `adaptive-openclaw-update` existia em `~/.local/bin`, mas o PATH do shell não incluía esse diretório.

O bootstrap passa a registrar `~/.local/bin` idempotentemente em shell startup files e a explicar a fronteira inevitável: um processo filho não pode alterar o environment de um terminal pai já aberto.

A correção de sessão corrente permanece:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

O setup instala os launchers antes do último E2E para manter uma rota de recuperação mesmo se o gate de runtime final falhar.

## 7. Regra de diagnóstico aprendida

A partir deste ponto, recuperação deve seguir a primeira fronteira real que falhar:

```text
PATH / command discovery
→ Git sync
→ Python/tests
→ OpenClaw config
→ Gateway RPC
→ skill visibility
→ outbound single-unit
→ direct multiagent
→ inbound bridge
→ semantic evidence formatting
```

Uma falha superior não autoriza reinstalar silenciosamente uma camada inferior já comprovada.

## 8. Warnings versus blockers

O warning do Gateway por Node/NVM é manutenção futura quando o RPC e os E2Es passam. Não deve disparar `gateway install --force` automaticamente.

`Capability: read-only` em um status probe também não substitui a evidência real de execução do E2E.

## 9. Estado arquitetural que não mudou

O scheduler continua:

- contínuo, não barrier-based;
- limitado por `max_concurrency`;
- econômico em workers/contexto;
- dependente de resultados aceitos;
- com bounded retry/replan;
- conservador em writes no checkout compartilhado.

Managed worktree/container isolation automático ainda não faz parte da capability v0.4 comprovada.

## 10. Próximo ponto exato de retomada

O próximo Work Unit oficial continua:

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

Depois seguem `WU-056`, `WU-057` e production hardening.

## 11. Relação com snapshots anteriores

v0.8 registra o estado imediatamente após o repository-side gate v0.4 e antes da prova instalada.

v0.9 prevalece para o estado operacional atual porque incorpora o deployment E2E e o hardening derivado da execução real.
