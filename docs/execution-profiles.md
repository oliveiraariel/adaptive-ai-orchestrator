# Perfis de execução do Adaptive (opt-in)

Sem uma preferência de operador configurada, o perfil de novas orquestrações
continua sendo `original`, preservando instalações existentes. Uma preferência
persistente pode definir outro perfil **como padrão de novas orquestrações**
sem modificar o conteúdo dos perfis e sem alterar projetos em andamento.
Cada perfil controla **separadamente** o modelo de
planejamento e o modelo executor, o nível de thinking, a política de fallback
de LLM por cota e o número de executores. A configuração é registrada no
checkpoint para retomada, sem alterar as variáveis globais.

## Nomes e regras

| Perfil solicitado | ID para CLI | Coordenador/planejador | Executor | Falta de cota | Falha na solução |
|---|---|---|---|---|---|
| Original | `original` | Configuração anterior | Configuração anterior | Política anterior | Política anterior |
| GPT-Terra-Medium-Low | `gpt-terra-medium-low` | `openai/gpt-5.6-terra`, medium | `openai/gpt-5.6-terra`, low | Somente Kimi K2.7; se ambos esgotarem, pausa | Fallback direto governado após esgotamento de estratégias |
| GPT-Luna-Medium-Low | `gpt-luna-medium-low` | `openai/gpt-5.6-luna`, medium | `openai/gpt-5.6-luna`, low; **1 por vez** | Nenhuma troca de LLM; pausa para retomada | Fallback direto governado após esgotamento de estratégias |
| GPT-Fallback-Direto | `gpt-fallback-direto` | `openai/gpt-5.6-terra`, medium | **O próprio agente coordenador**, Terra medium, sem subdelegação | Nenhuma troca de LLM; pausa | Sem novo fallback recursivo |
| Kimi-K3-K2.7 | `kimi-k3-k27` | `moonshot/kimi-k3` (thinking nativo do provedor) | `moonshot/kimi-k2.7-code` (thinking nativo) | Somente GPT Terra low; se ambos esgotarem, pausa | Fallback direto governado após esgotamento de estratégias |

Os três perfis não seriais usam concorrência `AUTO`, teto normal de
8 workers e reserva padrão de um slot em condição de *soft stall*. Esse teto
não determina quantos workers devem ser usados: o scheduler decide a fronteira
útil, respeitando dependências e conflitos de escrita.

**Não existe promoção automática de modelos após uma falha semântica.**
Troca automática de LLM é autorizada somente para incidentes classificados
como `quota` ou `rate_limit` com uma rota secundária explícita.
A cadeia de cada perfil é fechada: **sem fallback implícito para Laguna,
Kimi ou outro modelo fora da lista**.

Se o modelo secundário também ficar sem limite, a Work Unit é registrada como
`BLOCKED/RETURNED` com motivo
`PROFILE_MODEL_CAPACITY_EXHAUSTED`; o projeto solicita pausa durável,
não despacha novas WUs e pode ser retomado de maneira governada após restaurar
o limite. Outros workers já em atividade podem terminar antes da quiescência.
O estado `PAUSED` não significa que a cota tenha se renovado.

## Política de perfil padrão com autorização humana

A seleção automática pode ser configurada **uma vez** por operador, sem
repetir o nome do perfil em todos os prompts. A configuração fica em
`~/.config/adaptive-ai-orchestrator/execution-profile-selection.json`
(ou `ADAPTIVE_EXECUTION_PROFILE_SELECTION_FILE`) e é escrita com permissão
`0600`. Sem esse arquivo, o padrão continua `original`.

```bash
# Consultar o padrão real, sem alterar nada:
adaptive-orchestrator execution-profile default

# Configuração única, explicitamente autorizada pelo operador:
adaptive-orchestrator execution-profile set-default gpt-luna-medium-low \
  --authorize --actor user --reason "Usar Luna medium/low nas novas orquestrações"

# Confirmar:
adaptive-orchestrator execution-profile default
adaptive-orchestrator execution-profile list
```

Após a ativação, `adaptive-orchestrator orchestrate` (inclusive via Bridge)
**sem** `--execution-profile` aplica automaticamente
`gpt-luna-medium-low`: coordenador Luna medium, executor Luna low,
`FIXED=1`, sem overflow e sem fallback de troca de LLM.
A escolha efetiva é persistida no snapshot do checkpoint. Em `plan-only`
e no resultado da nova orquestração também aparece `execution_profile`.

## Papéis persistentes de agente

