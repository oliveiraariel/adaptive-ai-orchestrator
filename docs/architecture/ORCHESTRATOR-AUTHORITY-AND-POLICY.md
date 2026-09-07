# ORCHESTRATOR — AUTHORITY AND EXECUTION POLICY

**Projeto:** Adaptive AI Orchestrator  
**Status:** Arquitetura normativa incremental

## 1. Propósito

Transformar o princípio existente **segurança/integridade > autonomia** em um mecanismo operacional explícito, verificável e executado antes de efeitos externos.

O Orchestrator não deve depender apenas de instruções em prompt para determinar se uma ação pode ocorrer.

## 2. Autonomy classes

```text
AUTONOMOUS
AUTONOMOUS_WITH_REVIEW
HUMAN_APPROVAL_REQUIRED
HUMAN_EXECUTION_REQUIRED
FORBIDDEN
```

### AUTONOMOUS

O agente pode executar dentro das restrições declaradas.

### AUTONOMOUS_WITH_REVIEW

O agente pode executar, mas o resultado exige avaliação independente antes de integração/aceitação conforme a política do projeto.

### HUMAN_APPROVAL_REQUIRED

O agente pode executar apenas após autorização humana explícita para aquela unidade/ação.

### HUMAN_EXECUTION_REQUIRED

A ação deve ser executada pelo humano. O agente pode preparar instruções, brief, validações ou artefatos auxiliares, mas não deve realizar o side effect.

### FORBIDDEN

A ação não pode prosseguir no contexto atual.

## 3. Policy decisions

A avaliação de política produz um estado inequívoco:

```text
ALLOW
REQUIRE_HUMAN_APPROVAL
REQUIRE_HUMAN_EXECUTION
DENY
```

O runtime só pode ser chamado quando a decisão efetiva for `ALLOW`.

## 4. Side effects e tools

Policy também pode declarar:

- side effects autorizados;
- tools explicitamente negadas;
- exigência de review independente.

O default para side effects é conservador:

> ausência de autorização significa que nenhum side effect foi declarado como permitido.

Trabalho puramente de leitura/análise pode continuar sem side effects.

## 5. Pre-side-effect gate

A ordem obrigatória é:

```text
TaskPackage
→ ExecutionPolicy
→ requested side effects / tools
→ human approval evidence
→ PolicyDecision
→ ALLOW?
      ├─ yes → runtime
      └─ no  → stop / escalate / human path
```

Esse gate deve ocorrer **antes** de `AgentRuntime.submit`.

## 6. Human authority

A autoridade humana não significa microaprovação universal.

O Orchestrator deve empurrar a intervenção humana para os pontos em que julgamento, autoridade, credenciais, segurança ou irreversibilidade realmente exigem humano.

A inspiração operacional observada em `grilling`, `wizard`, `wayfinder` e guardrails do ecossistema Matt é generalizada assim:

```text
facts / reversible low-risk work
→ delegate when authorized

decisions / high-impact changes / human-only credentials
→ explicit authority path
```

## 7. Authority inheritance in recursive delegation

Subagentes não recebem autoridade maior do que o parent.

Regras mínimas:

1. child execution herda ou reduz a política;
2. child não pode elevar `max_depth` por conta própria;
3. child não pode transformar `HUMAN_APPROVAL_REQUIRED` em `AUTONOMOUS` sem nova autorização;
4. side effects adicionais exigem política compatível;
5. runtime adapter não pode ignorar decisão `DENY`.

A implementação atual garante bound de lineage; enforcement completo de monotonic policy inheritance é uma evolução posterior quando o Orchestrator criar TaskPackages filhos automaticamente.

## 8. Security boundary

Policy não substitui segurança de infraestrutura.

Camadas complementares:

```text
Orchestrator policy
+
Runtime sandbox / permissions
+
Tool-level guardrails
+
Provider permissions
+
Repository / CI controls
```

O princípio é defense in depth.

## 9. Skill supply-chain implication

Skills externas devem ser tratadas como conhecimento/instrução não confiável até passarem por processo de admissão que avalie:

- provenance;
- licença;
- versão;
- dependências;
- tools e network access;
- file/system mutations;
- secret handling;
- runtime assumptions;
- prompt-injection/authority escalation;
- atualização e revogação.

A admissão automatizada completa fica fora da primeira implementação, mas o novo ecossistema deve documentar provenance e contratos para possibilitá-la.

## 10. Verification gate

A implementação deve provar por teste:

- approval-required não chama runtime sem aprovação;
- a mesma tarefa chama runtime quando aprovada;
- HUMAN_EXECUTION_REQUIRED nunca é despachada para agente;
- FORBIDDEN nunca é despachada;
- tool negada bloqueia;
- side effect não autorizado bloqueia;
- decisões de policy são distinguíveis para observabilidade/escalation.
