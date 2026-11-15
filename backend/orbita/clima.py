# Gerado com IA (Claude)
"""O clima: lê a série da NASA POWER guardada e calcula a evaporação de referência de cada dia (ETo).

A conta é a do FAO-56 (Allen et al., 1998): https://www.fao.org/4/X0490E/x0490e07.htm
- Ra, a radiação do sol no topo da atmosfera, pela latitude e pelo dia do ano: equações 21 a 25.
- A troca de MJ/m²/dia para mm/dia de água evaporada: equação 20 (vezes 0,408).
- ETo por Hargreaves-Samani, que só pede a temperatura máxima e a mínima: equação 52.
"""
import collections
import datetime
import functools
import json
import math
from pathlib import Path

PASTA_DOS_DADOS = Path(__file__).resolve().parents[2] / "data" / "orbita"
PASTA_NASA_POWER = PASTA_DOS_DADOS / "nasa-power"
INICIO_DA_SIMULACAO = datetime.date(2014, 7, 1)
SEM_DADO = -999.0
CONSTANTE_SOLAR = 0.0820  # MJ/m²/min (FAO-56, eq. 21)

PASTA_DA_CHUVA = PASTA_DOS_DADOS / "validacao" / "chuva"
FONTES_DE_CHUVA = ("imerg", "chirps", "era5", "power")
ORIGENS_DA_CHUVA = {
    "imerg": "o satélite de chuva GPM IMERG, da NASA (o parâmetro IMERG_PRECTOT, entregue por ponto pela API da "
             "NASA POWER; o dia dele é o UTC)",
    "chirps": "o CHIRPS (chuva de satélite acertada com estações em terra)",
    "era5": "o modelo ERA5 (a chuva do arquivo histórico do Open-Meteo)",
    "power": "o modelo da NASA POWER (o parâmetro PRECTOTCORR), que fica só como comparação",
}
ORIGEM_DA_TEMPERATURA = "a NASA POWER (API diária, comunidade AG): T2M_MAX e T2M_MIN, no dia local"

CIDADE_DE_REFERENCIA = "rio_verde"     # a cidade da prova: os dados dela moram nas pastas de sempre
PASTA_DAS_CIDADES = PASTA_DOS_DADOS / "cidades"

Dia = collections.namedtuple("Dia", "data chuva tmax tmin eto")


def pastas_da_cidade(cidade_id=None):
    """Onde moram os dados guardados de cada cidade (a temperatura, a chuva, a colheita do IBGE e o verde).

    Rio Verde fica nas pastas de sempre; as outras, em data/orbita/cidades/<id>/, baixadas por
    data/orbita/cidades/baixar_cidade.py (o endereço e a hora de cada consulta ficam ao lado dos dados).
    """
    if cidade_id in (None, CIDADE_DE_REFERENCIA):
        return {"nasa_power": PASTA_NASA_POWER, "chuva": PASTA_DA_CHUVA,
                "ibge": PASTA_DOS_DADOS / "validacao" / "ibge" / "rendimento_rio_verde.csv",
                "ndvi": PASTA_DOS_DADOS / "ndvi", "texto": "data/orbita/nasa-power/",
                "texto_da_chuva": "data/orbita/validacao/chuva/"}
    base = PASTA_DAS_CIDADES / str(cidade_id)
    return {"nasa_power": base / "nasa-power", "chuva": base / "chuva", "ibge": base / "ibge" / "rendimento.csv",
            "ndvi": base / "ndvi", "texto": f"data/orbita/cidades/{cidade_id}/nasa-power/",
            "texto_da_chuva": f"data/orbita/cidades/{cidade_id}/chuva/"}


def chuvas_guardadas(cidade_id=None):
    """As fontes de chuva que a cidade tem guardadas (a de modelo da NASA POWER vem junto com a temperatura)."""
    pastas = pastas_da_cidade(cidade_id)
    return tuple(f for f in FONTES_DE_CHUVA if f == "power" or (pastas["chuva"] / f"{f}.csv").exists())


def dia_do_ano(data):
    """O número do dia no ano (1 de janeiro = 1)."""
    return data.timetuple().tm_yday


def distancia_relativa_terra_sol(j):
    """FAO-56, eq. 23."""
    return 1 + 0.033 * math.cos(2 * math.pi * j / 365)


