#!/usr/bin/env python3
# Gerado com IA (Claude). Órbita Rural (NASA Space Apps 2026).
"""Baixa a chuva do satélite (GPM IMERG V07, da NASA) dos últimos dias e guarda por dia, em mm, por cidade.

De onde vem: a cópia dos arquivos de meia em meia hora do IMERG V07 (Early e Late) que a dynamical.org mantém num
balde aberto da Amazon (s3://dynamical-nasa-imerg, ficha https://registry.opendata.aws/dynamical-nasa-imerg/), sem
login, licença CC BY 4.0. NÃO é um servidor da NASA: é uma cópia dos arquivos dela feita por terceiro.
O Early chega com umas 5 horas de atraso; o Late, com umas 15.

A conta e a regra do dia:
- o arquivo traz a taxa de chuva de cada meia hora em kg m-2 s-1, que é o mesmo que mm por segundo:
  chuva da meia hora (mm) = taxa x 1800 segundos;
- o rótulo de cada meia hora é o INÍCIO dela, em UTC (a série começa em 1998-01-01T00:00, como o 1º arquivo do
  IMERG; regra deduzida no teste de 2026-11-15, não lida na documentação da dynamical);
- o dia é o de Brasília (UTC-3, sem horário de verão): o dia D soma as 48 meias horas que começam de D 03:00 UTC a
  D+1 02:30 UTC. Meia hora das 02:30 UTC do dia 15 é 23:30 do dia 14 em Brasília: entra no dia 14;
- dia com menos de 48 meias horas com dado fica em branco (nunca vira zero); o dia de hoje fica fora, por estar
  incompleto.

Rodar de novo só acrescenta os dias novos e baixa outra vez os últimos 3 dias do arquivo (e o que estiver em branco
nos últimos 90), porque o Late chega depois do Early.

Precisa de quatro bibliotecas (icechunk, zarr, xarray e numpy; as versões estão em requisitos.txt), num ambiente
virtual FORA do repositório:
    python3 -m venv ~/.cache/orbita-rural/venv-chuva-do-dia
    ~/.cache/orbita-rural/venv-chuva-do-dia/bin/pip install -r data/orbita/chuva-do-dia/requisitos.txt
Como rodar (da raiz do repositório):
    ~/.cache/orbita-rural/venv-chuva-do-dia/bin/python -I data/orbita/chuva-do-dia/baixar_chuva_do_dia.py
    ... baixar_chuva_do_dia.py --cidade rio_verde                    (só uma cidade)
    ... baixar_chuva_do_dia.py --ponto -17.79 -50.92 --pasta SAIDA   (um ponto qualquer, numa pasta de fora)
Saída, por cidade: <cidade>/chuva-do-dia.csv (data, chuva_early_mm, chuva_late_mm) e <cidade>/fonte.json.
Quem lê depois é o ler.py, que é Python puro.
"""
import argparse
import csv
import datetime
import json
import os
import pathlib
import sys
import time

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import ler  # noqa: E402  (o leitor em Python puro, da mesma pasta)

# As mesmas coordenadas do motor (backend/orbita/motor.py, CIDADES). O test_baixar.py confere que continuam iguais.
CIDADES = {"rio_verde": {"nome": "Rio Verde (GO)", "latitude": -17.79, "longitude": -50.92},
           "jatai": {"nome": "Jataí (GO)", "latitude": -17.88, "longitude": -51.71},
           "silvania": {"nome": "Silvânia (GO)", "latitude": -16.66, "longitude": -48.61}}

VERSOES = ("early", "late")
VERSAO_DO_DADO = "GPM IMERG V07 (Early e Late, de meia em meia hora); conjunto da dynamical.org v0.1.0"
ENDERECO = "https://dynamical-nasa-imerg.s3.us-west-2.amazonaws.com/nasa-imerg-analysis-{versao}/v0.1.0.icechunk"
VARIAVEL = "precipitation_surface"
UNIDADE = "kg m-2 s-1"                      # = mm por segundo
SEGUNDOS_DA_MEIA_HORA = 1800
MEIAS_HORAS_DO_DIA = 48
UTC = datetime.timezone.utc
BRASILIA = datetime.timezone(datetime.timedelta(hours=-3))
DIAS = 90                                   # a primeira rodada baixa os últimos 90 dias
REFAZER = 3                                 # cada rodada baixa de novo os últimos 3 dias do arquivo
CONSULTAS_GUARDADAS = 400                   # o fonte.json guarda as últimas consultas (2 por rodada)
REGRA_DO_DIA = ("Dia de Brasília (UTC-3). O rótulo de cada meia hora é o início dela, em UTC. O dia D soma as 48 "
                "meias horas que começam de D 03:00 UTC a D+1 02:30 UTC. Dia com menos de 48 meias horas com dado "
                "fica em branco. O dia da consulta fica fora, por estar incompleto.")
