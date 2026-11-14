"""SMAP L3 (9 km) umidade do solo via AppEEARS, para várias cidades numa única tarefa.

ATENÇÃO: o SMAP mede só a camada SUPERFICIAL do solo (~5 cm). Não representa a
umidade na zona das raízes. Use como indicador de estresse hídrico, não como balanço hídrico completo.

Pré-requisitos: conta Earthdata + termos do AppEEARS aceitos (mesmos do script MODIS).
    export EARTHDATA_USER="..."   (ou use um arquivo .env com python-dotenv)
    export EARTHDATA_PASS="..."

Uso:
    python smap-dataset-colector.py                         # Espumoso (RS) + Silvânia (GO), 2015-2025
    python smap-dataset-colector.py --csv data/cache/smap_espumoso_silvania_2015_2025.csv
    python smap-dataset-colector.py --listar-layers         # só mostra versão e layers do produto

Os indicadores são salvos em data/cache/indicadores_smap_<cidade>.json.

Requisitos: pip install requests pandas   (opcional: python-dotenv)
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.scripts.appeears_utils import download_task_csv, earthdata_headers

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API = "https://appeears.earthdatacloud.nasa.gov/api"
PRODUTO_BASE = "SPL3SMP_E"        # SMAP Enhanced L3, 9 km, diário
PRODUTO_PADRAO = "SPL3SMP_E.006"  # usado se a lista de produtos não puder ser lida
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
PCT_SECO = 20                      # "dia seco" = abaixo do percentil 20 da série da própria cidade
CIDADES_PADRAO = {
    # "espumoso": (-28.725, -52.85),
    "silvania": (-16.66, -48.61),
}

RE_SM = re.compile(r"retrieval_data_(am|pm)_soil_moisture(_pm)?$", re.I)
RE_QA = re.compile(r"retrieval_data_(am|pm)_retrieval_qual_flag(_pm)?$", re.I)


def login():
    return earthdata_headers()


def descobrir_produto(forcar=None):
    """Escolhe a versão mais recente de SPL3SMP_E disponível no AppEEARS."""
    if forcar:
        return forcar
    try:
        prods = requests.get(f"{API}/product", timeout=60).json()
        versoes = [p["ProductAndVersion"] for p in prods
                   if p.get("Product") == PRODUTO_BASE and p.get("Available", True)]
        if versoes:
            return sorted(versoes, key=lambda v: int(v.split(".")[-1]))[-1]
    except Exception as e:  # sem rede para listar: cai no padrão
        print(f"[aviso] não consegui listar produtos ({e}); usando {PRODUTO_PADRAO}")
    return PRODUTO_PADRAO


def escolher_layers(produto):
    """Pega do AppEEARS os nomes reais dos layers de umidade e qualidade (AM/PM)."""
    r = requests.get(f"{API}/product/{produto}", timeout=60)
    r.raise_for_status()
    nomes = list(r.json().keys())
    sm = [n for n in nomes if RE_SM.search(n)]
    qa = [n for n in nomes if RE_QA.search(n)]
    if not sm:
        sugestao = [n for n in nomes if "soil" in n.lower()]
        sys.exit(f"Nenhum layer de umidade reconhecido em {produto}. Candidatos: {sugestao}\n"
                 f"Ajuste RE_SM no script.")
    return sm, qa, nomes


def baixar(cidades, ano_ini, ano_fim, produto, nome_arq):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    destino = CACHE_DIR / f"smap_{nome_arq}_{ano_ini}_{ano_fim}.csv"
    if destino.exists():
        print(f"[cache] usando {destino}")
        return destino

    sm, qa, _ = escolher_layers(produto)
    print(f"[api] produto {produto} | layers: {sm + qa}")
    tarefa = {
        "task_type": "point",
        "task_name": f"raizviva_smap_{nome_arq}_{int(time.time())}",
        "params": {
            "dates": [{"startDate": f"04-01-{ano_ini}", "endDate": f"12-31-{ano_fim}"}],
            "layers": [{"product": produto, "layer": l} for l in sm + qa],
            "coordinates": [
                {"id": str(i), "category": nome, "latitude": lat, "longitude": lon}
                for i, (nome, (lat, lon)) in enumerate(cidades.items())
            ],
        },
    }
    headers = login()
    task_id_file = CACHE_DIR / f"smap_task_id_{nome_arq}.txt"
    return download_task_csv(tarefa, headers, destino, task_id_file)


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def umidade_diaria(df):
    """Combina AM e PM, descarta preenchimento e retrievals sem qualidade recomendada."""
    cols_sm = [c for c in df.columns if RE_SM.search(c)]
    cols_qa = [c for c in df.columns if RE_QA.search(c)]
    if not cols_sm:
        sys.exit(f"Colunas de umidade não encontradas no CSV. Colunas: {list(df.columns)}")

    partes = []
    for c in cols_sm:
        v = _num(df[c])
        v = v.where((v >= 0) & (v < 1))              # fill = -9999; umidade volumétrica é 0–1 m³/m³
        periodo = "pm" if "_pm" in c.lower() or "_PM_" in c else "am"
        qa = next((q for q in cols_qa if (("_pm" in q.lower() or "_PM_" in q) == (periodo == "pm"))), None)
        if qa is not None:
            f = _num(df[qa])
            if f.notna().any():
                v = v.where(~(f.fillna(0).astype("int64") & 1).astype(bool))  # bit 0 = 0 → qualidade recomendada
        partes.append(v)
    return pd.concat(partes, axis=1).mean(axis=1)


def indicadores(df_cidade):
    d = df_cidade.copy()
    d["Date"] = pd.to_datetime(d["Date"])
    d["sm"] = umidade_diaria(d)
    d = d.dropna(subset=["sm"])
    if d.empty:
        return None
    d["ano"], d["mes"] = d["Date"].dt.year, d["Date"].dt.month

    limiar = d["sm"].quantile(PCT_SECO / 100)
    d["seco"] = (d["sm"] < limiar).astype(int)

    mensal = d.groupby("mes").agg(
        sm_medio=("sm", "mean"),
        sm_p10=("sm", lambda x: x.quantile(0.10)),
        sm_p90=("sm", lambda x: x.quantile(0.90)),
        pct_dias_secos=("seco", "mean"),
        anos_com_dado=("ano", "nunique"),
    )
    mensal["pct_dias_secos"] *= 100
    mensal = mensal.round(3).reset_index()

    anual = d.groupby("ano").agg(sm_medio=("sm", "mean"), dias_com_dado=("sm", "count"))
    anual = anual[anual["dias_com_dado"] >= 60]  # ignora anos quase sem dado
    z = (anual["sm_medio"] - anual["sm_medio"].mean()) / (anual["sm_medio"].std() or 1)
    anual["anomalia_z"] = z.round(2)
    anual["sm_medio"] = anual["sm_medio"].round(3)
    anual = anual.reset_index()

    meta = {
        "fonte": "NASA SMAP L3 Enhanced 9 km (SPL3SMP_E) via AppEEARS",
        "unidade": "m3/m3 (umidade volumétrica)",
        "aviso": "Mede só a camada superficial (~5 cm), não a zona de raízes. "
                 "Resolução ~9 km: não representa um talhão específico. Série começa em 2015.",
        "limiar_dia_seco": round(float(limiar), 3),
        "definicao_dia_seco": f"abaixo do percentil {PCT_SECO} da série desta cidade",
        "periodo": f"{d['Date'].min().date()} a {d['Date'].max().date()}",
        "observacoes_validas": int(len(d)),
        "ano_mais_seco": int(anual.loc[anual["sm_medio"].idxmin(), "ano"]) if len(anual) else None,
        "ano_mais_umido": int(anual.loc[anual["sm_medio"].idxmax(), "ano"]) if len(anual) else None,
    }
    return {"meta": meta, "mensal": mensal.to_dict("records"), "anual": anual.to_dict("records")}


def processar(csv_path):
    df = pd.read_csv(csv_path)
    saidas = {}
    for cidade, g in df.groupby("Category"):
        res = indicadores(g)
        if res is None:
            print(f"[aviso] {cidade}: sem observações válidas após o filtro")
            continue
        saidas[cidade] = res
    return saidas


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=int, default=2015)
    p.add_argument("--end", type=int, default=2025)
    p.add_argument("--produto", help="força uma versão, ex.: SPL3SMP_E.006")
    p.add_argument("--csv", help="processar um CSV já baixado, sem chamar a API")
    p.add_argument("--listar-layers", action="store_true")
    a = p.parse_args()

    produto = descobrir_produto(a.produto)
    if a.listar_layers:
        sm, qa, nomes = escolher_layers(produto)
        print(produto, "\nUmidade:", sm, "\nQualidade:", qa, "\nTodos:", nomes)
        return

    ano_ini = max(a.start, 2015)  # SMAP começa em 31/03/2015
    nome_arq = "_".join(CIDADES_PADRAO)
    csv_path = Path(a.csv) if a.csv else baixar(CIDADES_PADRAO, ano_ini, a.end, produto, nome_arq)

    saidas = processar(csv_path)
    for cidade, res in saidas.items():
        print(f"\n=== {cidade} ===")
        print(json.dumps(res["meta"], ensure_ascii=False, indent=2))
        print(pd.DataFrame(res["mensal"]).to_string(index=False))
        arq = CACHE_DIR / f"indicadores_smap_{cidade}.json"
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"salvo em {arq}")


if __name__ == "__main__":
    main()