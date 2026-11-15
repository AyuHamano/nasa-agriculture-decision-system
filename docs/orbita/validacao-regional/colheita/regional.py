#!/usr/bin/env python3
# Gerado com IA (Claude)
"""O teste regional: a falta de água do milho safrinha, na conta do motor, acompanha a colheita do IBGE em Goiás?

O método foi fixado antes de ver os resultados (em 2026-11-15; as escolhas de detalhe
estão no LEIA-ME.md, seção "O método", e também foram fixadas antes de rodar a conta):
1. as cidades: os 20 municípios de Goiás com a maior área colhida de milho 2ª safra (média de 2016 a 2025, SIDRA,
   tabela 839, categoria 114254), entre os que têm rendimento nos 10 anos; Rio Verde, Jataí e Silvânia à parte se
   não estiverem na lista;
2. o ponto: a sede do município, na base de Localidades do IBGE (2022);
3. os dados: NASA POWER diária (T2M_MAX, T2M_MIN e PRECTOTCORR no dia local; IMERG_PRECTOT no dia UTC), de 2014-07-01
   a 2025-12-31, como o data/orbita/cidades/baixar_cidade.py do motor faz; a colheita pelo SIDRA;
4. a conta: a do motor, sem mudar nada (rotação de hoje, terra média, o calendário e os parâmetros de hoje, a chuva
   IMERG), as 10 safras de 2015-16 a 2024-25; o número é o falta_relativa_pct do milho;
5. as medidas (a) a (d); 6. a checagem de sensibilidade (a soja 15 dias mais tarde), à parte.

Como rodar (Python 3, só a biblioteca padrão; o motor vem da cópia do repositório do time):
    python3 -I regional.py baixar      # baixa tudo de novo (uns 3 minutos; uma consulta por vez)
    python3 -I regional.py calcular    # a conta e as medidas, a partir do que está em dados/
    python3 -I regional.py tudo        # as duas coisas
O caminho do motor: a variável ORBITA_REPO, ou a raiz deste repositório (a pasta backend/).
"""
import csv
import datetime
import gzip
import hashlib
import json
import os
import random
import statistics
import struct
import subprocess
import sys
import tempfile
import time
import urllib.parse
import zipfile
from math import comb
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DADOS = AQUI / "dados"
BRUTO = DADOS / "bruto"
RESULTADOS = AQUI / "resultados"
REPO = Path(os.environ.get("ORBITA_REPO", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(REPO / "backend"))
from orbita import balanco, clima, motor, parametros, rotacoes, validar   # noqa: E402

INICIO, FIM = "2014-07-01", "2025-12-31"
ANOS = list(range(2016, 2026))                      # o ano N do IBGE é a safra (N-1)/N
SAFRAS = list(balanco.SAFRAS_DO_ESTUDO)             # 2015-16 a 2024-25
QUANTAS = 20
POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"
SIDRA = ("https://apisidra.ibge.gov.br/values/t/839/n6/in%20n3%2052/v/216,112/p/"
         + ",".join(map(str, ANOS)) + "/c81/114254")
LOCALIDADES = ("https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/localidades/"
               "Localidades_do_Brasil/2022/Localidades_Brasil_shp.zip")
AS_TRES = {"5218805": "Rio Verde", "5211909": "Jataí", "5220603": "Silvânia"}
PAUSA_S = 2.0
PERMUTACOES = 10000
SEMENTE = 20261115
PLANTIO_MAIS_TARDE = "2021-10-30"                   # o de costume é 15/10; 15 dias mais tarde (só o mês e o dia contam)


def agora():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def curl(url, espera=300):
    """Pelo curl, como o baixar_cidade.py faz com o IBGE (nesta máquina o Python fica preso no IBGE)."""
    return subprocess.run(["curl", "-s", "-f", "-L", "-m", str(espera), "-A", "orbita-rural/1.0 (curl)", url],
                          check=True, capture_output=True, timeout=espera + 20).stdout


def gravar_json(arquivo, coisa):
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps(coisa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def gravar_csv(arquivo, cabecalho, linhas):
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with open(arquivo, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cabecalho)
        w.writerows(linhas)


def numero(texto):
    """O SIDRA usa "...", "-" e "X" para sem dado, zero e sigilo: tudo isso vira None."""
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- 1. as cidades (SIDRA, tabela 839)
def baixar_sidra(registro):
    corpo = curl(SIDRA, 90)
    hora = agora()
    BRUTO.mkdir(parents=True, exist_ok=True)
    (BRUTO / "sidra-839-goias.json.gz").write_bytes(gzip.compress(corpo))
    registro["consultas"].append({"o_que": "SIDRA, tabela 839 (milho 2ª safra), todos os municípios de Goiás, "
                                           "área colhida (216) e rendimento (112), 2016 a 2025",
                                  "endereco": SIDRA, "baixado_em": hora, "arquivo": "dados/bruto/sidra-839-goias.json.gz"})


def ler_sidra():
    registros = json.loads(gzip.decompress((BRUTO / "sidra-839-goias.json.gz").read_bytes()).decode("utf-8"))[1:]
    tabela = {}
    for r in registros:
        if r["D4C"] != "114254" or r["D4N"] != "Milho (em grão) - 2ª safra":
            raise RuntimeError(f"produto inesperado na resposta do SIDRA: {r['D4C']} {r['D4N']}")
        cidade = tabela.setdefault(r["D1C"], {"nome": r["D1N"], "area": {}, "rendimento": {}})
        chave = {"216": "area", "112": "rendimento"}[r["D2C"]]
        cidade[chave][int(r["D3C"])] = numero(r["V"])
    return tabela


def escolher_cidades(tabela):
    """As 20 de maior área colhida média (2016 a 2025) entre as que têm rendimento (acima de zero) nos 10 anos."""
    completas = []
    for codigo, c in tabela.items():
        if all((c["rendimento"].get(a) or 0) > 0 for a in ANOS):
            area = statistics.mean(c["area"].get(a) or 0.0 for a in ANOS)
            completas.append((codigo, c["nome"], area))
    completas.sort(key=lambda x: (-x[2], x[0]))
    return completas[:QUANTAS], completas, len(tabela)


# ---------------------------------------------------------------- 2. a sede de cada cidade (IBGE, Localidades 2022)
def ler_dbf(caminho):
    with open(caminho, "rb") as f:
        n, tamanho_do_cabecalho, tamanho_da_linha = struct.unpack("<IHH", f.read(32)[4:12])
        campos = []
        while True:
            d = f.read(32)
            if d[0] == 0x0D:
                break
            campos.append((d[:11].split(b"\0")[0].decode(), d[16]))
        f.seek(tamanho_do_cabecalho)
        for _ in range(n):
            linha, pos, saida = f.read(tamanho_da_linha), 1, {}
            for nome, largura in campos:
                saida[nome] = linha[pos:pos + largura].decode("utf-8", errors="replace").strip()
                pos += largura
            yield saida


def baixar_sedes(registro):
    with tempfile.TemporaryDirectory() as pasta:
        arquivo = Path(pasta) / "localidades.zip"
        corpo = curl(LOCALIDADES, 300)
        hora = agora()
        arquivo.write_bytes(corpo)
        with zipfile.ZipFile(arquivo) as z:
            nome_dbf = [n for n in z.namelist() if n.lower().endswith(".dbf")][0]
            z.extract(nome_dbf, pasta)
        linhas = [r for r in ler_dbf(Path(pasta) / nome_dbf)
                  if r["CD_UF"] == "52" and r["SCT_LOCALI"] == "Sede Municipal"]
    gravar_csv(DADOS / "sedes-goias-ibge-2022.csv",
               ["codigo", "municipio", "localidade", "categoria", "latitude", "longitude"],
               [[r["CD_MUN"], r["NM_MUN"], r["NM_LOCALID"], r["SCT_LOCALI"], r["LAT_LOCALI"], r["LONG_LOCAL"]]
                for r in sorted(linhas, key=lambda r: r["CD_MUN"])])
    registro["consultas"].append({"o_que": "IBGE, Base de Localidades 2022 (shapefile do Brasil): as sedes municipais "
                                           "de Goiás (categoria 'Sede Municipal'), latitude e longitude",
                                  "endereco": LOCALIDADES, "baixado_em": hora, "sha256": hashlib.sha256(corpo).hexdigest(),
                                  "bytes": len(corpo), "arquivo": "dados/sedes-goias-ibge-2022.csv (só Goiás)"})


def ler_sedes():
    with open(DADOS / "sedes-goias-ibge-2022.csv", encoding="utf-8") as f:
        return {r["codigo"]: r for r in csv.DictReader(f)}


# ---------------------------------------------------------------- 3. o clima (NASA POWER), como o baixar_cidade.py
def url_power(parametros_, latitude, longitude, padrao):
    return POWER + "?" + urllib.parse.urlencode([
        ("parameters", parametros_), ("community", "AG"), ("longitude", str(longitude)), ("latitude", str(latitude)),
        ("start", INICIO.replace("-", "")), ("end", FIM.replace("-", "")), ("format", "JSON"),
        ("time-standard", padrao)], safe=",")


def baixar_clima(codigo, latitude, longitude, registro):
    saida = {}
    for rotulo, params, padrao in (("power", "PRECTOTCORR,T2M_MAX,T2M_MIN", "LST"), ("imerg", "IMERG_PRECTOT", "UTC")):
        url = url_power(params, latitude, longitude, padrao)
        for tentativa in range(3):
            try:
                corpo = curl(url, 300)
                break
            except subprocess.CalledProcessError:
                if tentativa == 2:
                    raise
                time.sleep(10)
        hora = agora()
        dados = json.loads(corpo.decode("utf-8"))
        (BRUTO / f"{codigo}-{rotulo}.json.gz").write_bytes(gzip.compress(corpo))
        saida[rotulo] = {"endereco": url, "baixado_em": hora, "arquivo": f"dados/bruto/{codigo}-{rotulo}.json.gz",
                         "ponto_devolvido": dados.get("geometry", {}).get("coordinates"),
                         "fontes": dados.get("header", {}).get("sources")}
        time.sleep(PAUSA_S)
    registro["clima"][codigo] = saida


def serie_da_cidade(codigo):
    """Os dias do motor (data, chuva, máxima, mínima, ETo) com a chuva IMERG, pelas mesmas regras do motor.

    A temperatura e a ETo: clima.serie_do_json (Hargreaves, a latitude devolvida pela NASA POWER). A chuva IMERG
    entra no lugar da chuva de modelo como no clima._serie_com_aviso: dia sem dado no fim é cortado, no meio é erro.
    """
    bruto = json.loads(gzip.decompress((BRUTO / f"{codigo}-power.json.gz").read_bytes()))
    dias = clima.serie_do_json(bruto)
    imerg = json.loads(gzip.decompress((BRUTO / f"{codigo}-imerg.json.gz").read_bytes()))
    serie, vazio = imerg["properties"]["parameter"]["IMERG_PRECTOT"], imerg["header"]["fill_value"]
    valores = {}
    for d, v in serie.items():   # o mesmo filtro do baixar_cidade.py: o vazio, None ou negativo ficam sem dado
        valores[datetime.date(int(d[:4]), int(d[4:6]), int(d[6:8]))] = (
            None if v == vazio or v is None or v < 0 else float(repr(v)))
    return trocar_a_chuva(dias, valores)


def trocar_a_chuva(dias, valores):
    pares = [(dia, valores.get(dia.data)) for dia in dias]
    while pares and pares[-1][1] is None:
        pares.pop()
    buracos = [dia.data for dia, valor in pares if valor is None]
    if buracos or not pares:
        raise ValueError(f"a chuva IMERG tem {len(buracos)} dia(s) sem dado no meio da série")
    return [dia._replace(chuva=valor) for dia, valor in pares]


# ---------------------------------------------------------------- 4. a conta do motor
def faltas_do_milho(dias, par, plantio=None):
    """safra -> falta de água do milho em % do que ele pediu (o falta_relativa_pct do motor, sem arredondar)."""
    cal = rotacoes.calendario(par, plantio)
    numeros = balanco.numeros_por_safra(balanco.simular(dias, False, par, "media", cal=cal))
    return {s: numeros[s]["milho"]["falta_relativa_pct"] for s in SAFRAS}


def conferir_contra_o_motor(par):
    """A conta deste programa, nos dados guardados do motor, contra a resposta do motor (arredondada a 1 casa)."""
    saida = {}
    for cidade in ("rio_verde", "jatai", "silvania"):
        dias, _ = clima.ler_serie_com_aviso("imerg", cidade_id=cidade, lugar=cidade)
        daqui = faltas_do_milho(dias, par)
        resposta = motor.responder({"cidade_id": cidade, "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media"})
        do_motor = {s: resposta["rotacoes"]["atual"]["safras"][s]["milho"]["falta_relativa_pct"] for s in SAFRAS}
        rend = motor.ler_rendimento_do_milho(clima.pastas_da_cidade(cidade)["ibge"])
        saida[cidade] = {"iguais": all(motor.r1(daqui[s]) == do_motor[s] for s in SAFRAS),
                         "spearman_nos_dados_guardados": validar.spearman([daqui[s] for s in SAFRAS],
                                                                          [rend[s] for s in SAFRAS]),
                         "falta_pct": {s: motor.r1(daqui[s]) for s in SAFRAS}}
    return saida


# ---------------------------------------------------------------- 5. as medidas
def teste_do_sinal(k, n):
    """k de n no sentido certo; sob o acaso, cada cidade tem 1/2. Devolve o p de um lado (k ou mais) e o dos dois."""
    cauda_de_cima = sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n
    cauda_de_baixo = sum(comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return cauda_de_cima, min(1.0, 2 * min(cauda_de_cima, cauda_de_baixo))


def pior_safra(rend):
    menor = min(rend[s] for s in SAFRAS)
    return [s for s in SAFRAS if rend[s] == menor][0]       # empate: a mais antiga, como no motor


def posto_na_falta(faltas, safra):
    """1 = a safra de maior falta de água das 10."""
    return 1 + sum(1 for s in SAFRAS if faltas[s] > faltas[safra])


def medida_a(faltas, rend):
    r = validar.spearman([faltas[s] for s in SAFRAS], [rend[s] for s in SAFRAS])
    pior = pior_safra(rend)
    posto = posto_na_falta(faltas, pior)
    return {"spearman": r, "pior_safra": pior, "rendimento_da_pior_kg_ha": rend[pior],
            "posto_da_pior_na_falta": posto, "pior_entre_as_3_de_maior_falta": posto <= 3}


def relativo(rend):
    mediana = statistics.median(rend[s] for s in SAFRAS)
    return {s: 100.0 * rend[s] / mediana for s in SAFRAS}


def medida_c(cidades, faltas, rend_rel, rng):
    """A correlação de postos sobre todas as cidade-safras e dois valores-p por permutação.

    O principal (fixado antes): embaralha a ordem das safras da falta de água, a MESMA ordem em todas as cidades
    (as cidades dividem o tempo de cada ano; embaralhar cada uma por si faria de conta que são 200 casos soltos).
    O outro, mostrado ao lado: embaralha as safras de cada cidade por si.
    """
    x = [faltas[c][s] for c in cidades for s in SAFRAS]
    y = [rend_rel[c][s] for c in cidades for s in SAFRAS]
    r = validar.spearman(x, y)
    postos_y = validar.postos(y)

    def r_com(ordem_por_cidade):
        xx = [faltas[c][SAFRAS[i]] for c, ordem in zip(cidades, ordem_por_cidade) for i in ordem]
        return validar.pearson(validar.postos(xx), postos_y)

    def p_de(gerar):
        mais_ou_igual, abs_mais_ou_igual = 0, 0
        for _ in range(PERMUTACOES):
            rp = r_com(gerar())
            mais_ou_igual += rp <= r
            abs_mais_ou_igual += abs(rp) >= abs(r)
        return (mais_ou_igual + 1) / (PERMUTACOES + 1), (abs_mais_ou_igual + 1) / (PERMUTACOES + 1)

    indices = list(range(len(SAFRAS)))

    def junto():
        ordem = indices[:]
        rng.shuffle(ordem)
        return [ordem] * len(cidades)

    def separado():
        saida = []
        for _ in cidades:
            ordem = indices[:]
            rng.shuffle(ordem)
            saida.append(ordem)
        return saida

    p1_junto, p2_junto = p_de(junto)
    p1_sep, p2_sep = p_de(separado)
    return {"spearman": r, "pares": len(x), "permutacoes": PERMUTACOES, "semente": SEMENTE,
            "p_um_lado_mesma_ordem_em_todas": p1_junto, "p_dois_lados_mesma_ordem_em_todas": p2_junto,
            "p_um_lado_cada_cidade_por_si": p1_sep, "p_dois_lados_cada_cidade_por_si": p2_sep}


def medida_d(cidades, faltas, rend_rel, rng):
    media_falta = {s: statistics.mean(faltas[c][s] for c in cidades) for s in SAFRAS}
    media_rend = {s: statistics.mean(rend_rel[c][s] for c in cidades) for s in SAFRAS}
    x, y = [media_falta[s] for s in SAFRAS], [media_rend[s] for s in SAFRAS]
    r = validar.spearman(x, y)
    mais_ou_igual = abs_mais_ou_igual = 0
    for _ in range(PERMUTACOES):
        xx = x[:]
        rng.shuffle(xx)
        rp = validar.spearman(xx, y)
        mais_ou_igual += rp <= r
        abs_mais_ou_igual += abs(rp) >= abs(r)
    pior = min(SAFRAS, key=lambda s: (media_rend[s], s))
    return {"spearman": r, "p_um_lado": (mais_ou_igual + 1) / (PERMUTACOES + 1),
            "p_dois_lados": (abs_mais_ou_igual + 1) / (PERMUTACOES + 1), "pior_safra_regional": pior,
            "posto_da_pior_na_falta": posto_na_falta(media_falta, pior),
            "por_safra": {s: {"falta_media_pct": media_falta[s], "rendimento_relativo_medio_pct": media_rend[s]}
                          for s in SAFRAS}}


def sem_uma_safra(cidades, faltas, rend, fora, rng):
    """Conferência pedida DEPOIS de ver os números (não é do método fixado): as medidas (b) e (d) sem uma safra.

    Entrou porque a pior safra é a mesma (2015-16) nas 20 cidades: mostra quanto do resultado vem só dela.
    """
    resto = [s for s in SAFRAS if s != fora]
    rs = {c: validar.spearman([faltas[c][s] for s in resto], [rend[c][s] for s in resto]) for c in cidades}
    negativas = sum(1 for c in cidades if rs[c] < 0)
    p1, p2 = teste_do_sinal(negativas, len(cidades))
    rel = {c: {s: 100.0 * rend[c][s] / statistics.median(rend[c][t] for t in resto) for s in resto} for c in cidades}
    x = [statistics.mean(faltas[c][s] for c in cidades) for s in resto]
    y = [statistics.mean(rel[c][s] for c in cidades) for s in resto]
    r = validar.spearman(x, y)
    conta = 0
    for _ in range(PERMUTACOES):
        xx = x[:]
        rng.shuffle(xx)
        conta += validar.spearman(xx, y) <= r
    return {"safra_fora": fora, "safras": len(resto), "negativas": negativas, "de": len(cidades),
            "p_um_lado_do_sinal": p1, "mediana_das_correlacoes": statistics.median(rs.values()),
            "d_spearman": r, "d_p_um_lado": (conta + 1) / (PERMUTACOES + 1), "por_cidade": rs}


def todas_as_medidas(cidades, faltas, rend):
    rng = random.Random(SEMENTE)
    por_cidade = {c: medida_a(faltas[c], rend[c]) for c in cidades}
    negativas = sum(1 for c in cidades if por_cidade[c]["spearman"] < 0)
    p1, p2 = teste_do_sinal(negativas, len(cidades))
    rend_rel = {c: relativo(rend[c]) for c in cidades}
    return {"a_por_cidade": por_cidade,
            "a_pior_entre_as_3": sum(1 for c in cidades if por_cidade[c]["pior_entre_as_3_de_maior_falta"]),
            "a_mediana_das_correlacoes": statistics.median(por_cidade[c]["spearman"] for c in cidades),
            "b": {"negativas": negativas, "de": len(cidades), "p_um_lado": p1, "p_dois_lados": p2},
            "c": medida_c(cidades, faltas, rend_rel, rng),
            "d": medida_d(cidades, faltas, rend_rel, rng)}, rend_rel


# ---------------------------------------------------------------- os passos
def baixar():
    BRUTO.mkdir(parents=True, exist_ok=True)
    registro = {"o_que_e": "O endereço e a hora de cada consulta deste teste.", "consultas": [], "clima": {}}
    baixar_sidra(registro)
    escolhidas, _, _ = escolher_cidades(ler_sidra())
    time.sleep(PAUSA_S)
    baixar_sedes(registro)
    sedes = ler_sedes()
    codigos = [c for c, _, _ in escolhidas] + [c for c in AS_TRES if c not in {x for x, _, _ in escolhidas}]
    for i, codigo in enumerate(codigos, 1):
        sede = sedes[codigo]
        print(f"[{i}/{len(codigos)}] {sede['municipio']} ({sede['latitude']}, {sede['longitude']})", flush=True)
        baixar_clima(codigo, float(sede["latitude"]), float(sede["longitude"]), registro)
        gravar_json(DADOS / "consultas.json", registro)
    gravar_json(DADOS / "consultas.json", registro)


def calcular():
    par = parametros.carregar()
    tabela = ler_sidra()
    escolhidas, completas, total = escolher_cidades(tabela)
    sedes = ler_sedes()
    codigos = [c for c, _, _ in escolhidas]
    a_parte = [c for c in AS_TRES if c not in codigos]
    area = {c: a for c, _, a in completas}
    gravar_csv(DADOS / "cidades.csv",
               ["ordem", "codigo_ibge", "municipio", "area_colhida_media_2016_2025_ha", "na_lista", "latitude_sede",
                "longitude_sede", "fonte_do_ponto"],
               [[i, c, tabela[c]["nome"], round(area.get(c, 0.0), 1), "sim" if c in codigos else "a parte",
                 sedes[c]["latitude"], sedes[c]["longitude"], "IBGE, Localidades 2022, Sede Municipal"]
                for i, c in enumerate(codigos + a_parte, 1)])
    rend = {c: {f"{a - 1}-{a % 100:02d}": tabela[c]["rendimento"][a] for a in ANOS} for c in codigos + a_parte}
    dias = {c: serie_da_cidade(c) for c in codigos + a_parte}
    resultado = {"cidades_de_goias_na_tabela": total, "com_rendimento_nos_10_anos": len(completas),
                 "escolhidas": codigos, "a_parte": a_parte, "nomes": {c: tabela[c]["nome"] for c in codigos + a_parte},
                 "area_media_ha": {c: area.get(c) for c in codigos + a_parte},
                 "conferencia_com_o_motor": conferir_contra_o_motor(par)}
    for rotulo, plantio in (("principal", None), ("sensibilidade_soja_15_dias_depois", PLANTIO_MAIS_TARDE)):
        faltas = {c: faltas_do_milho(dias[c], par, plantio) for c in codigos + a_parte}
        medidas, rend_rel = todas_as_medidas(codigos, faltas, rend)
        medidas["a_as_tres_a_parte"] = {c: medida_a(faltas[c], rend[c]) for c in a_parte}
        if plantio is None:   # depois de ver os números: sem a safra que é a pior em todas as cidades
            medidas["depois_de_ver_sem_2015_16"] = sem_uma_safra(codigos, faltas, rend, "2015-16",
                                                                 random.Random(SEMENTE + 1))
        resultado[rotulo] = medidas
        gravar_csv(RESULTADOS / f"cidade-safra-{rotulo}.csv",
                   ["codigo_ibge", "municipio", "na_lista", "safra", "ano_ibge", "falta_de_agua_do_milho_pct",
                    "rendimento_kg_ha", "rendimento_relativo_pct_da_mediana"],
                   [[c, tabela[c]["nome"], "sim" if c in codigos else "a parte", s, int(s[:4]) + 1,
                     round(faltas[c][s], 3), rend[c][s], round(100.0 * rend[c][s] / statistics.median(rend[c].values()), 2)]
                    for c in codigos + a_parte for s in SAFRAS])
        gravar_csv(RESULTADOS / f"por-cidade-{rotulo}.csv",
                   ["codigo_ibge", "municipio", "na_lista", "area_colhida_media_ha", "spearman", "pior_safra",
                    "rendimento_da_pior_kg_ha", "posto_da_pior_na_falta", "pior_entre_as_3_de_maior_falta"],
                   [[c, tabela[c]["nome"], "sim" if c in codigos else "a parte", round(area.get(c, 0.0), 1),
                     round(m["spearman"], 3), m["pior_safra"], m["rendimento_da_pior_kg_ha"], m["posto_da_pior_na_falta"],
                     "sim" if m["pior_entre_as_3_de_maior_falta"] else "não"]
                    for c, m in list(medidas["a_por_cidade"].items()) + list(medidas["a_as_tres_a_parte"].items())])
        gravar_csv(RESULTADOS / f"regional-por-safra-{rotulo}.csv",
                   ["safra", "falta_media_pct", "rendimento_relativo_medio_pct"],
                   [[s, round(v["falta_media_pct"], 2), round(v["rendimento_relativo_medio_pct"], 2)]
                    for s, v in medidas["d"]["por_safra"].items()])
    resultado["calculado_em"] = agora()
    gravar_json(RESULTADOS / "resultado.json", resultado)
    escrever_no_leia_me(resultado)
    mostrar(resultado)


def _br(x, casas=2, sinal=False):
    texto = f"{x:+.{casas}f}" if sinal else f"{x:.{casas}f}"
    return texto.replace("-", "−").replace(".", ",")


def _mil(x):
    return f"{x:,.0f}".replace(",", ".")


def _p(x):
    return "menor que 0,001" if x < 0.001 else _br(x, 3)


def tabelas(r):
    """As tabelas do LEIA-ME, feitas do resultado.json (nenhum número digitado à mão)."""
    saida = {}
    for rotulo, sufixo in (("principal", ""), ("sensibilidade_soja_15_dias_depois", "-sensibilidade")):
        m = r[rotulo]
        linhas = ["| # | município | área colhida média 2016-2025 (ha) | correlação (falta × rendimento) | pior safra no IBGE "
                  "(kg/ha) | posto dela na falta (1 = maior falta) | entre as 3 de maior falta? |",
                  "|---|---|---|---|---|---|---|"]
        for i, c in enumerate(r["escolhidas"], 1):
            a = m["a_por_cidade"][c]
            linhas.append(f"| {i} | {r['nomes'][c].replace(' - GO', '')} | {_mil(r['area_media_ha'][c])}"
                          + f" | {_br(a['spearman'], 2, True)} | {a['pior_safra']} ({_mil(a['rendimento_da_pior_kg_ha'])})"
                          + f" | {a['posto_da_pior_na_falta']}º | {'sim' if a['pior_entre_as_3_de_maior_falta'] else 'não'} |")
        saida["cidades" + sufixo] = "\n".join(linhas)
        b, c, d = m["b"], m["c"], m["d"]
        saida["medidas" + sufixo] = "\n".join([
            "| medida | o número |", "|---|---|",
            f"| (a) a correlação do meio das {b['de']} cidades (a mediana) | {_br(m['a_mediana_das_correlacoes'], 2, True)} |",
            f"| (a) cidades em que a pior safra está entre as 3 de maior falta | {m['a_pior_entre_as_3']} de {b['de']} |",
            f"| (b) cidades com correlação negativa (a conta no sentido certo) | {b['negativas']} de {b['de']} |",
            f"| (b) teste do sinal: a chance de {b['negativas']} ou mais de {b['de']} só pelo acaso | {_p(b['p_um_lado'])} "
            f"(dos dois lados: {_p(b['p_dois_lados'])}) |",
            f"| (c) a correlação de postos sobre as {c['pares']} cidade-safras (rendimento em % da mediana da cidade) | "
            f"{_br(c['spearman'], 2, True)} |",
            f"| (c) valor-p, a mesma ordem embaralhada em todas as cidades (o principal), {_mil(c['permutacoes'])} vezes"
            + f" | um lado {_p(c['p_um_lado_mesma_ordem_em_todas'])}; dois lados {_p(c['p_dois_lados_mesma_ordem_em_todas'])} |",
            f"| (c) valor-p, cada cidade embaralhada por si (mostrado ao lado) | um lado {_p(c['p_um_lado_cada_cidade_por_si'])}; "
            f"dois lados {_p(c['p_dois_lados_cada_cidade_por_si'])} |",
            f"| (d) a correlação de postos ano a ano (a média das cidades, 10 safras) | {_br(d['spearman'], 2, True)} |",
            f"| (d) valor-p por permutação ({_mil(PERMUTACOES)} vezes)"
            + f" | um lado {_p(d['p_um_lado'])}; dois lados {_p(d['p_dois_lados'])} |",
            f"| (d) a pior safra da região (o menor rendimento relativo médio) e o posto dela na falta média | "
            f"{d['pior_safra_regional']}, {d['posto_da_pior_na_falta']}º de 10 |"])
        saida["regional" + sufixo] = "\n".join(
            ["| safra | falta de água média do milho (%) | rendimento relativo médio (% da mediana da cidade) |",
             "|---|---|---|"] + [f"| {s} | {_br(v['falta_media_pct'], 1)} | {_br(v['rendimento_relativo_medio_pct'], 1)} |"
                                 for s, v in d["por_safra"].items()])
    e = r["principal"]["depois_de_ver_sem_2015_16"]
    saida["sem-2015-16"] = "\n".join([
        "| sem a safra 2015-16 (9 safras) | o número |", "|---|---|",
        f"| cidades com correlação negativa | {e['negativas']} de {e['de']} (teste do sinal, um lado: "
        f"{_p(e['p_um_lado_do_sinal'])}) |",
        f"| a correlação do meio das cidades (a mediana) | {_br(e['mediana_das_correlacoes'], 2, True)} |",
        f"| (d) ano a ano, 9 safras | {_br(e['d_spearman'], 2, True)} (valor-p de um lado: {_p(e['d_p_um_lado'])}) |"])
    conf = r["conferencia_com_o_motor"]
    p, s = r["principal"]["a_por_cidade"], r["sensibilidade_soja_15_dias_depois"]["a_por_cidade"]
    codigos = {"rio_verde": "5218805", "jatai": "5211909", "silvania": "5220603"}
    saida["as-tres"] = "\n".join(
        ["| cidade | antes deste teste | nos dados guardados do motor, a conta de hoje | neste teste (a sede do IBGE) | "
         "com a soja 15 dias depois | a conta deste programa = a do motor? |", "|---|---|---|---|---|---|"]
        + [f"| {nome} | {pedido} | {_br(conf[cid]['spearman_nos_dados_guardados'], 2, True)} | "
           f"{_br(p[codigos[cid]]['spearman'], 2, True) if codigos[cid] in p else '(fora da lista)'} | "
           f"{_br(s[codigos[cid]]['spearman'], 2, True) if codigos[cid] in s else '--'} | "
           f"{'sim, nas 10 safras' if conf[cid]['iguais'] else 'NÃO'} |"
           for cid, nome, pedido in (("rio_verde", "Rio Verde", "−0,52"), ("jatai", "Jataí", "−0,28"),
                                     ("silvania", "Silvânia", "−0,81"))])
    return saida


def escrever_no_leia_me(r):
    arquivo = AQUI / "LEIA-ME.md"
    if not arquivo.exists():
        return
    texto = arquivo.read_text(encoding="utf-8")
    for nome, tabela in tabelas(r).items():
        inicio, fim = f"<!-- TABELA:{nome} -->", f"<!-- FIM:{nome} -->"
        if inicio in texto and fim in texto:
            antes, resto = texto.split(inicio, 1)
            texto = antes + inicio + "\n" + tabela + "\n" + fim + resto.split(fim, 1)[1]
    arquivo.write_text(texto, encoding="utf-8")


def mostrar(r):
    for rotulo in ("principal", "sensibilidade_soja_15_dias_depois"):
        m = r[rotulo]
        print(f"== {rotulo}")
        for c, a in list(m["a_por_cidade"].items()) + list(m["a_as_tres_a_parte"].items()):
            print(f"  {r['nomes'][c][:28]:28} {a['spearman']:+.2f}  pior {a['pior_safra']} posto {a['posto_da_pior_na_falta']}")
        print("  b", m["b"], "| pior entre as 3:", m["a_pior_entre_as_3"], "| mediana r", round(m["a_mediana_das_correlacoes"], 3))
        print("  c", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m["c"].items()})
        print("  d", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m["d"].items() if k != "por_safra"})
    print("sem 2015-16", {k: v for k, v in r["principal"]["depois_de_ver_sem_2015_16"].items() if k != "por_cidade"})
    print("conferencia", {c:(v["iguais"], round(v["spearman_nos_dados_guardados"], 2))
                          for c, v in r["conferencia_com_o_motor"].items()})


if __name__ == "__main__":
    passo = sys.argv[1] if len(sys.argv) > 1 else ""
    if passo not in ("baixar", "calcular", "tudo"):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    if passo in ("baixar", "tudo"):
        baixar()
    if passo in ("calcular", "tudo"):
        calcular()
