# Development Continuity

**Projeto:** Professional Software Engineering Skill
**Documento:** Registro de Continuidade do Desenvolvimento
**Versão do registro:** 0.1
**Status:** Em desenvolvimento

---

# 1. Finalidade deste documento

Este documento registra o estado do desenvolvimento conceitual da Professional Software Engineering Skill.

Sua finalidade é permitir a continuidade do trabalho entre diferentes sessões, chats ou contextos, preservando:

* decisões já tomadas;
* princípios já consolidados;
* decisões ainda pendentes;
* linha de raciocínio necessária para continuidade;
* estado atual das etapas;
* pontos de retomada;
* alterações que ainda precisam ser incorporadas à especificação mestre.

Este documento não substitui o `MASTER-SPECIFICATION.md`.

O `MASTER-SPECIFICATION.md` contém a especificação normativa consolidada da Skill.

O presente documento contém o estado e a continuidade do processo de construção dessa especificação.

---

# 2. Estado atual do projeto

## 2.1 Objetivo geral

Construir uma Skill de Engenharia de Projetos de Software capaz de analisar, estruturar, desenvolver, documentar, validar, corrigir e evoluir projetos de software de diferentes domínios, tamanhos e níveis de maturidade.

A Skill deve ser orientada por processos e utilizar a documentação como representação formal do projeto.

---

# 3. Princípios gerais já estabelecidos

## 3.1 A Skill não é apenas uma ferramenta de documentação

A Skill é orientada à engenharia do projeto.

A documentação é entendida como formalização e representação do projeto.

Consequentemente, alterações documentais relevantes podem representar alterações reais no projeto e devem ser tratadas considerando seus impactos.

---

## 3.2 A Skill deve ser adaptativa

A estrutura interna dos projetos pode variar em:

* tamanho;
* complexidade;
* quantidade de informações;
* requisitos;
* riscos;
* integrações;
* segurança;
* profundidade documental.

Porém, a Skill deve preservar uma espinha dorsal metodológica padronizada.

Princípio:

> Padronização forte no método, adaptação na aplicação e evolução controlada do próprio padrão.

---

## 3.3 A solução deve ser proporcional ao projeto

O agente não deve maximizar documentação, entidades, camadas, tecnologias ou complexidade.

Deve buscar:

> solução mínima suficiente e profissionalmente adequada ao contexto.

A maturidade de um projeto não deve ser confundida com seu tamanho.

Um projeto pequeno pode ser maduro e suficiente.

Um projeto grande pode exigir maior profundidade por possuir maiores requisitos, riscos, integrações ou restrições.

---

# 4. Missão da Skill

A missão consolidada é:

> Conduzir a análise, estruturação, desenvolvimento, formalização, validação e evolução de projetos de software por meio de um processo adaptativo e sistemático, utilizando a documentação como representação formal do projeto e como instrumento de descoberta, decisão, comunicação, rastreabilidade e controle de qualidade.

A Skill deve adaptar seu processo ao domínio, contexto, maturidade, riscos, restrições e necessidades do cliente.

---

# 5. Capacidades fundamentais

As capacidades definidas são:

1. Compreender
2. Descobrir
3. Analisar
4. Estruturar
5. Decidir
6. Validar
7. Corrigir
8. Aprender e evoluir

---

# 6. Responsabilidades principais do agente

O agente deve ser responsável por:

1. compreender o projeto;
2. inventariar o conhecimento existente;
3. descobrir lacunas;
4. questionar decisões insuficientemente definidas;
5. estruturar o processo;
6. produzir e manter artefatos;
7. validar resultados;
8. corrigir problemas;
9. revalidar;
10. manter estado, decisões e histórico;
11. preservar coerência global;
12. manter rastreabilidade;
13. aprender e propor evolução da Skill.

---

# 7. Limites do agente

## 7.1 O agente não pode inventar

Não pode transformar ausência de informação em fato.

Não deve inventar:

* requisitos;
* regras de negócio;
* decisões do usuário;
* comportamentos do domínio;
* restrições;
* políticas;
* informações críticas.

---

## 7.2 O agente pode inferir

Pode realizar inferências quando existir evidência suficiente.

Uma inferência relevante deve permanecer distinguível de:

* fato confirmado;
* decisão;
* hipótese;
* questão pendente.

---

# 8. Modos de operação

## 8.1 Modo interativo

É o modo padrão.

O agente consulta o usuário quando uma decisão ultrapassa seus limites de autonomia ou quando a participação humana é necessária.

---

## 8.2 Modo automático

Ativado por:

