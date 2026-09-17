# Prompt Mestre — iniciar ou alterar uma API

Use este prompt para iniciar trabalho relevante de **criação de API ou alteração de contrato de API** em qualquer linguagem, framework, plataforma, protocolo ou nível de maturidade do projeto.

A condução obrigatória de runtime é `ADAPTIVE_API_GENERATION_POLICY_V1`. Este prompt é a entrada humana recomendada; a política também é aplicada automaticamente no `TaskPackage`, portanto não depende apenas da memória do operador.

## Prompt

```text
Quero iniciar ou continuar um trabalho profissional de API neste projeto.

Use o `adaptive-orchestrator-bridge` como porta de entrada para o
Adaptive AI Orchestrator e use o modo multiagente de projeto para este
trabalho não trivial.

Aplique obrigatoriamente a política:
ADAPTIVE_API_GENERATION_POLICY_V1

Não assuma linguagem, framework, plataforma, REST, HTTP, JSON, OpenAPI ou
qualquer outra tecnologia antes de descobrir o contexto real do projeto.

O Adaptive deve possuir a responsabilidade de:
- compreender o objetivo e o estado real do projeto;
- descobrir o tipo de API/contrato já existente ou necessário;
- criar ou revisar o Work Graph;
- identificar dependências reais;
- calcular e recalcular a ready frontier;
- criar workers lógicos conforme a necessidade;
- selecionar somente as skills necessárias por Work Unit;
- executar em paralelo somente trabalho independente e seguro;
- preencher slots liberados quando nova Work Unit ficar pronta;
- integrar/fazer fan-in dos resultados aceitos;
- avaliar, revisar e replanejar de forma limitada quando necessário.

Use `engineering-lifecycle` como capacidade de engenharia, sem transferir
para essa skill as responsabilidades de scheduling do Adaptive.

Antes de implementar, faça `project-discovery` quando o estado real ainda
não estiver suficientemente claro.

Descubra e diferencie, conforme aplicável:
- requisitos, regras de negócio e invariantes existentes;
- consumidores atuais e compatibilidade esperada;
- linguagem, framework, runtime, plataforma e arquitetura existentes;
- estilo/protocolo da API: REST/HTTP, GraphQL, gRPC/RPC, webhook/evento ou outro;
- contratos, schemas, documentação e integrações já autoritativos;
- operações/mensagens e comportamento externamente observável;
- entradas, saídas, validação e erros públicos;
- autenticação, autorização, ownership/tenant isolation e fronteiras de confiança;
- persistência, transações e consistência quando relevantes;
- dependências e serviços externos;
- testes, CI, build, deployment e ambientes disponíveis;
- fatos, inferências e dúvidas realmente bloqueantes.

Não recrie especificação ou documentação já autoritativa apenas por formalidade.
Não invente regra de negócio para preencher lacuna.

PROJETO
[nome do projeto]

LOCAL / REPOSITÓRIO
[repositório, diretório ou workspace]

OBJETIVO DA API / DESTA SESSÃO
[descrever o resultado desejado]

MATERIAL ADICIONAL
[contratos, documentos, schemas, diagramas, URLs, logs, referências ou nenhum]

CONTRATO E COMPATIBILIDADE
Antes de considerar uma Work Unit de implementação suficientemente definida,
identifique ou preserve, no nível necessário ao escopo:
- operações/mensagens/campos expostos;
- inputs e regras de validação;
- outputs;
- erros públicos;
- autenticação e autorização;
- expectativa de compatibilidade/versionamento.

Se a API já existe, preserve consumidores e comportamento publicado. Não faça
breaking change sem autoridade explícita e análise de impacto.

SEMÂNTICA ESPECÍFICA DO PROTOCOLO
Avalie somente quando aplicável:
- idempotência e retries;
- concorrência/conflitos;
- paginação, filtros e limites de consulta;
- rate/resource limits;
- serialização/content types;
- datas, horários e timezones;
- precisão numérica;
- enums, nullability e campos opcionais.

Quando algo não se aplicar ao protocolo/projeto, classifique como não aplicável.
Não crie funcionalidades apenas para preencher checklist.

SEGURANÇA
Trate input externo e fronteiras de confiança como não confiáveis.
Quando aplicável, exija:
- autenticação correta;
- autorização por operação/recurso;
- ownership ou isolamento entre tenants/usuários;
- validação de entradas;
- proteção de secrets/credenciais;
- erros públicos sanitizados, sem detalhes internos, banco, stack ou segredos.

VERIFICAÇÃO
A mudança de API deve possuir a menor combinação suficiente de evidência:
- testes de contrato;
- testes de implementação/integração;
- casos negativos de autorização e validação para superfícies protegidas;
- regressão do comportamento que precisa permanecer estável;
- E2E/protocolo/ambiente real quando o runtime necessário estiver disponível.

Não marque validação ambiental como PASS se ela não foi realmente executada.
Separe claramente conclusão local de gates ambientais posteriores.

PARALELISMO
Não trate a API como uma fila única por hábito.
Depois que contratos/decisões compartilhadas estiverem estáveis o suficiente,
o Adaptive pode executar em paralelo implementação independente, testes,
security review, consumidores, documentação necessária e outros trabalhos sem
dependência bloqueante real.

Toda Work Unit com `filesystem.write` em checkout compartilhado deve possuir
`write_paths` literais, precisos e relativos ao repositório. Writes concorrentes
não podem se sobrepor.

Quando resultados paralelos convergirem, use fan-in explícito de integração,
testes, síntese ou revisão.

AUTORIDADE
Você pode realizar mudanças não destrutivas dentro do projeto necessárias ao
objetivo autorizado.

Isso não autoriza automaticamente:
- alterar regra de negócio ou escopo material;
- introduzir breaking change;
- substituir arquitetura existente sem análise de impacto;
- executar migração destrutiva;
- apagar trabalho útil;
- expor credenciais/dados sensíveis;
- publicar/deploy em produção;
- executar operação externa irreversível.

Pare e solicite decisão humana somente quando houver bloqueio real, como:
- ambiguidade material de negócio/contrato;
- conflito entre fontes autoritativas;
- mudança material de escopo;
- breaking change sem autoridade;
- decisão arquitetural de alto impacto/difícil reversão;
- operação destrutiva;
- credencial indispensável ausente;
- publicação/deploy não autorizado.

GATE DE CONCLUSÃO LOCAL
Não considere o trabalho de API localmente concluído até que:
- o contrato alterado esteja implementado e conectado ao runtime previsto;
- verificações locais exigidas pelo escopo tenham passado;
- findings de segurança/code review dentro do escopo estejam resolvidos;
- resultados paralelos tenham sido integrados/fan-in verificados quando houver;
- pendências ambientais restantes estejam explicitamente classificadas.

Ao concluir ou interromper, use `project-handoff` e registre:
- contrato/API efetivamente alterado;
- Work Units concluídas/bloqueadas;
- evidências e testes realmente executados;
- security/code/integration/fan-in status;
- compatibilidade e riscos;
- gates ambientais pendentes;
- próximo trabalho executável.
```

## Como chamar no OpenClaw

> Leia `docs/prompts/INICIAR-PROJETO-API.md` no repositório `oliveiraariel/adaptive-ai-orchestrator` e use esse Prompt Mestre. Meu objetivo é: [objetivo].
