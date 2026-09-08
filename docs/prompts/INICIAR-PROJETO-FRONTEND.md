# Prompt Mestre — iniciar projeto Frontend

Use este prompt para iniciar trabalho relevante de **frontend/web UI** em um projeto novo ou existente, especialmente quando o nível de maturidade do projeto ainda não é conhecido.

Não é necessário usar este prompt para perguntas simples ou análises visuais muito pequenas.

## Prompt

```text
Quero iniciar ou continuar um trabalho profissional de frontend neste projeto.

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
- o que já existe;
- o que é fonte de verdade;
- stack e arquitetura atuais;
- framework, plataforma e rendering model;
- sistema de estilos, tokens e componentes existentes;
- documentação, requisitos e decisões já aprovadas;
- rotas, fluxos, estados e comportamentos existentes;
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

Não use todas as skills por padrão. Selecione a menor combinação capaz de
produzir evidência suficiente.

AUTORIDADE
Você pode realizar mudanças não destrutivas dentro do projeto necessárias
ao objetivo desta sessão.

Não está autorizado sem confirmação explícita a:
- alterar regras de negócio ou escopo do produto;
- substituir arquitetura existente sem análise de impacto;
- apagar trabalho útil;
- expor credenciais ou dados sensíveis;
- publicar/deploy em produção;
- executar operações externas irreversíveis.

Faça perguntas somente quando a resposta alterar materialmente o plano.
Quando possível, apresente sua recomendação junto da pergunta.

Execute em unidades pequenas e verificáveis. Valide e revise o resultado.

Ao concluir ou interromper a sessão, use `project-handoff` e deixe claro:
- o que foi feito;
- evidências e verificações;
- riscos ou pendências;
- próximo trabalho executável.
```

## Como chamar este prompt no OpenClaw

Você pode dizer apenas:

> Leia `docs/prompts/INICIAR-PROJETO-FRONTEND.md` no repositório `oliveiraariel/adaptive-ai-orchestrator` e use esse Prompt Mestre para iniciar este projeto. Meu objetivo é: [objetivo].
