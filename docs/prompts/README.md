# Prompts globais — OpenClaw + Adaptive AI Orchestrator

Este diretório concentra os **prompts mestres genéricos** para iniciar, continuar e encerrar trabalho de software através do OpenClaw usando o **Adaptive AI Orchestrator** como porta de entrada.

Eles são genéricos por projeto. Quando um repositório amadurecer e possuir governança, documentação, arquitetura, requisitos ou regras próprias, crie um prompt operacional específico dentro daquele projeto e prefira esse prompt local.

## Regra simples

```text
NOVO TRABALHO DE FRONTEND
→ INICIAR-PROJETO-FRONTEND.md

NOVO TRABALHO DE API / ALTERAÇÃO DE CONTRATO DE API
→ INICIAR-PROJETO-API.md

NOVO TRABALHO DE BACKEND / ENGINEERING
→ INICIAR-PROJETO-BACKEND.md

GERAR NOVO ZIP / PACOTE / ARTEFATO PARA RETESTE
→ GERAR-PACOTE-RETESTE.md

CONTINUAR UMA LINHA DE TRABALHO
→ CONTINUAR-PROJETO.md

PARAR E PRESERVAR CONTEXTO
→ PARAR-E-FAZER-HANDOFF.md
```

Não é necessário colar todos os prompts juntos.

## Padrão obrigatório de handoff

Salvo quando a governança do projeto declarar explicitamente outro caminho, o estado corrente deve ser mantido em um único arquivo canônico:

```text
HANDOFF.md
```

Esse arquivo é atualizado no lugar. Nomes datados ou descritivos não devem ser usados para representar o handoff corrente.

Snapshots históricos são opcionais. Quando forem realmente necessários e o projeto não possuir convenção própria, use:

```text
docs/governanca/handoffs/HANDOFF-YYYY-MM-DD-HHMM-<ESCOPO>.md
```

Snapshots devem ser marcados como históricos/não atuais e apontar para `HANDOFF.md`. A retomada sempre consulta primeiro o handoff canônico; não se determina a autoridade escolhendo o arquivo datado aparentemente mais recente. Handoffs legados usados como estado corrente devem ser normalizados para o caminho canônico sem perda de informação útil.

## Política obrigatória para APIs

Trabalho que cria uma API ou altera um contrato de API externamente observável deve obedecer a `ADAPTIVE_API_GENERATION_POLICY_V1`, independentemente de linguagem, framework, plataforma ou protocolo.

`INICIAR-PROJETO-API.md` é a entrada humana preferida para esse tipo de trabalho, mas **não é o único mecanismo de enforcement**. A política é aplicada no boundary comum de `TaskPackage`, para que uma Work Unit de API continue recebendo as obrigações mínimas mesmo quando o projeto entrou por outro prompt.

A política não força REST, HTTP, OpenAPI, JSON ou framework específico. Ela exige descoberta do contrato real, compatibilidade, segurança, verificação e fechamento/fan-in de forma proporcional ao protocolo e ao projeto. Consumo normal de API de terceiros ou rotação de API key não é automaticamente classificado como geração de API.

Detalhes: `docs/process/API-GENERATION-GOVERNANCE.md`.

## Política obrigatória para ZIPs e outros artefatos de release

Trabalho que cria ou regenera um pacote instalável/deployable deve obedecer a `ADAPTIVE_RELEASE_ARTIFACT_POLICY_V1`.

A política também é aplicada automaticamente no `TaskPackage`; portanto o operador não precisa repetir em cada prompt regras como "crie um ZIP novo", "não reutilize o antigo", "inclua apenas runtime", "exclua segredos/testes/cache", "teste o arquivo" e "calcule SHA-256".

Ela exige, de forma independente de stack:

- fonte exata e working tree identificados;
- gates locais aplicáveis executados contra o estado empacotado;
- artefato novo após fix/hotfix/reteste;
- composição runtime-only;
- estrutura instalável validada para a plataforma real;
- integridade do pacote e SHA-256;
- evidência source → artifact;
- distinção entre prontidão local e validação ambiental;
- nenhuma autorização implícita para merge/deploy/instalação/publicação.

`GERAR-PACOTE-RETESTE.md` é apenas um atalho humano. Com contexto já carregado, uma solicitação como **"Gere um novo ZIP para reteste ambiental"** deve ser suficiente para ativar a política.

Detalhes: `docs/process/RELEASE-ARTIFACT-GOVERNANCE.md`.

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

A partir daí, o prompt específico do projeto deve prevalecer sobre estes templates genéricos sempre que houver diferença de contexto ou governança. As políticas globais de API e artefato de release continuam funcionando como piso de engenharia; elas não devem sobrescrever fatos ou decisões canônicas do projeto.

## Como iniciar sem decorar o conteúdo

### Frontend

> Leia `docs/prompts/INICIAR-PROJETO-FRONTEND.md` no repositório `oliveiraariel/adaptive-ai-orchestrator` e use esse Prompt Mestre para iniciar este projeto. Meu objetivo é: [objetivo].

### API

> Leia `docs/prompts/INICIAR-PROJETO-API.md` no repositório `oliveiraariel/adaptive-ai-orchestrator` e use esse Prompt Mestre. Meu objetivo é: [objetivo].

### Backend / Engineering

> Leia `docs/prompts/INICIAR-PROJETO-BACKEND.md` no repositório `oliveiraariel/adaptive-ai-orchestrator` e use esse Prompt Mestre para iniciar este projeto. Meu objetivo é: [objetivo].

### Pacote para reteste

> Gere um novo ZIP para reteste ambiental.

Ou, quando quiser tornar a intenção explícita:

> Leia `docs/prompts/GERAR-PACOTE-RETESTE.md` e gere o novo artefato conforme esse contrato.

### Continuar

> Leia `docs/prompts/CONTINUAR-PROJETO.md` e continue a partir do estado atual.

### Parar

> Leia `docs/prompts/PARAR-E-FAZER-HANDOFF.md` e encerre a sessão conforme esse contrato.

## Limite importante

Estes prompts não transformam automaticamente todo chat em trabalho orquestrado. Eles instruem explicitamente o OpenClaw a usar a bridge e o Adaptive para trabalho sério de projeto.

Duas governanças mínimas são aplicadas automaticamente quando a Work Unit correspondente existe:

- criação/alteração de superfície de API → `ADAPTIVE_API_GENERATION_POLICY_V1`;
- criação/regeneração de artefato instalável/deployable → `ADAPTIVE_RELEASE_ARTIFACT_POLICY_V1`.

Perguntas simples, explicações conceituais e tarefas triviais podem continuar sendo respondidas diretamente quando não houver motivo para iniciar uma orquestração de projeto.
