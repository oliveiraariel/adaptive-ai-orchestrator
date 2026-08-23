# Orchestrator Development Continuity

**Projeto:** Adaptive AI Orchestrator
**Documento:** Registro de Continuidade do Desenvolvimento
**Versão do registro:** 0.5
**Status:** Fase 2 concluída — próximo gate: integração real com OpenClaw Gateway

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
OpenClaw Gateway real         ⏳
WebSocket/RPC real            ⏳
live event stream             ⏳
```

A próxima fase deve validar a integração contra uma instalação real do OpenClaw e sua versão efetivamente utilizada.

Não inventar um protocolo externo não verificado.

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

Após aplicar os artefatos no clone local, a suíte completa deve ser executada novamente antes de qualquer novo commit.

A validação local é a evidência autoritativa do estado atual do clone.

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
REAL OPENCLAW GATEWAY INTEGRATION     ⏳
WEBSOCKET / RPC VALIDATION            ⏳
REAL EXECUTION EVENTS                 ⏳
LIVE EXECUTION MONITORING             ⏳
PRODUCTION TELEMETRY                  ⏳
PRODUCTION SECURITY HARDENING         ⏳
PRODUCTION DEPLOYMENT                 ⏳
```

O projeto **não deve ser declarado production-ready** neste ponto.

---

# 15. Próximo gate

O próximo gate oficial é:

```text
OPENCLAW GATEWAY COMPATIBILITY SPIKE
```

Objetivo:

1. identificar a versão real do OpenClaw disponível;
2. confirmar modo de execução;
3. confirmar autenticação/autorização;
4. confirmar Gateway;
5. confirmar WebSocket;
6. confirmar RPC methods;
7. confirmar `agent`;
8. confirmar `agent.wait`;
9. confirmar eventos;
10. validar cancelamento/timeout;
11. executar um vertical slice real;
12. registrar evidências.

---

# 16. Próxima sequência prevista

```text
Gateway Compatibility
        ↓
WebSocket Transport
        ↓
agent / agent.wait
        ↓
Runtime Events
        ↓
Real OpenClaw Vertical Slice
        ↓
End-to-End Real Execution
        ↓
Operational Acceptance
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
Fase 2 concluída.
```

**Ponto de retomada:**

```text
OpenClaw Gateway Compatibility Spike
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

Se essa dependência não estiver disponível, não inventar integração. Executar primeiro um compatibility spike documental/experimental e registrar o bloqueio.

---

# 21. Registro de versão

```text
Continuity version: 0.5
Project state: Phase 2 complete
Next gate: OpenClaw Gateway Compatibility Spike
```

Qualquer mudança significativa neste documento deve ser feita junto com a atualização do estado real do projeto.