Perfis com `quality_direct_fallback=true` resolvem os papéis antes da admissão.
O Adaptive lê os agentes elegíveis de `~/.openclaw/openclaw.json` (ou de
`ADAPTIVE_OPENCLAW_CONFIG_FILE`) e usa a política persistente em
`~/.config/adaptive-ai-orchestrator/agent-role-selection.json` (ou em
`ADAPTIVE_AGENT_ROLE_SELECTION_FILE`). Configure uma vez, sem alterar o
perfil nem os snapshots existentes:

```bash
adaptive-orchestrator agent-roles set-default \
  --planner adaptive --worker main --authorize --actor user \
  --reason "Coordenador Adaptive e executor Main para novas orquestrações"
adaptive-orchestrator agent-roles default
```

Os IDs são validados contra `agents.entries`, e o Adaptive rejeita identidades
ausentes, inelegíveis ou iguais quando o perfil exige separação. Argumentos
explícitos válidos continuam prevalecendo; a conversa que iniciou a solicitação
não altera automaticamente os papéis.

A seleção de **outro** perfil para uma nova orquestração passa a exigir
autorização explícita e motivo atribuído a um operador:

```bash
adaptive-orchestrator orchestrate \
  --project-root "/caminho/projeto" \
  --agent main \
  --objective "Objetivo autorizado" \
  --execution-profile gpt-terra-medium-low \
  --authorize-profile-override \
  --profile-override-actor user \
  --profile-override-reason "O usuário pediu explicitamente outro perfil"
```

Essas flags são uma **declaração auditável de autorização**, não uma
identificação criptográfica da pessoa. O agente OpenClaw/Bridge só deve
encaminhá-las quando houver pedido humano real, e nunca para contornar
limites de cota ou erros semânticos. Sem autorização, o Adaptive recusa o
despacho **antes** de admitir a nova orquestração.

A política não altera definições dos perfis existentes, nem snapshots de
orquestrações já admitidas. `resume-project` continua com o perfil persistido;
`switch-execution-profile` mantém sua própria autorização governada.
Modificar novamente o padrão exige novo `set-default ... --authorize`.

## "Fallback direto" e "takeover direto"

- **Fallback direto**: termo apresentado ao usuário para o coordenador assumir
  a Work Unit com suas próprias skills, sem chamar novamente a Bridge.
- **Takeover governado, modo `direct`**: termo interno para a transferência
  protegida da Work Unit, preservando o histórico e impedindo dois escritores.
- Perfil `gpt-fallback-direto`: execução *desde o início* por sessões do agente
  coordenador, sem despachar a outro agente. O coordenador continua sujeito ao
  contrato de Work Units, claims, avaliação e Result Store.
- A passagem por falta de qualidade só é solicitada quando o orçamento de
  estratégias de resolução se esgota; para os perfis que a permitem, os papéis
  distintos são resolvidos pela política persistente de agentes.
  Projetos com autonomia que exige revisão/aprovação seguem essas garantias.
- **Falta de tokens não deve iniciar fallback direto para contornar a cota.**

A operação em curso pode demorar até o runtime confirmar que o executor
anterior foi encerrado. Uma solicitação de takeover é uma intenção,
**não** prova de cancelamento nem de execução já concluída.

## Comandos

```bash
adaptive-orchestrator execution-profile list
adaptive-orchestrator execution-profile show gpt-terra-medium-low
adaptive-orchestrator execution-profile show gpt-luna-medium-low

# Iniciar nova orquestração governada:
adaptive-orchestrator orchestrate \
  --project-root "/caminho/projeto" \
  --execution-profile gpt-luna-medium-low \
  --allow-side-effect filesystem.write \
  --objective "Executar o plano aprovado"
```

A Bridge existente pode encaminhar `--execution-profile` ao comando
`orchestrate` quando usa `--multi-agent` ou
`--durable-single-worker`. Para perfis seriais, opte por
`--durable-single-worker`; para perfis paralelos, use
`--multi-agent` e deixe o scheduler controlar o número útil de WUs.

### Fallback direto para uma Work Unit

```bash
adaptive-orchestrator fallback-direto \
  --orchestration-id ID \
  --project-root "/caminho/projeto" \
  --work-unit-id WU-ID \
  --owner-agent adaptive \
  --actor usuario \
  --reason "Assumir esta tarefa diretamente" \
  --authorize
```

### Fallback direto para todas as tarefas pendentes

