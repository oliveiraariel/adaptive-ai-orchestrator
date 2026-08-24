# Orchestrator New Chat Context

**Projeto:** Adaptive AI Orchestrator
**Documento:** Contexto de Retomada em Novo Chat
**Versão:** 0.7
**Status:** Fase 3 — OpenClaw Gateway real validado; próximo bloco: Runtime Event Monitoring

---

# 1. Finalidade

Este documento permite que um novo chat retome o desenvolvimento do Adaptive AI Orchestrator sem depender do histórico completo da conversa.

O objetivo é:

```text
ler
→ compreender
→ verificar estado
→ identificar ponto de retomada
→ continuar
```

Não:

```text
novo chat
→ reinventar projeto
```

---

# 2. Identidade

O projeto atual é:

> Adaptive AI Orchestrator

A Professional Software Engineering Skill é conhecimento legado de alto valor.

Não confundir:

```text
Skill legada
≠
Adaptive AI Orchestrator
```

Conhecimento legado pode ser reutilizado somente após avaliação de compatibilidade.

---

# 3. Fontes de verdade

Interpretar documentos pelo escopo.

## Orchestrator

Consultar prioritariamente:

```text
specifications/orchestrator/
docs/architecture/
docs/process/ORCHESTRATOR-SPEC-DRIVEN-DEVELOPMENT.md
docs/process/ORCHESTRATOR-DEVELOPMENT-CONTINUITY.md
docs/process/ORCHESTRATOR-NEW-CHAT-CONTEXT.md
```

Quando houver requisitos, arquitetura, design ou decisão específica, eles têm prioridade sobre contexto histórico.

## Legado

```text
specifications/MASTER-SPECIFICATION.md
docs/process/DEVELOPMENT-CONTINUITY*.md
```

Esses documentos podem fornecer conhecimento histórico/metodológico, mas não são autoridade automática para o Orchestrator.

---

# 4. Ordem de leitura obrigatória para retomada

Em um novo chat, a leitura deve seguir esta sequência:

```text
1.  CONTEXT.md

2.  docs/process/ORCHESTRATOR-NEW-CHAT-CONTEXT.md
    (este documento)

3.  docs/process/ORCHESTRATOR-DEVELOPMENT-CONTINUITY.md

4.  docs/architecture/ORCHESTRATOR-SYSTEM-ARCHITECTURE.md

5.  docs/architecture/ORCHESTRATOR-SYSTEM-DESIGN.md

6.  docs/process/ORCHESTRATOR-SPEC-DRIVEN-DEVELOPMENT.md

7.  docs/process/PHASE-3-IMPLEMENTATION-PLAN.md

8.  docs/process/PHASE-3-GATE-REPORT.md

9.  docs/process/OPENCLAW-GATEWAY-RESEARCH-WU-051.md

10. docs/architecture/OPENCLAW-GATEWAY-INTEGRATION-WU-052.md

```

A ordem tem propósito:

```text
contexto
→ continuidade
→ arquitetura
→ design
→ disciplina de desenvolvimento
→ plano da fase
→ evidência do gate
→ pesquisa OpenClaw
→ implementação OpenClaw
→ continuidade versionada
```

Não substituir essa sequência por leitura aleatória quando o objetivo for
retomar o desenvolvimento.

Consultar documentos adicionais somente quando a tarefa exigir.

Não ler todo o legado por padrão.


---

### Protocolo de inicialização de novo chat

Este documento deve ser tratado como o **primeiro documento operacional de retomada**.

Ao receber este arquivo em um novo chat:

1. Leia este documento integralmente.
2. Leia os documentos indicados na seção **Ordem de leitura obrigatória para retomada**.
3. Não implemente, altere arquivos ou proponha mudanças arquiteturais antes de concluir a leitura e reconstruir o estado atual.
4. Ao terminar a leitura, apresente um **checkpoint de entendimento** contendo:
   - objetivo atual do projeto;
   - estado das fases;
   - arquitetura vigente;
   - decisões consolidadas relevantes;
   - evidências de implementação/validação;
   - pendências abertas;
   - próximo Work Unit ou próximo gate;
   - documentos que sustentam cada conclusão.
