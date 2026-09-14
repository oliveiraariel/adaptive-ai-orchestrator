# ORCHESTRATOR-CONTINUITY-AND-LEARNING

**Projeto:** Adaptive AI Orchestrator  
**Capacidade:** Continuity & Learning  
**Versão:** v0.1 — definição inicial  
**Status:** Em desenvolvimento

---

## 1. Propósito

A capacidade **Continuity & Learning** permite ao Orchestrator preservar o estado necessário para continuidade e transformar experiências observadas em conhecimento utilizável em decisões futuras.

Ela possui duas responsabilidades relacionadas, mas distintas:

```text
CONTINUITY
→ preservar o que precisa continuar existindo

LEARNING
→ aprender o que pode melhorar decisões futuras
```

O objetivo não é armazenar tudo indiscriminadamente.

O objetivo é preservar e aprender **o que possui valor operacional, metodológico, histórico ou estratégico**.

---

## 2. Papel dentro do Orchestrator

Continuity & Learning responde:

> **"O que precisa ser preservado para que o projeto continue corretamente e o que pode ser aprendido com o que aconteceu para melhorar decisões futuras?"**

Ela recebe informações de:

- Project Awareness;
- Project Management;
- Ecosystem Awareness;
- Agent & Skill Analysis;
- Resource / Model Selection;
- Delegation & Coordination;
- Result Evaluation;
- Replanning.

Produz:

- estado persistido;
- histórico;
- decisões registradas;
- evidências;
- conhecimento reutilizável;
- experiência categorizada;
- candidatos a melhoria;
- indicadores de desempenho;
- informações para futuras seleções e replanejamentos.

---

## 3. Distinção fundamental entre continuidade e aprendizado

### Continuidade

Busca preservar:

```text
estado atual
contexto
decisões
baseline
pendências
dependências
resultados aceitos
artefatos
histórico necessário
```

### Aprendizado

Busca extrair:

```text
padrões
lições
evidências
desempenho
falhas recorrentes
configurações eficazes
configurações ineficazes
oportunidades de melhoria
```

Uma informação pode ser essencial para continuidade sem produzir aprendizado generalizável.

Da mesma forma, uma experiência de um projeto pode gerar conhecimento útil para outros projetos sem pertencer ao estado atual daquele projeto.

---

## 4. Princípio de preservação

> **Conhecimento, decisões ou estado relevantes não devem ser perdidos apenas porque não pertencem ao núcleo ativo da execução.**

Isso reutiliza diretamente o princípio de preservação do conhecimento do projeto legado e do novo `PROJECT-DEFINITION`.

O destino de uma informação deve ser determinado por sua função.

---

## 5. Estado do projeto

O Orchestrator deve manter uma representação suficiente do estado do projeto.

Conceitualmente:

```text
PROJECT STATE
├── identidade
├── objetivos
├── escopo
├── requisitos
├── decisões
├── Work Units
├── dependências
├── estados
├── artefatos
├── baselines
├── riscos
├── pendências
├── resultados
├── bloqueios
├── recursos
└── histórico relevante
```

Não significa que todos os itens devam ficar em um único armazenamento físico.

---

## 6. Estado atual versus histórico

O sistema deve diferenciar:

```text
CURRENT STATE
```

de:

```text
HISTORICAL STATE
```

Exemplo:

```text
Current:
Architecture v3

Historical:
Architecture v1
Architecture v2
```

O estado atual deve representar o que é válido agora.

O histórico deve preservar o que foi relevante para compreender a evolução.

---

## 7. Estado não é memória indiscriminada

Nem toda mensagem ou evento precisa ser preservado permanentemente.

O Orchestrator deve priorizar:

- decisões;
- mudanças;
- resultados;
- evidências;
- dependências;
- razões;
- estados;
- eventos relevantes;
- informações úteis para futuras decisões.

Informações sem valor operacional, histórico ou analítico podem ser descartadas conforme políticas posteriores.

---

## 8. Continuidade entre execuções

Ao retomar um projeto, o Orchestrator deve conseguir reconstruir:

```text
onde estamos
+
o que já foi concluído
+
o que está bloqueado
+
o que está pendente
+
quais decisões existem
+
quais dependências existem
+
qual é a próxima ação
```

A continuidade deve reduzir a necessidade de reconstrução manual do contexto.

---

