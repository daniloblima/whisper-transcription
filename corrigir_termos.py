#!/usr/bin/env python3
"""
Correção determinística de termos em transcrições.

Aplica o glossário de erros que o Whisper comete sempre do mesmo jeito
(nome próprio, sigla, marca, termo técnico). Roda como passo 5 do
transcribe_complete.py e também sozinho, sobre um arquivo já existente:

    python3 corrigir_termos.py caminho/da/transcricao.md

O que precisa de contexto para ser decidido NÃO é tratado aqui — isso é
trabalho da skill /arrumar-transcricao. Ver glossario.json.

Falha suave por decisão: se o glossário sumir ou estiver quebrado, a
transcrição é entregue sem correção em vez de o processo inteiro morrer.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

PASTA = Path(__file__).resolve().parent
GLOSSARIO_PADRAO = PASTA / "glossario.json"
GLOSSARIO_LOCAL = PASTA / "glossario.local.json"


def carregar_glossario(caminho=None):
    """
    Lê o glossário público e, se existir, o local, devolvendo a lista somada.

    O local (`glossario.local.json`) está no .gitignore e guarda termo ligado a
    pessoa ou empresa com quem o Danilo trabalha, que não vai para o repositório
    público. Ausência dele é normal e silenciosa: numa instalação nova ele não
    existe, e o script funciona igual.

    Quando `caminho` é informado explicitamente, só ele é lido.
    """
    if caminho:
        return _ler_arquivo(Path(caminho))

    termos = _ler_arquivo(GLOSSARIO_PADRAO)

    if GLOSSARIO_LOCAL.exists():
        locais = _ler_arquivo(GLOSSARIO_LOCAL, rotulo="local")
        if locais:
            termos = termos + locais
            print(f"   🔒 Glossário local: +{len(locais)} termos (fora do repositório)")

    return termos


def _ler_arquivo(caminho, rotulo="público"):
    """Lê um arquivo de glossário. Devolve lista de termos; vazia se algo falhar."""
    caminho = Path(caminho)

    if not caminho.exists():
        print(f"   ⚠️  Glossário não encontrado em: {caminho}")
        print(f"   ⚠️  Transcrição segue sem correção de termos.")
        return []

    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
    except json.JSONDecodeError as e:
        print(f"   ⚠️  Glossário {rotulo} com erro de formato: {e}")
        print(f"   ⚠️  Linha {e.lineno}, coluna {e.colno} de {caminho}")
        print(f"   ⚠️  Provável causa: vírgula sobrando ou faltando entre termos.")
        print(f"   ⚠️  Este arquivo foi ignorado.")
        return []
    except Exception as e:
        print(f"   ⚠️  Falha ao ler o glossário {rotulo} ({type(e).__name__}): {e}")
        return []

    termos = dados.get("termos", [])
    validos = []
    for i, t in enumerate(termos):
        if not isinstance(t, dict) or "de" not in t or "para" not in t:
            print(f"   ⚠️  Termo {i} ignorado (faltando 'de' ou 'para'): {t}")
            continue
        if not t["de"]:
            print(f"   ⚠️  Termo {i} ignorado ('de' vazio)")
            continue
        validos.append(t)

    if rotulo == "público":
        print(f"   📖 Glossário carregado: {len(validos)} termos")
    return validos


def compilar(termo):
    """
    Monta o regex de um termo.

    Limite de palavra por lookaround em vez de \\b: funciona igual para termo
    de uma palavra e para expressão com espaço ou hífen ('Connect Lab',
    'start-up'), e garante que 'FRJ' jamais case dentro de 'UFRJ'.
    """
    flags = 0 if termo.get("exato") else re.IGNORECASE
    padrao = r"(?<!\w)" + re.escape(termo["de"]) + r"(?!\w)"
    return re.compile(padrao, flags)


def aplicar_glossario(texto, termos):
    """
    Aplica os termos ao texto.

    Devolve (texto_corrigido, trocas), onde trocas é a lista de
    (de, para, quantidade) do que efetivamente mudou.
    """
    trocas = []

    for termo in termos:
        try:
            regex = compilar(termo)
        except re.error as e:
            print(f"   ⚠️  Termo inválido ignorado: {termo['de']!r} ({e})")
            continue

        texto, n = regex.subn(termo["para"], texto)
        if n:
            trocas.append((termo["de"], termo["para"], n))

    return texto, trocas


def escrever_log(destino, arquivo_alvo, trocas, termos_carregados):
    """Grava ao lado da transcrição o que foi trocado, para conferência."""
    with open(destino, "w", encoding="utf-8") as f:
        f.write("# Correção automática de termos\n\n")
        f.write(f"Arquivo: {arquivo_alvo.name}\n")
        f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Termos no glossário: {termos_carregados}\n")
        f.write(f"Termos aplicados: {len(trocas)}\n")
        f.write(f"Substituições totais: {sum(n for _, _, n in trocas)}\n\n")

        if not trocas:
            f.write("Nenhum termo do glossário apareceu nesta transcrição.\n")
        else:
            f.write("| Whisper escreveu | Virou | Vezes |\n")
            f.write("|---|---|---|\n")
            for de, para, n in sorted(trocas, key=lambda x: -x[2]):
                f.write(f"| {de} | {para} | {n} |\n")

        f.write("\n---\n\n")
        f.write("Erro que depende de contexto (palavra comum trocada por outra\n")
        f.write("palavra comum) não é tratado aqui. Para isso, rode a skill\n")
        f.write("/arrumar-transcricao sobre este arquivo.\n")


def corrigir_arquivo(caminho, caminho_glossario=None, gerar_log=True):
    """
    Corrige um arquivo de transcrição no lugar.

    Devolve a lista de trocas aplicadas.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        print(f"   ❌ Arquivo não encontrado: {caminho}")
        return []

    termos = carregar_glossario(caminho_glossario)
    if not termos:
        return []

    texto_original = caminho.read_text(encoding="utf-8")
    texto_corrigido, trocas = aplicar_glossario(texto_original, termos)

    total = sum(n for _, _, n in trocas)

    if trocas:
        caminho.write_text(texto_corrigido, encoding="utf-8")
        print(f"   ✏️  {total} correções em {len(trocas)} termos:")
        for de, para, n in sorted(trocas, key=lambda x: -x[2]):
            print(f"      {de} → {para} ({n}x)")
    else:
        print(f"   ✓  Nenhum termo do glossário apareceu nesta transcrição")

    if gerar_log:
        log = caminho.parent / f"{caminho.stem}_termos-corrigidos.md"
        escrever_log(log, caminho, trocas, len(termos))
        print(f"   📋 Log: {log.name}")

    return trocas


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("Erro: informe o arquivo de transcrição.\n")
        sys.exit(1)

    alvo = Path(sys.argv[1])
    glossario = sys.argv[2] if len(sys.argv) > 2 else None

    print("\n" + "=" * 80)
    print("CORREÇÃO DE TERMOS")
    print("=" * 80)
    print(f"Arquivo: {alvo}")
    print(f"Glossário: {glossario or GLOSSARIO_PADRAO}")
    print("=" * 80 + "\n")

    trocas = corrigir_arquivo(alvo, glossario)

    print("\n" + "=" * 80)
    print(f"✅ CONCLUÍDO — {sum(n for _, _, n in trocas)} substituições")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
