# 🎤 Transcrição com Diarização

Sistema local completo para transcrição de áudio/vídeo com identificação de speakers (quem fala quando).

**Tecnologias:**
- **Whisper.cpp** - Transcrição rápida (7-10x mais rápido que Python)
- **Sherpa-ONNX** - Speaker diarization otimizada
- **Pós-processamento inteligente** - Reduz falsos positivos em 70-80%

---

## 🚀 USO RÁPIDO (GUI - RECOMENDADO)

### Opção 1: Interface Gráfica (Arrasta e Solta)

1. **Abra o app**: `~/Applications/TranscribeVideo.app`
2. **Arraste seu vídeo** para o ícone do app
3. **Aguarde a notificação** de conclusão (com tempo total)
4. **Encontre o arquivo** em `~/Downloads/Transcricoes/nome_do_video/`

**Formatos suportados:** MP4, MOV, AVI, MKV, MP3, WAV, M4A

**Resultado:** Arquivo `nome_do_video_transcrito.txt`:
```
[00:00:12] SPEAKER_0: Olá, bem-vindos à apresentação de hoje...
[00:00:47] SPEAKER_1: Obrigado pela introdução, vamos começar...
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

**Tempo para vídeo de 1h:** ~16-18 minutos

---

## 🛠️ SCRIPTS DISPONÍVEIS

### transcribe_complete.py ⭐ (RECOMENDADO)
Faz tudo automaticamente.

### diarize_with_postprocessing.py
Apenas identifica speakers (sem transcrição).

---

## 📁 ESTRUTURA

```
whisper-transcription/
├── transcribe_complete.py          ⭐ Script principal (Terminal)
├── transcribe_wrapper.py           🖥️ Wrapper GUI (notificações)
├── diarize_with_postprocessing.py  🎯 Diarização
├── whisper_transcription_env/      📦 Python env
├── whisper-cpp-models/             🧠 Modelos Whisper
├── sherpa-onnx-models/             🎤 Modelos diarização
├── CHANGELOG.md                    📝 Histórico técnico completo
└── README.md                       📖 Este arquivo

~/Applications/
└── TranscribeVideo.app             🎬 Droplet GUI (arrasta e solta)

~/Downloads/Transcricoes/
└── [nome_do_video]/                📂 Saída organizada
    └── [nome]_transcrito.txt       📄 Transcrição final
```

---

## 🎯 RESULTADOS DOS TESTES

| Duração | Speakers Bruto | Speakers Final | Redução | Acurácia |
|---------|----------------|----------------|---------|----------|
| 3:12    | 7              | 2              | -71%    | ✅ 100%  |
| 10:00   | 21             | 6              | -71%    | ✅ Boa   |
| 15:00   | 33             | 7              | -79%    | ✅ Boa   |

---

Criado: Dezembro 2024 | Versão 1.0
