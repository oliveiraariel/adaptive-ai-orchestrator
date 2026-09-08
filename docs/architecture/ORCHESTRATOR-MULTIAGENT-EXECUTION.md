# ORCHESTRATOR — MULTIAGENT EXECUTION

**Projeto:** Adaptive AI Orchestrator  
**Status:** Arquitetura normativa implementada incrementalmente  
**Versão operacional relevante:** v0.4

## 1. Propósito

Esta especificação torna operacional a execução multiagente prevista pela arquitetura do Adaptive AI Orchestrator sem acoplar o núcleo a Git worktrees, Claude background agents, OpenClaw ou qualquer outro harness.

O problema central é:

> **Como avançar um grafo de Work Units com concorrência segura, delegação limitada, autoridade explícita e avaliação antes de liberar dependências, preenchendo continuamente a capacidade disponível?**

O fluxo executável high-level é detalhado em `ORCHESTRATOR-AUTOMATIC-PROJECT-EXECUTION.md`.

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
Policy + Budget + Claim + Conflict Safety
   ↓
Dispatch
```

A frontier deve ser recalculável após conclusão aceita, revisão, bloqueio, replanejamento ou satisfação de dependências.

### ME-002 — Paralelismo é limitado por política e orçamento

Estar na frontier não implica execução imediata. O Orchestrator deve respeitar:

- limite global de concorrência;
- execuções já ativas;
- disponibilidade de recursos;
- política de autoridade;
- claims existentes;
- criticidade e prioridade;
- segurança de escrita/workspace.

`max_concurrency` é teto, não meta.

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
→ conflict safety
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

Fan-out significa múltiplas Work Units independentes em execução concorrente. Fan-in significa reunir resultados aceitos em um ponto de integração, síntese, teste ou decisão.

```text
code workers       → integration
research agents    → synthesis
security reviewers → aggregate findings
design agents      → compare alternatives
```

O núcleo não presume que fan-in seja `git merge`.

### ME-007 — Concorrência é contínua, não uma barreira de lote

A v0.4 operacional deve poder repor um slot assim que uma execução relevante termina e sua avaliação permite novo trabalho.

Com dois workers A/B ativos:

```text
A termina e é aceito
→ C torna-se READY
→ existe um slot livre
→ C pode iniciar
→ B continua executando
```

O Orchestrator não deve aguardar B apenas porque A e B foram despachados na mesma geração anterior.

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

No bridge OpenClaw atual, workers recebem também constraint de não reentrada: uma tarefa já sob Adaptive não deve invocar `adaptive-orchestrator-bridge` novamente.

## 5. Context transfer

A transferência de contexto possui estratégia própria:

```text
MINIMAL_INLINE
POINTERS
HYBRID
FRESH
```

**Context pointers** referenciam artefatos autoritativos existentes em vez de duplicá-los. O adapter resolve o mecanismo físico.

No project mode v0.4, outputs aceitos de dependências podem ser transferidos com orçamento de caracteres. Artefatos grandes devem preferir ponteiros em vez de cópia integral.

## 6. Execution Coordinator

O `ExecutionCoordinator` continua responsável pelo dispatch seguro de uma frontier preparada:

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

A camada superior `RunContinuousProjectOrchestration` é responsável por manter o conjunto de execuções ativas, esperar o primeiro resultado disponível, finalizá-lo e recomputar/reabastecer a frontier.

## 7. Scheduler contínuo

A execução de projeto segue:

```text
plan validado
→ ready frontier
→ selecionar candidatos compatíveis com workers já ativos
→ despachar até max_concurrency
→ FIRST_COMPLETED
→ avaliar/finalizar concluídos
→ liberar dependências aceitas
→ recomputar frontier
→ preencher slots livres
↺
```

Os registros historicamente chamados `waves` são mantidos por compatibilidade, mas no scheduler contínuo representam **dispatch generations**, não barreiras.

A seleção de uma nova geração deve comparar conflito de recursos/escrita contra:

- todos os workers ainda ativos;
- todos os novos candidatos já escolhidos para aquela geração.

## 8. Segurança de workspace compartilhado

A v0.4 não afirma isolamento automático por worktree/container.

Para `filesystem.write`, cada Work Unit deve declarar `write_paths` literais e relativos ao repositório.

Devem falhar antes da execução:

- write sem escopo declarado;
- path absoluto;
- `..` traversal;
- glob/wildcard;
- drive prefix absoluto.

Dois writers podem sobrepor execução somente quando seus prefixos são disjuntos. Igualdade ou relação parent/child é conflito e deve ser serializada.

Um runtime futuro pode substituir esta estratégia por sandbox/worktree isolation comprovado, preservando as mesmas semânticas de ownership e autoridade.

## 9. Finalization

`FinalizeExecution` aplica o veredito produzido pela camada de avaliação.

| Verdict | Work Unit | Dependencies | Claim |
|---|---|---|---|
| ACCEPTED | COMPLETED | advance | release |
| ACCEPTED_WITH_CONDITIONS | COMPLETED | advance | release |
| RETURNED | REVISION_REQUIRED | unchanged | release |
| REJECTED | REVISION_REQUIRED | unchanged | release |
| BLOCKED | BLOCKED | unchanged | release |

As condições de `ACCEPTED_WITH_CONDITIONS` continuam rastreáveis na Evaluation/ResultPackage.

## 10. Retry e identidade

Cada nova tentativa deve receber identidade distinta de task/execution. A identidade não pode depender apenas do estado `REVISION_REQUIRED`, pois terceiro e posteriores retries poderiam reutilizar a mesma chave de idempotência.

O scheduler contínuo inclui o número explícito da tentativa na identidade delegada.

## 11. Replanning durante concorrência

O grafo não deve ser mutado de forma insegura sob Work Units em execução.

Quando um resultado aceito sinaliza `ADAPTIVE_REPLAN_REQUIRED`:

```text
parar novos dispatches
→ deixar workers já ativos concluírem
→ consolidar estado
→ executar bounded replan
→ validar novas unidades/edges
→ retomar frontier
```

Cada invocação de replan consome orçamento, mesmo quando não adiciona Work Unit.

Um replan não pode adicionar requisito obrigatório ainda não satisfeito a uma Work Unit já `RUNNING`, `EVALUATING` ou `COMPLETED` sem fluxo explícito de recovery/reopen.

## 12. Runtime boundary

O contrato runtime continua mínimo:

```text
submit
get_status
retrieve_result
cancel
```

Capacidades adicionais de harness devem ser descobertas e adaptadas, não presumidas pelo domínio.

Possíveis extensões futuras:

- event stream nativo;
- durable leases;
- sandbox/workspace allocation;
- background execution;
- child-agent native APIs.

A v0.4 alcança concorrência lateral sobre o contrato atual usando múltiplas execuções/sessões independentes e espera concorrente de resultados.

## 13. Failure behavior

O Orchestrator deve diferenciar:

```text
not ready
policy blocked
concurrency deferred
workspace conflict deferred
claim conflict
runtime dispatch failure
execution/result retrieval failure
evaluation return/rejection
human action
replan budget exhaustion
```

Esses estados não são equivalentes e não devem ser achatados em um único `FAILED`.

## 14. Economicidade

O worker count deve ser determinado pela quantidade de trabalho simultaneamente útil e seguro.

Exemplos:

```text
2 independentes úteis → 2 workers
4 independentes úteis → até 4 workers
6 independentes úteis + budget 6 → até 6 workers
1 unidade real → 1 worker
```

A fragmentação só é justificável quando o ganho de paralelismo/especialização supera custo de contexto, coordenação, avaliação e retrabalho.

## 15. Relação com Ariel Agent Skills

As skills fornecem capacidade de execução; não possuem o scheduler.

Mecanismos relevantes:

- `engineering-lifecycle`: expõe fluxo lateral sem impor sequência artificial;
- `work-decomposition`: cria DAG, write scopes, fan-in e frontiers;
- `implementation`, `testing`, `code-review`, `security-review`, `web-frontend-design`: capacidades por Work Unit;
- `adaptive-orchestrator-bridge`: apenas invoca `run` ou `orchestrate` e transporta resultado.

O Adaptive continua dono de claims, concorrência, authority policy, result evaluation e replanning.

## 16. Verificação mínima

A capacidade só é considerada válida no nível de código/CI quando testes demonstram:

- dependências bloqueiam corretamente;
- ciclos obrigatórios são rejeitados;
- orçamento de concorrência é respeitado;
- claim evita dispatch duplicado;
- dispatch falho libera claim;
- policy bloqueia antes do runtime;
- resultado rejeitado não libera dependência;
- resultado aceito libera dependência;
- frontend/backend podem compartilhar frontier;
- pelo menos seis workers independentes podem coexistir em cenário controlado;
- slot liberado é preenchido antes do fim de worker independente ainda ativo;
- fan-in recebe outputs aceitos;
- writers sobrepostos são serializados contra workers já ativos;
- write scopes inseguros falham;
- retries têm identidade distinta e limite;
- bounded replanning preserva consistência;
- recursão/reentrada indevida é bloqueada;
- CI propaga falhas reais de pytest.

A validação de uma **instalação OpenClaw específica** exige adicionalmente E2E real multi-session no Gateway local daquela máquina.
