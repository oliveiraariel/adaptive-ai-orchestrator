# Git Workflow — guia histórico do projeto Skill

> **ATENÇÃO — documento legado, não normativo para o Adaptive AI Orchestrator.**
> Os exemplos abaixo foram escritos para o antigo
> `Professional-Software-Engineering-Skill`, incluindo o repositório remoto
> e a especificação `MASTER-SPECIFICATION.md`. Use-os somente como referência
> geral sobre Git, **não** como comandos específicos para o repositório Adaptive.
> Para autoridade documental e estado atual, consulte
> [`CONTEXT.md`](../../CONTEXT.md),
> [`PROJECT-KNOWLEDGE-MANIFEST.yaml`](../../PROJECT-KNOWLEDGE-MANIFEST.yaml)
> e [`ORCHESTRATOR-SPEC-DRIVEN-DEVELOPMENT.md`](ORCHESTRATOR-SPEC-DRIVEN-DEVELOPMENT.md).

## 1. Objetivo

Este documento define o procedimento padronizado para utilizar Git e GitHub nos projetos deste repositório.

O guia contempla:

* criação de um novo repositório Git;
* conexão com um repositório GitHub;
* criação do primeiro commit;
* publicação inicial no GitHub;
* atualização de versões;
* verificação do estado do repositório;
* resolução de problemas comuns.

---

# 2. Conceitos fundamentais

## 2.1 Git

Git é o sistema de controle de versão utilizado para registrar alterações nos arquivos do projeto.

## 2.2 GitHub

GitHub é o serviço remoto utilizado para hospedar e compartilhar o repositório Git.

## 2.3 Repositório local

É o repositório Git existente na máquina de desenvolvimento.

## 2.4 Repositório remoto

É o repositório hospedado no GitHub.

Normalmente será identificado como:

```text
origin
```

## 2.5 Commit

Um commit registra um estado específico do projeto no histórico do Git.

Exemplo:

```bash
git commit -m "docs: cria especificacao mestre v0.1"
```

## 2.6 Branch

Branch representa uma linha de desenvolvimento.

O branch principal utilizado neste projeto é:

```text
main
```

## 2.7 Push

`push` envia os commits existentes no repositório local para o repositório remoto.

## 2.8 Pull

`pull` atualiza o repositório local utilizando alterações existentes no repositório remoto.

---

# 3. Criar Git em um projeto novo

## 3.1 Abrir o projeto

Abrir a pasta raiz do projeto no VS Code.

Exemplo:

```text
Professional-Software-Engineering-Skill/
```

## 3.2 Abrir o terminal

No VS Code:

```text
Terminal → New Terminal
```

## 3.3 Verificar o Git

Executar:

```bash
git --version
```

O Git deve responder com sua versão instalada.

## 3.4 Inicializar o repositório

Na raiz do projeto:

```bash
git init
```

Isso cria o diretório:

```text
.git/
```

e transforma a pasta em um repositório Git local.

## 3.5 Verificar o estado

```bash
git status
```

Verificar quais arquivos estão sendo identificados pelo Git.

---

# 4. Configurar identidade do Git

