# PLANO — Opus, controle de falantes e atualização de motores

> Documento vivo. Aberto em 20/08/2026, 17:30. Cada fase é marcada como concluída
> aqui e detalhada no `CHANGELOG.md`. Enquanto houver item pendente, este arquivo
> permanece na raiz; quando tudo fechar, vira entrada de histórico no CHANGELOG.

## TL;DR

Três frentes, executadas em ordem de valor. Primeiro aceitar `.opus` do WhatsApp,
que é correção de uma linha e destrava uso imediato. Depois dar controle sobre o
número de falantes, que é a causa do áudio de uma pessoa ter virado três. Por
último atualizar os três motores (whisper.cpp, sherpa-onnx e os modelos), medindo
antes e depois com áudio real em vez de trocar no escuro.

Todas as medições usam o mesmo áudio de referência, o `WhatsApp Audio 2026-08-11
at 10.57.05.opus`, com 620 s (10min20s), mono 48 kHz, uma pessoa falando. O
pipeline atual devolve 3 speakers nele.

---

## FASE 1 — Aceitar arquivos Opus

**Problema.** `transcribe_wrapper.py` valida a extensão contra uma lista de sete
itens que não inclui `.opus`. O ffmpeg lê opus nativamente, o que foi testado em 20/08 gerando um `.opus` e
extraindo dele o WAV 16 kHz mono, sem erro. A limitação é só da lista.

**O que muda.** Lista passa a incluir `.opus`, `.ogg`, `.oga`, `.aac`, `.flac`,
`.webm`, `.wma`, `.m4v`, `.wmv`, `.aiff`. Mensagem de erro passa a listar os
formatos aceitos de forma agrupada, em vez de enumerar dez extensões.

**Critério de sucesso.** Arrastar o `.opus` de 620 s para o app produz transcrição
completa, sem conversão prévia.

**Estado:** [x] CONCLUÍDA em 20/08/2026 17:31. O `.opus` de 620 s rodou pelo app em
2min57s. Entraram 21 extensões no total.

---

## FASE 2 — Controle do número de falantes

**Problema.** A configuração usa `num_clusters=-1`, o que manda o algoritmo
descobrir sozinho quantas pessoas existem, guiado só pelo threshold de 0,75. Num
áudio de uma pessoa só, variação de tom ao longo de dez minutos atravessa o limiar
e vira falante novo. O pós-processamento não salva, porque só descarta falante com
menos de 10% dos segmentos e o falso falante ficou com bem mais que isso.

**A ressalva que o desenho precisa respeitar.** Nem sempre o número é conhecido. Os
três casos reais de uso:

| Caso | O que se sabe | Tratamento |
|---|---|---|
| Nota de voz do WhatsApp | Exatamente uma pessoa | Número fixo |
| Webinário ou live | Um principal e algumas perguntas da plateia, quantidade desconhecida | Teto, não número fixo |
| Reunião ou aula | Nada | Automático, como hoje |

Forçar número fixo no webinário seria pior que o problema original, porque
descartaria quem fez pergunta. Daí o desenho ter dois parâmetros e não um.

**O que muda em `transcribe_complete.py`.**

- `--speakers N`. Força exatamente N falantes (`num_clusters=N`). Desativa o
  pós-processamento de fusão, porque se o número foi declarado não faz sentido o
  script reduzir abaixo dele.
- `--max-speakers N`. Teto. Roda a detecção automática e, se o resultado passar de
  N, refaz com `num_clusters=N`. Pós-processamento continua ativo.
- Sem nenhum dos dois, o comportamento atual permanece inalterado.

**O que muda no pós-processamento.** O corte hoje conta segmentos. Um falante que
fez uma pergunta de vinte segundos num webinário de uma hora tem poucos segmentos e
seria apagado. Passa a contar tempo total de fala, com corte proporcional à duração
do áudio. O corte deixa de se aplicar quando o número foi declarado.

**O que muda no app (sem terminal).** O droplet passa a abrir uma janela de escolha
ao receber o arquivo, com cinco opções em português. A escolha vira o parâmetro
correspondente. Nenhuma delas exige saber o que é threshold ou cluster.

**Critério de sucesso.** O áudio de referência com a opção "1 pessoa" produz
transcrição sem marcador de falante. Um webinário com a opção correspondente
preserva quem fez pergunta.

**Estado:** [x] CÓDIGO CONCLUÍDO em 20/08/2026. `--speakers`, `--max-speakers` e
`--embedding` no script; pós-processamento por tempo de fala; droplet recompilado
com as seis opções, testadas isoladas. Falta o teste ponta a ponta pelo app, que o
Danilo faz arrastando um arquivo.

---

## FASE 3 — Atualização dos motores

| Componente | Instalado | Alvo |
|---|---|---|
| whisper.cpp | 1.8.3 | 1.9.2 |
| sherpa-onnx (Python) | 1.12.18 | 1.13.6 |
| Modelo de transcrição | ggml-medium (1,53 GB) | ggml-large-v3-turbo (1,62 GB) |
| Modelo de embedding | eres2net **base**, treinado em mandarim | a definir por medição |

**Sobre o modelo de embedding.** É ele que decide se duas vozes são da mesma
pessoa. O atual é a menor variante da família, treinada em mandarim. Quatro
candidatos entram em teste com o mesmo áudio de referência e a escolha sai da
medição:

- `nemo_en_titanet_large.onnx` (97 MB). TitaNet-Large da NVIDIA
- `3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx` (27 MB). Bilíngue
- `wespeaker_en_voxceleb_resnet34_LM.onnx` (26 MB). VoxCeleb
- `3dspeaker_speech_eres2net_sv_zh-cn_16k-common.onnx` (224 MB). Mesma família do
  atual, versão grande, serve para separar o efeito do idioma do efeito do tamanho

