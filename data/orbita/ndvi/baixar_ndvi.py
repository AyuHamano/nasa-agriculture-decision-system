#!/usr/bin/env python3
# Gerado com IA (Claude)
"""Escolhe pontos de lavoura perto de uma cidade e baixa o verde do satélite (NDVI) de cada um, sem login.

É ferramenta de dados: não faz parte do motor. O motor (backend/orbita/ndvi.py) só lê os CSV que ela grava.
Só usa a biblioteca padrão do Python.

O produto é o mesmo de Rio Verde: MOD13Q1 v061 (MODIS/Terra, NDVI, uma medida a cada 16 dias, pixel de 250 m), da
NASA (LP DAAC), lido no espelho do Microsoft Planetary Computer (a coleção modis-13Q1-061).

Como os pontos são escolhidos (a regra foi escrita antes de ver o NDVI de qualquer ponto):
1. Os candidatos: a 15 e a 20 km do ponto da cidade, em 8 direções, nesta ordem: norte, leste, sul, oeste,
   nordeste, sudeste, sudoeste, noroeste (primeiro os de 15 km, depois os de 20 km).
2. O mapa: o mapa anual de uso da terra de 10 m (coleção io-lulc-annual-v02 do mesmo espelho: Impact Observatory,
   Esri e Microsoft, feito de imagens do Sentinel-2). O candidato passa se o centro e mais 4 lugares a uns 110 m
   dele (norte, sul, leste e oeste: o tamanho do pixel do MODIS) forem "lavoura" (classe 5, Crops) no mapa de 2018
   e no de 2023.
3. Ficam os 6 primeiros que passam, na ordem acima.
4. Se menos de 6 passam, entra mais uma volta de candidatos, a 25 km (--distancias 15,20,25), na mesma ordem.
   Foi o caso de Silvânia, em 2026-11-15: só 4 passaram a 15 e a 20 km.
Ninguém foi ao campo: não se sabe de quem são os pontos nem o que foi plantado em cada um.

Uso, de dentro desta pasta (a latitude e a longitude com o sinal de igual, porque são números negativos):
    python3 -I baixar_ndvi.py --cidade jatai --lat=-17.88 --lon=-51.71 --saida ../cidades/jatai/ndvi
"""
import argparse
import csv
import json
import math
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PONTO = "https://planetarycomputer.microsoft.com/api/data/v1/item/point/{lon},{lat}"
COLECAO_DO_NDVI = "modis-13Q1-061"
CAMADAS = ("250m_16_days_NDVI", "250m_16_days_pixel_reliability")
COLECAO_DO_MAPA = "io-lulc-annual-v02"
CLASSE_LAVOURA = 5                       # "Crops" na legenda do mapa
ANOS_DO_MAPA = (2018, 2023)
VIZINHO_GRAUS = 0.001                    # uns 110 m
DIRECOES = (("norte", 0, 1), ("leste", 1, 0), ("sul", 0, -1), ("oeste", -1, 0),
            ("nordeste", 1, 1), ("sudeste", 1, -1), ("sudoeste", -1, -1), ("noroeste", -1, 1))
DISTANCIAS_KM = (15, 20)
QUANTOS_PONTOS = 6
INICIO = "2018-07-01"                    # o mesmo começo dos pontos de Rio Verde
KM_POR_GRAU = 111.32


def agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def pedir(url, dados=None, tentativas=6):
    """Devolve (o JSON da resposta, a hora da consulta em UTC)."""
    for i in range(tentativas):
        try:
            pedido = urllib.request.Request(url, data=dados, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(pedido, timeout=60) as resposta:
                return json.loads(resposta.read()), agora()
        except Exception:  # noqa: BLE001
            if i == tentativas - 1:
                raise
            time.sleep(1.5 * (i + 1))


def candidatos(lat, lon, distancias=DISTANCIAS_KM):
    """Os candidatos (8 por distância), na ordem da regra: [(nome, lat, lon)], com 3 casas (uns 100 m)."""
    saida = []
    for km in distancias:
        for nome, leste, norte in DIRECOES:
            tamanho = math.hypot(leste, norte)
            d_lat = km * (norte / tamanho) / KM_POR_GRAU
            d_lon = km * (leste / tamanho) / (KM_POR_GRAU * math.cos(math.radians(lat)))
            saida.append((f"{nome}-{km}km", round(lat + d_lat, 3), round(lon + d_lon, 3)))
    return saida


def buscar(colecao, lat, lon, extra):
    """A lista das imagens do catálogo que cobrem o ponto. Devolve (as imagens, as consultas feitas)."""
    corpo = dict({"collections": [colecao], "intersects": {"type": "Point", "coordinates": [lon, lat]},
                  "limit": 1000}, **extra)
    imagens, consultas, url, dados = [], [], STAC, json.dumps(corpo).encode()
    while True:
        resposta, hora = pedir(url, dados)
        consultas.append({"endereco": url, "metodo": "POST" if dados else "GET",
                          "corpo": json.loads(dados) if dados else None, "consultado_em_utc": hora,
                          "imagens": len(resposta["features"])})
        imagens += resposta["features"]
        proxima = next((elo for elo in resposta.get("links", []) if elo.get("rel") == "next"), None)
        if not proxima:
            return imagens, consultas
        dados = json.dumps(proxima.get("body", corpo)).encode() if proxima.get("method") == "POST" else None
        url = proxima["href"]


def conferir_no_mapa(nome, lat, lon):
    """Lê o mapa de uso da terra no centro e nos 4 vizinhos, nos dois anos. Devolve a ficha do candidato."""
    imagens, consultas = buscar(COLECAO_DO_MAPA, lat, lon, {})
    por_ano = {}
    for imagem in imagens:
        por_ano.setdefault(int(imagem["properties"]["start_datetime"][:4]), imagem["id"])
    lugares = [("centro", lat, lon), ("norte", round(lat + VIZINHO_GRAUS, 4), lon),
               ("sul", round(lat - VIZINHO_GRAUS, 4), lon), ("leste", lat, round(lon + VIZINHO_GRAUS, 4)),
               ("oeste", lat, round(lon - VIZINHO_GRAUS, 4))]
    leituras = []
    for ano in ANOS_DO_MAPA:
        for lugar, la, lo in lugares:
            item = por_ano.get(ano)
            if item is None:
                leituras.append({"ano": ano, "lugar": lugar, "classe": None, "endereco": None})
                continue
            url = PONTO.format(lon=lo, lat=la) + f"?collection={COLECAO_DO_MAPA}&item={item}&assets=data"
            resposta, hora = pedir(url)
            leituras.append({"ano": ano, "lugar": lugar, "classe": int(resposta["values"][0]), "endereco": url,
                             "consultado_em_utc": hora})
    passou = all(leitura["classe"] == CLASSE_LAVOURA for leitura in leituras)
    return {"nome": nome, "lat": lat, "lon": lon, "passou": passou, "busca_no_catalogo": consultas,
            "leituras": leituras}


def baixar_ponto(nome, lat, lon, fim, pasta):
    """Baixa a série do NDVI do ponto e grava <nome>.csv. Devolve a ficha do que veio."""
    imagens, consultas = buscar(COLECAO_DO_NDVI, lat, lon, {
        "query": {"platform": {"eq": "terra"}}, "datetime": f"{INICIO}T00:00:00Z/{fim}T23:59:59Z"})
    camadas = "&".join(f"assets={camada}" for camada in CAMADAS)

    def ler(imagem):
        url = PONTO.format(lon=lon, lat=lat) + f"?collection={COLECAO_DO_NDVI}&item={imagem['id']}&{camadas}"
        resposta, hora = pedir(url)
        return imagem, resposta["values"], hora

    with ThreadPoolExecutor(12) as fila:
        respostas = list(fila.map(ler, imagens))
    linhas, repetidas = {}, 0
    for imagem, (ndvi, qualidade), hora in respostas:
        dia = imagem["properties"]["start_datetime"][:10]
        nova = (dia, int(ndvi), int(qualidade), imagem["id"], lat, lon, hora)
        if dia in linhas:
            repetidas += 1
        if dia not in linhas or (linhas[dia][1] == -3000 and nova[1] != -3000):   # fica a que tem dado
            linhas[dia] = nova
    with (pasta / f"{nome}.csv").open("w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["Date", "ndvi_bruto", "pixel_reliability", "item", "lat", "lon", "consultado_em_utc"])
        for dia in sorted(linhas):
            escritor.writerow(linhas[dia])
    datas = sorted(linhas)
    return {"arquivo": f"{nome}.csv", "lat": lat, "lon": lon, "medidas": len(datas),
            "primeira": datas[0] if datas else None, "ultima": datas[-1] if datas else None,
            "datas_repetidas_no_espelho": repetidas, "busca_no_catalogo": consultas,
            "endereco_de_cada_medida": PONTO.format(lon=lon, lat=lat) + f"?collection={COLECAO_DO_NDVI}"
                                       f"&item=<a coluna item do CSV>&{camadas}",
            "hora_de_cada_medida": "a coluna consultado_em_utc do CSV"}


def main():
    leitor = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    leitor.add_argument("--cidade", required=True)
    leitor.add_argument("--lat", type=float, required=True)
    leitor.add_argument("--lon", type=float, required=True)
    leitor.add_argument("--saida", required=True)
    leitor.add_argument("--fim", default=datetime.now(timezone.utc).date().isoformat())
    leitor.add_argument("--distancias", default=",".join(str(km) for km in DISTANCIAS_KM),
                        help="as distâncias dos candidatos, em km, na ordem (o padrão é 15,20)")
    a = leitor.parse_args()
    distancias = tuple(int(km) for km in a.distancias.split(","))
    pasta = Path(a.saida)
    pasta.mkdir(parents=True, exist_ok=True)
    comecou = agora()
    with ThreadPoolExecutor(8) as fila:
        fichas = list(fila.map(lambda c: conferir_no_mapa(*c), candidatos(a.lat, a.lon, distancias)))
    escolhidos = [ficha for ficha in fichas if ficha["passou"]][:QUANTOS_PONTOS]
    for ficha in fichas:
        classes = [leitura["classe"] for leitura in ficha["leituras"]]
        print(f"{ficha['nome']:14s} {ficha['lat']:8.3f} {ficha['lon']:8.3f} classes {classes} "
              f"{'passa' if ficha['passou'] else 'não passa'}", flush=True)
    if len(escolhidos) < QUANTOS_PONTOS:
        print(f"ATENÇÃO: só {len(escolhidos)} candidatos passaram no mapa (a regra pede {QUANTOS_PONTOS}).",
              flush=True)
    pontos = []
    for ficha in escolhidos:
        ponto = baixar_ponto(ficha["nome"], ficha["lat"], ficha["lon"], a.fim, pasta)
        pontos.append(ponto)
        print(f"baixado {ponto['arquivo']}: {ponto['medidas']} medidas, {ponto['primeira']} a {ponto['ultima']}",
              flush=True)
    fonte = {
        "gerado_com": "IA (Claude)", "cidade_id": a.cidade, "ponto_da_cidade": {"lat": a.lat, "lon": a.lon},
        "produto": "MOD13Q1 v061 (MODIS/Terra, NDVI, a cada 16 dias, pixel de 250 m), NASA LP DAAC, "
                   "https://doi.org/10.5067/MODIS/MOD13Q1.061",
        "espelho": "Microsoft Planetary Computer, coleção modis-13Q1-061, sem login",
        "periodo_pedido": {"de": INICIO, "ate": a.fim},
        "comecou_em_utc": comecou, "terminou_em_utc": agora(),
        "regra_da_escolha": {
            "candidatos": f"a {' e a '.join(str(km) for km in distancias)} km do ponto da cidade, em 8 direções, na "
                          "ordem: norte, leste, sul, oeste, nordeste, sudeste, sudoeste, noroeste (primeiro os mais "
                          "perto). O padrão é 15 e 20 km; a volta de 25 km só entra se menos de 6 passam.",
            "mapa": "io-lulc-annual-v02 (mapa anual de uso da terra de 10 m, Impact Observatory, Esri e Microsoft), "
                    "https://planetarycomputer.microsoft.com/dataset/io-lulc-annual-v02",
            "passa_se": f"o centro e os 4 vizinhos a {VIZINHO_GRAUS} grau (uns 110 m) são classe "
                        f"{CLASSE_LAVOURA} (Crops, lavoura) nos mapas de {ANOS_DO_MAPA[0]} e {ANOS_DO_MAPA[1]}",
            "ficam": f"os {QUANTOS_PONTOS} primeiros que passam, na ordem dos candidatos",
            "aviso": "Pontos escolhidos no mapa: não se sabe de quem são nem o que foi plantado em cada um. "
                     "Ninguém conferiu em campo.",
        },
        "candidatos": fichas, "pontos": pontos,
    }
    (pasta / "fonte.json").write_text(json.dumps(fonte, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0 if len(escolhidos) == QUANTOS_PONTOS else 1


if __name__ == "__main__":
    sys.exit(main())
