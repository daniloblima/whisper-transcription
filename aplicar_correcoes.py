#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aplicador único de correções de transcrição.

Existe por um motivo medido. Os cinco erros do corretor catalogados em
LICOES-APRENDIDAS.md foram cometidos editando o .md direto, sem backup, sem log
e sem verificação: fala apagada em três pontos, um país inventado, um nome
trocado por contaminação do vizinho. A auditoria só foi possível por acidente,
porque o método de substituição deixava espaço órfão onde mexia.

Daqui em diante nenhuma correção se aplica por edição livre. Toda troca se
declara num JSON, com motivo e origem, e passa por aqui. O que este módulo
garante, e que a edição livre não garantia:

  1. backup antes de qualquer escrita
  2. contagem esperada de ocorrências, declarada por quem corrige. Se a
     realidade não bater, a corrida inteira é recusada e nada é escrito.
     É o que pega regra larga demais e regra estreita demais.
  3. apagar texto exige tipo "remocao" com confirmação explícita de quem
     decidiu. Fala não some por acidente.
  4. separadores preservados na substituição de expressões com mais de uma
     palavra: carimbo de tempo e marcador de falante que ficam no meio são
     capturados e recolocados. É o padrao 7 do PADROES-DE-ERRO.md, que comeu
     34 carimbos em 16 arquivos.
  5. invariantes contados antes e depois. Carimbo ou marcador que suma sem
     justificativa aborta a corrida e o arquivo não é tocado.
  6. log estruturado com regra, arquivo, posição, carimbo mais próximo, texto
     antes e depois, motivo e origem.

Uso:
    python3 aplicar_correcoes.py correcoes.json            # aplica
    python3 aplicar_correcoes.py correcoes.json --dry-run  # só mostra

