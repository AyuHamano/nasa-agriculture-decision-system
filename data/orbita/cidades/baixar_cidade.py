#!/usr/bin/env python3
# Gerado com IA (Claude)
"""Baixa os dados de uma cidade nova para o motor do Órbita Rural e guarda o endereço e a hora de cada consulta.

O que baixa, para o ponto da cidade (tudo grátis e sem login):
  1. NASA POWER (API diária, comunidade AG, dia local): PRECTOTCORR, T2M_MAX e T2M_MIN  ->  <id>/nasa-power/
  2. A chuva do satélite GPM IMERG, pelo parâmetro IMERG_PRECTOT da NASA POWER (dia UTC)   ->  <id>/chuva/imerg.csv
  3. IBGE, Produção Agrícola Municipal (SIDRA): rendimento do milho de 2ª safra e da soja  ->  <id>/ibge/rendimento.csv
É o mesmo caminho usado para Rio Verde (a temperatura em data/orbita/nasa-power/, a chuva e o IBGE em
data/orbita/validacao/). Dia sem dado fica em branco no CSV e nunca vira zero.

Como rodar, de dentro desta pasta (data/orbita/cidades/):
    python3 -I baixar_cidade.py jatai "Jataí (GO)" -17.88 -51.71 5211909
    python3 -I baixar_cidade.py silvania "Silvânia (GO)" -16.66 -48.61 5220603
O último número é o código do município no IBGE (opcional: sem ele, o programa procura pelo nome).
"""
import csv
import datetime
import json
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
INICIO = "2014-07-01"                 # o motor começa a conta em 2014-07-01
FIM_DO_IMERG = "2026-10-31"           # o mesmo fim pedido para Rio Verde
POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"
SIDRA = "https://apisidra.ibge.gov.br/values"
MUNICIPIOS_DE_GOIAS = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/52/municipios"
PRODUTOS = [("milho_2a_safra", "839", "114254", "Milho (em grão) - 2ª safra"),
            ("soja", "1612", "2713", "Soja (em grão)")]
VARIAVEIS = {"112": "rendimento_kg_ha", "216": "area_colhida_ha", "214": "producao_t"}
PRIMEIRO_ANO = 2015


def agora():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def pegar(url, espera=180):
    pedido = urllib.request.Request(url, headers={"User-Agent": "orbita-rural/1.0 (python-urllib)"})
    with urllib.request.urlopen(pedido, timeout=espera) as resposta:
        return resposta.read()


def pegar_do_ibge(url):
    """As consultas ao IBGE vão pelo curl: nesta máquina a ligação do Python ao IBGE fica presa sem responder."""
    import subprocess
    return subprocess.run(["curl", "-s", "-f", "-m", "40", url], check=True, capture_output=True, timeout=50).stdout


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower()