def declinacao_solar(j):
    """FAO-56, eq. 24, em radianos."""
    return 0.409 * math.sin(2 * math.pi * j / 365 - 1.39)


def angulo_do_por_do_sol(latitude_graus, j):
    """FAO-56, eq. 25, em radianos. A latitude é negativa no hemisfério sul (eq. 22)."""
    phi = math.radians(latitude_graus)
    return math.acos(-math.tan(phi) * math.tan(declinacao_solar(j)))


def ra_mj(latitude_graus, j):
    """A radiação no topo da atmosfera (Ra), em MJ/m²/dia. FAO-56, eq. 21."""
    phi = math.radians(latitude_graus)
    dr = distancia_relativa_terra_sol(j)
    delta = declinacao_solar(j)
    ws = angulo_do_por_do_sol(latitude_graus, j)
    return (24 * 60 / math.pi) * CONSTANTE_SOLAR * dr * (
        ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws))


def mj_para_mm(valor_mj):
    """De MJ/m²/dia para mm/dia de água evaporada. FAO-56, eq. 20."""
    return 0.408 * valor_mj


def eto_hargreaves(tmax, tmin, ra_mm):
    """A evaporação de referência (ETo), em mm/dia. FAO-56, eq. 52 (Hargreaves-Samani); Ra em mm/dia."""
    if tmax < tmin:
        raise ValueError(f"A temperatura máxima ({tmax}) veio menor que a mínima ({tmin}): confira o dado do clima.")
    return 0.0023 * ((tmax + tmin) / 2 + 17.8) * math.sqrt(tmax - tmin) * ra_mm


def serie_do_json(bruto, inicio=INICIO_DA_SIMULACAO):
    """Da resposta da NASA POWER para a lista de dias (data, chuva, máxima, mínima, ETo), a partir de `inicio`.

    Dias sem dado (-999) no fim são cortados; no meio da série, é erro (a conta não inventa clima).
    """
    par = bruto["properties"]["parameter"]
    latitude = bruto["geometry"]["coordinates"][1]
    chuva, tmax, tmin = par["PRECTOTCORR"], par["T2M_MAX"], par["T2M_MIN"]
    dias, faltando = [], []
    data = inicio
    while data.strftime("%Y%m%d") in chuva:
        chave = data.strftime("%Y%m%d")
        valores = (chuva[chave], tmax.get(chave, SEM_DADO), tmin.get(chave, SEM_DADO))
        if SEM_DADO in valores:
            faltando.append(data)
        else:
            if faltando:
                raise ValueError("A série do clima tem dia sem dado no meio: " + faltando[0].isoformat()
                                 + ". Baixe a série de novo ou escolha outro começo.")
            ra = mj_para_mm(ra_mj(latitude, dia_do_ano(data)))
            dias.append(Dia(data, valores[0], valores[1], valores[2], eto_hargreaves(valores[1], valores[2], ra)))
        data += datetime.timedelta(days=1)
    if not dias:
        raise ValueError("A série do clima não tem nenhum dia com dado a partir de " + inicio.isoformat() + ".")
    return dias


def marca_dos_arquivos(*caminhos):
    """A hora da última mudança de cada arquivo (em nanossegundos; None se não existe).

    Entra na chave do que fica guardado na memória: arquivo baixado de novo é lido de novo, mesmo com o servidor
    ligado (sem isso, o "como está hoje" ficava preso ao último dia lido antes).
    """
    import os
    marcas = []
    for caminho in caminhos:
        try:
            marcas.append(os.stat(caminho).st_mtime_ns)
        except OSError:
            marcas.append(None)
    return tuple(marcas)


@functools.lru_cache(maxsize=8)
def _ler(caminho, inicio, marca=None):
    with open(caminho, encoding="utf-8") as arquivo:
        return tuple(serie_do_json(json.load(arquivo), inicio))


def ler_serie(pasta=PASTA_NASA_POWER, inicio=INICIO_DA_SIMULACAO):
    """A série guardada em data/orbita/nasa-power/, já com a ETo de cada dia."""
    caminho = str(Path(pasta) / "resposta.json")
    return list(_ler(caminho, inicio, marca_dos_arquivos(caminho)))


def ler_chuva_csv(caminho):
    """Um CSV `data,chuva_mm` (pode ter mais colunas): data -> chuva em mm, ou None no dia em branco."""
    import csv
    valores = {}
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            texto = (linha.get("chuva_mm") or "").strip()
            valores[datetime.date.fromisoformat(linha["data"].strip())] = float(texto) if texto else None
    return valores


