#!/usr/bin/env python3
# Gerado com IA (Claude). Órbita Rural (NASA Space Apps 2026).
"""Lê a chuva por dia que o baixar_chuva_do_dia.py guardou. Só biblioteca padrão (Python puro).

O arquivo de cada cidade é `<cidade>/chuva-do-dia.csv`, com as colunas `data`, `chuva_early_mm` e `chuva_late_mm`:
a chuva do satélite GPM IMERG V07 somada no dia de Brasília, na versão Early (a mais rápida) e na Late (a que a NASA
solta umas 15 horas depois, mais acertada). Dia sem dado fica em branco no arquivo e vira None aqui: nunca vira zero.

Como usar de outro programa:
    import ler
    chuva = ler.chuva_por_dia("rio_verde")              # {data: mm ou None}; o Late onde houver, senão o Early
    chuva = ler.chuva_por_dia("rio_verde", "early")     # só o Early
Como ver na tela:
    python3 -I ler.py rio_verde --dias 10
"""
import csv
import datetime
import json
import pathlib
import sys

AQUI = pathlib.Path(__file__).resolve().parent
ARQUIVO = "chuva-do-dia.csv"
COLUNAS = ("data", "chuva_early_mm", "chuva_late_mm")
VERSOES = ("late_ou_early", "early", "late")


def _numero(texto):
    texto = (texto or "").strip()
    return float(texto) if texto else None


def ler_linhas(cidade_id, pasta=None):
    """As linhas do arquivo da cidade, na ordem das datas: [{"data": date, "early": mm ou None, "late": mm ou None}].

    `pasta` é onde ficam as pastas das cidades (sem ela, a pasta deste arquivo). Sem arquivo, devolve None.
    """
    arquivo = pathlib.Path(pasta or AQUI) / cidade_id / ARQUIVO
    if not arquivo.exists():
        return None
    linhas = []
    with open(arquivo, encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            linhas.append({"data": datetime.date.fromisoformat(linha["data"].strip()),
                           "early": _numero(linha.get("chuva_early_mm")),
                           "late": _numero(linha.get("chuva_late_mm"))})
    return sorted(linhas, key=lambda linha: linha["data"])


def chuva_por_dia(cidade_id, versao="late_ou_early", pasta=None):
    """A chuva por dia da cidade, em mm: {data: mm ou None}. Sem arquivo, devolve None.

    `versao`: "late_ou_early" (o Late onde já existe e, nos dias em que ainda não chegou, o Early), "early" ou "late".
    """
    if versao not in VERSOES:
        raise ValueError(f"versão desconhecida: {versao!r}. Use uma de {VERSOES}.")
    linhas = ler_linhas(cidade_id, pasta)
    if linhas is None:
        return None
    if versao == "late_ou_early":
        return {l["data"]: l["late"] if l["late"] is not None else l["early"] for l in linhas}
    return {l["data"]: l[versao] for l in linhas}


def ultimo_dia_com_dado(cidade_id, versao="late_ou_early", pasta=None):
    """O último dia com chuva guardada (uma data), ou None."""
    chuva = chuva_por_dia(cidade_id, versao, pasta) or {}
    com_dado = [data for data, mm in chuva.items() if mm is not None]
    return max(com_dado) if com_dado else None


def ficha_da_fonte(cidade_id, pasta=None):
    """O `fonte.json` da cidade (de onde veio, a versão do dado, a hora de cada consulta), ou None."""
    arquivo = pathlib.Path(pasta or AQUI) / cidade_id / "fonte.json"
    return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else None


def main(argumentos):
    if not argumentos or argumentos[0].startswith("-"):
        print("Como usar: python3 -I ler.py CIDADE [--dias 10]   (rio_verde, jatai ou silvania)")
        return 2
    dias = int(argumentos[argumentos.index("--dias") + 1]) if "--dias" in argumentos else 10
    linhas = ler_linhas(argumentos[0])
    if linhas is None:
        print(f"Não há chuva guardada de {argumentos[0]}: rode o baixar_chuva_do_dia.py antes.")
        return 1
    print("data        early_mm  late_mm")
    escrever = lambda mm: "       -" if mm is None else f"{mm:8.2f}"  # noqa: E731
    for linha in linhas[-dias:]:
        print(linha["data"].isoformat(), escrever(linha["early"]), escrever(linha["late"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
