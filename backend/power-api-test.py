"""Teste da API NASA POWER (diário, ponto) com cache local e indicadores mensais.

Uso:
    python teste_power.py                       # Passo Fundo (RS), 1991-2023
    python teste_power.py --lat -29.69 --lon -53.80 --nome santa_maria
    python teste_power.py --start 2000 --end 2024

Requisitos: pip install requests pandas
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import requests

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# T2M: temp. média 2 m | T2M_MAX/MIN: máx/mín | PRECTOTCORR: chuva (mm/dia)
# EVLAND: evaporação da superfície (mm/dia) | ALLSKY_SFC_SW_DWN: radiação solar
PARAMS = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "EVLAND", "ALLSKY_SFC_SW_DWN"]

CACHE_DIR = Path("data/cache")
FROST_C = 2.0   # T2M_MIN <= 2 °C no ar a 2 m costuma indicar risco de geada no solo
HEAT_C = 35.0   # T2M_MAX >= 35 °C = dia de calor extremo


def baixar(lat, lon, ano_ini, ano_fim, nome):
    """Baixa do POWER ou lê do cache. Retorna DataFrame diário."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    arq = CACHE_DIR / f"power_{nome}_{ano_ini}_{ano_fim}.json"

    if arq.exists():
        print(f"[cache] usando {arq}")
        dados = json.loads(arq.read_text())
    else:
        print(f"[api] baixando POWER para ({lat}, {lon}), {ano_ini}-{ano_fim}...")
        r = requests.get(
            URL,
            params={
                "parameters": ",".join(PARAMS),
                "community": "AG",
                "latitude": lat,
                "longitude": lon,
                "start": f"{ano_ini}0101",
                "end": f"{ano_fim}1231",
                "format": "JSON",
            },
            timeout=120,
        )
        if r.status_code != 200:
            sys.exit(f"Erro {r.status_code}: {r.text[:500]}")
        dados = r.json()
        arq.write_text(json.dumps(dados))
        print(f"[cache] salvo em {arq}")

    par = dados["properties"]["parameter"]
    df = pd.DataFrame(par)
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    return df.replace(-999, pd.NA).astype(float)


def indicadores_mensais(df):
    """Resumo por mês do ano (climatologia), média entre os anos."""
    d = df.copy()
    d["geada"] = (d["T2M_MIN"] <= FROST_C).astype(int)
    d["calor"] = (d["T2M_MAX"] >= HEAT_C).astype(int)
    d["saldo_hidrico"] = d["PRECTOTCORR"] - d["EVLAND"]  # proxy simples (mm/dia)
    d["ano"], d["mes"] = d.index.year, d.index.month

    # totais/contagens por ano-mês
    por_ano_mes = d.groupby(["ano", "mes"]).agg(
        chuva_mm=("PRECTOTCORR", "sum"),
        evap_mm=("EVLAND", "sum"),
        saldo_mm=("saldo_hidrico", "sum"),
        dias_geada=("geada", "sum"),
        dias_calor=("calor", "sum"),
        temp_media=("T2M", "mean"),
    )
    por_ano_mes["deficit"] = (por_ano_mes["saldo_mm"] < 0).astype(int)

    # média entre anos + frequência de déficit
    clima = por_ano_mes.groupby("mes").mean().round(1)
    clima = clima.rename(columns={"deficit": "freq_deficit"})
    clima["freq_deficit"] = (clima["freq_deficit"] * 100).round(0)  # % dos anos
    return clima, por_ano_mes


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float, default=-28.26)   # Passo Fundo, RS
    p.add_argument("--lon", type=float, default=-52.41)
    p.add_argument("--nome", default="passo_fundo")
    p.add_argument("--start", type=int, default=1991)
    p.add_argument("--end", type=int, default=2023)
    a = p.parse_args()

    df = baixar(a.lat, a.lon, a.start, a.end, a.nome)
    print(f"\nLinhas: {len(df)} | período: {df.index.min().date()} a {df.index.max().date()}")
    print("Valores ausentes por variável:\n", df.isna().sum().to_string())

    clima, _ = indicadores_mensais(df)
    print("\n=== Climatologia mensal (média entre anos) ===")
    print(clima.to_string())

    saida = CACHE_DIR / f"indicadores_{a.nome}.json"
    saida.write_text(clima.reset_index().to_json(orient="records", force_ascii=False))
    print(f"\nIndicadores salvos em {saida}")


if __name__ == "__main__":
    main()
    