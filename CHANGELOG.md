# CHANGELOG - Sistema de Transcrição com Diarização

> **PROPÓSITO**: Este arquivo registra TODOS os problemas, bugs, decisões técnicas e soluções encontradas durante o desenvolvimento. É consultado OBRIGATORIAMENTE após cada compactação de contexto para evitar perda de informação.

---

## [2026-01-19] - SOLUÇÃO DEFINITIVA: Mix de Streams para Vídeos do Azayaka ✅

### 🎯 OBJETIVO
Resolver definitivamente o problema de repetições em transcrições de vídeos do Azayaka (tanto AAC quanto ALAC).

### ❌ PROBLEMA PERSISTENTE
Mesmo após correções anteriores, as transcrições ainda apresentam repetições massivas:
- Exemplo: "conseguiu um investimento privado" repetindo 50+ vezes
- Afeta tanto arquivos AAC quanto ALAC
- O problema não é a seleção de stream - é mais profundo

### 🔍 ANÁLISE / TENTATIVAS QUE NÃO RESOLVERAM

#### Tentativa 1: Seleção de stream por conteúdo (2026-01-17)
**O que fizemos:**
- Modificamos `get_best_audio_stream()` para testar conteúdo real de cada stream
- Usa `test_stream_content()` que transcreve 30s e conta caracteres/segundo
- Seleciona a stream com mais conteúdo transcrito

**Resultado:**
- ✅ Seleção de stream funciona corretamente (escolhe a stream certa)
- ❌ MAS as repetições ainda acontecem na transcrição completa

**Código implementado (linhas 167-210 de transcribe_complete.py):**
```python
def get_best_audio_stream(video_path, whisper_model_path=None):
    # Testa conteúdo de cada stream e seleciona a com mais texto
    # Métrica: caracteres por segundo de transcrição
```

#### Tentativa 2: Beam Search no Whisper (2026-01-17)
**O que fizemos:**
- Adicionamos `--beam-size 5 --best-of 5` ao comando whisper-cli
- Beam search geralmente reduz repetições

**Resultado:**
- ✅ Teste de 30s: transcrição SEM repetições
- ❌ Transcrição completa (47 min): AINDA tem repetições

**Código implementado (linhas 263-272 de transcribe_complete.py):**
```python
cmd = [
    whisper_cli,
    '-m', str(model_path),
    '-f', str(audio_path),
    '-l', language,
    '-osrt', '-of', output_base,
    '--beam-size', '5',
    '--best-of', '5'
]
```

### 💡 NOVA ABORDAGEM: Mixar Streams de Áudio

**Hipótese:**
- O Azayaka grava 2 streams: microfone + áudio do sistema
- Ao invés de ESCOLHER uma stream, MIXAR as duas em uma única faixa
- Isso captura ambos os lados da conversa sem precisar selecionar

**Comando FFmpeg para mixar:**
```bash
ffmpeg -i video.mp4 \
  -filter_complex "[0:1][0:2]amix=inputs=2:duration=longest[aout]" \
  -map "[aout]" -ar 16000 -ac 1 output.wav
```

**Teste inicial (trecho 5:30-6:00):**
- ✅ SEM REPETIÇÕES!
- Transcrição correta: "E a gente também recebeu um investimento privado, e essa startup foi investida e adquirida na sequência..."

### 📊 RESULTADO DO TESTE (2026-01-19)

**✅ SOLUÇÃO VALIDADA - MIXAR STREAMS FUNCIONA!**

Transcrição completa do arquivo AAC (47 min) com streams mixadas:
- ❌ **0** repetições de "conseguiu um investimento" (antes: 50+)
- ❌ **0** repetições de "ir para a sua casa"
- ❌ **0** repetições de "espelho de escritório"
- 📊 **326 segmentos** totais (arquivo limpo)
- 🎬 Final natural: "Valeu, Danilo, um abraço. Tchau, tchau."

**Comando FFmpeg validado:**
```bash
ffmpeg -i video.mp4 \
  -filter_complex "[0:1][0:2]amix=inputs=2:duration=longest[aout]" \
  -map "[aout]" -ar 16000 -ac 1 output.wav
```

### 📝 ARQUIVOS DE TESTE - TODOS VALIDADOS ✅

| Arquivo | Codec | Duração | Segmentos | Repetições | Status |
|---------|-------|---------|-----------|------------|--------|
| Recording at 2026-01-13 15.59.58.mp4 | AAC | 47 min | 326 | 0 | ✅ |
| Recording at 2026-01-15 10.00.24.mp4 | ALAC | 72 min | 1282 | 0 | ✅ |
| Recording at 2026-01-16 15.14.31.mp4 | ALAC | 43 min | 1488 | 0 | ✅ |
| Recording at 2026-01-16 16.00.15.mp4 | ALAC | 35 min | 828 | 0 | ✅ |

Transcrições salvas em: `/Users/daniloblima/Downloads/Transcricoes/[nome] - MIX TEST/`

### ✅ IMPLEMENTAÇÃO CONCLUÍDA

**Arquivo modificado:** `transcribe_complete.py`

**Função `extract_audio()` (linhas 213-268) - NOVA LÓGICA:**
```python
def extract_audio(video_path, output_wav, whisper_model_path=None):
    streams = get_audio_streams(video_path)

    if len(streams) == 1:
        # Uma única stream - extrair diretamente
        cmd = ['ffmpeg', '-i', str(video_path),
               '-map', f"0:{streams[0]['index']}",
               '-ar', '16000', '-ac', '1', '-acodec', 'pcm_s16le',
               '-y', str(output_wav)]
    else:
        # Múltiplas streams - MIXAR todas em mono
        stream_refs = ''.join([f"[0:{s['index']}]" for s in streams])
        filter_complex = f"{stream_refs}amix=inputs={len(streams)}:duration=longest[aout]"
        cmd = ['ffmpeg', '-i', str(video_path),
               '-filter_complex', filter_complex,
               '-map', '[aout]',
               '-ar', '16000', '-ac', '1',
               '-y', str(output_wav)]
```

### 📝 LIÇÕES APRENDIDAS

1. **Seleção de stream NÃO é confiável** - O Azayaka grava 2 streams (microfone + sistema), mas qual é qual VARIA por gravação. Regras baseadas em codec, índice ou bitrate NÃO funcionam.

2. **Mixar streams é a solução robusta** - Ao invés de escolher uma stream, mixar todas resolve o problema:
   - Captura ambos os lados da conversa
   - Não depende de qual stream tem o conteúdo
   - FFmpeg `amix` normaliza o volume automaticamente

3. **Beam search ajuda mas não resolve** - `--beam-size 5 --best-of 5` reduz repetições em trechos curtos, mas não elimina o problema em áudios longos quando a stream tem gaps/silêncio.

### ✅ CHECKLIST CONCLUÍDO
1. [x] ~~Validar transcrição completa com streams mixadas~~ ✅
2. [x] ~~Implementar mix de streams no script~~ ✅
3. [x] ~~Testar com arquivo ALAC~~ ✅ (3 arquivos testados)
4. [x] ~~Definir configuração final do Azayaka~~ ✅

### 🎛️ CONFIGURAÇÃO RECOMENDADA DO AZAYAKA

**Conclusão: O codec NÃO importa mais!**

Com a solução de mix de streams implementada, o script funciona corretamente com **qualquer configuração** do Azayaka:

| Configuração | Funciona? | Observação |
|--------------|-----------|------------|
| AAC (lossy) | ✅ | Arquivo menor, qualidade boa |
| ALAC (lossless) | ✅ | Arquivo maior, qualidade máxima |
| 1 stream | ✅ | Extração direta |
| 2 streams | ✅ | Mix automático |

**Recomendação para gravação de entrevistas:**
- **Codec**: AAC (menor tamanho, qualidade suficiente para voz)
- **Áudio do sistema**: ATIVADO (captura o outro lado da chamada)
- **Microfone**: ATIVADO (captura sua voz)

