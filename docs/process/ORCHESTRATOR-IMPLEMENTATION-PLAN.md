# ORCHESTRATOR — IMPLEMENTATION PLAN

**Projeto:** Adaptive AI Orchestrator
**Documento:** Plano de Implementação
**Versão:** v0.2
**Status:** Planejamento inicial — pré-implementação

---

# 1. Finalidade

Este documento transforma o `ORCHESTRATOR-SYSTEM-DESIGN.md` em uma sequência de **Work Units de implementação**, respeitando:

```text
Specification
→ Architecture
→ Design
→ Implementation Plan
→ Code
→ Verification / Evals
→ Evidence
```

Essa sequência é a adotada pelo SDD do projeto.

O objetivo não é construir toda a infraestrutura antecipadamente.

O objetivo é produzir o Orchestrator por **vertical slices verificáveis**, começando pelo núcleo e adicionando complexidade somente quando existir necessidade comprovada.

---

# 2. Escopo da implementação atual

O foco desta fase é:

> **concluir o Adaptive AI Orchestrator funcional.**

Não faz parte do escopo imediato implementar todas as futuras Skills especializadas.

O conhecimento necessário para futuras Skills permanece documentado e disponível para evolução posterior.

A implementação atual deve provar que o Orchestrator consegue:

```text
compreender o estado do projeto
→ estruturar trabalho
→ criar Work Units
→ controlar dependências
→ identificar capacidades / Skills / agentes
→ selecionar recursos
→ delegar
→ receber resultados
→ avaliar
→ replanejar
→ preservar continuidade
→ produzir Learning Candidates
```

---

# 3. Princípios de implementação

## 3.1 Agnosticismo tecnológico

A arquitetura do Orchestrator não fixa uma linguagem de programação, framework ou stack de implementação como requisito do sistema.

A tecnologia deve ser escolhida somente quando uma Work Unit concreta exigir essa decisão.

A seleção pode considerar:

```text
requisitos da Work Unit
+
características da implementação
+
capacidade do agente executor
+
Skills disponíveis
+
runtime
+
ferramentas
+
restrições do ecossistema
```

O Orchestrator deve permanecer capaz de coordenar trabalho produzido em diferentes linguagens e stacks quando isso for apropriado.

A linguagem da implementação de uma Work Unit é uma decisão local da implementação, não uma característica fixa do domínio do Orchestrator.

## 3.2 Núcleo antes de infraestrutura

Implementar inicialmente:

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
→ Model / Provider integration
```

Essa estratégia está explicitamente prevista no System Design.

## 3.3 Modular monolith

O Orchestrator será inicialmente uma aplicação modular única.

Não introduzir microserviços sem necessidade real.

## 3.4 Deep Modules

Preferir módulos profundos, coesos e com interfaces pequenas.

Não criar interfaces, ports ou adapters apenas por antecipação.

## 3.5 Runtime independence

O caso de uso de delegação não deve conhecer detalhes do OpenClaw.

A integração deve ocorrer por adapter.

O primeiro runtime real será OpenClaw.

Hermes e outros runtimes permanecem como possibilidade arquitetural futura.

## 3.6 Specification-driven

Nenhum comportamento relevante deve ser inventado silenciosamente durante a implementação.

Quando surgir uma lacuna normativa:

```text
descoberta
→ análise
→ atualização da especificação apropriada
→ revalidação
→ implementação
```

---

# 4. Ordem geral

```text
GATE 0
Design / Baseline
        ↓
SLICE 1
Project + Work Unit + State
        ↓
SLICE 2
Plan + Dependency + Ready/Blocked
        ↓
SLICE 3
Agent/Skill Analysis + Resource Selection
        ↓
SLICE 4
Delegation + OpenClaw Adapter
        ↓
SLICE 5
Result + Evaluation + Replanning
        ↓
SLICE 6
Continuity + Telemetry + Learning Candidate
        ↓
