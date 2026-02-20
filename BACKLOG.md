# Backlog — Whisper Transcription

Funcionalidades identificadas mas ainda não implementadas.
Consultar antes de iniciar uma nova sessão de desenvolvimento.

---

## Fluxo atual (referência)

1. Usuário arrasta arquivo de vídeo ou áudio para o app `TranscribeVideo.app` no Dock
2. App chama `transcribe_wrapper.py`, que chama `transcribe_complete.py`
3. Script transcreve com Whisper (GPU do Mac) e faz diarização com Sherpa-ONNX
4. Arquivo final salvo em `~/Downloads/transcrições/`

Modelos em uso:
- Transcrição: `whisper-cpp-models/ggml-medium.bin` (via whisper-cli)
- Diarização: `sherpa-onnx-models/sherpa-onnx-pyannote-segmentation-3-0/`

---

## Melhorias identificadas

### Seleção de modo ao dropar o arquivo

Hoje o app sempre roda transcrição + diarização completa.
Seria útil perguntar ao usuário o modo antes de processar:
- Modo 1: Transcrição simples (mais rápido, sem identificar falantes)
- Modo 2: Transcrição + diarização (fluxo atual)

Implementação provável: dialog AppleScript antes de chamar o script Python.

Nota: não existe "adicionar diarização depois" sem o áudio original. A diarização
precisa do áudio para identificar os falantes — não funciona só com o texto.

---

### Indicação de progresso mais clara

Durante o processamento de arquivos longos, o feedback para o usuário é mínimo.
Melhorar as notificações nativas do macOS para mostrar em qual etapa está
(convertendo áudio, transcrevendo, diarizando).

---

### Configuração de idioma

O script assume português. Para transcrever conteúdo em inglês ou outro idioma,
é necessário editar o código. Seria útil uma forma de passar o idioma como
parâmetro — talvez via nome do arquivo ou dialog de entrada.

---

## Scripts em _archive/

Ficam no Mac mas fora do GitHub. Consultar se precisar:

- `transcribe_fast.py` — versão sem diarização, mais rápida
- `add_diarization_only.py` — tentativa de diarizar transcrição existente (não funciona sem áudio)
- `diarize_with_postprocessing.py` — versão experimental do pipeline de diarização
- `explore_sherpa_api.py` / `explore_sherpa_api2.py` — exploração da API Sherpa-ONNX
- `test_*.py` — scripts de teste de desenvolvimento (threshold, otimização, comparação)
- `podcast` — atalho de linha de comando para transcribe_fast.py
