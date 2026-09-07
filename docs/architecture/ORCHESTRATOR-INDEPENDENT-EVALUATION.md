# ORCHESTRATOR — INDEPENDENT MULTI-AXIS EVALUATION

**Projeto:** Adaptive AI Orchestrator  
**Status:** Arquitetura normativa incremental

## 1. Propósito

Amadurecer `Result Evaluation` para que resultados críticos possam ser avaliados por eixos independentes, preservando a identidade de cada revisão antes da decisão de aceitação.

A inspiração operacional mais forte veio do `code-review` do ecossistema Matt Pocock, que separa Standards e Spec em subagentes distintos para reduzir contaminação de contexto. O Adaptive generaliza esse mecanismo para qualquer conjunto de eixos.

## 2. Princípio

> **Uma avaliação agregada não deve esconder a razão específica pela qual um resultado passa, falha ou precisa de revisão.**

Exemplos de eixos:

```text
Specification
Standards
Architecture
Security
Testing
Accessibility
Performance
Domain consistency
```

A política do projeto determina quais são obrigatórios.

## 3. EvaluationAxis

Cada eixo declara:

```text
name
reviewer/evaluator identity
criteria
required | optional
```

O eixo não precisa corresponder a um agente permanente. O Resource Selection pode escolher agente/modelo/skill adequados quando a avaliação for executada.

## 4. Context independence

Quando risco/criticidade justificarem, eixos devem ser executados em contextos separados.

Objetivos:

- reduzir anchoring;
- evitar que uma conclusão preliminar contamine outra revisão;
- permitir especialização real;
- preservar findings independentes.

O Orchestrator pode posteriormente executar esses eixos em paralelo via scheduler/runtime quando houver suporte.

## 5. Aggregation rules

A agregação é determinística e não apaga os resultados individuais.

Regras básicas para eixos obrigatórios:

```text
required REJECTED            → overall REJECTED
required RETURNED            → overall RETURNED
missing required             → overall BLOCKED
required BLOCKED             → overall BLOCKED
required ACCEPTED_WITH_CONDITIONS
                             → overall ACCEPTED_WITH_CONDITIONS
all required ACCEPTED        → overall ACCEPTED
```

Eixos opcionais permanecem visíveis, mas não podem transformar uma falha obrigatória em sucesso nem bloquear sozinhos uma aceitação quando a política os declarou apenas advisory.

## 6. Missing evaluation is not success

Um eixo obrigatório ausente resulta em `BLOCKED`.

Isso elimina uma classe de falso positivo:

```text
"não encontramos problema"
```

quando na realidade:

```text
"a revisão obrigatória não ocorreu"
```

## 7. Relation to Result Evaluation

`EvaluateResult` continua responsável por produzir uma `Evaluation` para critérios explícitos.

`EvaluationPlan` coordena múltiplas avaliações:

```text
ResultPackage
      ↓
Evaluation Plan
      ↓
┌─────────┬───────────┬──────────┐
Spec      Security    Architecture
│         │           │
Evaluation Evaluation Evaluation
└─────────┴───────────┴──────────┘
      ↓
Axis-preserving aggregation
      ↓
Final orchestration verdict
```

A implementação inicial do `EvaluateResult` continua minimalista; o plano multi-eixo não transforma uma heurística simples em prova sem evidência. Evaluators especializados deverão evoluir independentemente.

## 8. Proportionality

Nem toda Work Unit precisa de múltiplos reviewers.

A quantidade e independência dos eixos deve ser proporcional a:

- criticality;
- impact;
- uncertainty;
- reversibility;
- security sensitivity;
- project policy.

Exemplo:

```text
low-risk docs change
→ one local evaluation

critical auth change
→ spec + security + architecture + tests
```

## 9. Review independence and producer separation

Quando possível em trabalho crítico:

```text
producer != evaluator
```

Um mesmo modelo físico pode até ser reutilizado quando recursos forem limitados, mas a execução deve receber contexto/papel de avaliação independente e o Orchestrator deve registrar essa limitação como evidência de confiança inferior quando relevante.

## 10. Verification gate

Testes devem provar:

- eixo obrigatório ausente bloqueia;
- rejeição obrigatória não é mascarada;
- return obrigatório exige revisão;
- accepted-with-conditions permanece explícito;
- eixo opcional não sobrescreve veredito obrigatório;
- eixo não planejado/duplicado é rejeitado;
- ordenação dos resultados segue o plano para rastreabilidade.
