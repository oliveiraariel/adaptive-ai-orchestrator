# Nova máquina — comece aqui

Este é o **ponto de entrada** para reconstruir o ambiente
**Adaptive AI Orchestrator + Ariel Agent Skills + OpenClaw**.
Abrir esta página no GitHub **não executa a instalação**.
O procedimento detalhado e as opções de recuperação ficam em
[`bootstrap/README.md`](bootstrap/README.md).

## Antes de começar

- Use Linux Mint, Ubuntu, Debian ou distribuição compatível com `apt`.
  O bootstrap é para Linux; não é um instalador nativo para Windows.
- Tenha acesso à internet, permissões para instalar dependências e
  **Python 3.12 ou superior** disponível como `python3`.
  O bootstrap instala dependências de sistema ausentes, mas **não atualiza
  automaticamente um Python antigo para 3.12**.
- Reserve acesso à sua própria conta/provedor de IA: a autenticação no
  OpenClaw pode exigir uma etapa pessoal e interativa.
- Preserve trabalhos locais existentes: a sincronização Git usa
  *fast-forward* e recusa alterações que não possam ser preservadas.
- Os três testes E2E usam modelos/serviços reais e podem consumir
  cota ou gerar cobrança conforme o provedor configurado.

## Instalação recomendada: revisar antes de executar

Abra um terminal na máquina Linux:

```bash
curl -fsSLo adaptive-install.sh \
  https://raw.githubusercontent.com/oliveiraariel/adaptive-ai-orchestrator/main/install.sh
less adaptive-install.sh
bash adaptive-install.sh
```

O arquivo é obtido da branch `main`, que pode evoluir. Revise-o e,
se precisar reproduzir exatamente uma versão no futuro, use um commit
fixo em vez da referência mutável `main`.

### Alternativa rápida

Se optar por executar diretamente o instalador remoto:

```bash
curl -fsSL https://raw.githubusercontent.com/oliveiraariel/adaptive-ai-orchestrator/main/install.sh | bash
```

**Execute apenas depois de confiar na origem e no conteúdo do script.**

Por padrão, a instalação usa:

```text
~/Projects/AdaptiveOpenClaw/
├── adaptive-ai-orchestrator/
└── ariel-agent-skills/
```

Para escolher outro diretório-base:

```bash
bash adaptive-install.sh --stack-root "$HOME/MeuDiretorio"
```

Esse último comando presume que você baixou o instalador conforme a etapa
recomendada. Em uma máquina nova, o bootstrap pode abrir o onboarding oficial
do OpenClaw. Não coloque chaves API, tokens ou credenciais no GitHub nem em
prompts de IA.

## Após a instalação

O bootstrap cria os seguintes comandos no Linux e seus atalhos gráficos:

| Comando | Finalidade |
| --- | --- |
| `adaptive-openclaw-setup` | Instalar ou reparar a integração existente |
| `adaptive-openclaw-update` | Atualizar com segurança e verificar por padrão |
| `adaptive-openclaw-verify` | Verificar o ambiente sem atualizar |

**Update já executa a verificação completa por padrão**. Não é preciso rodar
Verify novamente após um Update bem-sucedido, a menos que se deseje uma
validação independente. Os testes E2E podem utilizar provedores externos.

Se aparecer `comando não encontrado`, primeiro confira se os launchers
existem:

```bash
ls -l ~/.local/bin/adaptive-openclaw-*
```

Se existirem, abra um terminal novo ou ajuste o `PATH` apenas no terminal
atual:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Não reinstale a pilha somente por um problema de `PATH`.

## O que a verificação ao vivo comprova

```text
E2E 1 — Adaptive → OpenClaw → Adaptive
E2E 2 — Adaptive → 3 workers paralelos → fan-in → Adaptive
E2E 3 — OpenClaw → bridge → Adaptive → workers → fan-in → OpenClaw
```

A terceira etapa usa validação semântica das evidências, sem depender de
uma frase exata gerada pelo modelo. Um teste falho deve ser diagnosticado
pela **primeira camada que falhou**, não tratado automaticamente como
motivo para reinstalação.

## Se precisar de ajuda de uma IA

> Abra o repositório `oliveiraariel/adaptive-ai-orchestrator`, leia
> `COMECE-AQUI-NOVA-MAQUINA.md`, `bootstrap/manifest.json`,
> `bootstrap/README.md`, `bootstrap/TROUBLESHOOTING.md` e
> `bootstrap/RECOVERY-PROMPT.md`. Use o bootstrap versionado como fonte
> de verdade. Faça primeiro um diagnóstico de leitura, preserve o trabalho
> existente, diagnostique a primeira camada com falha e nunca solicite,
> exiba ou registre credenciais.

Para opções, comandos de manutenção, segurança e diagnóstico, consulte
[`bootstrap/README.md`](bootstrap/README.md) e
[`bootstrap/TROUBLESHOOTING.md`](bootstrap/TROUBLESHOOTING.md).
