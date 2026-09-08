# Orchestrator New Chat Context — v0.8

**Projeto:** Adaptive AI Orchestrator  
**Status:** Fase 3 em andamento  
**Capacidade atual validada em repositório:** multiagent project execution v0.4  
**Próximo Work Unit oficial:** `WU-055 — Runtime Event Monitoring`

## 1. Finalidade

Este documento é o contexto operacional curto para retomar o Adaptive AI Orchestrator após a integração da camada superior de execução multiagente v0.4.

Ele complementa, e não substitui, as fontes normativas do projeto.

## 2. Ordem de leitura para retomada

1. `CONTEXT.md`
2. `docs/process/MULTIAGENT-PROJECT-EXECUTION-v0.4-GATE.md`
3. `docs/process/ORCHESTRATOR-NEW-CHAT-CONTEXT-v0.8.md`
4. `docs/process/ORCHESTRATOR-DEVELOPMENT-CONTINUITY-v0.8.md`
5. `PROJECT-KNOWLEDGE-MANIFEST.yaml`
6. documentos normativos/arquiteturais necessários à tarefa
7. plano/gate da Fase 3 quando a tarefa atingir WU-055 ou posteriores

Os documentos operacionais v0.7 permanecem como snapshot histórico anterior ao fechamento multiagente v0.4 e não devem prevalecer sobre este contexto quando houver divergência de estado.

## 3. Estado consolidado

Concluído e validado no repositório:

- núcleo do Adaptive;
- integração real mínima com OpenClaw Gateway no caminho previamente validado;
- `adaptive-orchestrator run` para uma Work Unit governada;
- `adaptive-orchestrator orchestrate` para execução de projeto multiagente;
- planejamento em Work Graph;
- Ready Frontier dinâmica;
- scheduler contínuo e limitado;
- workers efêmeros em sessões/executions independentes;
- fan-out e fan-in por dependências aceitas;
- backend/backend, frontend/frontend e backend/frontend quando dependências e política permitem;
- escalabilidade dinâmica, com evidência automatizada de seis Work Units independentes;
- bounded retries e identidades distintas por tentativa;
- bounded additive replanning;
- HUMAN_ACTION fora do runtime autônomo;
- write ownership explícito para `filesystem.write`;
- CI corrigida para fail-closed;
- 284 testes passando no merge v0.4.

## 4. Semântica atual do scheduler

O scheduler não trabalha por waves com barreira obrigatória.

```text
Ready Frontier
→ despacha trabalho útil até o limite seguro
→ primeiro resultado retorna
→ Adaptive avalia/finaliza
→ dependências aceitas avançam
→ frontier é recalculada
→ novo worker pode ocupar o slot liberado
→ outros workers independentes continuam ativos
```

`max_concurrency` é teto, não meta. O Adaptive deve buscar economicidade de contexto/tokens e evitar fan-out artificial.

## 5. Segurança de escrita

A v0.4 não reivindica isolamento automático por Git worktree/container.

No checkout compartilhado, writers só podem compartilhar execução quando seus `write_paths` são literais, relativos ao repositório e não sobrepostos.

Se a governança do projeto for mais rígida — por exemplo, exigir worktree/branch isolado para qualquer writer paralelo — essa regra prevalece. O Adaptive deve serializar writers até que o runtime comprove o isolamento exigido.

## 6. OpenClaw boundary

A bridge permanece fina:

```text
OpenClaw
→ adaptive-orchestrator-bridge --multi-agent
→ adaptive-orchestrator orchestrate
→ planner / graph / frontier / workers / evaluation / replan
```

OpenClaw não redefine o estado, a política, os gates ou a semântica do Adaptive.

## 7. Evidência atual

Merge principal da implementação v0.4:

`f90a2f02f6217549837dc6d4b1f14c6abebc9f34`

CI de `main`:

- Orchestrator Validation: PASS;
- Bootstrap Validation: PASS;
- pytest: 284 passed.

Ariel Agent Skills foi alinhado ao project mode multiagente e sua validação em `main` também passou.

## 8. Limite de validação ainda aberto

Ainda falta executar, no ambiente Linux/OpenClaw instalado do usuário:

```bash
adaptive-openclaw-update
adaptive-openclaw-verify --e2e
```

Esse E2E é a prova do ambiente instalado, não uma condição para negar que o código/CI do v0.4 já está integrado no repositório.

## 9. Próximo gate oficial

O roadmap principal continua:

```text
WU-055 Runtime Event Monitoring
        ↓
WU-056 Durable Execution / Recovery Integration
        ↓
WU-057 Operational Acceptance
        ↓
Production Hardening
```

A introdução do v0.4 multiagente não elimina essas Work Units e não torna o projeto production-ready.

## 10. Regra de retomada

Ao retomar:

```text
ler contexto atual
→ verificar estado real
→ respeitar fontes normativas
→ não repetir discovery já fechado sem nova evidência
→ selecionar a menor frontier útil
→ executar dentro da autoridade
→ avaliar resultados
→ replanejar somente quando necessário
→ registrar handoff/evidência
```

Se houver conflito documental, não resolver silenciosamente; comparar autoridade, versão, escopo e evidência.