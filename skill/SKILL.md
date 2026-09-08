---
name: arrumar-transcricao
description: Corrige transcrições automáticas (Whisper, etc.) de reuniões, webinares, áudios, vídeos, podcasts e sessões de consultoria. Use quando o usuário fornecer um arquivo de transcrição para correção ou diarização. Subcomandos: /arrumar-transcricao:corrigir.
---

# Skill: Arrumar Transcrição

Corrige transcrições automáticas (Whisper, etc.) de qualquer tipo de conteúdo: reuniões, webinares, áudios, vídeos, podcasts, sessões de consultoria.

## Onde esta skill mora

Dentro do projeto `~/Experimentos/whisper-transcription/skill/`, acessível de qualquer pasta pelo symlink em `~/.claude/skills/arrumar-transcricao`. Ela vive junto do projeto porque divide com ele o mesmo glossário.

## Divisão de trabalho com o glossário

O `transcribe_complete.py` já aplica sozinho, no passo 5 de toda transcrição, o `glossario.json` do projeto. Ele trata só o erro cujo acerto é sempre o mesmo, independente do assunto: nome próprio, sigla, marca, termo técnico. Isso significa que ao receber um arquivo recém-transcrito, esses erros já estão corrigidos.

O que sobra para esta skill é tudo que exige contexto, e é a maior parte do volume:

- Palavra comum do português trocada por outra palavra comum. Medido nos arquivos já corrigidos: "livro" por "líder", "ganho" por "gancho", "lixo" por "lítio", "testa" por "estratégia", "Canva" por "Notion". Nenhuma regra fixa acerta isso, porque as duas palavras existem e só o assunto decide.
- Sigla curta demais para substituição automática: NP por ANP, ES por AES, IMP por INPE, PIP por PIPE.
- Nome próprio legítimo que naquele áudio é outra pessoa: Vitor por Victor, Iara por Yara.
- Sigla em minúscula que colide com palavra comum. Caso real: o Whisper escreveu "a anel regula o setor elétrico", que é ANEEL, e o glossário não pode tocar porque destruiria "anel de vedação".
- Diarização, junção indevida de falas e identificação de quem fala.

Desde 08/09/2026 há uma terceira camada entre as duas: os dicionários por tema, em `dicionarios/<tema>/`. Eles guardam o que só vale dentro de um assunto — `Marco Polo` para `Marcopolo` numa conversa sobre carrocerias, que estragaria qualquer áudio onde ele é o viajante. Rodar `python3 dicionarios.py --sugerir "<o contexto que o usuário deu>"` propõe quais carregar; a transcrição os aplica com `--tema <nome>`, e mais de um pode ser usado ao mesmo tempo.

Ao propor termo novo no fim da correção, dizer também onde ele entra: no glossário geral, se o acerto valeria em qualquer áudio sobre qualquer assunto, ou num dicionário de tema, se depende do assunto. O teste é o mesmo de sempre, agora com três destinos em vez de dois.

Antes de começar, vale abrir o `glossario.json` para saber o que já foi tratado e não perder tempo procurando erro que o script já corrigiu. Se existir um arquivo `*_termos-corrigidos.md` ao lado da transcrição, ele lista exatamente o que foi trocado nela.

## Subcomandos

| Comando | Função |
|---------|--------|
| /arrumar-transcricao:help | Mostra como usar a skill |
| /arrumar-transcricao:corrigir | Executa o fluxo completo de correção |

## Fluxo de trabalho

Arquivo de transcrição + contexto do usuário → coleta → análise → dúvidas → correção → arquivo final

O usuário fornece o arquivo, o tema, as referências e responde as dúvidas. Claude faz a análise, corrige e gera o arquivo final.

## A correção não se aplica à mão

Desde 04/09/2026, nenhuma correção se aplica editando o arquivo. Toda troca se declara num JSON e passa pelo `aplicar_correcoes.py`, na raiz do projeto. O formato está em `FORMATO-CORRECOES.md`.

O motivo é medido, e está na parte 4 do `LICOES-APRENDIDAS.md`. Os cinco erros mais caros do acervo de 50 aulas foram cometidos por sessão de Claude editando o `.md` direto: três apagaram fala do palestrante, um inventou um país que ninguém disse e um trocou um nome por contaminação do vizinho. Nenhum deixou rastro, e a auditoria só foi possível por acidente.

O aplicador recusa a corrida inteira, sem escrever nada, quando a contagem de ocorrências não bate com a declarada, quando a troca apaga fala sem declaração explícita, ou quando um carimbo de tempo ou marcador de falante desaparece. Ele também preserva o carimbo que fica no meio de uma expressão de várias palavras, que é o padrão 7 e comeu 34 carimbos em 16 arquivos.

