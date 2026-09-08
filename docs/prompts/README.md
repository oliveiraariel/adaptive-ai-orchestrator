# Prompts globais — OpenClaw + Adaptive AI Orchestrator

Este diretório concentra os **prompts mestres genéricos** para iniciar, continuar e encerrar trabalho de software através do OpenClaw usando o **Adaptive AI Orchestrator** como porta de entrada.

Eles são genéricos por projeto. Quando um repositório amadurecer e possuir governança, documentação, arquitetura, requisitos ou regras próprias, crie um prompt operacional específico dentro daquele projeto e prefira esse prompt local.

## Regra simples

```text
NOVO TRABALHO DE FRONTEND
→ INICIAR-PROJETO-FRONTEND.md

NOVO TRABALHO DE BACKEND / ENGINEERING
→ INICIAR-PROJETO-BACKEND.md

CONTINUAR UMA LINHA DE TRABALHO
→ CONTINUAR-PROJETO.md

PARAR E PRESERVAR CONTEXTO
→ PARAR-E-FAZER-HANDOFF.md
```

Não é necessário colar todos os prompts juntos.

## Princípio operacional

```text
Usuário
  ↓
OpenClaw
  ↓
adaptive-orchestrator-bridge
  ↓
Adaptive AI Orchestrator
  ↓
engineering-lifecycle
  ↓
project-discovery, quando necessário
  ↓
skills especializadas necessárias
  ↓
execução / validação / handoff
```

O usuário define **o objetivo**. O Adaptive organiza o trabalho. O `engineering-lifecycle` ajuda a determinar o menor fluxo de engenharia suficiente. As skills especializadas são selecionadas conforme a necessidade real.

Não tente usar todas as skills manualmente em toda tarefa.

## Quando criar um prompt específico no próprio projeto

Os prompts deste diretório são o ponto de entrada para projetos novos, pouco documentados ou ainda sem governança própria.

Quando um projeto passar a possuir fontes de verdade e regras operacionais claras, é recomendado criar dentro dele algo como:

```text
PROMPTS-OPENCLAW-<PROJETO>.md
```

ou:

```text
docs/governanca/prompts-openclaw.md
```

Esse arquivo específico pode referenciar:

- documentos canônicos;
- requisitos e regras de negócio;
- arquitetura aprovada;
- stack e convenções;
- gates de desenvolvimento;
- limites de autoridade;
- regras de deploy/release;
- handoffs e fontes de continuidade.

A partir daí, o prompt específico do projeto deve prevalecer sobre estes templates genéricos sempre que houver diferença de contexto ou governança.

## Como iniciar sem decorar o conteúdo

No OpenClaw, você pode dizer apenas:

### Frontend

> Leia `docs/prompts/INICIAR-PROJETO-FRONTEND.md` no repositório `oliveiraariel/adaptive-ai-orchestrator` e use esse Prompt Mestre para iniciar este projeto. Meu objetivo é: [objetivo].

### Backend / Engineering

> Leia `docs/prompts/INICIAR-PROJETO-BACKEND.md` no repositório `oliveiraariel/adaptive-ai-orchestrator` e use esse Prompt Mestre para iniciar este projeto. Meu objetivo é: [objetivo].

### Continuar

> Leia `docs/prompts/CONTINUAR-PROJETO.md` e continue a partir do estado atual.

### Parar

> Leia `docs/prompts/PARAR-E-FAZER-HANDOFF.md` e encerre a sessão conforme esse contrato.

## Limite importante

Estes prompts não transformam automaticamente todo chat em trabalho orquestrado. Eles instruem explicitamente o OpenClaw a entrar pelo `adaptive-orchestrator-bridge` e delegar ao Adaptive.

Perguntas simples, explicações conceituais e tarefas triviais podem continuar sendo respondidas diretamente quando não houver motivo para usar o orchestrator.
