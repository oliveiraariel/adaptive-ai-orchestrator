# ORCHESTRATOR-SYSTEM-ARCHITECTURE

**Projeto:** Adaptive AI Orchestrator  
**Versão:** v0.1 — arquitetura conceitual inicial  
**Status:** Em desenvolvimento

---

# 1. Objetivo

Este documento define a arquitetura conceitual do **Adaptive AI Orchestrator** a partir dos requisitos e capacidades consolidados nas fases anteriores.

A arquitetura deve responder:

> **Como organizar o sistema para que o Orchestrator consiga compreender projetos, estruturar trabalho, analisar recursos, selecionar configurações, delegar, avaliar resultados, replanejar e manter continuidade, sem depender conceitualmente de um único runtime?**

A arquitetura deve preservar:

- separação de responsabilidades;
- baixo acoplamento;
- alta coesão;
- rastreabilidade;
- extensibilidade;
- portabilidade do conhecimento;
- integração com runtimes de agentes;
- controle de contexto;
- governança;
- observabilidade;
- capacidade de evolução.

---

# 2. Princípios Arquiteturais

## PA-001 — Separação entre inteligência própria e infraestrutura

O núcleo conceitual do Orchestrator pertence ao projeto.

OpenClaw, Hermes ou outro runtime fornecem infraestrutura de execução.

```text
NOSSA ARQUITETURA
        ↓
Runtime Adapter
        ↓
OpenClaw / Hermes / outro
```

O runtime não deve definir o modelo conceitual do projeto.

---

## PA-002 — Separação entre Agent, Skill e Model

A arquitetura deve tratar:

```text
Agent
Skill
Model
```

como entidades distintas e combináveis.

```text
Agent
├── role
├── responsibilities
├── skills
├── tools
└── eligible models
```

---

## PA-003 — Project-first

O sistema deve iniciar pela necessidade do projeto e não pela disponibilidade de agentes.

```text
Project
→ Work
→ Capability
→ Skill
→ Agent
→ Model
```

---

## PA-004 — Knowledge-first

Conhecimento estruturado deve possuir existência própria antes de ser convertido em prompt, Skill ou configuração de runtime.

Isso permite:

```text
Knowledge
→ Skill
→ Prompt
→ Agent
```

sem perder o conhecimento original.

---

## PA-005 — Adaptação contextual

A profundidade de análise, coordenação e validação deve ser proporcional a:

- impacto;
- risco;
- complexidade;
- incerteza;
- criticidade;
- reversibilidade.

---

## PA-006 — Não fragmentar sem benefício

A arquitetura deve suportar múltiplos agentes, mas não pressupor que mais agentes produzem melhor resultado.

---

## PA-007 — Produção não implica aceitação

Resultados retornados por agentes devem passar pelo mecanismo de avaliação correspondente.

---

## PA-008 — Estado como elemento central

O projeto, e não a sessão individual de um modelo, deve ser a unidade principal de continuidade.

---

## PA-009 — Evolução controlada

Mudanças no conhecimento, Skills, prompts, políticas, agentes e componentes devem poder ser versionadas e avaliadas.

---

## PA-010 — Segurança acima da autonomia

A arquitetura deve manter fronteiras para decisões e ações que exigem autoridade humana.

---

# 3. Visão Geral

A arquitetura conceitual é:

```text
                         ADAPTIVE AI ORCHESTRATOR
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
 Project State                Knowledge Layer            Ecosystem Layer
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    ▼
                         Orchestrator Decision Core
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
       Planning              Agent/Skill Analysis       Resource Selection
          │                         │                         │
          └─────────────────────────┼─────────────────────────┘
                                    ▼
                         Delegation & Coordination
                                    │
                                    ▼
                              Runtime Adapter
                                    │
                     ┌──────────────┼──────────────┐
                     ▼              ▼              ▼
                  OpenClaw       Hermes         Other Runtime
                     │              │              │
                     └──────────────┼──────────────┘
                                    ▼
                              Agent Execution
                                    │
                                    ▼
                             Result Packages
                                    │
                                    ▼
                             Result Evaluation
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                             ▼
                 Project State              Continuity/Learning
                     │                             │
                     └──────────────┬──────────────┘
                                    ▼
                                 Replanning
                                    ↺
```

---

# 4. Fronteira do Sistema

O sistema próprio compreende:

```text
Project State
Knowledge Layer
Ecosystem Abstraction
Decision Core
Planning
Structural Analysis
Agent & Skill Analysis
Resource / Model Selection
Delegation & Coordination
Result Evaluation
Replanning
Continuity & Learning
Policy / Governance
Observability
Runtime Adapter
```

