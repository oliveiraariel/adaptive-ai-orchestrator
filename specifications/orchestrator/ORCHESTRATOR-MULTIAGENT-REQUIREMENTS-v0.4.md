# ORCHESTRATOR — MULTIAGENT REQUIREMENTS v0.4

**Projeto:** Adaptive AI Orchestrator  
**Status:** suplemento normativo vigente de `ORCHESTRATOR-REQUIREMENTS.md`  
**Escopo:** execução automática multi-Work-Unit, concorrência lateral contínua, fan-out/fan-in, segurança de workspace e economicidade

## 1. Relação normativa

Este documento **não substitui** `ORCHESTRATOR-REQUIREMENTS.md`. Ele o especializa para a capacidade multiagente operacional introduzida na v0.4.

Em caso de aparente conflito:

1. `PROJECT-DEFINITION.md` continua definindo identidade/escopo do sistema;
2. `ORCHESTRATOR-REQUIREMENTS.md` mantém os requisitos gerais;
3. este suplemento define os requisitos mais específicos da operação multiagente v0.4;
4. arquitetura/código/testes devem implementar estes requisitos sem ampliar autoridade.

## 2. Requisitos funcionais adicionais

### RF-ORC-061 — Manter Ready Frontier dinâmica

O Orchestrator deve calcular o conjunto de Work Units atualmente elegíveis a partir de estado, dependências, políticas e disponibilidade operacional.

**Critério de aceitação:** uma Work Unit bloqueada por dependência obrigatória não integra a frontier; quando a dependência é aceita e satisfeita, a Work Unit torna-se elegível sem exigir reconstrução manual do plano.

---

### RF-ORC-062 — Executar trabalho independente em paralelo

O Orchestrator deve poder delegar simultaneamente múltiplas Work Units independentes quando isso for seguro, útil e permitido pelo orçamento de concorrência.

O paralelismo não depende de camada técnica. São combinações válidas, conforme o grafo:

```text
backend + backend
frontend + frontend
backend + frontend
implementação + teste
pesquisa + pesquisa
outras combinações independentes
```

**Critério de aceitação:** um plano com seis Work Units independentes e `max_concurrency >= 6` pode alcançar seis execuções simultaneamente ativas, sem tornar seis agentes uma meta obrigatória.

---

### RF-ORC-063 — Repor continuamente slots liberados

O Orchestrator não deve aguardar a conclusão de todos os workers despachados conjuntamente para aproveitar capacidade liberada.

Quando uma execução termina, seu resultado deve ser avaliado e, se aceito, suas dependências devem ser avançadas. Se isso tornar nova Work Unit elegível e existir slot livre, o novo worker pode iniciar enquanto execuções independentes anteriores continuam ativas.

**Critério de aceitação:** com dois workers A/B ativos, se A conclui e libera C enquanto B continua executando, C pode iniciar antes da conclusão de B.

---

### RF-ORC-064 — Aplicar limite global de concorrência

O Orchestrator deve manter o número de execuções delegadas simultaneamente ativas dentro do `max_concurrency` autorizado para a execução do projeto.

O limite deve considerar workers iniciados em dispatch generations anteriores e ainda ativos.

---

### RF-ORC-065 — Escalar workers conforme necessidade útil

O número de workers deve emergir da Ready Frontier útil, de dependências, risco, recursos, política e custo; não de uma quantidade fixa ou objetivo artificial de paralelismo.

O Orchestrator deve poder operar com 1, 2, 3, 4, 6 ou mais workers dentro do limite configurado quando o benefício for justificável.

---

### RF-ORC-066 — Preservar identidade exclusiva de tentativa

Cada tentativa de execução de uma Work Unit deve possuir identidade de task/execution suficientemente distinta para impedir colisão de sessão, claim ou chave de idempotência, inclusive em terceiro ou posterior retry.

---

### RF-ORC-067 — Realizar fan-in apenas a partir de resultados aceitos

Quando uma Work Unit depende de múltiplos produtores, o Orchestrator deve disponibilizar ao consumidor somente resultados que já tenham atravessado a avaliação aplicável.

Uma conclusão de runtime não equivale a conclusão semântica e não deve, por si só, satisfazer dependências.

---

### RF-ORC-068 — Propagar contexto de dependência de forma limitada

Resultados aceitos necessários a Work Units dependentes devem poder ser propagados por contexto ou ponteiro autoritativo, respeitando orçamento de contexto e evitando duplicação desnecessária.

---

### RF-ORC-069 — Coordenar escrita concorrente em workspace compartilhado

Quando workers compartilham o mesmo checkout/workspace e não existe isolamento mais forte fornecido pelo runtime, o Orchestrator deve impedir escrita concorrente com ownership desconhecido ou sobreposto.

Para `filesystem.write`:

- o plano deve declarar `write_paths` literais e relativos ao repositório;
- paths absolutos, traversal `..`, globs ou ausência de escopo devem ser rejeitados;
- escopos iguais ou parent/child devem ser considerados sobrepostos;
- escopos disjuntos podem compartilhar execução quando as demais políticas permitirem;
- conflitos devem ser comparados também com workers já ativos, não somente com os selecionados no mesmo dispatch.

---

