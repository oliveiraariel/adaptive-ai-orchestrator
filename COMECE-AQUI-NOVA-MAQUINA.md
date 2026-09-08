# 🚀 NOVA MÁQUINA — COMECE AQUI

Você **não precisa lembrar nenhum dos comandos usados para montar o ambiente manualmente**.

A fonte de verdade é este repositório.

## O único que você precisa lembrar

Meu ambiente **Adaptive + OpenClaw** está documentado no repositório:

`oliveiraariel/adaptive-ai-orchestrator`

Se eu estiver em uma máquina nova, **não preciso lembrar dos comandos de instalação**.

Posso simplesmente:

1. entrar no meu GitHub;
2. abrir `oliveiraariel/adaptive-ai-orchestrator`;
3. abrir `COMECE-AQUI-NOVA-MAQUINA.md`;
4. seguir a instrução exibida aqui.

Se estiver usando uma IA, basta dizer:

> Abra meu repositório `oliveiraariel/adaptive-ai-orchestrator`, leia `COMECE-AQUI-NOVA-MAQUINA.md`, `bootstrap/README.md`, `bootstrap/TROUBLESHOOTING.md` e `bootstrap/RECOVERY-PROMPT.md` e reconstrua meu ambiente seguindo o bootstrap versionado. Não improvise uma configuração paralela e não exponha credenciais.

Depois de instalado, preciso lembrar apenas de três conceitos:

```text
Setup  → instalar ou reparar
Update → atualizar tudo com segurança
Verify → verificar se tudo continua funcionando
```

Comandos correspondentes:

```text
adaptive-openclaw-setup
adaptive-openclaw-update
adaptive-openclaw-verify
```

O bootstrap também cria atalhos gráficos correspondentes no Linux.

## Opção recomendada: um único comando

Em uma máquina Linux Mint / Ubuntu / Debian compatível, abra um terminal e cole:

```bash
curl -fsSL https://raw.githubusercontent.com/oliveiraariel/adaptive-ai-orchestrator/main/install.sh | bash
```

O instalador cuida do restante.

Ele reconstrói o ambiente com:

- Adaptive AI Orchestrator;
- Ariel Agent Skills;
- ambiente Python e `.venv`;
- dependências de teste e Gateway;
- OpenClaw, quando ainda não estiver instalado;
- configuração do catálogo de skills;
- `adaptive-orchestrator-bridge`;
- autenticação local do Gateway por SecretRef;
- serviço do Gateway;
- launchers de Setup / Update / Verify;
- persistência de `~/.local/bin` no PATH dos próximos shells;
- verificações e três testes E2E, incluindo multiagente paralelo e rota inbound pela bridge.

Os launchers são instalados **antes do último E2E**. Assim, se uma falha externa de modelo/runtime bloquear a validação final, o ambiente já possui uma rota estável de reparo.

## A única etapa que continua sendo sua

Em uma máquina realmente nova, o OpenClaw pode abrir o onboarding para que **você autentique sua própria conta/provedor de modelo** (por exemplo OpenAI).

Essa autenticação pessoal não fica no GitHub e não deve ser automatizada copiando credenciais entre máquinas.

Depois de concluir o login solicitado pelo OpenClaw, o bootstrap continua.

## Você nem precisa decorar o comando acima

No futuro, faça apenas isto:

1. entre no seu GitHub;
2. abra o repositório **`oliveiraariel/adaptive-ai-orchestrator`**;
3. abra este arquivo **`COMECE-AQUI-NOVA-MAQUINA.md`**;
4. copie o comando mostrado no início da página.

O `README.md` principal também mantém esse comando em destaque.

## Se estiver usando uma IA

Você pode entregar a ela somente esta instrução:

> Abra o repositório `oliveiraariel/adaptive-ai-orchestrator`, leia `COMECE-AQUI-NOVA-MAQUINA.md`, `bootstrap/README.md`, `bootstrap/TROUBLESHOOTING.md` e `bootstrap/RECOVERY-PROMPT.md`, e me ajude a reconstruir o ambiente seguindo exatamente o bootstrap versionado. Diagnostique a primeira camada que falhar; não reinstale componentes que já estejam funcionando e não exponha credenciais.

A IA deve usar o bootstrap como fonte de verdade, e não tentar reconstruir de memória os passos manuais.

## Depois que a instalação terminar

O bootstrap cria comandos e atalhos gráficos para a manutenção cotidiana:

```text
adaptive-openclaw-setup
adaptive-openclaw-update
adaptive-openclaw-verify
```

Use:

- **Setup** para instalar/reparar;
- **Update** para atualizar com segurança e executar a verificação completa automaticamente;
- **Verify** para comprovar a integração sem precisar atualizar antes.

### Se aparecer `comando não encontrado`

Antes de reinstalar qualquer coisa, confira se os launchers já existem:

```bash
ls -l ~/.local/bin/adaptive-openclaw-*
```

O bootstrap grava `~/.local/bin` nos arquivos de inicialização do shell, mas um processo instalador não consegue alterar o PATH de um terminal pai que já estava aberto.

Se os arquivos existirem, abra um novo terminal. Para usar imediatamente no mesmo terminal antigo:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Isso é um problema de descoberta pelo shell, não uma instalação ausente.

## Verificação completa

Quando quiser comprovar toda a integração:

```bash
adaptive-openclaw-verify
```

A validação comprova:

```text
E2E 1 — Adaptive → OpenClaw → Adaptive
E2E 2 — Adaptive → 3 workers paralelos → fan-in → Adaptive
E2E 3 — OpenClaw → bridge → Adaptive → workers paralelos → fan-in → OpenClaw
```

O E2E inbound é validado semanticamente. Variações de apresentação como `Max parallelism observed: 3` versus `max_parallelism_observed: 3` não devem mais gerar falso negativo quando o projeto realmente concluiu, o paralelismo exigido ocorreu e o fan-in foi comprovado.

## Se alguma verificação falhar

Abra [`bootstrap/TROUBLESHOOTING.md`](bootstrap/TROUBLESHOOTING.md) antes de modificar a máquina. A ordem é diagnosticar a primeira fronteira que falhou — PATH, Git, Python, configuração, Gateway, skill, outbound, multiagente ou inbound — e corrigir somente essa camada.

O objetivo é que a reconstrução futura dependa de **um ponto de entrada versionado e de diagnósticos reproduzíveis**, e não da memória do processo que foi feito originalmente.