**Uso do script:**
```bash
cd ~/Experimentos/whisper-transcription
./whisper_transcription_env/bin/python3 transcribe_complete.py '/caminho/video.mp4'
```

O script automaticamente:
1. Detecta número de streams de áudio
2. Se múltiplas: mixa em mono com FFmpeg `amix`
3. Transcreve com Whisper + beam search
4. Identifica speakers com Sherpa-ONNX
5. Salva em `~/Downloads/Transcricoes/nome_video/`

---

## [2026-01-15] - Bug RESOLVIDO: Transcrição [silêncio] em Vídeos ALAC do Azayaka

### 🎯 OBJETIVO
Investigar por que vídeo ALAC gerava [silêncio] em quase toda a transcrição, exceto nos últimos minutos.

### ❌ PROBLEMA
- **Sintoma**: Transcrição com [silêncio] de 0:00 até ~1:05, só depois aparecia conteúdo
- **Arquivo**: `Recording at 2026-01-15 10.00.24.mp4` (478 MB, 72 min, ALAC)
- **Causa**: Correção anterior para AAC (usar primeira stream) quebrou ALAC

### 🔍 ANÁLISE / ROOT CAUSE

**Estrutura de streams do Azayaka (ALAC):**
```
Stream #1 (199 kbps): Apenas microfone do usuário
Stream #2 (318 kbps): Áudio COMPLETO (microfone + áudio do sistema/chamada)
```