O sistema não pretende substituir:

```text
LLM
Agent Runtime
Provider
Tool Provider
MCP Server
External Service
IDE
Model Harness
```

Esses componentes fazem parte do ecossistema externo ou de infraestrutura.

---

# 5. Camadas Conceituais

A arquitetura utiliza camadas conceituais, mas não exige que a implementação futura possua exatamente a mesma quantidade de camadas físicas.

## 5.1 Project Layer

Representa:

- projeto;
- objetivos;
- requisitos;
- decisões;
- estrutura;
- Work Units;
- estado;
- dependências.

---

## 5.2 Knowledge Layer

Representa conhecimento reutilizável:

- conhecimento do Orchestrator;
- conhecimento compartilhado;
- conhecimento de agentes;
- Skills;
- referências;
- conhecimento empírico;
- evidências.

---

## 5.3 Ecosystem Layer

Representa:

- Agents;
- Skills;
- Models;
- Providers;
- Tools;
- MCPs;
- Plugins;
- Hooks;
- Runtime;
- políticas;
- disponibilidade.

---

## 5.4 Decision Layer

Responsável por decisões de:

- estruturação;
- priorização;
- elegibilidade;
- seleção;
- delegação;
- avaliação;
- replanejamento.

---

## 5.5 Execution Coordination Layer

Responsável por:

- Task Packages;
- handoff;
- acompanhamento;
- Result Packages;
- coordenação;
- retries;
- fallback;
- cancelamento.

---

## 5.6 Evaluation Layer

Responsável por:

- critérios;
- avaliação;
- validação;
- impacto;
- coerência;
- confiança;
- decisão de integração.

---

## 5.7 Continuity Layer

Responsável por:

- estado persistente;
- histórico;
- decisões;
- evidências;
- aprendizado;
- versões;
- recuperação.

---

## 5.8 Runtime Adapter Layer

Responsável por traduzir conceitos do sistema para mecanismos concretos do runtime.

Exemplo:

```text
System Agent
    ↓
Runtime Adapter
    ↓
OpenClaw Agent
```

ou:

```text
System Agent
    ↓
Runtime Adapter
    ↓
Hermes Agent
```

---

# 6. Componentes Principais

## C-001 — Project State Manager

Responsabilidade:

- manter estado atual;
- atualizar estados;
- controlar Work Units;
- manter dependências;
- manter baselines;
- registrar transições relevantes.

Não deve tomar decisões de domínio por conta própria.

---

## C-002 — Knowledge Manager

Responsabilidade:

- fornecer conhecimento;
- organizar fontes;
- separar conhecimento atual de histórico;
- controlar proveniência;
- controlar confiança;
- permitir atualização.

---

## C-003 — Ecosystem Registry

Responsabilidade:

- representar recursos do ecossistema;
- disponibilizar agentes;
- Skills;
- modelos;
- ferramentas;
- providers;
- runtimes;
- compatibilidades;
- disponibilidade;
- políticas aplicáveis.

---

## C-004 — Project Awareness Engine

Responsabilidade:

- compreender projeto;
- consolidar contexto;
- identificar lacunas;
- manter visão global.

---

## C-005 — Structural Analysis Engine

Responsabilidade:

- analisar estruturas;
- revisar propostas;
- verificar granularidade;
- dependências;
- sequência;
- paralelismo;
- riscos;
- estabelecer baseline quando aprovado.

---

## C-006 — Project Management Engine

Responsabilidade:

- gerir Work Units;
- prioridade;
- fila;
- estados;
- dependências;
- liberação;
- bloqueios;
- planejamento operacional.

---

## C-007 — Agent & Skill Analysis Engine

Responsabilidade:

- identificar capacidades;
- Skills necessárias;
- agentes elegíveis;
- lacunas;
- composições possíveis.

---

## C-008 — Resource / Model Selection Engine

Responsabilidade:

- selecionar configuração;
- considerar custo;
- qualidade;
- contexto;
- risco;
- latência;
- histórico;
- política.

---

## C-009 — Delegation & Coordination Engine

Responsabilidade:

- montar Task Packages;
- executar handoff;
- acompanhar execução;
- receber Result Packages;
- controlar retries/fallback;
- coordenar agentes.

---

## C-010 — Result Evaluation Engine

Responsabilidade:

- avaliar resultados;
- verificar critérios;
- analisar consistência;
- impacto;
- evidência;
- decisão de integração.

---

## C-011 — Replanning Engine

Responsabilidade:

- detectar necessidade de mudança;
- analisar impacto;
- ajustar Work Units;
- atualizar dependências;
- reconstruir plano afetado.

---

## C-012 — Continuity & Learning Engine

Responsabilidade:

- registrar histórico;
- manter continuidade;
- registrar telemetria;
- produzir candidatos a aprendizado;
- preservar evidências.

---

## C-013 — Policy & Governance Engine

Responsabilidade:

- controlar autoridade;
- políticas;
- limites;
- aprovações;
- recursos proibidos;
- decisões que exigem humano.

---

## C-014 — Observability & Evidence Engine

Responsabilidade:

- registrar eventos;
- métricas;
- custos;
- latência;
- falhas;
- decisões;
- evidências;
- rastreabilidade.

---

## C-015 — Runtime Adapter

Responsabilidade:

- encapsular diferenças entre OpenClaw, Hermes e outros runtimes;
- criar/encaminhar execuções;
- acessar Skills;
- configurar modelos;
- iniciar subagentes;
- recuperar resultados;
- traduzir estados.

---

# 7. Dependências entre Componentes

A dependência conceitual principal é:

```text
Project State
        ↓
Project Awareness
        ↓
Project Management
        ↓
Structural Analysis
        ↓
Agent & Skill Analysis
        ↓
Resource / Model Selection
        ↓
Delegation
        ↓
Execution
        ↓
Result Evaluation
        ↓
Replanning
        ↓
Project State
```

Continuity & Learning atua transversalmente.

Ecosystem Registry fornece informações para:

```text
Agent & Skill Analysis
Resource / Model Selection
Delegation
```

Policy & Governance pode restringir todas as decisões relevantes.

---

# 8. Orchestrator Decision Core

O Orchestrator Decision Core é o núcleo de coordenação.

Ele não precisa implementar toda lógica em um único módulo.

Sua função é coordenar serviços especializados:

```text
Decision Core
├── consult Project State
├── consult Knowledge
├── consult Ecosystem
├── invoke Capability Engine
├── apply Policy
├── produce Decision
└── update State
```

Isso evita um agente/módulo monolítico.

---

# 9. Modelo de Estado

O estado global pode ser conceitualmente dividido em:

```text
PROJECT STATE
├── Project Identity
├── Goals
├── Scope
├── Requirements
├── Decisions
├── Structure
├── Baseline
├── Work Units
├── Dependencies
├── Execution State
├── Results
├── Risks
├── Issues
├── Resources
└── Learning References
```

---

# 10. Estado e Histórico

O estado atual deve ser separado do histórico:

```text
Current State
     +
Historical Events
```

O histórico permite reconstruir:

```text
what happened
why
when
with which resource
what result
what decision followed
```

---

# 11. Work Unit

Work Unit é um conceito central da arquitetura.

```text
WORK UNIT
├── id
├── objective
├── scope
├── inputs
├── outputs
├── dependencies
├── preconditions
├── priority
├── criticality
├── constraints
├── required capabilities
├── selected agent
├── selected Skill(s)
├── selected model
├── acceptance criteria
├── state
└── history
```

Ela funciona como elo entre planejamento e execução.

---

# 12. Task Package

O Task Package representa o contrato de execução.

```text
TASK PACKAGE
├── work_unit
├── objective
├── scope
├── context
├── inputs
├── artifacts
├── decisions
├── dependencies
├── constraints
├── resources
├── expected_output
└── acceptance_criteria
```

---

# 13. Result Package

Representa o retorno:

```text
RESULT PACKAGE
├── task_id
├── status
├── result
├── artifacts
├── decisions
├── assumptions
├── evidence
├── discovered dependencies
├── discovered issues
├── uncertainty
├── validation
└── metadata
```

---

# 14. Knowledge Architecture

O conhecimento deve ser separado por função.

```text
KNOWLEDGE
│
├── Orchestrator Knowledge
│
├── Shared/Core Knowledge
│
├── Specialist Knowledge
│
├── Skill Knowledge
│
├── Project Knowledge
│
├── Empirical Knowledge
│
└── Historical Knowledge
```

Essa separação permite que conhecimento não operacional seja preservado sem necessariamente entrar no prompt de execução.

---

# 15. Knowledge Sources

Fontes possíveis:

```text
Project documents
User decisions
Validated artifacts
Skills
References
Historical results
Execution telemetry
External documentation
Research
Runtime metadata
Agent feedback
```

Toda fonte relevante deve possuir proveniência quando possível.

---

# 16. Knowledge Promotion

O caminho recomendado é:

```text
observation
→ evidence
→ candidate learning
→ validation
→ reusable knowledge
```

