# Política global de verificação proporcional — V1

**Identificador:** `ADAPTIVE_VERIFICATION_EFFICIENCY_V1`. Esta regra é aplicada a **todas** as Work Units pelo `TaskPackage`, independentemente de prompts, skills, linguagem ou projeto. As orientações não substituem o executor de CI nem alteram os gates de aceitação obrigatórios.

## Princípio

**Testar em proporção ao risco e à alteração; não repetir evidência válida sem mudança relevante.** Ganhar tempo sem confundir ausência de execução com `PASS`.

## Seleção de testes

| Evento | Checagem recomendada |
| --- | --- |
| Diagnóstico em leitura | Consultar evidência já existente e executar reprodução mínima, quando possível; não iniciar suíte ampla só para investigar |
| Modificação localizada | Executar teste de regressão causal + testes afetados + sintaxe/lint dos arquivos tocados |
| Mudança em contrato externo, serialização, persistência, autorização ou finanças | Executar também testes de integração/contrato pertinentes; ampliar proporcionalmente ao risco |
| Integração/release | Executar os gates obrigatórios para o **estado exato a empacotar** (incluindo suíte completa **uma vez**, quando o projeto a exigir), integridade e versão |
| `RETURNED` sem alteração do código | Ler `reason` e revalidar apenas evidência faltante; não repetir a suíte inteira sem causa |
| Manifestações repetidas / atraso de observador | Consultar `project-status` e Result Store autoritativos; mensagens duplicadas não são prova de testes repetidos |
| Ambiente indisponível | Registrar `NOT_RUN` e a limitação; não registrar `PASS` ou insistir indefinidamente |

## Cache de evidência (regra, não mecanismo automático de cache)

Uma evidência `PASS` pode ser citada como `REUSED` somente se **todos** coincidirem:
- identidade exata dos arquivos/código testados, incluindo WIP, quando relevante;
- comando, argumentos e versão das ferramentas;
- dependências, configuração e ambiente com impacto no resultado;
- escopo do critério de aceite;
- referência autoritativa de resultado de teste que possa ser conferida.

Mudou algum elemento material? Executar de novo o gate afetado. Se houver dúvida, preferir nova verificação focal; gates obrigatórios de release permanecem obrigatórios.

## Reconciliação de release

Produzir ZIP novo após mudar o código que será empacotado. Em uma tentativa `RETURNED` **sem mudança do código**, se houver artefato canônico verificável e manifesto/relatório íntegros, executar validação do manifesto e reconciliação oficial antes de reconstruir o ZIP.

A auditoria deve distinguir: erro funcional, erro de teste, artefato inválido, contrato de Result Store, erro de aceitação e observer/controle. Não promova veredito manualmente.

Obrigatórios: estrutura instalável, exclusão de segredos, versão interna, SHA-256, tamanho, manifesto, relatório e campos estruturados do gate. Testes em ambiente real ausentes permanecem `NOT_RUN`.

## Sem tarefas administrativas redundantes

- `Preflight` enxuto: branch/HEAD/WIP, execução concorrente e perfil quando relevante. Não reinventariar tudo em cada WU.
- Evitar uma WU só de documentação/checkpoint ou duplicar fase de testes sem critério distinto. A quantidade de WUs deve refletir fronteiras reais de responsabilidade.
- Não repetir a mesma resposta/relatório completo em várias mensagens. A emissão de progresso pode ser compacta; diagnóstico detalhado só em bloqueio.
- Auditorias `read-only` não podem usar limpeza destrutiva (inclusive limpeza automática por shell); criar arquivos temporários só durante etapas autorizadas de teste/empacotamento.
- Uma recusa de comando por política de shell não invalida automaticamente o artefato; escolher método sem mutação ou reportar bloqueio.

## Exceções e segurança

Não simplificar gates de proteção de dados, cálculo financeiro, permissões, migração, concorrência, segurança, release e rastreabilidade quando forem materialmente necessários.

A regra universal **não** autoriza desativar a inspeção AMEP, os hashes de referência, checkpoints, aceitação independente ou Result Store; validações de identidade/autoridade permanecem por transação/execução quando exigidas.

A implementação v1 **injeta diretivas**, mas não oferece cache automático de testes nem impede fisicamente todo rerun. Auditoria/deduplicação automática na lógica de execução requer mecanismos próprios e regressões adicionais.

## Aplicação

Runtime: `src/domain/verification_efficiency_policy.py` → `TaskPackage.__post_init__()`. Complementos documentais: skill `testing`, `integration-release` e Bridge. O contrato do projeto e a autorização humana têm precedência em gates mais estritos.
