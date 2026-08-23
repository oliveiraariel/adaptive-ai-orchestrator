# New Chat Context — Adaptive AI Orchestrator

**Projeto:** Adaptive AI Orchestrator  
**Documento:** Contexto de Retomada em Novo Chat  
**Versão:** 0.2  
**Status:** Atualizado para a fase pré-Implementation Plan

---

# 1. Finalidade

Este documento permite retomar o desenvolvimento do **Adaptive AI Orchestrator** em outro chat, sessão ou contexto sem depender do histórico completo da conversa anterior.

Seu objetivo é fornecer ao agente que assumir o projeto:

- identidade atual do projeto;
- fontes de verdade;
- estado consolidado;
- decisões importantes;
- estrutura documental vigente;
- transição ainda em andamento;
- inconsistências conhecidas;
- ponto exato de retomada;
- próximo gate.

Este documento não substitui os documentos normativos, arquiteturais ou processuais do projeto.

---

# 2. Regra principal de retomada

Ao iniciar um novo chat:

```text
LER
→ COMPREENDER
→ VERIFICAR ESTADO
→ IDENTIFICAR PONTO DE RETOMADA
→ CONTINUAR
```

Não:

```text
novo chat
→ reinventar o projeto
```

O objetivo é **continuidade**, não reinicialização.

---

# 3. Identidade atual do projeto

O projeto atualmente é:

> **Adaptive AI Orchestrator**

Ele evoluiu do conceito anterior de uma única Professional Software Engineering "Super Skill".

O objetivo agora é desenvolver um Orchestrator que compreenda projetos, organize trabalho, selecione recursos, delegue execução, avalie resultados, reprograme o trabalho e preserve conhecimento e continuidade.

A Professional Software Engineering Skill permanece como conhecimento legado de alto valor, não como o objetivo final do sistema.

---

# 4. Fontes de verdade e autoridade

As fontes de verdade devem ser interpretadas conforme o **escopo ao qual pertencem**.

O repositório contém conhecimento legado e o novo projeto do Adaptive AI Orchestrator. Portanto, não deve existir uma única hierarquia normativa para documentos de domínios diferentes.

## 4.1 Projeto legado — Professional Software Engineering Skill

```text
specifications/MASTER-SPECIFICATION.md
```

É a fonte normativa do projeto legado da Professional Software Engineering Skill.

Seu conteúdo pode ser reutilizado como conhecimento pelo novo projeto, mas uma decisão do Orchestrator não deve ser tratada como subordinada ao Master apenas por estar no mesmo repositório.

---

## 4.2 Novo projeto — Adaptive AI Orchestrator

```text
specifications/orchestrator/ORCHESTRATOR-REQUIREMENTS.md
```

É a referência normativa de requisitos do Adaptive AI Orchestrator.

A arquitetura, o design e as demais decisões do Orchestrator devem ser coerentes com seus requisitos aprovados.

Quando uma decisão do projeto legado for reutilizada, ela deve ser analisada e adaptada ao contexto do Orchestrator antes de ser incorporada.

---

## 4.3 Continuidade

```text
docs/process/DEVELOPMENT-CONTINUITY.md
```

É o registro operacional de continuidade.

Para a atualização mais recente, também verificar o arquivo de versão correspondente, quando ainda estiver em fase de consolidação.

---

## 4.4 Arquitetura

```text
docs/architecture/ORCHESTRATOR-SYSTEM-ARCHITECTURE.md
```

Define a arquitetura sistêmica consolidada.

---

## 4.5 Design

```text
docs/architecture/ORCHESTRATOR-SYSTEM-DESIGN.md
```

É o design técnico canônico atual.

Antes de iniciar implementação, verificar se o conteúdo efetivamente incorpora a revisão v0.2 registrada em:

```text
docs/reviews/ORCHESTRATOR-DESIGN-REVIEW.md
```

---

## 4.6 SDD

```text
docs/process/ORCHESTRATOR-SPEC-DRIVEN-DEVELOPMENT.md
```

Define Specification-Driven Development como disciplina transversal.

---

## 4.7 Contexto de domínio

```text
CONTEXT.md
```