## 9. Continuidade entre conversas ou sessões

Quando o runtime oferecer persistência de contexto, workspace ou memória, o Orchestrator deve aproveitar esses mecanismos.

Quando não oferecer, o projeto deverá possuir mecanismos próprios de estado persistente.

O conceito de continuidade é independente do mecanismo físico utilizado.

---

## 10. Identidade do projeto

O estado persistente deve possuir referência inequívoca ao projeto.

Conceitualmente:

```text
project_id
project_version
state_version
```

ou equivalente.

Isso reduz risco de misturar conhecimento entre projetos diferentes.

---

## 11. Versionamento do estado

Mudanças relevantes no estado devem ser versionáveis.

Não é necessário versionar cada evento trivial.

A granularidade deve ser proporcional à importância da alteração.

Exemplos de eventos que justificam registro:

- nova baseline;
- mudança arquitetural;
- mudança de requisito;
- aceitação/rejeição importante;
- decisão estratégica;
- mudança de agente/modelo relevante;
- conclusão de etapa;
- reabertura relevante.

---

## 12. Decisões

Decisões importantes devem ser preservadas com:

```text
questão
contexto
evidência
alternativas
impacto
riscos
recomendação
responsável
resultado
versão/data
```

Essa estrutura é diretamente reutilizada do modelo de decisão já consolidado no legado.

---

## 13. Proveniência

Sempre que possível, o estado deve preservar a origem da informação:

```text
user
agent
tool
document
code
test
external source
inference
historical record
```

Isso permite avaliar a confiabilidade do conhecimento posteriormente.

---

## 14. Estados epistemológicos

Conhecimento relevante deve poder distinguir:

```text
UNKNOWN
IDENTIFIED
INFERRED
PROPOSED
CONFIRMED
DECIDED
VALIDATED
```

O fluxo não precisa ser linear.

Uma informação pode voltar a estado de incerteza quando uma evidência posterior a contradizer.

---

## 15. Incerteza persistente

Desconhecimento deve permanecer representado como desconhecimento.

O Orchestrator não deve preencher automaticamente:

```text
UNKNOWN
```

com uma suposição só porque precisa continuar o projeto.

Se uma inferência for necessária:

```text
INFERRED
+
evidência
+
confidence
```

devem ser preservados.

---

## 16. Confiança

Conhecimento aprendido pode possuir:

```text
HIGH
MEDIUM
LOW
UNKNOWN
CONTRADICTORY
```

A confiança deve considerar:

- qualidade da evidência;
- repetição;
- independência;
- contexto;
- tempo;
- consistência;
- resultados observados.

---

## 17. Eventos de execução

A execução de uma Work Unit pode gerar eventos:

```text
delegated
started
progress
blocked
failed
completed
evaluated
reopened
cancelled
```

Eventos relevantes podem alimentar:

- estado;
- histórico;
- métricas;
- diagnóstico;
- aprendizagem.

---

## 18. Registro de configuração utilizada

Para aprendizado real, registrar, quando possível:

```text
Work Unit
Agent
Skill(s)
Model
Provider
Context characteristics
Execution time
Cost
Result
Evaluation
Rework
Human intervention
```

Essa combinação é fundamental porque desempenho isolado de um modelo não informa necessariamente o desempenho da configuração completa.

---

## 19. Configuração como unidade de evidência

Uma experiência deve ser associada à configuração real:

```text
Task
+
Agent
+
Skill
+
Model
+
Context
+
Strategy
```

Isso permite descobrir que:

```text
Model X
```

pode funcionar bem com:

```text
Skill A + Agent A
```

mas não necessariamente com:

```text
Skill B + Agent B
```

---

## 20. Métricas de execução

Quando disponíveis, registrar:

```text
tempo
custo
volume de chamadas
latência
retries
falhas
revisões
intervenções
retrabalho
qualidade
```

As métricas não devem ser interpretadas isoladamente.

---

## 21. Qualidade observada

Qualidade deve ser derivada, quando possível, de:

- critérios de aceitação;
- avaliação do Orchestrator;
- revisão independente;
- resultado real;
- feedback humano;
- ausência/presença de retrabalho;
- testes.

Uma resposta longa não deve ser presumida como qualidade superior.

---

## 22. Eficiência observada

Eficiência pode considerar:

```text
resultado obtido
vs.
recursos utilizados
```

Incluindo:

```text
custo
tempo
número de agentes
número de chamadas
complexidade de coordenação
retrabalho
```

Uma solução mais barata nem sempre é mais eficiente se gerar retrabalho elevado.

---

## 23. Registro de falhas

Falhas devem ser classificadas quando possível:

```text
planning_failure
selection_failure
delegation_failure
context_failure
skill_failure
agent_failure
model_failure
tool_failure
integration_failure
evaluation_failure
external_failure
```

Essa classificação é importante para não corrigir o componente errado.

---

## 24. Registro de retrabalho

Quando uma Work Unit precisar ser refeita, registrar:

```text
causa
parte refeita
recurso anterior
recurso novo
custo
tempo
impacto
```

Retrabalho é uma evidência valiosa para planejamento e seleção futuros.

---

## 25. Registro de intervenções humanas

Quando o desenvolvedor precisar intervir, preservar:

```text
motivo
decisão
contexto
alternativas
resultado
```

Intervenções recorrentes podem revelar lacunas de autonomia, conhecimento ou governança.

---

## 26. Aprendizado

Aprender significa transformar experiências observadas em informação potencialmente útil para decisões futuras.

O ciclo pode ser:

```text
experiência
↓
observação
↓
análise
↓
padrão candidato
↓
validação
↓
conhecimento reutilizável
```

A experiência não deve virar regra imediatamente.

---

## 27. Candidato a conhecimento

Uma observação pode gerar:

```text
LEARNING CANDIDATE
```

Exemplo:

```text
"Architecture Agent X apresentou menos retrabalho em projetos desta classe."
```

Isso é uma observação.

Ainda não é uma regra:

```text
"sempre usar Agent X."
```

---

## 28. Evidência repetida

Uma hipótese pode ganhar confiança quando:

```text
mesmo padrão
+
múltiplas execuções
+
contextos comparáveis
+
resultados consistentes
```

forem observados.

Ainda assim, contexto deve permanecer associado.

---

## 29. Generalização

Uma experiência específica:

```text
Projeto A
```

não deve automaticamente tornar-se:

```text
regra global
```

Para generalizar, avaliar:

- repetição;
- diversidade de contextos;
- consistência;
- explicação;
- ausência de contradições;
- relevância.

Essa regra vem diretamente do princípio de evolução governada do legado.

---

## 30. Conhecimento específico versus geral

Uma observação pode ser:

```text
PROJECT-SPECIFIC
```

ou:

```text
GENERALIZABLE
```

Exemplo:

```text
"Neste projeto o cliente exige documentação X."
→ específica.

"Projetos críticos deste domínio frequentemente exigem revisão adicional."
→ potencialmente generalizável.
```

---

## 31. Conhecimento sobre agentes

O histórico pode ajudar a construir perfis empíricos:

```text
Agent A
├── tarefas executadas
├── Skills utilizadas
├── qualidade observada
├── custo
├── retrabalho
├── estabilidade
└── limitações observadas
```

Não deve substituir as capacidades declaradas.

É uma camada adicional de evidência.

---

## 32. Conhecimento sobre Skills

Da mesma forma:

```text
Skill X
├── tarefas
├── agentes
├── modelos
├── resultados
├── limitações
└── evidências
```

Isso pode revelar:

- Skills muito amplas;
- Skills insuficientes;
- Skills que funcionam melhor em determinadas condições.

---

## 33. Conhecimento sobre modelos

O projeto já definiu esse conhecimento como dinâmico.

Registrar:

```text
versão
capacidade
custo
contexto
latência
disponibilidade
resultados
feedback
```

Ao longo do tempo, o histórico pode mostrar mudanças de desempenho.

---

## 34. Conhecimento sobre combinações

Uma das formas mais úteis de aprendizado será registrar combinações:

```text
Agent + Skill + Model + Task Type
```

Exemplo:

```text
Architecture Agent
+
Architecture Skill
+
Model X
+
Architecture Design
```

Essa combinação pode se tornar uma configuração candidata recorrente.

---

## 35. Conhecimento sobre delegação

Também registrar:

```text
quem delegou
para quem
qual contexto
qual tamanho do contexto
qual resultado
qual qualidade
qual custo
```

Isso permite avaliar se determinadas estratégias de handoff funcionam melhor.

---

## 36. Conhecimento sobre paralelismo

O histórico pode revelar:

