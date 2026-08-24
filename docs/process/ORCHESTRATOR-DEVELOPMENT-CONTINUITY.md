# Orchestrator Development Continuity

**Projeto:** Adaptive AI Orchestrator
**Documento:** Registro de Continuidade do Desenvolvimento
**Versão do registro:** 0.7
**Status:** Fase 3 — runtime compatibility validated; event monitoring, durable recovery and operational acceptance remain open

---

# 1. Finalidade

Este documento registra o estado operacional do desenvolvimento do **Adaptive AI Orchestrator**.

Sua finalidade é permitir a continuidade entre sessões e chats preservando:

- decisões consolidadas;
- estado real da implementação;
- evidências de validação;
- limitações conhecidas;
- dependências externas;
- pendências;
- ponto exato de retomada.

Este documento **não substitui** requisitos, arquitetura, design, SDD ou outros documentos normativos do projeto.

Ele responde principalmente:

> **Onde estamos, o que já foi feito, o que foi validado e qual é o próximo passo seguro?**

---

# 2. Identidade do projeto

O projeto atual é:

> **Adaptive AI Orchestrator**

O Orchestrator é um sistema que deve compreender projetos, organizar trabalho, selecionar recursos, delegar execução, avaliar resultados, replanejar, preservar continuidade e apoiar evolução governada.

A **Professional Software Engineering Skill** é conhecimento legado de alto valor. Ela não deve ser confundida com a identidade normativa do Orchestrator.

Quando conhecimento legado for reutilizado:

```text
conhecimento legado
→ avaliar compatibilidade
→ adaptar ao Orchestrator
→ consolidar decisão específica
```

---

# 3. Regra de autoridade

As fontes devem ser interpretadas pelo escopo ao qual pertencem.

## 3.1 Orchestrator

A autoridade normativa segue, conforme aplicável:

```text
Requirements
→ Architecture
→ Design
→ Reviews / Decisions
→ Implementation Plan
→ Implementation
→ Verification / Evidence
```

## 3.2 Legado

Os documentos da Professional Software Engineering Skill permanecem como conhecimento histórico e metodológico.

Eles não substituem as decisões específicas do Orchestrator.

## 3.3 Continuidade

Este documento é a referência operacional de continuidade do Orchestrator.

Quando houver divergência:

```text
fonte normativa apropriada
        ↓
verificar decisão consolidada
        ↓
avaliar impacto
        ↓
atualizar continuidade
```

Não alterar decisões silenciosamente.

---

# 4. Estado geral

## Fase 1 — Implementação do núcleo

**Status: CONCLUÍDA**

Foram implementados e verificados:

- Domain;
- Application;
- Infrastructure in-memory;
- Agent Runtime boundary;
- Agent / Skill analysis;
- Resource Selection;
- Delegation;
- Evaluation;
- Replanning;
- Continuity;
- Evidence;
- Learning Candidate;
- Failure / Recovery;
- Vertical Slices;
- End-to-End;
- Architecture Verification;
- Traceability Verification;
- Practical Validation.

A fase foi encerrada com o repositório limpo e sincronizado com `origin/main`.

---

# 5. Fase 2 — Evolução operacional

**Status: CONCLUÍDA**

A Fase 2 ampliou o núcleo para aproximá-lo de um Orchestrator operacional.

## 5.1 Persistência

Foi estabelecida a fronteira:

```text
Application
    ↓
ProjectStateRepository
    ↓
Durable Persistence Adapter
```

O objetivo é manter separada a lógica de domínio da tecnologia de persistência.

A evolução inclui:

- estado persistente;
- versionamento;
- controle de concorrência;
- persistência coordenada do estado relevante do projeto;
- capacidade de recuperação após reinício.

## 5.2 Resume

Foi estabelecido o conceito de retomada de projeto após reinício.

Regras importantes:

```text
COMPLETED
→ não retomar automaticamente

ACTIVE / RUNNING
→ pode exigir recuperação

BLOCKED
→ exige decisão / replanning conforme o caso

stale version
→ conflito
```

Resume não significa repetir automaticamente uma execução já concluída.

---

# 6. Runtime