```text
--auto
```

`--auto` significa:

> executar autonomamente aquilo que estiver dentro dos limites de autoridade estabelecidos pela Skill.

Não significa:

> nunca solicitar intervenção humana.

---

# 9. Política de autonomia

A autonomia é contextual.

A decisão de agir autonomamente deve considerar:

* evidência;
* incerteza;
* impacto;
* reversibilidade;
* sensibilidade;
* autoridade.

---

# 10. Intervenção humana

A intervenção humana deve ocorrer quando:

* uma decisão de negócio relevante não puder ser determinada;
* o impacto ultrapassar a autoridade do agente;
* a segurança estiver envolvida de forma relevante;
* dados sensíveis estiverem envolvidos;
* existir impacto arquitetural elevado;
* houver risco relevante;
* o impacto permanecer desconhecido;
* houver alteração de políticas da própria Skill;
* houver alteração do núcleo protegido da Skill.

---

# 11. Impacto desconhecido

Quando o agente não conseguir determinar o impacto com confiança suficiente:

```text
IMPACTO_DESCONHECIDO
```

Esse estado exige intervenção humana antes de uma ação potencialmente relevante.

Casos desse tipo são esperados como raros porque a análise prévia de sensibilidade deve identificar antecipadamente aspectos relacionados a:

* segurança;
* dados sensíveis;
* privacidade;
* conformidade;
* autenticação;
* autorização;
* integridade;
* outros riscos relevantes.

---

# 12. Impacto e prioridade

Impacto e prioridade são conceitos independentes.

## Impacto

Responde:

> Qual o tamanho, risco ou alcance de estar errado?

## Prioridade

Responde:

> Quão necessário é resolver isso agora?

## 12.1 Níveis de impacto

* baixo;
* médio;
* alto;
* crítico;
* desconhecido.

## 12.2 Níveis de prioridade

* bloqueadora;
* urgente;
* importante;
* normal;
* futura.

---

# 13. Diagnóstico

O diagnóstico não deve ser global por padrão.

A Skill deve começar pela menor abrangência suficiente e aumentar a profundidade conforme necessário.

## 13.1 Diagnóstico local

Aplicado a mudanças pequenas e isoladas.

## 13.2 Diagnóstico contextual

É o nível padrão para alterações semânticas.

Deve verificar:

* elemento alterado;
* referências;
* dependências;
* elementos diretamente relacionados;
* coerência do contexto.

## 13.3 Diagnóstico global

É reservado para situações que realmente justifiquem sua abrangência, tais como:

* alterações estruturais;
* riscos elevados;
* contradições generalizadas;
* solicitações de auditoria;
* impossibilidade de determinar impacto local ou contextual.

---

# 14. Princípio de análise proporcional

A abrangência da análise deve ser determinada pelo:

* significado da mudança;
* impacto;
* dependências;
* risco;
* incerteza.

O tamanho textual da alteração não determina seu impacto.

Uma pequena alteração textual pode possuir grande impacto semântico.

---

# 15. Estrutura dos projetos

Os projetos devem possuir uma estrutura metodológica padronizada, mas adaptativa.

A estrutura deve ser entendida como:

```text
ESPINHA DORSAL OBRIGATÓRIA
+
EXTENSÕES CONDICIONAIS
+
ELEMENTOS ESPECÍFICOS DO DOMÍNIO
```

---

# 16. Espinha dorsal metodológica

A Skill deve possuir uma sequência lógica de formalização do projeto.

A estrutura precisa preservar o princípio de que:

* documentos iniciais estabelecem contexto;
* necessidades e requisitos são compreendidos antes da solução;
* modelagem e arquitetura derivam da compreensão anterior;
* implementação e testes são consequências da definição anterior.

A lista definitiva e formal da espinha dorsal ainda será fechada posteriormente.

---

# 17. Documentos obrigatórios e documentos condicionais

A metodologia deve diferenciar:

## Documentos estruturais obrigatórios

Documentos que pertencem à espinha dorsal metodológica e devem existir mesmo em projetos pequenos, ainda que tenham profundidade menor.

O Documento de Visão e o Plano de Desenvolvimento são exemplos dessa categoria.

## Documentos condicionais

Podem ser necessários conforme:

* domínio;
* risco;
* complexidade;
* segurança;
* integrações;
* arquitetura;
* operação;
* necessidades específicas do projeto.

A ausência de um artefato condicional deve ser uma decisão metodológica justificável.

---

# 18. Ordem metodológica

A posição conceitual dos artefatos deve ser preservada.