CONTA = "chuva do dia (mm) = soma, nas 48 meias horas, da taxa (kg m-2 s-1 = mm por segundo) x 1800 segundos"


def agora_utc():
    return datetime.datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def em_uma_linha(erro):
    """O erro em uma linha curta, para o aviso na tela e para o fonte.json."""
    linhas = str(erro).strip().splitlines() or [""]
    return f"{type(erro).__name__}: {linhas[0][:200]}"


# ------------------------------------------------------------------ as contas (Python puro, com teste)
def dia_de_brasilia(inicio_utc):
    """O dia de Brasília em que cai a meia hora que começa em `inicio_utc` (um datetime em UTC, sem fuso)."""
    return (inicio_utc - datetime.timedelta(hours=3)).date()


def somar_por_dia(meias_horas):
    """De [(início em UTC, taxa em mm por segundo ou None)] para {dia de Brasília: mm ou None}.

    Só dia com as 48 meias horas com dado ganha valor; os outros ficam None (em branco no arquivo).
    """
    dias = {}
    for inicio, taxa in meias_horas:
        dias.setdefault(dia_de_brasilia(inicio), []).append(taxa)
    saida = {}
    for dia, taxas in dias.items():
        com_dado = [t for t in taxas if t is not None]
        saida[dia] = (round(sum(com_dado) * SEGUNDOS_DA_MEIA_HORA, 2) + 0.0
                      if len(com_dado) == MEIAS_HORAS_DO_DIA else None)
    return saida


def desde_quando(linhas, hoje, dias=DIAS, refazer=REFAZER):
    """O primeiro dia a baixar. Sem arquivo: `dias` dias antes de hoje. Com arquivo: os últimos `refazer` dias que
    ele tem, ou antes, se houver dia em branco (Early ou Late) nos últimos `dias` dias."""
    piso = hoje - datetime.timedelta(days=dias)
    com_early = [l["data"] for l in linhas or [] if l["early"] is not None]
    if not com_early:
        return piso
    inicio = max(com_early) - datetime.timedelta(days=refazer - 1)
    em_branco = [l["data"] for l in linhas if l["data"] >= piso and (l["early"] is None or l["late"] is None)]
    return min([inicio] + em_branco)


def juntar(linhas, novos, inicio, hoje):
    """Junta o arquivo de antes com o que acabou de ser baixado. `novos`: {"early": {dia: mm}, "late": {dia: mm}}.

    Antes de `inicio` nada muda. De `inicio` até ontem vale o valor novo; se o novo veio em branco, fica o de antes.
    O dia de hoje (e o que vier depois) fica fora. A lista sai sem buraco de data.
    """
    antes = {l["data"]: l for l in linhas or []}
    primeiro = min(list(antes) + [inicio])
    saida, dia = [], primeiro
    while dia < hoje:
        velho = antes.get(dia, {"early": None, "late": None})
        linha = {"data": dia, "early": velho["early"], "late": velho["late"]}
        if dia >= inicio:
            for versao in VERSOES:
                novo = novos.get(versao, {}).get(dia)
                if novo is not None:
                    linha[versao] = novo
        saida.append(linha)
        dia += datetime.timedelta(days=1)
    return saida


# ------------------------------------------------------------------ a leitura (precisa das quatro bibliotecas)
def abrir(versao):
    """Abre a cópia do IMERG (Early ou Late) da dynamical.org. Devolve (o conjunto, o snapshot, o endereço)."""
    import icechunk
    import xarray
    endereco = ENDERECO.format(versao=versao)
    sessao = icechunk.Repository.open(icechunk.http_storage(endereco)).readonly_session("main")
    conjunto = xarray.open_zarr(sessao.store, chunks=None)
    unidade = conjunto[VARIAVEL].attrs.get("units")
    if unidade != UNIDADE:
        raise RuntimeError(f"a unidade do arquivo mudou: esperava {UNIDADE!r} e veio {unidade!r}. A conta não vale.")
    return conjunto, sessao.snapshot_id, endereco


