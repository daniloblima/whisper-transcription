#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Varreduras de suspeita sobre transcrições. Aponta, nunca corrige.

O erro que importa numa transcrição técnica é gramaticalmente correto e passa
por revisão inteira sem nada acusar: "fez o ato" onde se lê "fez o Atlas",
"ICI" onde a mesma aula diz ECI seis vezes, "os continentes mais iguais do
mundo" onde o parágrafo argumenta o contrário. Ler tudo é a única alternativa,
e não escala.

Este módulo roda em segundos, sem contexto nenhum, e devolve uma fila de
pontos para leitura humana, no formato do "00 A RESOLVER" — arquivo, instante
e o trecho. Ele não decide nada, e é de propósito: distinguir "Serra Leoa da
vida" de erro de transcrição exige conhecer português falado e o assunto.

As sete varreduras, e de onde cada uma veio:

  INVERSAO    o prefixo "des" comido e "sofisticação" virando "simplificação".
              Padrões 1 e 2 do PADROES-DE-ERRO.md. Inverte a tese e não quebra
              a gramática.
  ANO_PCT     "%" colado em ano. Padrão 3. Nunca corrigir por script.
  ALUCINACAO  crédito de legendagem e afins, que o Whisper reproduz em trecho
              de silêncio. "Legenda por Sônia Ruberti" fechava duas aulas e
              não é fala. Peso maior perto do fim do arquivo.
  NOMES       capitalizadas de cauda ao lado das formas parecidas frequentes.
              Padrão 4: nome deformado aparece com duas ou três ocorrências
              ao lado da forma correta.
  COERENCIA   sigla ou nome grafado de dois jeitos no mesmo arquivo. Teria
              achado sozinho o ECI contra ICI e o Eric contra Erik Reinert.
  CICATRIZ    espaço duplo e espaço antes de pontuação, rastro de substituição
              malfeita. Foram 19 no acervo, três escondendo fala apagada.
  CONCORDANCIA artigo que não concorda com o substantivo, rastro de correção
              pela metade ("é a aparelho de raio-x"). Só roda na vizinhança de
              trocas registradas em log, porque varredura solta em português
              gera ruído demais.

Uso:
    python3 varrer_suspeitas.py <arquivo ou pasta> [--saida relatorio.md]
    python3 varrer_suspeitas.py <pasta> --log _correcoes/<data>/log.json