A ordem de criação não deve ser confundida com a ordem de revisão.

Um Documento de Visão pode ser revisado posteriormente sem deixar de ser um documento estrutural inicial.

---

# 19. Aprovação da estrutura inicial

Depois do diagnóstico inicial, o agente deve propor:

* etapas;
* subetapas;
* atividades;
* artefatos;
* dependências;
* critérios de validação;
* sequência de execução.

A estrutura proposta deve ser submetida à aprovação do responsável antes da execução estruturada.

Mesmo quando o projeto recebido estiver muito bem documentado e a estrutura proposta for praticamente uma formalização do que já existe, a aprovação continua sendo importante.

---

# 20. Reestruturação inicial

Projetos recebidos podem estar:

* incompletos;
* desorganizados;
* parcialmente implementados;
* documentados de forma inconsistente;
* estruturados de maneira inadequada.

Nesses casos, a Skill deve:

1. analisar;
2. diagnosticar;
3. propor reorganização;
4. definir a estrutura metodológica;
5. obter aprovação;
6. executar a reestruturação;
7. estabelecer uma nova baseline;
8. realizar uma análise mais profunda.

A primeira grande reestruturação é esperada principalmente no início dos projetos que chegam desorganizados.

---

# 21. Baseline do projeto

A estrutura aprovada após a análise inicial constitui a baseline do projeto.

A baseline tem a função de:

* estabilizar o processo;
* orientar a execução;
* evitar reorganizações constantes;
* estabelecer a referência estrutural para as etapas seguintes.

---

# 22. Mudanças após a baseline

## 22.1 Mudanças estruturais

Grandes alterações na estrutura ou na estratégia do projeto.

São esperadas principalmente no início e devem ser excepcionais após a baseline.

Podem exigir:

* nova análise;
* novo planejamento;
* nova aprovação.

## 22.2 Mudanças médias

São acomodações decorrentes de novas descobertas.

Podem incluir:

* novas subetapas;
* novos artefatos;
* novas dependências;
* reorganizações internas moderadas.

Podem ser executadas autonomamente quando estiverem dentro da autoridade do agente.

## 22.3 Mudanças pequenas

São muito frequentes.

Exemplos:

* ajustes documentais;
* referências;
* padronização;
* índices;
* correções locais;
* ajustes de estrutura menores.

Devem ser predominantemente automatizadas.

## 22.4 Mudanças críticas

Podem ocorrer independentemente do tamanho aparente e estão relacionadas a:

* segurança;
* integridade;
* dados sensíveis;
* conformidade;
* alto risco;
* impacto elevado.

Devem seguir as regras de governança.

---

# 23. Frequência esperada das mudanças

A expectativa é:

```text
Mudanças estruturais
→ raras

Mudanças médias
→ ocasionais

Mudanças pequenas
→ frequentes
```

Uma segunda grande reestruturação não é impossível, mas deve ser considerada improvável.

Quando uma segunda mudança estrutural ocorrer, deverá ser tratada como evento relevante e analisada.

---

# 24. Granularidade

A estrutura não deve ser fragmentada artificialmente.

Uma divisão deve existir quando melhorar pelo menos uma destas funções:

* execução;
* validação;
* rastreabilidade;
* decisão;
* controle de risco.

---

# 25. Tipos de unidade de trabalho

## Etapa

Possui:

* objetivo próprio;
* resultado próprio;
* dependências significativas;
* critérios de conclusão;
* necessidade de gate.

## Subetapa

É uma divisão que merece controle ou validação independente.

## Atividade

É trabalho necessário que não precisa possuir um gate próprio.

## Artefato

É um produto resultante do trabalho.

Etapa e documento não são conceitos equivalentes.

---

# 26. Execução sequencial

A estratégia padrão da Skill é:

> execução sequencial controlada por dependências.

A Skill prioriza:

* estabilidade;
* coerência;
* previsibilidade;
* qualidade;
* redução de retrabalho.

A velocidade não deve ser maximizada em prejuízo da qualidade.

---

# 27. Paralelismo controlado

Paralelismo é permitido quando:

* a estrutura estiver madura;
* as dependências estiverem bem definidas;
* as informações necessárias estiverem validadas;
* houver baixo risco de mudança;
* houver baixo acoplamento;
* existir benefício real.

O agente deve detectar possibilidades de paralelismo, mas normalmente administrar uma fila de trabalho controlada em vez de manter muitas atividades abertas simultaneamente.

---

# 28. Regra de maturidade para paralelismo

Quanto mais instável a estrutura:

```text
menos paralelismo
```

