# ORCHESTRATOR-SYSTEM-DESIGN

**Projeto:** Adaptive AI Orchestrator
**Versão:** v0.2 — design consolidado após revisão arquitetural
**Status:** Design consolidado — pronto para Implementation Plan
**Base:** `ORCHESTRATOR-SYSTEM-ARCHITECTURE.md` + `ORCHESTRATOR-REQUIREMENTS.md`

**Discipline transversal:** `ORCHESTRATOR-SPEC-DRIVEN-DEVELOPMENT.md`

---

# 1. Objetivo

Este documento transforma a arquitetura conceitual do Adaptive AI Orchestrator em um design suficientemente detalhado para orientar a futura implementação.

O design deve responder:

> **Como os componentes, objetos, contratos, camadas e dependências serão organizados para produzir uma implementação limpa, coesa, testável, extensível e independente de detalhes de infraestrutura?**

A principal referência arquitetural adotada é a família de abordagens:

```text
Clean Architecture
Onion Architecture
Hexagonal Architecture
Ports and Adapters
DDD
Separation of Concerns
Dependency Inversion
Single Responsibility
```

Essas abordagens possuem diferenças de terminologia e aplicação, mas convergem em um princípio essencial: **as regras centrais do sistema não devem depender diretamente de detalhes externos e de infraestrutura**. A documentação da Microsoft sobre Clean Architecture descreve justamente a lógica de negócio e o modelo de aplicação no centro, com infraestrutura e interfaces externas dependendo do núcleo; também relaciona Clean Architecture a Onion e Ports-and-Adapters. citeturn483369search0turn483369search1turn483369search5

Robert C. Martin trata Clean Architecture como uma disciplina de arquitetura e design voltada a manter as decisões importantes independentes de detalhes e a preservar a capacidade de evolução do sistema. citeturn297293search2turn297293search3

---

# 2. Decisão arquitetural principal

## 2.1 Estilo adotado

O design adotará:

> **Clean Architecture com elementos de DDD e Ports-and-Adapters.**

Não significa copiar uma estrutura específica de um framework.

Significa aplicar seus princípios ao domínio particular do Orchestrator.

---

# 3. Por que Clean Architecture é adequada ao Orchestrator

O Orchestrator possuirá muitos detalhes externos e voláteis:

```text
OpenClaw
Hermes
outros runtimes
LLMs
providers
modelos
APIs
MCPs
ferramentas
banco
filesystem
telemetria
```

Esses elementos podem mudar sem que o conceito de:

```text
Work Unit
Decision
Plan
Evaluation
Agent
Skill
Model Selection
```

precise ser reconstruído.

Portanto:

```text
DETALHES EXTERNOS
        ↓
dependem de
        ↓
NÚCLEO
```

e não o contrário.

---

# 4. Regra de Dependência

A regra de dependência do design é:

```text
Interface / Infrastructure
        ↓
Application
        ↓
Domain
```

Nunca:

```text
Domain
 ↓
OpenClaw
```

ou:

```text
Domain
 ↓
SQL
```

ou:

```text
Domain
 ↓
SDK de provider
```

A direção de dependência deve apontar para o núcleo.

---

# 5. Camadas do sistema

A implementação será organizada conceitualmente em:

```text
┌──────────────────────────────────────────────┐
│ Interface / Delivery                         │
├──────────────────────────────────────────────┤
│ Application                                   │
├──────────────────────────────────────────────┤
│ Domain / Core                                 │
├──────────────────────────────────────────────┤
│ Ports / Contracts                             │
├──────────────────────────────────────────────┤
│ Infrastructure / Adapters                     │
└──────────────────────────────────────────────┘
```

Observação:

**Ports não devem ser entendidos necessariamente como uma camada física isolada.**

Na implementação, contratos pertencentes ao domínio ou à aplicação podem estar localizados junto às abstrações que os consomem. O objetivo é preservar a direção das dependências, não produzir uma árvore de diretórios por estética.

---

# 6. Domain Layer

É o núcleo do sistema.

Responsável por representar as regras e conceitos próprios do Orchestrator.

Deve conter:

```text
Project
WorkUnit
Plan
Dependency
Decision
Baseline
Evaluation
AgentProfile
SkillProfile
ModelProfile
ResourceConfiguration
Policy
LearningCandidate
ProjectState
```

Quando uma regra for intrínseca ao significado desses conceitos, ela pertence ao domínio.

---

# 7. O que não pertence ao Domain

Não devem estar no Domain:

```text
OpenClaw SDK
Hermes SDK
HTTP clients
SQL/ORM
filesystem
LLM SDK
MCP client
CLI framework
Web framework
logging implementation
concrete provider
```

Esses elementos pertencem à infraestrutura ou à interface.

---

# 8. Application Layer

A camada de Application representa **casos de uso e coordenação de operações**.

Ela não é o domínio.

Ela orquestra objetos e portas do domínio para realizar casos de uso.

Exemplos:

```text
InitializeProject
AnalyzeProject
StructureProject
ApproveStructure
CreateWorkUnits
AnalyzeAgentCapabilities
SelectResource
DelegateWork
EvaluateResult
ReplanProject
ResumeProject
RecordLearning
```

A camada de aplicação deve permanecer suficientemente fina.

A documentação da Microsoft sobre DDD enfatiza exatamente que a camada de aplicação coordena trabalho e delega as regras de negócio ao domínio, em vez de concentrar conhecimento de domínio nela. citeturn483369search4turn483369search8

---

# 9. Infrastructure Layer

A infraestrutura implementa detalhes externos.

Exemplos:

```text
OpenClawRuntimeAdapter
HermesRuntimeAdapter
PostgresProjectRepository
FileKnowledgeRepository
OpenAIModelProvider
AnthropicModelProvider
MCPToolAdapter
HttpEvidenceProvider
TelemetryAdapter
```

Essas implementações devem satisfazer contratos definidos pelas camadas internas.

---

# 10. Interface / Delivery Layer

Representa como o sistema é acionado.

Pode incluir:

```text
CLI
REST API
Web UI
Background Worker
Agent Runtime Entrypoint
Test Harness
```

A interface não deve possuir regras de negócio.

Ela traduz:

```text
entrada externa
→ comando / request
```

e:

```text
resultado
→ response
```

---

# 11. Ports and Adapters

O sistema terá dois tipos conceituais de portas.

## Input Ports

Representam operações que o sistema oferece:

```text
InitializeProject
PlanWork
DelegateWork
EvaluateResult
Replan
ResumeProject
```

## Output Ports

Representam capacidades externas necessárias:

```text
ProjectRepository
KnowledgeRepository
AgentRuntime
ModelCatalog
SkillCatalog
ToolGateway
EventStore
TelemetrySink
Clock
```

Os adapters implementam essas portas.

---

# 12. Regra de Inversão

O Domain/Application define o contrato.

A Infrastructure implementa o contrato.

Exemplo:

```text
Application
    ↓
ProjectRepository
    ↑
PostgresProjectRepository
```

Não:

```text
Application
    ↓
PostgresProjectRepository
```

---

# 13. Single Responsibility Principle

Responsabilidade única será interpretada como:

> **um componente deve ter uma razão principal de mudança coerente.**

Não significa:

```text
uma classe por método
```

nem:

```text
uma classe de três linhas para qualquer ação
```

A granularidade deve ser suficiente para:

- isolamento;
- testabilidade;
- clareza;
- coesão;
- manutenção.

---

# 14. Alta coesão

Um módulo deve concentrar conceitos fortemente relacionados.

Exemplo bom:

```text
work_unit/
├── WorkUnit
├── WorkUnitState
├── WorkUnitPolicy
└── WorkUnitRules
```

Exemplo ruim:

```text
utils/
├── WorkUnit
├── Agent
├── Repository
├── SQL
├── Prompt
└── Logging
```

---

# 15. Baixo acoplamento

Componentes devem depender de abstrações estáveis.

Evitar:

```text
DelegationService
→ OpenClawClient
→ SQL
→ PromptParser
→ Filesystem
```

Preferir:

```text
DelegationService
→ AgentRuntime
→ KnowledgeProvider
→ WorkUnitRepository
```

com adapters externos implementando as interfaces.

---

# 16. Domínio do Orchestrator

O domínio é diferente do domínio de um software empresarial tradicional.

O domínio principal é:

> **gestão adaptativa da execução de trabalho por agentes e recursos de IA em um projeto.**

Portanto, as regras centrais tratam de:

- trabalho;
- dependência;
- capacidade;
- delegação;
- seleção;
- avaliação;
- estado;
- decisão;
- evolução.

---

# 17. Bounded Context conceitual

O sistema pode ser tratado como um contexto delimitado:

```text
Adaptive AI Orchestration
```

Dentro dele existem subdomínios/modos de responsabilidade:

```text
Project Management
Resource Management
Agent Capability Management
Execution Coordination
Evaluation
Continuity
Learning
Governance
```

Esses agrupamentos não precisam se tornar microsserviços.

Eles são limites conceituais.

---

# 18. Domain Model — Project

```text
Project
├── id
├── identity
├── objectives
├── scope
├── requirements
├── constraints
├── decisions
├── structure
├── baseline
├── workUnits
├── dependencies
├── risks
└── status
```