def gravar_json(arquivo, coisa):
    arquivo.write_text(json.dumps(coisa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def baixar_power(pasta, latitude, longitude, fim):
    pasta.mkdir(parents=True, exist_ok=True)
    url = POWER + "?" + urllib.parse.urlencode([
        ("parameters", "PRECTOTCORR,T2M_MAX,T2M_MIN"), ("community", "AG"), ("longitude", str(longitude)),
        ("latitude", str(latitude)), ("start", INICIO.replace("-", "")), ("end", fim.replace("-", "")),
        ("format", "JSON"), ("time-standard", "LST")], safe=",")
    corpo = pegar(url)
    hora = agora()
    dados = json.loads(corpo.decode("utf-8"))
    serie = dados["properties"]["parameter"]["T2M_MAX"]
    (pasta / "resposta.json").write_bytes(corpo)
    (pasta / "consulta.txt").write_text(url + "\n", encoding="utf-8")
    (pasta / "baixado-em.txt").write_text(hora + "\n", encoding="utf-8")
    com_dado = [d for d in sorted(serie) if serie[d] != dados["header"]["fill_value"]]
    return {"endereco": url, "baixado_em": hora, "dias": len(serie), "ultimo_dia_com_dado": com_dado[-1],
            "ponto_devolvido": dados["geometry"]["coordinates"], "fontes": dados["header"].get("sources")}


def baixar_imerg(pasta, latitude, longitude, lugar):
    pasta.mkdir(parents=True, exist_ok=True)
    url = POWER + "?" + urllib.parse.urlencode([
        ("parameters", "IMERG_PRECTOT"), ("community", "AG"), ("longitude", str(longitude)),
        ("latitude", str(latitude)), ("start", INICIO.replace("-", "")), ("end", FIM_DO_IMERG.replace("-", "")),
        ("format", "JSON"), ("time-standard", "UTC")])
    corpo = pegar(url)
    hora = agora()
    dados = json.loads(corpo.decode("utf-8"))
    serie, vazio = dados["properties"]["parameter"]["IMERG_PRECTOT"], dados["header"]["fill_value"]
    sem_dado, com_dado = [], []
    with open(pasta / "imerg.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["data", "chuva_mm"])
        for d in sorted(serie):
            data, valor = f"{d[:4]}-{d[4:6]}-{d[6:8]}", serie[d]
            if valor == vazio or valor is None or valor < 0:
                sem_dado.append(data)
                w.writerow([data, ""])
            else:
                com_dado.append(data)
                w.writerow([data, repr(valor)])
    registro = {
        "o_que_e": "Endereço exato e hora da consulta que gerou o CSV desta pasta.",
        "ponto": {"latitude": latitude, "longitude": longitude, "lugar": lugar},
        "periodo_pedido": {"inicio": INICIO, "fim": FIM_DO_IMERG},
        "fontes": {"imerg": {
            "arquivo": "imerg.csv",
            "o_que_e": "GPM IMERG: chuva estimada por satélites (a missão GPM, da NASA e da JAXA), servida por ponto "
                       "pela NASA POWER no parâmetro IMERG_PRECTOT.",
            "consultas": [{"endereco": url, "baixado_em": hora}],
            "cabecalho_da_resposta": dados.get("header"), "avisos_da_resposta": dados.get("messages"),
            "ponto_devolvido": dados.get("geometry", {}).get("coordinates"),
            "horario": "UTC (o dia vai das 21h do dia anterior às 21h do dia, em Brasília)",
            "dias": len(serie), "dias_sem_dado": len(sem_dado),
            "primeiro_dia": com_dado[0] if com_dado else None,
            "ultimo_dia_com_dado": com_dado[-1] if com_dado else None}}}
    gravar_json(pasta / "fonte.json", registro)
    return {"endereco": url, "baixado_em": hora, "dias": len(serie), "dias_sem_dado": len(sem_dado),
            "ultimo_dia_com_dado": com_dado[-1] if com_dado else None}


def codigo_do_municipio(nome):
    """O código do IBGE do município de Goiás com esse nome (sem contar acento), e a consulta que o achou."""
    corpo = pegar_do_ibge(MUNICIPIOS_DE_GOIAS)
    hora = agora()
    alvo = sem_acento(nome.split("(")[0].strip())
    for municipio in json.loads(corpo.decode("utf-8")):
        if sem_acento(municipio["nome"]) == alvo:
            return str(municipio["id"]), municipio["nome"], {"endereco": MUNICIPIOS_DE_GOIAS, "baixado_em": hora}
    raise RuntimeError(f"o IBGE não tem município de Goiás com o nome '{nome}'")


def baixar_ibge(pasta, nome, codigo=None):
    """`codigo`: o código do IBGE do município, se já for conhecido (a resposta confere o nome); sem ele, procura."""
    pasta.mkdir(parents=True, exist_ok=True)
    if codigo is None:
        codigo, nome_no_ibge, consulta_do_codigo = codigo_do_municipio(nome)
        consultas = [dict(consulta_do_codigo, para_que="achar o código do município")]
    else:
        nome_no_ibge, consultas = nome.split("(")[0].strip(), []
    linhas, conferidos = {}, {}
    for produto, tabela, categoria, nome_esperado in PRODUTOS:
        url = f"{SIDRA}/t/{tabela}/n6/{codigo}/v/216,214,112/p/all/c81/{categoria}"
        corpo = pegar_do_ibge(url)
        hora = agora()
        registros = json.loads(corpo.decode("utf-8"))[1:]
        for r in registros:
            if r["D1C"] != codigo or sem_acento(nome_no_ibge) not in sem_acento(r["D1N"]):
                raise RuntimeError(f"município inesperado na resposta: {r['D1C']} {r['D1N']}")
            if r["D4C"] != categoria or r["D4N"] != nome_esperado:
                raise RuntimeError(f"produto inesperado: {r['D4C']} {r['D4N']}")
            ano, valor = int(r["D3C"]), r["V"]
            if ano >= PRIMEIRO_ANO:   # o IBGE usa "...", "-" e "X" para sem dado, zero e sigilo: ficam em branco
                linhas.setdefault((ano, produto), {})[VARIAVEIS[r["D2C"]]] = (
                    valor if valor.replace(".", "", 1).isdigit() else "")
        conferidos[produto] = {"tabela": tabela, "categoria": categoria, "nome_da_categoria_na_resposta": nome_esperado,
                               "municipio_na_resposta": registros[0]["D1N"] if registros else None}
        consultas.append({"produto": produto, "endereco": url, "baixado_em": hora})
    ordem = {p[0]: i for i, p in enumerate(PRODUTOS)}
    chaves = sorted(linhas, key=lambda k: (ordem[k[1]], k[0]))
    with open(pasta / "rendimento.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ano", "produto", "rendimento_kg_ha", "area_colhida_ha", "producao_t"])
        for ano, produto in chaves:
            v = linhas[(ano, produto)]
            w.writerow([ano, produto, v.get("rendimento_kg_ha", ""), v.get("area_colhida_ha", ""),
                        v.get("producao_t", "")])
    com_rendimento = sorted(ano for (ano, produto), v in linhas.items()
                            if produto == "milho_2a_safra" and v.get("rendimento_kg_ha"))
    gravar_json(pasta / "fonte.json", {
        "o_que_e": "IBGE, Produção Agrícola Municipal (PAM), pela API do SIDRA: o que o município colheu por ano.",
        "arquivo": "rendimento.csv", "municipio": {"codigo": codigo, "nome": nome_no_ibge + " (GO)"},
        "consultas": consultas, "codigos_conferidos_na_resposta": conferidos,
        "anos_com_rendimento_do_milho_de_2a_safra": com_rendimento})
    return {"codigo": codigo, "anos_com_rendimento_do_milho_de_2a_safra": com_rendimento}


def main(argv=None):
    argumentos = sys.argv[1:] if argv is None else list(argv)
    if len(argumentos) not in (4, 5):
        print(__doc__, file=sys.stderr)
        return 2
    cidade, nome, latitude, longitude = argumentos[0], argumentos[1], float(argumentos[2]), float(argumentos[3])
    codigo = argumentos[4] if len(argumentos) == 5 else None
    pasta = AQUI / cidade
    fim = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()
    resumo = {"cidade_id": cidade, "nome": nome, "latitude": latitude, "longitude": longitude}
    for rotulo, baixar in (("nasa_power", lambda: baixar_power(pasta / "nasa-power", latitude, longitude, fim)),
                           ("imerg", lambda: baixar_imerg(pasta / "chuva", latitude, longitude, nome)),
                           ("ibge", lambda: baixar_ibge(pasta / "ibge", nome, codigo))):
        try:
            resumo[rotulo] = baixar()
        except Exception as erro:   # uma fonte fora do ar não impede as outras; o resumo diz qual faltou
            resumo[rotulo] = {"erro": f"{type(erro).__name__}: {erro}"}
        print(rotulo, json.dumps(resumo[rotulo], ensure_ascii=False)[:400], flush=True)
    gravar_json(pasta / "baixado.json", resumo)
    return 1 if any("erro" in resumo[r] for r in ("nasa_power", "imerg")) else 0


if __name__ == "__main__":
    sys.exit(main())