Quanto mais madura a estrutura:

```text
maior possibilidade de paralelismo controlado
```

O objetivo é reduzir retrabalho.

---

# 29. Dependências

A ordem lógica deve ser definida pelas dependências, e não apenas pela posição temporal.

O princípio é:

> o processo é sequencial por dependência, não necessariamente por calendário.

---

# 30. Dependências parciais

Uma unidade pode estar:

### LIBERADA

As dependências necessárias estão validadas.

### PARCIALMENTE LIBERADA

Parte da unidade pode avançar com segurança.

### BLOQUEADA

Não existe base suficiente para avançar.

Informações inferidas podem ser usadas para exploração e preparação, mas não como conhecimento consolidado sem validação apropriada.

---

# 31. Ciclo da unidade de trabalho

Cada unidade deve seguir, conforme aplicável:

```text
decidir
→ planejar
→ executar
→ testar
→ validar
→ verificar efeitos
→ concluir
```

Quando houver problema:

```text
problema
→ analisar
→ corrigir
→ revalidar
```

---

# 32. Tipos de teste

Teste não está limitado ao código.

Podem existir:

* testes documentais;
* testes lógicos;
* testes de consistência;
* testes de rastreabilidade;
* testes executáveis.

---

# 33. Teste lógico

O agente deve verificar se uma alteração continua coerente com aquilo que está relacionado.

Exemplo:

```text
Regra
  ↓
Requisito
  ↓
Caso de Uso
  ↓
Domínio
  ↓
Dados
  ↓
Teste
```

A alteração só deve ser considerada concluída quando a coerência relevante tiver sido verificada.

---

# 34. Validação de subetapa

Toda subetapa deve possuir uma validação antes de ser considerada concluída.

A validação deve verificar, conforme aplicável:

* completude;
* consistência;
* coerência;
* rastreabilidade;
* qualidade;
* ausência de bloqueios;
* atendimento aos critérios definidos.

---

# 35. Validação de etapa

Depois que as subetapas necessárias forem concluídas, a etapa deve passar por uma validação consolidada.

A etapa só pode ser considerada concluída quando o conjunto estiver suficientemente coerente para permitir avanço.

---

# 36. Revalidação

Se uma validação falhar:

```text
corrigir
→ revalidar
```

Se uma alteração posterior afetar uma unidade já concluída:

```text
reabrir
→ analisar impacto
→ corrigir
→ revalidar
```

A reabertura deve atingir apenas o conjunto realmente afetado.

---

# 37. Estados de execução

Os estados considerados até aqui incluem:

* não iniciada;
* em análise;
* executando;
* em validação;
* corrigindo;
* concluída;
* concluída com pendências;
* bloqueada;
* reaberta.

---

# 38. Suficiência

Um projeto não precisa eliminar toda incerteza.

O projeto deve atingir um nível suficiente de:

* definição;
* estrutura;
* solução;
* validação.

A suficiência depende de:

* necessidades do cliente;
* objetivos;
* riscos;
* restrições;
* complexidade;
* impacto;
* contexto;
* nível de serviço esperado.

---

# 39. Evolução da Skill

A Skill deve poder evoluir com base em:

* projetos realizados;
* decisões;
* erros;
* validações;
* padrões recorrentes;
* pesquisas externas;
* novas práticas;
* evolução tecnológica;
* evolução das práticas empresariais e de TI.

---

# 40. Evolução governada

A Skill não deve aprender sem controle.

A evolução deve ser:

* fundamentada;
* avaliada;
* rastreável;
* versionada;
* reversível quando possível.

---

# 41. Conhecimento externo

A descoberta de uma nova prática externa não significa automaticamente que ela seja um novo padrão da Skill.

O agente deve distinguir entre:

```text
observação
→ tendência
→ prática recorrente
→ prática consolidada
→ candidato a padrão
→ incorporação
```

Uma fonte isolada não deve automaticamente modificar a metodologia.

---

# 42. Separação entre conhecimento do projeto e conhecimento da Skill

Uma regra específica de um projeto não deve ser incorporada automaticamente ao conhecimento geral da Skill.

O agente pode identificar padrões generalizáveis, mas deve avaliá-los antes de incorporá-los à metodologia.

---

# 43. Segurança da própria Skill

Alterações que possam afetar:

* segurança;
* autonomia;
* desempenho crítico;
* integridade;
* governança;
* políticas de evolução;

devem receber tratamento especial e podem exigir intervenção humana.

---

# 44. Estado atual das etapas

## Etapa 1 — Propósito e Contrato

