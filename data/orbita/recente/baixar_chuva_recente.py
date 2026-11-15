#!/usr/bin/env python3
# Gerado com IA (Claude). Teste de 2026-11-15 para o motor do Órbita Rural (NASA Space Apps 2026).
"""Baixa a chuva diária recente do satélite (GPM IMERG, da NASA) num ponto, sem login, pelo NASA GIBS.

De onde vem: a camada diária IMERG_Precipitation_Rate do GIBS (o serviço de imagens da NASA, o mesmo do Worldview).
O GIBS só entrega imagem (PNG), mas a imagem usa uma paleta fixa e a NASA publica a tabela "cor -> faixa de mm/hora"
(https://gibs.earthdata.nasa.gov/colormaps/v1.3/GPM_Precipitation_Rate.xml). Este programa baixa o ladrilho do dia
onde o ponto cai, lê a cor do ponto e traduz pela tabela.

A conta: chuva do dia (mm) = meio da faixa (mm/hora, média geométrica dos dois limites) x 24.

RESSALVAS (ler antes de usar):
- É valor lido de cor, em faixas: cada faixa tem uns 6% de largura (erro pequeno).
- Abaixo de 0,1 mm/hora (2,4 mm no dia) a camada é transparente: esses dias saem como 0. Chuva fraca some.
- O dia é o dia UTC do GIBS. Dia sem ladrilho (ainda não publicado) ou com cor "No Data" fica em branco.
- No teste de 2026-11-15 a soma de 30 dias bateu com o IMERG da NASA POWER, mas dia a dia há diferença (ver tentativas.md).

Como rodar:  python3 -I baixar_chuva_recente.py LATITUDE LONGITUDE PASTA_DE_SAIDA [--dias 45]
             python3 -I baixar_chuva_recente.py -17.79 -50.92 saida --inicio 2026-03-01 --fim 2026-03-30
Saída: PASTA/chuva-recente.csv (data,chuva_mm) e PASTA/fonte.json (endereço exato e hora UTC de cada consulta).
Só biblioteca padrão.
"""
import argparse
import concurrent.futures
import csv
import datetime
import json
import math
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.request
import zlib

CAMADA = "IMERG_Precipitation_Rate"
LADRILHO = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/" + CAMADA + "/default/{dia}/2km/{nivel}/{linha}/{coluna}.png"
TABELA_DE_CORES = "https://gibs.earthdata.nasa.gov/colormaps/v1.3/GPM_Precipitation_Rate.xml"
NIVEL = 5                 # o nível mais fino do conjunto "2km"
LADO = 512                # pixels por ladrilho
UTC = datetime.timezone.utc
AGENTE = {"User-Agent": "chuva-recente/1.0 (python-urllib)"}


def agora_utc():
    return datetime.datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def pegar(url, espera=40):
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENTE), timeout=espera) as r:
        return r.read()