Formato do JSON em FORMATO-CORRECOES.md, ao lado deste arquivo.
"""
import argparse, json, re, sys, unicodedata
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------- estruturas

RE_CARIMBO = r"`\[\d+:\d\d:\d\d\]`"
RE_FALANTE = r"\*\*[A-Z][A-Z_0-9]*\*\*"
# O que pode aparecer entre duas palavras de uma mesma expressão falada:
# espaço, quebra de linha, marcador de falante e carimbo de tempo.
SEP = rf"(\s+(?:{RE_FALANTE}\s+)?(?:{RE_CARIMBO}\s*)?)"

ORIGENS = {"glossario", "dicionario", "contexto", "anexo", "externa", "forma", "usuario"}


class Recusa(Exception):
    """Erro que aborta a corrida inteira antes de escrever qualquer coisa."""


# ---------------------------------------------------------------- utilidades

def log(msg=""):
    print(msg, flush=True)


def contar_invariantes(texto):
    return {
        "carimbos": len(re.findall(RE_CARIMBO, texto)),
        "falantes": len(re.findall(RE_FALANTE, texto)),
        "linhas": texto.count("\n"),
    }


def carimbo_antes(texto, pos):
    """Último carimbo de tempo antes da posição. É o 'instante' do relatório."""
    achados = [m.group(0) for m in re.finditer(RE_CARIMBO, texto[:pos])]
    return achados[-1].strip("`[]") if achados else "?"


def linha_de(texto, pos):
    return texto.count("\n", 0, pos) + 1


def cicatrizes(texto):
    """Assinaturas de substituição malfeita: o que denunciou a rodada de 01/09."""
    fora = []
    for m in re.finditer(r"\S  +\S", texto):
        fora.append(("espaço duplo", linha_de(texto, m.start()), m.group(0).strip()))
    for m in re.finditer(r"\s+[,.;:!?]", texto):
        if "\n" in m.group(0):
            continue                      # quebra de linha antes de pontuação é do formato
        fora.append(("espaço antes de pontuação", linha_de(texto, m.start()), m.group(0)))
    return fora


def desacentua(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------- o motor

def construir_padrao(de, exato=True):
    """Padrão que atravessa carimbo e marcador de falante entre as palavras."""
    palavras = de.split()
    if not palavras:
        raise Recusa("correção com campo 'de' vazio")
    corpo = SEP.join(re.escape(p) for p in palavras)
    # Lookaround só onde faz sentido: 'de' pode começar ou terminar em pontuação.
    ini = r"(?<!\w)" if re.match(r"\w", palavras[0], re.UNICODE) else ""
    fim = r"(?!\w)" if re.search(r"\w$", palavras[-1], re.UNICODE) else ""
    flags = re.UNICODE | (0 if exato else re.IGNORECASE)
    return re.compile(ini + corpo + fim, flags)


def montar_substituicao(separadores, para):
    """Recoloca os separadores entre as palavras novas.

    Quando 'para' tem menos palavras que 'de', sobra separador. Ele vai para o
    fim, e é assim que o carimbo de tempo que estava no meio sobrevive. Quando
    tem mais, os que faltam viram espaço simples.
    """
    novas = para.split()
    if not novas:
        return ""
    saida = []
    for i, palavra in enumerate(novas):
        saida.append(palavra)
        if i < len(novas) - 1:
            saida.append(separadores[i] if i < len(separadores) else " ")
    # Só sobrevive o separador que carrega carimbo ou marcador de falante: é ele
    # que é invariante. Separador que é só espaço em branco vira a cicatriz que
    # este módulo existe para impedir — foi assim que nasceram as 19 de 01/09.
    for s in separadores[max(len(novas) - 1, 0):]:
        if re.search(RE_CARIMBO, s) or re.search(RE_FALANTE, s):
            saida.append(s)
    return "".join(saida)


def aplicar_uma(texto, c, arquivo):
    """Aplica uma correção declarada. Devolve (texto novo, eventos)."""
    padrao = construir_padrao(c["de"], c.get("exato", True))
    eventos = []

    def troca(m):
        seps = [g for g in m.groups() if g is not None]
        novo = montar_substituicao(seps, c["para"])
        eventos.append({
            "arquivo": arquivo,
            "de": m.group(0),
            "para": novo,
            "linha": linha_de(texto, m.start()),
            "carimbo": carimbo_antes(texto, m.start()),
            "atravessa_carimbo": any(re.search(RE_CARIMBO, s) for s in seps),
            "atravessa_falante": any(re.search(RE_FALANTE, s) for s in seps),
            "motivo": c["motivo"],
            "origem": c["origem"],
            "tipo": c.get("tipo", "troca"),
        })
        return novo

    return padrao.sub(troca, texto), eventos


# ---------------------------------------------------------------- validação

def validar_declaracao(decl):
    if "correcoes" not in decl or not decl["correcoes"]:
        raise Recusa("declaração sem lista 'correcoes'")
    for i, c in enumerate(decl["correcoes"], 1):
        rot = f"correção {i} ({c.get('de', '?')!r})"
        for campo in ("de", "para", "motivo", "origem", "ocorrencias"):
            if campo not in c:
                raise Recusa(f"{rot}: falta o campo obrigatório '{campo}'")
        if not str(c["motivo"]).strip():
            raise Recusa(f"{rot}: 'motivo' vazio. Correção sem porquê não se aplica")
        if c["origem"] not in ORIGENS:
            raise Recusa(f"{rot}: origem {c['origem']!r} inválida. Use uma de {sorted(ORIGENS)}")
        encurta = len(str(c["para"]).split()) < len(str(c["de"]).split())
        if not str(c["para"]).strip() or encurta:
            if c.get("tipo") != "remocao":
                raise Recusa(
                    f"{rot}: a troca apaga fala — {len(str(c['de']).split())} palavra(s) "
                    f"viram {len(str(c['para']).split())}.\n"
                    f"    Hesitação e repetição são fala e ficam. Se o dado está errado, "
                    f"isso é nota ao lado, não edição.\n"
                    f"    Foi assim que 'S11D, ou SD11' virou 'S11D' em 01/09.\n"
                    f"    Para apagar mesmo assim: \"tipo\": \"remocao\" e 'confirmado_por'.")
            if not str(c.get("confirmado_por", "")).strip():
                raise Recusa(f"{rot}: remoção exige 'confirmado_por' com quem decidiu")


def resolver_alvos(decl, raiz):
    base = Path(decl.get("base", raiz)).expanduser()
    alvos = []
    for padrao in decl.get("alvos", []):
        p = Path(padrao).expanduser()
        if p.is_absolute():
            alvos.extend(sorted(p.parent.glob(p.name)) if any(ch in p.name for ch in "*?[") else [p])
        else:
            alvos.extend(sorted(base.glob(padrao)))
    alvos = [a for a in alvos if a.is_file()]
    if not alvos:
        raise Recusa(f"nenhum arquivo encontrado a partir de {base} e {decl.get('alvos')}")
    return alvos


# ---------------------------------------------------------------- relatórios

def escrever_relatorio(destino, decl, eventos, invariantes, avisos, aplicado):
    carimbo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    j = {
        "quando": carimbo,
        "descricao": decl.get("descricao", ""),
        "aplicado": aplicado,
        "total_trocas": len(eventos),
        "invariantes": invariantes,
        "avisos": avisos,
        "eventos": eventos,
    }
    (destino / "log.json").write_text(json.dumps(j, ensure_ascii=False, indent=2))

    md = [f"# Correções aplicadas — {carimbo}\n\n"]
    if decl.get("descricao"):
        md.append(decl["descricao"] + "\n\n")
    md.append(f"{len(eventos)} trocas em {len({e['arquivo'] for e in eventos})} arquivo(s).\n\n")
    if not aplicado:
        md.append("**Simulação (`--dry-run`). Nada foi escrito.**\n\n")
    md.append("## Invariantes\n\n| Arquivo | Carimbos | Marcadores de falante |\n|---|---|---|\n")
    for arq, inv in invariantes.items():
        c, f = inv["antes"]["carimbos"], inv["antes"]["falantes"]
        c2, f2 = inv["depois"]["carimbos"], inv["depois"]["falantes"]
        sc = f"{c}" if c == c2 else f"{c} → {c2} ⚠"
        sf = f"{f}" if f == f2 else f"{f} → {f2} ⚠"
        md.append(f"| {arq} | {sc} | {sf} |\n")
    if avisos:
        md.append("\n## Avisos\n\n")
        md += [f"- {a}\n" for a in avisos]
    md.append("\n## Trocas\n\n")
    for e in sorted(eventos, key=lambda x: (x["arquivo"], x["linha"])):
        marca = " (atravessa carimbo)" if e["atravessa_carimbo"] else ""
        md.append(f"\n**{e['arquivo']}** `[{e['carimbo']}]` linha {e['linha']}{marca}\n\n")
        md.append(f"- antes: `{e['de']}`\n- depois: `{e['para']}`\n")
        md.append(f"- motivo: {e['motivo']} _(origem: {e['origem']})_\n")
    (destino / "correcoes.md").write_text("".join(md))


# ---------------------------------------------------------------- orquestração

def rodar(caminho_decl, dry_run=False):
    decl = json.loads(Path(caminho_decl).read_text())
    validar_declaracao(decl)
    alvos = resolver_alvos(decl, Path(caminho_decl).parent)

    log(f"declaração: {caminho_decl}")
    log(f"{len(decl['correcoes'])} correções declaradas, {len(alvos)} arquivo(s) alvo\n")

    originais = {a: a.read_text() for a in alvos}
    novos = dict(originais)
    eventos, avisos = [], []

    # Passo 1: aplicar em memória e conferir a contagem declarada.
    for i, c in enumerate(decl["correcoes"], 1):
        restrito = c.get("arquivos")
        total = 0
        evs_desta = []
        for a in alvos:
            if restrito and a.name not in restrito:
                continue
            texto, evs = aplicar_uma(novos[a], c, a.name)
            if evs:
                novos[a] = texto
                evs_desta += evs
                total += len(evs)
        esperado = int(c["ocorrencias"])
        estado = "ok" if total == esperado else "DIVERGE"
        log(f"  [{i:02d}] {c['de']!r} -> {c['para']!r}: {total} ocorrência(s), "
            f"esperado {esperado} — {estado}")
        if total != esperado:
            raise Recusa(
                f"correção {i} ({c['de']!r}) casou {total} vez(es) e a declaração dizia "
                f"{esperado}. Nada foi escrito.\n"
                f"    Se casou menos, a regra é estreita demais ou o texto já mudou.\n"
                f"    Se casou mais, a regra é larga demais e pegaria texto que não devia."
            )
        eventos += evs_desta

    # Passo 2: invariantes. Carimbo ou marcador que suma aborta tudo.
    invariantes = {}
    for a in alvos:
        antes, depois = contar_invariantes(originais[a]), contar_invariantes(novos[a])
        invariantes[a.name] = {"antes": antes, "depois": depois}
        for chave in ("carimbos", "falantes"):
            if antes[chave] != depois[chave]:
                raise Recusa(
                    f"{a.name}: {chave} passou de {antes[chave]} para {depois[chave]}. "
                    f"Correção não pode mexer nisso. Nada foi escrito."
                )

    # Passo 3: cicatriz introduzida pela própria aplicação.
    for a in alvos:
        novas = set(cicatrizes(novos[a])) - set(cicatrizes(originais[a]))
        for tipo, linha, trecho in sorted(novas):
            avisos.append(f"{a.name} linha {linha}: {tipo} introduzido por esta corrida — {trecho!r}")

    tocados = [a for a in alvos if novos[a] != originais[a]]
    log(f"\n{len(eventos)} trocas em {len(tocados)} arquivo(s). "
        f"Invariantes conferidos: nenhum carimbo ou marcador perdido.")
    for av in avisos:
        log(f"  aviso: {av}")

    # Passo 4: backup e escrita.
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destino = (tocados[0].parent if tocados else alvos[0].parent) / "_correcoes" / stamp
    destino.mkdir(parents=True, exist_ok=True)

    if dry_run:
        log(f"\n--dry-run: nada escrito. Relatório em {destino}")
    else:
        for a in tocados:
            (destino / f"{a.stem}.bak.md").write_text(originais[a])
        for a in tocados:
            a.write_text(novos[a])
        log(f"\naplicado. Backup e log em {destino}")

    escrever_relatorio(destino, decl, eventos, invariantes, avisos, aplicado=not dry_run)
    return destino


def main():
    p = argparse.ArgumentParser(description="Aplica correções declaradas em transcrições.")
    p.add_argument("declaracao", help="JSON com as correções")
    p.add_argument("--dry-run", action="store_true", help="mostra sem escrever")
    args = p.parse_args()
    try:
        rodar(args.declaracao, args.dry_run)
    except Recusa as e:
        log(f"\nRECUSADO: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