**Status:** CONCLUÍDA

### Resultado

Foram definidos:

* missão;
* capacidades;
* responsabilidades;
* limites;
* autonomia;
* intervenção humana;
* princípios fundamentais;
* política de evolução.

---

## Etapa 2 — Modelo Mental do Agente

**Status:** CONCLUÍDA

### Resultado

Foram definidos:

* representação contextual do projeto;
* modelo de conhecimento;
* evidência;
* inferência;
* incerteza;
* decisões;
* relações entre artefatos;
* maturidade;
* suficiência.

---

## Etapa 3 — Ciclo Operacional

**Status:** EM DESENVOLVIMENTO

### Definições já estabelecidas

* diagnóstico adaptativo;
* diagnóstico local/contextual/global;
* análise proporcional ao impacto;
* impacto desconhecido;
* prioridade;
* intervenção humana proporcional;
* estrutura metodológica adaptativa;
* aprovação da estrutura inicial;
* baseline;
* reestruturação inicial;
* mudanças estruturais;
* mudanças médias;
* mudanças pequenas;
* mudanças críticas;
* granularidade;
* execução sequencial;
* paralelismo controlado;
* dependências;
* dependências parciais;
* ciclo de execução;
* validação;
* teste lógico;
* revalidação.

---

# 45. Ponto exato de retomada

O próximo ponto a ser desenvolvido é:

> Consolidar formalmente o ciclo completo de execução, validação, revalidação, conclusão da subetapa, conclusão da etapa e critérios de gate.

Também deverá ser aprofundado:

* classificação formal dos resultados de validação;
* fila de trabalho;
* priorização entre unidades;
* critérios de conclusão;
* comportamento diante de pendências;
* comportamento diante de bloqueios;
* reabertura de etapas;
* finalização do ciclo;
* aprendizagem pós-projeto.

---

# 46. Questões ainda pendentes

As seguintes questões permanecem abertas ou precisam de refinamento:

* Espinha dorsal documental definitiva.
* Critérios formais de conclusão de cada grande etapa.
* Critérios formais dos gates.
* Estados formais de validação.
* Estrutura formal da fila de trabalho.
* Algoritmo de priorização.
* Política detalhada de replanejamento médio.
* Política formal de versionamento das baselines.
* Estrutura formal do grafo de conhecimento.
* Estrutura detalhada de rastreabilidade.
* Estrutura definitiva da avaliação da Skill.
* Política detalhada de atualização do conhecimento da Skill.
* Processo detalhado de pós-projeto.
* Estrutura final dos arquivos da Skill.

---

# 47. Regra de continuidade

Ao retomar o desenvolvimento:

1. Ler o `MASTER-SPECIFICATION.md`.
2. Ler este `DEVELOPMENT-CONTINUITY.md`.
3. Preservar decisões já consolidadas.
4. Não reabrir decisões já aprovadas sem motivo técnico.
5. Identificar a etapa atual.
6. Retomar a partir do ponto exato registrado.
7. Perguntar somente quando uma indefinição relevante impedir uma decisão segura.
8. Consolidar novas decisões no `MASTER-SPECIFICATION.md`.
9. Atualizar este documento de continuidade.
10. Versionar as alterações no Git.

---

# 48. Regra de consistência entre documentos

O `MASTER-SPECIFICATION.md` possui prioridade normativa.

Este documento possui prioridade operacional de continuidade.

Quando houver divergência:

```text
MASTER-SPECIFICATION
        ↓
verificar decisão consolidada
        ↓
DEVELOPMENT-CONTINUITY
        ↓
atualizar continuidade
```

Uma nova decisão só deve alterar a especificação mestre depois de ser explicitamente consolidada.

---

# 49. Estado do versionamento

## Versão atual da especificação

```text
v0.1
```

## Próxima versão esperada

```text
v0.2
```

A próxima versão deverá incorporar a consolidação da Etapa 3 quando ela for oficialmente concluída.

---

# 50. Objetivo da próxima sessão

Continuar a construção da Etapa 3 sem reiniciar as Etapas 1 e 2.

O próximo trabalho deve começar pela definição dos mecanismos de:

```text
fila de trabalho
→ priorização
→ execução
→ validação
→ revalidação
→ gate
→ conclusão
```

---

## Depois de colar

Salve o arquivo. **Não faça commit ainda.**

Quando estiver salvo, teremos os dois documentos de referência:

```text
specifications/
└── MASTER-SPECIFICATION.md

docs/
├── GIT-WORKFLOW.md
└── DEVELOPMENT-CONTINUITY.md
```