**Sobre o large-v3-turbo.** É mais rápido que o medium, porque tem 4 camadas de
decodificação contra 24 do large original. Sobre ser mais preciso em português, não
há como afirmar daqui.

**Protocolo de comparação, corrigido em 20/08/2026.** Cheguei a afirmar que uma
transcrição estava melhor que outra comparando os dois textos entre si. Foi um erro.
A palavra que julguei corrigida ("gatinha" virando "Catinha") era justamente a que
estava certa antes, porque o assunto era a gata do interlocutor, que tinha morrido.
Quem sabe o que foi dito é quem estava na conversa.

Daí o protocolo passa a ser este. Os dois modelos rodam sobre o mesmo trecho, sai um
arquivo só com os pontos em que discordam, numerados, para o Danilo marcar qual
acertou em cada um. A contagem decide. Sem esse passo, a troca de modelo de transcrição não
acontece.

O critério da diarização é diferente e não precisa dele, porque ali existe verdade
conhecida. O áudio de referência tem uma pessoa, então detectar 1 é acerto e
qualquer número acima disso é erro.

**Ordem de execução.** Modelo de embedding primeiro, com o whisper antigo, para
isolar a variável. Depois o whisper. Cada troca medida sozinha.

**Critério de sucesso.** Tabela no CHANGELOG com falantes detectados e tempo de
processamento para cada combinação, mais uma escolha justificada por número.

**Estado:** em 21/08/2026.
- [x] `whisper-cpp` 1.8.3 → 1.9.2
- [x] `sherpa-onnx` 1.12.18 → 1.13.6, o que resolveu segfault em dois modelos
- [x] Medição dos cinco embeddings em dois áudios com verdade conhecida
- [x] Desempate na aula de duas vozes, resolvido pelo ouvido do Danilo
- [x] Modelo escolhido e aplicado: wespeaker resnet34 LM, limiar 0,92
- [x] Droplet remapeado: teto em vez de número fixo, de duas pessoas em diante
- [x] Escolha do modelo de transcrição: `large-v3-turbo`, por 23 a 11 nas 39
      marcações do Danilo, conferido contra laço em áudio de 1h09

---

## FASE 4 — Registro e publicação

- CHANGELOG com problema, causa, solução e medições de cada fase
- README atualizado (formatos aceitos, opções de falante, modelos em uso)
- Commit e push para `github.com/daniloblima/whisper-transcription`

O repositório é público. Os modelos baixados não entram no commit; conferir o
`.gitignore` antes de publicar.

**Estado:** em 21/08/2026. CHANGELOG e README escritos, commit feito. A tabela de
resultados do README, que era de dezembro/2024 e media outra coisa, foi substituída
pela comparação dos cinco modelos de voz.

---

## Riscos conhecidos

**O modelo maior pode não melhorar.** Modelo de embedding treinado em inglês ou
mandarim aplicado a português é aposta razoável, não certeza. Se a medição não
mostrar ganho, o parâmetro de falantes da Fase 2 continua resolvendo o caso
principal sozinho. A troca de modelo é descartada em vez de mantida por ter dado
trabalho.

**O turbo pode degradar em português.** É modelo destilado. A medição decide. De
qualquer forma o `ggml-medium.bin` continua em disco.

**~~Uma única amostra não é evidência forte.~~** RESOLVIDO em 20 e 21/08/2026. O
Danilo forneceu uma aula do Nutror com duas vozes conhecidas, 1h09min22s, e ela
mudou a decisão: o TitaNet, que empatava no áudio de uma pessoa, perdeu na aula.
Sem esse segundo áudio, a escolha teria sido no cara ou coroa.

**Contar falantes não é separar falantes.** Descoberto na aula. Três configurações
devolveram o número certo de falantes, e duas delas o fizeram colando as duas vozes
numa e sobrando um resto de 2 minutos. Qualquer medição futura de diarização olha a
distribuição de tempo junto com a contagem.


---

## Fechamento — 21/08/2026

As três fases estão concluídas. Os dois motores do projeto foram trocados por
medição em áudios reais do Danilo, não por reputação de modelo.

| o quê | antes | depois |
|---|---|---|
| formatos aceitos | 7 | 21, com `.opus` do WhatsApp |
| controle de falantes | nenhum | `--speakers`, `--max-speakers`, seis opções no app |
| modelo de voz | eres2net base zh-cn, 40 MB | wespeaker resnet34 LM, 26 MB |
| limiar | 0,75 | 0,92 |
| modelo de transcrição | `medium` | `large-v3-turbo` |
| whisper.cpp | 1.8.3 | 1.9.2 |
| sherpa-onnx | 1.12.18 | 1.13.6 |

Medida do ganho, na aula de 1h09 com duas pessoas: de 7 falantes detectados para 2,
separados nos pontos certos.

## O que ficou aberto

**Filtro de muletas de fala.** Princípio acordado com o Danilo: transcrever fiel e
gerar a versão limpa ao lado da bruta, nunca por cima. Os inequívocos ("ãh", "hum")
por regra fixa; os ambíguos ("né", "tipo", "assim") pela skill, porque as mesmas
palavras têm uso legítimo. Régua vinda da revisão dele: quando não dá para pontuar
corretamente uma muleta, omitir causa menos dano que incluir sem a vírgula.

Não iniciado por decisão de escopo. Vale como frente própria, e ela deveria começar
medindo quais muletas aparecem de fato nas transcrições existentes, do mesmo jeito
que o `glossario.json` nasceu das correções reais em vez de uma lista inventada.

**Negação sem vírgula.** Encerrado sem construir nada, por decisão do Danilo em
21/08/2026. Ver CHANGELOG.
