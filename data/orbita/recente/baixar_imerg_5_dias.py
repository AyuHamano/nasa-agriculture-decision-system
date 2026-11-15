#!/usr/bin/env python3
# Gerado com IA (Claude)
"""Baixa a chuva do satélite GPM IMERG Late (V07) somada de 5 em 5 dias, em mm, sem login, para os pontos do motor.

É ferramenta de dados: não faz parte do motor e é a única peça daqui que usa biblioteca de fora (Pillow e numpy,
para abrir a imagem GeoTIFF). O que ela grava é CSV e JSON simples.

A fonte: o servidor de dados do Climate Hazards Center da Universidade da Califórnia em Santa Barbara (o grupo do
CHIRPS, parceiro da rede FEWS NET), que guarda o IMERG Late da NASA somado por pêntada (5 dias; a última do mês vai
até o fim do mês) para o visualizador Early Warning eXplorer:
    https://data.chc.ucsb.edu/products/EWX2/IMERGlatev7/imerglatev7_global_pentad_data/data_AAAAMMDD_AAAAMMDD.tif
Não é um servidor da NASA: é um espelho do produto da NASA. A unidade (mm na pêntada) foi conferida aqui contra a
soma do IMERG guardado da NASA POWER nas mesmas pêntadas (ver o LEIA-ME desta pasta).

Uso, de dentro desta pasta:
    python3 -I baixar_imerg_5_dias.py --inicio 2026-02-01 --fim 2026-11-15
Grava, na pasta de cada cidade, chuva-5-dias.csv (inicio,fim,chuva_mm) e fonte-5-dias.json.
"""
import argparse
import calendar
import csv
import datetime
import json
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://data.chc.ucsb.edu/products/EWX2/IMERGlatev7/imerglatev7_global_pentad_data/"
PONTOS = {"rio_verde": (-17.79, -50.92), "jatai": (-17.88, -51.71), "silvania": (-16.66, -48.61)}
AQUI = Path(__file__).resolve().parent


def pentadas(inicio, fim):
    """As pêntadas do calendário que começam em [inicio, fim]: dias 1, 6, 11, 16, 21 e 26 (a última vai ao fim do mês)."""
    saida, dia = [], inicio.replace(day=1)
    while dia <= fim:
        ultimo = calendar.monthrange(dia.year, dia.month)[1]
        for comeco in (1, 6, 11, 16, 21, 26):
            a = dia.replace(day=comeco)
            b = dia.replace(day=ultimo if comeco == 26 else comeco + 4)
            if inicio <= a <= fim:
                saida.append((a, b))
        dia = (dia.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    return saida


def ler_pontos(caminho):
    """O valor de cada ponto do motor no GeoTIFF: {cidade: mm ou None}, e a ficha da grade."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    imagem = Image.open(caminho)
    escala, amarra = imagem.tag_v2[33550], imagem.tag_v2[33922]      # o tamanho do pixel e o canto de cima
    sem_dado = imagem.tag_v2.get(42113)
    valores = {}
    for cidade, (lat, lon) in PONTOS.items():
        coluna, linha = int((lon - amarra[3]) / escala[0]), int((amarra[4] - lat) / escala[1])
        valor = float(imagem.getpixel((coluna, linha)))
        vazio = valor < 0 or valor != valor or (sem_dado is not None and str(valor) == str(float(sem_dado)))
        valores[cidade] = None if vazio else round(valor, 2)
    return valores, {"largura": imagem.size[0], "altura": imagem.size[1], "pixel_graus": [escala[0], escala[1]],
                     "canto": [amarra[3], amarra[4]], "sem_dado": sem_dado}


def main():
    leitor = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    leitor.add_argument("--inicio", type=datetime.date.fromisoformat, required=True)
    leitor.add_argument("--fim", type=datetime.date.fromisoformat, required=True)
    a = leitor.parse_args()
    linhas, consultas, grade = {cidade: [] for cidade in PONTOS}, [], None
    with tempfile.TemporaryDirectory() as pasta:
        for comeco, termino in pentadas(a.inicio, a.fim):
            url = f"{BASE}data_{comeco:%Y%m%d}_{termino:%Y%m%d}.tif"
            hora = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
            registro = {"inicio": comeco.isoformat(), "fim": termino.isoformat(), "endereco": url,
                        "consultado_em_utc": hora}
            try:
                arquivo = Path(pasta) / "pentada.tif"
                with urllib.request.urlopen(url, timeout=120) as resposta:
                    arquivo.write_bytes(resposta.read())
                    registro["http"] = resposta.status
                valores, grade = ler_pontos(arquivo)
                registro["bytes"] = arquivo.stat().st_size
            except urllib.error.HTTPError as erro:          # pêntada ainda não publicada: fica em branco, nunca zero
                registro["http"], valores = erro.code, {cidade: None for cidade in PONTOS}
            consultas.append(dict(registro, valores_mm=valores))
            for cidade, valor in valores.items():
                linhas[cidade].append((comeco.isoformat(), termino.isoformat(), "" if valor is None else valor))
            print(comeco, termino, registro["http"], valores, flush=True)
    for cidade, (lat, lon) in PONTOS.items():
        destino = AQUI / cidade
        destino.mkdir(exist_ok=True)
        with (destino / "chuva-5-dias.csv").open("w", newline="", encoding="utf-8") as f:
            escritor = csv.writer(f)
            escritor.writerow(["inicio", "fim", "chuva_mm"])
            escritor.writerows(linhas[cidade])
        com_dado = [linha for linha in linhas[cidade] if linha[2] != ""]
        fonte = {"gerado_com": "IA (Claude)",
                 "o_que_e": "A chuva do satélite GPM IMERG Late V07, somada de 5 em 5 dias (pêntada), em mm.",
                 "de_quem": "NASA (GPM IMERG Late Run V07); a soma por pêntada e o arquivo são do Climate Hazards "
                            "Center da UC Santa Barbara (dados do Early Warning eXplorer). Não é um servidor da NASA.",
                 "ponto": {"lat": lat, "lon": lon}, "grade": grade,
                 "ultima_pentada_com_dado": com_dado[-1][1] if com_dado else None,
                 "consultas": [{chave: valor for chave, valor in c.items() if chave != "valores_mm"}
                               | {"chuva_mm": c["valores_mm"][cidade]} for c in consultas]}
        (destino / "fonte-5-dias.json").write_text(json.dumps(fonte, ensure_ascii=False, indent=1) + "\n",
                                                   encoding="utf-8")


if __name__ == "__main__":
    main()