```bash
adaptive-orchestrator fallback-direto \
  --orchestration-id ID \
  --project-root "/caminho/projeto" \
  --all-pending \
  --owner-agent adaptive \
  --actor usuario \
  --reason "Assumir tarefas pendentes diretamente" \
  --authorize
```

Os comandos não alteram tarefas `COMPLETED`/`CANCELLED`, nem tarefas
`HUMAN_ACTION`. Criam intenções duráveis e idempotentes. O controller
faz a transição após confirmar a situação do executor anterior.
Para a opção `--all-pending`, todas as WUs já **planejadas e elegíveis**
são incluídas; tarefas que só forem criadas em replanning posterior não
são automaticamente incluídas na lista anterior.

### Trocar de perfil durante um projeto

Para trocar de modelo, thinking, ou modo do **projeto** existente, primeiro
solicite `pause-project` e confirme estado `PAUSED`, zero workers ativos e
control-plane `QUIESCENT`. Depois:

```bash
adaptive-orchestrator switch-execution-profile \
  --orchestration-id ID \
  --project-root "/caminho/projeto" \
  --execution-profile gpt-luna-medium-low \
  --actor usuario \
  --reason "Alterar orçamento de execução" \
  --authorize

adaptive-orchestrator resume-project \
  --orchestration-id ID --project-root "/caminho/projeto"
```

Essa alteração é explícita, mantém o ID e histórico da orquestração,
registra autor/motivo/perfil anterior e vale somente após a retomada.
Alterações em um perfil salvo não modificam silenciosamente o snapshot
de uma orquestração ativa. Projetos terminados exigem
`continue-project`, não mutação de checkpoint histórico.

## Perfis personalizados

Crie um arquivo JSON com os campos abaixo (exemplo):

```json
{
  "name": "meu-perfil",
  "planner_model": "openai/gpt-5.6-terra",
  "planner_thinking": "medium",
  "planner_fallback_models": ["moonshot/kimi-k2.7-code"],
  "worker_model": "openai/gpt-5.6-terra",
  "worker_thinking": "low",
  "worker_fallback_models": ["moonshot/kimi-k2.7-code"],
  "quality_direct_fallback": true,
  "direct_owner_mode": false,
  "concurrency_mode": "FIXED",
  "max_concurrency": 2,
  "worker_stall_overflow_slots": 0,
  "direct_takeover": "manual"
}
```

```bash
adaptive-orchestrator execution-profile save --file meu-perfil.json
adaptive-orchestrator execution-profile show meu-perfil
adaptive-orchestrator execution-profile delete meu-perfil
```

Os perfis antigos `economy-serial`, `quality-parallel` e
`governed-direct` continuam reconhecidos como compatibilidade dos primeiros
testes, mas para as novas regras use os quatro identificadores acima.
O registro customizado usa arquivo restrito `0600` e gravação atômica em
`~/.config/adaptive-ai-orchestrator/execution-profiles.json` (caminho
opcional `ADAPTIVE_EXECUTION_PROFILES_FILE`).

## Autorizações, riscos e implantação

- É obrigatório configurar autenticação real via OpenClaw. Perfis GPT exigem
  `ADAPTIVE_OPENAI_OAUTH_PROFILE`. Os perfis Kimi exigem um provedor
  Moonshot disponível e com crédito válido.
- A seleção explícita do perfil `kimi-k3-k27` libera **apenas nesse runtime**
  o Kimi K3, que é excluído da rota automática original. Isso é uma seleção
  manual de modelo que pode incorrer em cobrança; o custo real depende do provedor.
- Nenhum perfil concede escrita, commit, push, merge, deploy, credenciais,
  ampliação de orçamento ou permissão de takeover não solicitada.
- Modelos e identificadores mencionados precisam existir no catálogo real do
  OpenClaw. Testes de CI não validam disponibilidade real nem limite de tokens.
- O Control Room poderá exibir o perfil selecionado em uma evolução separada.
- A CLI usa IDs de perfil em minúsculas e sem espaços, mas os nomes de exibição
  podem usar as formas GPT-Terra-Medium-Low etc.
- Nenhuma mudança de perfis entra em operação sem integração/instalação
  expressamente autorizada.

## Contratos de teste

São exigidos testes de resolução das quatro políticas, proibição de fallback
não autorizado, histórico das trocas, isolamento de checkpoints, pausa em
exaustão de cota, takeover individual e coletivo, planner/worker com thinking
diferente e demonstração de que `original` continua compatível.
Um teste integrado OpenClaw com cotas reais depende de implantação futura.
