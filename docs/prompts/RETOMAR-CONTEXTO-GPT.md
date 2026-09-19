# Prompt básico — retomada de contexto no GPT

Use este modelo para abrir uma nova janela de contexto em GPT/ChatGPT e reconstruir rapidamente o estado de desenvolvimento de um projeto a partir dos arquivos disponíveis.

Este é um **baseline genérico**, não um contrato rígido. Dependendo do projeto, da maturidade, da fase atual, dos riscos e da quantidade de contexto perdido, o prompt pode ser **menor** ou **bem mais detalhado**. Projetos com governança própria devem acrescentar seus arquivos, regras e fontes de verdade específicas.

## Prompt

```text
Retome o contexto de desenvolvimento deste projeto a partir dos arquivos disponíveis.

1. Leia primeiro o handoff canônico definido pelo próprio projeto. Se não houver uma convenção explícita e existir `HANDOFF.md`, use-o como ponto inicial.
2. A partir do handoff, leia somente os arquivos de contexto, governança, arquitetura, requisitos ou etapa atual que forem necessários para reconstruir o estado corrente. Não faça uma varredura ampla sem necessidade.
3. Se tiver acesso ao repositório, confirme branch, estado da working tree e WIP existente. Se não tiver esse acesso, deixe essa limitação explícita.
4. Não invente estado ausente e não trate memória de conversa como mais autoritativa que os arquivos correntes do projeto.
5. Durante esta retomada, não altere arquivos nem execute mudanças no projeto. O objetivo é apenas reconstruir o contexto.

Comece com um resumo curto contendo:
- objetivo/linha de trabalho atual;
- fase ou etapa em andamento;
- WIP relevante;
- principal pendência ou blocker conhecido;
- próximo passo seguro;
- fontes principais consultadas.

Depois aguarde meu próximo comando.
```

## Ajuste de tamanho

Use este texto como ponto de partida. Para um projeto simples ou uma retomada muito recente, ele pode ser reduzido. Para uma fase crítica, migração, incidente, release, mudança arquitetural ou projeto com governança forte, acrescente explicitamente os documentos, invariantes, gates, ambientes, limitações de autoridade e verificações necessários.