"""
import argparse, difflib, json, re, sys, unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from aplicar_correcoes import RE_CARIMBO, carimbo_antes, linha_de, cicatrizes

# ---------------------------------------------------------------- padrões

INVERSAO = [
    (r"\bmais\s+igua(?:l|is)\b", "o prefixo 'des' pode ter sido comido: 'mais desigual'"),
    (r"\bmenos\s+desigua(?:l|is)\b", "conferir se não é 'mais desigual'"),
    (r"\bmais\s+iguais\s+do\s+mundo\b", "trecho onde o 'des' sumiu quatro vezes no acervo de 2026"),
    (r"\bsimplifica[çc][ãa]o\b", "conferir se não é 'sofisticação', que inverte a tese"),
    (r"\bsimplificad[oa]s?\b", "conferir se não é 'sofisticado'"),
]
CONTEXTO_SIMPLIFICACAO = re.compile(r"produtiv|industrial|complexidade|estrutura", re.I)

ANO_PCT = r"\b(1[5-9]\d\d|20[0-5]\d)\s*%"

ALUCINACAO = [
    r"legenda[s]?\s+(?:por|pela|feita)", r"legendado\s+por", r"revis[ãa]o\s+por",
    r"inscreva-se", r"se\s+inscreva\s+no\s+canal", r"obrigado\s+por\s+assistir",
    r"at[ée]\s+o\s+pr[óo]ximo\s+v[íi]deo", r"amara\.org", r"deixe\s+seu\s+like",
]

# Artigos e as terminações que costumam denunciar troca de palavra pela metade.
ARTIGOS_M = r"\b(?:o|os|um|uns|ao|aos|do|dos|no|nos|pelo|pelos|este|esse|aquele)\b"
ARTIGOS_F = r"\b(?:a|as|uma|umas|à|às|da|das|na|nas|pela|pelas|esta|essa|aquela)\b"
# Substantivos comuns que terminam em vogal "errada" e não são discordância.
EXCECOES = {
    "problema", "dia", "mapa", "sistema", "tema", "programa", "clima", "cinema",
    "planeta", "poeta", "idioma", "drama", "esquema", "diagrama", "dilema",
    "paradigma", "carisma", "trauma", "enigma", "fantasma", "cometa", "profeta",
    "foto", "moto", "tribo", "libido", "mão", "razão", "questão",
}

CAPITALIZADA = re.compile(r"\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]{2,})\b")
MINUSCULA = re.compile(r"\b([a-záéíóúâêôãõç]{3,})\b")


def lexico_minusculo(textos, minimo=3):
    """Palavras que aparecem em minúscula no acervo.

    O maior ruído da varredura de nomes vem de palavra comum capitalizada por
    estar no começo de frase: 'Nessas', 'Veja', 'Quatro', 'Muitos'. Se a mesma
    palavra aparece em minúscula várias vezes, ela não é nome próprio, e isso
    se mede sem lista de exceções e sem dicionário externo.
    """
    c = Counter()
    for texto in textos.values():
        c.update(desacentua(w) for w in MINUSCULA.findall(texto))
    return {w for w, n in c.items() if n >= minimo}
SIGLA = re.compile(r"\b([A-Z]{2,6})\b")
PALAVRAS_COMUNS = {
    "Brasil", "Estado", "Estados", "Unidos", "Europa", "China", "Japão", "Coreia",
    "América", "Latina", "Ásia", "África", "Nova", "São", "Paulo", "Rio", "Janeiro",
    "Norte", "Sul", "Leste", "Oeste", "Mundial", "Banco", "Guerra", "Federal",
    "Então", "Isso", "Essa", "Esse", "Aqui", "Agora", "Bom", "Vamos", "Olha",
    "Quando", "Porque", "Depois", "Antes", "Mas", "Como", "Aí", "Você", "Ele",
}


def dist_um(a, b):
    """Uma letra de diferença: troca, inserção ou remoção.

    Existe porque similaridade proporcional não serve para sigla curta. 'ECI' e
    'ICI' diferem por uma letra e a razão dá 0,67, abaixo de qualquer corte
    razoável para nome. E era exatamente esse o caso que a varredura precisava
    achar: seis ECI e um ICI na mesma aula.
    """
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(1 for x, y in zip(a, b) if x != y) == 1
    longa, curta = (a, b) if len(a) > len(b) else (b, a)
    for i in range(len(longa)):
        if longa[:i] + longa[i + 1:] == curta:
            return True
    return False


def plural_um_do_outro(a, b):
    """'Fusca' e 'Fuscas' não são duas grafias, são singular e plural."""
    x, y = sorted((desacentua(a), desacentua(b)), key=len)
    return y in (x + "s", x + "es")


ROMANO = re.compile(r"^[IVXLCDM]+$")


def desacentua(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


def mascarar_editorial(texto):
    """Apaga da varredura o que não é fala, preservando as posições.

    Cabeçalho do arquivo e blocos de citação são texto escrito por quem
    revisou — as NOTA DE VERIFICAÇÃO, o título, o módulo. Varrer isso produz
    achado sobre a própria nota, como o 'Canaã dos Carajás' que uma delas cita.
    Troca por espaço em vez de remover, para linha e carimbo continuarem certos.
    """
    linhas = texto.split("\n")
    primeiro = next((i for i, l in enumerate(linhas) if re.search(RE_CARIMBO, l)), 0)
    for i, l in enumerate(linhas):
        if i < primeiro or l.lstrip().startswith(">"):
            linhas[i] = " " * len(l)
    return "\n".join(linhas)


def trecho(texto, pos, raio=90):
    ini, fim = max(0, pos - raio), min(len(texto), pos + raio)
    return re.sub(r"\s+", " ", texto[ini:fim]).strip()


def achado(arquivo, texto, pos, tipo, nota, extra=""):
    return {
        "tipo": tipo, "arquivo": arquivo,
        "carimbo": carimbo_antes(texto, pos), "linha": linha_de(texto, pos),
        "trecho": trecho(texto, pos), "nota": nota, "extra": extra,
    }


# ---------------------------------------------------------------- varreduras

def varrer_inversao(arquivo, texto):
    out = []
    for padrao, nota in INVERSAO:
        for m in re.finditer(padrao, texto, re.I):
            if "simplifica" in m.group(0).lower():
                volta = texto[max(0, m.start() - 250): m.end() + 250]
                if not CONTEXTO_SIMPLIFICACAO.search(volta):
                    continue          # 'simplificação' longe do assunto é uso legítimo
            out.append(achado(arquivo, texto, m.start(), "INVERSAO", nota))
    return out


def varrer_ano_pct(arquivo, texto):
    return [achado(arquivo, texto, m.start(), "ANO_PCT",
                   "'%' colado em ano; conferir se é percentual ou data")
            for m in re.finditer(ANO_PCT, texto)]


def varrer_alucinacao(arquivo, texto):
    out = []
    fim_do_arquivo = len(texto) * 0.9
    for padrao in ALUCINACAO:
        for m in re.finditer(padrao, texto, re.I):
            perto_do_fim = m.start() >= fim_do_arquivo
            nota = ("padrão de legendagem, e está nos últimos 10% do arquivo — quase certo que não é fala"
                    if perto_do_fim else
                    "padrão de legendagem; conferir se é fala de verdade")
            out.append(achado(arquivo, texto, m.start(), "ALUCINACAO", nota,
                              extra="fim do arquivo" if perto_do_fim else ""))
    return out


def varrer_cicatriz(arquivo, texto):
    out = []
    for tipo, linha, tr in cicatrizes(texto):
        pos = sum(len(l) + 1 for l in texto.splitlines()[:linha - 1])
        out.append(achado(arquivo, texto, pos, "CICATRIZ",
                          f"{tipo}: rastro de substituição malfeita", extra=tr))
    return out


def varrer_coerencia(arquivo, texto, lexico):
    """Sigla ou nome grafado de dois jeitos no mesmo arquivo.

    Só reporta quando uma forma domina e a outra é rara: foi assim que o ECI,
    com seis ocorrências, denunciou o ICI com uma. Duas formas igualmente
    frequentes costumam ser duas coisas diferentes, não erro.
    """
    out = []
    familias = [
        ("sigla", Counter(SIGLA.findall(texto))),
        ("nome", Counter(n for n in CAPITALIZADA.findall(texto)
                         if n not in PALAVRAS_COMUNS and desacentua(n) not in lexico)),
    ]
    for rotulo, contagem in familias:
        itens = list(contagem.items())
        for forte, nf in sorted(itens, key=lambda x: -x[1]):
            if nf < 3:
                continue
            for fraca, nr in itens:
                if fraca == forte or nr > 2 or abs(len(fraca) - len(forte)) > 2:
                    continue
                if desacentua(fraca) == desacentua(forte):
                    continue
                if plural_um_do_outro(forte, fraca):
                    continue
                if ROMANO.match(forte) and ROMANO.match(fraca):
                    continue          # século XIX contra século XX não é erro
                curtas = max(len(forte), len(fraca)) <= 4
                perto = (dist_um(desacentua(forte), desacentua(fraca)) if curtas else
                         difflib.SequenceMatcher(None, desacentua(forte), desacentua(fraca)).ratio() >= 0.8)
                if not perto:
                    continue
                pos = texto.find(fraca)
                out.append(achado(arquivo, texto, pos, "COERENCIA",
                                  f"{rotulo} grafada de dois jeitos no mesmo arquivo: "
                                  f"'{forte}' ({nf}x) e '{fraca}' ({nr}x)",
                                  extra=f"{forte} | {fraca}"))
    return out


def varrer_nomes(arquivos_texto):
    """Capitalizadas de cauda ao lado das formas parecidas frequentes, no acervo."""
    freq = Counter()
    onde = defaultdict(list)
    lexico = lexico_minusculo(arquivos_texto)
    for arq, texto in arquivos_texto.items():
        for m in CAPITALIZADA.finditer(texto):
            nome = m.group(1)
            if nome in PALAVRAS_COMUNS or desacentua(nome) in lexico:
                continue
            freq[nome] += 1
            if len(onde[nome]) < 3:
                onde[nome].append((arq, carimbo_antes(texto, m.start())))

    frequentes = {n: c for n, c in freq.items() if c >= 5}
    out = []
    for nome, c in sorted(freq.items(), key=lambda x: x[1]):
        if c > 3:
            continue
        for forte, cf in frequentes.items():
            if nome == forte or abs(len(nome) - len(forte)) > 3:
                continue
            if plural_um_do_outro(nome, forte):
                continue
            r = difflib.SequenceMatcher(None, desacentua(nome), desacentua(forte)).ratio()
            if r >= 0.75:
                arq, car = onde[nome][0]
                out.append({
                    "tipo": "NOMES", "arquivo": arq, "carimbo": car, "linha": 0,
                    "trecho": f"'{nome}' ({c}x)",
                    "nota": f"parecido com '{forte}' ({cf}x), semelhança {r:.2f}",
                    "extra": ", ".join(f"{a} [{t}]" for a, t in onde[nome]),
                    "confianca": r,
                })
                break
    return out


def varrer_concordancia(arquivo, texto, posicoes):
    """Artigo que não concorda, na vizinhança de trocas já aplicadas."""
    out = []
    for pos in posicoes:
        janela = texto[max(0, pos - 120): pos + 120]
        base = max(0, pos - 120)
        for padrao, gen in ((ARTIGOS_M + r"\s+(\w+a)\b", "m"),
                            (ARTIGOS_F + r"\s+(\w+o)\b", "f")):
            for m in re.finditer(padrao, janela, re.I):
                palavra = m.group(1).lower()
                if palavra in EXCECOES or len(palavra) < 4:
                    continue
                out.append(achado(arquivo, texto, base + m.start(), "CONCORDANCIA",
                                  "artigo não concorda com o substantivo, perto de uma troca aplicada; "
                                  "rastro clássico de correção pela metade",
                                  extra=m.group(0)))
    return out


def deduplicar(achados):
    vistos, out = set(), []
    for a in achados:
        chave = (a["tipo"], a["arquivo"], a["carimbo"], a["extra"], a["nota"][:60])
        if chave in vistos:
            continue
        vistos.add(chave); out.append(a)
    return out


# ---------------------------------------------------------------- relatório

ORDEM = ["INVERSAO", "ALUCINACAO", "COERENCIA", "NOMES", "ANO_PCT", "CICATRIZ", "CONCORDANCIA"]
CABECA = {
    "INVERSAO": ("Inversão de sentido", "Os erros que continuam gramaticais e fazem o texto dizer o contrário. Ler o parágrafo em volta antes de decidir."),
    "ALUCINACAO": ("Alucinação do motor", "Crédito de legendagem e afins, que o Whisper reproduz em trecho de silêncio. Nunca apagar sem conferir."),
    "COERENCIA": ("Duas grafias no mesmo arquivo", "Sigla ou nome escrito de dois jeitos. O desempate costuma estar dentro da própria unidade."),
    "NOMES": ("Nomes próprios candidatos", "Capitalizadas raras ao lado de formas parecidas frequentes. Nome deformado aparece na cauda."),
    "ANO_PCT": ("'%' colado em ano", "Padrão claro e correção arriscada, porque o texto mistura anos e percentuais de verdade."),
    "CICATRIZ": ("Cicatriz de substituição", "Espaço órfão onde alguém mexeu. Foi o que revelou três falas apagadas em 01/09/2026."),
    "CONCORDANCIA": ("Correção pela metade", "Artigo que não concorda com o substantivo, perto de troca aplicada."),
}


def escrever_relatorio(achados, destino, quantos_arquivos):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    por_tipo = defaultdict(list)
    for a in achados:
        por_tipo[a["tipo"]].append(a)

    md = [f"# A resolver na revisão\n\n",
          f"Gerado em {agora} por `varrer_suspeitas.py`, sobre {quantos_arquivos} arquivo(s).\n\n",
          "Cada item traz o arquivo e o instante, para ouvir o trecho e decidir. ",
          "**Nada aqui foi corrigido.** A varredura aponta candidatos; quem decide é quem conhece o assunto ",
          "e sabe distinguir erro de transcrição de português falado.\n\n"]

    md.append(f"## TL;DR\n\n{len(achados)} pontos, em {len(por_tipo)} grupos.\n\n")
    for t in ORDEM:
        if por_tipo[t]:
            md.append(f"- **{CABECA[t][0]}**: {len(por_tipo[t])}\n")
    md.append("\n---\n")

    for t in ORDEM:
        itens = por_tipo[t]
        if not itens:
            continue
        titulo, explica = CABECA[t]
        md.append(f"\n## {titulo} ({len(itens)})\n\n{explica}\n\n")
        md.append("| Arquivo | Instante | Trecho | O que conferir |\n|---|---|---|---|\n")
        chave = ((lambda x: -x.get("confianca", 0)) if t == "NOMES"
                 else (lambda x: (x["arquivo"], x["carimbo"])))
        for a in sorted(itens, key=chave):
            tr = a["trecho"].replace("|", "\\|")
            nota = a["nota"].replace("|", "\\|")
            md.append(f"| {a['arquivo'][:34]} | `{a['carimbo']}` | {tr} | {nota} |\n")

    Path(destino).write_text("".join(md))


# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description="Varreduras de suspeita sobre transcrições.")
    p.add_argument("alvo", help="arquivo .md ou pasta com .md")
    p.add_argument("--saida", default=None, help="arquivo do relatório")
    p.add_argument("--log", default=None, help="log.json de uma corrida de correções")
    args = p.parse_args()

    alvo = Path(args.alvo).expanduser()
    arquivos = sorted(alvo.glob("*.md")) if alvo.is_dir() else [alvo]
    arquivos = [a for a in arquivos if not a.name.startswith("00 A RESOLVER")]
    if not arquivos:
        sys.exit(f"nenhum .md em {alvo}")

    textos = {a.name: mascarar_editorial(a.read_text()) for a in arquivos}
    lexico = lexico_minusculo(textos)
    achados = []
    for nome, texto in textos.items():
        achados += varrer_inversao(nome, texto)
        achados += varrer_ano_pct(nome, texto)
        achados += varrer_alucinacao(nome, texto)
        achados += varrer_cicatriz(nome, texto)
        achados += varrer_coerencia(nome, texto, lexico)
    achados += varrer_nomes(textos)
    achados = deduplicar(achados)

    if args.log:
        log = json.loads(Path(args.log).read_text())
        porarq = defaultdict(list)
        for e in log["eventos"]:
            porarq[e["arquivo"]].append(e)
        for nome, evs in porarq.items():
            if nome not in textos:
                continue
            posicoes = [textos[nome].find(e["para"].split("\n")[0]) for e in evs]
            achados += varrer_concordancia(nome, textos[nome], [p for p in posicoes if p > 0])

    saida = Path(args.saida) if args.saida else (
        (alvo if alvo.is_dir() else alvo.parent) / "00 A RESOLVER na revisão.md")
    escrever_relatorio(achados, saida, len(arquivos))

    contagem = Counter(a["tipo"] for a in achados)
    print(f"{len(arquivos)} arquivo(s) varridos, {len(achados)} pontos:")
    for t in ORDEM:
        if contagem[t]:
            print(f"  {t:13s} {contagem[t]:4d}   {CABECA[t][0]}")
    print(f"\nrelatório: {saida}")


if __name__ == "__main__":
    main()