O Project deve proteger invariantes importantes do seu estado.

---

# 19. Domain Model — WorkUnit

```text
WorkUnit
├── id
├── objective
├── scope
├── inputs
├── outputs
├── dependencies
├── preconditions
├── requiredCapabilities
├── criteria
├── priority
├── criticality
├── state
└── executionReference
```

Uma Work Unit representa uma unidade de trabalho controlável.

---

# 20. WorkUnit Invariants

Exemplos:

- uma Work Unit deve possuir identidade;
- uma Work Unit executável deve possuir objetivo;
- uma Work Unit concluída deve atender aos critérios aplicáveis;
- uma Work Unit bloqueada não deve ser tratada como pronta;
- uma dependência obrigatória não pode ser ignorada.

---

# 21. Value Objects

Value Objects podem representar conceitos sem identidade própria.

Exemplos:

```text
ProjectId
WorkUnitId
AgentId
SkillId
ModelId
Priority
Criticality
Confidence
CostEstimate
LatencyEstimate
ContextBudget
Version
```

Eles ajudam a evitar valores primitivos sem semântica.

---

# 22. Enums e estados

Estados relevantes devem possuir representação explícita.

Exemplo:

```text
WorkUnitState
- PLANNED
- READY
- BLOCKED
- RUNNING
- EVALUATING
- REVISION_REQUIRED
- COMPLETED
- CANCELLED
- REOPENED
```

A lista final será refinada durante o design detalhado.

---

# 23. State Machine

Estados importantes devem possuir transições autorizadas.

Exemplo:

```text
PLANNED
  ↓
READY
  ↓
RUNNING
  ↓
EVALUATING
  ├── COMPLETED
  ├── REVISION_REQUIRED
  └── BLOCKED
```

Retorno:

```text
REVISION_REQUIRED
→ RUNNING
```

Reabertura:

```text
COMPLETED
→ REOPENED
→ READY
```

---

# 24. Não usar estado como texto livre

Evitar:

```text
status = "acho que está quase pronto"
```

Preferir estado tipado:

```text
WorkUnitState.EVALUATING
```

Informações qualitativas complementares podem existir separadamente.

---

# 25. Dependency Model

```text
Dependency
├── source
├── target
├── type
├── required
├── condition
└── status
```

Tipos possíveis:

```text
artifact
decision
knowledge
resource
sequence
external
```

A lista definitiva poderá crescer conforme surgirem necessidades.

---

# 26. Dependency Rules

Uma dependência obrigatória deve impedir a execução do alvo quando a pré-condição não estiver satisfeita.

Dependências independentes não devem bloquear umas às outras.

Isso incorpora diretamente a lógica de dependências do legado.

---

# 27. Plan Model

```text
Plan
├── version
├── baseline
├── workUnits
├── dependencies
├── priorities
├── parallelGroups
├── gates
└── status
```

O Plan representa o estado planejado.

O Project representa o projeto como um todo.

---

# 28. Decision Model

```text
Decision
├── id
├── question
├── context
├── evidence
├── alternatives
├── impact
├── risks
├── recommendation
├── authority
├── decision
├── timestamp
└── version
```

Decisions críticas devem ser persistidas.

---

# 29. Evaluation Model

```text
Evaluation
├── id
├── target
├── evaluator
├── criteria
├── evidence
├── findings
├── verdict
├── confidence
├── impact
└── timestamp
```

Verdict pode incluir:

```text
ACCEPTED
ACCEPTED_WITH_CONDITIONS
RETURNED
BLOCKED
REJECTED
```

---

# 30. Agent Profile

```text
AgentProfile
├── id
├── role
├── responsibilities
├── capabilities
├── skills
├── tools
├── eligibleModels
├── contextRequirements
├── permissions
├── runtime
└── evidence
```

O perfil declarado deve ser separado do histórico empírico.

---

# 31. Skill Profile

```text
SkillProfile
├── id
├── purpose
├── capabilities
├── inputs
├── outputs
├── dependencies
├── compatibleAgents
├── compatibleModels
├── compatibleRuntimes
├── version
└── evidence
```

---

# 32. Model Profile

```text
ModelProfile
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

---

# 33. ResourceConfiguration

```text
ResourceConfiguration
├── agent
├── skills
├── model
├── provider
├── tools
├── runtime
└── policyConstraints
```

Esse objeto representa uma configuração concreta candidata ou selecionada.

---

# 34. Task Package Model

```text
TaskPackage
├── taskId
├── workUnitId
├── objective
├── scope
├── context
├── inputs
├── artifacts
├── decisions
├── dependencies
├── constraints
├── configuration
├── expectedOutput
└── acceptanceCriteria
```

TaskPackage não deve conter regras de negócio da execução do agente; ele transmite contrato e contexto.

---

# 35. Result Package Model

```text
ResultPackage
├── taskId
├── status
├── result
├── artifacts
├── decisions
├── assumptions
├── evidence
├── discoveredDependencies
├── discoveredIssues
├── uncertainty
├── recommendations
└── metadata
```

---

# 36. LearningCandidate

```text
LearningCandidate
├── observation
├── context
├── evidence
├── scope
├── confidence
├── potentialImpact
├── proposedUse
├── validationStatus
└── history
```

Esse objeto impede que experiência seja transformada diretamente em regra.

---

# 37. Policy Model

```text
Policy
├── id
├── scope
├── authority
├── allowedActions
├── deniedActions
├── escalationRules
└── version
```

Políticas devem possuir precedência sobre preferências operacionais.

---

# 38. Interfaces de Domínio

O Domain deve possuir interfaces apenas quando elas forem necessárias para inverter dependências ou representar políticas essenciais.

Evitar criar interfaces artificiais para todas as classes.

---

# 39. Repository Ports

Exemplos:

```text
ProjectRepository
WorkUnitRepository
DecisionRepository
EvaluationRepository
LearningRepository
EventStore
```

Esses contratos pertencem à camada interna que necessita das operações.

---

# 40. Runtime Port

Uma abstração conceitual:

```text
AgentRuntime
├── discover
├── execute
├── monitor
├── cancel
├── retrieveResult
└── telemetry
```

A implementação concreta será OpenClaw, Hermes ou outra.

---

# 41. Model Catalog Port

```text
ModelCatalog
├── getModel
├── listEligible
├── capabilities
├── availability
└── metadata
```

---

# 42. Skill Catalog Port

```text
SkillCatalog
├── getSkill
├── search
├── capabilities
├── dependencies
└── compatibility
```

---

# 43. Agent Catalog Port

```text
AgentCatalog
├── getAgent
├── search
├── capabilities
├── skills
└── availability
```

---

# 44. Knowledge Port

```text
KnowledgeProvider
├── retrieve
├── search
├── cite/provenance
├── confidence
└── version
```

A interface deve permitir múltiplos backends.

---

# 45. Tool Gateway Port

```text
ToolGateway
├── listTools
├── authorize
├── invoke
└── inspectResult
```

O Domain não deve conhecer a API de um MCP específico.

---

# 46. Clock Port

Para operações dependentes de tempo:

```text
Clock
→ now()
```

Isso aumenta testabilidade.

---

# 47. Id Generator Port

```text
IdGenerator
→ next()
```

Permite testes determinísticos e evita acoplamento a mecanismos concretos de geração de IDs.

---

# 48. Use Case Layer

Cada caso de uso deve possuir uma responsabilidade clara.

Exemplo:

```text
InitializeProject
```

Responsável por inicialização.

Não:

```text
InitializeProject
→ executar agente
→ salvar SQL
→ gerar prompt
→ chamar API
→ enviar email
```

Essas responsabilidades pertencem a outras portas/serviços.

---

# 49. Use Case — Structure Project

```text
StructureProject
1. load project
2. validate context
3. request structural proposal
4. receive proposal
5. invoke structural evaluation
6. approve or return
7. persist baseline
```

---

# 50. Use Case — Plan Work

```text
PlanWork
1. load baseline
2. identify Work Units
3. evaluate dependencies
4. determine readiness
5. prioritize
6. produce Plan
```

---

# 51. Use Case — Select Resource

```text
SelectResource
1. load Work Unit
2. identify capabilities
3. query AgentCatalog
4. query SkillCatalog
5. query ModelCatalog
6. apply Policy
7. evaluate alternatives
8. produce ResourceConfiguration
```

---

# 52. Use Case — Delegate Work

```text
DelegateWork
1. load Work Unit
2. load configuration
3. validate preconditions
4. assemble TaskPackage
5. call AgentRuntime
6. persist execution state
7. monitor
8. retrieve ResultPackage
```

---

# 53. Use Case — Evaluate Result

```text
EvaluateResult
1. load ResultPackage
2. load criteria
3. load relevant project state
4. evaluate
5. persist Evaluation
6. update WorkUnit state
7. trigger Replanning if needed
```

---

# 54. Use Case — Replan

```text
ReplanProject
1. load current Plan
2. load event/change
3. analyze impact
4. identify affected WorkUnits
5. preserve unaffected work
6. adjust plan
7. re-evaluate resources
8. validate new plan
9. persist version
```

---

# 55. Use Case — Learn

```text
RecordLearning
1. collect execution evidence
2. classify observation
3. create LearningCandidate
4. assess confidence
5. persist
6. promote only after validation
```

---

# 56. Service boundaries

Serviços de aplicação podem existir quando:

```text
uma operação exige coordenação entre múltiplos objetos
```

Não criar serviços apenas para encapsular uma única atribuição.

---

# 57. Domain Services

Um Domain Service é adequado quando:

- a regra pertence ao domínio;
- a operação envolve múltiplos agregados;
- não pertence naturalmente a uma entidade única.

Exemplos possíveis:

```text
DependencyResolutionService
ResourceEligibilityService
ImpactAssessmentService
```

---

# 58. Application Services

Exemplos:

```text
ProjectOrchestrationService
ExecutionCoordinator
PlanningService
EvaluationApplicationService
LearningApplicationService
```

Eles coordenam casos de uso, não substituem as entidades de domínio.

---

# 59. Aggregate boundaries

Agregados devem proteger invariantes que precisem ser consistentes juntos.

Possíveis candidatos:

```text
Project
Plan
WorkUnit
Decision
ResourceConfiguration
```

A definição final de agregados será refinada quando as invariantes estiverem completamente definidas.

Não transformar automaticamente cada entidade em agregado.

---

# 60. Repository responsibilities

Repositories devem:

- persistir;
- recuperar;
- consultar por critérios relevantes ao domínio.

Não devem:

- conter regras de negócio;
- escolher modelos;
- construir prompts;
- executar agentes.

---

# 61. DTOs

DTOs devem ser utilizados quando houver fronteira entre:

```text
Application ↔ Interface
Application ↔ External Adapter
```

Evitar expor diretamente entidades de domínio a APIs externas quando isso criar acoplamento ou vazar invariantes.

---

# 62. Mapping

Mapeamentos devem existir explicitamente quando necessário:

```text
Domain Model
↔
Persistence Model