Na prática, o que muda no seu trabalho: em vez de aplicar a correção, você a escreve na declaração com `motivo` e `origem`, roda com `--dry-run` para conferir as contagens, e só então aplica. O backup e o log saem de graça.

## Etapas

### 1. Coleta de contexto
Perguntar ao usuário usando AskUserQuestion:
- Qual o tema/assunto da transcrição?
- Tem referências para fornecer? (arquivos, URLs, textos, glossários, nomes de pessoas)
- Quer separar falantes? Se sim, quais são os nomes?
- Formato de saída desejado? (MD, TXT, ou manter o formato original)

Se o usuário já forneceu parte dessas informações na mensagem inicial, não perguntar de novo. Preencher o que falta.

### 2. Leitura e análise

Antes de ler, rodar `python3 varrer_suspeitas.py <arquivo ou pasta>`. Ele devolve um `00 A RESOLVER na revisão.md` com os pontos que merecem olho: inversão de sentido, alucinação de legendagem, sigla ou nome grafado de dois jeitos, capitalizada rara ao lado de forma parecida frequente, `%` colado em ano e cicatriz de substituição. Ele não corrige nada e erra bastante — a fila é ponto de partida da leitura, não conclusão.

A varredura rende mais sobre transcrição recém-saída do motor. Sobre material já revisado, a maior parte do que ela aponta é legítima.

Depois, ler o arquivo e classificar erros em 3 categorias:

**Erros óbvios** (corrigir sem perguntar):
- Palavras que não existem em português
- Nomes próprios claramente deformados pelo Whisper
- Termos técnicos do tema que foram mal transcritos (usando as referências fornecidas)
- Acentuação errada em nomes e termos técnicos

**Erros de contexto** (corrigir sem perguntar, mas listar na entrega):
- Palavras que existem mas estão erradas dado o tema (ex: "Ares" por "Áries", "Newton" por "Netuno")
- Gênero errado de pronomes/adjetivos quando se sabe quem fala
- Palavras sonoramente parecidas trocadas pelo Whisper

**Dúvidas** (perguntar ao usuário):
- Trechos ambíguos onde há mais de uma interpretação possível
- Palavras que podem ser gíria, expressão regional ou erro
- Nomes próprios que não constam nas referências

### 3. Human in the loop
- Apresentar dúvidas ao usuário usando AskUserQuestion (máximo 4 perguntas por rodada)
- Cada pergunta deve incluir o trecho original, a linha aproximada e opções de correção
- Repetir rodadas até esgotar as dúvidas
- Nunca inventar correção quando em dúvida

### 4. Correção e diarização
- Escrever todas as correções (óbvias + contexto + respostas do usuário) numa declaração JSON e aplicá-la com `aplicar_correcoes.py`. Nunca editar o arquivo direto — ver a seção acima
- Se diarização pedida: reclassificar falantes com base no contexto
  - Critérios: quem pergunta vs quem responde, pronomes usados, conteúdo da fala, alternância natural de diálogo
  - Substituir labels genéricos (SPEAKER_0, SPEAKER_1) pelos nomes reais
  - Formato: `[timestamp] **Nome:** texto`
- Manter timestamps sempre
- Quando o Whisper junta falas de pessoas diferentes numa mesma linha, separar em linhas distintas

### 5. Geração do arquivo
- Salvar no mesmo diretório do original
- Nome: `[nome_original]_corrigido.[extensão_escolhida]`
- Cabeçalho com metadados: título, data (se identificável), participantes (se diarização ativa)

### 6. Verificação
- Grep pelos termos errados mais recorrentes para confirmar que foram todos corrigidos
- Se diarização ativa: grep por "SPEAKER_" para confirmar que nenhum label genérico restou
- A contagem de carimbos e marcadores já é feita pelo aplicador, que aborta se algum sumir. O relatório de cada corrida fica em `_correcoes/<data-hora>/`

### 7. Alimentar o glossário

Esta etapa é o que faz a correção de hoje poupar trabalho amanhã. Sem ela, o mesmo erro é redescoberto a cada transcrição.

Ao terminar, revisar as correções aplicadas e separar as que se qualificam para o `glossario.json`. Uma correção se qualifica quando o acerto seria o mesmo em qualquer áudio, sobre qualquer assunto. O teste é direto: se a mesma palavra errada pudesse aparecer numa transcrição de outro tema e a correção continuasse valendo, ela entra.

Entra: nome próprio deformado ("Minquedinho" por LinkedIn), marca ("Substeck" por Substack), sigla inequívoca ("em Brapi" por EMBRAPII), nome de empresa, termo técnico que não existe em português ("hidralétrica").