Foi preservado o seam:

```text
AgentRuntime
    ↓
OpenClawAdapter
```

O núcleo não deve depender diretamente do runtime externo.

A primeira integração concreta foi preparada por meio de adapter/cliente de execução.

Estado atual:

```text
runtime boundary              ✅
adapter boundary              ✅
CLI-compatible integration    ✅
OpenClaw Gateway real         ✅
WebSocket/RPC real            ✅
real vertical slice           ✅
live event stream             ⏳
durable recovery              ⏳
operational acceptance        ⏳
```

A compatibilidade mínima com uma instalação real do OpenClaw foi validada no caminho documentado em `OPENCLAW-GATEWAY-RESEARCH-WU-051.md`, `OPENCLAW-GATEWAY-INTEGRATION-WU-052.md` e `PHASE-3-GATE-REPORT.md`.

O próximo trabalho deve concentrar-se em **Runtime Event Monitoring**, sem repetir a investigação básica do Gateway salvo mudança de versão, protocolo ou evidência contraditória.

Não inventar comportamento externo não verificado.

---

# 7. Telemetria e operação

Foi criada uma fronteira de telemetria independente da implementação de domínio.

Conceitos preparados:

```text
TelemetrySink
TelemetryEvent
ExecutionCost
ExecutionLatency
```

O objetivo é permitir observabilidade sem acoplamento direto do Domain a um vendor ou exporter.

Estado:

```text
telemetry boundary       ✅
cost representation      ✅
latency representation   ✅
production telemetry     ⏳
```

---

# 8. Recovery

O modelo de recovery foi fortalecido para distinguir:

```text
RETRY
RESELECT_RESOURCE
REPLAN
ESCALATE
STOP
```

e controlar tentativas por policy.

Princípio:

```text
falha
→ classificar
→ decidir ação
→ aplicar limite
→ registrar evidência
```

Retry ilimitado não é permitido.

---

# 9. Resource Policy

A seleção de recursos passou a admitir policy explícita.

As políticas podem restringir:

```text
agents
skills
models
providers
runtimes
```

e também negar determinados recursos.

Princípio:

```text
candidate
→ technical eligibility
→ policy filter
→ scoring / selection
→ ResourceConfiguration
```

A existência de um recurso não cria automaticamente uma necessidade de utilizá-lo.

---

# 10. Learning governado

O projeto mantém a distinção:

```text
LearningCandidate
≠
permanent policy
```

Um candidato validado pode gerar uma proposta de promoção, mas a promoção deve permanecer governada.

Possíveis destinos:

```text
knowledge
rule candidate
skill update
prompt revision
agent configuration
model-selection heuristic
```

O aprendizado não deve alterar silenciosamente a política do Orchestrator.

---

# 11. CI e hardening

Foram preparados mecanismos de:

- validação automatizada;
- configuração de testes;
- verificação de compilação;
- boundaries de pacote;
- execução consistente da suíte.

O hardening de produção ainda não está encerrado.

Pendências:

```text
security hardening
secrets management
deployment model
operational runbooks
production observability
```

---

# 12. Evidência de validação

Durante a consolidação da Fase 2, a cópia de trabalho utilizada para a validação apresentou:

```text
237 passed
PRACTICAL VALIDATION: PASS
compileall: PASS
```

Esses números correspondem ao snapshot utilizado na execução da Fase 2.

Na validação posterior da integração real com OpenClaw Gateway foi registrado outro snapshot:

```text
207 tests passed
real OpenClaw Gateway compatibility: PASS
real output: ORCHESTRATOR_GATEWAY_OK
```

Esses snapshots possuem escopos e momentos distintos e **não devem ser combinados como se fossem a mesma execução**.

Ao trabalhar em outro clone ou após mudanças relevantes, a suíte completa deve ser executada novamente antes de declarar o estado atual.

A validação local mais recente é a evidência autoritativa do estado efetivamente presente no clone.

---

# 13. O que está concluído