5. Se houver conflito entre documentos, não escolha silenciosamente. Identifique a fonte, compare autoridade e evidência e destaque a divergência antes de propor uma alteração.
6. Trate números de testes, estado do Git, versões de runtime e outros estados operacionais como **evidência de snapshot**: confirme no clone atual antes de declarar que ainda são verdadeiros.
7. Não reabra uma decisão consolidada apenas porque ela poderia ser desenhada de outra forma. Reavalie-a somente diante de nova evidência, contradição, impacto desconhecido, mudança de contexto ou necessidade explícita.
8. Não avance automaticamente para o próximo Work Unit. Primeiro confirme que o trabalho anterior está realmente consolidado e identifique o próximo passo documentado.
9. Quando finalmente for necessário implementar, siga o ciclo do projeto:

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
→ atualizar documentação
→ versionar
→ prosseguir
```

O objetivo desta inicialização é:

```text
retomar
≠
reiniciar
```

---

# 5. Estado atual

```text
FASE 1 — IMPLEMENTAÇÃO DO NÚCLEO
✅ concluída

FASE 2 — EVOLUÇÃO OPERACIONAL
✅ concluída

FASE 3 — INTEGRAÇÃO REAL COM OPENCLAW
✅ compatibilidade de runtime validada

PRÓXIMO BLOCO
⏳ Runtime Event Monitoring

---

# 6. O que já foi implementado

O núcleo possui:

```text
Domain
Application
Infrastructure
Planning
Agent / Skill Analysis
Resource Selection
Delegation
Evaluation
Replanning
Continuity
Evidence
Learning Candidate
Failure / Recovery
Persistence boundary
Resume
Runtime boundary
OpenClaw adapter boundary
Telemetry boundary
Resource Policy
Governed Learning
CI / validation foundation
```

---

# 7. Arquitetura atual

Macro:

```text
Interface / Infrastructure
            ↓
        Application
            ↓
          Domain
```

Estilo:

```text
Clean Architecture
DDD
Ports & Adapters
SOLID / Clean Code
Deep Modules
Specification-Driven Development
Modular Monolith
```

O núcleo não deve depender diretamente de:

```text
OpenClaw
SDKs de providers
SQL
MCP
frameworks específicos
```

Quando existir um seam real:

```text
necessidade real
→ port
→ adapter
```

Não criar abstrações especulativas.

---

# 8. Fluxo operacional

O fluxo principal consolidado é:

```text
PROJECT
↓
UNDERSTAND
↓
STRUCTURE
↓
WORK UNITS
↓
CAPABILITIES
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
RESULT
↓
EVALUATION
↓
REPLANNING
↓
CONTINUITY / LEARNING
```

---

# 9. Replanning

Regra central:

```text
PLAN
→ EXECUTE
→ EVALUATE
→ NEW INFORMATION
→ REPLAN
→ NEW PLAN
```

Preservar o máximo possível do trabalho válido.

Não reiniciar o projeto inteiro para mudança localizada.

---

# 10. Resource Selection

Sempre raciocinar:

```text
need
→ Work Unit
→ capability
→ Skill
→ Agent
→ Model
→ Runtime
→ configuration
```

Não:

```text
available agent
→ inventar trabalho
```

Considerar:

```text
adequação
qualidade
risco
tempo
custo
latência
contexto
coordenação
retrabalho
```

---

# 11. Evaluation

Resultado recebido não significa resultado aceito.

A avaliação pode considerar:

```text
correção
completude
coerência
aderência
restrições
suficiência
evidência
rastreabilidade
dependências
risco
impacto
necessidade de revisão
```

A profundidade é proporcional ao impacto e à criticidade.

---

# 12. Continuity vs Learning

Separar:

```text
CONTINUITY
→ preservar estado e histórico necessário

LEARNING
→ extrair conhecimento útil para decisões futuras
```

Experiência não vira regra automaticamente.

```text
LearningCandidate
→ validação
→ governança
→ eventual promoção
```

---

# 13. Estado da integração OpenClaw

A integração real foi validada.

```text
AgentRuntime
↓
OpenClawAdapter
↓
OpenClawGatewayClient
↓
Gateway WebSocket / RPC
↓
agent
↓
agent.wait
↓
chat.history
↓
assistant text
```

Métodos concretamente utilizados:

```text
connect
agent
agent.wait
chat.history
sessions.abort
```

Contrato de sessão:

```text
sessionKey = orchestrator:<task_id>
```