Define a linguagem canônica do Adaptive AI Orchestrator.

Não é especificação, arquitetura ou design.

---

## 4.8 Git

```text
docs/process/GIT-WORKFLOW.md
```

Usar quando a tarefa envolver Git/GitHub.

---

## 5. Ordem recomendada de leitura

Em uma retomada de desenvolvimento:

```text
1. CONTEXT.md
2. DEVELOPMENT-CONTINUITY.md
3. MASTER-SPECIFICATION.md
4. ORCHESTRATOR-REQUIREMENTS.md
5. ORCHESTRATOR-SYSTEM-ARCHITECTURE.md
6. ORCHESTRATOR-SYSTEM-DESIGN.md
7. ORCHESTRATOR-DESIGN-REVIEW.md
8. ORCHESTRATOR-SPEC-DRIVEN-DEVELOPMENT.md
```

Não é necessário ler todo o projeto legado ou todos os documentos de capacidade em toda sessão.

Consultar somente os documentos necessários para a tarefa atual.

---

# 6. O que o Orchestrator será

O Adaptive AI Orchestrator deve possuir conhecimento aprofundado sobre:

```text
projeto
+
gestão
+
ecossistema
+
agentes
+
Skills
+
modelos
+
delegação
+
avaliação
+
replanning
+
continuidade
+
aprendizagem
```

Mas:

> **conhecer, supervisionar e avaliar não implica executar diretamente toda especialização.**

O Orchestrator deve delegar partes do trabalho a agentes especializados quando isso produzir melhor resultado.

---

# 7. Capacidades fundamentais

As capacidades centrais atualmente definidas são:

```text
Project Awareness
Project Management
Ecosystem Awareness
Structural Analysis
Agent & Skill Analysis
Resource / Model Selection
Delegation & Coordination
Result Evaluation
Replanning
Continuity & Learning
```

A separação entre essas capacidades deve ser preservada.

---

# 8. Fluxo conceitual principal

O modelo de raciocínio do Orchestrator é:

```text
PROJECT
   ↓
UNDERSTAND
   ↓
STRUCTURE
   ↓
APPROVE
   ↓
WORK UNITS
   ↓
REQUIRED CAPABILITIES
   ↓
SKILLS
   ↓
ELIGIBLE AGENTS
   ↓
ELIGIBLE MODELS
   ↓
RESOURCE CONFIGURATION
   ↓
DELEGATION
   ↓
EXECUTION
   ↓
EVALUATION
   ↓
INTEGRATION
   ↓
REPLANNING
   ↓
CONTINUITY / LEARNING
```

---

# 9. Regra fundamental de delegação

Nunca partir simplesmente de:

```text
"quais agentes estão disponíveis?"
```

Partir de:

```text
necessidade
→ Work Unit
→ capacidade
→ Skill
→ agente
→ modelo
→ configuração
```

A existência de um recurso não cria automaticamente uma necessidade de utilizá-lo.

---

# 10. Economicidade

O Orchestrator deve considerar:

```text
capacidade
qualidade
custo
latência
contexto
coordenação
retrabalho
risco
```

Mais agentes não significa automaticamente melhor resultado.

Um agente ou modelo de menor custo pode ser adequado quando satisfizer os critérios exigidos.

---

# 11. Autoridade do desenvolvedor

O desenvolvedor permanece responsável por definir limites estratégicos.

Podem incluir:

```text
modelos permitidos
providers
orçamento
custos máximos
segurança
recursos proibidos
níveis de autonomia
qualidade mínima
políticas
```

O Orchestrator escolhe dentro dessas restrições.

---

# 12. Structural Analysis

A estrutura do projeto pode ser produzida por agente especialista e revisada pelo Orchestrator.

Fluxo:

```text
Orchestrator
→ estruturação especializada
→ proposta
→ análise do Orchestrator
→ feedback
→ revisão
→ reanálise
→ aprovação
→ baseline
```

O Orchestrator deve compreender a estrutura suficientemente para avaliá-la, sem precisar produzir sozinho toda a especialização estrutural.

---

# 13. Project Management

A unidade operacional principal é:

```text
Work Unit
```

O trabalho deve ser liberado por dependência.

