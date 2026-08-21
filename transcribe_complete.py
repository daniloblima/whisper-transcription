#!/usr/bin/env python3
"""
Script integrado completo para transcrição com diarização
Usa Whisper.cpp para transcrição rápida + Sherpa-ONNX para speaker diarization

Uso:
    python3 transcribe_complete.py <video_ou_audio>
    python3 transcribe_complete.py <video_ou_audio> --speakers 1
    python3 transcribe_complete.py <video_ou_audio> --max-speakers 5
    python3 transcribe_complete.py <video_ou_audio> --threshold 0.75
    python3 transcribe_complete.py <video_ou_audio> --model medium
    python3 transcribe_complete.py <video_ou_audio> --sem-glossario

Saída: arquivo .md no formato [HH:MM:SS] SPEAKER_X: texto transcrito,
já com os termos do glossario.json corrigidos.
"""

import sys
import os
import subprocess
import tempfile
import wave
import numpy as np
import sherpa_onnx
from pathlib import Path
from datetime import timedelta
from collections import Counter
import argparse
import time

# Correção determinística de termos (passo 5). Import tolerante a falha:
# o módulo é opcional e a transcrição nunca pode morrer por causa dele.
try:
    from corrigir_termos import corrigir_arquivo
    GLOSSARIO_DISPONIVEL = True
except ImportError as e:
    print(f"⚠️  corrigir_termos.py não pôde ser importado ({e}).")
    print(f"⚠️  A transcrição roda normalmente, sem correção de termos.")
    GLOSSARIO_DISPONIVEL = False

def print_step(step_num, total_steps, message):
    """Imprime mensagem de progresso formatada"""
    print(f"\n{'='*80}")
    print(f"PASSO {step_num}/{total_steps}: {message}")
    print(f"{'='*80}")

def format_timestamp(seconds):
    """Formata segundos para HH:MM:SS"""
    return str(timedelta(seconds=int(seconds)))

def get_audio_streams(video_path):
    """Detecta todas as streams de áudio do vídeo"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'a',
        '-show_entries', 'stream=index,bit_rate,codec_name',
        '-of', 'csv=p=0',
        str(video_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return []

    streams = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split(',')
        if len(parts) >= 2:
            try:
                index = int(parts[0])
                codec = parts[1] if len(parts) > 1 else 'unknown'
                bitrate = int(parts[2]) if len(parts) > 2 and parts[2] != 'N/A' else 0
                streams.append({'index': index, 'codec': codec, 'bitrate': bitrate})
            except (ValueError, IndexError):
                continue

    return streams


def get_video_duration(video_path):
    """Retorna a duração do vídeo em segundos"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            return float(result.stdout.strip())
        except ValueError:
            pass
    return 0


