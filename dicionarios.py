#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Catálogo dos dicionários por tema.

O `glossario.json` da raiz é o dicionário geral: só entra ali erro cujo acerto é
sempre o mesmo, independentemente do assunto. "Minquedinho" vira LinkedIn em
qualquer áudio sobre qualquer coisa.

O que depende do assunto não tinha casa. `Levi → Levy` vale em economia
brasileira e estraga qualquer outro áudio, então ficou de fora e uma ocorrência
escapou. É esse o buraco que os dicionários por tema tapam.

Cada tema é uma pasta em `dicionarios/`, com dois arquivos:

    dicionarios/<tema>/dicionario.md    o porquê de cada decisão, com fonte
    dicionarios/<tema>/glossario.json   as substituições determinísticas

Um nível só, sem subtema. Se um tema crescer demais, ele se divide em dois no
mesmo nível e o áudio carrega os dois — composição em vez de hierarquia, o que
evita a pergunta que a árvore obriga a responder toda vez: onde mora o termo que
serve aos dois ramos.

A pasta está no `.gitignore`, porque o dicionário é do usuário e o repositório é
público. Só `dicionarios/exemplo/` é versionado, e serve de formato.

Uso:
    python3 dicionarios.py --listar
    python3 dicionarios.py --sugerir "aula sobre política industrial e câmbio"
"""
import argparse, json, re, unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PASTA = RAIZ / "dicionarios"

STOPWORDS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "ou", "em", "no", "na",
    "nos", "nas", "um", "uma", "uns", "umas", "para", "por", "com", "sem", "sobre",
    "que", "se", "ao", "aos", "à", "às", "pelo", "pela", "este", "esta", "esse", "essa",
    "audio", "video", "aula", "reuniao", "conversa", "gravacao", "transcricao", "fala",
}


def desacentua(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")


def palavras(texto):
    return {p for p in re.findall(r"[a-zà-ÿ]{3,}", desacentua(texto)) if p not in STOPWORDS}


def ler_cabecalho(caminho):
    """Lê só o bloco do topo do dicionário, no formato do frontmatter de skill.

    Custa nada e é o que permite propor sem abrir o arquivo inteiro, que pode
    ter centenas de termos.
    """
    dados, dentro = {}, False
    with caminho.open() as f:
        for linha in f:
            linha = linha.rstrip("\n")
            if linha.strip() == "---":
                if dentro:
                    break
                dentro = True
                continue
            if dentro and ":" in linha:
                chave, valor = linha.split(":", 1)
                dados[chave.strip()] = valor.strip()
    return dados


def catalogo(pasta=None):
    """Todos os dicionários disponíveis, com cabeçalho e caminhos."""
    pasta = Path(pasta) if pasta else PASTA
    if not pasta.exists():
        return []
    out = []
    for dir_tema in sorted(p for p in pasta.iterdir() if p.is_dir()):
        md = dir_tema / "dicionario.md"
        if not md.exists():
            continue
        cab = ler_cabecalho(md)
        out.append({
            "tema": cab.get("tema", dir_tema.name),
            "descricao": cab.get("descricao", ""),
            "quando_usar": cab.get("quando_usar", ""),
            "pasta": dir_tema,
            "dicionario": md,
            "glossario": dir_tema / "glossario.json",
            "termos": contar_termos(dir_tema / "glossario.json"),
        })
    return out


def contar_termos(caminho):
    try:
        return len(json.loads(caminho.read_text()).get("termos", []))
    except Exception:
        return 0


def sugerir(contexto, pasta=None):
    """Dicionários que combinam com o contexto declarado, do mais para o menos.

    Casamento por palavra em comum, de propósito simples: quem decide é o dono
    do áudio, e a lista existe para ele marcar, não para a ferramenta escolher.
    """
    alvo = palavras(contexto or "")
    if not alvo:
        return []
    saida = []
    for d in catalogo(pasta):
        campo = " ".join((d["tema"], d["descricao"], d["quando_usar"]))
        comuns = alvo & palavras(campo)
        if comuns:
            saida.append({**d, "pontos": len(comuns), "porque": sorted(comuns)})
    return sorted(saida, key=lambda d: -d["pontos"])


def glossarios_de(temas, pasta=None):
    """Caminhos dos glossários dos temas pedidos. Tema inexistente é avisado."""
    disponiveis = {d["tema"]: d for d in catalogo(pasta)}
    caminhos, faltando = [], []
    for t in temas or []:
        d = disponiveis.get(t)
        if d and d["glossario"].exists():
            caminhos.append(d["glossario"])
        else:
            faltando.append(t)
    return caminhos, faltando


def main():
    p = argparse.ArgumentParser(description="Catálogo dos dicionários por tema.")
    p.add_argument("--listar", action="store_true", help="mostra os dicionários disponíveis")
    p.add_argument("--sugerir", metavar="CONTEXTO", help="propõe dicionários para um contexto")
    args = p.parse_args()

    if args.sugerir:
        achados = sugerir(args.sugerir)
        if not achados:
            print("Nenhum dicionário combina com esse contexto. "
                  "A transcrição usa só o glossário geral.")
            return
        print(f"Dicionários que combinam com {args.sugerir!r}:\n")
        for d in achados:
            print(f"  {d['tema']:20s} {d['termos']:4d} termos   "
                  f"(bate em: {', '.join(d['porque'])})")
            if d["descricao"]:
                print(f"  {'':20s} {d['descricao']}")
        print(f"\nPara usar: --tema {' --tema '.join(d['tema'] for d in achados)}")
        return

    cat = catalogo()
    if not cat:
        print(f"Nenhum dicionário em {PASTA}. "
              f"Copie `dicionarios/exemplo/` para começar um.")
        return
    print(f"{len(cat)} dicionário(s) em {PASTA}:\n")
    for d in cat:
        print(f"  {d['tema']:20s} {d['termos']:4d} termos")
        if d["descricao"]:
            print(f"  {'':20s} {d['descricao']}")


if __name__ == "__main__":
    main()