Domain Model
↔
API DTO

Domain Model
↔
Runtime DTO
```

A entidade do domínio não deve carregar dependências de formato externo.

---

# 63. Persistence Model

O modelo físico de persistência pode divergir do modelo de domínio.

Isso é aceitável e frequentemente desejável.

O objetivo é:

```text
persistência otimizada
sem contaminar domínio
```

A documentação da Microsoft sobre DDD reforça justamente o isolamento do domínio em relação à infraestrutura de persistência. citeturn483369search4turn483369search7

---

# 64. Infrastructure Adapters

Adapters externos incluem:

```text
OpenClawAdapter
HermesAdapter
PostgresRepository
FileRepository
OpenAIAdapter
AnthropicAdapter
MCPAdapter
HttpAdapter
TelemetryAdapter
```

Cada adapter deve possuir responsabilidade específica.

---

# 65. OpenClaw Adapter Responsibility

O adapter deve traduzir:

```text
ResourceConfiguration
→ OpenClaw configuration

TaskPackage
→ OpenClaw execution request

OpenClaw result
→ ResultPackage
```

Não deve conter:

```text
"qual agente devo escolher?"
```

Essa decisão pertence ao Application/Decision layer.

---

# 66. Hermes Adapter Responsibility

Mesma regra:

```text
ResourceConfiguration
→ Hermes configuration

TaskPackage
→ Hermes execution

Hermes result
→ ResultPackage
```

A implementação não deve alterar o modelo de decisão central.

---

# 67. Model Provider Adapters

Um provider adapter deve cuidar apenas de:

- conexão;
- autenticação;
- chamada;
- resposta;
- metadados técnicos.

Não deve decidir a estratégia do projeto.

---

# 68. Tool Adapters

Um adapter de ferramenta deve:

```text
Tool invocation
→ external service
→ result
```

e traduzir erros relevantes.

Não deve tomar decisões de planejamento.

---

# 69. Error Model

Erros devem ser categorizáveis.

Exemplos:

```text
DomainError
ValidationError
PolicyViolation
ResourceUnavailable
RuntimeError
ProviderError
ToolError
TimeoutError
ContextError
PersistenceError
ConflictError
```

---

# 70. Business Error versus Technical Error

Separar:

```text
regra de domínio violada
```

de:

```text
infraestrutura indisponível
```

Isso permite decisões de recuperação diferentes.

---

# 71. Retry Policy

Retry deve existir na camada apropriada.

```text
transient technical failure
→ retry possível
```

Mas:

```text
invalid domain decision
→ retry não resolve
```

---

# 72. Fallback Policy

Fallback é uma decisão de aplicação/recurso, não uma responsabilidade do adapter.

Adapter informa:

```text
unavailable
```

A camada superior decide:

```text
fallback
reselection
pause
escalation
```

---

# 73. Observability Design

Eventos importantes devem ser emitidos em pontos claros.

Exemplo:

```text
TaskDelegated
TaskStarted
TaskCompleted
TaskFailed
ResultEvaluated
PlanChanged
DecisionRequested
```

Esses eventos não devem exigir que o domínio conheça um sistema de logging específico.

---

# 74. Domain Events

Podem existir eventos de domínio como:

```text
WorkUnitReady
WorkUnitCompleted
WorkUnitBlocked
ResultAccepted
PlanChanged
DecisionRequired
LearningCandidateCreated
```

Eles representam mudanças semanticamente relevantes.

---

# 75. Event Bus

Um Event Bus concreto é infraestrutura.

O domínio/aplicação deve depender de uma abstração quando necessário.

---

# 76. Transaction Boundaries

Cada caso de uso deve definir uma fronteira consistente.

Exemplo:

```text
EvaluateResult
→ persist Evaluation
→ update WorkUnit
→ update Project
```

A implementação deve garantir consistência conforme o mecanismo de persistência escolhido.

---

# 77. Concurrency Control

Se duas execuções tentarem alterar a mesma Work Unit:

```text
version conflict
```

deve ser detectado.

Possibilidades:

```text
optimistic concurrency
```

ou mecanismo equivalente.

A tecnologia concreta será definida posteriormente.

---

# 78. Idempotent Commands

Comandos críticos devem possuir identificação:

```text
commandId
```

quando necessário.

Isso reduz efeitos duplicados em retries.

---

# 79. Configuration Model

A configuração do sistema deve ser separada do domínio.

Exemplo:

```text
OrchestratorConfig
├── runtime
├── policies
├── budgets
├── model policies
├── persistence
├── telemetry
└── environment
```

---

# 80. Secrets

Credenciais não devem ser armazenadas nas entidades do domínio.

Devem ser tratadas pela infraestrutura de configuração/segredos.

---

# 81. Environment Separation

Configurações devem poder variar entre:

```text
development
test
staging
production
```

sem alterar o código de domínio.

---

# 82. Testing Design

A organização de testes deve seguir as camadas.

```text
tests/
├── domain/
├── application/
├── infrastructure/
├── integration/
└── system/
```

A estrutura física será definida na implementação.

---

# 83. Domain Tests

Devem testar:

```text
invariants
state transitions
dependency rules
decision rules
policy rules
```

Sem depender de runtime externo.

---

# 84. Application Tests

Devem testar:

```text
use cases
orchestration
port interactions
error paths
state transitions
```

Usando doubles/fakes para adapters.

---

# 85. Adapter Tests

Devem verificar:

```text
translation
serialization
authentication behavior
error translation
runtime compatibility
```

---

# 86. Integration Tests

Devem verificar combinações reais ou controladas:

```text
Application
+
Persistence
```

e:

```text
Application
+
Runtime Adapter
```

---

# 87. System Tests

Devem verificar fluxos completos:

```text
Project
→ structure
→ plan
→ selection
→ delegation
→ evaluation
→ replan
```

---

# 88. Evals versus software tests

Devem permanecer distintos.

### Software tests

Verificam:

```text
comportamento determinístico
contratos
estado
integração
erros
```

### Evals

Verificam:

```text
qualidade de decisões
qualidade de planejamento
adequação de delegação
qualidade de avaliação
uso adequado do conhecimento
```

Essa distinção será importante para o sistema agentic.

---

# 89. Clean Code

O código futuro deve observar:

- nomes explícitos;
- funções pequenas quando isso aumentar clareza;
- classes coesas;
- ausência de duplicação relevante;
- tratamento explícito de erros;
- dependências claras;
- comentários apenas quando agregarem contexto;
- preferência por código que explique sua intenção.

Clean Code é uma disciplina de legibilidade e manutenção, não um conjunto de regras mecânicas.

---

# 90. Single Responsibility aplicada

Pergunta para cada componente:

> **"Qual é a razão principal para este componente mudar?"**

Se a resposta possuir múltiplas razões independentes:

```text
split responsibility
```

Se a divisão produzir apenas indireção artificial:

```text
keep together
```

---

# 91. Dependency Inversion aplicada

O sistema deve depender de abstrações estáveis.

Exemplo:

```text
EvaluationUseCase
        ↓
EvidenceProvider
        ↑
DocumentEvidenceProvider
```

em vez de:

```text
EvaluationUseCase
        ↓