```text
parallel execution
```

reduziu tempo ou:

```text
parallel execution
```

aumentou retrabalho.

Isso alimenta futuras decisões de Project Management.

---

## 37. Conhecimento sobre replanejamento

Registrar:

```text
trigger
impact
change
result
```

pode revelar:

- quais eventos mais frequentemente causam replanejamento;
- quais mudanças são normalmente locais;
- quais mudanças tendem a ser estruturais;
- onde o planejamento inicial falha.

---

## 38. Knowledge Lifecycle

O conhecimento pode passar por:

```text
OBSERVED
↓
RECORDED
↓
ANALYZED
↓
CANDIDATE
↓
VALIDATED
↓
ADOPTED
↓
REVISED
↓
DEPRECATED
```

Nem todo conhecimento precisa passar por todas as fases.

---

## 39. Conhecimento obsoleto

Conhecimento pode deixar de ser válido.

Exemplos:

```text
modelo removido
API alterada
Skill substituída
política modificada
prática superada
```

O sistema deve preservar histórico, mas impedir que conhecimento obsoleto seja utilizado como atual sem sinalização.

---

## 40. Conhecimento contraditório

Quando existirem duas evidências conflitantes:

```text
Evidence A
vs.
Evidence B
```

o Orchestrator deve registrar a divergência.

Não deve resolver arbitrariamente.

Pode:

- diminuir confiança;
- solicitar nova evidência;
- executar experimento;
- consultar fonte;
- escalar.

---

## 41. Evidência temporal

Conhecimento dinâmico deve possuir contexto temporal.

Exemplo:

```text
Model X
price:
valor em data T
```

e:

```text
Model X
capability:
observada na versão V
```

Isso evita usar informações antigas como se fossem atuais.

---

## 42. Memória de curto prazo e longo prazo

Conceitualmente, pode existir:

```text
SHORT-TERM CONTEXT
```

para o ciclo atual e:

```text
LONG-TERM KNOWLEDGE
```

para experiências reutilizáveis.

A divisão física dependerá do runtime e da arquitetura de armazenamento.

---

## 43. Memória operacional

Informações necessárias para continuar o trabalho atual:

```text
current state
active Work Units
dependencies
pending decisions
recent results
current plan
```

---

## 44. Memória histórica

Informações necessárias para compreender evolução:

```text
previous baselines
decisions
revisions
failures
important changes
```

---

## 45. Memória de aprendizagem

Informações potencialmente úteis em projetos futuros:

```text
validated patterns
empirical evidence
successful configurations
failure patterns
recommendations
```

---

## 46. Separação entre memória e metodologia

Uma experiência histórica não deve automaticamente alterar a Skill do Orchestrator.

Deve existir:

```text
experience
→ candidate learning
→ evaluation
→ possible update
```

A metodologia deve possuir governança própria.

---

## 47. Feedback para Resource / Model Selection

O histórico de execução deve permitir:

```text
selected configuration
→ actual result
→ evaluated result
→ learning
→ future selection
```

Assim o sistema pode eventualmente melhorar a adequação das seleções.

---

## 48. Feedback para Agent & Skill Analysis

Também poderá revelar:

```text
Skill aparentemente suficiente
→ repetidamente insuficiente
```

ou:

```text
Agent especializado
→ boa performance somente quando Skill X está presente
```

Esses dados sugerem refinamentos.

---

## 49. Feedback para Delegation & Coordination

Pode revelar:

```text
handoff grande demais
```

ou:

```text
contexto insuficiente
```

ou:

```text
muitos agentes
```

Essas observações alimentam melhoria do protocolo de delegação.

---

## 50. Feedback para Result Evaluation

Pode revelar:

```text
critério de avaliação muito permissivo
```

ou:

```text
critério excessivamente rigoroso
```

Mas ajustes metodológicos devem passar por governança.

---

## 51. Feedback para Replanning

O histórico pode revelar padrões de:

```text
replanejamento tardio
```

ou:

```text
replanejamento excessivo
```

permitindo melhorar a política posteriormente.

---

## 52. Feedback para Project Management

O histórico de execução pode indicar:

- estimativas inadequadas;
- dependências mal identificadas;
- excesso de paralelismo;
- granularidade inadequada;
- prioridades mal definidas.

Esses padrões devem gerar candidatos a melhoria.

---

