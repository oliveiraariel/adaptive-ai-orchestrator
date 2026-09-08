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

> Abra meu repositório `oliveiraariel/adaptive-ai-orchestrator`, leia `COMECE-AQUI-NOVA-MAQUINA.md` e `bootstrap/RECOVERY-PROMPT.md` e reconstrua meu ambiente seguindo o bootstrap versionado. Não improvise uma configuração paralela e não exponha credenciais.

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
- verificações e testes E2E;
- atalhos gráficos de Setup, Update e Verify.

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

> Abra o repositório `oliveiraariel/adaptive-ai-orchestrator`, leia `COMECE-AQUI-NOVA-MAQUINA.md` e `bootstrap/RECOVERY-PROMPT.md`, e me ajude a reconstruir o ambiente seguindo exatamente o bootstrap versionado. Não improvise uma configuração paralela e não exponha credenciais.

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
- **Update** para atualizar com segurança;
- **Verify** para comprovar que toda a integração continua operacional.

## Verificação completa

Quando quiser comprovar inclusive as duas direções da integração:

```bash
adaptive-openclaw-verify --e2e
```

O objetivo é que a reconstrução futura dependa de **um ponto de entrada versionado**, e não da memória do processo que foi feito originalmente.