```text
IMPLEMENTATION CORE                 ✅
DOMAIN                              ✅
APPLICATION                         ✅
IN-MEMORY INFRASTRUCTURE             ✅
RESOURCE SELECTION                   ✅
DELEGATION                          ✅
EVALUATION                          ✅
REPLANNING                          ✅
CONTINUITY / LEARNING MODEL         ✅
FAILURE / RECOVERY MODEL            ✅
PERSISTENCE BOUNDARY                ✅
RESUME MODEL                         ✅
RUNTIME BOUNDARY                     ✅
OPENCLAW ADAPTER BOUNDARY            ✅
TELEMETRY BOUNDARY                   ✅
RESOURCE POLICY                      ✅
GOVERNED LEARNING                    ✅
CI / VALIDATION FOUNDATION           ✅
```

---

# 14. O que ainda não está concluído

```text
RUNTIME EVENT MONITORING                 ⏳
EVENT STREAM / RECONCILIATION            ⏳
DURABLE EXECUTION / RECOVERY             ⏳
PRODUCTION TELEMETRY                     ⏳
PRODUCTION SECURITY HARDENING            ⏳
PRODUCTION DEPLOYMENT                    ⏳
FINAL OPERATIONAL ACCEPTANCE             ⏳
```

A integração real mínima com OpenClaw Gateway e a validação WebSocket/RPC já foram concluídas para o caminho testado.

O projeto **não deve ser declarado production-ready** neste ponto.

---

# 15. Próximo gate

O próximo gate oficial é:

```text
WU-055 — RUNTIME EVENT MONITORING
```

Objetivo:

1. identificar os eventos mínimos de lifecycle necessários;
2. assinar eventos relevantes do Gateway;
3. normalizar estado de execução;
4. preservar correlação entre `runId`, sessão e Work Unit;
5. integrar eventos com telemetry/evidence;
6. definir semântica de reconnect/reconciliation;
7. verificar comportamento com testes e evidência operacional.

---

# 16. Próxima sequência prevista

```text
WU-055 Runtime Event Monitoring
        ↓
WU-056 Durable Execution / Recovery
        ↓
WU-057 Operational Acceptance
        ↓
Production Hardening
```

Não iniciar produção antes de validar essa sequência.

---

# 17. Regra de trabalho

A construção continua seguindo:

```text
propor
→ identificar indefinições
→ pesquisar quando necessário
→ testar hipótese
→ decidir
→ consolidar
→ implementar
→ verificar
→ registrar evidência
→ atualizar continuidade
→ versionar
→ prosseguir
```

Não pular diretamente da ideia para código quando houver uma decisão arquitetural ainda não resolvida.

---

# 18. Regra de perguntas

Perguntar somente quando existir:

```text
ambiguidade material
conflito entre fontes
impacto desconhecido
decisão fora da autoridade
dependência externa não disponível
bloqueio real
```

Quando a decisão puder ser resolvida com evidência técnica suficiente, resolver autonomamente e registrar a decisão.

---

# 19. Regra contra reinicialização

Ao retomar:

```text
NÃO:
→ reconstruir arquitetura do zero
→ reescrever o Design sem necessidade
→ ignorar implementação existente
→ tratar legado como autoridade automática
→ repetir fases concluídas
```

Primeiro:

```text
ler
→ verificar
→ localizar estado
→ confirmar evidência
→ continuar
```

---

# 20. Próximo ponto exato de retomada

**Estado atual:**

```text
Fase 1 concluída.
Fase 2 concluída.
Fase 3 em andamento.
OpenClaw Gateway compatibility: VALIDATED.
```

**Ponto de retomada:**

```text
WU-055 — Runtime Event Monitoring
```

**Pré-requisito externo:**

```text
OpenClaw real disponível
+
versão identificada
+
Gateway disponível
+
credenciais/autorização
+
modelo/provider funcional
```

A investigação básica do Gateway não deve ser repetida sem mudança de versão, protocolo ou evidência contraditória.

---

# 21. Registro de versão

```text
Continuity version: 0.7
Project state: Phase 3 in progress
Real OpenClaw Gateway compatibility: VALIDATED
Next gate: WU-055 Runtime Event Monitoring
```

Qualquer mudança significativa neste documento deve ser feita junto com a atualização do estado real do projeto.

---

