# 🎤 Transcrição com Diarização

Sistema local completo para transcrição de áudio/vídeo com identificação de speakers (quem fala quando).

**Tecnologias:**
- **Whisper.cpp 1.9.2** - Transcrição rápida (7-10x mais rápido que Python)
- **Sherpa-ONNX 1.13.6** - Identificação de quem fala
- **Pós-processamento por tempo de fala** - Descarta falante espúrio sem apagar quem
  fez uma pergunta curta

---

## 🚀 USO RÁPIDO (GUI - RECOMENDADO)

### Opção 1: Interface Gráfica (Arrasta e Solta)

1. **Abra o app**: `~/Applications/TranscribeVideo.app`
2. **Arraste seu vídeo** para o ícone do app
3. **Aguarde a notificação** de conclusão (com tempo total)
4. **Encontre o arquivo** em `~/Downloads/Transcricoes/nome_do_video/`

**Formatos suportados**

Vídeo: MP4, MOV, AVI, MKV, WEBM, M4V, WMV, FLV, MPG
Áudio: MP3, WAV, M4A, OPUS, OGG, AAC, FLAC, WMA, AIFF

O OPUS é o formato das notas de voz do WhatsApp. Arraste o arquivo como veio, sem
converter nada antes.

**O app pergunta quantas pessoas falam.** A janela aparece assim que você solta o
arquivo, com seis opções:

```
Não sei, deixar o app decidir
1 pessoa (nota de voz, gravação sua)
2 pessoas (entrevista, conversa)
3 pessoas
Webinário ou live (um principal, mais perguntas da plateia)
Reunião ou aula (até 8 pessoas)
```

Responder faz diferença. Deixado por conta própria, o app já identificou três
pessoas diferentes num áudio de dez minutos em que só uma falava. As opções de
número exato eliminam isso. A opção de webinário funciona como teto e não como
número fixo, então quem faz uma pergunta da plateia continua aparecendo separado do
palestrante.

**Resultado:** Arquivo `nome_do_video_transcrito.md`, já com os termos do
glossário corrigidos:
```
**SPEAKER_0**

`[0:00:12]` Olá, bem-vindos à apresentação de hoje...

**SPEAKER_1**

`[0:00:47]` Obrigado pela introdução, vamos começar...
```

---

### Opção 2: Terminal (Mais Opções)

```bash
cd ~/Experimentos/whisper-transcription

# Ativar ambiente virtual
source whisper_transcription_env/bin/activate

# Transcrever vídeo ou áudio
python3 transcribe_complete.py "caminho/para/seu/video.mp4"
```

---

## ⚙️ OPÇÕES

### Escolher modelo Whisper
```bash
python3 transcribe_complete.py video.mp4 --model tiny   # Rápido
python3 transcribe_complete.py video.mp4 --model medium # Padrão  
python3 transcribe_complete.py video.mp4 --model large  # Preciso
```

### Dizer quantas pessoas falam
```bash
python3 transcribe_complete.py audio.opus --speakers 1        # número exato
python3 transcribe_complete.py webinario.mp4 --max-speakers 5 # teto
```

`--max-speakers` é o que você quer na maioria dos casos, inclusive quando sabe o
número. Ele roda a detecção livre e, se ela passar do limite, sobe o limiar até
caber, mantendo a estratégia de agrupamento que funciona.

`--speakers` fixa o número, o que faz o agrupamento trocar de estratégia e ignorar o
limiar. **Isso costuma piorar de duas pessoas em diante.** Medido em 21/08/2026 numa
aula de 1h09 com duas vozes: com o número fixo o resultado foi 67 minutos para um
falante e 2 para o outro, colando as duas vozes numa; no modo livre com limiar 0,92
foi 12 e 57, que é a divisão correta. Use `--speakers` para uma pessoa só, onde não
há o que colar.

### Ajustar sensibilidade de speakers
```bash
python3 transcribe_complete.py video.mp4 --threshold 0.85  # Menos speakers
python3 transcribe_complete.py video.mp4 --threshold 0.65  # Mais speakers
```

---

## 📊 ETAPAS DO PROCESSAMENTO

1. **Extração de áudio** - FFmpeg converte para WAV
2. **Transcrição** - Whisper.cpp transcreve
3. **Diarização** - Sherpa-ONNX identifica speakers
4. **Mesclagem** - Combina transcrição + diarização
5. **Correção de termos** - Aplica o `glossario.json`

**Tempo para vídeo de 1h:** ~16-18 minutos

---

## ✏️ CORREÇÃO DE ERROS DO WHISPER

A transcrição sai com erros, e eles têm duas naturezas diferentes. Cada uma tem
seu tratamento.

### Erro que é sempre o mesmo → automático, passo 5

Nome próprio, sigla, marca e termo técnico que o Whisper deforma sempre igual.
Corrigido sozinho em toda transcrição, sem custo e sem você pedir.

| Whisper escreve | Vira |
|---|---|
| Minquedinho | LinkedIn |
| Substeck | Substack |
| Connect Lab | konekt.lab |
| em Brapi | EMBRAPII |
| hidralétrica | hidroelétrica |

São 33 termos, extraídos das correções que já tinham sido feitas à mão.

**Para adicionar um termo:** abra `glossario.json` na IDE, copie um bloco e edite.
O próprio arquivo explica os campos no topo.