def onde_cai(latitude, longitude):
    """Ladrilho (linha, coluna) e pixel (x, y) do ponto, na grade EPSG:4326 do GIBS."""
    vao = 288.0 / 2 ** NIVEL          # graus por ladrilho
    grau_por_pixel = vao / LADO
    coluna = int((longitude + 180.0) // vao)
    linha = int((90.0 - latitude) // vao)
    x = min(LADO - 1, int(((longitude + 180.0) - coluna * vao) / grau_por_pixel))
    y = min(LADO - 1, int(((90.0 - latitude) - linha * vao) / grau_por_pixel))
    return linha, coluna, x, y


def cor_do_pixel(png, px, py):
    """Lê um PNG (paleta, RGB ou RGBA, 8 bits) e devolve ((r, g, b), alfa) do pixel pedido."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("a resposta não é um PNG")
    i, idat, paleta, transp = 8, b"", None, None
    while i < len(png):
        n, tipo = struct.unpack(">I4s", png[i:i + 8])
        dado = png[i + 8:i + 8 + n]
        i += 12 + n
        if tipo == b"IHDR":
            largura, altura, bits, cor, _, _, entrelacado = struct.unpack(">IIBBBBB", dado)
        elif tipo == b"PLTE":
            paleta = dado
        elif tipo == b"tRNS":
            transp = dado
        elif tipo == b"IDAT":
            idat += dado
    if bits != 8 or entrelacado or cor not in (2, 3, 6):
        raise ValueError("PNG de um tipo que este leitor não trata (bits=%s, cor=%s)" % (bits, cor))
    canais = {2: 3, 3: 1, 6: 4}[cor]
    passo = largura * canais
    cru = zlib.decompress(idat)
    anterior, pos = bytearray(passo), 0
    for _ in range(py + 1):
        filtro = cru[pos]
        linha = bytearray(cru[pos + 1:pos + 1 + passo])
        pos += 1 + passo
        if filtro == 1:
            for k in range(canais, passo):
                linha[k] = (linha[k] + linha[k - canais]) & 255
        elif filtro == 2:
            for k in range(passo):
                linha[k] = (linha[k] + anterior[k]) & 255
        elif filtro == 3:
            for k in range(passo):
                linha[k] = (linha[k] + (((linha[k - canais] if k >= canais else 0) + anterior[k]) >> 1)) & 255
        elif filtro == 4:
            for k in range(passo):
                a = linha[k - canais] if k >= canais else 0
                b = anterior[k]
                c = anterior[k - canais] if k >= canais else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                linha[k] = (linha[k] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 255
        anterior = linha
    if cor == 3:
        indice = anterior[px]
        return tuple(paleta[indice * 3:indice * 3 + 3]), (transp[indice] if transp and indice < len(transp) else 255)
    o = px * canais
    return tuple(anterior[o:o + 3]), (anterior[o + 3] if canais == 4 else 255)


def ler_tabela_de_cores():
    """cor (r,g,b) -> (minimo, maximo) em mm/hora; None = "No Data"."""
    texto = pegar(TABELA_DE_CORES).decode("utf-8")
    hora = agora_utc()
    tabela = {}
    for entrada in re.findall(r"<ColorMapEntry[^>]*>", texto):
        rgb = re.search(r'rgb="([^"]*)"', entrada)
        faixa = re.search(r'value="[\[\(]([^,]*),([^\]\)]*)[\]\)]"', entrada)
        if not rgb:
            continue
        cor = tuple(int(v) for v in rgb.group(1).split(","))
        if cor in tabela:
            continue
        if not faixa:
            tabela[cor] = None
        else:
            lo, hi = faixa.group(1).strip(), faixa.group(2).strip()
            tabela[cor] = (float("-inf") if "INF" in lo else float(lo), float("inf") if "INF" in hi else float(hi))
    if len(tabela) < 50:
        raise RuntimeError("a tabela de cores do GIBS veio com menos de 50 cores")
    return tabela, hora


def mm_do_dia(faixa):
    lo, hi = faixa
    if lo == float("-inf"):
        return 0.0                      # abaixo de 0,1 mm/hora: a camada não mostra
    taxa = lo if hi == float("inf") else math.sqrt(lo * hi)
    return round(taxa * 24.0, 2)


def um_dia(dia, linha, coluna, x, y, tabela):
    url = LADRILHO.format(dia=dia, nivel=NIVEL, linha=linha, coluna=coluna)
    reg = {"data": dia, "endereco": url, "consultado_em_utc": None, "http": None, "cor_rgb": None,
           "faixa_mm_por_hora": None, "chuva_mm": None, "obs": ""}
    for tentativa in range(3):
        reg["consultado_em_utc"] = agora_utc()
        try:
            png = pegar(url)
            reg["http"] = 200
            cor, alfa = cor_do_pixel(png, x, y)
            reg["cor_rgb"] = list(cor)
            if cor not in tabela:
                reg["obs"] = "cor fora da tabela (transparência %s)" % alfa
            elif tabela[cor] is None:
                reg["obs"] = "No Data na camada"
            else:
                lo, hi = tabela[cor]
                reg["faixa_mm_por_hora"] = [None if math.isinf(lo) else lo, None if math.isinf(hi) else hi]
                reg["chuva_mm"] = mm_do_dia(tabela[cor])
                if math.isinf(lo):
                    reg["obs"] = "abaixo de 0,1 mm/hora (menos de 2,4 mm no dia): sai como 0"
            return reg
        except urllib.error.HTTPError as erro:
            reg["http"] = erro.code
            reg["obs"] = "sem ladrilho para o dia (HTTP %s)" % erro.code
            if erro.code in (400, 404):
                return reg
        except Exception as erro:
            reg["obs"] = "%s: %s" % (type(erro).__name__, erro)
        time.sleep(1.5 * (tentativa + 1))
    return reg


def main():
    p = argparse.ArgumentParser(description="Chuva diária recente do GPM IMERG num ponto, sem login (NASA GIBS).")
    p.add_argument("latitude", type=float)
    p.add_argument("longitude", type=float)
    p.add_argument("pasta")
    p.add_argument("--dias", type=int, default=45, help="quantos dias para trás, contando hoje em UTC (padrão 45)")
    p.add_argument("--inicio", help="AAAA-MM-DD (em vez de --dias)")
    p.add_argument("--fim", help="AAAA-MM-DD (padrão: hoje em UTC)")
    a = p.parse_args()

    fim = datetime.date.fromisoformat(a.fim) if a.fim else datetime.datetime.now(UTC).date()
    inicio = datetime.date.fromisoformat(a.inicio) if a.inicio else fim - datetime.timedelta(days=a.dias - 1)
    dias = [(inicio + datetime.timedelta(days=i)).isoformat() for i in range((fim - inicio).days + 1)]
    os.makedirs(a.pasta, exist_ok=True)
    comecou = agora_utc()

    tabela, hora_tabela = ler_tabela_de_cores()
    linha, coluna, x, y = onde_cai(a.latitude, a.longitude)
    with concurrent.futures.ThreadPoolExecutor(8) as fila:
        registros = list(fila.map(lambda d: um_dia(d, linha, coluna, x, y, tabela), dias))

    with open(os.path.join(a.pasta, "chuva-recente.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["data", "chuva_mm"])
        for r in registros:
            w.writerow([r["data"], "" if r["chuva_mm"] is None else repr(r["chuva_mm"])])

    com_dado = [r["data"] for r in registros if r["chuva_mm"] is not None]
    fonte = {
        "o_que_e": "Chuva diária do GPM IMERG (satélite, NASA/JAXA) lida da cor do ponto na camada diária "
                   "IMERG_Precipitation_Rate do NASA GIBS e traduzida pela tabela de cores oficial. Sem login.",
        "conta": "chuva do dia (mm) = meio da faixa de mm/hora (média geométrica dos limites) x 24",
        "ressalvas": ["valor em faixas de uns 6% de largura",
                      "abaixo de 0,1 mm/hora (2,4 mm no dia) a camada é transparente: o dia sai como 0",
                      "dia UTC; dia sem ladrilho ou 'No Data' fica em branco"],
        "ponto": {"latitude": a.latitude, "longitude": a.longitude},
        "ladrilho": {"conjunto": "2km", "nivel": NIVEL, "linha": linha, "coluna": coluna, "pixel_x": x, "pixel_y": y},
        "periodo_pedido": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "comecou_em_utc": comecou, "terminou_em_utc": agora_utc(),
        "tabela_de_cores": {"endereco": TABELA_DE_CORES, "consultado_em_utc": hora_tabela, "cores": len(tabela)},
        "ultimo_dia_com_dado": com_dado[-1] if com_dado else None,
        "dias_com_dado": len(com_dado), "dias_pedidos": len(dias),
        "consultas": registros,
    }
    with open(os.path.join(a.pasta, "fonte.json"), "w", encoding="utf-8") as f:
        json.dump(fonte, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("chuva-recente.csv: %s a %s, %d dias, %d com dado; último dia com dado: %s; soma %.1f mm" % (
        inicio, fim, len(dias), len(com_dado), fonte["ultimo_dia_com_dado"],
        sum(r["chuva_mm"] for r in registros if r["chuva_mm"] is not None)))


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("Não deu para baixar a chuva recente:", type(erro).__name__, erro, file=sys.stderr)
        sys.exit(1)
