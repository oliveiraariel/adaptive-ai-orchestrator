# Prompt Mestre — iniciar projeto Backend / Engineering

Use este prompt para iniciar trabalho relevante de **backend, API, engenharia de software, serviços, banco de dados ou arquitetura de aplicação** em um projeto novo ou existente, especialmente quando o nível de maturidade do projeto ainda não é conhecido.

## Prompt

```text
Quero iniciar ou continuar um trabalho profissional de backend/engenharia neste projeto.

Use o `adaptive-orchestrator-bridge` como porta de entrada para o
Adaptive AI Orchestrator e use o modo multiagente de projeto para este
trabalho não trivial.

O Adaptive deve possuir a responsabilidade de:
- compreender o objetivo e o estado real do projeto;
- criar ou revisar o Work Graph;
- identificar dependências reais;
- calcular a ready frontier;
- criar workers lógicos conforme a necessidade;
- selecionar somente as skills necessárias por Work Unit;
- executar em paralelo somente trabalho independente e seguro;
- sincronizar/fazer fan-in dos resultados;
- avaliar, avançar dependências e replanejar de forma limitada quando necessário.

Use `engineering-lifecycle` como capacidade de engenharia, sem transferir
para essa skill as responsabilidades de scheduling do Adaptive.

O projeto pode estar em qualquer nível de maturidade: vazio, apenas com
uma ideia, parcialmente documentado, parcialmente implementado, legado
ou já bem estruturado.

Antes de alterar qualquer coisa, faça `project-discovery` quando o estado
do projeto ainda não estiver suficientemente claro.

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
para uma Work Unit verificável.

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

PARALELISMO
Não trate “backend” como uma única fila sequencial.

Depois que contratos/decisões compartilhadas estiverem suficientemente
estáveis, o Adaptive pode executar em paralelo:
- dois ou mais módulos backend independentes;
- backend + testes/review/security;
- backend + frontend consumidor do mesmo contrato;
- outros trabalhos sem dependência bloqueante real.

Não espere todo o backend terminar para liberar frontend por hábito. Se uma
API/interface/schema já estiver estável o suficiente para o consumidor, use essa
fronteira como seam de paralelismo. Mantenha bloqueio quando o consumidor ainda
precisaria inventar contrato, regra de negócio ou decisão arquitetural.

O número de workers deve seguir a ready frontier útil e a economicidade de
contexto/tokens. Não maximize agentes por si só. Escale para 2, 3, 4, 6 ou mais
somente quando houver trabalho independente e o limite configurado permitir.

Quando workers compartilham o mesmo checkout, Work Units com escrita só podem
compartilhar a mesma onda quando possuírem escopos de escrita precisos e não
sobrepostos. Escopo amplo, desconhecido ou conflitante deve ser serializado.

Quando resultados paralelos precisarem convergir, crie fan-in explícito de
integração, testes, síntese ou revisão em vez de depender de conversa informal
entre workers.

Não invente requisitos para preencher lacunas e não use todas as skills
por padrão. Selecione a menor combinação capaz de produzir evidência
suficiente.

AUTORIDADE
Você pode realizar mudanças não destrutivas dentro do projeto necessárias
ao objetivo desta sessão.

Se esse objetivo autoriza edição dos arquivos do projeto, permita somente o
efeito de escrita necessário (`filesystem.write`). Isso não autoriza deploy,
publicação, mudanças de credenciais, exclusões destrutivas ou operações externas.

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

Execute em Work Units pequenas o suficiente para serem verificáveis, mas não
microfragmente apenas para criar mais agentes. Teste, revise, preserve evidência
e faça fan-in quando resultados paralelos precisarem ser integrados.

Ao concluir ou interromper a sessão, use `project-handoff` e deixe claro:
- o que foi feito;
- Work Units concluídas/bloqueadas;
- paralelismo efetivamente utilizado;
- evidências e verificações;
- riscos ou pendências;
- próximo trabalho executável.
```

## Como chamar este prompt no OpenClaw

Você pode dizer apenas:

> Leia `docs/prompts/INICIAR-PROJETO-BACKEND.md` no repositório `oliveiraariel/adaptive-ai-orchestrator` e use esse Prompt Mestre para iniciar este projeto. Meu objetivo é: [objetivo].
