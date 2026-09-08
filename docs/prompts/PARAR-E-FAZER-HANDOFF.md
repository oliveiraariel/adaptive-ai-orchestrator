# Prompt curto — parar e fazer handoff

Use este prompt quando quiser encerrar uma sessão de trabalho de forma controlada, preservando continuidade sem iniciar nova Work Unit/wave.

## Prompt

```text
Encerre esta sessão de forma controlada.

Se houver uma wave multiagente já em execução, aguarde os workers dessa wave
terminarem ou atingirem um blocker/timeout controlado, recolha seus resultados e
faça a avaliação/finalização correspondente.

Não despache uma nova wave e não inicie novas Work Units depois desse ponto.
Não abandone worker ativo silenciosamente.

Use `project-handoff` para consolidar a continuidade desta sessão.

Entregue:
- objetivo desta sessão;
- estado atual do projeto e do Work Graph;
- Work Units concluídas, bloqueadas, revision-required ou ainda não iniciadas;
- waves executadas e paralelismo observado quando relevante;
- workers/resultados que participaram do último fan-out/fan-in;
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