def ler_ponto(conjunto, latitude, longitude, inicio, hoje):
    """As meias horas do ponto, de `inicio` 03:00 UTC até a última que houver: [(início em UTC, mm/s ou None)]."""
    import numpy
    ponto = conjunto[VARIAVEL].sel(latitude=latitude, longitude=longitude, method="nearest")
    ate = (hoje + datetime.timedelta(days=1)).isoformat() + "T02:59"
    ponto = ponto.sel(time=slice(inicio.isoformat() + "T03:00", ate)).load()
    meias = [(datetime.datetime.strptime(str(t)[:16], "%Y-%m-%dT%H:%M"), None if numpy.isnan(v) else float(v))
             for t, v in zip(ponto.time.values, ponto.values)]
    return meias, [float(ponto.latitude), float(ponto.longitude)]


def baixar(pontos, hoje, dias=DIAS):
    """Baixa e grava cada ponto. `pontos`: {nome: {"latitude", "longitude", "pasta", "nome"}}. Devolve o resumo."""
    for p in pontos.values():
        p["linhas"] = ler.ler_linhas(p["pasta"].name, p["pasta"].parent)
        p["inicio"] = desde_quando(p["linhas"], hoje, dias)
        p["novos"], p["consultas"] = {}, []
    for versao in VERSOES:
        try:
            conjunto, snapshot, endereco = abrir(versao)
        except Exception as erro:                       # sem o Early não há o que gravar; sem o Late, segue
            if versao == "early":
                raise
            print(f"  O Late não abriu ({em_uma_linha(erro)}). Fica o que já estava guardado.")
            for p in pontos.values():
                p["consultas"].append({"versao": versao, "endereco": ENDERECO.format(versao=versao),
                                       "hora_utc": agora_utc(), "erro": em_uma_linha(erro)})
            continue
        for p in pontos.values():
            hora, t0 = agora_utc(), time.monotonic()
            meias, celula = ler_ponto(conjunto, p["latitude"], p["longitude"], p["inicio"], hoje)
            com_dado = [inicio for inicio, taxa in meias if taxa is not None]
            p["novos"][versao] = {dia: mm for dia, mm in somar_por_dia(meias).items() if dia < hoje}
            p["celula"] = celula
            p["consultas"].append({
                "versao": versao, "endereco": endereco, "hora_utc": hora, "snapshot": snapshot,
                "pedido_de": p["inicio"].isoformat() + "T03:00Z", "meias_horas_lidas": len(meias),
                "meias_horas_vazias": len(meias) - len(com_dado),
                "ultima_meia_hora_com_dado_inicio_utc": com_dado[-1].strftime("%Y-%m-%dT%H:%MZ") if com_dado else None,
                "segundos": round(time.monotonic() - t0, 1)})
    resumo = {}
    for nome, p in pontos.items():
        linhas = juntar(p["linhas"], p["novos"], p["inicio"], hoje)
        gravar(p, linhas)
        ultimo = {v: max((l["data"] for l in linhas if l[v] is not None), default=None) for v in VERSOES}
        resumo[nome] = {"dias_no_arquivo": len(linhas), "baixado_desde": p["inicio"], "ultimo_early": ultimo["early"],
                        "ultimo_late": ultimo["late"]}
    return resumo