# 22. Fase 3 — Integração Real com OpenClaw Gateway

**Status: RUNTIME COMPATIBILITY VALIDATED**

A Fase 3 deixou de ser apenas uma implementação contra fake Gateway.
O runtime boundary foi exercitado contra uma instalação real do OpenClaw.

## 22.1 Estado das Work Units

```text
WU-051  Gateway protocol research
        ✅ consolidada

WU-052  OpenClaw Gateway WebSocket adapter
        ✅ implementada e validada

WU-053  Gateway runtime vertical slice
        ✅ validada localmente e em Gateway real

WU-054  Live Gateway compatibility / acceptance
        ✅ compatibilidade real mínima validada

WU-055  Runtime event monitoring
        ⏳ próximo bloco

WU-056  Durable execution / recovery integration
        ⏳ posterior

WU-057  Operational acceptance
        ⏳ ainda aberta
```

## 22.2 Implementação real validada

```text
AgentRuntime
    ↓
OpenClawAdapter
    ↓
OpenClawGatewayClient
    ↓
Gateway WebSocket/RPC
    ↓
OpenClaw Agent
    ↓
Codex
    ↓
openai/gpt-5.5
```

O cliente real suporta:

```text
connect
agent
agent.wait
chat.history
sessions.abort
```

## 22.3 Semântica de execução consolidada

```text
agent
→ runId

agent.wait
→ estado terminal ou timeout de espera

timeout de agent.wait
→ não significa cancelamento

get_status()
→ timeout de espera é exposto como RUNNING

retrieve_result()
→ aguarda conclusão
→ lê chat.history
→ extrai texto do assistant
```

## 22.4 Resultado real

Foi validado:

```text
task
→ agent main
→ GPT-5.5
→ agent.wait
→ chat.history
→ output
```

Saída final:

```text
ORCHESTRATOR_GATEWAY_OK
```

## 22.5 Evidência da suíte

Após a integração e os testes de regressão:

```text
207 tests passed
```

A suíte é a evidência autoritativa do clone em que foi executada.

## 22.6 Descobertas de integração

Foram consolidadas as seguintes decisões:

```text
1. Gateway protocol v4 é o contrato validado nesta integração.

2. O cliente deve usar client.id = gateway-client
   e client.mode = backend para o caller testado.

3. O runtime efetivo permanece separado do domínio.

4. Modelo listado não implica modelo executável.

5. Overrides de provider/model podem ser rejeitados pelo runtime.

6. O modelo default executável validado foi openai/gpt-5.5.

7. agent.wait timeout é estado da espera, não estado terminal do run.

8. O texto final deve ser recuperado do transcript via chat.history.

9. Blocos de thinking não devem ser promovidos a output.

10. SessionKey do adapter segue orchestrator:<task_id>.
```

## 22.7 Limitações ainda abertas

```text
runtime event streaming
durable execution/recovery
reconnect reconciliation
production observability
production security hardening
deployment
final operational acceptance
```

O projeto não deve ser classificado como production-ready.

# 23. Ponto exato de retomada

O próximo trabalho recomendado é:

```text
RUNTIME EVENT MONITORING
        ↓
definir eventos mínimos necessários
        ↓
normalizar lifecycle
        ↓
integrar com telemetry/evidence
        ↓
testar reconnection semantics
```

Somente depois:

```text
DURABLE EXECUTION / RECOVERY
        ↓
OPERATIONAL ACCEPTANCE
```

A investigação básica do Gateway não deve ser repetida sem mudança de versão,
mudança de protocolo ou evidência contraditória.

# 24. Regra de documentação após a integração real

Qualquer alteração futura na integração OpenClaw deve atualizar, conforme o
impacto:

```text
Design
→ Work Unit / research
→ Gate report
→ Development Continuity
→ New Chat Context
→ tests
```

O objetivo é impedir que conhecimento operacional validado permaneça apenas
no histórico de chat.

# 25. Estado de versionamento

```text
Continuity version: 0.7
Phase: 3
Real OpenClaw Gateway compatibility: VALIDATED
Automated regression snapshot: 207 passed
Next gate: WU-055 Runtime Event Monitoring
```