def test_stream_content(video_path, stream_index, whisper_model_path, test_duration=30):
    """Testa uma stream de áudio transcrevendo um trecho e contando silêncios"""
    import tempfile

    # Obter duração do vídeo
    duration = get_video_duration(video_path)

    # Testar no INÍCIO do vídeo (após primeiros 30s para pular introduções)
    # É onde a diferença entre streams é mais evidente em gravações do Azayaka
    if duration < 90:
        start_time = 0
    else:
        start_time = 30  # Pular primeiros 30 segundos (pode ter silêncio de setup)

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp_wav = tmp.name

    try:
        # Extrair trecho de áudio
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-ss', str(int(start_time)),
            '-t', str(test_duration),
            '-map', f'0:{stream_index}',
            '-ar', '16000', '-ac', '1', '-acodec', 'pcm_s16le',
            '-y', tmp_wav
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {'silence_count': 999, 'total_count': 0}

        # Transcrever com Whisper
        with tempfile.NamedTemporaryFile(suffix='.srt', delete=False) as tmp_srt:
            tmp_srt_base = tmp_srt.name.replace('.srt', '')

        cmd = [
            '/opt/homebrew/bin/whisper-cli',
            '-m', whisper_model_path,
            '-f', tmp_wav,
            '-l', 'auto',
            '-osrt',
            '-of', tmp_srt_base
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        # Analisar resultado - contar quantidade de conteúdo real
        srt_file = f"{tmp_srt_base}.srt"
        if os.path.exists(srt_file):
            with open(srt_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extrair apenas linhas de texto (não números de segmento nem timestamps)
            text_lines = [l.strip() for l in content.split('\n')
                         if l.strip() and not l.strip().isdigit() and '-->' not in l]

            # Contar caracteres totais de texto (melhor métrica que número de linhas)
            total_chars = sum(len(l) for l in text_lines)

            # Contar silêncios explícitos
            silence_lines = sum(1 for l in text_lines if 'silêncio' in l.lower() or 'silencio' in l.lower())

            os.remove(srt_file)
            os.remove(tmp_wav)

            # content_ratio baseado em caracteres por segundo de áudio testado
            # Quanto mais texto, melhor a stream
            chars_per_second = total_chars / max(test_duration, 1)

            return {
                'silence_count': silence_lines,
                'total_count': len(text_lines),
                'total_chars': total_chars,
                'chars_per_second': chars_per_second,
                'content_ratio': chars_per_second / 10.0  # Normalizar (10 chars/s = 100%)
            }

        return {'silence_count': 999, 'total_count': 0, 'content_ratio': 0}

    except Exception as e:
        return {'silence_count': 999, 'total_count': 0, 'content_ratio': 0}


def get_best_audio_stream(video_path, whisper_model_path=None):
    """
    Detecta a melhor stream de áudio testando o conteúdo real.

    Para arquivos do Azayaka com múltiplas streams, a única forma confiável
    de selecionar a stream correta é testar o conteúdo de cada uma.

    O Azayaka grava 2 streams (microfone + sistema), mas qual é qual
    VARIA por gravação/configuração. Regras baseadas em codec, índice
    ou bitrate NÃO funcionam de forma consistente.
    """
    streams = get_audio_streams(video_path)

    if not streams:
        return None

    if len(streams) == 1:
        print(f"   📢 Apenas 1 stream de áudio detectada: #{streams[0]['index']}")
        return streams[0]['index']

    print(f"   📢 {len(streams)} streams de áudio detectadas")

    # Para múltiplas streams: SEMPRE testar conteúdo real
    if whisper_model_path and len(streams) > 1:
        print("   🔍 Testando conteúdo de cada stream (isso pode levar ~60s)...")
        best_stream = None
        best_content_ratio = -1

        for stream in streams:
            result = test_stream_content(video_path, stream['index'], whisper_model_path)
            ratio = result.get('content_ratio', 0)
            print(f"      Stream #{stream['index']} ({stream['codec']}, {stream['bitrate']} bps): {ratio:.0%} conteúdo")

            if ratio > best_content_ratio:
                best_content_ratio = ratio
                best_stream = stream

        if best_stream and best_content_ratio > 0:
            print(f"   🎯 Selecionada stream #{best_stream['index']} ({best_content_ratio:.0%} conteúdo)")
            return best_stream['index']

    # Fallback: maior bitrate (se teste falhar ou whisper_model_path não fornecido)
    best = max(streams, key=lambda x: x['bitrate'])
    print(f"   🎯 Fallback: usando stream #{best['index']} (maior bitrate: {best['bitrate']} bps)")
    return best['index']

def extract_audio(video_path, output_wav, whisper_model_path=None):
    """Extrai áudio do vídeo em formato WAV 16kHz mono

    Para arquivos do Azayaka com múltiplas streams de áudio (microfone + sistema),
    mixa todas as streams em mono. Isso resolve o problema de repetições causado
    por streams parcialmente silenciosas ou com gaps.
    """
    print(f"   Extraindo áudio de: {video_path}")
    print(f"   Formato de saída: WAV 16kHz mono")

    # Detectar streams de áudio
    streams = get_audio_streams(video_path)

    if not streams:
        print(f"   ❌ Nenhuma stream de áudio encontrada")
        return False

    if len(streams) == 1:
        # Uma única stream - extrair diretamente
        print(f"   📢 1 stream de áudio detectada: #{streams[0]['index']} ({streams[0]['codec']})")
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-map', f"0:{streams[0]['index']}",
            '-ar', '16000', '-ac', '1', '-acodec', 'pcm_s16le',
            '-y', str(output_wav)
        ]
    else:
        # Múltiplas streams - MIXAR todas em mono
        # Isso resolve o problema de repetições do Azayaka, onde uma stream pode
        # ter silêncio ou gaps que causam comportamento errático do Whisper
        print(f"   📢 {len(streams)} streams de áudio detectadas - MIXANDO em mono")
        for s in streams:
            print(f"      Stream #{s['index']}: {s['codec']}, {s['bitrate']} bps")

        # Construir filter_complex para mixar todas as streams
        # Ex: "[0:1][0:2]amix=inputs=2:duration=longest[aout]"
        stream_refs = ''.join([f"[0:{s['index']}]" for s in streams])
        filter_complex = f"{stream_refs}amix=inputs={len(streams)}:duration=longest[aout]"

        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-filter_complex', filter_complex,
            '-map', '[aout]',
            '-ar', '16000', '-ac', '1',
            '-y', str(output_wav)
        ]
        print(f"   🔀 Mixando streams com: {filter_complex}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"   ❌ Erro ao extrair áudio: {result.stderr}")
        return False

    file_size = os.path.getsize(output_wav) / (1024*1024)  # MB
    print(f"   ✅ Áudio extraído: {file_size:.1f} MB")
    return True

def transcribe_with_whisper(audio_path, model_name='medium', language='auto'):
    """Transcreve áudio usando Whisper.cpp"""
    home = Path.home()
    model_path = home / f"Experimentos/whisper-transcription/whisper-cpp-models/ggml-{model_name}.bin"
    whisper_cli = "/opt/homebrew/bin/whisper-cli"

    if not model_path.exists():
        print(f"   ❌ Modelo não encontrado: {model_path}")
        return None

    print(f"   Modelo Whisper: {model_name}")
    print(f"   Idioma: {language}")
    print(f"   Processando (pode demorar)...")

    # Criar arquivo temporário para resultado
    output_base = tempfile.mktemp(prefix='whisper_')

    cmd = [
        whisper_cli,
        '-m', str(model_path),
        '-f', str(audio_path),
        '-l', language,
        '-osrt',  # formato SRT com timestamps
        '-of', output_base,
        '--beam-size', '5',  # Beam search para evitar repetições
        '--best-of', '5'     # Múltiplas candidatas para melhor resultado
    ]

    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start_time

    if result.returncode != 0:
        print(f"   ❌ Erro na transcrição: {result.stderr}")
        return None

    # Ler resultado
    output_file = f"{output_base}.srt"
    if not os.path.exists(output_file):
        print(f"   ❌ Arquivo de transcrição não gerado: {output_file}")
        return None

    with open(output_file, 'r', encoding='utf-8') as f:
        transcription_content = f.read()

    # Limpar arquivo temporário
    os.remove(output_file)

    print(f"   ✅ Transcrição concluída em {elapsed:.1f}s")
    print(f"   📝 Arquivo SRT processado")

    return transcription_content

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

# Escolhido em 21/08/2026 por medição em dois áudios com verdade conhecida, e
# desempatado pelo ouvido do Danilo numa aula de 1h09 com duas vozes. O modelo
# anterior (eres2net base) via 7 pessoas nessa aula e 2 numa nota de voz de 1.
EMBEDDING_PADRAO = "wespeaker_en_voxceleb_resnet34_LM.onnx"

# 0,75 era o valor do modelo antigo. Com o wespeaker, 0,92 acerta os dois áudios de
# referência e 0,75 erra a aula. Medição no CHANGELOG de 21/08/2026.
THRESHOLD_PADRAO = 0.92


def _montar_diarizer(segmentation_model, embedding_model, num_clusters, threshold):
    """Monta o diarizador do Sherpa-ONNX.

    num_clusters = -1 deixa o algoritmo decidir sozinho quantas pessoas existem,
    guiado só pelo threshold. Qualquer valor >= 1 fixa o número.
    """
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
            num_clusters=num_clusters,
            threshold=threshold
        ),
        min_duration_on=0.5,
        min_duration_off=0.5
    )
    return sherpa_onnx.OfflineSpeakerDiarization(config)