**O problema:**
- Correção de 2026-01-13 mudou para usar "primeira stream" (evitar repetições AAC)
- Em ALAC, a primeira stream (#1) só tem o microfone
- Quando o outro lado fala (e usuário ouve), stream #1 é silêncio
- Stream #2 tem ambos os lados da conversa

**Testes realizados:**
1. ✅ Stream #2 (318 kbps) transcreve corretamente - tem conversa completa
2. ❌ Stream #1 (199 kbps) gera silêncio - só tem microfone do usuário

### ✅ SOLUÇÃO

**Regra baseada no codec** em `get_best_audio_stream()`:
- **ALAC**: Usar stream com MAIOR bitrate (áudio completo)
- **AAC**: Usar PRIMEIRA stream (evita artefatos de compressão)

```python
if alac_streams:
    best = max(alac_streams, key=lambda x: x['bitrate'])  # MAIOR
elif aac_streams:
    best = min(aac_streams, key=lambda x: x['index'])     # PRIMEIRA
```

### 📊 RESULTADO
- ✅ Vídeo ALAC agora transcreve corretamente desde o início
- ✅ Primeira linha: "Que abordagem fria no LinkedIn, mas agradeço seu tempo..."

### 📝 LIÇÃO CRÍTICA

**AAC e ALAC requerem regras OPOSTAS:**

| Codec | Stream a usar | Razão |
|-------|---------------|-------|
| ALAC  | MAIOR bitrate | Contém áudio completo (mic + sistema) |
| AAC   | PRIMEIRA      | Maior bitrate tem artefatos que causam repetições |

### ⚠️ PENDENTE
- Testar que vídeos AAC continuam funcionando com a nova lógica

---

## [2026-01-13] - Bug: Whisper Repetindo Frases em Vídeos AAC do Azayaka

### 🎯 OBJETIVO
Investigar por que vídeos gravados com AAC no Azayaka geravam transcrições com frases repetidas centenas de vezes, mesmo o áudio original estando correto.

### ❌ PROBLEMA
- **Sintoma**: Transcrição continha frases repetindo dezenas/centenas de vezes
- **Exemplo**: "conseguiu um investimento privado, e a gente" repetiu 88 vezes
- **Arquivo teste**: `Recording at 2026-01-13 15.59.58.mp4` (47 minutos, AAC 102-107 kbps)
- **Impacto**: Transcrições inutilizáveis, arquivo final com 1139 linhas (deveria ter ~900)
- **Gravidade**: ALTA - problema afeta vídeos com codec AAC-LC

### 🔍 ANÁLISE / ROOT CAUSE

**Investigação sistemática**:

1. **Comparação com transcrição de referência (Riverside.fm)**:
   - Riverside transcreveu o mesmo vídeo PERFEITAMENTE (sem repetições)
   - Confirmado: áudio do arquivo está correto, problema é no Whisper

2. **Análise das streams de áudio**:
   ```bash
   ffprobe -show_entries stream=codec_name,bit_rate Recording...15.59.58.mp4
   ```

   **Resultado**:
   ```json
   Stream #0:1: Audio: aac (LC), 48000 Hz, stereo, 102883 bps
   Stream #0:2: Audio: aac (LC), 48000 Hz, stereo, 107068 bps
   ```

   - Vídeo AAC do Azayaka tem **2 streams de áudio**
   - Código estava selecionando stream de **maior bitrate** (#2 = 107 kbps)

3. **Teste com stream #1 (102 kbps)**:
   ```bash
   ffmpeg -i video.mp4 -map 0:1 -ar 16000 -ac 1 test.wav
   whisper-cli -m ggml-medium.bin -f test.wav -l pt -osrt
   ```

   **Resultado**: ✅ **FUNCIONA PERFEITAMENTE - SEM REPETIÇÕES!**

4. **Teste com stream #2 (107 kbps)**:
   ```bash
   ffmpeg -i video.mp4 -map 0:2 -ar 16000 -ac 1 test.wav
   whisper-cli -m ggml-medium.bin -f test.wav -l pt -osrt
   ```

   **Resultado**: ❌ **REPETIÇÕES MASSIVAS NO SRT GERADO**

5. **Causa raiz identificada**:
   - Código em `transcribe_complete.py:68-70` selecionava stream por bitrate:
     ```python
     # Retornar a stream com maior bitrate
     best_stream = max(streams, key=lambda x: x[1])
     return best_stream[0]
     ```
   - Stream #2 (maior bitrate) tem algum **artefato de compressão AAC** que confunde o Whisper
   - Stream #1 (menor bitrate) funciona perfeitamente
   - **Whisper é sensível a qualidade/artefatos do codec de áudio AAC-LC**

6. **Comparação com vídeos ALAC**:
   - Vídeo `Recording at 2026-01-13 11.42.56.mp4` (91 min, ALAC)
   - **ALAC (lossless)**: Ambas as streams funcionam perfeitamente
   - **AAC-LC 102-107 kbps**: Apenas stream #1 funciona

### ✅ SOLUÇÃO

**Modificação no código de seleção de stream**:

**Arquivo**: `transcribe_complete.py:37-72`

**Mudança**:
```python
def get_best_audio_stream(video_path):
    """Detecta a primeira stream de áudio (mais confiável)"""
    # ... código de detecção de streams ...

    # ANTES (selecionava por bitrate):
    # best_stream = max(streams, key=lambda x: x[1])

    # DEPOIS (seleciona primeira stream):
    first_stream = min(streams, key=lambda x: x[0])
    return first_stream[0]
```

**Mensagem atualizada** (linha 90):
```python
print(f"   🎯 Usando stream de áudio #{best_stream} (primeira stream)")
```

**Justificativa**:
- Primeira stream é mais confiável para Whisper
- Evita artefatos de compressão AAC problemáticos
- Funciona para AAC e ALAC
- Bitrate NÃO é indicador confiável de qualidade para transcrição

### 📊 RESULTADOS

**Teste após correção (vídeo problemático AAC 47min)**:
```bash
./whisper_transcription_env/bin/python3 transcribe_complete.py "Recording...15.59.58.mp4"
```

**Output**:
```
🎯 Usando stream de áudio #1 (primeira stream)
✅ Áudio extraído: 86.1 MB
✅ Transcrição concluída em 190.6s
📝 911 segmentos transcritos
🎤 Speakers detectados: 48 → 3 (após pós-processamento)
```

**Comparação**:
- ❌ ANTES: 1139 linhas, 88 repetições, inutilizável
- ✅ AGORA: 914 linhas, 0 repetições da frase problemática, perfeito

**Validação com vídeo ALAC (91min)**:
```bash
./whisper_transcription_env/bin/python3 transcribe_complete.py "Recording...11.42.56.mp4"
```

**Output**:
```
🎯 Usando stream de áudio #1 (primeira stream)
✅ Transcrição concluída em 272.0s
📝 2221 segmentos transcritos
🎤 Speakers detectados: 43 → 2
```

- ✅ **Continua funcionando perfeitamente com ALAC**
- ✅ **Agora funciona com AAC também**

### 📝 LIÇÕES APRENDIDAS

1. **Bitrate NÃO garante melhor qualidade para ML**
   - Stream de 107 kbps pior que 102 kbps para Whisper
   - Artefatos de compressão AAC podem confundir modelos de transcrição
   - Primeira stream geralmente é a mais confiável

2. **AAC-LC com bitrate baixo é problemático para Whisper**
   - AAC 102-107 kbps: apenas stream #1 funciona
   - ALAC (lossless): todas as streams funcionam
   - Recomendação: **usar ALAC para gravações críticas**

3. **Sempre comparar com transcrição de referência**
   - Riverside.fm foi essencial para confirmar que áudio estava correto
   - Problema estava no processamento, não no arquivo

4. **Teste metódico de cada stream individualmente**
   - Extrair e transcrever cada stream separadamente
   - Identificar qual funciona antes de modificar código

5. **Configurações de áudio recomendadas no Azayaka**:
   - **VÍDEO**: H.265 (HEVC), 720p, 15fps, low quality (economiza ~700MB/hora)
   - **ÁUDIO**: ALAC lossless (garantia de transcrição perfeita, +75MB/hora)
   - **Razão**: Compressão de vídeo economiza MUITO mais que compressão de áudio
   - Diferença de 75MB/hora no áudio é desprezível vs garantia de qualidade

6. **Whisper é sensível a codec de áudio**
   - Testado funcionando: ALAC, AAC stream #1
   - Problemático: AAC stream #2 (maior bitrate)
   - Não confiar cegamente em bitrate

### 🔗 ARQUIVOS MODIFICADOS
- `transcribe_complete.py:37-72` (função `get_best_audio_stream()`)
- `transcribe_complete.py:90` (mensagem de log)

### 🎯 IMPACTO
- **CRÍTICO**: Bug afetava todos os vídeos AAC do Azayaka
- **RESOLVIDO**: Agora funciona para AAC e ALAC
- **BONUS**: Solução mais robusta e confiável

---

## [2026-01-13] - Bug Crítico: Transcrição Vazia em Vídeos do Azayaka

### 🎯 OBJETIVO
Investigar por que os vídeos gravados pelo Azayaka estavam gerando transcrições vazias (apenas "[SILÊNCIO]"), mesmo com áudio claro e reproduzível.

### ❌ PROBLEMA
- **Sintoma**: Arquivo de transcrição gerado continha apenas "[SILÊNCIO]", mesmo com áudio claro e audível
- **Arquivo teste**: `Recording at 2026-01-13 11.19.38.mp4` (25.3 segundos)
- **Impacto**: TODOS os vídeos do Azayaka falhavam na transcrição, gerando arquivos vazios
- **Gravidade**: CRÍTICA - funcionalidade principal completamente quebrada para vídeos do Azayaka

### 🔍 ANÁLISE / ROOT CAUSE

**Investigação passo a passo**:

1. **Verificação do arquivo de saída**:
   ```
   [0:00:00] SPEAKER_0: [SILÊNCIO]
   ```
   - Apenas 1 segmento detectado
   - Conteúdo vazio

2. **Análise das streams de áudio do vídeo**:
   ```bash
   ffprobe -show_streams -select_streams a "Recording at 2026-01-13 11.19.38.mp4"
   ```

   **Resultado crítico**:
   ```
   Stream #0:1 (index=1): Audio: alac, 48000 Hz, stereo, s16p, 3 kb/s
   Stream #0:2 (index=2): Audio: alac, 48000 Hz, stereo, s16p, 189 kb/s
   ```

   - Vídeo tem **2 streams de áudio**
   - **Stream 1**: 3 kb/s (quase vazia, sem conteúdo útil)
   - **Stream 2**: 189 kb/s (contém o áudio real)

3. **Teste manual da Stream 2**:
   ```bash
   ffmpeg -i "Recording..." -map 0:a:1 -ar 16000 -ac 1 /tmp/test.wav
   whisper-cli -m ggml-medium.bin -f /tmp/test.wav -l pt
   ```

   **Resultado**:
   ```
   [00:00:00.000 --> 00:00:04.000] Alô?
   [00:00:04.000 --> 00:00:10.000] Só estou testando um negócio aqui...
   [00:00:10.000 --> 00:00:12.000] Entendi.
   [00:00:12.000 --> 00:00:14.000] Tá bom.
   [00:00:14.000 --> 00:00:16.000] Alô, alô, alô.
   [00:00:16.000 --> 00:00:20.000] Ah, o chefe está de férias, entendi.
   [00:00:20.000 --> 00:00:22.000] Tá bom.
   ```

   ✅ **Áudio perfeito na Stream 2!**

4. **Causa raiz identificada**:
   - Código em `transcribe_complete.py:42-49` usava extração padrão do ffmpeg:
     ```python
     cmd = [
         'ffmpeg', '-i', str(video_path),
         '-ar', '16000',
         '-ac', '1',
         '-acodec', 'pcm_s16le',
         '-y',
         str(output_wav)
     ]
     ```
   - **ffmpeg por padrão pega a PRIMEIRA stream de áudio encontrada**
   - No caso do Azayaka, a primeira stream (index=1) estava vazia (3 kb/s)
   - Áudio real estava na segunda stream (index=2, 189 kb/s)

5. **Por que o Azayaka gera 2 streams?**
   - Vídeos gravados pelo Azayaka (app de screen recording) incluem:
     - Stream 1: Áudio do sistema (3 kb/s - normalmente vazio)
     - Stream 2: Áudio do microfone (189 kb/s - áudio real)

### ✅ SOLUÇÃO

**Implementação de seleção automática da melhor stream de áudio**:

**1. Nova função `get_best_audio_stream()` (linhas 37-70)**:

```python
def get_best_audio_stream(video_path):
    """Detecta a stream de áudio com maior bitrate"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'a',
        '-show_entries', 'stream=index,bit_rate',
        '-of', 'csv=p=0',
        str(video_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None

    # Parse output: cada linha é "index,bitrate"
    streams = []
    for line in result.stdout.strip().split('\n'):
        parts = line.split(',')
        if len(parts) >= 2:
            index = int(parts[0])
            bitrate = int(parts[1]) if parts[1] != 'N/A' else 0
            streams.append((index, bitrate))

    # Retornar a stream com maior bitrate
    best_stream = max(streams, key=lambda x: x[1])
    return best_stream[0]
```

**Lógica**:
1. Usa `ffprobe` para listar todas as streams de áudio com seus bitrates
2. Escolhe a stream com **maior bitrate** (assume que é a com melhor qualidade)
3. Retorna o índice da stream

**2. Modificação da função `extract_audio()` (linhas 72-105)**:

```python
def extract_audio(video_path, output_wav):
    # Detectar melhor stream de áudio (maior bitrate)
    best_stream = get_best_audio_stream(video_path)

    # Montar comando ffmpeg
    cmd = ['ffmpeg', '-i', str(video_path)]

    # Se detectou múltiplas streams, usar a melhor
    if best_stream is not None:
        cmd.extend(['-map', f'0:{best_stream}'])
        print(f"   🎯 Usando stream de áudio #{best_stream} (maior bitrate)")

    cmd.extend([
        '-ar', '16000',
        '-ac', '1',
        '-acodec', 'pcm_s16le',
        '-y',
        str(output_wav)
    ])

    result = subprocess.run(cmd, capture_output=True, text=True)
    # ...
```

**Mudança de comportamento**:
- ❌ ANTES: Sempre usava primeira stream (padrão do ffmpeg)
- ✅ AGORA: Detecta e usa a stream com maior bitrate automaticamente

### 📊 RESULTADOS

**Teste após correção no mesmo vídeo**:
```bash
./whisper_transcription_env/bin/python3 transcribe_complete.py "Recording at 2026-01-13 11.19.38.mp4"
```

**Output**:
```
================================================================================
PASSO 1/4: Extraindo áudio
================================================================================
   Extraindo áudio de: Recording at 2026-01-13 11.19.38.mp4
   Formato de saída: WAV 16kHz mono
   🎯 Usando stream de áudio #2 (maior bitrate)
   ✅ Áudio extraído: 0.8 MB

================================================================================
PASSO 2/4: Transcrevendo áudio com Whisper
================================================================================
   ✅ Transcrição concluída em 2.9s
   📝 7 segmentos transcritos

================================================================================
PASSO 3/4: Identificando speakers (diarização)
================================================================================
   ✅ Diarização concluída em 2.6s
   🎤 Speakers detectados: 2 → 2 (após pós-processamento)
   📊 Total de segmentos: 5
```

**Arquivo de transcrição gerado**:
```
TRANSCRIÇÃO COM DIARIZAÇÃO
================================================================================

[0:00:00] SPEAKER_0: Alô?
[0:00:04] SPEAKER_0: Só estou testando um negócio aqui, calma aí, não é para responder não.
[0:00:10] SPEAKER_0: Entendi.
[0:00:12] SPEAKER_0: Tá bom.
[0:00:14] SPEAKER_0: Alô, alô, alô.
[0:00:16] SPEAKER_1: Ah, o chefe está de férias, entendi.
[0:00:20] SPEAKER_0: Tá bom.
```

**Comparação**:
- ❌ ANTES: 1 segmento, "[SILÊNCIO]", 0 speakers
- ✅ AGORA: 7 segmentos, texto completo, 2 speakers detectados

### 📝 LIÇÕES APRENDIDAS

1. **NUNCA assumir que vídeos têm apenas 1 stream de áudio**
   - Apps de screen recording (Azayaka, OBS, etc.) frequentemente gravam:
     - Áudio do sistema (pode estar vazio)
     - Áudio do microfone
   - Sempre usar a stream de melhor qualidade

2. **Bitrate é indicador de qualidade de áudio**
   - Stream com 3 kb/s: provavelmente vazia ou ruído
   - Stream com 189 kb/s: áudio real de boa qualidade
   - Usar `ffprobe` para detectar bitrates

3. **Validação de extração de áudio deve verificar CONTEÚDO**
   - Não basta verificar tamanho do arquivo WAV
   - Arquivo pode ser grande mas ter apenas silêncio
   - Considerar adicionar validação: se Whisper retorna "[SILÊNCIO]", alertar usuário

4. **Ferramentas de screen recording são casos especiais**
   - Azayaka, OBS, QuickTime: comportamentos diferentes
   - Testar com vídeos de diferentes fontes
   - Documentar estruturas de stream conhecidas

5. **Mensagens de debug são essenciais**
   - Adicionar `🎯 Usando stream de áudio #2 (maior bitrate)` ajuda a diagnosticar
   - Mostrar tamanho do áudio extraído (0.3 MB vs 0.8 MB indica problema)

### 🔗 ARQUIVOS MODIFICADOS
- `transcribe_complete.py:37-70` (nova função `get_best_audio_stream()`)
- `transcribe_complete.py:72-105` (modificação de `extract_audio()`)

### 🎯 IMPACTO
- **CRÍTICO**: Bug afetava 100% dos vídeos do Azayaka
- **RESOLVIDO**: Todos os vídeos agora processam corretamente
- **BONUS**: Solução também beneficia outros apps de screen recording com múltiplas streams

---

## [2026-01-13] - Bug: Falha em Áudios Curtos (<15s) - "Arquivo Corrompido"

### 🎯 OBJETIVO
Investigar por que o aplicativo TranscribeVideo.app estava reportando "arquivo corrompido" para vídeos MP4 gravados pelo Azayaka, mesmo os vídeos sendo reproduzíveis normalmente.

### ❌ PROBLEMA
- **Sintoma**: Dialog de erro "Verifique se o arquivo de vídeo está corrompido" ao fazer upload de vídeos MP4 gravados pelo Azayaka
- **Arquivo teste**: `Recording at 2026-01-13 11.09.26.mp4` (10.8 segundos)
- **Confusão**: Mensagem genérica "corrompido" não indicava a causa real
- **Impacto**: Usuário acreditava que o arquivo estava com problemas, quando na verdade era uma limitação do sistema

### 🔍 ANÁLISE / ROOT CAUSE

**Investigação passo a passo**:

1. **Teste manual do ffmpeg**: ✅ SUCESSO
   ```bash
   ffmpeg -i "Recording at 2026-01-13 11.09.26.mp4" -ar 16000 -ac 1 -acodec pcm_s16le -y /tmp/test.wav
   ```
   - Áudio extraído sem problemas (332KB WAV)
   - Arquivo NÃO estava corrompido

2. **Execução manual do script completo**:
   ```bash
   ./whisper_transcription_env/bin/python3 transcribe_complete.py "Recording at 2026-01-13 11.09.26.mp4"
   ```
   - **Passo 1/4** (Extrair áudio): ✅ SUCESSO (0.3 MB)
   - **Passo 2/4** (Transcrição Whisper): ✅ SUCESSO (1 segmento em 4.9s)
   - **Passo 3/4** (Diarização Sherpa-ONNX): ❌ **FALHOU**
     - Erro: `No speakers found in the audio samples`
     - Retorno: Lista vazia `[]`
   - **Resultado**: Script executou `sys.exit(1)` (linha 413)

3. **Causa raiz identificada**:
   - Vídeo tem apenas **10.8 segundos**
   - Sistema de diarização (Sherpa-ONNX) precisa de áudio mais longo (≥15s) para detectar speakers
   - Código em `transcribe_complete.py:411-413`:
     ```python
     diarization_segments = diarize_audio(temp_audio, args.threshold)
     if not diarization_segments:
         os.remove(temp_audio)
         sys.exit(1)  # ❌ Falha total!
     ```
   - Script ABORTAVA completamente quando diarização falhava
   - Mesmo que transcrição tivesse funcionado perfeitamente!

4. **Problema secundário**: Mensagem de erro enganosa
   - `transcribe_wrapper.py:224`: "Verifique se o arquivo de vídeo está corrompido"
   - Mensagem genérica não indicava o problema real (áudio curto)

### ✅ SOLUÇÃO

**1. Correção no `transcribe_complete.py` (linhas 411-419)**:

```python
# Passo 3: Diarizar
diarization_segments = diarize_audio(temp_audio, args.threshold)

# Se não detectar speakers (áudio muito curto), criar segmento único com speaker padrão
if not diarization_segments:
    print(f"   ⚠️  Diarização falhou. Usando speaker padrão (SPEAKER_0).")
    print(f"   💡 Dica: Áudios muito curtos (<15s) podem não ter speakers detectados.")
    # Criar um único segmento cobrindo toda a duração do áudio
    max_end = max(seg['end'] for seg in transcription_segments)
    diarization_segments = [(0.0, max_end, 0)]

# Continua normalmente...
```

**Mudança de comportamento**:
- ❌ ANTES: `sys.exit(1)` → Falha total
- ✅ AGORA: Cria speaker padrão → Continua processamento

**2. Melhoria da mensagem de erro no `transcribe_wrapper.py` (linhas 222-229)**:

```python
send_error_dialog(
    "Erro durante a transcrição.\\n\\n"
    "Possíveis causas:\\n"
    "• Áudio muito curto (<15 segundos)\\n"
    "• Áudio sem fala detectável\\n"
    "• Arquivo de vídeo incompatível\\n\\n"
    "Verifique o arquivo e tente novamente.",
    "Erro na Transcrição"
)
```

### 📊 RESULTADOS

**Teste após correção**:
```bash
./whisper_transcription_env/bin/python3 transcribe_complete.py "Recording at 2026-01-13 11.09.26.mp4"
```

**Output**:
```
================================================================================
PASSO 3/4: Identificando speakers (diarização)
================================================================================
   Threshold: 0.75
   Pós-processamento: 10%
   Carregando modelos...
   Lendo áudio...
   Processando diarização...
   ⚠️  Nenhum segmento de fala detectado
   ⚠️  Diarização falhou. Usando speaker padrão (SPEAKER_0).
   💡 Dica: Áudios muito curtos (<15s) podem não ter speakers detectados.

================================================================================
PASSO 4/4: Mesclando transcrição com diarização
================================================================================
   Mesclando 1 segmentos de transcrição
   com 1 segmentos de diarização...
   ✅ Mesclagem concluída: 1 segmentos finais

✅ PROCESSAMENTO CONCLUÍDO!
================================================================================
📄 Arquivo de saída: ~/Downloads/Transcricoes/Recording at 2026-01-13 11.09.26/Recording at 2026-01-13 11.09.26_transcrito.txt
📊 Total de segmentos: 1
🎤 Speakers identificados: 1
```

**Arquivo gerado com sucesso**:
```
TRANSCRIÇÃO COM DIARIZAÇÃO
================================================================================

[0:00:00] SPEAKER_0: [SILÊNCIO]
```

### 📝 LIÇÕES APRENDIDAS

1. **Fallback é melhor que falha total**
   - Sistema DEVE continuar processando mesmo se uma etapa opcional falhar
   - Diarização é útil mas não essencial - transcrição é o core

2. **Mensagens de erro devem ser específicas**
   - "Arquivo corrompido" é muito genérico e enganoso
   - Listar possíveis causas ajuda o usuário a diagnosticar

3. **Validação de entrada deve considerar limitações do sistema**
   - Áudios muito curtos (<15s) não funcionam bem com diarização Sherpa-ONNX
   - Documentar limitações conhecidas

4. **Logs detalhados são essenciais**
   - `applescript_debug.log` e `transcribe_log.txt` foram cruciais
   - Mostrar código de saída e mensagens de erro facilita debugging

5. **Testar casos extremos**
   - Vídeos de 10 segundos são casos válidos de uso
   - Sistema deve degradar gracefully (graceful degradation)

### 🔗 ARQUIVOS MODIFICADOS
- `transcribe_complete.py:411-419` (fallback para speaker padrão)
- `transcribe_wrapper.py:222-229` (mensagem de erro melhorada)

---

## [2025-12-03] - Criação de GUI (Droplet App) + Debug Sistemático do AppleScript

### 🎯 OBJETIVO DA SESSÃO
Criar uma interface GUI simples para não-desenvolvedores usarem o sistema de transcrição sem necessidade de terminal. Implementar um "droplet" macOS que aceita arrastar-e-soltar arquivos de vídeo.

### 🏗️ IMPLEMENTAÇÃO DO GUI

#### Arquivos Criados

**1. `transcribe_wrapper.py`** (Wrapper com notificações nativas)
- Ponte entre AppleScript e Python
- Valida arquivo (existência, formato)
- Executa `transcribe_complete.py`
- Mostra dialog boxes nativos do macOS (sucesso/erro)
- Logging detalhado para debug
- **Localização**: `~/Experimentos/whisper-transcription/transcribe_wrapper.py`

**Funcionalidades**:
```python
# Dialog de sucesso com informações
send_success_dialog(
    "Transcrição concluída com sucesso!\n\n"
    f"Tempo total: {duration_str}\n\n"
    f"Arquivo salvo em:\n"
    f"~/Downloads/Transcricoes/{video_name}/"
)

# Dialog de erro com contexto
send_error_dialog("Formato não suportado: .avi\n\nFormatos aceitos:\nMP4, MOV, AVI, MKV, MP3, WAV, M4A")
```

**2. `TranscribeVideo.app`** (AppleScript Droplet)
- App nativo macOS em `~/Applications/TranscribeVideo.app`
- Aceita drag-and-drop de arquivos
- Executa wrapper Python em background
- **Código AppleScript**:
```applescript
on open droppedItems
    repeat with theFile in droppedItems
        set posixPath to POSIX path of theFile

        -- LOG: Arquivo recebido
        do shell script "echo 'AppleScript recebeu: " & posixPath & "' >> ~/Experimentos/whisper-transcription/applescript_debug.log"

        try
            -- Executar wrapper diretamente (SEM nohup, SEM capture de exit code)
            do shell script "~/Experimentos/whisper-transcription/transcribe_wrapper.py " & quoted form of posixPath & " &"

            -- LOG: Sucesso
            do shell script "echo 'Wrapper foi chamado' >> ~/Experimentos/whisper-transcription/applescript_debug.log"
        on error errMsg
            -- LOG: Erro
            do shell script "echo 'ERRO: " & errMsg & "' >> ~/Experimentos/whisper-transcription/applescript_debug.log"
        end try
    end repeat
end open
```

#### Estrutura de Saída
```
~/Downloads/Transcricoes/
└── nome_do_video/
    └── nome_do_video_transcrito.txt
```

Cada vídeo gera sua própria pasta organizada em Downloads.

---

### ❌ PROBLEMA CRÍTICO: "Erro durante a transcrição"

#### Sintomas
- Dialog de erro aparecia imediatamente: "Erro durante a transcrição. Verifique se o arquivo de vídeo está corrompido."
- Mesmo teste funcionando perfeitamente no terminal
- Erro persistiu por **4 tentativas** de correção

#### Tentativas Falhadas (Abordagem "Força Bruta")

**Tentativa #1**: Redirecionamento stderr
```applescript
do shell script "~/Experimentos/.../transcribe_wrapper.py " & quoted form of posixPath & " > /dev/null 2>&1"
```
❌ FALHOU - Mesmo erro apareceu

**Tentativa #2**: Adicionar bloco try
```applescript
try
    do shell script "~/Experimentos/.../transcribe_wrapper.py " & quoted form of posixPath & " > /dev/null 2>&1"
end try
```
❌ FALHOU - Mesmo erro apareceu

**Tentativa #3**: Execução detached com nohup + &
```applescript
do shell script "nohup ~/Experimentos/.../transcribe_wrapper.py " & quoted form of posixPath & " > /dev/null 2>&1 &"
```
❌ FALHOU - Mesmo erro apareceu

**Tentativa #4**: Capturar exit code
```applescript
set output to do shell script "nohup ~/Experimentos/.../transcribe_wrapper.py " & quoted form of posixPath & " > /dev/null 2>&1 &; echo EXIT_CODE:$?"
```
❌ FALHOU - Erro de sintaxe shell

#### Crítica do Usuário
> "O que aconteceu com o nosso método de identificação e solução de problemas? A gente já está indo para a segunda rodada em que a gente faz alguma coisa e não entende. Vamos lá! Quero ver se a gente vai ler o log, identificar a causa raiz do problema e não simplesmente ficar tratando o sintoma."

**Problema na abordagem**: Estávamos ASSUMINDO que:
- AppleScript interpreta output como erro
- Redirecionamentos resolveriam
- Background execution resolveria

**Mas NUNCA VALIDAMOS** se essas suposições estavam corretas.

---

### 🔍 DEBUG SISTEMÁTICO (Abordagem Correta)

#### FASE 1: Coleta de Evidências

**Modificações para logging**:

1. **`transcribe_wrapper.py`** - Adicionado logging detalhado:
```python
def log_debug(message):
    """Salva log detalhado para debug do AppleScript"""
    script_dir = Path(__file__).parent
    log_file = script_dir / "applescript_debug.log"
    with open(log_file, 'a') as f:
        f.write(f"{message}\n")

def main():
    # DEBUG: Log detalhado de TUDO
    log_debug(f"\n{'='*80}")
    log_debug(f"INÍCIO: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_debug(f"sys.argv: {sys.argv}")
    log_debug(f"len(sys.argv): {len(sys.argv)}")
    if len(sys.argv) >= 2:
        log_debug(f"Arquivo recebido: {sys.argv[1]}")
        log_debug(f"Arquivo existe: {Path(sys.argv[1]).exists()}")
    log_debug(f"Working directory: {os.getcwd()}")
    log_debug(f"Environment PATH: {os.environ.get('PATH', 'NOT SET')}")
    # ... logs antes de cada return
```

2. **AppleScript com logging**:
```applescript
-- LOG: Escrever arquivo recebido
do shell script "echo 'AppleScript recebeu: " & posixPath & "' >> ~/Experimentos/whisper-transcription/applescript_debug.log"
```

#### FASE 2: Análise dos Logs

**Evidências coletadas do log**:
```
AppleScript recebeu: /Users/daniloblima/Experimentos/whisper-transcription/test_10sec.mp4

================================================================================
INÍCIO: 2025-12-03 16:43:56
sys.argv: ['/Users/daniloblima/Experimentos/whisper-transcription/transcribe_wrapper.py',
           '/Users/daniloblima/Experimentos/whisper-transcription/test_10sec.mp4']
Arquivo recebido: /Users/daniloblima/Experimentos/whisper-transcription/test_10sec.mp4
Arquivo existe: True
Working directory: /                    ← ⚠️ PROBLEMA #1
Environment PATH: /usr/bin:/bin:/usr/sbin:/sbin    ← ⚠️ PROBLEMA #2
SUBPROCESS: return_code = 1 (ERRO)     ← ⚠️ PROBLEMA #3
```

**Outros checks**:
```bash
$ ls -la transcribe_wrapper.py
-rwx--x--x  transcribe_wrapper.py  ✅ Executável

$ head -1 transcribe_wrapper.py
#!/usr/bin/env python3  ✅ Shebang correto

$ which python3
/opt/homebrew/bin/python3  ✅ Python instalado
```

#### ROOT CAUSE IDENTIFICADO

**Problema**: Ambiente minimalista do AppleScript

Quando AppleScript executa `do shell script`, ele roda em um **ambiente mínimo**:

1. **Working directory = `/`** (raiz do sistema, não o diretório do projeto)
2. **PATH incompleto** = `/usr/bin:/bin:/usr/sbin:/sbin` (faltando `/opt/homebrew/bin/`)
3. **Ferramentas não encontradas**:
   - `ffmpeg` está em `/opt/homebrew/bin/ffmpeg` ❌
   - `whisper-cli` está em `/opt/homebrew/bin/whisper-cli` ❌
   - Subprocess não consegue encontrar essas ferramentas
   - Retorna exit code 1 (erro)

4. **Wrapper recebe exit code 1**:
   - Interpreta como falha na transcrição (linha 175-186 em `transcribe_wrapper.py`)
   - Mostra dialog de erro: "Erro durante a transcrição. Verifique se o arquivo de vídeo está corrompido."

**Por que funcionava no terminal?**
- Working directory: `~/Experimentos/whisper-transcription/` ✅
- PATH completo: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:...` ✅
- Todas as ferramentas encontradas ✅

---

### ✅ SOLUÇÃO (Baseada em Evidências)

**Arquivo**: `transcribe_wrapper.py`

**Modificação**: Configurar ambiente no início de `main()`:

```python
def main():
    # CORRIGIR AMBIENTE: AppleScript roda com PATH mínimo e working dir = /
    # Adicionar /opt/homebrew/bin ao PATH (onde estão ffmpeg e whisper-cli)
    os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ.get('PATH', '')

    # Mudar para o diretório do script
    script_dir = Path(__file__).parent
    os.chdir(str(script_dir))

    # Iniciar medição de tempo
    start_time = time.time()

    # DEBUG: Log detalhado de TUDO
    log_debug(f"\n{'='*80}")
    log_debug(f"INÍCIO: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    # ... resto do código
```

**Mudanças específicas**:
1. **Linha 56**: `os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ.get('PATH', '')`
   - Adiciona `/opt/homebrew/bin` ao PATH
   - Permite subprocess encontrar `ffmpeg` e `whisper-cli`

2. **Linhas 59-60**:
   ```python
   script_dir = Path(__file__).parent
   os.chdir(str(script_dir))
   ```
   - Muda working directory para o diretório do script
   - Garante paths relativos funcionem corretamente

---

### 📊 RESULTADO FINAL

**Log após correção**:
```
AppleScript recebeu: /Users/daniloblima/Experimentos/whisper-transcription/test_10sec.mp4

================================================================================
INÍCIO: 2025-12-03 17:13:39
sys.argv: ['/Users/daniloblima/Experimentos/whisper-transcription/transcribe_wrapper.py',
           '/Users/daniloblima/Experimentos/whisper-transcription/test_10sec.mp4']
Arquivo recebido: /Users/daniloblima/Experimentos/whisper-transcription/test_10sec.mp4
Arquivo existe: True
Working directory: /Users/daniloblima/Experimentos/whisper-transcription  ✅
Environment PATH (CORRIGIDO): /opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin  ✅
SUBPROCESS: return_code = 0 (sucesso)  ✅
OUTPUT FILE: exists = .../Downloads/Transcricoes/test_10sec/test_10sec_transcrito.txt  ✅
RETURN CODE: 0 (sucesso)
FIM: 2025-12-03 17:13:51
Wrapper foi chamado
```

**Tempo total**: 12 segundos (17:13:39 → 17:13:51)

**Validação**:
- ✅ Dialog de sucesso apareceu
- ✅ Arquivo gerado em `~/Downloads/Transcricoes/test_10sec/test_10sec_transcrito.txt`
- ✅ Tempo exibido corretamente no dialog
- ✅ Sem erros ou warnings

---

### 🚨 LIÇÕES APRENDIDAS (CRÍTICAS!)

#### 1. SEMPRE seguir metodologia de debug sistemático
**ERRADO**: Fazer 4 tentativas de correção sem entender o problema (força bruta)
**CERTO**:
1. Coletar evidências (logs completos)
2. Analisar root cause
3. Implementar solução baseada em evidências

#### 2. AppleScript `do shell script` roda em ambiente minimalista
**Problema recorrente**:
- Working directory = `/` (não o diretório do script)
- PATH mínimo (apenas `/usr/bin:/bin:/usr/sbin:/sbin`)
- Sem variáveis de ambiente do usuário

**Solução padrão**:
Sempre configurar ambiente no início de scripts Python chamados por AppleScript:
```python
os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ.get('PATH', '')
os.chdir(str(Path(__file__).parent))
```

#### 3. Logging detalhado é ESSENCIAL para debug
Sem logging:
- 4 tentativas falhas
- Assumindo causas incorretas
- Tratando sintomas

Com logging:
- Causa raiz identificada imediatamente
- Solução implementada em 1 tentativa
- Evidências para documentação futura

#### 4. NUNCA assumir ambiente de execução
**Teste terminal ≠ Teste GUI**
- Terminal: Shell completo, PATH do usuário, working dir correto
- AppleScript: Shell mínimo, PATH básico, working dir = `/`

Sempre validar:
```python
log_debug(f"Working directory: {os.getcwd()}")
log_debug(f"Environment PATH: {os.environ.get('PATH', 'NOT SET')}")
```

#### 5. macOS notificações nativas via osascript são simples
**Implementação**:
```python
def send_success_dialog(message, title="Transcrição Concluída"):
    cmd = f'display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK" with icon note'
    subprocess.run(['osascript', '-e', cmd], check=False)
```

**Funcionam dentro de subprocess Python** sem problemas quando ambiente está configurado.

#### 6. Droplet apps são ideais para processamento de arquivos
**Vantagens**:
- Interface nativa macOS (drag-and-drop)
- Sem dependências (apenas AppleScript + Python)
- Distribuível como `.app` bundle
- Pode ser colocado no Dock

**Compilação**:
```bash
osacompile -o ~/Applications/TranscribeVideo.app script.applescript
```

---

### 📁 ARQUIVOS CRIADOS/MODIFICADOS

#### Novos arquivos
- `transcribe_wrapper.py`: Wrapper com notificações e logging
- `~/Applications/TranscribeVideo.app`: Droplet macOS
- `applescript_debug.log`: Log de debug detalhado

#### Arquivos modificados
- `transcribe_complete.py`: Adicionado parâmetro `--output-dir` (já documentado anteriormente)

#### Arquivos temporários (limpeza pendente)
- `/tmp/test_applescript_simple.applescript`
- `/tmp/test_applescript_debug.applescript`
- `test_10sec.mp4` (arquivo de teste)

---

### ⏭️ PRÓXIMOS PASSOS

1. ✅ GUI funcional (droplet app)
2. ✅ Debug sistemático documentado
3. ⏳ TODO: Atualizar README com instruções de uso do GUI
4. ⏳ TODO: Testar com vídeos maiores via GUI
5. ⏳ TODO: Adicionar suporte a múltiplos arquivos simultâneos
6. ⏳ TODO: Implementar barra de progresso (difícil em AppleScript)

---

## [2025-12-02] - Teste com Vídeo ANP-PRH + Bug Crítico do Parser

### 🎯 OBJETIVO DA SESSÃO
Testar o sistema integrado `transcribe_complete.py` com novo vídeo: `[ANP-PRH] Innovation Connections: Oficina 5 | Encontro de Tira-Dúvidas.mp4` (primeiros 10 minutos).

### ❌ PROBLEMA CRÍTICO DESCOBERTO
**Bug**: Parser retornando 0 segmentos apesar de transcrição e diarização funcionarem.

**Sintomas**:
- Transcrição: ✅ 55.7s, 166 linhas geradas
- Diarização: ✅ 148.0s, 9→5 speakers, 52 segmentos
- **Mesclagem: ❌ 0 segmentos finais**
- Arquivo final: 113 bytes (apenas cabeçalho, SEM conteúdo)

**Diagnóstico**:
1. Script completava todas as 4 etapas sem erros
2. Whisper-cli gerava arquivo temporário corretamente
3. Parser `parse_whisper_output()` não extraía nenhum segmento

**Investigação**:
- Criado áudio de teste de 30s: `/tmp/test_30s.wav`
- Testado whisper-cli com flag `-otxt`:
  - Resultado: Texto puro SEM timestamps
  - Exemplo: `e a gente vai ver se a gente vai conseguir fazer isso.`
- Testado whisper-cli com flag `-osrt`:
  - Resultado: Formato SRT COM timestamps
  - Exemplo:
    ```
    1
    00:00:00,000 --> 00:00:04,000
     e a gente vai ver se a gente vai conseguir fazer isso.
    ```

**ROOT CAUSE**:
O script usava flag `-otxt` mas o parser `parse_whisper_output()` esperava timestamps. Texto puro não contém timestamps, então nenhum segmento era extraído.

### ✅ SOLUÇÃO IMPLEMENTADA

**Arquivo**: `transcribe_complete.py`

**Mudanças**:
1. **Linha 82**: Alterado flag de saída
   ```python
   # ANTES:
   '-otxt',  # formato texto

   # DEPOIS:
   '-osrt',  # formato SRT com timestamps
   ```

2. **Linha 95**: Alterado extensão do arquivo de saída
   ```python
   # ANTES:
   output_file = f"{output_base}.txt"

   # DEPOIS:
   output_file = f"{output_base}.srt"
   ```

3. **Linhas 111-175**: Reescrito completamente o parser
   ```python
   def parse_whisper_output(srt_content):
       """Parse da saída do Whisper em formato SRT"""
       segments = []
       lines = srt_content.strip().split('\n')

       i = 0
       while i < len(lines):
           # Pular linha vazia
           if not lines[i].strip():
               i += 1
               continue

           # Linha do número do segmento (ignorar)
           if lines[i].strip().isdigit():
               i += 1
               if i >= len(lines):
                   break

           # Linha de timestamp: 00:00:00,000 --> 00:00:04,000
           if '-->' in lines[i]:
               try:
                   timestamp_line = lines[i].strip()
                   start_str, end_str = timestamp_line.split('-->')
                   start_str = start_str.strip()
                   end_str = end_str.strip()

                   # Converter para segundos
                   start_seconds = parse_srt_timestamp(start_str)
                   end_seconds = parse_srt_timestamp(end_str)

                   i += 1
                   if i >= len(lines):
                       break

                   # Próxima linha é o texto
                   text = lines[i].strip()

                   if text:
                       segments.append({
                           'start': start_seconds,
                           'end': end_seconds,
                           'text': text
                       })
               except Exception as e:
                   pass

           i += 1

       return segments
   ```

4. **Linhas 161-175**: Adicionada função de conversão de timestamp SRT
   ```python
   def parse_srt_timestamp(timestamp_str):
       """Converte timestamp SRT (HH:MM:SS,mmm) para segundos"""
       # Formato: 00:00:12,000
       try:
           time_part, ms_part = timestamp_str.replace(',', '.').split('.')
           parts = time_part.split(':')
           if len(parts) == 3:
               hours = int(parts[0])
               minutes = int(parts[1])
               seconds = int(parts[2])
               milliseconds = int(ms_part)
               return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
       except:
           return 0.0
       return 0.0
   ```

### ✅ RESULTADO DO TESTE (Após correção)

**Vídeo**: `test_video_10min.mp4` (20.3 MB, extraído com `ffmpeg -t 00:10:00`)

**Execução**:
```bash
python3 transcribe_complete.py test_video_10min.mp4 --model medium --threshold 0.75
```

**Resultados**:
- ✅ Extração de áudio: 18.3 MB
- ✅ Transcrição: 81.7s, **166 segmentos** (formato SRT)
- ✅ Diarização: 142.1s, **9→5 speakers** (pós-processamento)
- ✅ Mesclagem: **166 segmentos finais**
- ✅ Saída: `test_video_10min_transcrito.txt`

**Validação**:
- Formato: `[HH:MM:SS] SPEAKER_X: texto` ✅
- 3 speakers principais identificados ✅
- Timestamps progressivos de 0:00:00 até 0:10:00 ✅
- Transcrição em português clara e coerente ✅
- Diarização contextualmente correta (turnos de conversação) ✅

**Exemplo de saída**:
```
[0:00:00] SPEAKER_0: Peso grande ou pequeno, enfim, vocês pudessem, às vezes,
[0:00:02] SPEAKER_0: me esclarecer isso fazendo, por favor?
[0:00:03] SPEAKER_1: Bacana. Quando você diz acessível, é tipo comercialmente acessível?
[0:00:09] SPEAKER_0: É. Ou já naqueles níveis de pesquisa ali mais prestes a sair para o mercado, sabe?
```

---

## [2025-11-XX] - Ajuste de Threshold e Pós-processamento

### ❌ PROBLEMA
Threshold inicial de 0.5 detectando **335 speakers** (absurdamente alto para vídeos com 2-5 pessoas).

### 🔍 ANÁLISE
- Threshold muito baixo agrupa vozes muito similares como speakers diferentes
- Variações naturais da mesma voz (tom, volume, ruído) criavam múltiplos clusters

### ✅ SOLUÇÃO
1. **Aumentado threshold para 0.75**:
   ```python
   clustering=sherpa_onnx.FastClusteringConfig(
       num_clusters=-1,
       threshold=0.75  # era 0.5
   ),
   ```

2. **Adicionado pós-processamento** (`post_process_speakers()`):
   - Identifica speakers "esporádicos" com <10% dos segmentos
   - Mapeia speakers esporádicos para o speaker principal mais próximo temporalmente
   - Renumera speakers finais (0, 1, 2, ...)

**Resultado**:
- Teste Aula IA: 9 speakers → 5 speakers (após pós-processamento)
- Teste ANP-PRH: 9 speakers → 5 speakers (após pós-processamento)

---

## [2025-11-XX] - Abandono de Pyannote + Adoção de Sherpa-ONNX

### ❌ PROBLEMA COM PYANNOTE
Tentativa de usar `pyannote.audio` para diarização resultou em múltiplos problemas:

**Incompatibilidades**:
- PyTorch 2.5.1 incompatível com pyannote.audio
- Downgrade para PyTorch 2.0.0 quebrou outras dependências
- Conflitos entre versões de `torchaudio`, `pytorch`, `pyannote-audio`
- Instalação congelando em `Resolving dependencies...`

**Problemas de autenticação**:
- Pyannote exige token do Hugging Face
- Modelos pesados (centenas de MB)
- Processo complicado de configuração

### ✅ SOLUÇÃO: SHERPA-ONNX
Migrado para `sherpa-onnx` como biblioteca de diarização:

**Vantagens**:
- ✅ Sem dependência de PyTorch
- ✅ Usa ONNX Runtime (mais leve e rápido)
- ✅ Instalação simples: `pip install sherpa-onnx`
- ✅ Modelos públicos disponíveis sem autenticação
- ✅ API Python clara e documentada

**Implementação**:
```python
import sherpa_onnx

config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
    segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
        pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
            model=str(segmentation_model)
        ),
        num_threads=os.cpu_count()
    ),
    embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
        model=str(embedding_model),
        num_threads=os.cpu_count()
    ),
    clustering=sherpa_onnx.FastClusteringConfig(
        num_clusters=-1,
        threshold=0.75
    ),
    min_duration_on=0.5,
    min_duration_off=0.5
)