## 53. Métricas não são conhecimento por si mesmas

Um número como:

```text
cost = X
```

é uma observação.

Para virar conhecimento:

```text
contextualização
+
comparação
+
interpretação
```

são necessárias.

---

## 54. Benchmark interno

O sistema pode construir referências históricas:

```text
Task Type
→ média de custo
→ média de tempo
→ qualidade
→ retrabalho
```

Essas referências devem ser usadas como evidência, não como regra absoluta.

---

## 55. Experimentos

Quando uma hipótese importante surgir, o Orchestrator pode propor experimento:

```text
Hypothesis
↓
controlled execution
↓
comparison
↓
evidence
↓
learning candidate
```

Isso pode ser especialmente útil para:

- comparação de modelos;
- comparação de Skills;
- estratégia de delegação;
- paralelismo;
- revisão independente.

---

## 56. Feedback humano

Feedback do desenvolvedor é uma fonte de evidência importante.

Deve ser preservado com:

```text
context
task
resource
feedback
reason
consequence
```

Feedback não deve ser interpretado automaticamente como verdade universal.

---

## 57. Lições aprendidas

Após uma etapa ou projeto, gerar:

```text
LESSON
├── context
├── observation
├── cause
├── impact
├── recommendation
├── confidence
└── scope
```

Isso facilita transformação posterior em conhecimento.

---

## 58. Aprendizado pós-projeto

Ao concluir um projeto:

```text
Projeto
↓
Resultados
↓
Avaliações
↓
Falhas
↓
Sucessos
↓
Lições
↓
Candidatos
↓
Avaliação
```

Essa sequência já está prevista conceitualmente no conhecimento legado.

---

## 59. Controle contra deriva metodológica

O Orchestrator não deve:

- alterar silenciosamente suas regras;
- transformar uma preferência em padrão;
- remover controles para ganhar velocidade;
- reduzir critérios de avaliação para aumentar taxa de conclusão;
- esconder incerteza.

Alterações metodológicas devem ser explicitamente avaliadas.

Isso reutiliza diretamente o princípio de evolução governada do projeto anterior.

---

## 60. Retenção

O sistema deve possuir política para decidir:

```text
manter
arquivar
agregar
resumir
remover
```

A retenção deve considerar:

- utilidade;
- custo;
- sensibilidade;
- histórico;
- auditoria;
- necessidade futura.

A política detalhada ficará para a arquitetura de conhecimento.

---

## 61. Privacidade e sensibilidade

Informações que contenham:

- dados pessoais;
- segredos;
- credenciais;
- informações sensíveis;
- conteúdo proprietário;

não devem ser incorporadas ao aprendizado de maneira indiscriminada.

A arquitetura de armazenamento e políticas do runtime deverão controlar esse aspecto.

---

## 62. Isolamento entre projetos

Aprendizado de um projeto não deve contaminar outro automaticamente.

Devem existir níveis:

```text
PROJECT-SPECIFIC
```

e:

```text
GENERAL KNOWLEDGE
```

A promoção de conhecimento deve ser controlada.

---

## 63. Atualização de conhecimento

Uma atualização relevante deve preservar:

```text
versão
origem
motivo
evidência
impacto
```

Isso permite reversão quando necessário.

---

## 64. Conhecimento derivado do legado

O conhecimento herdado do projeto anterior deve passar pelo mesmo processo:

```text
legado
↓
análise
↓
classificação
↓
validação
↓
reposicionamento
```

Não deve ser tratado como automaticamente correto apenas por ser antigo.

Entretanto, seu conhecimento já consolidado possui valor especial como **base metodológica previamente construída**.

---

## 65. Destinos possíveis do conhecimento

Uma informação pode ser destinada a:

```text
Orchestrator Knowledge
Core Knowledge
Component Knowledge
Skill Knowledge
Agent-specific Knowledge
Project Knowledge
Empirical Knowledge
Research
Archive
```

Essa taxonomia já aparece no `PROJECT-DEFINITION`.

---

## 66. Transformação em Skill

Quando uma experiência se tornar procedimento generalizável:

```text
learning candidate
↓
validated pattern
↓
Skill candidate
```

Depois:

```text
Skill
↓
implementation
↓
evaluation
```

A existência de uma Skill deve depender de necessidade e evidência, não de simplesmente haver um documento.

---

## 67. Transformação em prompt/instrução