def _ler_wav_mono(audio_path):
    """Lê WAV e devolve as amostras em float32 mono, normalizadas."""
    with wave.open(str(audio_path), 'rb') as wf:
        num_channels = wf.getnchannels()
        audio_data = wf.readframes(wf.getnframes())

        if wf.getsampwidth() != 2:
            raise ValueError("Unsupported sample width")

        samples = np.frombuffer(audio_data, dtype=np.int16)

        if num_channels == 2:
            samples = samples.reshape(-1, 2).mean(axis=1)

        return samples.astype(np.float32) / 32768.0


def diarize_audio(audio_path, threshold=THRESHOLD_PADRAO, min_fala_segundos=8.0,
                  min_fala_ratio=0.005, num_speakers=None, max_speakers=None,
                  embedding_model=None):
    """Diariza áudio usando Sherpa-ONNX, com controle sobre o número de falantes.

    Três modos, e a escolha entre eles depende do que se sabe sobre o áudio:

    - num_speakers=N: o número é conhecido (nota de voz, entrevista de duas
      pessoas). Fixa N e desliga a fusão do pós-processamento, porque se o número
      foi declarado não faz sentido o script reduzir abaixo dele.
    - max_speakers=N: existe um teto conhecido mas não o número exato (webinário
      com um palestrante e perguntas da plateia). Roda a detecção livre e só
      refaz com N fixo se o resultado passar do teto.
    - nenhum dos dois: detecção livre, como sempre foi.

    O modo livre é o que produziu três falantes num áudio de dez minutos com uma
    pessoa só, em 20/08/2026: variação de tom ao longo do tempo atravessa o
    threshold e vira gente nova. Daí a existência dos dois primeiros modos.
    """
    home = Path.home()
    models_dir = home / "Experimentos/whisper-transcription/sherpa-onnx-models"
    segmentation_model = models_dir / "sherpa-onnx-pyannote-segmentation-3-0/model.onnx"

    if embedding_model is None:
        embedding_model = models_dir / EMBEDDING_PADRAO
    else:
        embedding_model = Path(embedding_model)
        if not embedding_model.is_absolute():
            embedding_model = models_dir / embedding_model

    if not embedding_model.exists():
        print(f"   ❌ Modelo de embedding não encontrado: {embedding_model}")
        return []

    if num_speakers is not None:
        print(f"   Falantes: {num_speakers} (declarado)")
    elif max_speakers is not None:
        print(f"   Falantes: automático, teto de {max_speakers}")
    else:
        print(f"   Falantes: automático, sem teto")
    print(f"   Threshold: {threshold}")
    print(f"   Embedding: {embedding_model.name}")
    print(f"   Carregando modelos...")

    print(f"   Lendo áudio...")
    samples = _ler_wav_mono(audio_path)

    num_clusters = num_speakers if num_speakers is not None else -1
    diarizer = _montar_diarizer(segmentation_model, embedding_model, num_clusters, threshold)

    print(f"   Processando diarização...")
    start_time = time.time()
    result = diarizer.process(samples)
    elapsed = time.time() - start_time

    if result.num_segments == 0:
        print("   ⚠️  Nenhum segmento de fala detectado")
        return []

    detectados_brutos = result.num_speakers

    # Teto: só age se a detecção livre passou do limite informado.
    #
    # Sobe o limiar antes de fixar o número, e a ordem importa. Fixar num_clusters faz
    # o agrupamento ignorar o limiar e trocar de estratégia, e para o wespeaker isso
    # piora muito: na aula de 1h09 com duas pessoas, o número fixo devolveu 67 e 2
    # minutos (as duas vozes coladas numa), enquanto o modo livre com limiar 0,92
    # devolveu 12 e 57. Fixar fica como último recurso.
    if num_speakers is None and max_speakers is not None and detectados_brutos > max_speakers:
        for tentativa in (0.95, 0.97, 0.99):
            if tentativa <= threshold:
                continue
            print(f"   ↻ Achou {result.num_speakers}, acima do teto de {max_speakers}. "
                  f"Subindo o limiar para {tentativa}.")
            diarizer = _montar_diarizer(segmentation_model, embedding_model, -1, tentativa)
            inicio_refaz = time.time()
            novo = diarizer.process(samples)
            elapsed += time.time() - inicio_refaz
            if novo.num_segments and novo.num_speakers <= max_speakers:
                result = novo
                break
            if novo.num_segments:
                result = novo
        else:
            if result.num_speakers > max_speakers:
                print(f"   ↻ Limiar no teto e ainda {result.num_speakers}. "
                      f"Fixando em {max_speakers} como último recurso.")
                diarizer = _montar_diarizer(segmentation_model, embedding_model, max_speakers, threshold)
                inicio_refaz = time.time()
                novo = diarizer.process(samples)
                elapsed += time.time() - inicio_refaz
                if novo.num_segments:
                    result = novo
        if result.num_segments == 0:
            print("   ⚠️  Nenhum segmento de fala detectado após o teto")
            return []

    segments = result.sort_by_start_time()
    raw_segments = [(seg.start, seg.end, seg.speaker) for seg in segments]

    # Com número declarado, a fusão sairia por cima da informação do usuário.
    if num_speakers is not None:
        processed_segments = renumerar(raw_segments)
        print(f"   Pós-processamento: desligado (número declarado)")
    else:
        print(f"   Pós-processamento: mínimo de {min_fala_segundos:.0f}s de fala por pessoa")
        processed_segments = post_process_speakers(
            raw_segments, min_fala_segundos=min_fala_segundos, min_fala_ratio=min_fala_ratio
        )

    final_speaker_count = len(set(seg[2] for seg in processed_segments))

    print(f"   ✅ Diarização concluída em {elapsed:.1f}s")
    print(f"   🎤 Speakers detectados: {detectados_brutos} → {final_speaker_count} (após pós-processamento)")
    print(f"   📊 Total de segmentos: {len(processed_segments)}")

    return processed_segments


