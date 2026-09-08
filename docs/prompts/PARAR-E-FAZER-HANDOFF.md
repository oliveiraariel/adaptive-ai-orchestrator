# Prompt curto — parar e fazer handoff

Use este prompt quando quiser encerrar uma sessão de trabalho de forma controlada, preservando continuidade sem iniciar novas Work Units.

## Prompt

```text
Encerre esta sessão de forma controlada.

A partir deste pedido de parada, não reabasteça slots livres e não despache novas
Work Units. Se houver workers já ativos, permita que terminem ou atinjam um
blocker/timeout controlado, recolha seus resultados e faça a avaliação/finalização
correspondente. Não abandone worker ativo silenciosamente.

Não trate dispatch generation como uma wave/barreira: workers ativos podem ter
sido iniciados em generations diferentes. A regra de parada é simples: nenhum
novo dispatch após este ponto; apenas drenagem controlada das execuções já ativas.

Se um worker ativo devolver `ADAPTIVE_REPLAN_REQUIRED`, registre o sinal como
pendência no handoff, mas não inicie um novo ciclo de planejamento/execução depois
desta solicitação de encerramento, salvo se isso for indispensável apenas para
restaurar consistência do estado.

Use `project-handoff` para consolidar a continuidade desta sessão.

Entregue:
- objetivo desta sessão;
- estado atual do projeto e do Work Graph;
- Work Units concluídas, bloqueadas, revision-required ou ainda não iniciadas;
- dispatch generations relevantes e `max_parallelism_observed`, quando disponível;
- workers/resultados que participaram do último fan-out/fan-in;
- sinais de replan ainda não executados;
- arquivos, commits, PRs, issues ou artefatos modificados;
- testes, verificações e revisões executados;
- decisões tomadas e respectivas fontes;
- blockers;
- riscos ou incertezas restantes;
- pendências deliberadamente não executadas;
- ready frontier/next Work Units que seriam executáveis na próxima sessão;
- skills/capacidades recomendadas para a retomada.

Não copie documentação grande para o handoff. Referencie fontes de verdade por
caminho, URL, commit, issue, PR ou identificador quando possível.

Não exponha credenciais, secrets, tokens, dados pessoais ou contexto sensível
desnecessário.

O handoff deve permitir que uma nova sessão ou agente retome o trabalho sem
repetir discovery já concluído, sem depender da memória desta conversa e sem
perder a situação de dependências/fan-in deixada pela execução multiagente.
```

## Como chamar este prompt no OpenClaw

> Leia `docs/prompts/PARAR-E-FAZER-HANDOFF.md` no repositório `oliveiraariel/adaptive-ai-orchestrator` e encerre a sessão conforme esse contrato.
