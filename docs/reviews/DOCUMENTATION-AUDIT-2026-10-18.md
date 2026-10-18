# Auditoria documental — 2026-10-18

**Repositório:** `oliveiraariel/adaptive-ai-orchestrator`  
**Baseline:** `main` em `a367446bae096c92ef4cd1f5e3f5810190343142` (2026-10-16)  
**Escopo:** guias de entrada, instalação/recuperação, roteamento e perfis, prompts operacionais, documentação de fluxo Git; conferência cruzada com scripts, manifesto, contexto e implementação de fallback.

## Resultado

Foram inventariados **385 arquivos**, dos quais **148 Markdown**. A auditoria
aprofundou nove guias orientativos e confrontou instruções críticas com
`install.sh`, `bootstrap/{setup,update,verify}.sh`,
`bootstrap/lib/common.sh`, `pyproject.toml`,
`src/application/model_routing_policy.py`,
`src/infrastructure/openclaw_gateway_client.py`,
`CONTEXT.md` e `PROJECT-KNOWLEDGE-MANIFEST.yaml`.

### Correções incluídas nesta revisão

| Documento | Alteração |
| --- | --- |
| `README.md` | Remove seção de bootstrap duplicada e separadores consecutivos; referencia políticas canônicas de roteamento e perfis, evitando modelo fixo descontextualizado. |
| `README.pt-BR.md` | Direciona para o guia brasileiro de nova máquina; esclarece requisito de Python, custos E2E e perfis de execução. |
| `COMECE-AQUI-NOVA-MAQUINA.md` | Consolida o caminho de entrada, elimina orientações repetidas, fornece alternativa de execução após inspeção, requisitos e diagnóstico mínimo. |
| `bootstrap/README.md` | Esclarece fontes do token, autenticação, Python, custos e o exemplo de caminho portátil para uma migração antiga. |
| `bootstrap/TROUBLESHOOTING.md` | Adiciona diagnóstico de Python incompatível e de token exportado no shell sem imprimir credenciais. |
| `bootstrap/RECOVERY-PROMPT.md` | Impede interpretação da verificação ao vivo como gratuita ou automaticamente autorizada; reforça a inspeção segura de token. |
| `docs/model-routing-policy.md` | Corrige a afirmação de fallback único e explica o desvio por Kimi em determinados incidentes de cota, conforme o código. |
| `docs/prompts/README.md` | Passa a referenciar a regra global de verificação proporcional ao risco, implementada em outubro. |
| `docs/process/GIT-WORKFLOW.md` | Classifica como histórico o tutorial do repositório Skill e a antiga autoridade `MASTER-SPECIFICATION.md`. |

### Pendências / riscos fora da correção apenas documental

1. **Atualidade operacional — prioridade alta.** `CONTEXT.md` e
   `PROJECT-KNOWLEDGE-MANIFEST.yaml` ainda indicam `WU-055` como próximo
   trabalho e apresentam evidências históricas de setembro como estado atual.
   O repositório já contém commits de outubro. Não é seguro inventar a Work Unit
   corrente: reconciliar a situação com os checkpoints duráveis, PRs e evidências
   operacionais antes de atualizar esses dois arquivos.
2. **Precedência do token do Gateway — prioridade alta.**
   Em `bootstrap/lib/common.sh`, a função `ensure_secret_file` reutiliza um
   token persistido apenas quando `OPENCLAW_GATEWAY_TOKEN` está vazia/ausente
   no shell. Com a variável preenchida, o arquivo existente é sobrescrito.
   O comportamento foi agora documentado, mas **o código não foi alterado**.
   Recomenda-se hardening separado com testes e política explícita de migração.
3. **Validação ambiental — pendente.** Não foi executado bootstrap real nem
   E2E de modelos/Gateway nesta auditoria remota. Identificadores de modelos,
   contas e perfis dependem da configuração da máquina.
4. **Documentação histórica.** Materiais de versões antigas são mantidos como
   evidência; não foram reescritos em massa nem tratados como fontes normativas.

## Verificações realizadas

- Comparação dos comandos, caminhos, flags, versões e dependências com os
  scripts e o `pyproject.toml` versionados.
- Conferência de instalação `--no-onboard` e semântica de
  `openclaw update --yes` na documentação oficial OpenClaw.
- Verificação automatizada dos **45 links relativos** presentes nos nove
  guias alterados: **nenhum alvo ausente** na árvore da branch.
- Nenhum par de separadores Markdown adjacentes ou título duplicado nos
  nove guias alterados.
- **Não houve alteração de código executável, configurações, credenciais,
  estado de orquestração ou branch `main` nesta proposta.**
- Testes GitHub Actions deverão ser conferidos no pull request; uma revisão
  documental remota não equivale a validação E2E do runtime.

## Recomendações

Aprovar a simplificação de guias após revisão do diff. Em etapa separada,
realizar a reconciliação do contexto/manifesto com o estado durável atual e
corrigir a precedência do Gateway token de modo conservador, sem rotação
implícita de credenciais e com testes de regressão.