Quando o conhecimento for principalmente comportamental:

```text
regra
prioridade
critério
limite
```

pode tornar-se:

```text
prompt
AGENTS
system instruction
rule
```

A implementação dependerá do runtime.

---

## 68. Transformação em referência

Quando o conhecimento for detalhado e consultável:

```text
reference
documentation
catalog
guide
```

pode permanecer fora do prompt principal e ser carregado conforme necessidade.

---

## 69. Aprendizado sobre prompts

O sistema também pode avaliar:

```text
Prompt Version
→ Result
→ Evaluation
```

permitindo descobrir se uma alteração de instrução:

- melhorou qualidade;
- aumentou custo;
- aumentou contexto;
- reduziu erro;
- aumentou retrabalho.

Isso será útil para a evolução dos agentes.

---

## 70. Aprendizado sobre Skills

Da mesma forma:

```text
Skill Version
→ Agent
→ Model
→ Task
→ Result
```

pode ser comparado ao longo do tempo.

---

## 71. Aprendizado sobre agentes

Pode revelar:

```text
Agent profile
```

empírico, distinto do perfil declarado.

Exemplo:

```text
declared:
Architecture specialist

observed:
excellent design
weak documentation
```

Isso pode influenciar tarefas futuras.

---

## 72. Aprendizado sobre modelos

Pode registrar:

```text
Model version
→ task class
→ configuration
→ outcome
```

permitindo diferenciar:

```text
model capability
```

de:

```text
model suitability
```

---

## 73. Aprendizado sobre custo

O histórico pode comparar:

```text
estimated cost
vs.
actual cost
```

Isso permite melhorar futuras estimativas.

---

## 74. Aprendizado sobre tempo

Da mesma forma:

```text
estimated duration
vs.
actual duration
```

Pode contribuir para planejamento futuro.

---

## 75. Aprendizado sobre quantidade de agentes

O histórico pode revelar:

```text
1 agent
→ suficiente

4 agents
→ não aumentaram qualidade
```

ou:

```text
1 agent
→ insuficiente

3 specialized agents
→ melhor resultado
```

Essas observações alimentam estratégias futuras.

---

## 76. Aprendizado sobre contexto

Pode identificar:

```text
context too large
```

ou:

```text
context insufficient
```

permitindo melhorar futuras Task Packages.

---

## 77. Aprendizado sobre falhas recorrentes

Se o mesmo tipo de falha ocorrer repetidamente:

```text
failure pattern
```

pode justificar:

- nova Skill;
- ajuste de prompt;
- novo critério de avaliação;
- mudança de seleção;
- alteração de planejamento.

---

## 78. Aprendizado controlado

O princípio final é:

```text
experiência
→ evidência
→ hipótese
→ validação
→ conhecimento
→ possível mudança
```

Não:

```text
experiência
→ regra automática
```

---

## 79. Critérios de sucesso

Continuity & Learning estará suficientemente desenvolvida quando o Orchestrator puder:

1. preservar estado atual;
2. recuperar contexto necessário;
3. registrar decisões;
4. manter histórico relevante;
5. distinguir estado atual de histórico;
6. preservar evidência e proveniência;
7. representar incerteza;
8. registrar execução e configuração;
9. registrar falhas e retrabalho;
10. extrair lições;
11. gerar candidatos a aprendizado;
12. distinguir conhecimento específico e generalizável;
13. alimentar seleção futura;
14. alimentar planejamento;
15. melhorar delegação;
16. preservar governança;
17. evitar deriva metodológica;
18. permitir evolução controlada.

---

## 80. Limites

Continuity & Learning não deve:

- aprender automaticamente qualquer coisa como regra;
- contaminar projetos entre si;
- alterar políticas sem governança;
- armazenar dados sensíveis indiscriminadamente;
- confundir opinião com evidência;
- tratar frequência como qualidade;
- tratar uma experiência como regra universal;
- apagar histórico relevante;
- impedir evolução por excesso de rigidez.

---

## 81. Princípio operacional consolidado

> **O Orchestrator deve preservar o estado necessário para continuidade e transformar experiências observadas em evidência e candidatos a conhecimento, promovendo-os para padrões, Skills ou mudanças metodológicas somente após análise, validação e governança adequadas.**

---

## 82. Fluxo completo

