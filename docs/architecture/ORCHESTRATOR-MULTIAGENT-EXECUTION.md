# ORCHESTRATOR — MULTIAGENT EXECUTION

**Projeto:** Adaptive AI Orchestrator  
**Status:** Arquitetura normativa incremental com execução high-level operacional na v0.4  
**Origem:** maturação da capacidade Delegation & Coordination após auditoria comparativa do ecossistema Matt Pocock

## 1. Propósito

Esta especificação torna operacional a execução multiagente já prevista pela arquitetura do Adaptive AI Orchestrator sem acoplar o núcleo a Git worktrees, Claude background agents, OpenClaw ou qualquer outro harness.

O problema central é:

> **Como avançar um grafo de Work Units com concorrência segura, delegação limitada, autoridade explícita e avaliação antes de liberar dependências?**

### Estado de implementação v0.4

Os invariantes deste documento deixam de existir apenas como mecanismos de baixo nível isolados. A v0.4 acrescenta `RuntimeProjectPlanner` + `RunProjectOrchestration`, que transformam um objetivo amplo em `ProjectExecutionPlan`, executam frontiers em ondas sincronizadas paralelas, propagam resultados aceitos para fan-in e podem expandir o grafo por replanning aditivo limitado.

O fluxo executável é documentado em `ORCHESTRATOR-AUTOMATIC-PROJECT-EXECUTION.md`.

A implementação cria **worker sessions lógicos efêmeros** por Work Unit. Ela não cria perfis persistentes de agentes OpenClaw e não presume isolamento por Git worktree/container. Em checkout compartilhado, writes concorrentes exigem escopos de escrita declarados e não sobrepostos.

## 2. Princípios

### ME-001 — Frontier, não lista linear

O Orchestrator deve tratar o plano como grafo de dependências. A **ready frontier** é o conjunto de Work Units atualmente elegíveis para execução.

```text
Work Graph
   ↓
Readiness Evaluation
   ↓
Ready Frontier
   ↓
Policy + Budget + Claim
   ↓
Dispatch
```

A frontier deve ser recalculável após mudanças de estado, conclusão, revisão, replanejamento ou satisfação de dependências.

### ME-002 — Paralelismo é limitado por política e orçamento

Estar na frontier não implica execução imediata. O Orchestrator deve respeitar, conforme aplicável:

- limite de concorrência;
- execuções já ativas;
- disponibilidade de recursos;
- política de autoridade;
- claims existentes;
- criticidade e prioridade;
- conflito de write/resource scope quando workers compartilham workspace.

A v0.4 permite frontiers com 2, 3, 4, 6 ou mais workers até o limite configurado, mas não usa worker count como objetivo. A frontier útil e segura determina o paralelismo real.

### ME-003 — Claim é separado de estado da Work Unit

`READY`, `RUNNING` e demais estados representam progresso do trabalho. Um **Execution Claim** representa propriedade exclusiva durante uma tentativa de execução.

```text
WorkUnit.state        ExecutionClaim
--------------        --------------
READY                 quem possui direito de despachar
RUNNING               qual execução está associada
REVISION_REQUIRED     claim anterior já deve estar liberado
```

Não incorporar `CLAIMED` ao estado de negócio evita misturar concorrência com progresso.

### ME-004 — Claim antes do side effect de dispatch

A ordem segura é:

```text
readiness
→ policy
→ concurrency budget
→ acquire claim
→ runtime submit
→ bind execution
```

Se o runtime rejeitar a execução antes de iniciá-la, o claim deve ser liberado.

### ME-005 — Produção não libera dependências

Uma execução retornar resultado não é suficiente para avançar o grafo.

```text
Runtime result
→ ResultPackage
→ Evaluation
→ Acceptance decision
→ FinalizeExecution
→ dependency satisfaction
```

Dependências só avançam depois de resultado aceito ou aceito com condições segundo a política de avaliação aplicável.

### ME-006 — Fan-out/fan-in é semântico

Fan-out significa múltiplas Work Units independentes em execução concorrente. Fan-in significa reunir resultados em um ponto de integração ou decisão.

O núcleo não presume que fan-in seja `git merge`.

Exemplos:

```text
code workers      → integration
research agents   → synthesis
security reviewers→ aggregate findings
design agents     → compare alternatives
backend + frontend→ cross-layer integration/test
```

Git branches/worktrees, sandboxes, containers ou runtime-managed workspaces são estratégias de adapter.

## 3. Work Unit kinds

A classificação de intenção complementa o estado:

```text
EXECUTION
DECISION
RESEARCH
PROTOTYPE
HUMAN_ACTION
```

Ela permite que o Orchestrator selecione políticas e recursos adequados sem criar agentes artificiais para trabalho que exige decisão humana.

## 4. Delegation lineage

Delegação recursiva deve carregar explicitamente:

```text
root_task_id
parent_task_id
depth
max_depth
ancestry
```

Regras:

1. a profundidade nunca pode ultrapassar `max_depth`;
2. um descendente não pode reutilizar id presente na ancestry;
3. o parent deve corresponder ao topo da linhagem atual;
4. subdelegação não amplia autoridade automaticamente;
5. um runtime pode não suportar subagentes; nesse caso a capacidade é indisponível, não simulada por invenção.

