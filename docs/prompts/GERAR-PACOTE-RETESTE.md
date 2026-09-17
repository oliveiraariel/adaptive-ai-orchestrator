# Prompt curto — gerar pacote para reteste

Use este prompt quando o objetivo for gerar um **novo artefato instalável/deployable para reteste**, sem repetir manualmente o checklist de empacotamento.

A política obrigatória de runtime é `ADAPTIVE_RELEASE_ARTIFACT_POLICY_V1`. Ela também é aplicada automaticamente no `TaskPackage` quando o objetivo é claramente de empacotamento, portanto o operador não depende de decorar este arquivo.

## Prompt recomendado

```text
Gere um novo pacote instalável para reteste ambiental deste projeto.

Use o estado autoritativo atual do projeto e aplique obrigatoriamente:
ADAPTIVE_RELEASE_ARTIFACT_POLICY_V1

Respeite a governança e os gates específicos do projeto.
Não faça merge, publicação, deploy, instalação/ativação remota ou outra mutação externa apenas por estar gerando o pacote; essas ações exigem autoridade própria.
```

## Forma mínima

Quando o contexto do projeto já estiver carregado, esta solicitação deve ser suficiente:

> Gere um novo ZIP para reteste ambiental.

O `TaskPackage` deve reconhecer a intenção de empacotamento e acrescentar automaticamente as obrigações de:

- identificar a fonte exata que será empacotada;
- executar os gates locais aplicáveis do projeto;
- gerar artefato novo após a mudança;
- incluir somente runtime necessário;
- excluir segredos, estado local e material de desenvolvimento não necessário;
- validar a estrutura e a integridade do pacote;
- calcular tamanho e SHA-256;
- registrar evidências de source → artifact;
- separar prontidão local de validação ambiental;
- não transformar empacotamento em autorização implícita para deploy/instalação/merge.

## Observação

Não presuma WordPress, Composer, npm, PHP, JavaScript ou qualquer stack específica. Se o projeto possuir gates e estrutura próprios, eles prevalecem sobre exemplos genéricos.