SpecificPdfLibrary
```

---

# 92. Interface Segregation aplicada

Interfaces devem expor somente o necessário.

Evitar:

```text
HugeRuntimeInterface
```

Preferir:

```text
AgentExecutor
AgentMonitor
AgentResultReader
```

quando as responsabilidades forem independentes e isso reduzir acoplamento.

---

# 93. Open/Closed aplicada

O sistema deve permitir adicionar:

```text
novo runtime
novo provider
novo modelo
novo adapter
```

sem alterar regras centrais do domínio.

---

# 94. Liskov aplicada

Implementações de portas devem respeitar o contrato sem alterar a semântica esperada.

Por exemplo, um `HermesAdapter` não pode tratar sucesso de execução de forma incompatível com o contrato usado pelo `OpenClawAdapter`.

---

# 95. Dependency Rule — exemplo

### Permitido

```text
Infrastructure
→ Application
→ Domain
```

### Proibido

```text
Domain
→ Infrastructure
```

### Também evitar

```text
Domain
→ OpenClaw
```

---

# 96. Package Boundaries

A estrutura de packages deverá seguir responsabilidades.

Uma proposta inicial:

```text
src/
├── domain/
├── application/
├── infrastructure/
└── interfaces/
```

Dentro de cada uma, agrupar por capacidade/coerência, não por uma pasta genérica para cada arquivo.

---

# 97. Estrutura inicial sugerida

Uma estrutura possível:

```text
src/
├── domain/
│   ├── projects/
│   ├── work/
│   ├── planning/
│   ├── resources/
│   ├── evaluation/
│   ├── decisions/
│   ├── policies/
│   └── learning/
│
├── application/
│   ├── project/
│   ├── planning/
│   ├── resource_selection/
│   ├── delegation/
│   ├── evaluation/
│   ├── replanning/
│   └── continuity/
│
├── infrastructure/
│   ├── persistence/
│   ├── runtimes/
│   │   ├── openclaw/
│   │   └── hermes/
│   ├── models/
│   ├── tools/
│   ├── knowledge/
│   └── telemetry/
│
└── interfaces/
    ├── cli/
    ├── api/
    └── runtime/
```

Esta é uma **proposta de design**, não ainda uma decisão final sobre a árvore física.

---

# 98. Não organizar por tecnologia no núcleo

Evitar:

```text
src/
├── openclaw/
├── postgres/
├── anthropic/
├── fastapi/
```

como estrutura principal.

A tecnologia deve ficar atrás das responsabilidades.

---

# 99. Organizar por capacidade quando útil

Dentro das camadas internas, é aceitável agrupar por domínio/capacidade:

```text
domain/work/
domain/evaluation/
domain/planning/
```

Isso melhora coesão.

---

# 100. Organização por feature versus camada

A implementação poderá utilizar uma combinação:

```text
Clean Architecture
+
feature-oriented modules
```

Exemplo:

```text
application/delegation/
    commands/
    services/
    ports/
```

desde que a direção das dependências permaneça clara.

---

# 101. Evitar "Service Blob"

Não criar:

```text
OrchestratorService
```

com centenas de responsabilidades.

Preferir casos de uso e serviços coesos:

```text
PlanWork
SelectResource
DelegateWork
EvaluateResult
ReplanProject
```

---

# 102. Evitar "God Object"

Nenhum objeto deve conhecer:

```text
Project
+
Agent
+
Model
+
SQL
+
OpenClaw
+
Prompt
+
Telemetry
```

ao mesmo tempo.

---

# 103. Application layer não é mero espelho do Domain

Nem toda entidade precisa de um serviço homônimo.

Exemplo:

```text
WorkUnit
WorkUnitService
```

não é automaticamente necessário.

Só existe serviço quando houver uma responsabilidade real de aplicação.

---

# 104. Repositories não são "lógica de negócio"

Repository:

```text
persist / retrieve
```

não:

```text
decide whether agent should execute
```

---

# 105. DTOs não são entidades de domínio

Um request externo:

```text
DelegateTaskRequest
```

não deve ser automaticamente:

```text
TaskPackage
```

Pode haver transformação explícita.

---

# 106. Prompt como Infrastructure Concern

O conteúdo conceitual do prompt é conhecimento e política.

A forma concreta de armazenar/carregar/enviar prompt pode ser infraestrutura/runtime.

Isso permite:

```text
knowledge
→ prompt builder
→ runtime
```

sem prender o Domain a strings específicas.

---

# 107. Skill loading

O Domain deve conhecer:

```text
Skill identity
capabilities
constraints
```

mas não:

```text
filesystem path /skills/foo/SKILL.md
```

Isso pertence ao adapter/repository.

---

# 108. Model selection

O Application layer solicita:

```text
select configuration
```

mas não precisa conhecer diretamente a SDK de cada modelo.

---

# 109. Runtime session

A sessão concreta de OpenClaw/Hermes deve ser um detalhe de infraestrutura.

O Domain deve conhecer apenas algo equivalente a:

```text
ExecutionReference
```

ou:

```text
AgentExecution
```

---

# 110. Context assembler

O Context Assembler pode ser um serviço de aplicação:

```text
Project State
+
Knowledge
+
Work Unit
+
Policy
→
TaskPackage
```

Ele não deve ser colocado no runtime adapter.

---

# 111. Evaluation pipeline

Uma avaliação pode ser estruturada:

```text
EvaluationRequest
→ CriteriaResolver
→ EvidenceResolver
→ Evaluator
→ Verdict
→ StateUpdate
```

Isso permite testar cada parte.

---

# 112. Replanning pipeline

```text
Change/Event
→ ImpactAssessment
→ AffectedSetResolver
→ PlanUpdater
→ ResourceReassessment
→ PlanValidator
→ New Plan
```

---

# 113. Resource Selection pipeline

```text
WorkUnit
→ CapabilityResolver
→ AgentCandidates
→ SkillCandidates
→ ModelCandidates
→ PolicyFilter
→ MultiObjectiveEvaluator
→ ResourceConfiguration
```

---

# 114. Delegation pipeline

```text
WorkUnit
→ Preconditions
→ ContextAssembly
→ TaskPackage
→ RuntimeAdapter
→ Execution
→ ResultPackage
```

---

# 115. Structural Analysis pipeline

```text
Project Context
→ Structure Request
→ Specialist Result
→ Structural Validator
→ Feedback or Approval
→ Baseline
```

---

# 116. Project Awareness pipeline

```text
Project Inputs
→ Evidence Collection
→ Context Model
→ State Reconstruction
→ Gaps
→ Project Awareness
```

---

# 117. Learning pipeline

```text
Execution Evidence
→ Outcome Classification
→ Pattern Detection
→ Learning Candidate
→ Validation
→ Promotion
```

---

# 118. Dependency Graph

O grafo deve ser tratado como domínio conceitual.

```text
Node
→ WorkUnit / Decision / Artifact / Knowledge

Edge
→ depends_on / produces / validates / requires
```

A persistência do grafo é uma decisão de infraestrutura.

---

# 119. Event-driven aspects

O sistema pode utilizar eventos internamente para:

- observabilidade;
- atualização de projeções;
- histórico;
- aprendizagem.

Isso não significa que todo o sistema precise ser event-driven.

---

# 120. Synchronous versus asynchronous execution

Casos simples podem ser síncronos:

```text
select
→ execute
→ result
```

Execuções longas podem ser assíncronas:

```text
delegate
→ return execution reference
→ monitor
→ result event
```

O Application layer deve suportar ambos quando necessário.

---

# 121. Execution Reference

Uma execução pode possuir:

```text
ExecutionReference
├── id
├── runtime
├── externalId
├── status
└── timestamps
```

Isso permite acompanhar uma execução externa sem expor o modelo do runtime ao Domain.

---

# 122. External Identity Mapping

Um agente do nosso sistema:

```text
AgentId = A001
```

pode corresponder a:

```text
OpenClaw agent id
```

ou:

```text
Hermes session/profile
```

O mapping pertence ao adapter.

---

# 123. Versioning

Versionar quando relevante:

```text
Project
Plan
WorkUnit
Skill
Prompt
Agent
Model
Policy
Knowledge
Evaluation
```

A versão deve ser associada quando ela for necessária para reproduzir ou explicar a execução.

---

# 124. Compatibility

A seleção deve considerar compatibilidade entre:

```text
Agent
Skill
Model
Tool
Runtime
```

Essa informação vem do Ecosystem Registry.

---

# 125. Runtime Capability Detection

Na inicialização:

```text
Runtime Adapter
→ discover capabilities
→ Ecosystem Registry
```

Isso evita hard-code de pressupostos.

---

# 126. Fail-fast versus degrade gracefully

Quando uma capacidade obrigatória estiver ausente:

```text
fail / block
```

Quando uma capacidade opcional estiver ausente:

```text
degrade
```

Exemplo:

```text
Telemetry unavailable
→ execute if policy allows