```text
EXECUÇÃO
    ↓
RESULTADO
    ↓
AVALIAÇÃO
    ↓
REGISTRO
    ↓
ESTADO ATUALIZADO
    ↓
HISTÓRICO
    ↓
OBSERVAÇÕES
    ↓
PADRÕES CANDIDATOS
    ↓
ANÁLISE
    ↓
VALIDAÇÃO
    ↓
CONHECIMENTO REUTILIZÁVEL
    ↓
FUTURA SELEÇÃO / PLANEJAMENTO / DELEGAÇÃO
    ↺
```

---

## 83. Relação com as capacidades anteriores

```text
Project Awareness
        ↓
estado do projeto

Project Management
        ↓
plano e execução

Ecosystem Awareness
        ↓
recursos

Agent & Skill Analysis
        ↓
capacidades

Resource / Model Selection
        ↓
configuração

Delegation & Coordination
        ↓
execução real

Result Evaluation
        ↓
qualidade observada

Replanning
        ↓
novo plano

Continuity & Learning
        ↓
estado + histórico + conhecimento
        ↓
melhor próximo ciclo
```

Isso fecha o ciclo adaptativo do Orchestrator.

---

## 84. Relação com o projeto legado

O projeto legado oferece uma base particularmente forte para esta capacidade:

- evolução governada;
- aprendizagem pós-projeto;
- distinção entre projeto e Skill;
- preservação de conhecimento;
- evidência;
- estados epistemológicos;
- confiança;
- histórico;
- rastreabilidade.

O novo projeto adiciona:

- evidência de configuração Agent + Skill + Model;
- telemetria operacional;
- aprendizado de seleção;
- aprendizado de delegação;
- aprendizado de contexto;
- aprendizado de custo;
- aprendizado de replanejamento.

---

## 85. Estado

**Status:** Definição inicial concluída.

### Artefatos relacionados

- `PROJECT-DEFINITION.md`
- `ORCHESTRATOR-CAPABILITIES.md`
- `ORCHESTRATOR-KNOWLEDGE-MAP.md`
- `ORCHESTRATOR-PROJECT-AWARENESS.md`
- `ORCHESTRATOR-PROJECT-MANAGEMENT.md`
- `ORCHESTRATOR-ECOSYSTEM-AWARENESS.md`
- `ORCHESTRATOR-AGENT-AND-SKILL-ANALYSIS.md`
- `ORCHESTRATOR-RESOURCE-MODEL-SELECTION.md`
- `ORCHESTRATOR-DELEGATION-AND-COORDINATION.md`
- `ORCHESTRATOR-RESULT-EVALUATION.md`
- `ORCHESTRATOR-REPLANNING.md`

### Próxima atividade

As dez capacidades centrais do Orchestrator estarão conceitualmente cobertas.

A próxima etapa do projeto deve consolidar:

```text
capacidades
+
conhecimento necessário
+
dependências
+
lacunas
```

e então transformar esse conjunto em **requisitos formais do Orchestrator**.

---

## 86. Fechamento do ciclo

As capacidades centrais agora formam:

```text
COMPREENDER
    ↓
PLANEJAR
    ↓
CONHECER RECURSOS
    ↓
ANALISAR CAPACIDADES
    ↓
SELECIONAR
    ↓
DELEGAR
    ↓
AVALIAR
    ↓
REPLANEJAR
    ↓
PRESERVAR / APRENDER
    ↺
```

O ciclo representa o comportamento adaptativo que define o núcleo conceitual do Adaptive AI Orchestrator.


---

## Incident-to-knowledge lifecycle

Continuity & Learning now has an executable incident bridge for meaningful
defects and runtime/protocol anomalies.

An unresolved incident is persisted independently from the conversation or
runtime session that discovered it. It therefore participates in continuity as
active state and cannot disappear merely because the initiating execution
ended.

The four persistence roles are explicit:

~~~text
operational memory
  -> what is unresolved now

historical incident memory
  -> what was tried, observed and decided

empirical learning
  -> what may have been learned

validated knowledge
  -> what may guide later planning and Skills
~~~

The Incident Lifecycle Manager prevents a validated incident from skipping
learning disposition and consistency review. Resolution Pressure makes active
incidents compete for orchestration attention while preserving normal budgets,
side-effect policy and human authority.

See INCIDENT-PROACTIVE-LEARNING-PROTOCOL-V1.md for the normative v1 flow.