Onde gravar: `glossario.json` é público, então termo ligado a pessoa ou empresa com quem o Danilo trabalha vai para `glossario.local.json`, que está no `.gitignore`. Mesmo formato, e o script lê os dois somados. Na dúvida sobre um nome, perguntar antes de gravar no público.

Não entra: palavra comum trocada por palavra comum, sigla de duas ou três letras, nome próprio que também é nome de outra pessoa, e qualquer correção cuja substituição se acumularia ao rodar duas vezes (o caso de "vesta" para "Vesta Greentech", que viraria "Vesta Greentech Greentech").

Regra de segurança para termo novo: se a palavra errada também existe em português com outro sentido, marcar `"exato": true`, o que exige casamento idêntico de maiúsculas. Foi assim que ANEL virou ANEEL sem destruir "anel de vedação".

Apresentar os candidatos ao usuário antes de gravar, com o motivo de cada um, e escrever no arquivo apenas os aprovados. Depois de gravar, rodar `python3 corrigir_termos.py <arquivo>` uma vez para conferir que o glossário continua carregando sem erro de formato.

## Regras de correção

### Preservar
- Fala coloquial natural: gírias, contrações, "né", "tá", "ó", hesitações
- Interjeições que fazem sentido no contexto
- Erros gramaticais de quem fala (transcrição não é texto formal)
- Repetições naturais da fala ("de, de, de")

### Corrigir
- Palavras que o Whisper inventou ou deformou
- Nomes próprios e termos técnicos
- Acentuação de nomes e termos
- Junção indevida de falas de pessoas diferentes

### Nunca fazer
- Reescrever frases para "melhorar" a fala
- Remover hesitações ou repetições naturais
- Adicionar pontuação formal onde a fala é informal
- Inventar correção quando há dúvida (perguntar ao usuário)
- Corrigir gramática da fala oral

## Aprendizados do lote de 47 aulas (01/09/2026)

Primeira vez que a skill enfrentou volume grande de uma vez: 47 transcrições, 200 mil palavras, 673 correções. O detalhe de cada padrão está em `PADROES-DE-ERRO.md`, na raiz do projeto. O que muda para a skill:

### Três erros invertem o sentido sem quebrar a frase

São os únicos perigosos, porque a frase continua gramatical e o leitor absorve o contrário do que foi dito.

1. **O prefixo "des" some.** "desigual" vira "igual". Apareceu quatro vezes, sempre em trecho cujo parágrafo argumentava o oposto.
2. **"sofisticação" vira "simplificação".** Duas vezes, invertendo a tese do material.
3. **O "%" gruda em ano.** "em 82%" onde se lê "em 82". Não corrigir por script onde o texto mistura anos e percentuais.

Vale começar toda revisão buscando "mais igual", "mais iguais" e "simplificação", e lendo o parágrafo em volta.

### Erro do palestrante não é erro de transcrição

Quando o material traz afirmação factualmente errada dita pela própria pessoa, a transcrição está certa. **Política definida por Danilo em 01/09/2026:** não mexer no texto. Inserir uma `NOTA DE VERIFICAÇÃO` no ponto exato, com o fato correto, e um aviso no cabeçalho do arquivo, para quem abrir saber de saída que há afirmação incorreta ali dentro.

### Não completar o nome que o falante encurtou

Corrigir o nome errado, na forma que o falante usa. Se ele diz "Albert Barabási", não virar "Albert-László Barabási", ainda que esse seja o nome completo. E quando o primeiro nome está errado de um jeito que pode ter sido erro do palestrante, e não da máquina, a troca deixa de ser fiel ao áudio: isso vai para a lista de decisões do dono do material, não para a correção automática.

### Método, para correção em lote

- **Fazer backup antes**, e no fim rodar um diff palavra a palavra contra ele. É o único jeito de auditar o que se fez.
- **Contar o que deveria ser invariante:** carimbos de tempo, marcadores de falante, número de arquivos. Substituição de expressão com várias palavras come o carimbo que fica entre elas, e isso não aparece na leitura do texto. Aconteceu: 34 carimbos perdidos em 16 arquivos, descobertos só porque Danilo desconfiou de outra coisa.
- **Ao substituir expressão de várias palavras**, capturar os separadores como grupos e recolocá-los entre as palavras novas.

### A terceira camada é entregável

Depois do glossário e da leitura de contexto, o que sobra vira documento com **aula e instante de cada dúvida**, para o dono ouvir o trecho e decidir. Sem isso a correção vira caixa-preta. No curso conferido esse documento tinha 27 pontos em quatro grupos, e Danilo resolveu todos numa passada.

## Prioridade de fontes
1. Respostas do usuário (maior prioridade)
2. Referências fornecidas (arquivos, URLs, glossários)
3. Conhecimento do modelo sobre o tema (menor prioridade)
