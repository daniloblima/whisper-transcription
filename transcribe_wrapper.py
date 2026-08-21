#!/usr/bin/env python3
"""
Wrapper para executar transcrição com notificações nativas do macOS
Chamado pelo app TranscribeVideo.app

Uso: transcribe_wrapper.py <arquivo> [argumentos extras para transcribe_complete.py]

Os argumentos extras vêm do droplet, que pergunta ao usuário quantas pessoas
falam no áudio antes de disparar o processamento. Exemplo do que chega aqui:
    transcribe_wrapper.py audio.opus --speakers 1
"""
import sys
import os
import subprocess
import re
import time
from pathlib import Path
from datetime import timedelta

def send_success_dialog(message, title="Transcrição Concluída"):
    """Mostra dialog box de sucesso"""
    cmd = f'display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK" with icon note'
    subprocess.run(['osascript', '-e', cmd], check=False)

def send_error_dialog(message, title="Erro"):
    """Mostra dialog box de erro"""
    cmd = f'display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK" with icon stop'
    subprocess.run(['osascript', '-e', cmd], check=False)

def send_progress_notification(message, title="Processando"):
    """Mostra notificação nativa do macOS (discreta)"""
    cmd = f'display notification "{message}" with title "{title}"'
    subprocess.run(['osascript', '-e', cmd], check=False)

def log_to_file(message):
    """Salva log em arquivo para debug"""
    script_dir = Path(__file__).parent
    log_file = script_dir / "transcribe_log.txt"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")

def log_debug(message):
    """Salva log detalhado para debug do AppleScript"""
    script_dir = Path(__file__).parent
    log_file = script_dir / "applescript_debug.log"
    with open(log_file, 'a') as f:
        f.write(f"{message}\n")