O objetivo é impedir explosão recursiva, ciclos e delegação de autoridade sem limite.

No project mode v0.4, workers não subdelegam novos Adaptive runs. Necessidade real de novo trabalho retorna ao orchestrator por sinal de replanning, preservando centralização da autoridade.

## 5. Context transfer

A transferência de contexto possui estratégia própria:

```text
MINIMAL_INLINE
POINTERS
HYBRID
FRESH
```

**Context pointers** referenciam artefatos autoritativos existentes em vez de duplicá-los. O adapter resolve o mecanismo físico.

Contexto sensível só pode atravessar fronteiras quando a política declara que redaction foi aplicada ou quando outra política superior autoriza mecanismo seguro equivalente.

No project executor v0.4, resultados aceitos de dependências são propagados ao consumidor por contexto limitado; artefatos extensos continuam preferindo pointers para evitar custo desnecessário.

## 6. Execution Coordinator

O `ExecutionCoordinator` é responsável pelo dispatch seguro da frontier preparada.

Responsabilidades:

```text
validate request
→ calculate readiness
→ order by priority
→ enforce human/action policy
→ enforce concurrency budget
→ acquire exclusive claim
→ delegate through AgentRuntime
→ bind claim to ExecutionReference
→ report per-Work-Unit outcome
```

Ele não deve:

- escolher framework de aplicação;
- conhecer comandos do harness;
- criar Git worktrees;
- decidir sozinho se um resultado é correto;
- liberar dependências sem avaliação.

A camada `RunProjectOrchestration` fica acima do coordinator: prepara a wave, chama o coordinator, aguarda/junta resultados, finaliza cada Work Unit e recalcula a próxima frontier.

## 7. Finalization

`FinalizeExecution` aplica o veredito já produzido pela camada de avaliação.

| Verdict | Work Unit | Dependencies | Claim |
|---|---|---|---|
| ACCEPTED | COMPLETED | advance | release |
| ACCEPTED_WITH_CONDITIONS | COMPLETED | advance | release |
| RETURNED | REVISION_REQUIRED | unchanged | release |
| REJECTED | REVISION_REQUIRED | unchanged | release |
| BLOCKED | BLOCKED | unchanged | release |

As condições de `ACCEPTED_WITH_CONDITIONS` continuam rastreáveis na Evaluation/ResultPackage; completar a Work Unit não deve apagá-las.

## 8. Runtime boundary

O contrato runtime continua mínimo:

```text
submit
get_status
retrieve_result
cancel
```

Capacidades adicionais de harness devem ser descobertas e adaptadas, não presumidas pelo domínio.

Possíveis extensões futuras:

- event stream;
- durable leases;
- sandbox/workspace allocation;
- background execution;
- child-agent native APIs.

Essas extensões não são pré-condição para o modelo semântico atual. O OpenClaw adapter atual obtém paralelismo através de múltiplas execuções/sessões independentes do mesmo contrato mínimo.

## 9. Failure behavior

O Orchestrator deve diferenciar:

```text
not ready
policy blocked
concurrency deferred
workspace-conflict deferred
claim conflict
runtime dispatch failure
execution/result failure
result rejection
human-action blocked
```

Esses estados não são equivalentes e não devem ser achatados em um único `FAILED`.

Retries e replans são limitados. Um erro persistente vira blocker em vez de loop infinito.

## 10. Relação com Matt Pocock skills

Mecanismos estudados contribuíram como evidência de operação:

- `wayfinder`: frontier, claims, trabalho decisório e fog of war;
- `to-tickets`: dependency graph e tracer bullets;
- `implement-spec`: fan-out/fan-in, worker isolation, frontier recomputation;
- `research`: background specialization;
- `handoff`: context transfer;
- `wizard`: human-only boundary.

A arquitetura Adaptive adota os invariantes generalizáveis, não as implementações Git/Claude/tracker específicas.

## 11. Verificação mínima

A capacidade só é considerada válida quando testes demonstram:

- dependências bloqueiam corretamente;
- ciclos obrigatórios são rejeitados;
- orçamento de concorrência é respeitado;
- claim evita dispatch duplicado;
- dispatch falho libera claim;
- policy bloqueia antes do runtime;
- resultado rejeitado não libera dependência;
- resultado aceito libera dependência;
- frontier subsequente consegue avançar;
- recursão acima do limite falha deterministicamente;
- um contrato pode liberar backend e frontend na mesma frontier;
- seis Work Units independentes podem ocupar seis workers quando o cap permite;
- resultados paralelos convergem em fan-in downstream;
- writes com paths sobrepostos são serializados;
- writes com paths disjuntos podem ser paralelos;
- skill resolution não carrega skills desnecessárias;
- HUMAN_ACTION não é delegado;
- replanning aditivo é limitado e revalidado;
- project-mode CLI produz evidência estruturada de waves e parallelism.

A passagem desses testes valida a lógica do repositório. Uma instalação específica ainda exige live E2E no Gateway real para provar paralelismo operacional naquela máquina.
