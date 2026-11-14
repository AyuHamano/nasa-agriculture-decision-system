"""Teste do MODIS NDVI via AppEEARS (série temporal por ponto) com cache local.

Pré-requisito: conta gratuita no NASA Earthdata (https://urs.earthdata.nasa.gov)
e, na primeira vez, aceitar os termos do AppEEARS em https://appeears.earthdatacloud.nasa.gov

Uso:
    export EARTHDATA_USER="seu_usuario"
    export EARTHDATA_PASS="sua_senha"
    python teste_modis.py                       # Espumoso (RS), 2013-2023
    python teste_modis.py --csv data/cache/modis_espumoso_2013_2023.csv   # só processa o cache

Os indicadores são salvos em data/cache/indicadores_ndvi_<nome>.json, na raiz do projeto.

Requisitos: pip install requests pandas
"""
import argparse
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.scripts.appeears_utils import download_task_csv, earthdata_headers

API = "https://appeears.earthdatacloud.nasa.gov/api"
PRODUTO = "MOD13Q1.061"  # MODIS Terra, 250 m, composto de 16 dias
LAYER_NDVI = "_250m_16_days_NDVI"
LAYER_QA = "_250m_16_days_pixel_reliability"
COL_NDVI = "MOD13Q1_061__250m_16_days_NDVI"
COL_QA = "MOD13Q1_061__250m_16_days_pixel_reliability"

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"
LIMIAR_SOLO_DESCOBERTO = 0.30  # NDVI abaixo disso ~ solo exposto/palha seca (calibrar com agrônomo)
ESCALA = 0.0001                # NDVI do MOD13Q1 vem multiplicado por 10000
FILL = -3000


def login():
    return earthdata_headers()


def baixar(lat, lon, ano_ini, ano_fim, nome):
    """Submete a tarefa no AppEEARS, espera terminar e salva o CSV no cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    destino = CACHE_DIR / f"modis_{nome}_{ano_ini}_{ano_fim}.csv"
    if destino.exists():
        print(f"[cache] usando {destino}")
        return destino

    tarefa = {
        "task_type": "point",
        "task_name": f"raizviva_{nome}_{int(time.time())}",
        "params": {
            "dates": [{"startDate": f"01-01-{ano_ini}", "endDate": f"12-31-{ano_fim}"}],
            "layers": [
                {"product": PRODUTO, "layer": LAYER_NDVI},
                {"product": PRODUTO, "layer": LAYER_QA},
            ],
            "coordinates": [{"id": "0", "category": nome, "latitude": lat, "longitude": lon}],
        },
    }
    headers = login()
    task_id_file = CACHE_DIR / f"modis_task_id_{nome}_{ano_ini}_{ano_fim}.txt"
    return download_task_csv(tarefa, headers, destino, task_id_file)


def processar(csv_path):
    """Lê o CSV do AppEEARS, filtra qualidade e calcula indicadores mensais."""
    df = pd.read_csv(csv_path)
    df["Date"] = pd.to_datetime(df["Date"])
    n0 = len(df)

    df["ndvi"] = df[COL_NDVI].where(df[COL_NDVI] != FILL) * ESCALA
    # pixel_reliability: 0 = bom, 1 = marginal, 2 = neve/gelo, 3 = nuvem
    df = df[(df[COL_QA] <= 1) & df["ndvi"].notna()].copy()
    print(f"Observações: {n0} | usadas após filtro de qualidade: {len(df)}")

    df["ano"], df["mes"] = df["Date"].dt.year, df["Date"].dt.month
    df["descoberto"] = (df["ndvi"] < LIMIAR_SOLO_DESCOBERTO).astype(int)

    por_ano_mes = df.groupby(["ano", "mes"]).agg(
        ndvi=("ndvi", "mean"), frac_descoberto=("descoberto", "mean")
    )
    clima = por_ano_mes.groupby("mes").agg(
        ndvi_medio=("ndvi", "mean"),
        ndvi_min=("ndvi", "min"),
        ndvi_max=("ndvi", "max"),
        pct_solo_descoberto=("frac_descoberto", "mean"),
        anos_com_dado=("ndvi", "count"),
    )
    clima["pct_solo_descoberto"] = (clima["pct_solo_descoberto"] * 100).round(0)
    clima = clima.round(2)
    return clima


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float, default=-28.725)   # Espumoso, RS
    p.add_argument("--lon", type=float, default=-52.85)
    p.add_argument("--nome", default="espumoso")
    p.add_argument("--start", type=int, default=2013)
    p.add_argument("--end", type=int, default=2023)
    p.add_argument("--csv", help="processar um CSV já baixado, sem chamar a API")
    a = p.parse_args()

    csv_path = Path(a.csv) if a.csv else baixar(a.lat, a.lon, a.start, a.end, a.nome)
    clima = processar(csv_path)

    print(f"\n=== NDVI mensal (limiar de solo descoberto: {LIMIAR_SOLO_DESCOBERTO}) ===")
    print(clima.to_string())

    saida = CACHE_DIR / f"indicadores_ndvi_{a.nome}.json"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(
        clima.reset_index().to_json(orient="records", force_ascii=False),
        encoding="utf-8",
    )
    print(f"\nIndicadores salvos em {saida}")


if __name__ == "__main__":
    main()