Princípio:

```text
dependência
→ disponibilidade
→ execução
```

e não apenas:

```text
disponibilidade
→ execução
```

A execução padrão é sequencial por dependência.

Paralelismo é permitido quando houver maturidade, baixo acoplamento, dependências claras e benefício real.

---

# 14. Resource / Model Selection

A seleção responde:

> Entre as configurações tecnicamente elegíveis, qual oferece a melhor relação entre adequação, qualidade, risco, tempo e custo para esta Work Unit?

Separar:

```text
Agent
≠
Skill
≠
Model
≠
Runtime
```

Um Agent pode possuir diferentes modelos elegíveis.

---

# 15. Result Evaluation

Resultado recebido não significa resultado aceito.

A avaliação verifica, conforme necessário:

```text
correção
completude
coerência
aderência ao objetivo
restrições
suficiência
rastreabilidade
evidências
dependências
risco
impacto
necessidade de revisão
```

A profundidade da avaliação é proporcional ao impacto, criticidade, incerteza e sensibilidade.

---

# 16. Replanning

Replanning preserva o máximo de trabalho válido.

Fluxo:

```text
PLAN
→ EXECUTE
→ EVALUATE
→ NEW INFORMATION
→ REPLAN
→ NEW PLAN
```

Não reiniciar o projeto inteiro por uma mudança localizada.

Classificação de impacto:

```text
LOCAL
CONTEXTUAL
STRUCTURAL
CRITICAL
UNKNOWN IMPACT
```

---

# 17. Continuity & Learning

Distinguir:

```text
CONTINUITY
→ preservar estado e histórico necessário

LEARNING
→ extrair conhecimento útil para decisões futuras
```

Experiência não se torna regra automaticamente.

O conceito de:

```text
Learning Candidate
```

existe justamente para representar conhecimento que ainda precisa de validação e governança.

---

# 18. Arquitetura atual

A arquitetura macro adotada é:

```text
Clean Architecture
+
DDD
+
Ports & Adapters
+
SOLID / Clean Code
+
Deep Modules
+
Specification-Driven Development
```

Regra de dependência:

```text
Interface / Infrastructure
        ↓
Application
        ↓
Domain
```

O núcleo não deve depender diretamente de:

```text
OpenClaw
Hermes
SQL
SDKs de providers
MCP
frameworks
```

---

# 19. Modular Monolith

A implementação inicial será tratada como:

```text
modular monolith
```

Não há justificativa atual para iniciar com microserviços.

As separações são inicialmente lógicas e internas.

---

# 20. Deep Modules

O design deve favorecer:

```text
interface pequena
+
comportamento profundo
+
alto leverage
+
alta locality
```

Evitar conjuntos de módulos rasos que apenas repassem chamadas.

Antes de criar uma abstração, perguntar:

```text
Existe complexidade real para esconder?
Existe variação real?
Existe necessidade de substituição?
Existe benefício de teste?
```

---

# 21. Seam Discipline

Ports e adapters devem existir quando houver seam real.

Regra:

```text
necessidade real
→ seam
→ interface
→ adapter
```

Não criar interfaces especulativas para todas as classes.

`AgentRuntime` é um seam real porque OpenClaw é o primeiro runtime e Hermes/outros runtimes podem ocupar o mesmo papel.

---

# 22. Design It Twice

Módulos críticos já identificados:

```text
Resource Selection
Delegation
Result Evaluation
Replanning
```

Para esses módulos, interfaces devem ser avaliadas por:

```text
Depth
Leverage
Locality
Seam placement
```

antes do congelamento do contrato de implementação.

---

# 23. Specification-Driven Development

SDD é disciplina transversal.

Fluxo:

```text
Intention
→ Specification
→ Architecture
→ Design
→ Implementation Plan
→ Implementation
→ Verification / Evals
→ Evidence
→ Feedback
```

Regras fundamentais:

```text
Specification = fonte normativa da intenção
Code = implementação
Test / Eval = verificação
Evidence = demonstração
```

Prompt não substitui Specification.

Skill não substitui Project Specification.

Policy não deve depender apenas de Prompt.

---

# 24. Skill Architecture