SLICE 7
Integration + Hardening + Real-Use Readiness
```

---

# 5. GATE 0 — Consolidar Design

## WU-000 — Confirm Design Baseline

**Objetivo**

Confirmar que o arquivo canônico de Design contém efetivamente as decisões da revisão arquitetural mais recente.

**Entrada**

```text
ORCHESTRATOR-SYSTEM-DESIGN.md
ORCHESTRATOR-DESIGN-REVIEW.md
ORCHESTRATOR-SYSTEM-ARCHITECTURE.md
ORCHESTRATOR-REQUIREMENTS.md
```

**Atividades**

- comparar Design canônico com a revisão;
- resolver eventual divergência de versão;
- confirmar domínio, casos de uso, estados, contratos e boundaries;
- registrar a baseline válida.

**Critério de aceitação**

O Design canônico representa a versão efetivamente aprovada e não possui conflito documental relevante com a Review.

**Saída**

```text
Design baseline
```

---

# 6. SLICE 1 — Núcleo do projeto

## WU-001 — Bootstrap agnóstico de linguagem

**Objetivo**

Criar a estrutura mínima do projeto de implementação sem fixar uma linguagem, framework ou runtime de aplicação antes que uma Work Unit concreta justifique essa decisão.

**Critérios**

- estrutura inicial compatível com a arquitetura aprovada;
- separação lógica entre Domain, Application, Infrastructure e Interface/Delivery;
- mecanismo de testes definido de acordo com a tecnologia escolhida para a primeira Work Unit;
- dependências iniciais mínimas;
- nenhuma dependência externa desnecessária no domínio;
- convenções de desenvolvimento suficientes para iniciar a primeira implementação.

**Importante**

Esta Work Unit prepara o terreno de implementação. Ela não deve criar abstrações ou componentes específicos apenas para preencher uma estrutura prevista.

A decisão tecnológica concreta deve ser registrada quando necessária para a implementação.

---

## WU-002 — Project Domain

Implementar:

```text
Project
ProjectState
ProjectId
```

**Critérios**

- identidade;
- objetivos;
- requisitos;
- restrições;
- decisões;
- baseline;
- Work Units;
- estado;
- invariantes fundamentais.

---

## WU-003 — WorkUnit Domain

Implementar:

```text
WorkUnit
WorkUnitId
WorkUnitState
```

**Critérios**

Uma Work Unit executável deve possuir, conforme aplicável:

```text
identity
objective
scope
inputs
outputs
dependencies
preconditions
requiredCapabilities
criteria
priority
criticality
state
```

Uma Work Unit bloqueada não pode ser tratada como pronta.

---

## WU-004 — Project State Repository In-Memory

Criar o primeiro adapter em memória para preservar o estado.

**Critérios**

- salvar;
- recuperar;
- substituir estado;
- testes determinísticos;
- domínio independente do mecanismo de armazenamento.

---

## WU-005 — Initialize Project + Create Work Unit

Primeiro vertical slice executável:

```text
Initialize Project
→ Create Work Unit
→ Store State
→ Read State
```

**Critério de saída do Slice 1**

O fluxo deve funcionar sem OpenClaw, banco externo ou provider externo.

Deve possuir testes de comportamento através das interfaces relevantes.

---

# 7. SLICE 2 — Planejamento e dependências

## WU-006 — Dependency Domain

Implementar:

```text
Dependency
DependencyType
DependencyStatus
```

**Critérios**

- dependência obrigatória bloqueia quando pré-condição não é satisfeita;
- dependências independentes não se bloqueiam;
- ciclos inválidos devem ser detectáveis.

---

## WU-007 — Plan Domain

Implementar:

```text
Plan
PlanVersion
Priority
```

com:

```text
workUnits
dependencies
priorities
parallelGroups
gates
status
baseline
```

---

## WU-008 — Plan Work Use Case

Fluxo:

```text
load baseline
→ identify Work Units
→ evaluate dependencies
→ determine readiness
→ prioritize
→ produce Plan
```

---

## WU-009 — Ready / Blocked Evaluation

Formalizar o mecanismo que determina:

```text
READY
ou
BLOCKED
```

**Critérios**

A decisão deve ser derivada das dependências e pré-condições, não de texto livre.

---

## WU-010 — Second Vertical Slice

Executar:

```text
Plan Work
+
Dependency
+
Ready / Blocked
```

**Critério de saída**

O Orchestrator consegue produzir um plano mínimo e determinar quais Work Units podem iniciar.

---

# 8. SLICE 3 — Conhecimento do ecossistema e seleção

## WU-011 — Agent Profile

Implementar:

```text
AgentProfile
AgentId
```

Incluindo, conforme necessário:

```text
role
responsibilities
capabilities
skills
tools
eligibleModels
contextRequirements
permissions
runtime
evidence
```

---

## WU-012 — Skill Profile

Implementar a representação necessária para o Orchestrator raciocinar sobre Skills.

O modelo deve permanecer compatível com futura materialização em:

```text
skills/
```

A implementação não deve exigir que todas as Skills futuras já existam.

---

## WU-013 — Model Profile

Implementar:

```text
ModelProfile
ModelId
```

Incluindo informações necessárias para seleção, como:

```text
capabilities
context
cost
latency
availability
restrictions
evidence
```

---

## WU-014 — In-Memory Catalogs

Criar adapters mínimos para:

```text
AgentCatalog
SkillCatalog
ModelCatalog
```

Somente operações necessárias aos casos de uso devem existir.

Evitar interfaces especulativas.

---

## WU-015 — Agent & Skill Analysis

Implementar o fluxo:

```text
Work Unit
→ required capabilities
→ required Skills
→ eligible agents
→ compatibility
→ confidence
→ evidence
```

A análise não escolhe definitivamente o modelo.

---

## WU-016 — Resource Configuration

Implementar:

```text
ResourceConfiguration
```

com:

```text
agent
skills
model
provider
tools
runtime
policy constraints
```

---

## WU-017 — Resource Selection

Implementar:

```text
SelectResource
```

Fluxo:

```text
load Work Unit
→ identify capabilities
→ query catalogs
→ apply policies
→ evaluate alternatives
→ produce ResourceConfiguration
```

---

## WU-018 — Third Vertical Slice

Executar:

```text
Agent & Skill Analysis
+
Resource Selection
```

com catálogos em memória.

**Critério de saída**

O Orchestrator consegue escolher uma configuração candidata sem depender de OpenClaw.

---

# 9. SLICE 4 — Delegação e primeiro runtime real

## WU-019 — Task Package

Implementar:

```text
TaskPackage
```

Incluindo, conforme aplicável:

```text
taskId
workUnitId
objective
scope
context
inputs
artifacts
decisions
dependencies
constraints
configuration
expectedOutput
acceptanceCriteria
```

O Task Package transmite contexto e contrato; não deve conter regras internas do agente executor.

---

## WU-020 — Agent Runtime Port

Definir o seam de execução.

Contrato mínimo orientado ao caso de uso, evitando expor detalhes do runtime.

---

## WU-021 — OpenClaw Adapter

Implementar o primeiro adapter real:

```text
OpenClawAdapter
```

Responsabilidades:

- traduzir o contrato interno para o runtime;
- executar;
- acompanhar;
- recuperar o resultado;
- converter detalhes externos em conceitos internos.

O domínio não deve conhecer objetos específicos do OpenClaw.

---

## WU-022 — Delegate Work Use Case

Fluxo:

```text
load Work Unit
→ load configuration
→ validate preconditions
→ assemble TaskPackage
→ call AgentRuntime
→ persist execution state
→ monitor
→ retrieve ResultPackage
```

---

## WU-023 — Fourth Vertical Slice

Executar:

```text
Delegation
+
OpenClaw Adapter
```

**Critério de saída**

Uma Work Unit pode ser enviada ao runtime real escolhido e o resultado pode retornar ao sistema em formato interno.

---

# 10. SLICE 5 — Avaliação e adaptação

## WU-024 — Result Package

Implementar representação estruturada do retorno do agente.

---

## WU-025 — Evaluation Domain

Implementar:

```text
Evaluation
Verdict
Confidence
Evidence
```

com estados adequados, por exemplo:

```text
ACCEPTED
ACCEPTED_WITH_CONDITIONS
RETURNED
BLOCKED
REJECTED
```

---

## WU-026 — Evaluate Result Use Case

Fluxo:

```text
load ResultPackage
→ load criteria
→ load project state
→ evaluate
→ persist Evaluation
→ update WorkUnit state
→ trigger Replanning when necessary
```

---

## WU-027 — Replanning

Implementar:

```text
ReplanProject
```

Fluxo:

```text
event/result/change
→ classify impact
→ identify affected Work Units
→ preserve valid work
→ update dependencies/states
→ adjust plan
→ reassess resources
→ validate
→ persist new version
```

---

## WU-028 — Fifth Vertical Slice

Executar:

```text
Result
+
Evaluation
+
Replanning
```

**Critério de saída**

O Orchestrator consegue receber um resultado, avaliá-lo e adaptar o plano sem reinicializar o projeto inteiro.

---

# 11. SLICE 6 — Continuidade, observabilidade e aprendizagem

## WU-029 — Continuity Model

Persistir:

```text
state
context
decisions
baseline
pending work
dependencies
accepted results
required history
```

---

## WU-030 — Evidence / Telemetry

Registrar evidências necessárias para:

```text
quality
time
cost
failures
interventions
runtime
agent
skill
model
work type
```

O objetivo é produzir dados úteis, não armazenar tudo indiscriminadamente.

---

## WU-031 — Learning Candidate

Implementar um mecanismo explícito para registrar:

```text
pattern
observation
evidence
potential improvement
confidence
provenance
```

Um Learning Candidate não vira automaticamente regra do sistema.

---

## WU-032 — Sixth Vertical Slice

Executar:

```text
Continuity
+
Telemetry
+
Learning Candidate
```

**Critério de saída**

Uma execução deixa evidência suficiente para continuidade e para futura avaliação de desempenho, sem transformar automaticamente experiência em regra.

---

# 12. SLICE 7 — Integração e endurecimento

## WU-033 — End-to-End Orchestrator Flow

Executar o fluxo:

```text
Project
→ Work Unit
→ Plan
→ Agent/Skill Analysis
→ Resource Selection
→ TaskPackage
→ Delegation
→ ResultPackage
→ Evaluation
→ Replanning
→ Continuity
```

---

## WU-034 — Architecture Verification

Verificar:

```text
Domain does not depend on infrastructure
Application does not depend on runtime details
OpenClaw is behind adapter
providers are isolated
ports are justified
shared modules are cohesive
```

---

## WU-035 — Traceability Verification

Verificar:

```text
Requirement
→ Use Case
→ Design
→ Work Unit
→ Code
→ Test/Eval
→ Evidence
```

quando proporcional ao impacto.

---

## WU-036 — Failure and Recovery Paths

Validar, conforme aplicável:

```text
blocked Work Unit
runtime failure
agent failure
invalid result
returned result
replanning
retry
fallback
resource replacement
```

---

## WU-037 — Practical Operational Validation

Executar uma utilização real controlada.

Não é necessário tentar simular todas as situações possíveis.

Avaliar:

```text
qualidade
correção
eficiência
custo
contexto
retrabalho
necessidade de intervenção
```

Registrar evidências para evolução posterior.

---

# 13. Definição de Done do Orchestrator

O Orchestrator pode ser considerado pronto para uso controlado quando:

```text
✅ Project state funciona
✅ Work Units funcionam
✅ Dependencies funcionam
✅ Plan / Ready / Blocked funcionam
✅ Agent & Skill Analysis funciona
✅ Resource Selection funciona
✅ TaskPackage funciona
✅ Delegation funciona
✅ OpenClaw Adapter funciona
✅ ResultPackage funciona
✅ Evaluation funciona
✅ Replanning funciona
✅ Continuity funciona
✅ Evidence / Telemetry funciona
✅ Learning Candidate funciona
✅ fluxo end-to-end funciona
✅ testes essenciais existem
✅ Evals essenciais existem
✅ arquitetura permanece desacoplada
✅ rastreabilidade essencial existe
✅ uso real controlado produziu evidência
```

---

# 14. O que fica deliberadamente fora

Para evitar que o projeto volte a crescer durante sua própria implementação, fica fora desta fase:

```text
❌ desenvolver todas as futuras Skills
❌ implementar Hermes Adapter sem necessidade
❌ implementar múltiplos providers imediatamente
❌ criar microserviços
❌ criar todos os catálogos externos antes de necessidade
❌ construir uma UI complexa antes do núcleo
❌ automatizar todo tipo de avaliação possível
❌ construir mecanismos de aprendizado avançado antes de existir evidência real
```

Esses itens podem ser considerados posteriormente.

---

# 15. Estratégia de paralelismo

A execução das Work Units deve seguir dependências.

Exemplo:

```text
WU-001
   ↓