Somente depois:

```text
knowledge
→ Skill / Rule / Prompt / Reference
```

Isso impede a transformação automática de experiência isolada em metodologia.

---

# 17. Agent Registry

O registro de agentes deve representar:

```text
Agent
├── id
├── role
├── responsibilities
├── capabilities
├── skills
├── tools
├── eligible models
├── runtime
├── context requirements
├── permissions
├── status
└── performance evidence
```

---

# 18. Skill Registry

Representação conceitual:

```text
Skill
├── id
├── name
├── purpose
├── capabilities
├── inputs
├── outputs
├── dependencies
├── compatible agents
├── compatible runtimes
├── version
└── evidence
```

---

# 19. Model Registry

Representação conceitual:

```text
Model
├── id
├── name
├── version
├── provider
├── capabilities
├── context
├── cost
├── latency
├── availability
├── restrictions
└── evidence
```

Informações voláteis devem permanecer atualizáveis.

---

# 20. Resource Configuration

A unidade real de seleção pode ser:

```text
RESOURCE CONFIGURATION
├── agent
├── Skill(s)
├── model
├── provider
├── tools
├── runtime
└── constraints
```

Isso representa a configuração efetivamente usada na execução.

---

# 21. Decision Model

Decisões relevantes devem possuir:

```text
Decision
├── question
├── context
├── evidence
├── alternatives
├── impact
├── risks
├── recommendation
├── authority
├── decision
└── version
```

---

# 22. Policy Model

Políticas devem representar:

```text
Policy
├── scope
├── rule
├── authority
├── permitted actions
├── prohibited actions
├── escalation criteria
└── version
```

As políticas do desenvolvedor possuem precedência sobre preferências do Orchestrator.

---

# 23. Governance Boundary

O sistema deve separar:

```text
AUTONOMOUS
```

de:

```text
HUMAN AUTHORIZATION REQUIRED
```

Critérios podem considerar:

```text
impact
risk
uncertainty
sensitivity
reversibility
authority
```

---

# 24. Runtime Adapter Architecture

A arquitetura deve utilizar uma abstração semelhante a:

```text
RuntimeAdapter
├── discoverResources()
├── getAgent()
├── getSkill()
├── getModel()
├── prepareContext()
├── spawnAgent()
├── execute()
├── monitor()
├── cancel()
├── retrieveResult()
└── collectTelemetry()
```

Os nomes são conceituais e não definem ainda a API concreta.

---

# 25. OpenClaw Adapter

A primeira implementação deverá poder mapear conceitos do sistema para recursos do OpenClaw.

Conceitualmente:

```text
System Agent
        ↓
OpenClaw Adapter
        ↓
OpenClaw Agent
        ↓
OpenClaw Skill
        ↓
OpenClaw Model
```

O Adapter deve esconder detalhes específicos do runtime do restante do sistema.

---

# 26. Hermes Adapter

Posteriormente:

```text
System Agent
        ↓
Hermes Adapter
        ↓
Hermes Agent
```

O mesmo conhecimento e conceitos devem permanecer reutilizáveis.

---

# 27. Runtime Independence

A arquitetura não deve possuir regras centrais como:

```text
"OpenClaw faz X, logo o Orchestrator sempre fará X."
```

A regra correta é:

```text
Orchestrator requires capability X
        ↓
Runtime capability mapping
```

Se outro runtime possuir mecanismo equivalente, poderá suportá-lo.

---

# 28. Capability Mapping

O Adapter deverá futuramente manter um mapa:

```text
SYSTEM CAPABILITY
        ↕
RUNTIME CAPABILITY
```

Exemplo:

```text
Subagent Execution
↔
runtime-specific subagent mechanism
```

---

# 29. Context Architecture

O contexto deve ser dividido conceitualmente em:

```text
Global Project Context
      +
Relevant Work Unit Context
      +
Task Context
      +
Agent/Skill Context
      +
Runtime Context
```

O Orchestrator deve selecionar o subconjunto necessário para cada execução.

---

# 30. Context Assembly

A montagem deve seguir:

```text
Project State
→ relevant facts
→ relevant decisions
→ relevant artifacts
→ dependencies
→ constraints
→ Task Package
```

Evitar:

```text
entire project blindly
```

---

# 31. Context Provenance

Elementos relevantes do contexto devem poder indicar:

```text
source
state
version
confidence
```

Isso permite ao agente receptor distinguir informação consolidada de hipótese.

---

# 32. Execution Flow

Fluxo principal:

```text
1. Load Project State
2. Identify next Work Unit
3. Check dependencies
4. Analyze capabilities
5. Select agent / Skill / model
6. Apply policies
7. Assemble context
8. Create Task Package
9. Handoff
10. Monitor
11. Receive Result Package
12. Evaluate
13. Update state
14. Replan if necessary
15. Persist evidence
```

---

# 33. Initialization Flow

```text
New Project
    ↓
Project Awareness
    ↓
Context
    ↓
Structural Analysis
    ↓
Structure Approval
    ↓
Baseline
    ↓
Work Units
```

---

# 34. Execution Flow

```text
READY Work Unit
      ↓
Agent & Skill Analysis
      ↓
Resource / Model Selection
      ↓
Delegation
      ↓
Execution
      ↓
Result Package
      ↓
Evaluation
```

---

# 35. Rejection Flow

```text
Result
 ↓
Evaluation
 ↓
REJECTED / RETURNED
 ↓
diagnosis
 ↓
new configuration or revision
 ↓
re-execution
```

---

# 36. Block Flow

```text
Work Unit
 ↓
BLOCKED
 ↓
identify reason
 ↓
continue independent work
 ↓
resolve condition
 ↓
re-evaluate
 ↓
resume
```

---

# 37. Replanning Flow

```text
Event
 ↓
Impact Analysis
 ↓
Affected Set
 ↓
Update Work Units
 ↓
Re-evaluate Resources
 ↓
New Plan
 ↓
Validation
 ↓
Execution
```

---

# 38. Learning Flow

```text
Execution
 ↓
Telemetry
 ↓
Result Evaluation
 ↓
Observed Outcome
 ↓
Learning Candidate
 ↓
Validation
 ↓
Reusable Knowledge
```

---

# 39. Component Interaction Rules

## Rule A

Project State must not depend directly on a concrete runtime.

## Rule B

Knowledge Manager must not depend directly on OpenClaw/Hermes.

## Rule C

Runtime Adapter must not contain project-management rules.

## Rule D

Result Evaluation must not select a new model as its primary responsibility.

## Rule E

Resource Selection must not execute a task.

## Rule F

Delegation must not redefine the project independently of planning.

## Rule G

Learning must not silently modify protected policies.

---

# 40. Dependency Direction

Prefer:

```text
Core concepts
      ↓
Capability services
      ↓
Application orchestration
      ↓
Runtime adapters
      ↓
External systems
```

Avoid:

```text
External Runtime
      ↓
Core domain
```

This keeps the system adaptable.

---

# 41. Architectural Boundaries

A future implementation should identify at least:

```text
DOMAIN / CORE
APPLICATION
INFRASTRUCTURE / ADAPTERS
INTERFACES
```

The exact implementation structure may vary, but responsibility boundaries must remain.

---

# 42. Core Domain Concepts

The core should conceptually own:

```text
Project
WorkUnit
Dependency
Decision
Baseline
AgentProfile
SkillProfile
ModelProfile
ResourceConfiguration
TaskPackage
ResultPackage
Evaluation
Plan
Policy
LearningCandidate
```

---

# 43. Application Services

Application-level orchestration may include:

```text
InitializeProject
StructureProject
PlanWork
AnalyzeResources
SelectConfiguration
DelegateWork
EvaluateResult
ReplanProject
PersistLearning
ResumeProject
```

These names are conceptual.

---

# 44. Infrastructure

Infrastructure will later handle:

```text
runtime
storage
model providers
tool providers
MCP
telemetry
external APIs
filesystem
```

---

# 45. Persistence

The architecture must support persistence for at least:

```text
Project State
Decisions
Baselines
Work Units
Results
Evaluations
Events
Evidence
Learning Candidates
Resource metadata
```

The concrete persistence technology is intentionally left open at this stage.

---

# 46. Event Model

Important state transitions may produce events:

```text
ProjectCreated
StructureProposed
StructureApproved
WorkUnitCreated
WorkUnitReleased
TaskDelegated
TaskStarted
TaskCompleted
ResultEvaluated
WorkUnitReopened
PlanChanged
DecisionRequested
DecisionRecorded
LearningCandidateCreated
```

Events support:

- history;
- observability;
- replay;
- learning;
- debugging.

The final event list will be defined during detailed design.

---

# 47. State Transitions

The system should treat state transitions explicitly.

Example:

```text
PROPOSED
→ APPROVED
→ READY
→ RUNNING
→ EVALUATION
→ COMPLETED
```

With alternatives:

```text
RUNNING
→ FAILED
→ RETRYING
→ RUNNING
```

or:

```text
EVALUATION
→ RETURNED
→ REVISION
→ EVALUATION
```

---

# 48. Concurrency

The architecture must support controlled concurrency without making parallel execution mandatory.

Concurrency decisions belong to Project Management and Replanning, based on:

- dependencies;
- context;
- risk;
- benefit;
- cost.

---

# 49. Failure Isolation

A failure in one agent should not automatically corrupt:

- project state;
- unrelated Work Units;
- knowledge base;
- other runtime sessions.

The architecture should isolate execution where practical.

---

# 50. Idempotency

Important operations should be designed, when practical, to avoid duplicate effects.

Examples:

```text
duplicate event
duplicate delegation
duplicate persistence
duplicate retry
```

must not silently create inconsistent state.

---

# 51. Retry Boundary

Retry logic belongs to execution coordination.

But the decision:

```text
retry
vs
reselect
vs
replan
```

should consider diagnosis and may invoke other capability services.

---

# 52. Transaction Boundary

Operations affecting important state should have clear consistency boundaries.

Examples:

```text
accept result
→ persist result
→ update Work Unit
→ update dependencies
```

The implementation must avoid partially applied state when possible.

---

# 53. Observability

The architecture should expose enough information to answer:

```text
what happened?
when?
with which project?
which Work Unit?
which agent?
which Skill?
which model?
what cost?
what result?
what evaluation?
what decision?
```

---

# 54. Metrics

Potential metrics:

```text
task success rate
quality rate
rework rate
cost per Work Unit
latency
agent utilization
model utilization
delegation count
retry rate
failure rate
human intervention rate
planning revision rate
```

Metrics are observability data, not automatic quality truth.

---

# 55. Evidence Architecture

Evidence should remain distinguishable from:

```text
decision
```

and:

```text
learning
```

Conceptually:

```text
Observation
→ Evidence
→ Evaluation
→ Learning Candidate
```

---

# 56. Security Boundary

Security must cover:

- runtime credentials;
- provider credentials;
- tool permissions;
- project data;
- agent permissions;
- Skill provenance;
- external resources;
- sensitive context.

The Orchestrator should not need direct access to every credential simply because a subagent needs it.

---

# 57. Permission Delegation

Where the runtime supports scoped permissions:

```text
Orchestrator
→ grants minimum required capability
```

rather than:

```text
Agent
→ full system access
```

The exact permission model will depend on the runtime.

---

# 58. Skill Loading Boundary

Knowledge can exist in several forms:

```text
prompt
Skill
reference
project context
memory
tool
```

The architecture must not force all knowledge into the prompt.

---

# 59. Prompt Boundary

The Orchestrator prompt should contain:

- role;
- priorities;
- rules;
- boundaries;
- behavior;
- decision principles.

Deep reference knowledge can remain outside the prompt and be loaded as needed.

---

# 60. Specialist Agent Boundary

The Orchestrator should not necessarily possess all specialist operational knowledge.

Example:

```text
Orchestrator
→ knows architecture sufficiently to supervise

Architecture Agent
→ possesses deeper architecture knowledge to execute
```

This preserves the project's intended division of cognitive labor.

---

# 61. Knowledge Distribution

The architecture supports:

```text
Orchestrator Knowledge
      ↓
global reasoning

Specialist Knowledge
      ↓
specialist execution

Shared Knowledge
      ↓
common concepts

Project Knowledge
      ↓
current work
```

---

# 62. Integration with Future Specialist Agents

Future agents may include:

```text
Requirements Agent
Architecture Agent
Domain Agent
Data Agent
Documentation Agent
Implementation Agent
Testing Agent
Review Agent
Research Agent
```

These are not required to implement the core architecture immediately.

The architecture only needs to support their future addition.

---

# 63. Agent Composition

The system should support:

```text
Agent
+
Skill
+
Model
+
Tools
+
Project Context
```

without permanently coupling the agent to a single model.

---

# 64. Multiple Model Strategy

The architecture must support:

```text
Orchestrator → frontier model selected by developer

Specialist A → model A
Specialist B → model B
Specialist C → model C
Reviewer → model D
```

The exact selection is runtime/configuration dependent.

---

# 65. Cost Awareness

Cost metadata should be accessible to Resource Selection.

The core architecture must not assume a specific billing system.

---

# 66. External Knowledge

The system can use:

```text
web
documents
repositories
databases
tools
MCP
APIs
```

but external information must be represented with appropriate provenance and confidence where relevant.

---

# 67. Adaptation to OpenClaw

OpenClaw can provide:

- agent execution;
- workspace;
- Skills;
- subagents;
- model configuration;
- tools;
- runtime integrations.