**Dois arquivos, e o motivo:** este repositório é público. O `glossario.json`
guarda termo genérico e de organização pública; nome de pessoa ou empresa com
quem você trabalha vai para o `glossario.local.json`, que está no `.gitignore` e
não sai da sua máquina. Mesmo formato nos dois, e o script lê os dois somados.
Se o local não existir, tudo funciona igual.

**Onde conferir o que foi trocado:** ao lado de cada transcrição nasce um
`nome_transcrito_termos-corrigidos.md` listando cada substituição e quantas vezes.

**Para pular a etapa:** `--sem-glossario`.

**Para corrigir um arquivo antigo:**
```bash
python3 corrigir_termos.py ~/Downloads/Transcricoes/pasta/arquivo.md
```

### Erro que depende do contexto → skill `/arrumar-transcricao`

Palavra comum trocada por outra palavra comum ("livro" por "líder", "lixo" por
"lítio"), sigla curta (NP por ANP), nome de pessoa, junção de falas, diarização.
Nenhuma regra fixa acerta isso: as duas palavras existem e só o assunto decide.

Abra uma sessão de Claude Code e peça a correção do arquivo. A skill pergunta o
tema, aceita referências, tira dúvidas antes de corrigir e, ao final, propõe os
termos novos que merecem entrar no glossário — é assim que a correção de hoje
poupa trabalho na próxima.

A skill mora em `skill/`, dentro deste projeto, com symlink em
`~/.claude/skills/arrumar-transcricao`.

---

## 🛠️ SCRIPTS DISPONÍVEIS

### transcribe_complete.py ⭐ (RECOMENDADO)
Faz tudo automaticamente: os 5 passos, da extração de áudio à correção de termos.

### corrigir_termos.py
Aplica só o glossário, sobre um arquivo de transcrição já existente. Útil para
recuperar transcrições antigas, feitas antes de o glossário existir.

### diarize_with_postprocessing.py
Apenas identifica speakers (sem transcrição).

---

## 📁 ESTRUTURA

```
whisper-transcription/
├── transcribe_complete.py          ⭐ Script principal (Terminal)
├── transcribe_wrapper.py           🖥️ Wrapper GUI (notificações)
├── diarize_with_postprocessing.py  🎯 Diarização
├── corrigir_termos.py              ✏️ Correção de termos (passo 5)
├── glossario.json                  📖 Termos que o Whisper erra sempre igual
├── skill/                          🧠 Skill /arrumar-transcricao
├── whisper_transcription_env/      📦 Python env
├── whisper-cpp-models/             🧠 Modelos Whisper
├── sherpa-onnx-models/             🎤 Modelos diarização
├── CHANGELOG.md                    📝 Histórico técnico completo
└── README.md                       📖 Este arquivo

~/Applications/
└── TranscribeVideo.app             🎬 Droplet GUI (arrasta e solta)

~/.claude/skills/
└── arrumar-transcricao ->          🔗 symlink para skill/

~/Downloads/Transcricoes/
└── [nome_do_video]/                        📂 Saída organizada
    ├── [nome]_transcrito.md                📄 Transcrição final
    └── [nome]_transcrito_termos-corrigidos.md  📋 O que o glossário trocou
```

---

## 🎯 MODELOS EM USO, E POR QUÊ

### Transcrição
`whisper-cpp-models/ggml-medium.bin`. O `ggml-large-v3-turbo.bin` está em disco e é
mais rápido. A troca depende de uma comparação de qualidade que só quem gravou o
áudio pode julgar.

### Identificação de quem fala
`sherpa-onnx-models/wespeaker_en_voxceleb_resnet34_LM.onnx`, 26 MB, com limiar 0,92.

Escolhido em 21/08/2026 por medição em dois áudios com verdade conhecida. O que o
projeto usava antes, o `3dspeaker_speech_eres2net_base_sv_zh-cn`, identificava 7
pessoas numa aula onde falavam 2. Numa nota de voz onde falava 1, identificava 2.

| modelo | nota de voz (1 pessoa) | aula 1h09 (2 pessoas) | tamanho |
|---|---|---|---|
| eres2net base zh-cn (o antigo) | 2 ❌ | 7 ❌ | 40 MB |
| campplus zh+en | 2 ❌ | não testado | 28 MB |
| eres2net grande zh-cn | 1 ✅ | não testado, 5x mais lento | 224 MB |
| TitaNet-Large | 1 ✅ | 4 ❌ | 97 MB |
| **wespeaker resnet34 LM** | **1 ✅** | **2 ✅** | **26 MB** |

O empate entre TitaNet e wespeaker foi desfeito ouvindo um trecho da aula, porque
contar dois falantes não prova que a separação está certa. Detalhe completo no
CHANGELOG.

### Como baixar os modelos
Os modelos não vão para o repositório. Numa instalação nova:

```bash
cd sherpa-onnx-models
curl -LO https://huggingface.co/csukuangfj/speaker-embedding-models/resolve/main/wespeaker_en_voxceleb_resnet34_LM.onnx

cd ../whisper-cpp-models
curl -LO https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin
```

O modelo de segmentação (`sherpa-onnx-pyannote-segmentation-3-0`) vem do mesmo
catálogo do Sherpa e não mudou.

---

Criado: Dezembro 2024 | Última revisão de motores: 21/08/2026