def gravar(p, linhas):
    """Grava o CSV e o fonte.json do ponto. Escreve num arquivo ao lado e troca no fim: falha não estraga o de antes."""
    pasta = p["pasta"]
    pasta.mkdir(parents=True, exist_ok=True)
    texto = lambda mm: "" if mm is None else f"{mm:.2f}"  # noqa: E731
    provisorio = pasta / (ler.ARQUIVO + ".novo")
    with open(provisorio, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(ler.COLUNAS)
        for l in linhas:
            w.writerow([l["data"].isoformat(), texto(l["early"]), texto(l["late"])])
    os.replace(provisorio, pasta / ler.ARQUIVO)

    arquivo = pasta / "fonte.json"
    antes = json.loads(arquivo.read_text(encoding="utf-8")).get("consultas", []) if arquivo.exists() else []
    ultimo = {v: max((l["data"].isoformat() for l in linhas if l[v] is not None), default=None) for v in VERSOES}
    ficha = {
        "o_que_e": "Chuva por dia, em mm, do satélite GPM IMERG V07 (NASA/JAXA), nas versões Early e Late, somada "
                   "das meias horas no dia de Brasília. Sem login.",
        "de_onde_vem": "Cópia dos arquivos da NASA (GES DISC e PPS) mantida pela dynamical.org num balde aberto da "
                       "Amazon (s3://dynamical-nasa-imerg). Não é um servidor da NASA.",
        "ficha_do_conjunto": "https://registry.opendata.aws/dynamical-nasa-imerg/",
        "licenca": "CC BY 4.0", "citacao": "NASA IMERG from dynamical.org",
        "versao_do_dado": VERSAO_DO_DADO,
        "enderecos": {v: ENDERECO.format(versao=v) for v in VERSOES},
        "como_le": "icechunk.http_storage(endereço) -> readonly_session('main') -> xarray.open_zarr; variável "
                   f"{VARIAVEL}, o quadrado mais perto do ponto (sel method='nearest')",
        "conta": CONTA, "regra_do_dia": REGRA_DO_DIA,
        "ponto": {"nome": p.get("nome"), "latitude": p["latitude"], "longitude": p["longitude"],
                  "centro_do_quadrado_lido": p.get("celula")},
        "primeiro_dia": linhas[0]["data"].isoformat() if linhas else None,
        "ultimo_dia_com_dado": ultimo["early"], "ultimo_dia_com_dado_late": ultimo["late"],
        "dias_no_arquivo": len(linhas),
        "dias_em_branco": {v: sum(1 for l in linhas if l[v] is None) for v in VERSOES},
        "ultima_rodada_utc": p["consultas"][0]["hora_utc"] if p["consultas"] else None,
        "consultas": (antes + p["consultas"])[-CONSULTAS_GUARDADAS:]}
    provisorio = pasta / "fonte.json.novo"
    provisorio.write_text(json.dumps(ficha, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(provisorio, arquivo)


def main(argumentos=None):
    p = argparse.ArgumentParser(description="Baixa a chuva por dia do GPM IMERG V07 (cópia da dynamical.org).")
    p.add_argument("--cidade", choices=sorted(CIDADES), action="append", help="só esta cidade (pode repetir)")
    p.add_argument("--ponto", nargs=2, type=float, metavar=("LATITUDE", "LONGITUDE"), help="um ponto qualquer")
    p.add_argument("--pasta", help="com --ponto: a pasta onde gravar (fora das pastas das cidades)")
    p.add_argument("--dias", type=int, default=DIAS, help="quantos dias para trás na primeira rodada (padrão: 90)")
    p.add_argument("--hoje", help="AAAA-MM-DD, para testar; sem isso, vale o dia de hoje em Brasília")
    a = p.parse_args(argumentos)
    hoje = (datetime.date.fromisoformat(a.hoje) if a.hoje else datetime.datetime.now(BRASILIA).date())
    if a.ponto:
        if not a.pasta:
            p.error("com --ponto, diga também --pasta (onde gravar)")
        pasta = pathlib.Path(a.pasta).resolve()
        if pasta.parent == AQUI and pasta.name in CIDADES:
            p.error("essa pasta é a de uma cidade do motor: escolha outra para o ponto")
        pontos = {pasta.name: {"nome": None, "latitude": a.ponto[0], "longitude": a.ponto[1], "pasta": pasta}}
    else:
        pontos = {c: dict(CIDADES[c], pasta=AQUI / c) for c in (a.cidade or sorted(CIDADES))}
    t0 = time.monotonic()
    try:
        resumo = baixar(pontos, hoje, a.dias)
    except ImportError as erro:
        print(f"Falta uma biblioteca ({erro}). Rode com o Python do ambiente virtual (o comando está no LEIA-ME.md).",
              file=sys.stderr)
        return 3
    except Exception as erro:
        print(f"A chuva não foi baixada ({em_uma_linha(erro)}). O que já estava guardado não mudou. "
              "Tente de novo em alguns minutos.", file=sys.stderr)
        return 1
    ontem = hoje - datetime.timedelta(days=1)
    for nome, r in resumo.items():
        em_dia = "em dia" if r["ultimo_early"] == ontem else f"ATRASADO (ontem foi {ontem})"
        print(f"{nome}: {r['dias_no_arquivo']} dias no arquivo, baixado desde {r['baixado_desde']}; "
              f"último dia Early {r['ultimo_early']} ({em_dia}), Late {r['ultimo_late']}")
    print(f"Pronto em {round(time.monotonic() - t0)} s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