def format_duration(seconds):
    """Formata duração em formato legível"""
    td = timedelta(seconds=int(seconds))
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    secs = td.seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}min {secs}s"
    elif minutes > 0:
        return f"{minutes}min {secs}s"
    else:
        return f"{secs}s"

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
    log_debug(f"sys.argv: {sys.argv}")
    log_debug(f"len(sys.argv): {len(sys.argv)}")
    if len(sys.argv) >= 2:
        log_debug(f"Arquivo recebido: {sys.argv[1]}")
        log_debug(f"Arquivo existe: {Path(sys.argv[1]).exists()}")
    log_debug(f"Working directory: {os.getcwd()}")
    log_debug(f"Environment PATH (CORRIGIDO): {os.environ.get('PATH', 'NOT SET')}")

    if len(sys.argv) < 2:
        send_error_dialog("Nenhum arquivo fornecido.")
        log_to_file("ERRO: Nenhum arquivo fornecido")
        log_debug("RETURN CODE: 1 (Nenhum arquivo fornecido)")
        log_debug(f"FIM: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        return 1

    video_file = sys.argv[1]
    video_path = Path(video_file)

    log_to_file(f"INÍCIO: Processando {video_path.name}")

    # Argumentos extras repassados ao script principal (--speakers, --max-speakers).
    # Vêm do droplet e nunca do usuário digitando, então a validação de verdade
    # acontece no argparse do transcribe_complete.py.
    extra_args = sys.argv[2:]
    if extra_args:
        log_to_file(f"Argumentos extras: {' '.join(extra_args)}")

    # Validar arquivo
    if not video_path.exists():
        send_error_dialog(f"Arquivo não encontrado:\\n{video_file}")
        log_to_file(f"ERRO: Arquivo não encontrado - {video_file}")
        log_debug(f"RETURN CODE: 1 (Arquivo não encontrado)")
        log_debug(f"FIM: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        return 1

    # Validar extensão
    # Tudo que o ffmpeg lê e o pipeline consegue converter para WAV 16 kHz mono.
    # .opus e .ogg entraram em 20/08/2026: são o formato nativo das notas de voz do
    # WhatsApp, e a ausência deles obrigava a converter o arquivo por fora antes de
    # arrastar para o app.
    valid_extensions = {
        # vídeo
        '.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv', '.mpg', '.mpeg',
        # áudio
        '.mp3', '.wav', '.m4a', '.opus', '.ogg', '.oga', '.aac', '.flac', '.wma', '.aiff', '.aif',
    }
    if video_path.suffix.lower() not in valid_extensions:
        send_error_dialog(f"Formato não suportado: {video_path.suffix}\\n\\nFormatos aceitos:\\nVídeo: MP4, MOV, AVI, MKV, WEBM, M4V, WMV, FLV, MPG\\nÁudio: MP3, WAV, M4A, OPUS, OGG, AAC, FLAC, WMA, AIFF")
        log_to_file(f"ERRO: Formato não suportado - {video_path.suffix}")
        log_debug(f"RETURN CODE: 1 (Formato não suportado)")
        log_debug(f"FIM: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        return 1

    # Caminhos
    script_dir = Path(__file__).parent
    python_exe = script_dir / "whisper_transcription_env/bin/python3"
    main_script = script_dir / "transcribe_complete.py"

    # Verificar se scripts existem
    if not python_exe.exists():
        send_error_dialog("Ambiente Python não encontrado.\\n\\nVerifique a instalação.")
        log_to_file("ERRO: Ambiente Python não encontrado")
        log_debug(f"RETURN CODE: 1 (Python não encontrado)")
        log_debug(f"FIM: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        return 1

    if not main_script.exists():
        send_error_dialog("Script de transcrição não encontrado.")
        log_to_file("ERRO: Script de transcrição não encontrado")
        log_debug(f"RETURN CODE: 1 (Script não encontrado)")
        log_debug(f"FIM: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        return 1

    log_to_file("Iniciando processo de transcrição...")

    # Notificar usuário que arquivo foi recebido
    send_progress_notification(
        f"Arquivo recebido: {video_path.name}\nIniciando processamento...",
        "Transcrição Iniciada"
    )

    # Executar script principal
    try:
        process = subprocess.Popen(
            [str(python_exe), str(main_script), str(video_path)] + extra_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(script_dir)
        )

        # Monitorar output e detectar etapas para notificações
        for line in process.stdout:
            line = line.strip()

            # Detectar etapas e mostrar notificações
            if "PASSO 1/5" in line:
                send_progress_notification(
                    "Extraindo áudio do arquivo...",
                    "Transcrição, etapa 1 de 5"
                )
            elif "PASSO 2/5" in line:
                send_progress_notification(
                    "Transcrevendo áudio (pode demorar)...",
                    "Transcrição, etapa 2 de 5"
                )
            elif "PASSO 3/5" in line:
                send_progress_notification(
                    "Identificando quem fala...",
                    "Transcrição, etapa 3 de 5"
                )
            elif "PASSO 4/5" in line:
                send_progress_notification(
                    "Juntando texto e falantes...",
                    "Transcrição, etapa 4 de 5"
                )
            elif "PASSO 5/5" in line:
                send_progress_notification(
                    "Corrigindo termos do glossário...",
                    "Transcrição, etapa 5 de 5"
                )

            # Continuar consumindo output para não bloquear

        # Aguardar conclusão
        return_code = process.wait()

        # Calcular tempo total
        end_time = time.time()
        duration = end_time - start_time
        duration_str = format_duration(duration)

        if return_code == 0:
            log_to_file(f"SUCESSO: Processo concluído em {duration_str}")
            log_debug(f"SUBPROCESS: return_code = 0 (sucesso)")

            # Sucesso: encontrar arquivo de saída
            # NOVA ESTRUTURA: pasta organizada em Downloads/Transcricoes/nome_video/
            base_output_dir = Path.home() / "Downloads" / "Transcricoes"
            video_folder = base_output_dir / video_path.stem
            output_file = video_folder / f"{video_path.stem}_transcrito.md"

            if output_file.exists():
                # Dialog de sucesso com tempo
                log_debug(f"OUTPUT FILE: exists = {output_file}")
                send_success_dialog(
                    f"Transcrição concluída com sucesso!\\n\\n"
                    f"Tempo total: {duration_str}\\n\\n"
                    f"Arquivo salvo em:\\n"
                    f"~/Downloads/Transcricoes/{video_path.stem}/\\n\\n"
                    f"Vídeo: {video_path.name}"
                )
                log_debug("RETURN CODE: 0 (sucesso)")
                log_debug(f"FIM: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                log_to_file("ERRO: Arquivo de saída não encontrado")
                log_debug(f"OUTPUT FILE: NOT FOUND - {output_file}")
                send_error_dialog(
                    "Processo concluído mas arquivo não encontrado.\\n\\n"
                    "Verifique a pasta Downloads/Transcricoes/"
                )
                log_debug("RETURN CODE: 0 (mas arquivo não encontrado)")
                log_debug(f"FIM: {time.strftime('%Y-%m-%d %H:%M:%S')}")

            return 0
        else:
            # Erro
            log_to_file(f"ERRO: Processo falhou com código {return_code} após {duration_str}")
            log_debug(f"SUBPROCESS: return_code = {return_code} (ERRO)")
            send_error_dialog(
                "Erro durante a transcrição.\\n\\n"
                "Possíveis causas:\\n"
                "• Áudio muito curto (<15 segundos)\\n"
                "• Áudio sem fala detectável\\n"
                "• Arquivo de vídeo incompatível\\n\\n"
                "Verifique o arquivo e tente novamente.",
                "Erro na Transcrição"
            )
            log_debug(f"RETURN CODE: {return_code}")
            log_debug(f"FIM: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            return return_code

    except Exception as e:
        log_to_file(f"ERRO: Exceção - {str(e)}")
        log_debug(f"EXCEPTION: {str(e)}")
        send_error_dialog(f"Erro inesperado:\\n\\n{str(e)}")
        log_debug("RETURN CODE: 1 (exceção)")
        log_debug(f"FIM: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