Required runtime execution unavailable
→ BLOCKED
```

---

# 127. Configuration validation

Antes de executar:

```text
ResourceConfiguration
→ validate
```

Verificar:

- agent;
- Skills;
- model;
- permissions;
- runtime;
- tools;
- context.

---

# 128. Policy validation

Antes de qualquer ação relevante:

```text
Action
→ Policy Engine
→ allowed / denied / escalation
```

---

# 129. Human approval port

O sistema deve possuir uma abstração equivalente a:

```text
HumanDecisionGateway
```

para casos que exigem intervenção.

---

# 130. Human decision package

```text
DecisionRequest
├── question
├── context
├── evidence
├── alternatives
├── impact
├── risks
└── recommendation
```

O resultado retorna como:

```text
DecisionResponse
```

---

# 131. Dependency Injection

A implementação deverá preferir Dependency Injection para:

- repositories;
- adapters;
- runtime;
- model catalogs;
- clock;
- identifiers;
- telemetry.

Isso reduz acoplamento.

---

# 132. Static factories versus containers

Não é obrigatório usar um container DI pesado.

O importante é:

```text
dependencies explicit
```

e:

```text
construction separate from behavior
```

---

# 133. Logging

Logging deve ser infraestrutura.

O Domain pode produzir:

```text
domain event / error
```

mas não deve depender diretamente de um logger concreto.

---

# 134. Configuration versus Policy

Não confundir:

```text
CONFIGURATION
```

com:

```text
POLICY
```

Configuration:

```text
"qual runtime usar?"
```

Policy:

```text
"quais runtimes são permitidos?"
```

---

# 135. Prompt versus Policy

Prompt:

```text
orientação comportamental
```

Policy:

```text
restrição de autoridade
```

Uma política crítica não deve existir somente porque foi escrita em prompt.

---

# 136. Knowledge versus Memory

Knowledge:

```text
informação estruturada reutilizável
```

Memory:

```text
estado/histórico operacional recuperável
```

Podem compartilhar infraestrutura, mas possuem funções diferentes.

---

# 137. Context versus Knowledge

Knowledge:

```text
informação disponível
```

Context:

```text
informação selecionada para uma execução específica
```

O Context Assembler faz a seleção.

---

# 138. Decision versus Result

Result:

```text
o que o agente produziu
```

Decision:

```text
o que foi escolhido como direção válida
```

Um resultado pode recomendar uma decisão sem tornar-se automaticamente uma decisão.

---

# 139. Evaluation versus Acceptance

Evaluation:

```text
análise
```

Acceptance:

```text
verdict
```

Separar os dois melhora auditabilidade.

---

# 140. Learning versus Rule

Learning:

```text
evidence / candidate
```

Rule:

```text
governed behavior
```

A promoção exige validação.

---

# 141. Architectural Decision Records

Decisões arquiteturais relevantes devem ser registradas como ADRs ou estrutura equivalente.

Exemplos:

```text
ADR-001 — Clean Architecture
ADR-002 — Runtime Adapter
ADR-003 — Project State
ADR-004 — Work Unit
ADR-005 — OpenClaw as first runtime
```

---

# 142. ADR Criteria

Uma decisão arquitetural relevante deve conter:

```text
context
problem
options
decision
consequences
status
```

---

# 143. Design Traceability

A relação deve ser:

```text
Requirement
→ Use Case
→ Domain Model
→ Application Service
→ Port
→ Adapter
→ Test
```

Exemplo:

```text
RF-ORC-027
→ UC-ORC-006
→ DelegateWork
→ AgentRuntime
→ OpenClawAdapter
→ integration test
```

---

# 144. Code Organization Rule

A organização física deve refletir responsabilidade e dependência.

Não deve ser construída apenas para "parecer Clean Architecture".

---

# 145. Folder rule

Uma pasta deve existir quando ajuda a representar:

```text
cohesion
boundary
ownership
dependency
```

Não criar uma pasta porque "Clean Architecture manda".

---

# 146. Class rule

Uma classe deve possuir responsabilidade clara.

Se uma classe muda por:

```text
runtime
+
business rule
+
persistence
```

há sinais fortes de violação de responsabilidade única.

---

# 147. Function rule

Funções devem ter:

- propósito claro;
- entrada compreensível;
- saída previsível;
- poucos efeitos colaterais;
- tratamento de erro explícito.

---

# 148. Dependency rule

Imports/dependencies devem permitir identificar rapidamente:

```text
who depends on whom
```

Idealmente, regras de lint/build podem reforçar a arquitetura.

---

# 149. Architecture Tests

Podem existir testes que verifiquem:

```text
Domain does not import Infrastructure
Application does not import concrete runtime
Infrastructure implements ports
```

Isso transforma a arquitetura em regra verificável.

---

# 150. Initial Design Folder Proposal

Proposta física inicial:

```text
src/
├── domain/
│   ├── project/
│   ├── work/
│   ├── planning/
│   ├── resource/
│   ├── evaluation/
│   ├── decision/
│   ├── policy/
│   └── learning/
│
├── application/
│   ├── project/
│   ├── structure/
│   ├── planning/
│   ├── resource_selection/
│   ├── delegation/
│   ├── evaluation/
│   ├── replanning/
│   └── continuity/
│
├── infrastructure/
│   ├── persistence/
│   ├── runtimes/
│   │   ├── openclaw/
│   │   └── hermes/
│   ├── models/
│   ├── skills/
│   ├── tools/
│   ├── knowledge/
│   └── telemetry/
│
└── interfaces/
    ├── cli/
    ├── api/
    └── runtime/
```

---

# 151. Tests Folder Proposal

```text
tests/
├── domain/
├── application/
├── infrastructure/
├── integration/
├── system/
└── architecture/
```

---

# 152. Documentation

Documentação de design deve permanecer separada do código.

Sugestão:

```text
docs/
├── architecture/
├── design/
├── decisions/
└── operations/
```

A estrutura final do repositório será definida posteriormente.

---

# 153. Package Ownership

Cada pacote deve possuir uma responsabilidade e um proprietário conceitual.

Exemplo:

```text
domain/work
→ regras de Work Unit

application/delegation
→ caso de uso de delegação

infrastructure/runtimes/openclaw
→ adaptação OpenClaw
```

---

# 154. No Shared Kernel indiscriminado

Evitar um pacote:

```text
common/
utils/
shared/
```

contendo tudo que "é usado por muitos".

Somente conceitos genuinamente compartilhados devem pertencer a um módulo comum.

---

# 155. Anti-Corruption Layer

O Runtime Adapter pode ser tratado como uma forma de Anti-Corruption Layer.

Sua função é impedir que conceitos específicos de:

```text
OpenClaw
Hermes
provider
tool
```

contaminem o modelo interno.

---

# 156. Adapter Translation

Exemplo:

```text
OpenClaw Session
→ ExecutionReference
```

não:

```text
Domain.WorkUnit
→ OpenClawSessionObject
```

---

# 157. Framework Independence

O núcleo não deve herdar de classes de:

```text
FastAPI
Flask
OpenClaw SDK
Hermes SDK
ORM
```

quando isso puder ser evitado.

---

# 158. Runtime Independence

O mesmo caso de uso:

```text
DelegateWork
```

deve ser capaz de utilizar:

```text
OpenClawAdapter
```

ou:

```text
HermesAdapter
```

sem mudança no caso de uso.

---

# 159. Provider Independence

A mesma seleção de modelo deve poder apontar para providers diferentes quando a configuração permitir.

---

# 160. Storage Independence

ProjectRepository pode ter:

```text
InMemory
File
Postgres
SQLite
```

sem alterar o domínio.

---

# 161. Initial Development Strategy

Implementar primeiro:

```text
Domain
→ Application
→ In-memory adapters
→ Tests
```

Depois:

```text
Persistence
→ Runtime adapter
→ External model/provider
```

Isso reduz simultaneamente:

- complexidade;
- dependências;
- custo inicial;
- dificuldade de teste.

---

# 162. Vertical Slice

Apesar da arquitetura em camadas, a implementação deve preferir progresso por fluxo completo.

Exemplo:

```text
Create Project
→ persist
→ load
→ inspect
```

depois:

```text
Create Work Unit
→ plan
→ select
→ delegate
```

em vez de construir toda a infraestrutura antes de ter um caso de uso executável.

---

# 163. Primeiro Vertical Slice

O primeiro slice recomendado:

```text
Initialize Project
+
Create Work Unit
+
Store State
+
Read State
```

Sem runtime externo.

Objetivo:

> provar o núcleo do estado e do domínio.

---

# 164. Segundo Vertical Slice

```text
Plan Work
+
Dependency
+
Ready/Blocked
```

Objetivo:

> provar planejamento e controle de dependências.

---

# 165. Terceiro Vertical Slice

```text
Agent & Skill Analysis
+
Resource Selection
```

com catálogo inicialmente in-memory.

Objetivo:

> provar decisão sem depender ainda de OpenClaw.

---

# 166. Quarto Vertical Slice

```text
Delegation
+
OpenClaw Adapter
```

Objetivo:

> provar a primeira integração real com o runtime escolhido.

---

# 167. Quinto Vertical Slice

```text
Result
+
Evaluation
+
Replanning
```

Objetivo:

> fechar o ciclo adaptativo.

---

# 168. Sexto Vertical Slice

```text
Continuity
+
Telemetry
+
Learning Candidate
```

Objetivo:

> tornar a execução observável e evolutiva.

---

# 169. Modern Application Architecture

A arquitetura moderna não deve ser interpretada como:

```text
controller
service
repository
```

simplesmente.

A preocupação principal é:

```text
dependency boundaries
cohesion
business rules
interfaces
external systems
```

A Microsoft destaca que separar componentes e utilizar interfaces explícitas ou mensagens ajuda a reduzir acoplamento e manter sistemas sustentáveis. citeturn483369search2

---

# 170. Layers are logical

Camadas são artefatos lógicos.

Não precisam necessariamente ser:

```text
5 processos
```

ou:

```text
5 microservices
```

ou:

```text
5 servidores
```

A documentação da Microsoft sobre DDD ressalta que camadas são artefatos lógicos usados para gerenciar complexidade e não são equivalentes à topologia de implantação. citeturn483369search4

---

# 171. Não transformar em microserviços cedo demais

O Orchestrator deve inicialmente ser tratado como:

```text
modular monolith
```

ou:

```text
single deployable application
```

com fronteiras internas fortes.

Não há requisito atual que justifique distribuir o núcleo em múltiplos serviços.

---

# 172. Por que modular monolith inicialmente

Benefícios:

- menor complexidade operacional;
- transações mais simples;
- depuração mais simples;
- menor latência interna;
- desenvolvimento mais rápido;
- capacidade de testar limites arquiteturais.

Se posteriormente houver razão real para distribuição, os limites modulares já estarão definidos.

---

# 173. Domain versus Application Core

No contexto do Orchestrator:

```text
Domain
→ significado e invariantes