Our architecture consumes those mechanisms through the Adapter.

---

# 68. Adaptation to Hermes

Hermes can provide:

- agent execution;
- Skills;
- subagents;
- tools;
- context;
- model configuration.

The Hermes Adapter will map equivalent concepts.

---

# 69. Unsupported Runtime Capability

If a runtime lacks a capability required by the Orchestrator:

```text
required capability
        ↓
runtime unsupported
        ↓
degrade
fallback
or
unsupported configuration
```

The system should not pretend the capability exists.

---

# 70. Runtime Capability Registry

The Adapter should eventually expose:

```text
Runtime Capability Profile
├── agents
├── subagents
├── skills
├── model selection
├── tools
├── context
├── memory
├── permissions
├── hooks
├── MCP
└── telemetry
```

This profile feeds Ecosystem Awareness.

---

# 71. Architecture and the Developer

The developer should remain able to configure:

```text
allowed models
allowed agents
allowed Skills
allowed runtimes
budget
policies
autonomy
approval thresholds
```

The Orchestrator operates within those boundaries.

---

# 72. Architecture and Human Intervention

Human decisions should enter the system as explicit state:

```text
Decision Requested
→ Human Decision
→ Decision Recorded
→ Replan if necessary
```

The system should not encode human decisions only in volatile conversation context.

---

# 73. Architecture and Reproducibility

For meaningful executions, preserve enough information to reproduce or diagnose:

```text
project state/version
Work Unit
agent
Skill version
model/version
runtime
important context references
policy version
result
evaluation
```

Exact reproducibility of stochastic model output is not assumed.

---

# 74. Architecture and Testing

The architecture should support testing at multiple levels:

```text
component
integration
system
runtime adapter
orchestration scenario
```

Later operational evaluations can complement conventional software tests.

---

# 75. Architecture and Evals

The project should eventually support an evaluation layer capable of testing:

```text
planning
delegation
selection
evaluation
replanning
continuity
```

The exact physical Evals structure is intentionally deferred.

---

# 76. Architectural Risks

Known risks include:

### R-ARCH-001 — Orchestrator monolith

Central component accumulates every responsibility.

**Mitigation:** capability boundaries and application services.

### R-ARCH-002 — Runtime lock-in

Core logic becomes dependent on OpenClaw.

**Mitigation:** Runtime Adapter.

### R-ARCH-003 — Context explosion

Agents receive excessive context.

**Mitigation:** Context Assembly and scoped packages.

### R-ARCH-004 — Excessive specialization

Too many agents create coordination cost.

**Mitigation:** Agent & Skill Analysis + economic selection.

### R-ARCH-005 — Knowledge duplication

Same knowledge copied across prompts and Skills.

**Mitigation:** Knowledge Layer with references and explicit ownership.

### R-ARCH-006 — Learning drift

Experience silently alters behavior.

**Mitigation:** candidate learning + validation + governance.

### R-ARCH-007 — State inconsistency

Project state and runtime state diverge.

**Mitigation:** explicit state/event boundaries.

### R-ARCH-008 — Hidden human decisions

Decisions remain only in conversation.

**Mitigation:** explicit Decision model.

---

# 77. Architectural Trade-offs

## Rich core versus simple core

A richer core supports more intelligent orchestration but increases complexity.

Chosen direction:

> **rich enough to represent project, resources and decisions, but modular rather than monolithic.**

---

## Multiple agents versus single agent

Multiple agents increase specialization and isolation but also increase coordination.

Chosen direction:

> **dynamic composition, not fixed agent count.**

---

## Deep context versus minimal context

More context can improve comprehension but increases cost and noise.

Chosen direction:

> **context proportional to task needs.**

---

## Runtime integration versus portability

Deep runtime integration improves capability but creates coupling.

Chosen direction:

> **adapter-based integration.**

---

# 78. Initial Implementation Boundary

The first implementation should focus on:

```text
Orchestrator Core
+
Project State
+
Knowledge access
+
Ecosystem Registry
+
Planning
+
Agent / Skill Analysis
+
Resource Selection
+
Delegation
+
Evaluation
+
Replanning
+
Continuity
+
OpenClaw Adapter
```

Other runtime adapters can be added later.

---

# 79. What does not need to be implemented initially

Não é necessário no primeiro ciclo:

```text
multiple runtime adapters
complete autonomous learning
automatic Skill generation
automatic model discovery
advanced distributed execution
large-scale event infrastructure
universal provider abstraction
```

Esses recursos podem evoluir após o núcleo demonstrar utilidade.