WU-002
   ↓
WU-003
   ↓
WU-004
```

Somente unidades realmente independentes podem ser paralelizadas.

O objetivo é reduzir:

```text
context switching
coordenação
custo
retrabalho
```

---

# 16. Estratégia de testes

A implementação deve priorizar:

```text
Domain Tests
Application Tests
Architecture Tests
Integration Tests
System Tests
Evals
```

Os testes devem atravessar as interfaces relevantes.

Não criar testes acoplados desnecessariamente a detalhes internos.

---

# 17. Estratégia de Evals

Evals devem ser utilizadas especialmente para capacidades agentic:

```text
Structural Analysis
Agent / Skill Analysis
Resource Selection
Delegation
Result Evaluation
Replanning
```

Os Evals devem utilizar critérios observáveis e evidências registráveis.

---

# 18. Regra para implementação por agentes

Quando a implementação for delegada a um agente:

```text
Work Unit
→ Task Package
→ Agent + Skill + Model
→ execução
→ Result Package
→ Evaluation
```

O Orchestrator do próprio projeto deve aplicar essa lógica ao seu desenvolvimento futuro.

---

# 19. Ordem operacional imediata

A partir deste documento:

```text
1. WU-000 — Confirm Design Baseline
2. WU-001 — Bootstrap
3. WU-002 — Project
4. WU-003 — WorkUnit
5. WU-004 — In-Memory State
6. WU-005 — Primeiro Vertical Slice
```

Somente depois iniciar o Slice 2.

---

# 20. Critério de avanço

Uma Work Unit só avança quando:

```text
implementada
+
testada
+
validada
+
rastreável
```

Quando o resultado revelar uma lacuna arquitetural ou de especificação:

```text
parar
→ analisar
→ atualizar artefato apropriado
→ revalidar
→ continuar
```

---

# 21. Relação com o projeto futuro de Skills

A implementação do Orchestrator deve manter conhecimento suficiente para permitir posteriormente:

```text
skills/
├── orchestrator/
├── architecture/
├── documentation/
├── requirements/
├── testing/
└── ...
```

Mas essas Skills futuras não são Work Units obrigatórias deste plano.

Elas serão uma fase posterior do projeto.

---

# 22. Estado do plano

Este documento representa a primeira consolidação do Implementation Plan.

Próximo passo:

```text
WU-000
→ Confirm Design Baseline
```

Depois:

```text
WU-001
→ Bootstrap do código
```

Não iniciar a implementação antes de concluir o Gate 0.
