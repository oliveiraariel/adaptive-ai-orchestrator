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

## Princípio operacional v0.4+

Trabalho de projeto não trivial deve entrar pelo modo multiagente do bridge:

```text
Usuário
  ↓
OpenClaw
  ↓
adaptive-orchestrator-bridge --multi-agent
  ↓
Adaptive AI Orchestrator / orchestrate
  ↓
Project discovery + planning
  ↓
validated Work Graph
  ↓
ready frontier
  ↓
dynamic logical workers + minimum skills
  ↓
parallel execution when safe
  ↓
primeiro resultado concluído
  ↓
evaluation/finalization + dependency advancement
  ↓
ready frontier recalculada
  ↓
slot liberado pode receber novo worker enquanto outros continuam
  ↓
fan-in / bounded replan quando necessário
  ↺
```

O usuário define **o objetivo e a autoridade**. O Adaptive organiza o trabalho. `engineering-lifecycle` e as demais skills são capacidades selecionadas por Work Unit; elas não substituem o scheduler/orchestrator.

O Adaptive não usa uma quantidade fixa de agentes. A frontier útil pode gerar 1, 2, 3, 4, 6 ou mais worker sessions dentro do limite configurado. A economicidade de tokens/contexto deve impedir microfragmentação e skills desnecessárias.

Paralelismo não depende de “ser frontend” ou “ser backend”. Backend/backend, frontend/frontend, frontend/backend e outras combinações podem ocorrer quando dependências reais estiverem satisfeitas. Contratos/interfaces estáveis são seams naturais para desbloquear trabalho lateral.

A execução de projeto é **continuamente reabastecida**, não baseada em barreiras artificiais de wave: quando um resultado aceito desbloqueia trabalho e existe slot compatível, o novo worker pode ser iniciado sem aguardar workers independentes ainda ativos. Os registros de `dispatch generation` servem para rastreabilidade, não como obrigação de término em grupo.

Em checkout compartilhado, toda Work Unit que solicita `filesystem.write` deve possuir `write_paths` literais, precisos e relativos ao repositório. Writes concorrentes só são elegíveis quando seus escopos não se sobrepõem, inclusive contra writers já ativos. O prompt não deve afirmar que há Git worktree/container isolation se o runtime não a forneceu.

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
- handoffs e fontes de continuidade;
- regras específicas para paralelismo e integração.

A partir daí, o prompt específico do projeto deve prevalecer sobre estes templates genéricos sempre que houver diferença de contexto ou governança.

## Como iniciar sem decorar o conteúdo

### Frontend

> Leia `docs/prompts/INICIAR-PROJETO-FRONTEND.md` no repositório `oliveiraariel/adaptive-ai-orchestrator` e use esse Prompt Mestre para iniciar este projeto. Meu objetivo é: [objetivo].

### Backend / Engineering

> Leia `docs/prompts/INICIAR-PROJETO-BACKEND.md` no repositório `oliveiraariel/adaptive-ai-orchestrator` e use esse Prompt Mestre para iniciar este projeto. Meu objetivo é: [objetivo].

### Continuar

> Leia `docs/prompts/CONTINUAR-PROJETO.md` e continue a partir do estado atual.

### Parar

> Leia `docs/prompts/PARAR-E-FAZER-HANDOFF.md` e encerre a sessão conforme esse contrato.

## Limite importante

Estes prompts não transformam automaticamente todo chat em trabalho orquestrado. Eles instruem explicitamente o OpenClaw a usar a bridge e o Adaptive para trabalho sério de projeto.

Perguntas simples, explicações conceituais e tarefas triviais podem continuar sendo respondidas diretamente quando não houver motivo para iniciar uma orquestração de projeto.
