# Development Continuity

**Projeto:** Professional Software Engineering Skill
**Documento:** Registro de Continuidade do Desenvolvimento
**Versão do registro:** 0.3
**Status:** Consolidado — Etapas 3 e 4 concluídas

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

A espinha dorsal conceitual consolidada é:

```text
Contexto e Visão
→ Planejamento e Estrutura do Projeto
→ Necessidades e Requisitos
→ Casos de Uso e Comportamentos
→ Domínio
→ Dados e Modelagem
→ Arquitetura e Solução
→ Implementação
→ Verificação e Validação
→ Operação e Evolução
```

A profundidade e os artefatos concretos permanecem adaptativos ao contexto.

---

# 17. Documentos obrigatórios e documentos condicionais

A metodologia deve diferenciar:

## Documentos estruturais obrigatórios

Documentos que pertencem à espinha dorsal metodológica e devem existir mesmo em projetos pequenos, ainda que tenham profundidade menor.

O Documento de Visão e o Plano de Desenvolvimento são exemplos dessa categoria.

Os artefatos específicos da espinha dorsal podem variar conforme a natureza e a maturidade do projeto, desde que a função metodológica correspondente seja preservada.

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

Mudanças médias não substituem automaticamente a baseline. Uma nova baseline somente é estabelecida quando uma alteração estrutural significativa exigir nova análise e aprovação.

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

# 30. Dependências e disponibilidade

Uma unidade pode estar:

### LIBERADA

Todas as dependências necessárias estão validadas e existe base suficiente para iniciar sua execução.

### PARCIALMENTE LIBERADA

Parte das dependências ou informações necessárias está validada.

Esse estado permite exploração ou preparação quando apropriado, mas **não autoriza o início da execução da unidade**.

Uma unidade somente pode avançar para execução quando estiver integralmente `LIBERADA`.

### BLOQUEADA

Não existe base suficiente para continuar autonomamente ou existe uma condição que exige intervenção humana.

Informações inferidas podem ser usadas para exploração e preparação, mas não como conhecimento consolidado sem validação apropriada.

---

# 31. Ciclo da unidade de trabalho

Cada unidade deve seguir, conforme aplicável:

```text
selecionar
→ preparar
→ executar
→ testar
→ validar
→ analisar efeitos
→ gate
→ concluir
```

Quando houver problema:

```text
problema
→ analisar
→ corrigir
→ revalidar
```

### 31.1 Resultados de validação

A validação possui dois resultados normativos:

* `APROVADA`;
* `REPROVADA`.

`BLOQUEADA` não é resultado de validação; é estado operacional.

### 31.2 Reprovação

`REPROVADA` significa que a unidade não atende aos critérios de validação e deve permanecer no ciclo de análise, correção e revalidação enquanto o agente possuir autoridade e condições para resolver o problema.

### 31.3 Bloqueio

`BLOQUEADA` significa que o agente não pode continuar autonomamente de forma segura ou autorizada, ou que existem alternativas de solução cuja escolha exige intervenção humana.

O bloqueio representa uma interrupção deliberada do avanço autônomo para permitir decisão conjunta com o responsável humano.

### 31.4 Propagação do bloqueio

O bloqueio impede o avanço das unidades que dependem da unidade bloqueada quando sua resolução for necessária para o trabalho dependente.

O bloqueio não se propaga para unidades independentes.

Quando a situação for resolvida:

```text
decisão humana
→ registrar decisão
→ reavaliar unidade
→ reavaliar dependentes afetados
```

O desbloqueio não significa conclusão automática.

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

# 37. Estados e resultados operacionais

## 37.1 Estado de execução

Os estados de execução são:

* não iniciada;
* em análise;
* executando;
* em validação;
* corrigindo;
* concluída;
* bloqueada;
* reaberta.

Não existe estado normativo de conclusão parcial.

Uma pendência relevante impede a conclusão enquanto não for resolvida.

## 37.2 Disponibilidade / dependência

A disponibilidade de uma unidade pode ser:

* `LIBERADA`;
* `PARCIALMENTE LIBERADA`;
* `BLOQUEADA`.

Esses estados não devem ser confundidos com o estado de execução.

## 37.3 Resultado da validação

O resultado de uma validação pode ser:

* `APROVADA`;
* `REPROVADA`.

`BLOQUEADA` não é resultado de validação.

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

A suficiência necessária deve ser atingida antes da conclusão. Não deve ser criada uma categoria de conclusão parcial para acomodar pendências relevantes.

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

**Status:** CONCLUÍDA

### Resultado

Foram consolidados:

* diagnóstico adaptativo;
* análise proporcional ao impacto;
* impacto desconhecido;
* prioridade;
* intervenção humana proporcional;
* estrutura metodológica adaptativa;
* aprovação da estrutura inicial;
* baseline;
* mudanças estruturais, médias, pequenas e críticas;
* granularidade;
* execução sequencial;
* paralelismo controlado;
* dependências e disponibilidade;
* fila de trabalho dinâmica;
* elegibilidade para execução;
* priorização da fila;
* seleção e retirada da fila;
* ciclo de execução;
* testes;
* resultados de validação;
* diferenciação entre reprovação e bloqueio;
* propagação de bloqueios por dependência;
* correção e revalidação;
* análise de efeitos;
* gates;
* critérios de conclusão;
* reabertura proporcional;
* finalização do projeto;
* aprendizagem pós-projeto.

### Decisões relevantes consolidadas

* A fila é dinâmica e deve ser reavaliada quando um evento puder alterar a elegibilidade ou a prioridade relativa de pelo menos uma unidade.
* Somente unidades integralmente `LIBERADAS` podem entrar na fila de execução.
* `PARCIALMENTE LIBERADA` não autoriza o início da execução.
* `PRIORIDADE` é o critério primário de ordenação.
* Em empate de prioridade, considera-se o efeito no fluxo do projeto.
* Em novo empate, considera-se o tempo de espera.
* Em empate absoluto, qualquer unidade empatada pode ser escolhida, desde que a escolha seja registrada e rastreável.
* Uma unidade que perde elegibilidade sai da fila.
* Uma unidade selecionada é retirada da fila e passa a `EM EXECUÇÃO`.
* Alteração de prioridade ou efeito no fluxo, mantendo a elegibilidade, provoca reordenação da fila.
* `REPROVADA` significa que o problema pode ser tratado autonomamente pelo agente, enquanto houver autoridade e condições para resolução.
* `BLOQUEADA` significa que a continuidade autônoma não é possível ou que a decisão exige intervenção humana.
* O bloqueio propaga-se somente às unidades dependentes afetadas.
* O estado de conclusão parcial foi eliminado da metodologia.
* Pendências relevantes impedem a conclusão até sua resolução.
* A conclusão é hierárquica: unidade → subetapa → etapa → projeto.
* Unidades, subetapas ou etapas concluídas podem ser reabertas quando alterações posteriores demonstrarem impacto.
* A reabertura deve ser proporcional ao conjunto afetado.
* Auditorias são condicionais ao contexto e aos riscos e não constituem requisito universal de encerramento.

### Critério de conclusão

A Etapa 3 foi considerada concluída porque seu ciclo operacional foi definido, validado e consolidado, sem pendências conceituais que impeçam a continuidade da especificação.

## Etapa 4 — Necessidades e Requisitos

**Status:** CONCLUÍDA

### Resultado

Foram consolidados:

* compreensão e contexto do problema;
* objetivos e resultados esperados;
* stakeholders e necessidades;
* escopo e limites;
* requisitos funcionais;
* requisitos não funcionais;
* regras de negócio e restrições;
* critérios de aceitação;
* rastreabilidade;
* validação da especificação.

### Decisões relevantes consolidadas