Caso o Git ainda não tenha nome e e-mail configurados:

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"
```

Verificar:

```bash
git config --global user.name
git config --global user.email
```

O e-mail deve ser compatível com a conta utilizada no GitHub ou utilizar uma identidade `noreply` do GitHub, quando desejado.

---

# 5. Criar o primeiro commit

## 5.1 Adicionar arquivos ao staging

É possível adicionar uma pasta específica:

```bash
git add specifications/
```

Ou, quando apropriado:

```bash
git add .
```

### Regra de segurança

Antes de utilizar:

```bash
git add .
```

verificar primeiro:

```bash
git status
```

Nunca adicionar indiscriminadamente arquivos que possam conter:

* senhas;
* tokens;
* chaves;
* credenciais;
* arquivos temporários;
* arquivos de ambiente;
* artefatos que não pertençam ao repositório.

## 5.2 Verificar o staging

```bash
git status
```

Confirmar quais arquivos serão incluídos no commit.

## 5.3 Criar o commit

Exemplo:

```bash
git commit -m "docs: cria especificacao mestre v0.1"
```

O commit deve possuir uma mensagem que explique claramente o que foi registrado.

---

# 6. Utilizar o branch principal `main`

Se o Git criou o branch principal como `master`, alterar para:

```bash
git branch -M main
```

Verificar:

```bash
git status
```

O branch deverá ser:

```text
main
```

---

# 7. Criar o repositório no GitHub

No GitHub:

```text
New repository
```

Utilizar o nome desejado para o projeto.

Quando o projeto já possui um repositório Git local com commits, recomenda-se criar o repositório remoto vazio.

Não inicializar novamente com:

* README;
* `.gitignore`;
* license;

quando esses elementos já forem controlados pelo repositório local.

---

# 8. Conectar o Git local ao GitHub

Na raiz do projeto:

```bash
git remote add origin "https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git"
```

Exemplo:

```bash
git remote add origin "https://github.com/oliveiraariel/Professional-Software-Engineering-Skill.git"
```

Verificar:

```bash
git remote -v
```

O resultado esperado:

```text
origin  https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git (fetch)
origin  https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git (push)
```

---

# 9. Publicar o primeiro commit

Executar:

```bash
git push -u origin main
```

O parâmetro `-u` estabelece o relacionamento entre o branch local e o branch remoto.

Após isso, normalmente será possível utilizar apenas:

```bash
git push
```

nas atualizações seguintes.

---

# 10. Verificar se a publicação funcionou

## 10.1 Verificar o estado local

```bash
git status
```

O estado esperado é semelhante a:

```text
On branch main
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean
```

## 10.2 Verificar o histórico

```bash
git log --oneline --max-count=3
```

Exemplo:

```text
b93d34d docs: cria especificacao mestre v0.1
```

## 10.3 Verificar no GitHub

Abrir o repositório no GitHub e confirmar:

```text
specifications/
└── MASTER-SPECIFICATION.md
```

---

# 11. Fluxo normal de atualização

Depois que o projeto já está configurado e conectado ao GitHub, o processo normal é:

```text
Editar
  ↓
Validar
  ↓
git status
  ↓
git add
  ↓
git commit
  ↓
git push
```

## 11.1 Verificar alterações

```bash
git status
```

## 11.2 Adicionar arquivos alterados

Exemplo específico:

```bash
git add specifications/MASTER-SPECIFICATION.md
```

Ou:

```bash
git add .
```

quando todos os arquivos identificados forem realmente desejados no commit.

## 11.3 Criar o commit

Exemplo:

```bash
git commit -m "docs: atualiza especificacao mestre"
```

## 11.4 Publicar no GitHub

```bash
git push
```

---

# 12. Fluxo para criação de uma nova versão da especificação

Exemplo:

```text
v0.1
  ↓
Etapa 3 concluída
  ↓
MASTER-SPECIFICATION atualizado
  ↓
v0.2
```

Procedimento:

```bash
git status
```

Validar as alterações.

Depois:

```bash
git add specifications/MASTER-SPECIFICATION.md
```

Criar o commit:

```bash
git commit -m "docs: consolida etapa 3 e cria v0.2"
```

Publicar:

```bash
git push
```

---

# 13. Verificar diferenças antes do commit

Para visualizar alterações:

```bash
git diff
```

Depois de colocar arquivos no staging:

```bash
git diff --staged
```

Esses comandos permitem verificar o conteúdo antes de criar o commit.

---

# 14. Histórico de versões

Consultar os últimos commits:

```bash
git log --oneline --max-count=10
```

Exemplo:

```text
c91a111 docs: consolida etapa 3 e cria v0.2
b93d34d docs: cria especificacao mestre v0.1
```

O histórico representa a evolução do projeto.

---

# 15. Tags de versão

Quando desejado, uma versão formal pode receber uma tag.

Exemplo:

```bash
git tag v0.1
```

Publicar:

```bash
git push origin v0.1
```

Para uma nova versão:

```bash
git tag v0.2
git push origin v0.2
```

Tags podem ser utilizadas para identificar versões importantes do projeto.

---

# 16. Verificar o repositório remoto

```bash
git remote -v
```

Caso o endereço esteja incorreto, remover:

```bash
git remote remove origin
```

e adicionar novamente:

```bash
git remote add origin "https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git"
```

---

# 17. Problemas comuns

## 17.1 Git não reconhece o usuário

Erro semelhante a:

```text
Author identity unknown
```

Configurar:

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"
```