### RF-ORC-070 — Preservar limite de autoridade por Work Unit

Um worker deve receber objetivo, escopo, contexto, ferramentas, side effects e restrições limitados à sua Work Unit.

Um worker não deve criar autonomamente nova orquestração Adaptive, ampliar seu próprio escopo ou aumentar autoridade herdada.

---

### RF-ORC-071 — Replanejar de forma aditiva e limitada

Quando trabalho genuinamente necessário não representado no grafo for descoberto, o Orchestrator deve poder executar replanning limitado.

Na v0.4:

- apenas resultado aceito pode solicitar replan;
- o número de invocações de replan deve ser limitado;
- Work Units existentes não devem ser silenciosamente renomeadas/redefinidas;
- novas unidades/edges devem manter o grafo válido e acíclico;
- um requisito obrigatório novo não pode ser anexado retroativamente a uma Work Unit já iniciada/concluída;
- execução válida já concluída deve ser preservada.

---

### RF-ORC-072 — Estabilizar o grafo antes de replanning

Ao surgir sinal de replanning enquanto existem workers ativos, o Orchestrator deve impedir novos dispatches e atingir um estado consistente antes de mutar o grafo, salvo se futura estratégia transacional/isolation provar segurança equivalente.

Na implementação v0.4, esse estado consistente é obtido drenando as execuções já ativas antes do replan.

---

### RF-ORC-073 — Representar trabalho humano sem agente fictício

Uma ação que dependa genuinamente de autoridade/execução humana deve ser representada como `HUMAN_ACTION` e não deve ser despachada a runtime de agente apenas para manter o grafo em movimento.

## 3. Requisitos não funcionais adicionais

### RNF-ORC-029 — Concorrência bounded-by-policy

A escalabilidade operacional deve ser configurável e limitada. Paralelismo ilimitado não é requisito e não é comportamento permitido por padrão.

### RNF-ORC-030 — Economicidade de coordenação

A decomposição deve evitar micro-Work-Units cujo custo de contexto, criação de sessão, sincronização e avaliação seja maior que o ganho de especialização/paralelismo.

### RNF-ORC-031 — Segurança de concorrência

Quando não houver sandbox/worktree/container por worker, a estratégia de concorrência deve adotar fail-closed para ownership de escrita ambíguo.

### RNF-ORC-032 — Reatividade operacional

A disponibilidade de um slot de execução deve poder ser reaproveitada após a conclusão/aceitação relevante sem depender do término de workers independentes ainda ativos.

### RNF-ORC-033 — Testabilidade de concorrência

A suíte deve demonstrar não apenas o número de workers despachados, mas também comportamento temporal observável: slot replenishment, fan-in, conflito de escrita, retries e bounded replanning.

### RNF-ORC-034 — CI fail-closed

Falhas de compilação, coleta ou testes não podem ser ocultadas por pipelines de diagnóstico (`tee`, upload de artefatos ou similares). Dependências necessárias aos testes de integração devem estar instaladas no job correspondente.

## 4. Regras de orquestração adicionais

### RO-021 — Paralelismo exige independência real

Não serializar por hábito, mas também não paralelizar por estética. A pergunta é se as Work Units podem produzir resultados corretos e seguros simultaneamente.

### RO-022 — Slot livre deve ser reavaliado

Quando uma execução termina, o Orchestrator deve recalcular a frontier e a disponibilidade antes de aguardar workers não relacionados.

### RO-023 — Avaliação precede desbloqueio

```text
runtime result
→ avaliação
→ finalização
→ dependência satisfeita
→ nova elegibilidade
```

### RO-024 — Escrita concorrente ambígua é serializada

Na ausência de isolamento técnico mais forte, conflito/ambiguidade de write scope prevalece sobre ganho de paralelismo.

### RO-025 — Quantidade de agentes não é KPI

`max_concurrency` é teto, não meta. Economicidade, qualidade, latência, contexto, risco e retrabalho definem a escala útil.

### RO-026 — Replanning não corre por baixo de workers

A v0.4 não modifica dependências obrigatórias enquanto Work Units potencialmente afetadas permanecem em execução. O scheduler estabiliza o estado antes da mutação do grafo.

## 5. Critério de aceitação da capacidade multiagente

A capacidade é considerada implementada em nível de código/CI quando houver evidência automatizada de:

- DAG e endpoints válidos;
- Ready Frontier dinâmica;
- 2+ workers simultâneos;
- escala demonstrada até pelo menos 6 workers em cenário controlado;
- frontend/backend lateral quando independentes;
- backend/backend e frontend/frontend permitidos pelo mesmo modelo;
- slot liberado preenchido antes do fim de worker independente ainda ativo;
- fan-in de resultados aceitos;
- side effect negado antes do runtime;
- write scopes perigosos rejeitados;
- writes sobrepostos serializados, inclusive contra worker já ativo;
- writes disjuntos paralelos;
- retry limitado e identidades de tentativa distintas;
- `HUMAN_ACTION` não delegado;
- replanning aditivo, limitado e revalidado;
- CI que falha de fato quando pytest falha.

A capacidade só é considerada validada **na instalação local OpenClaw específica** após E2E real multi-session pelo Gateway daquela máquina. A aprovação em CI não substitui esse teste operacional local.