def renumerar(segments):
    """Renumera os ids de speaker para 0, 1, 2... na ordem em que aparecem."""
    unique_speakers = sorted(set(seg[2] for seg in segments))
    mapping = {old: new for new, old in enumerate(unique_speakers)}
    return [(s, e, mapping[spk]) for s, e, spk in segments]


def post_process_speakers(segments, min_fala_segundos=8.0, min_fala_ratio=0.005):
    """Funde falantes espúrios no vizinho mais próximo, medindo por tempo de fala.

    O critério anterior contava segmentos e descartava quem tivesse menos de 10%
    do total. Isso apaga quem fez uma pergunta curta num webinário de uma hora,
    que é falante legítimo, e é justamente o caso de uso que o Danilo tem além das
    notas de voz. O critério passa a ser tempo somado de fala, com piso absoluto
    em segundos e uma fração pequena da duração total para áudio longo.
    """
    tempo_por_speaker = {}
    for inicio, fim, speaker in segments:
        tempo_por_speaker[speaker] = tempo_por_speaker.get(speaker, 0.0) + (fim - inicio)

    tempo_total = sum(tempo_por_speaker.values())
    corte = max(min_fala_segundos, min_fala_ratio * tempo_total)

    main_speakers = {s: t for s, t in tempo_por_speaker.items() if t >= corte}
    sporadic_speakers = {s: t for s, t in tempo_por_speaker.items() if t < corte}

    # Ninguém passou do corte (áudio curto): mantém o de maior tempo em vez de zerar.
    if not main_speakers:
        dominante = max(tempo_por_speaker.items(), key=lambda x: x[1])[0]
        main_speakers = {dominante: tempo_por_speaker[dominante]}
        sporadic_speakers = {s: t for s, t in tempo_por_speaker.items() if s != dominante}

    if sporadic_speakers:
        nomes = ", ".join(f"SPEAKER_{s} ({t:.1f}s)" for s, t in sorted(sporadic_speakers.items()))
        print(f"   ↳ Fundidos por tempo abaixo de {corte:.1f}s: {nomes}")

    speaker_mapping = {speaker: speaker for speaker in main_speakers}

    for sporadic_speaker in sporadic_speakers:
        sporadic_segments = [seg for seg in segments if seg[2] == sporadic_speaker]
        if not sporadic_segments:
            continue

        closest_main_speaker = None
        min_distance = float('inf')

        for seg in sporadic_segments:
            for main_seg in segments:
                if main_seg[2] not in main_speakers:
                    continue
                distance = min(abs(seg[0] - main_seg[1]), abs(seg[1] - main_seg[0]))
                if distance < min_distance:
                    min_distance = distance
                    closest_main_speaker = main_seg[2]

        if closest_main_speaker is None:
            closest_main_speaker = max(main_speakers.items(), key=lambda x: x[1])[0]

        speaker_mapping[sporadic_speaker] = closest_main_speaker

    merged_segments = [(seg[0], seg[1], speaker_mapping[seg[2]]) for seg in segments]
    return renumerar(merged_segments)