Application
→ execução dos casos de uso
```

Exemplo:

```text
Domain:
"Work Unit bloqueada não está pronta."

Application:
"PlanWork deve verificar isso antes de liberar a unidade."
```

---

# 174. Infrastructure versus Application

```text
Application:
"preciso executar a tarefa."

Infrastructure:
"OpenClaw API precisa desta chamada específica."
```

Application não deve conhecer o mecanismo concreto.

---

# 175. Infrastructure versus Domain

```text
Infrastructure:
"Postgres usa esta query."

Domain:
"Project precisa preservar esta invariável."
```

Essas responsabilidades não devem se misturar.

---

# 176. Interface versus Application

```text
CLI:
"usuário enviou comando."

Application:
"executar caso de uso."
```

A CLI não deve decidir regras de domínio.

---

# 177. Design principle — explicit contracts

Contratos importantes devem ser explícitos:

```text
TaskPackage
ResultPackage
DecisionRequest
DecisionResponse
ResourceConfiguration
EvaluationResult
Plan
```

Isso facilita integração entre agentes e runtimes.

---

# 178. Design principle — stable abstractions

As abstrações internas devem representar capacidades estáveis:

```text
AgentRuntime
KnowledgeProvider
ProjectRepository
ModelCatalog
SkillCatalog
AgentCatalog
ToolGateway
```

e não tecnologias específicas.

---

# 179. Design principle — volatile details at the boundary

Detalhes voláteis devem ficar nas bordas:

```text
SDKs
API versions
provider clients
filesystem structure
runtime configuration
ORM
```

---

# 180. Design principle — no accidental coupling

Evitar dependências causadas por:

- tipos externos vazando;
- callbacks de framework no domínio;
- configurações globais;
- singletons indiscriminados;
- imports de infraestrutura no core.

---

# 181. Design principle — explicit state transitions

Transições de estado relevantes devem ser executáveis e testáveis.

Evitar alteração arbitrária:

```text
workUnit.status = ...
```

quando isso puder violar invariantes.

Preferir comportamento explícito:

```text
workUnit.start()
workUnit.block()
workUnit.complete()
workUnit.reopen()
```

quando apropriado ao modelo.

---

# 182. Design principle — immutable data where appropriate

Dados de evidência, decisões, versões e eventos podem se beneficiar de imutabilidade.

Isso reduz alterações acidentais.

---

# 183. Design principle — append-only history where useful

Histórico relevante pode ser modelado como eventos imutáveis:

```text
DecisionRecorded
ResultEvaluated
PlanChanged
```

enquanto o estado atual pode ser uma projeção.

---

# 184. Design principle — separate current state and event history

```text
CURRENT STATE
+
EVENT HISTORY
```

A persistência concreta será escolhida posteriormente.

---

# 185. Design principle — no implicit global state

Evitar estado global mutável.

O estado do projeto deve ser explícito e injetável.

---

# 186. Design principle — deterministic policies

Sempre que possível, políticas de:

- elegibilidade;
- transição;
- prioridade;
- autorização;

devem ser representadas de maneira testável e previsível.

---

# 187. Design principle — AI decisions remain observable

As decisões do modelo devem resultar em estruturas observáveis:

```text
decision
criteria
evidence
recommendation
confidence
```

sem depender de registrar cadeia privada de raciocínio.

---

# 188. AI-specific design boundary

A LLM não deve ser tratada como todo o Orchestrator.

```text
LLM
→ inferência

