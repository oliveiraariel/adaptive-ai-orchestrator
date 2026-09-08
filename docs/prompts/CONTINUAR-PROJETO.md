# Prompt curto — continuar projeto

Use este prompt quando quiser continuar uma linha de trabalho já iniciada sem reenviar o Prompt Mestre inteiro.

## Prompt

```text
Continue a partir do estado atual.

Use o `adaptive-orchestrator-bridge` em modo multiagente de projeto e mantenha o
Adaptive AI Orchestrator como autoridade de coordenação desta linha de trabalho.

Não refaça discovery, pesquisa, especificação ou decisões já concluídas sem
necessidade. Consulte o último handoff e as fontes de verdade que ele referencia.

Reavalie o Work Graph e a ready frontier a partir do estado atual.
Não presuma uma fila sequencial por camada: se múltiplas Work Units estiverem
realmente prontas, independentes e seguras, execute-as lateralmente dentro do
limite de concorrência e da política atual.

Selecione somente as skills necessárias por Work Unit e evite criar workers
adicionais sem benefício real. O número de workers deve seguir a frontier útil,
não uma meta fixa de paralelismo.

Quando resultados paralelos convergirem, faça fan-in explícito por integração,
testes, síntese ou revisão antes de liberar dependências posteriores.

Em checkout compartilhado, não execute writes paralelos com escopos sobrepostos,
amplos ou desconhecidos. Preserve a serialização necessária para segurança.

Respeite a governança, arquitetura, requisitos, convenções, gates e limites de
autoridade já existentes no projeto.

Prossiga com mudanças não destrutivas dentro do escopo atual e dos efeitos já
autorizados. Não amplie side effects silenciosamente.

Pare somente diante de:
- blocker real;
- decisão humana necessária;
- conflito entre fontes de verdade;
- mudança material de escopo;
- operação destrutiva ou irreversível;
- publicação/deploy não autorizado;
- conclusão do escopo atual.

Ao completar cada wave significativa, avalie resultados, avance apenas
Work Units aceitas, preserve evidência e recompute a próxima frontier.
```

## Como chamar este prompt no OpenClaw

> Leia `docs/prompts/CONTINUAR-PROJETO.md` no repositório `oliveiraariel/adaptive-ai-orchestrator` e continue a partir do estado atual.