@functools.lru_cache(maxsize=16)
def _serie_com_aviso(chuva, pasta_da_chuva, pasta_power=None, lugar=None, marca=None):
    dias = ler_serie() if pasta_power is None else ler_serie(pasta_power)
    if chuva == "power":
        return tuple(dias), ("A chuva de modelo da NASA POWER (PRECTOTCORR) fica só como comparação: em Rio Verde "
                             "ela fica bem abaixo da estação em terra do INMET de 2021 para cá (o comando validar "
                             "mostra safra por safra)." + ("" if lugar is None else f" Em {lugar} não há estação "
                                                           "conferida: vale o mesmo cuidado."),)
    if chuva not in FONTES_DE_CHUVA:
        raise ValueError(f"Fonte de chuva desconhecida: '{chuva}'. Use imerg, chirps, era5 ou power.")
    arquivo = Path(pasta_da_chuva) / f"{chuva}.csv"
    if not arquivo.exists():
        raise ValueError(f"A chuva '{chuva}' não está guardada: falta o arquivo {arquivo}.")
    valores = ler_chuva_csv(arquivo)
    pares = [(dia, valores.get(dia.data)) for dia in dias]
    cortados = 0
    while pares and pares[-1][1] is None:
        pares.pop()
        cortados += 1
    buracos = [dia.data for dia, valor in pares if valor is None]
    if buracos or not pares:
        raise ValueError(f"A chuva '{chuva}' tem {len(buracos)} dia(s) sem dado no meio da série (o primeiro: "
                         f"{buracos[0].isoformat() if buracos else 'todos'}). O motor não troca dia sem dado por "
                         "zero: escolha outra fonte de chuva ou baixe a série de novo.")
    avisos = []
    if cortados:
        avisos.append(f"A chuva desta fonte vai até {pares[-1][0].data.isoformat()}: os {cortados} dias seguintes da "
                      "série, sem dado de chuva, ficaram fora da conta (dia sem dado nunca vira zero).")
    if chuva == "imerg":
        avisos.append(f"O dia do IMERG é o UTC (começa 3 horas antes do dia de {lugar or 'Rio Verde'}); a "
                      "temperatura é do dia local. A chuva de um fim de tarde pode cair no dia seguinte da conta.")
    return tuple(dia._replace(chuva=valor) for dia, valor in pares), tuple(avisos)


def ler_serie_com_aviso(chuva="power", pasta_da_chuva=PASTA_DA_CHUVA, cidade_id=None, lugar=None):
    """A série do motor com a chuva da fonte pedida (a temperatura e a ETo são sempre da NASA POWER) e os avisos.

    `cidade_id`: a cidade (sem ela, Rio Verde, nas pastas de sempre); `lugar`: o nome dela, para os avisos.
    """
    if cidade_id in (None, CIDADE_DE_REFERENCIA):
        marca = marca_dos_arquivos(PASTA_NASA_POWER / "resposta.json", Path(pasta_da_chuva) / f"{chuva}.csv")
        dias, avisos = _serie_com_aviso(chuva, str(pasta_da_chuva), None, None, marca)
    else:
        pastas = pastas_da_cidade(cidade_id)
        if not (pastas["nasa_power"] / "resposta.json").exists():
            raise ValueError(f"O clima de '{cidade_id}' não está guardado: falta baixar (data/orbita/cidades/"
                             "baixar_cidade.py).")
        marca = marca_dos_arquivos(pastas["nasa_power"] / "resposta.json", pastas["chuva"] / f"{chuva}.csv")
        dias, avisos = _serie_com_aviso(chuva, str(pastas["chuva"]), str(pastas["nasa_power"]), lugar or cidade_id,
                                        marca)
    return list(dias), list(avisos)


def origem_da_serie(pasta=PASTA_NASA_POWER):
    """De onde veio a série: a fonte, o endereço da consulta e a hora em que foi baixada."""
    pasta = Path(pasta)
    return {"fonte": "NASA POWER (API diária, comunidade AG): chuva PRECTOTCORR, temperatura T2M_MAX e T2M_MIN",
            "consulta": (pasta / "consulta.txt").read_text(encoding="utf-8").strip(),
            "baixado_em": (pasta / "baixado-em.txt").read_text(encoding="utf-8").strip()}