Orchestrator
→ estado + políticas + ferramentas + casos de uso + avaliação
```

Isso é fundamental.

---

# 189. LLM as dependency

A LLM deve ser tratada como dependência externa do sistema.

```text
ReasoningProvider
```

ou mecanismo equivalente pode abstrair:

- prompt;
- context;
- model;
- response.

---

# 190. Reasoning Provider

Uma abstração conceitual:

```text
ReasoningProvider
├── complete()
├── structuredOutput()
└── metadata()
```

O design final poderá usar interfaces mais específicas.

---

# 191. Não colocar negócio no Prompt

Regras críticas do sistema não devem existir somente em prompt.

Exemplo:

```text
"não execute tarefa bloqueada"
```

deve ser protegido pela aplicação/domínio, não apenas instruído ao LLM.

O prompt é uma camada de orientação, não substituto de enforcement.

---

# 192. Prompt as policy hint

O prompt pode ajudar o agente a:

```text
priorizar
explicar
estruturar
seguir procedimento
```

Mas políticas críticas devem ser verificadas pelo software.

---

# 193. Agent as execution unit

Um agente runtime é um recurso de execução.

A lógica de projeto permanece fora dele.

```text
Orchestrator
→ decide
→ delegate
→ agent executes
→ result
→ evaluate
```

---

# 194. Specialist agent contract

Especialistas devem receber:

```text
TaskPackage
```

e retornar:

```text
ResultPackage
```

Isso padroniza integração.

---

# 195. Reviewer agent contract

Um reviewer também recebe:

```text
TaskPackage
```

contendo:

```text
artifact
criteria
context
```

e retorna:

```text
Evaluation / ResultPackage
```

---

# 196. Context limits

O Design deve permitir definir:

```text
ContextBudget
```

por Work Unit ou configuração.

Isso permite que Resource Selection considere custo e capacidade.

---

# 197. Model capability abstraction

Modelos podem possuir:

```text
reasoning
coding
long-context
structured-output
vision
tool-use
```

como capacidades declaradas.

A seleção depende do requisito.

---

# 198. Tool capability abstraction

Ferramentas também podem ser descritas por capacidades.

Exemplo:

```text
filesystem.read
filesystem.write
git.commit
web.search
database.query
```

Resource Selection pode avaliar necessidade.

---

# 199. MCP boundary

MCP deve ser tratado como mecanismo de infraestrutura/integração.

O domínio conhece:

```text
ToolCapability
```

e não o protocolo específico.

---

# 200. Hook boundary

Hooks são mecanismos de runtime.

Podem apoiar:

- auditoria;
- observabilidade;
- automações;
- políticas.

Mas não devem concentrar regras de domínio essenciais.

---

# 201. Event hooks versus domain events

Distinguir:

```text
Domain Event
```

de:

```text
Runtime Hook
```

O primeiro pertence ao significado do sistema.

O segundo pertence à infraestrutura de execução.

---

# 202. Memory Adapter

Memória externa deve ser tratada como adapter:

```text
MemoryProvider
```

O domínio conhece a necessidade de recuperar contexto; não o mecanismo específico.

---

# 203. File Knowledge Adapter

Arquivos Markdown podem ser fonte de conhecimento.

Exemplo:

```text
MarkdownKnowledgeRepository
```

mas o Domain não deve conhecer:

```text
/mnt/project/skills/foo/SKILL.md
```

---

# 204. Knowledge indexing

O design deve permitir futuramente:

```text
document
→ chunk/index
→ retrieval
→ source reference
```

mas não exige vector database nesta fase.

---

# 205. Knowledge hierarchy

Uma possibilidade:

```text
Global
Project
Agent
Skill
Task
Execution
```

Quanto mais específico o nível, maior a prioridade contextual.

---

# 206. Context precedence

Conceitualmente:

```text
protected policy
>
project constraints
>
validated project state
>
task context
>
skill guidance
>
agent preference
```

A ordem concreta pode ser refinada.

---

# 207. Conflict resolution

Quando duas fontes conflitam:

```text
identify
→ classify
→ compare authority
→ compare evidence
→ escalate if unresolved
```

Não fazer merge silencioso.

---

# 208. Design of policies

Políticas devem ser avaliadas antes da execução e novamente quando o contexto mudar.

---

# 209. Design of budgets

Budget pode incluir:

```text
per task
per project
per agent
per model
per time window
```

A unidade física do orçamento será definida posteriormente.

---

# 210. Cost accounting

Toda execução relevante deve possuir referência de custo quando disponível.

```text
ExecutionCost
├── model
├── tools
├── runtime
├── coordination
└── total
```

---

# 211. Latency accounting

```text
ExecutionLatency
├── queue
├── model
├── tools
├── coordination
└── total
```

---

# 212. Quality accounting

Qualidade deve relacionar:

```text
Task
+
Configuration
+
Evaluation
+
Outcome
```

---

# 213. Telemetry contract

```text
TelemetryEvent
├── event
├── timestamp
├── project
├── workUnit
├── execution
├── agent
├── skill
├── model
├── cost
└── metadata
```

---

# 214. Learning boundaries

Learning should read telemetry but not mutate policies directly.

```text
Telemetry
→ LearningCandidate
→ Validation
→ Promotion
```

---

# 215. Promotion targets

Aprendizado validado pode virar:

```text
Knowledge
Rule candidate
Skill update
Prompt revision
Agent configuration
Model selection heuristic
```

Cada mudança deve passar pelo mecanismo correspondente.

---

# 216. Architecture and legacy knowledge

O projeto legado é menos relevante como **estrutura física de código** nesta fase.

Ele é, porém, muito relevante como fonte de princípios:

```text
responsibility separation
state
dependency
impact
validation
traceability
baseline
evolution
```

O novo Design traduz esses princípios para um sistema de software orientado a agentes.

---

# 217. Relation to DDD

DDD será usado como ferramenta de modelagem e linguagem do domínio do Orchestrator, não como obrigação de transformar tudo em entidade/agregado.

O modelo deve existir onde houver regra e identidade significativas.

---

# 218. Domain language

Termos fundamentais do projeto tornam-se linguagem ubíqua:

```text
Project
Work Unit
Agent
Skill
Model
Resource Configuration
Plan
Dependency
Decision
Evaluation
Delegation
Result
Learning Candidate
Policy
Baseline
```

Esses nomes devem permanecer consistentes no código e documentação.

---

# 219. Anti-pattern — generic manager classes

Evitar:

```text
Manager
Helper
Util
Processor
Handler
Service
```

quando o nome não indicar claramente a responsabilidade.

---

# 220. Naming

Preferir:

```text
ResourceSelector
WorkPlanner
ResultEvaluator
DelegationCoordinator
ImpactAssessment
ProjectStateRepository
```

em vez de:

```text
Manager
Helper
Utils
CommonService
```

---

# 221. Error semantics

Erros devem ser semanticamente claros.

```text
AgentUnavailable
```

é melhor que:

```text
RuntimeException
```

quando o primeiro possui significado útil para recuperação.

---

# 222. Boundary validation

Entradas externas devem ser validadas na fronteira.

Não depender de entidades para aceitar qualquer objeto inválido.

---

# 223. Domain invariants

Após a entrada passar pela fronteira, o domínio deve proteger suas próprias invariantes.

---

# 224. Mapping errors

Falhas de tradução entre runtime e domínio devem ser tratadas no adapter.

Não deixar exceções externas vazarem para o core.

---

# 225. External API volatility

Qualquer SDK que possa mudar deve estar encapsulado.

Isso se aplica principalmente a:

```text
OpenClaw
Hermes
LLM providers
MCP
cloud APIs
```

---

# 226. Architecture enforcement

A arquitetura deve ser reforçada por:

- import rules;
- static analysis;
- architecture tests;
- code review;
- package boundaries.

Não confiar apenas em convenção verbal.

---

# 227. Code Review Criteria

Revisões de código futuras devem perguntar:

```text
A responsabilidade é clara?
Há acoplamento indevido?
O domínio conhece infraestrutura?
Há duplicação?
Há estados inválidos possíveis?
Existe uma abstração artificial?
O design é testável?
```

---

# 228. Design Review Criteria

O design deve ser revisado antes de implementação quando:

- houver novo agregado;
- nova porta;
- novo adapter;
- mudança de estado;
- mudança de contrato;
- nova integração externa.

---

# 229. Implementation Readiness

O design estará pronto para implementação quando for possível responder:

```text
Onde mora cada regra?
Quem chama quem?
Quem possui cada estado?
Qual contrato existe?
Como persistir?
Como testar?
Como trocar runtime?
Como tratar falhas?
Como observar?
```

---

# 230. Architecture Decision — initial deployment style

**Decisão:** começar como **aplicação modular única**, não como conjunto de microserviços.

Justificativa:

- menor complexidade;
- melhor velocidade de desenvolvimento;
- menor overhead de rede;
- transações mais simples;
- fronteiras internas suficientes;
- possibilidade de futura distribuição.

As camadas são lógicas e não implicam distribuição física; a documentação da Microsoft reforça essa distinção. citeturn483369search4

---

# 231. Architecture Decision — runtime

**Decisão:** OpenClaw é o primeiro runtime alvo.

**Regra:** essa escolha não deve contaminar o Domain/Application Core.

---

# 232. Architecture Decision — Clean Architecture

**Decisão:** aplicar Clean Architecture + DDD + Ports-and-Adapters como fundamentos de design.

Justificativa:

- núcleo independente;
- infraestrutura substituível;
- testes mais simples;
- menor acoplamento;
- melhor manutenção;
- alinhamento com a natureza modular do Orchestrator.

Microsoft descreve Clean Architecture como uma organização em que lógica de negócio e modelo de aplicação ficam no centro, enquanto infraestrutura e interfaces externas dependem desse núcleo. citeturn483369search0turn483369search1

---

# 233. Architecture Decision — conhecimento independente

**Decisão:** conhecimento permanecerá separado do código e poderá ser transformado em Skills, prompts, referências ou contexto conforme o runtime.

---

# 234. Architecture Decision — agent count

**Decisão:** nenhum número fixo de agentes será incorporado à arquitetura.

A composição será dinâmica e contextual.

---

# 235. Design Constraints

O Design deve respeitar:

```text
clean architecture
single responsibility
low coupling
high cohesion
dependency inversion
runtime abstraction
testability
observability
security
```

---

# 236. Design Risks

## D-001 — Overengineering

Risco de criar abstrações excessivas antes de existir necessidade.

Mitigação:

```text
design enough
→ implement
→ learn
→ refine
```

## D-002 — Abstração artificial do runtime

Risco de criar um adapter genérico demais e perder capacidades reais do runtime.

Mitigação:

```text
abstração estável
+
mapeamento explícito de capacidades específicas
```

## D-003 — Domain demasiado genérico

Risco de criar modelos vagos para "qualquer agente".

Mitigação:

```text
modelar primeiro as necessidades reais do Orchestrator.
```

## D-004 — Application logic becoming domain logic

Mitigação:

```text
regras invariantes → Domain
coordenação de caso de uso → Application
```

## D-005 — Prompt bypassing software rules

Mitigação:

```text
policy enforcement → software
prompt guidance → model behavior
```

---

# 237. Traceability

Exemplo completo:

```text
RF-ORC-027
Delegar trabalho
    ↓
UC-ORC-006
Delegar trabalho
    ↓
DelegateWork
    ↓
TaskPackage
    ↓
AgentRuntime
    ↓
OpenClawAdapter
    ↓
Integration Test
```

Outro:

```text
RF-ORC-031
Avaliar resultado
    ↓
UC-ORC-007
Evaluate Result
    ↓
EvaluationUseCase
    ↓
ResultEvaluator
    ↓
EvaluationRepository
    ↓
Evaluation Tests
```

---

# 238. Requirements Coverage

As dez capacidades possuem componentes e casos de uso correspondentes.

```text
Project Awareness
→ ProjectStateManager
→ ProjectAwareness
→ Initialize / Resume

Project Management
→ Planning / Work
→ PlanWork

Ecosystem Awareness
→ EcosystemRegistry
→ Catalogs

Structural Analysis
→ StructuralAnalysis
→ StructureProject

Agent & Skill Analysis
→ CapabilityResolver
→ Agent/Skill catalogs

Resource / Model Selection
→ ResourceSelector
→ ModelCatalog

Delegation & Coordination
→ DelegationCoordinator
→ RuntimeAdapter

Result Evaluation
→ ResultEvaluator
→ Evaluation

Replanning
→ ReplanningEngine
→ ReplanProject

