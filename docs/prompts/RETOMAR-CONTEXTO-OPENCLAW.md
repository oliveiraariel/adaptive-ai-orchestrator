# Prompt básico — retomada de contexto no OpenClaw

Use este modelo para abrir uma nova janela/sessão do OpenClaw e reconstruir o estado de desenvolvimento sem transformar uma simples retomada de contexto em nova execução de projeto.

Este é um **baseline genérico**. Dependendo do projeto, da fase, do risco e da governança existente, ele pode ser **menor** ou **bem mais detalhado**. Quando houver prompt específico do projeto, ele deve complementar ou prevalecer sobre este modelo genérico.

## Prompt

```text
Retome o contexto de desenvolvimento deste projeto em modo somente leitura.

Antes de executar qualquer trabalho novo:

1. Leia primeiro o handoff canônico definido pelo projeto. Se não houver convenção explícita e existir `HANDOFF.md`, use-o como ponto inicial.
2. A partir dele, leia apenas os arquivos necessários para entender o estado atual. Se existirem arquivos como `AGENTS.md`, `ORCHESTRATOR.md`, manifesto do projeto, documentação da etapa atual, requisitos ou arquitetura, consulte somente o que for relevante para a retomada.
3. Confirme a branch atual, `git status` e o WIP existente.
4. Se o projeto usar Adaptive e houver uma orquestração já conhecida, consulte somente seu estado autoritativo/checkpoint. Não crie, retome ou substitua uma orquestração apenas para reconstruir contexto.
5. Não descarte, resete, faça stash, clean ou sobrescreva WIP.
6. Não edite arquivos, não rode implementação/testes, não faça commit, push, merge ou deploy durante esta retomada.
7. Não crie Work Unit, worker, precheck ou nova orquestração para uma tarefa que é apenas leitura de contexto.
8. Não invente estado ausente e não trate mensagens antigas da conversa como mais autoritativas que os arquivos e estados operacionais atuais.

Comece respondendo somente com um resumo curto contendo:
- estado atual;
- fase/etapa em andamento;
- branch e WIP relevante;
- principal pendência ou blocker conhecido;
- próximo passo seguro;
- fontes principais consultadas.

Depois aguarde meu próximo comando.
```

## Ajuste de tamanho

Este modelo deve permanecer pequeno por padrão. Ele pode ser reduzido quando o contexto já estiver praticamente carregado ou ampliado quando a retomada envolver múltiplos repositórios, incidentes, release, migração, ambientes externos, regras de segurança, Work Graph ativo, decisões arquiteturais ou outras obrigações específicas do projeto.
