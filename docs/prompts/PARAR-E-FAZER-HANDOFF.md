# Prompt curto — parar e fazer handoff

Use este prompt quando quiser encerrar uma sessão de trabalho de forma controlada, preservando continuidade sem iniciar uma nova unidade.

## Prompt

```text
Pare ao concluir a unidade atômica de trabalho atualmente em andamento.

Não inicie uma nova unidade.

Use `project-handoff` para consolidar a continuidade desta sessão.

Entregue:
- objetivo desta sessão;
- estado atual do projeto e da unidade em andamento;
- trabalho concluído;
- arquivos, commits, PRs, issues ou artefatos modificados;
- testes, verificações e revisões executados;
- decisões tomadas e respectivas fontes;
- blockers;
- riscos ou incertezas restantes;
- pendências deliberadamente não executadas;
- próximo trabalho executável;
- skills/capacidades recomendadas para a próxima sessão.

Não copie documentação grande para o handoff. Referencie fontes de verdade por
caminho, URL, commit, issue, PR ou identificador quando possível.

Não exponha credenciais, secrets, tokens, dados pessoais ou contexto sensível
desnecessário.

O handoff deve permitir que uma nova sessão ou agente retome o trabalho sem
repetir discovery já concluído e sem depender da memória desta conversa.
```

## Como chamar este prompt no OpenClaw

> Leia `docs/prompts/PARAR-E-FAZER-HANDOFF.md` no repositório `oliveiraariel/adaptive-ai-orchestrator` e encerre a sessão conforme esse contrato.