A arquitetura física das Skills ainda não foi implementada.

O modelo conceitual deverá considerar, quando aplicável:

```text
identity
purpose
capabilities
invocationPolicy
dependencies
composition
inputs
outputs
constraints
compatibleAgents
compatibleModels
compatibleRuntimes
provenance
version
```

Também foi identificada a distinção:

```text
User-invoked
Model-invoked
```

A forma final da Skill Architecture ainda será definida.

---

# 25. Linguagem do domínio

`CONTEXT.md` é o glossário canônico.

Termos centrais incluem:

```text
Project
Work Unit
Plan
Baseline
Agent
Skill
Model
Resource Configuration
Task Package
Result Package
Evaluation
Decision
Delegation
Replanning
Continuity
Learning Candidate
Policy
Module
Interface
Seam
Adapter
Depth
```

Quando um novo termo relevante for consolidado, atualizar `CONTEXT.md` no momento apropriado.

---

# 26. Estrutura documental-alvo

Estrutura definitiva pretendida:

```text
Professional-Software-Engineering-Skill/
│
├── README.md
├── CONTEXT.md
│
├── specifications/
│   ├── MASTER-SPECIFICATION.md
│   ├── orchestrator/
│   │   └── ...
│   └── [future-skills]/
│
├── skills/
│   ├── orchestrator/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   ├── resources/
│   │   └── ...
│   └── [future-skills]/
│
└── docs/
    ├── architecture/
    ├── process/
    └── reviews/
```

Durante a transição ainda existe:

```text
docs/transition/
```

Essa pasta é temporária e deverá desaparecer quando seu conteúdo tiver sido devidamente reposicionado, consolidado, reescrito, renomeado ou eliminado.

---

# 27. Localizações relevantes atuais

```text
specifications/orchestrator/
└── ORCHESTRATOR-REQUIREMENTS.md
```

```text
docs/architecture/
├── ORCHESTRATOR-SYSTEM-ARCHITECTURE.md
└── ORCHESTRATOR-SYSTEM-DESIGN.md
```

```text
docs/process/
├── DEVELOPMENT-CONTINUITY*.md
├── GIT-WORKFLOW.md
├── NEW-CHAT-CONTEXT.md
└── ORCHESTRATOR-SPEC-DRIVEN-DEVELOPMENT.md
```

```text
docs/reviews/
└── ORCHESTRATOR-DESIGN-REVIEW.md
```

---

# 28. Documentos de transição

Ainda existem documentos em:

```text
docs/transition/
```

Eles não devem ser considerados automaticamente parte da estrutura definitiva.

Para cada documento:

```text
analisar função
→ decidir destino
→ mover / renomear / consolidar / reescrever / eliminar
```

Não mover tudo em massa.

---

# 29. Estado atual

Já foram consolidados:

```text
Project Definition
Capabilities
Knowledge Map
Requirements
System Architecture
System Design
Design Review
Specification-Driven Development
CONTEXT.md
```

A arquitetura e o design já passaram por revisão usando:

```text
Clean Architecture
DDD
SOLID
Ports & Adapters
Deep Modules
Seam Discipline
Design It Twice
SDD
```

---

# 30. Inconsistência que deve ser verificada

A revisão de Design registra um **Design v0.2**, mas deve ser verificado se o arquivo canônico:

```text
docs/architecture/ORCHESTRATOR-SYSTEM-DESIGN.md
```

já contém efetivamente o conteúdo consolidado da revisão v0.2.

Não presumir que a versão está consolidada apenas porque a review existe.

Se necessário:

```text
review
→ consolidar Design
→ validar
→ atualizar arquivo canônico
```

---

# 31. Próximo gate

O próximo gate é:

```text
DESIGN CONSOLIDADO
        ↓
IMPLEMENTATION PLAN
        ↓
WORK UNITS
        ↓
DEPENDENCY ORDER
        ↓
ACCEPTANCE CRITERIA
        ↓
VERIFICATION STRATEGY
        ↓
IMPLEMENTATION
```

Não iniciar código diretamente.

---

# 32. Objetivo do Implementation Plan

O Implementation Plan deve converter o Design em trabalho executável.

