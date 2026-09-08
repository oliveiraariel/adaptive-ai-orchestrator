# Prompt Mestre — iniciar projeto Frontend

Use este prompt para iniciar trabalho relevante de **frontend/web UI** em um projeto novo ou existente, especialmente quando o nível de maturidade do projeto ainda não é conhecido.

Não é necessário usar este prompt para perguntas simples ou análises visuais muito pequenas.

## Prompt

```text
Quero iniciar ou continuar um trabalho profissional de frontend neste projeto.

Use o `adaptive-orchestrator-bridge` como porta de entrada para o
Adaptive AI Orchestrator e use o modo multiagente de projeto para este
trabalho não trivial.

O Adaptive deve possuir a responsabilidade de:
- compreender o objetivo e o estado real do projeto;
- criar ou revisar o Work Graph;
- identificar dependências reais;
- calcular e recalcular a ready frontier;
- criar workers lógicos conforme a necessidade;
- selecionar somente as skills necessárias por Work Unit;
- executar em paralelo somente trabalho independente e seguro;
- preencher continuamente slots liberados sem aguardar workers independentes;
- fazer fan-in somente de resultados aceitos;
- avaliar, avançar dependências e replanejar de forma limitada quando necessário.

Use `engineering-lifecycle` como capacidade de engenharia, sem transferir
para essa skill as responsabilidades de scheduling do Adaptive.

O projeto pode estar em qualquer nível de maturidade: vazio, apenas com
uma ideia, parcialmente documentado, parcialmente implementado, legado
ou já bem estruturado.

Antes de alterar qualquer coisa, faça `project-discovery` quando o estado
do projeto ainda não estiver suficientemente claro.

Descubra e diferencie:
- o que já existe;
- o que é fonte de verdade;
- stack e arquitetura atuais;
- framework, plataforma e rendering model;
- sistema de estilos, tokens e componentes existentes;
- documentação, requisitos e decisões já aprovadas;
- rotas, fluxos, estados e comportamentos existentes;
- contratos/backend dos quais a interface depende;
- testes, CI e ferramentas de qualidade;
- restrições de acessibilidade, responsividade e performance;
- fatos, inferências e dúvidas realmente bloqueantes.

Não recrie documentação, especificações, arquitetura ou design system já
existentes apenas por formalidade.

PROJETO
[nome do projeto]

LOCAL / REPOSITÓRIO / URL
[repositório, diretório, site ou workspace]

OBJETIVO DESTA SESSÃO
[descrever o resultado desejado]

MATERIAL ADICIONAL
[URLs, screenshots, imagens, referências visuais, documentos ou nenhum]

Para trabalho de UI web, use `web-frontend-design` quando aplicável.
Preserve a arquitetura, framework, plataforma e styling system existentes
quando forem adequados ao projeto.

Se o projeto ainda não possuir definição suficiente para implementação,
crie ou proponha somente o contrato mínimo necessário antes de prosseguir.
Não invente requisitos para preencher lacunas.

Considere conforme o escopo:
- público e contexto de uso;
- objetivo primário da interface;
- arquitetura da informação;
- fluxos e estados;
- responsividade;
- acessibilidade;
- loading, empty, error, disabled e success states;
- desktop, mobile e larguras intermediárias;
- performance e compatibilidade;
- conteúdo real e variações extremas;
- integração com backend e contratos já existentes.

PARALELISMO
Não trate “frontend” como uma fase única e sequencial por padrão.
Quando houver trabalho independente, o Adaptive pode abrir múltiplos workers
frontend em paralelo, por exemplo para superfícies/componentes distintos,
acessibilidade, testes ou auditorias.

Quando este frontend fizer parte de um sistema full-stack, não espere todo o
backend terminar por hábito. Um contrato/API/interface suficientemente estável
pode desbloquear frontend e backend em paralelo. Preserve bloqueio apenas quando
houver uma dependência real ainda não resolvida ou o frontend teria de inventar
contrato, regra de negócio ou decisão arquitetural.

O número de workers deve seguir a ready frontier útil e a economicidade de
contexto/tokens. Não maximize agentes por si só. Escale para 2, 3, 4, 6 ou mais
somente quando houver trabalho independente e o limite configurado permitir.

Quando um worker concluir e seu resultado aceito desbloquear nova Work Unit,
reavalie a frontier imediatamente. Se houver slot livre e nenhuma colisão de
recursos/escrita, inicie o novo worker sem aguardar workers independentes que
ainda estejam em execução.

Quando workers compartilham o mesmo checkout, toda Work Unit que solicita
`filesystem.write` deve possuir `write_paths` literais, precisos e relativos ao
repositório. Escopo ausente, absoluto, com traversal/glob, desconhecido ou
sobreposto deve falhar ou ser serializado. Compare também com writers já ativos
de dispatches anteriores.

Quando resultados paralelos precisarem convergir, crie fan-in explícito de
integração, testes, síntese ou revisão em vez de depender de conversa informal
entre workers.

Não use todas as skills por padrão. Selecione a menor combinação capaz de
produzir evidência suficiente.

AUTORIDADE
Você pode realizar mudanças não destrutivas dentro do projeto necessárias
ao objetivo desta sessão.

Se esse objetivo autoriza edição dos arquivos do projeto, permita somente o
efeito de escrita necessário (`filesystem.write`). Isso não autoriza deploy,
publicação, mudanças de credenciais, exclusões destrutivas ou alterações externas.

Não está autorizado sem confirmação explícita a:
- alterar regras de negócio ou escopo do produto;
- substituir arquitetura existente sem análise de impacto;
- apagar trabalho útil;
- expor credenciais ou dados sensíveis;
- publicar/deploy em produção;
- executar operações externas irreversíveis.

Faça perguntas somente quando a resposta alterar materialmente o plano.
Quando possível, apresente sua recomendação junto da pergunta.

Execute em Work Units pequenas o suficiente para serem verificáveis, mas não
microfragmente apenas para criar mais agentes. Valide, revise e faça fan-in
quando resultados paralelos precisarem ser integrados.

Ao concluir ou interromper a sessão, use `project-handoff` e deixe claro:
- o que foi feito;
- Work Units concluídas/bloqueadas;
- paralelismo efetivamente utilizado (`max_parallelism_observed` quando disponível);
- dispatch generations relevantes e fan-in realizado;
- evidências e verificações;
- riscos ou pendências;
- próximo trabalho executável.
```

## Como chamar este prompt no OpenClaw

Você pode dizer apenas:

> Leia `docs/prompts/INICIAR-PROJETO-FRONTEND.md` no repositório `oliveiraariel/adaptive-ai-orchestrator` e use esse Prompt Mestre para iniciar este projeto. Meu objetivo é: [objetivo].