def merge_transcription_and_diarization(transcription_segments, diarization_segments):
    """Mescla transcrição com diarização"""
    print(f"   Mesclando {len(transcription_segments)} segmentos de transcrição")
    print(f"   com {len(diarization_segments)} segmentos de diarização...")

    result = []

    for trans_seg in transcription_segments:
        trans_start = trans_seg['start']
        trans_end = trans_seg['end']
        trans_mid = (trans_start + trans_end) / 2

        # Encontrar speaker no meio do segmento de transcrição
        speaker = find_speaker_at_time(trans_mid, diarization_segments)

        result.append({
            'start': trans_start,
            'end': trans_end,
            'speaker': speaker,
            'text': trans_seg['text']
        })

    print(f"   ✅ Mesclagem concluída: {len(result)} segmentos finais")
    return result

def find_speaker_at_time(timestamp, diarization_segments):
    """Encontra qual speaker está falando em um determinado momento"""
    for seg_start, seg_end, speaker in diarization_segments:
        if seg_start <= timestamp <= seg_end:
            return speaker

    # Se não encontrou overlap exato, encontrar o mais próximo
    min_distance = float('inf')
    closest_speaker = 0

    for seg_start, seg_end, speaker in diarization_segments:
        distance = min(abs(timestamp - seg_start), abs(timestamp - seg_end))
        if distance < min_distance:
            min_distance = distance
            closest_speaker = speaker

    return closest_speaker