Cada Work Unit deverá definir, conforme aplicável:

```text
objetivo
escopo
entradas
saídas
dependências
componentes afetados
critério de aceitação
estratégia de verificação
ordem
```

A implementação deve começar preferencialmente pelo núcleo e validar o primeiro vertical slice antes das integrações mais complexas.

---

# 33. Primeiro vertical slice esperado

Direção preliminar:

```text
Initialize Project
+
Create Work Unit
+
Store State
+
Read State
```

Depois:

```text
Plan Work
+
Dependencies
+
Ready / Blocked
```

E posteriormente:

```text
Agent / Skill Analysis
+
Resource Selection
+
Delegation
+
Evaluation
+
Replanning
```

A sequência exata será confirmada no Implementation Plan.

---

# 34. Regra para decisões durante a retomada

Não perguntar quando a decisão puder ser tomada pela lógica já consolidada.

Perguntar quando houver:

```text
ambiguidade material
conflito entre fontes
impacto desconhecido
decisão fora da autoridade
bloqueio real
```

Quando uma pergunta for necessária, apresentar:

```text
Questão
Contexto
Evidências
Alternativas
Impacto
Riscos
Recomendação
```

---

# 35. Regra de preservação das decisões

Quando uma decisão consolidada for reconsiderada:

```text
Decisão atual
↓
Nova evidência
↓
Problema
↓
Impacto
↓
Alternativas
↓
Nova decisão
↓
Atualização documental
↓
Versionamento
```

Não alterar silenciosamente.

---

# 36. Regra de análise proporcional

Não analisar tudo por padrão.

Começar pela menor abrangência suficiente:

```text
LOCAL
→ CONTEXTUAL
→ GLOBAL
```

Aumentar a abrangência quando o impacto, risco, dependências ou natureza da mudança exigirem.

---

# 37. Regra de Git

Quando a tarefa envolver versionamento:

```text
git status
→ git diff
→ validar
→ git add
→ git commit
→ git push
→ git status
```

O `GIT-WORKFLOW.md` é o documento operacional de referência para Git.

---

# 38. Regra de uso do legado

O projeto legado pode e deve ser consultado quando seu conhecimento puder qualificar o novo projeto.

Processo:

```text
conhecimento legado
→ identificar
→ avaliar compatibilidade
→ adaptar
→ incorporar
```

O legado é uma fonte de conhecimento, não uma obrigação de preservar sua organização anterior.

---

# 39. Regra contra reinicialização

O agente que assumir o projeto não deve:

```text
recomeçar a definição do projeto
reconstruir a arquitetura do zero
recriar o Design sem necessidade
ignorar a revisão v0.2
descartar o conhecimento legado já aproveitado
tratar a pasta transition como estrutura definitiva
```

Primeiro deve:

```text
ler
→ verificar
→ identificar
→ continuar
```

---

# 40. Ponto exato de retomada

Ao receber este documento, o ponto esperado é:

```text
Projeto:
Adaptive AI Orchestrator

Arquitetura:
consolidada em nível conceitual

Design:
revisado; confirmar consolidação efetiva do v0.2

SDD:
consolidado

Context:
criado

Skills:
arquitetura conceitual ainda em desenvolvimento

Transição:
em andamento

Implementação:
ainda não iniciada

Próximo trabalho:
Implementation Plan
```

Primeiro verificar a consistência do Design canônico.

Depois:

```text
Implementation Plan
```

---

# 41. Processo de trabalho

A construção continua seguindo:

```text
propor
→ identificar indefinições
→ perguntar quando necessário
→ decidir
→ consolidar
→ registrar
→ revisar
→ prosseguir
```

A colaboração com o responsável pelo projeto faz parte do processo.

---

# 42. Instrução final para um novo chat

Não assumir que este documento é a única fonte de verdade.

Use-o para saber **onde o projeto está**.

Use os documentos especializados para saber **o que o projeto define**.

Em caso de conflito:

```text
identificar fonte
→ verificar autoridade
→ analisar impacto
→ não decidir silenciosamente
```

O objetivo de uma nova sessão é **continuar o projeto do ponto registrado**, não reconstruí-lo.
