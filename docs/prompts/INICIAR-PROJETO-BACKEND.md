# Prompt Mestre — iniciar projeto Backend / Engineering

Use este prompt para iniciar trabalho relevante de **backend, API, engenharia de software, serviços, banco de dados ou arquitetura de aplicação** em um projeto novo ou existente, especialmente quando o nível de maturidade do projeto ainda não é conhecido.

## Prompt

```text
Quero iniciar ou continuar um trabalho profissional de backend/engenharia neste projeto.

Use o `adaptive-orchestrator-bridge` como porta de entrada para o
Adaptive AI Orchestrator.

Use `engineering-lifecycle` para determinar o fluxo de engenharia e
selecionar somente as skills necessárias ao objetivo.

O projeto pode estar em qualquer nível de maturidade: vazio, apenas com
uma ideia, parcialmente documentado, parcialmente implementado, legado
ou já bem estruturado.

Antes de alterar qualquer coisa, comece com `project-discovery` quando o
estado do projeto ainda não estiver suficientemente claro.

Descubra e diferencie:
- requisitos e regras já existentes;
- domínio e invariantes;
- stack e arquitetura;
- contratos, APIs e integrações;
- modelo de dados e persistência;
- autenticação e autorização;
- dependências e serviços externos;
- testes, CI, build e deployment;
- convenções de código e ferramentas;
- documentação e decisões existentes;
- fatos, inferências e dúvidas realmente bloqueantes.

Não recrie documentação, especificações, arquitetura ou modelos já
existentes apenas por formalidade.

PROJETO
[nome do projeto]

LOCAL / REPOSITÓRIO
[repositório, diretório ou workspace]

OBJETIVO DESTA SESSÃO
[descrever o resultado desejado]

MATERIAL ADICIONAL
[documentos, diagramas, URLs, logs, referências ou nenhum]

Se houver incerteza material, selecione conforme necessário capacidades
como `technical-research`, `domain-modeling`, `software-specification`,
`software-architecture` e `work-decomposition`.

Somente avance para `implementation` quando existir definição suficiente
para uma unidade de trabalho verificável.

Na implementação, use conforme necessário:
- implementation;
- testing;
- debugging;
- code-review;
- security-review;
- integration-release.

Considere `security-review` especialmente quando houver:
- autenticação ou autorização;
- dados sensíveis;
- input externo;
- upload;
- API pública;
- banco de dados;
- dependências externas;
- secrets ou credenciais;
- fronteiras de confiança;
- deployment ou exposição em rede.

Não invente requisitos para preencher lacunas e não use todas as skills
por padrão. Selecione a menor combinação capaz de produzir evidência
suficiente.

AUTORIDADE
Você pode realizar mudanças não destrutivas dentro do projeto necessárias
ao objetivo desta sessão.

Não está autorizado sem confirmação explícita a:
- alterar regra de negócio ou escopo material;
- substituir arquitetura existente sem análise de impacto;
- apagar trabalho útil;
- executar migrações destrutivas;
- expor credenciais ou dados sensíveis;
- publicar/deploy em produção;
- executar operações externas irreversíveis.

Pare e solicite decisão humana quando houver:
- ambiguidade real de negócio;
- conflito entre fontes de verdade;
- mudança material de escopo;
- decisão arquitetural de alto impacto e difícil reversão;
- operação destrutiva;
- credencial ausente;
- publicação/deploy não autorizado.

Execute em unidades pequenas e verificáveis. Teste, revise e preserve
evidência suficiente para continuidade.

Ao concluir ou interromper a sessão, use `project-handoff` e deixe claro:
- o que foi feito;
- evidências e verificações;
- riscos ou pendências;
- próximo trabalho executável.
```

## Como chamar este prompt no OpenClaw

Você pode dizer apenas:

> Leia `docs/prompts/INICIAR-PROJETO-BACKEND.md` no repositório `oliveiraariel/adaptive-ai-orchestrator` e use esse Prompt Mestre para iniciar este projeto. Meu objetivo é: [objetivo].