## 17.2 Repositório remoto incorreto

Verificar:

```bash
git remote -v
```

Corrigir:

```bash
git remote set-url origin "https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git"
```

## 17.3 Origin já existe

Se aparecer:

```text
remote origin already exists
```

Verificar:

```bash
git remote -v
```

Se for necessário recriar:

```bash
git remote remove origin
git remote add origin "https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git"
```

## 17.4 Push não funciona

Primeiro verificar:

```bash
git status
git remote -v
git log --oneline --max-count=3
```

Não alterar o repositório aleatoriamente antes de compreender o erro.

## 17.5 Push solicita autenticação

O Git pode solicitar autenticação pelo navegador ou por um mecanismo de credenciais integrado ao sistema ou VS Code.

Concluir a autenticação e aguardar o retorno do comando.

## 17.6 O GitHub não mostra os arquivos

Verificar:

```bash
git status
```

e:

```bash
git log --oneline --max-count=3
```

Depois verificar se o commit foi enviado:

```bash
git push
```

Também confirmar no GitHub se o branch visualizado é:

```text
main
```

---

# 18. Fluxo recomendado para trabalho diário

Antes de iniciar:

```bash
git status
```

Durante o trabalho:

```text
editar
  ↓
validar
  ↓
git diff
```

Ao concluir uma unidade lógica:

```bash
git add <arquivos>
git commit -m "mensagem"
git push
```

Depois confirmar:

```bash
git status
```

---

# 19. Princípio de commits

Um commit deve representar uma alteração lógica coerente.

Evitar commits que misturem, sem necessidade:

```text
documentação
+
código
+
configuração
+
arquivos temporários
```

quando essas mudanças não fizerem parte da mesma unidade lógica.

Preferir commits com finalidade clara.

Exemplos:

```text
docs: atualiza especificacao de requisitos
docs: consolida etapa 3
feat: implementa autenticacao
fix: corrige validacao de senha
test: adiciona testes de autenticacao
refactor: reorganiza camada de servicos
```

---

# 20. Resumo — projeto novo

```bash
git --version
git init
git status
```

Configurar identidade:

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"
```

Adicionar arquivos:

```bash
git add .
git status
```

Criar o commit:

```bash
git commit -m "chore: cria versao inicial"
```

Definir o branch principal:

```bash
git branch -M main
```

Conectar ao GitHub:

```bash
git remote add origin "https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git"
git remote -v
```

Publicar:

```bash
git push -u origin main
```

---

# 21. Resumo — atualização de projeto existente

```bash
git status
git diff
```

Adicionar arquivos:

```bash
git add <arquivos>
git status
```

Criar o commit:

```bash
git commit -m "docs: atualiza projeto"
```

Publicar:

```bash
git push
```

Confirmar:

```bash
git status
```

---

# 22. Resumo do ciclo de versionamento

```text
TRABALHAR
   ↓
VALIDAR
   ↓
VERIFICAR STATUS
   ↓
STAGING
   ↓
COMMIT
   ↓
PUSH
   ↓
VERIFICAR
```

O Git deve ser utilizado como mecanismo de controle de evolução do projeto.

Cada versão importante deve possuir:

* estado identificável;
* histórico;
* mensagem clara;
* rastreabilidade;
* possibilidade de comparação com versões anteriores.

---

# 23. Regra histórica do projeto Skill (não vigente no Adaptive)

No **projeto legado Skill**, `MASTER-SPECIFICATION.md` foi a fonte normativa
para aquela especificação. No Adaptive AI Orchestrator atual, esse arquivo é
**histórico e não autoritativo**. A precedência vigente está em `CONTEXT.md`.

Mudanças conceituais importantes devem ser:

```text
discutidas
   ↓
decididas
   ↓
consolidadas
   ↓
validadas
   ↓
versionadas
   ↓
publicadas
```

Exemplo:

```text
v0.1
→ Etapa 1 e Etapa 2 consolidadas

v0.2
→ Etapa 3 consolidada

v0.3
→ Etapa 4 consolidada
```

O histórico do Git deve preservar a evolução da especificação.