---

# 80. Implementation Priority

Prioridade recomendada:

```text
1. Project State
2. Work Unit
3. Knowledge access
4. Ecosystem Registry
5. Planning
6. Resource Selection
7. Delegation
8. Result Evaluation
9. Replanning
10. Continuity
11. Runtime Adapter
12. Specialist Agents
```

A ordem de implementação detalhada será definida na próxima etapa de Design.

---

# 81. Definition of Architecture Complete

A arquitetura estará conceitualmente suficiente quando:

```text
responsibilities defined
+
components defined
+
boundaries defined
+
main flows defined
+
state model defined conceptually
+
runtime boundary defined
+
knowledge boundary defined
+
security boundary defined
+
extension strategy defined
+
major risks identified
```

Sem necessidade de determinar ainda todos os detalhes físicos.

---

# 82. Relação com Requisitos

A arquitetura deve permitir rastrear:

```text
Requirement
→ Component
→ Responsibility
→ Flow
→ Verification
```

Exemplo:

```text
RF-ORC-027 Delegation
→ Delegation Engine
→ Runtime Adapter
→ Task Package / Handoff flow
→ Integration test
```

---

# 83. Relação com conhecimento legado

A arquitetura reutiliza diretamente princípios do legado:

- separação de responsabilidades;
- adaptação ao contexto;
- suficiência;
- diagnóstico proporcional;
- estados;
- dependências;
- paralelismo;
- baseline;
- impacto;
- rastreabilidade;
- validação;
- evolução controlada.

A diferença é que o novo sistema adiciona uma camada explícita de:

```text
Agents
Skills
Models
Runtime
Delegation
Resource Selection
Operational Learning
```

---

# 84. Estado

**Status:** Arquitetura conceitual inicial consolidada.

Este documento define a arquitetura necessária para iniciar o detalhamento técnico sem ainda fixar a implementação em uma plataforma específica.

---

# 85. Próxima fase

A próxima fase será:

## **Design do Sistema**

Nela serão detalhados:

```text
component interfaces
domain models
schemas
state transitions
APIs
contracts
runtime adapter contracts
persistence model
knowledge structures
execution protocols
error handling
configuration
```

Somente então a implementação poderá começar de forma organizada.

---

# 86. Fechamento

A arquitetura final proposta separa claramente:

```text
                      ORCHESTRATOR
                           │
                  ┌────────┴────────┐
                  ▼                 ▼
             OUR SYSTEM          RUNTIME
                  │                 │
        ┌─────────┼─────────┐       │
        ▼         ▼         ▼       ▼
     Project   Knowledge  Decision OpenClaw
     State     Ecosystem  Engine   Hermes
        │         │         │       Other
        └─────────┼─────────┘
                  ▼
            Coordination
                  │
                  ▼
              Agents
                  │
                  ▼
               Results
                  │
                  ▼
              Evaluation
                  │
                  ▼
             Replanning
                  │
                  ▼
             Continuity
                  ↺
```

O sistema passa a possuir uma fronteira clara entre **o conhecimento e a inteligência de orquestração que estamos desenvolvendo** e **a infraestrutura de execução fornecida por OpenClaw, Hermes ou outro runtime**.


# 87. Adaptive Message Exchange Protocol — AMEP v1

A evolução operacional demonstrou que o canal conversacional/runtime não deve ser
tratado como armazenamento autoritativo de payloads extensos. O contrato atual
adota o **Adaptive Message Exchange Protocol (AMEP) v1**:

    componente emissor
    -> payload completo no Message Store do projeto
    -> manifest + SHA-256 + schema versionado
    -> MESSAGE_REF compacto
    -> runtime/control plane
    -> receptor verifica e lê o payload completo

O protocolo é transversal a Planner, Adaptive, Workers, Evaluator,
Sentinel/watchers e futuros subagentes. Chat/history permanece canal de
apresentação/progresso, não fonte autoritativa de dados de máquina.

O Worker Result Store existente é preservado como perfil endurecido e integrado
ao AMEP; não existe uma segunda semântica concorrente de comunicação.

Contrato normativo detalhado:

`docs/architecture/ADAPTIVE-MESSAGE-EXCHANGE-PROTOCOL.md`

Schemas de transporte:

`specifications/protocols/`

Invariantes principais:

- publicação de payload antes da referência;
- escrita atômica;
- referência e payload verificados por hash;
- mensagens versionadas por tipo/schema;
- validação específica do domínio após validação de transporte;
- nenhuma Skill, prompt ou worker pode redefinir o protocolo obrigatório.