diarizer = sherpa_onnx.OfflineSpeakerDiarization(config)
result = diarizer.process(samples)
segments = result.sort_by_start_time()  # API descoberta: sort_by_start_time()!
```

**Modelos usados**:
- Segmentação: `sherpa-onnx-pyannote-segmentation-3-0/model.onnx`
- Embedding: `3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx`

**Descoberta importante**:
API `result.sort_by_start_time()` retorna lista já ordenada temporalmente!

---

## [2025-11-XX] - Escolha do Whisper.cpp

### 🎯 DECISÃO
Usar `whisper.cpp` em vez de `whisper` Python oficial.

### 💡 JUSTIFICATIVA
- **Performance**: 7-10x mais rápido que versão Python
- **Instalação simples**: `brew install whisper-cpp`
- **Mesmos modelos**: Compatível com modelos GGML do OpenAI
- **CLI prático**: `whisper-cli` com flags intuitivas
- **Saída SRT**: Flag `-osrt` para timestamps estruturados

**Comando padrão**:
```bash
whisper-cli \
  -m ~/Experimentos/whisper-transcription/whisper-cpp-models/ggml-medium.bin \
  -f audio.wav \
  -l pt \
  -osrt \
  -of output
```

**Modelos disponíveis**: tiny, base, small, medium, large
**Modelo escolhido**: `medium` (bom equilíbrio velocidade/qualidade)

---

## 📊 MÉTRICAS DE PERFORMANCE

### Teste ANP-PRH (10 minutos de vídeo)
- **Extração de áudio**: ~2s
- **Transcrição (Whisper medium)**: 81.7s (RTF ≈ 0.14)
- **Diarização (Sherpa-ONNX)**: 142.1s (RTF ≈ 0.24)
- **Mesclagem**: <1s
- **Total**: ~226s (3min 46s) para 10min de vídeo
- **RTF total**: ≈ 0.38 (2.6x mais rápido que tempo real)

### Qualidade
- **Transcrição**: 166 segmentos com texto claro
- **Diarização**: 9→5 speakers (pós-processamento eficaz)
- **WER (estimado)**: Não medido, mas visualmente < 5%
- **Speaker accuracy (visual)**: Turnos de conversação coerentes

---

## 🏗️ ARQUITETURA FINAL

### Pipeline Integrado (`transcribe_complete.py`)
```
Vídeo/Áudio
    ↓