Semântica consolidada:

```text
agent.wait timeout
→ RUNNING para get_status()

agent.wait ok
→ conclusão

chat.history
→ fonte do texto final

thinking blocks
→ não são output
```

Validação real:

```text
OpenClaw real                 ✅
Gateway / WebSocket           ✅
protocol v4                   ✅
agent main                   ✅
Codex runtime                 ✅
openai/gpt-5.5                ✅
real execution                ✅
real final text               ✅
ORCHESTRATOR_GATEWAY_OK       ✅
207 tests passed              ✅
```

Descobertas importantes:

```text
catalog model ≠ executable model
runtime authorization ≠ resource selection
provider/model override pode ser rejeitado pelo runtime
```

O `gpt-5.5` foi o modelo efetivamente validado neste ambiente.

---

# 15. Pré-requisitos externos

A integração real depende de:

```text
OpenClaw instalado
versão identificada
Gateway disponível
autorização configurada
modelo/provider funcional
```

Se algum desses elementos faltar:

```text
não inventar
→ identificar bloqueio
→ pesquisar/validar
→ registrar
→ continuar pelo trabalho que puder ser feito com segurança
```

---

# 16. Validação

A Fase 2 foi validada historicamente no snapshot usado na sua consolidação.

A evidência mais recente da integração OpenClaw registrada neste contexto é:

```text
207 tests passed
real OpenClaw Gateway compatibility: PASS
real output: ORCHESTRATOR_GATEWAY_OK
```

Esses números são evidências de snapshots distintos e não devem ser misturados.

Ao retomar em outro ambiente, executar novamente:

```text
PYTHONPATH=src python -m pytest tests
```

e:

```text
PYTHONPATH=src python scripts/validate.py
```

A saída do ambiente atual é a evidência autoritativa para o estado efetivamente presente no clone.

---

# 17. Regra de mudanças

Uma decisão consolidada só deve ser revisada quando existir:

```text
nova evidência
contradição
impacto anteriormente desconhecido
mudança significativa de contexto
necessidade explícita
evolução técnica fundamentada
```

Ao revisar:

```text
decisão atual
→ motivo da revisão
→ evidências
→ alternativas
→ impacto
→ recomendação
→ decisão
→ atualização documental
→ versionamento
```

Não alterar silenciosamente.

---

# 18. Regra de análise proporcional

Começar pelo menor escopo suficiente:

```text
LOCAL
→ CONTEXTUAL
→ GLOBAL
```

Aumentar a abrangência quando impacto, risco, dependências ou natureza da mudança exigirem.

---

# 19. Regra de autonomia

Resolver autonomamente quando:

```text
evidência suficiente
+
baixo impacto
+
autoridade suficiente
+
reversibilidade adequada
```

Perguntar quando houver:

```text
ambiguidade material
conflito
impacto desconhecido
decisão fora da autoridade
bloqueio real
```

Quando perguntar, apresentar:

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

# 20. Regra contra reinicialização

O novo chat NÃO deve:

```text
reconstruir arquitetura
recomeçar requisitos
ignorar implementação existente
ignorar o Design vigente
misturar legado com o Orchestrator
tratar hipótese como decisão
```

Deve:

```text
ler
→ verificar
→ confirmar estado
→ continuar
```

---

# 21. Git

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

Não fazer commit sem antes verificar testes e diff.

---

# 22. Ponto exato de retomada

```text
FASE 3 — compatibilidade real com OpenClaw: VALIDADA

207 testes: PASS

Próximo trabalho:
Runtime Event Monitoring
```

Antes de iniciar:

```text
ler ORCHESTRATOR-DEVELOPMENT-CONTINUITY.md
ler ORCHESTRATOR-SYSTEM-DESIGN.md
ler PHASE-3-GATE-REPORT.md
```

Depois:

```text
propor
→ pesquisar se necessário
→ testar
→ consolidar
→ implementar
→ verificar
→ documentar
→ versionar
```

---

# 23. Regra final

Este documento indica:

> **onde o projeto está.**

Os documentos especializados indicam:

> **o que o projeto define.**

Em caso de conflito:

```text
identificar fonte
→ verificar autoridade
→ avaliar impacto
→ não decidir silenciosamente
```

O objetivo de um novo chat é:

> **retomar o projeto do ponto registrado, não reconstruí-lo.**