* 4.1 identifica objetivos conhecidos no contexto; 4.2 formaliza objetivos, resultados esperados, indicadores e critérios de sucesso quando aplicáveis.
* Objetivos devem permanecer separados de soluções.
* Stakeholder não é sinônimo de ator.
* Necessidade não é requisito.
* Uma necessidade pode originar requisito funcional, requisito não funcional, regra, restrição ou combinação desses elementos.
* Escopo, requisito e solução permanecem conceitualmente distintos.
* Requisito funcional especifica comportamento, capacidade, processamento ou resultado que o sistema deve fornecer.
* Requisito não funcional especifica propriedade, qualidade, condição de operação ou restrição relevante do sistema.
* Categorias de requisitos não funcionais são adaptativas e não constituem checklist obrigatório.
* Regra de negócio, requisito e restrição permanecem conceitualmente distintos e rastreáveis.
* Critério de aceitação define a condição objetiva e verificável para considerar um requisito atendido; não é o mesmo que teste.
* A rastreabilidade deve permitir relações entre origem, necessidade, requisito, critério, verificação, dependências e impactos.
* O nível de rastreabilidade deve ser proporcional à relevância, impacto, risco, dependência e complexidade.
* A própria especificação deve ser validada antes da conclusão da Etapa 4.
* A validação possui os resultados `APROVADA` e `REPROVADA`; `BLOQUEADA` permanece como estado operacional.
* Reprovação entra em análise, correção e revalidação; bloqueio ocorre quando a continuidade autônoma não é possível ou quando a decisão exige intervenção humana.
* A Etapa 4 não antecipa domínio, dados, arquitetura, tecnologias ou implementação.

### Critério de conclusão

A Etapa 4 foi considerada concluída quando a especificação atingiu definição, consistência, rastreabilidade, verificabilidade e suficiência adequadas ao avanço responsável para as etapas seguintes.

---

# 45. Ponto exato de retomada

As Etapas 1, 2, 3 e 4 estão concluídas e consolidadas.

A próxima etapa ainda não foi definida neste registro e não deve ser inventada antecipadamente.

O próximo trabalho deve preparar a definição da próxima etapa da Skill, preservando as decisões já consolidadas e sem reabrir etapas concluídas sem motivo técnico.

A continuidade deve seguir:

```text
identificar a próxima etapa
→ compreender o objetivo
→ verificar decisões já existentes, se houver
→ diagnosticar lacunas
→ estruturar o trabalho
→ obter aprovação quando aplicável
→ estabelecer baseline
→ executar
```

---

# 46. Questões ainda pendentes

As questões conceituais centrais das Etapas 1 a 4 foram resolvidas e consolidadas.

Permanecem como trabalho posterior de implementação ou detalhamento, sem bloquear a conclusão conceitual das etapas já consolidadas:

* schemas e formatos concretos do estado operacional;
* implementação concreta do grafo de conhecimento e rastreabilidade;
* estrutura física dos evals;
* scripts, automações e demais recursos de implementação;
* decomposição física definitiva dos arquivos da Skill.

Esses pontos deverão ser tratados de forma coerente com a especificação mestre quando a implementação for iniciada.

Questões específicas da próxima etapa ainda não foram definidas e serão levantadas quando essa etapa for iniciada.

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
v0.3
```

A versão `v0.3` incorpora a consolidação da Etapa 4 — Necessidades e Requisitos.

## Estado do registro de continuidade

Este documento corresponde ao registro operacional da consolidação da `v0.3`.

Antes do commit e do push, o `MASTER-SPECIFICATION.md` e este documento devem ser verificados em conjunto.

---

# 50. Objetivo da próxima sessão

Preparar a definição da próxima etapa da Skill sem reabrir as Etapas 1, 2, 3 ou 4.

A próxima sessão deverá:

```text
identificar a próxima etapa
→ compreender seu objetivo
→ verificar decisões já existentes
→ identificar lacunas
→ propor estrutura de trabalho
→ decidir somente o que não puder ser determinado autonomamente
```

A definição da próxima etapa será realizada quando seu conteúdo for formalmente iniciado.

Após a validação conjunta dos documentos `MASTER-SPECIFICATION.md` e `DEVELOPMENT-CONTINUITY.md`, as alterações deverão ser versionadas conforme o `GIT-WORKFLOW.md`.