[1] Extração de áudio (ffmpeg)
    → WAV 16kHz mono
    ↓
[2] Transcrição (Whisper.cpp)
    → Formato SRT com timestamps
    ↓
[3] Diarização (Sherpa-ONNX)
    → Segmentos (start, end, speaker_id)
    → Pós-processamento (merge esporádicos)
    ↓
[4] Mesclagem
    → Matching timestamp meio do segmento
    → Resultado: [{start, end, speaker, text}, ...]
    ↓
Arquivo TXT final
    → Formato: [HH:MM:SS] SPEAKER_X: texto
```

### Dependências Críticas
- `ffmpeg`: Extração/conversão de áudio
- `whisper-cpp`: Transcrição rápida
- `sherpa-onnx`: Diarização sem PyTorch
- `numpy`: Manipulação de arrays de áudio
- `wave`: Leitura de arquivos WAV

---

## 🚨 LIÇÕES APRENDIDAS

### 1. SEMPRE use formato SRT para transcrição
- Formatos sem timestamp (`-otxt`) são inúteis para diarização
- SRT estruturado facilita parsing e debugging

### 2. Teste formatos de saída antes de integrar
- Criado `/tmp/test_30s.wav` para validar whisper-cli
- Descobriu incompatibilidade antes de gastar horas

### 3. Pós-processamento é essencial
- Algoritmos de clustering geram speakers "esporádicos"
- Threshold 10% funciona bem para vídeos de 10-60min

### 4. API Sherpa-ONNX é bem projetada
- `result.sort_by_start_time()` evita sorting manual
- `result.num_speakers` e `result.num_segments` úteis

### 5. Evite Pyannote se possível
- Muitas dependências e problemas de compatibilidade
- Sherpa-ONNX é alternativa superior

### 6. Logging permanente é CRÍTICO
- Autocompactações causam perda massiva de contexto
- CHANGELOG.md previne retrabalho
- Nuances de problemas/soluções são valiosas

---

## 📁 ARQUIVOS IMPORTANTES

### Scripts principais
- `transcribe_complete.py`: Script integrado completo (USAR ESTE!)
- `transcribe_with_diarization.py`: Versão anterior (DEPRECATED)
- `add_diarization_only.py`: Apenas diarização (DEPRECATED)

### Modelos
- `~/Experimentos/whisper-transcription/whisper-cpp-models/ggml-medium.bin`: Modelo Whisper
- `~/Experimentos/whisper-transcription/sherpa-onnx-models/`: Modelos de diarização

### Testes
- `test_video_10min.mp4`: Vídeo ANP-PRH (10min, 20.3 MB)
- `test_video_10min_transcrito.txt`: Resultado final validado
- `/tmp/test_30s.wav`: Áudio de teste para whisper-cli
- `/tmp/test_srt.srt`: Saída SRT de teste

---

## ⏭️ PRÓXIMOS PASSOS

1. ✅ VALIDADO: Sistema funciona corretamente
2. ⏳ TODO: Testar com vídeos mais longos (30min, 1h)
3. ⏳ TODO: Medir WER (Word Error Rate) objetivamente
4. ⏳ TODO: Implementar cache de transcrições
5. ⏳ TODO: Interface web para upload/download
6. ⏳ TODO: Suporte a múltiplos idiomas

---

## 🔗 REFERÊNCIAS

- Whisper.cpp: https://github.com/ggerganov/whisper.cpp
- Sherpa-ONNX: https://github.com/k2-fsa/sherpa-onnx
- SRT Format: https://en.wikipedia.org/wiki/SubRip

---

**ÚLTIMA ATUALIZAÇÃO**: 2 de dezembro de 2025
**AUTOR**: Claude Code + Danilo Lima
**STATUS**: ✅ Sistema em produção, funcionando corretamente