def save_final_output(segments, output_file):
    """Salva resultado final formatado em markdown"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Transcrição com Diarização\n\n")

        prev_speaker = None
        for seg in segments:
            timestamp = format_timestamp(seg['start'])
            speaker = f"SPEAKER_{seg['speaker']}"
            text = seg['text']
            if speaker != prev_speaker:
                f.write(f"\n**{speaker}**\n\n")
                prev_speaker = speaker
            f.write(f"`[{timestamp}]` {text}\n\n")

    print(f"\n✅ Resultado salvo em: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Transcrição com diarização usando Whisper + Sherpa-ONNX')
    parser.add_argument('input_file', help='Arquivo de vídeo ou áudio')
    parser.add_argument('--model', default='medium',
                       choices=['tiny', 'base', 'small', 'medium', 'large', 'large-v3-turbo'],
                       help='Modelo Whisper (padrão: medium)')
    parser.add_argument('--threshold', type=float, default=THRESHOLD_PADRAO,
                       help=f'Threshold para diarização (padrão: {THRESHOLD_PADRAO})')
    parser.add_argument('--speakers', type=int, default=None, metavar='N',
                       help='Número exato de pessoas falando. Use quando souber '
                            '(nota de voz do WhatsApp: --speakers 1). Desliga a fusão '
                            'do pós-processamento.')
    parser.add_argument('--max-speakers', type=int, default=None, metavar='N',
                       help='Teto de pessoas, para quando o número exato é desconhecido '
                            '(webinário com palestrante e perguntas da plateia). Só entra '
                            'em ação se a detecção livre passar do teto.')
    parser.add_argument('--embedding', type=str, default=None, metavar='MODELO',
                       help='Modelo de embedding de voz alternativo, por nome de arquivo '
                            'dentro de sherpa-onnx-models/ ou caminho completo.')
    parser.add_argument('--language', default='auto', help='Idioma para transcrição (padrão: auto — detecção automática)')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Diretório de saída (padrão: ~/Downloads/Transcricoes/nome_video/)')
    parser.add_argument('--sem-glossario', action='store_true',
                       help='Pula a correção automática de termos (passo 5)')
    parser.add_argument('--glossario', type=str, default=None,
                       help='Caminho de um glossário alternativo (padrão: glossario.json do projeto)')

    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"❌ Arquivo não encontrado: {input_path}")
        sys.exit(1)

    if args.speakers is not None and args.max_speakers is not None:
        print("❌ Use --speakers ou --max-speakers, não os dois. O primeiro fixa o número, "
              "o segundo é teto para quando o número é desconhecido.")
        sys.exit(1)
    if args.speakers is not None and args.speakers < 1:
        print("❌ --speakers precisa ser 1 ou mais.")
        sys.exit(1)
    if args.max_speakers is not None and args.max_speakers < 1:
        print("❌ --max-speakers precisa ser 1 ou mais.")
        sys.exit(1)

    print("\n" + "="*80)
    print("TRANSCRIÇÃO COMPLETA COM DIARIZAÇÃO")
    print("="*80)
    print(f"Arquivo de entrada: {input_path}")
    print(f"Modelo Whisper: {args.model}")
    print(f"Threshold diarização: {args.threshold}")
    if args.speakers is not None:
        print(f"Falantes: {args.speakers} (declarado)")
    elif args.max_speakers is not None:
        print(f"Falantes: automático, teto de {args.max_speakers}")
    else:
        print(f"Falantes: automático, sem teto")
    print(f"Idioma: {args.language}")
    print("="*80)

    # Passo 1: Extrair áudio
    print_step(1, 5, "Extraindo áudio")
    temp_audio = tempfile.mktemp(suffix='.wav', prefix='audio_')
    # Construir caminho do modelo Whisper para teste de streams
    home = Path.home()
    whisper_model_path = str(home / f"Experimentos/whisper-transcription/whisper-cpp-models/ggml-{args.model}.bin")
    if not extract_audio(input_path, temp_audio, whisper_model_path):
        sys.exit(1)

    # Passo 2: Transcrever
    print_step(2, 5, "Transcrevendo áudio com Whisper")
    transcription_lines = transcribe_with_whisper(temp_audio, args.model, args.language)
    if not transcription_lines:
        os.remove(temp_audio)
        sys.exit(1)

    transcription_segments = parse_whisper_output(transcription_lines)
    print(f"   📝 {len(transcription_segments)} segmentos transcritos")

    # Passo 3: Diarizar
    print_step(3, 5, "Identificando speakers (diarização)")
    diarization_segments = diarize_audio(
        temp_audio,
        threshold=args.threshold,
        num_speakers=args.speakers,
        max_speakers=args.max_speakers,
        embedding_model=args.embedding,
    )

    # Se não detectar speakers (áudio muito curto), criar segmento único com speaker padrão
    if not diarization_segments:
        print(f"   ⚠️  Diarização falhou. Usando speaker padrão (SPEAKER_0).")
        print(f"   💡 Dica: Áudios muito curtos (<15s) podem não ter speakers detectados.")
        # Criar um único segmento cobrindo toda a duração do áudio
        # Usar a duração do último segmento de transcrição
        max_end = max(seg['end'] for seg in transcription_segments)
        diarization_segments = [(0.0, max_end, 0)]

    # Passo 4: Mesclar
    print_step(4, 5, "Mesclando transcrição com diarização")
    final_segments = merge_transcription_and_diarization(transcription_segments, diarization_segments)

    # Criar estrutura de diretórios organizada
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        # Padrão: ~/Downloads/Transcricoes/nome_video/
        base_dir = Path.home() / "Downloads" / "Transcricoes"
        output_dir = base_dir / input_path.stem

    # Criar diretório se não existir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Salvar resultado na pasta organizada
    output_file = output_dir / f"{input_path.stem}_transcrito.md"
    save_final_output(final_segments, output_file)

    # Limpar arquivo temporário
    os.remove(temp_audio)

    # Passo 5: Corrigir termos conhecidos do glossário
    # Só trata erro cujo acerto é sempre o mesmo (nome próprio, sigla, marca).
    # Erro que depende do contexto continua sendo trabalho da skill
    # /arrumar-transcricao, rodada depois sobre este arquivo.
    print_step(5, 5, "Corrigindo termos conhecidos (glossário)")
    trocas = []
    if args.sem_glossario:
        print("   ⏭️  Pulado por --sem-glossario")
    elif not GLOSSARIO_DISPONIVEL:
        print("   ⏭️  Pulado: corrigir_termos.py indisponível")
    else:
        try:
            trocas = corrigir_arquivo(output_file, args.glossario)
        except Exception as e:
            # Falha suave: a transcrição já está salva e não pode ser perdida
            # por causa da etapa de correção.
            print(f"   ⚠️  Correção de termos falhou ({type(e).__name__}): {e}")
            print(f"   ⚠️  A transcrição foi salva sem essa etapa.")

    print("\n" + "="*80)
    print("✅ PROCESSAMENTO CONCLUÍDO!")
    print("="*80)
    print(f"📄 Arquivo de saída: {output_file}")
    print(f"📊 Total de segmentos: {len(final_segments)}")
    print(f"🎤 Speakers identificados: {len(set(seg['speaker'] for seg in final_segments))}")
    print(f"📖 Termos corrigidos: {sum(n for _, _, n in trocas)} em {len(trocas)} termos")
    print("="*80 + "\n")
    print("💡 Erros que dependem do contexto (nome de pessoa, termo do assunto,")
    print("   palavra trocada por outra parecida) não são tratados aqui.")
    print("   Para esses, rode a skill /arrumar-transcricao sobre o arquivo acima.\n")

if __name__ == "__main__":
    main()