Continuity & Learning
→ Continuity/Learning
→ RecordLearning
```

---

# 239. Implementation Sequence

Depois deste Design:

```text
1. repository bootstrap
2. domain skeleton
3. domain tests
4. application use cases
5. in-memory adapters
6. architecture tests
7. persistence
8. OpenClaw adapter
9. real model/runtime integration
10. specialist agents
11. complete integration
```

---

# 240. Code Quality Gate

Antes de considerar qualquer componente implementado:

```text
responsibility clear
+
dependencies correct
+
tests adequate
+
errors handled
+
naming clear
+
no accidental runtime coupling
+
documented boundary
```

---

# 241. Definition of Done for Design

O Design estará concluído quando:

```text
domain model defined
+
application use cases defined
+
ports defined
+
adapters identified
+
state transitions defined
+
contracts defined
+
persistence boundary defined
+
runtime boundary defined
+
testing strategy defined
+
package boundaries defined
+
architecture enforcement defined
+
traceability established
```

---


---

# 246. Consolidação da Revisão Arquitetural v0.2

Esta versão consolida formalmente as decisões registradas em `ORCHESTRATOR-DESIGN-REVIEW.md`.

A revisão não altera a arquitetura macro. Ela refina a forma dos módulos, interfaces e seams para reduzir abstrações artificiais e aumentar depth, leverage e locality.

## 246.1 Seam Discipline

Ports e adapters não devem ser criados por antecipação.

A criação de um seam deve ser justificada por pelo menos uma necessidade real de:

```text
substituição
+
isolamento
+
dependência externa
+
testabilidade relevante
+
variação real
```

`AgentRuntime` permanece como seam real porque o Orchestrator deve permanecer independente do runtime e pode operar com OpenClaw inicialmente e Hermes/outros runtimes posteriormente.

Os seguintes elementos devem permanecer internos ao módulo enquanto não houver necessidade concreta de exposição como seam:

```text
AgentCatalog
SkillCatalog
ModelCatalog
Clock
IdGenerator
```

## 246.2 Deep Module Rule

Pipelines internos não devem ser tratados automaticamente como módulos públicos.

A decomposição:

```text
CapabilityResolver
AgentCandidates
SkillCandidates
ModelCandidates
PolicyFilter
MultiObjectiveEvaluator
```

pode existir como implementação interna de um módulo profundo de seleção.

O chamador deve depender de uma interface pequena, e não reconstruir o pipeline interno.

## 246.3 Resource Selection

A forma preferencial é:

```text
Work Unit
→ ResourceSelection
→ ResourceConfiguration / SelectionDecision
```

A composição interna pode evoluir sem alterar a interface externa enquanto o seam permanecer estável.

## 246.4 Result Evaluation

A avaliação deve manter sua pipeline interna privada.

Forma conceitual:

```text
EvaluationRequest
→ Evaluation
```

A interface pública não deve expor obrigatoriamente:

```text
CriteriaResolver
EvidenceResolver
Evaluator
StateUpdate
```

Esses elementos podem permanecer internos à implementação do módulo.

## 246.5 Replanning

A mesma regra se aplica ao replanning.

A forma conceitual preferencial é:

```text
replan(projectState, trigger)
→ PlanRevision
```

A análise de impacto, identificação do conjunto afetado, atualização de dependências e validação do plano devem permanecer localizadas dentro do módulo, salvo necessidade real de exposição.

## 246.6 Delegation

A delegação mantém um seam real em:

```text
Application
→ AgentRuntime
→ Runtime Adapter
```

O módulo de delegação deve esconder:

```text
handoff
lifecycle
execution correlation
result normalization
technical failure handling
```

O contrato interno não deve copiar a API de OpenClaw, Hermes ou outro runtime.

## 246.7 Knowledge / Context

Knowledge e Context continuam sendo conceitos distintos.

O contexto necessário para uma Work Unit deve ser montado por uma unidade de aplicação e pode consultar fontes externas por seams somente quando houver dependência real.

Backends específicos de recuperação não devem virar abstrações públicas antecipadamente.

## 246.8 Skill Architecture

O `SkillProfile` existente fornece a base conceitual.

Características adicionais como:

```text
invocationPolicy
skill composition
provenance
runtime-specific metadata
```

pertencem à futura Skill Architecture.

Não implementar essas capacidades como parte obrigatória do núcleo do Orchestrator nesta fase sem uma Work Unit que as exija.

## 246.9 Interface as Test Surface

Testes comportamentais devem atravessar preferencialmente a interface externa do módulo.

Quando um módulo interno for aprofundado e seus antigos testes se tornarem redundantes:

```text
shallow modules
→ deep module
→ interface tests
→ remove redundant tests
```

## 246.10 Design It Twice

As decisões de interface dos módulos críticos foram comparadas antes da implementação:

```text
Resource Selection
Delegation
Result Evaluation
Replanning
```

O critério de comparação é:

```text
depth
+
leverage
+
locality
+
seam placement
```

Essas decisões orientam a implementação, mas não impedem refinamentos durante uma Work Unit quando novas evidências surgirem.

## 246.11 Technology Neutrality

O Design não fixa linguagem de programação, framework, banco ou stack de implementação.

A escolha tecnológica deve ocorrer quando uma Work Unit concreta exigir uma decisão, considerando:

```text
requisitos
+
características da implementação
+
agente
+
Skill
+
runtime
+
ferramentas
+
restrições do ecossistema
```

O Orchestrator deve permanecer capaz de coordenar Work Units implementadas em diferentes linguagens e stacks quando isso for adequado.

## 246.12 Design Baseline

Com esta consolidação:

```text
Requirements
→ Architecture
→ Design v0.2
→ Implementation Plan
```

passa a ser a cadeia normativa de implementação.

O Design v0.2 é a baseline arquitetural para o próximo gate.

---

# 247. Definition of Done — Design v0.2

O Design v0.2 está pronto para o Implementation Plan quando:

```text
domain model defined
+
application use cases defined
+
runtime boundary defined
+
necessary seams justified
+
adapters identified
+
state transitions defined
+
contracts sufficiently defined
+
testing strategy defined
+
package/module responsibilities sufficiently clear
+
architecture enforcement defined
+
traceability established
+
technology remains intentionally unconstrained
```

---

# 248. Próximo Gate

O próximo gate é:

```text
Design v0.2
    ↓
Implementation Plan
    ↓
Work Units
    ↓
Dependency ordering
    ↓
Acceptance criteria
    ↓
Verification
    ↓
Implementation
```

O `ORCHESTRATOR-IMPLEMENTATION-PLAN.md` v0.2 já materializa essa sequência em Work Units.

A próxima unidade operacional é:

```text
WU-001 — Bootstrap agnóstico de linguagem
```

A implementação não deve fixar uma linguagem como requisito do Orchestrator.


# 242. Specification-Driven Development

O desenvolvimento deste sistema seguirá **Specification-Driven Development (SDD)** como disciplina transversal.

A especificação será tratada como o artefato primário de intenção e comportamento do sistema, enquanto design, plano de implementação, código, testes e evidências deverão manter alinhamento rastreável com ela.

A disciplina é aprofundada e formalizada em:

`ORCHESTRATOR-SPEC-DRIVEN-DEVELOPMENT.md`

Esta seção registra as decisões arquiteturais essenciais:

```text
Specification
      ↓
Architecture
      ↓
Design
      ↓
Implementation Plan
      ↓
Code
      ↓
Verification / Evals
      ↓
Evidence
```

### Regra SD-001 — Especificação como fonte de verdade

Quando houver conflito entre uma implementação e a especificação válida, a implementação não deve prevalecer silenciosamente.

O conflito deve gerar:

```text
conflict
→ impact analysis
→ specification/design update
→ revalidation
→ implementation update
```

### Regra SD-002 — Código é expressão da especificação

Código não deve ser tratado como autoridade superior simplesmente por existir.

### Regra SD-003 — Mudança começa na especificação

Uma mudança de comportamento deve iniciar pela alteração ou criação da especificação correspondente.

### Regra SD-004 — Design deve ser derivado

A arquitetura e o design devem responder às necessidades expressas na especificação, sem introduzir comportamento funcional arbitrário.

### Regra SD-005 — Verificação contra intenção

Testes e Evals devem produzir evidência de que a implementação satisfaz a especificação aplicável.

### Regra SD-006 — Rastreamento bidirecional

Quando proporcional ao impacto:

```text
Specification
↔ Design
↔ Implementation
↔ Verification
↔ Evidence
```

### Regra SD-007 — Nenhum requisito silencioso

Se a implementação exigir comportamento não previsto:

```text
new behavior
→ specification gap
→ specification decision
→ update
```

e não:

```text
new behavior
→ code only
```

### Regra SD-008 — Prompt não substitui especificação

Prompt é instrumento de orientação da execução do agente.

Especificação é artefato persistente, revisável e rastreável do projeto.

### Regra SD-009 — Policy não depende apenas do prompt

Regras críticas de segurança, autorização e governança devem ser aplicadas pela arquitetura de software, e não somente por instruções ao modelo.

### Regra SD-010 — Feedback altera o nível apropriado

Uma descoberta pode exigir alteração em:

```text
requirement
architecture
design
implementation
prompt
Skill
```

A mudança deve atingir o menor nível suficiente que preserve a coerência global.

# 243. Estado

**Status:** Design conceitual detalhado concluído.

O documento fornece uma base suficiente para iniciar a implementação do núcleo sem transformar detalhes externos em dependências internas.

---

# 244. Próxima fase

A próxima fase será:

## **Implementação do Núcleo**

A implementação inicial deverá começar pelo **Domain**, seguida pela camada de **Application**, com adapters em memória e testes, antes de incorporar a integração real com OpenClaw.

---

# 245. Fechamento

O design final estabelece:

```text
                 INTERFACE
                     │
                 APPLICATION
                     │
                DOMAIN / CORE
                     │
              PORTS / CONTRACTS
                     │
              INFRASTRUCTURE
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
     OpenClaw      Hermes       Others
```

e, paralelamente:

```text
             DOMAIN KNOWLEDGE
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
      Orchestrator       Specialists
          │                   │
          └─────────┬─────────┘
                    ▼
                 Runtime
```

A intenção é que a arquitetura seja limpa **não porque possui determinada quantidade de camadas ou pastas**, mas porque suas responsabilidades, dependências e fronteiras são claras e verificáveis.
