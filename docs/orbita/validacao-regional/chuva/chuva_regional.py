#!/usr/bin/env python3
# Gerado com IA (Claude), 2026-11-15. Órbita Rural (NASA Space Apps 2026): a validação regional da chuva.
"""A chuva do satélite (IMERG_PRECTOT) e a chuva de modelo (PRECTOTCORR) da NASA POWER contra todas as
estações automáticas do INMET em Goiás (e, à parte, no Distrito Federal), de fevereiro a junho de 2016 a 2025.

Só a biblioteca padrão do Python 3. Rodar com `python3 -I`, de qualquer pasta:

    python3 -I chuva_regional.py testar     # confere as regras com casos feitos à mão
    python3 -I chuva_regional.py baixar     # zips do INMET (curl) -> arquivos de GO e DF; NASA POWER por estação
    python3 -I chuva_regional.py calcular   # as contas e os CSV desta pasta

O método está no LEIA-ME.md desta pasta (fixado antes de ver o resultado). Os dados grandes (os zips do INMET, os
arquivos das estações e as respostas da NASA POWER) ficam em ~/.cache/orbita-rural/dados-regionais/.
"""
import concurrent.futures
import csv
import datetime
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.expanduser("~/.cache/orbita-rural/dados-regionais")
ZIPS = os.path.join(CACHE, "zips")
INMET = os.path.join(CACHE, "inmet")
POWER = os.path.join(CACHE, "power")
FONTE = os.path.join(AQUI, "fonte.json")
RIO_VERDE_ANTES = os.path.normpath(os.path.join(AQUI, "..", "..", "..", "..", "data", "orbita", "validacao", "chuva", "inmet.csv"))

ENDERECO_INMET = "https://portal.inmet.gov.br/uploads/dadoshistoricos/{ano}.zip"
PAGINA_INMET = "https://portal.inmet.gov.br/dadoshistoricos"
BASE_POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"
ANOS = list(range(2016, 2026))          # as janelas: 1/fev a 30/jun de 2016 (safra 2015-16) a 2025 (safra 2024-25)
UFS = ("GO", "DF")
MIN_HORAS = 20                          # dia com menos horas com dado de chuva fica em branco
FUSO_HORAS = 3                          # Brasília = UTC-3
BRANCOS_TOLERADOS = 10                  # a regra do validar.py: mais de 10 dias em branco, a janela não é comparada
MIN_JANELAS = 5                         # a estação entra na conta com pelo menos 5 janelas comparáveis
FONTES = (("imerg", "IMERG_PRECTOT", "UTC"), ("power", "PRECTOTCORR", "LST"))
# a lista à parte (só o dado da estação decide)
ANO_ZEROS_DIAS, ANO_ZEROS_MM = 180, 100.0
JANELA_BAIXA_MM = 100.0
SECA_DIAS = 40
DIA_EXTREMO_MM = 200.0
MUDOU_KM = 5.0


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").upper()


def agora_local():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_de(dados):
    return hashlib.sha256(dados).hexdigest()


def sha256_arquivo(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def distancia_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def ler_fonte():
    if os.path.exists(FONTE):
        with open(FONTE, encoding="utf-8") as f:
            return json.load(f)
    return {"gerado_com": "IA (Claude)", "o_que_e": "De onde veio cada dado desta pasta: endereço, hora, tamanho e "
            "assinatura (sha256).", "inmet": {"pagina": PAGINA_INMET, "zips": {}}, "power": {}}


def gravar_fonte(fonte):
    with open(FONTE, "w", encoding="utf-8") as f:
        json.dump(fonte, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


# ------------------------------------------------------------------ ler o arquivo da estação

def numero(texto):
    """Número do arquivo (vírgula decimal). Vazio ou valor de falha (-9999) vira None, nunca zero."""
    t = (texto or "").strip()
    if not t:
        return None
    try:
        v = float(t.replace(",", "."))
    except ValueError:
        return None
    if v <= -9000:
        return None
    return v


def ler_bruto(caminho):
    """(cabeçalho, {data-hora UTC do rótulo: chuva ou None}). Hora repetida no arquivo: vale a primeira."""
    cab, horas, repetidas = {}, {}, 0
    with open(caminho, encoding="latin-1", newline="") as f:
        col = None
        for linha in csv.reader(f, delimiter=";"):
            if not linha:
                continue
            if col is None:
                chave = sem_acento(linha[0])
                if chave.startswith("DATA") and len(linha) > 5:
                    nomes = [sem_acento(c) for c in linha]
                    achou = [i for i, n in enumerate(nomes) if n.startswith("PRECIPITACAO TOTAL")]
                    if len(achou) != 1:
                        raise ValueError(f"{caminho}: a coluna da chuva apareceu {len(achou)} vezes")
                    col = achou[0]
                else:
                    cab[chave.rstrip(":").strip()] = linha[1].strip() if len(linha) > 1 else ""
                continue
            data = linha[0].strip().replace("/", "-")
            hora = "".join(c for c in linha[1] if c.isdigit()) if len(linha) > 1 else ""
            if len(data) != 10 or len(hora) < 2:
                continue
            quando = datetime.datetime.strptime(data, "%Y-%m-%d") + datetime.timedelta(hours=int(hora[:2]))
            chuva = numero(linha[col]) if col < len(linha) else None
            if chuva is not None and chuva < 0:
                chuva = None
            if quando in horas:
                repetidas += 1
                continue
            horas[quando] = chuva
    return cab, horas, repetidas


def por_dia(horas):
    """As horas (rótulo UTC no fim da hora) somadas por dia de Brasília; menos de 20 horas com dado: em branco."""
    recuo = datetime.timedelta(hours=FUSO_HORAS + 1)
    dias = {}
    for quando, chuva in horas.items():
        x = dias.setdefault((quando - recuo).date(), [0, 0.0])
        if chuva is not None:
            x[0] += 1
            x[1] += chuva
    return {d: (round(s, 1) if n >= MIN_HORAS else None) for d, (n, s) in dias.items()}


# ------------------------------------------------------------------ baixar

def baixar_zips(fonte):
    os.makedirs(ZIPS, exist_ok=True)
    for ano in ANOS:
        zip_ = os.path.join(ZIPS, f"{ano}.zip")
        if not os.path.exists(zip_):
            parte = zip_ + ".part"
            r = subprocess.run(["curl", "-sS", "--fail", "--http1.1", "-A", "Mozilla/5.0 (X11; Linux x86_64)",
                                "--max-time", "900", "-o", parte, ENDERECO_INMET.format(ano=ano)], timeout=920)
            if r.returncode != 0:
                print(f"{ano}: o zip não baixou (curl saiu com {r.returncode})")
                continue
            os.replace(parte, zip_)
        registro = fonte["inmet"]["zips"].get(str(ano))
        if registro and registro.get("zip_bytes") == os.path.getsize(zip_):
            continue
        registro = {
            "endereco": ENDERECO_INMET.format(ano=ano),
            "baixado_em_utc": datetime.datetime.fromtimestamp(os.path.getmtime(zip_), datetime.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "zip_bytes": os.path.getsize(zip_), "zip_sha256": sha256_arquivo(zip_), "arquivos": [],
        }
        destino = os.path.join(INMET, str(ano))
        os.makedirs(destino, exist_ok=True)
        with zipfile.ZipFile(zip_) as z:
            for nome in sorted(z.namelist()):
                base = os.path.basename(nome)
                partes = base.upper().split("_")
                if not base.upper().endswith(".CSV") or len(partes) < 4 or partes[2] not in UFS:
                    continue
                dados = z.read(nome)
                with open(os.path.join(destino, base), "wb") as f:
                    f.write(dados)
                registro["arquivos"].append({"arquivo_no_zip": nome, "guardado_em": f"inmet/{ano}/{base}",
                                             "bytes": len(dados), "sha256": sha256_de(dados)})
        fonte["inmet"]["zips"][str(ano)] = registro
        gravar_fonte(fonte)
        print(f"{ano}: {len(registro['arquivos'])} arquivos de GO e DF tirados do zip")


def estacoes_dos_arquivos(fonte):
    """codigo -> {uf, nome, arquivos: [(ano, caminho)], cabeçalhos por ano}."""
    est = {}
    for ano in ANOS:
        reg = fonte["inmet"]["zips"].get(str(ano))
        if not reg:
            continue
        for a in reg["arquivos"]:
            base = os.path.basename(a["guardado_em"])
            partes = base.split("_")
            uf, codigo = partes[2].upper(), partes[3].upper()
            x = est.setdefault(codigo, {"uf": uf, "arquivos": []})
            x["arquivos"].append((ano, os.path.join(CACHE, a["guardado_em"])))
    return est


def cabecalho(caminho):
    cab = {}
    with open(caminho, encoding="latin-1", newline="") as f:
        for linha in csv.reader(f, delimiter=";"):
            if not linha:
                continue
            chave = sem_acento(linha[0])
            if chave.startswith("DATA") and len(linha) > 5:
                break
            cab[chave.rstrip(":").strip()] = linha[1].strip() if len(linha) > 1 else ""
    return cab


def lugar(cab):
    return numero(cab.get("LATITUDE")), numero(cab.get("LONGITUDE")), numero(cab.get("ALTITUDE"))


def pegar(url, tentativas=4):
    erro = None
    for i in range(tentativas):
        try:
            pedido = urllib.request.Request(url, headers={"User-Agent": "validacao-regional/1.0 (python-urllib)"})
            with urllib.request.urlopen(pedido, timeout=180) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 (tenta de novo e diz no fim)
            erro = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"não baixou depois de {tentativas} tentativas: {type(erro).__name__} {erro}")


def url_power(parametro, padrao, lat, lon):
    return BASE_POWER + "?" + urllib.parse.urlencode([
        ("parameters", parametro), ("community", "AG"), ("longitude", f"{lon:.5f}"), ("latitude", f"{lat:.5f}"),
        ("start", f"{ANOS[0]}0101"), ("end", f"{ANOS[-1]}1231"), ("format", "JSON"), ("time-standard", padrao)])


def baixar_power(fonte):
    os.makedirs(POWER, exist_ok=True)
    est = estacoes_dos_arquivos(fonte)
    tarefas = []
    for codigo, x in sorted(est.items()):
        ano, caminho = max(x["arquivos"])
        lat, lon, _ = lugar(cabecalho(caminho))
        for chave, parametro, padrao in FONTES:
            bruto = os.path.join(POWER, f"{codigo}-{chave}.json")
            ja = fonte["power"].get(codigo, {}).get(chave)
            url = url_power(parametro, padrao, lat, lon)
            if ja and ja.get("endereco") == url and os.path.exists(bruto):
                continue
            tarefas.append((codigo, chave, parametro, url, bruto))

    def uma(t):
        codigo, chave, parametro, url, bruto = t
        corpo = pegar(url)
        hora = agora_local()
        d = json.loads(corpo.decode("utf-8"))
        if parametro not in d.get("properties", {}).get("parameter", {}):
            raise RuntimeError(f"{codigo} {parametro}: a resposta não trouxe o parâmetro: {d.get('messages')}")
        with open(bruto, "wb") as f:
            f.write(corpo)
        return codigo, chave, {"endereco": url, "baixado_em": hora, "bytes": len(corpo), "sha256": sha256_de(corpo),
                               "guardado_em": os.path.relpath(bruto, CACHE),
                               "fontes_no_cabecalho": d.get("header", {}).get("sources"),
                               "padrao_de_hora": d.get("header", {}).get("time_standard"),
                               "ponto_devolvido": d.get("geometry", {}).get("coordinates"),
                               "avisos": d.get("messages")}

    falhas = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for fut in concurrent.futures.as_completed([ex.submit(uma, t) for t in tarefas]):
            try:
                codigo, chave, reg = fut.result()
            except Exception as e:  # noqa: BLE001
                falhas.append(str(e))
                continue
            fonte["power"].setdefault(codigo, {})[chave] = reg
            gravar_fonte(fonte)
    print(f"NASA POWER: {len(tarefas) - len(falhas)} pedidos novos; {len(falhas)} falharam")
    for f in falhas:
        print("  ", f)


# ------------------------------------------------------------------ a conta

def dias_entre(a, b):
    d = a
    while d <= b:
        yield d
        d += datetime.timedelta(days=1)


def comparar_janela(estacao, fontes, inicio, fim):
    """A regra do validar.py: brancos na estação, e o % de cada fonte somada só nos dias com dado na estação."""
    dias = list(dias_entre(inicio, fim))
    validos = [d for d in dias if estacao.get(d) is not None]
    r = {"dias": len(dias), "brancos": len(dias) - len(validos),
         "estacao_mm": round(sum(estacao[d] for d in validos), 1)}
    r["passa_nos_brancos"] = r["brancos"] <= BRANCOS_TOLERADOS
    for nome, serie in fontes.items():
        r[f"{nome}_mm"] = r[f"{nome}_pct"] = None
        r[f"{nome}_dias"] = 0
        if not r["passa_nos_brancos"]:
            continue
        com = [d for d in validos if serie.get(d) is not None]
        medido = sum(estacao[d] for d in com)
        r[f"{nome}_dias"] = len(com)
        if len(com) >= len(validos) - BRANCOS_TOLERADOS and medido > 0:
            soma = sum(serie[d] for d in com)
            r[f"{nome}_mm"] = round(soma, 1)
            r[f"{nome}_pct"] = 100 * soma / medido
    r["comparavel"] = all(r[f"{nome}_pct"] is not None for nome in fontes)
    return r


def media(xs):
    return sum(xs) / len(xs) if xs else None


def resumo_da_estacao(janelas):
    comp = [j for j in janelas if j["comparavel"]]
    s = {"janelas_comparaveis": len(comp)}
    for nome in ("imerg", "power"):
        s[f"erro_{nome}"] = media([abs(j[f"{nome}_pct"] - 100) for j in comp])
        s[f"{nome}_pct_medio"] = media([j[f"{nome}_pct"] for j in comp])
        s[f"{nome}_ate_2020"] = media([j[f"{nome}_pct"] for j in comp if j["ano"] <= 2020])
        s[f"{nome}_2021_em_diante"] = media([j[f"{nome}_pct"] for j in comp if j["ano"] >= 2021])
    s["n_ate_2020"] = sum(1 for j in comp if j["ano"] <= 2020)
    s["n_2021_em_diante"] = sum(1 for j in comp if j["ano"] >= 2021)
    return s


def mediana(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def medidas(linhas):
    """(b), (c) e (d) sobre as estações que entram na conta."""
    m = {"n_estacoes": len(linhas)}
    m["satelite_mais_perto"] = sum(1 for e in linhas if e["erro_imerg"] < e["erro_power"])
    m["modelo_mais_perto"] = sum(1 for e in linhas if e["erro_power"] < e["erro_imerg"])
    m["empates"] = sum(1 for e in linhas if e["erro_power"] == e["erro_imerg"])
    m["mediana_erro_imerg"] = mediana([e["erro_imerg"] for e in linhas])
    m["mediana_erro_power"] = mediana([e["erro_power"] for e in linhas])
    for nome in ("power", "imerg"):
        antes = [e[f"{nome}_ate_2020"] for e in linhas if e[f"{nome}_ate_2020"] is not None]
        depois = [e[f"{nome}_2021_em_diante"] for e in linhas if e[f"{nome}_2021_em_diante"] is not None]
        pares = [(e[f"{nome}_ate_2020"], e[f"{nome}_2021_em_diante"]) for e in linhas
                 if e[f"{nome}_ate_2020"] is not None and e[f"{nome}_2021_em_diante"] is not None]
        m[nome] = {"mediana_ate_2020": mediana(antes), "n_ate_2020": len(antes),
                   "mediana_2021_em_diante": mediana(depois), "n_2021_em_diante": len(depois),
                   "estacoes_com_os_dois": len(pares),
                   "caiu_em": sum(1 for a, b in pares if b < a),
                   "mediana_da_diferenca": mediana([b - a for a, b in pares])}
    return m


def marcas(codigo, diario, versoes_de_lugar, janelas):
    """A lista à parte: só o dado da estação decide (nunca a NASA)."""
    saida = []
    for ano in ANOS:
        dias = [diario.get(d) for d in dias_entre(datetime.date(ano, 1, 1), datetime.date(ano, 12, 31))]
        com = [v for v in dias if v is not None]
        if len(com) >= ANO_ZEROS_DIAS and sum(com) < ANO_ZEROS_MM:
            saida.append(("ano_de_zeros", f"{ano}: {len(com)} dias com dado e {sum(com):.1f} mm no ano"))
        corrida = maior = 0
        for d in dias_entre(datetime.date(ano, 2, 1), datetime.date(ano, 3, 31)):
            v = diario.get(d)
            corrida = corrida + 1 if v == 0.0 else 0
            maior = max(maior, corrida)
        if maior >= SECA_DIAS:
            saida.append(("seca_longa_no_auge", f"{ano}: {maior} dias seguidos com 0,0 mm entre 1/fev e 31/mar"))
        extremos = [(d, diario[d]) for d in dias_entre(datetime.date(ano, 1, 1), datetime.date(ano, 12, 31))
                    if diario.get(d) is not None and diario[d] > DIA_EXTREMO_MM]
        for d, v in extremos:
            saida.append(("dia_extremo", f"{d.isoformat()}: {v:.1f} mm"))
    for j in janelas:
        if j["passa_nos_brancos"] and j["estacao_mm"] < JANELA_BAIXA_MM:
            saida.append(("janela_baixa", f"fev-jun de {j['ano']}: {j['estacao_mm']:.1f} mm na estação "
                                          f"({j['brancos']} dias em branco)"))
    maior_km = 0.0
    for i, a in enumerate(versoes_de_lugar):
        for b in versoes_de_lugar[i + 1:]:
            if None not in (a["latitude"], a["longitude"], b["latitude"], b["longitude"]):
                maior_km = max(maior_km, distancia_km(a["latitude"], a["longitude"], b["latitude"], b["longitude"]))
    if maior_km > MUDOU_KM:
        saida.append(("mudou_de_lugar", f"o cabeçalho mudou {maior_km:.1f} km entre os anos"))
    return saida


def ler_power(codigo, chave, fonte):
    reg = fonte["power"][codigo][chave]
    with open(os.path.join(CACHE, reg["guardado_em"]), "rb") as f:
        corpo = f.read()
    if sha256_de(corpo) != reg["sha256"]:
        raise SystemExit(f"{codigo} {chave}: o arquivo guardado mudou desde que baixou (sha256 diferente)")
    d = json.loads(corpo.decode("utf-8"))
    falha = d.get("header", {}).get("fill_value", -999.0)
    parametro = dict((c, p) for c, p, _ in FONTES)[chave]
    serie = {}
    for k, v in d["properties"]["parameter"][parametro].items():
        dia = datetime.date(int(k[:4]), int(k[4:6]), int(k[6:8]))
        serie[dia] = None if (v is None or v == falha or v < 0) else float(v)
    return serie


def f1(v, casas=1):
    return "" if v is None else f"{v:.{casas}f}"


def f2(v):
    return f1(v, 2)


def calcular():
    fonte = ler_fonte()
    est = estacoes_dos_arquivos(fonte)
    if not est:
        raise SystemExit("Não há arquivo das estações. Rode antes: python3 -I chuva_regional.py baixar")
    tabela, todas_janelas, lista_a_parte, diario_csv = [], [], [], []
    for codigo, x in sorted(est.items()):
        horas, versoes, repetidas, anos_com_arquivo = {}, [], 0, []
        for ano, caminho in sorted(x["arquivos"]):
            if not os.path.exists(caminho):
                raise SystemExit(f"falta {caminho}: rode o baixar")
            cab, h, rep = ler_bruto(caminho)
            repetidas += rep
            anos_com_arquivo.append(ano)
            for k, v in h.items():
                horas.setdefault(k, v)
            lat, lon, alt = lugar(cab)
            nome = next((v for k, v in cab.items() if k.startswith("ESTAC")), "")
            versao = {"latitude": lat, "longitude": lon, "altitude_m": alt, "nome": nome,
                      "codigo_no_cabecalho": cab.get("CODIGO (WMO)")}
            if not versoes or {k: v for k, v in versoes[-1].items() if k != "anos"} != versao:
                versao["anos"] = [ano]
                versoes.append(versao)
            else:
                versoes[-1]["anos"].append(ano)
        diario = por_dia(horas)
        if codigo not in fonte["power"] or any(c not in fonte["power"][codigo] for c, _, _ in FONTES):
            raise SystemExit(f"{codigo}: falta a NASA POWER; rode o baixar")
        series = {c: ler_power(codigo, c, fonte) for c, _, _ in FONTES}
        janelas = []
        for ano in ANOS:
            j = comparar_janela(diario, series, datetime.date(ano, 2, 1), datetime.date(ano, 6, 30))
            j.update({"codigo": codigo, "ano": ano, "safra": f"{ano - 1}-{str(ano)[2:]}"})
            janelas.append(j)
            for d in dias_entre(datetime.date(ano, 2, 1), datetime.date(ano, 6, 30)):
                diario_csv.append([codigo, d.isoformat(), f1(diario.get(d)), f1(series["imerg"].get(d), 2),
                                   f1(series["power"].get(d), 2)])
        todas_janelas.extend(janelas)
        ultima = versoes[-1]
        s = resumo_da_estacao(janelas)
        m = marcas(codigo, diario, versoes, janelas)
        for tipo, detalhe in m:
            lista_a_parte.append({"codigo": codigo, "nome": ultima["nome"], "uf": x["uf"], "motivo": tipo,
                                  "detalhe": detalhe})
        tabela.append({
            "codigo": codigo, "nome": ultima["nome"], "uf": x["uf"], "latitude": ultima["latitude"],
            "longitude": ultima["longitude"], "altitude_m": ultima["altitude_m"],
            "anos_com_arquivo": f"{min(anos_com_arquivo)}-{max(anos_com_arquivo)} ({len(anos_com_arquivo)})",
            "versoes_do_cabecalho": len(versoes), "horas_repetidas_ignoradas": repetidas,
            "entra_na_conta": s["janelas_comparaveis"] >= MIN_JANELAS, "na_lista_a_parte": bool(m),
            "ponto_power_imerg": fonte["power"][codigo]["imerg"]["ponto_devolvido"],
            "ponto_power_prectotcorr": fonte["power"][codigo]["power"]["ponto_devolvido"],
            "versoes": versoes, **s})

    # os CSV
    campos_tab = ["codigo", "nome", "uf", "latitude", "longitude", "altitude_m", "anos_com_arquivo",
                  "janelas_comparaveis", "entra_na_conta", "na_lista_a_parte", "erro_imerg", "erro_power",
                  "imerg_pct_medio", "power_pct_medio", "power_ate_2020", "power_2021_em_diante", "imerg_ate_2020",
                  "imerg_2021_em_diante", "n_ate_2020", "n_2021_em_diante", "versoes_do_cabecalho",
                  "horas_repetidas_ignoradas"]
    with open(os.path.join(AQUI, "estacoes.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(campos_tab)
        for e in tabela:
            w.writerow([f1(e[c]) if isinstance(e[c], float) and c not in ("latitude", "longitude") else
                        ("sim" if e[c] is True else "não" if e[c] is False else ("" if e[c] is None else e[c]))
                        for c in campos_tab])
    campos_jan = ["codigo", "safra", "ano", "dias", "brancos", "passa_nos_brancos", "comparavel", "estacao_mm",
                  "imerg_mm", "power_mm", "imerg_pct", "power_pct", "imerg_dias", "power_dias"]
    with open(os.path.join(AQUI, "janelas.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(campos_jan)
        for j in todas_janelas:
            w.writerow([f1(j[c]) if isinstance(j[c], float) else
                        ("sim" if j[c] is True else "não" if j[c] is False else ("" if j[c] is None else j[c]))
                        for c in campos_jan])
    with open(os.path.join(AQUI, "lista-a-parte.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["codigo", "nome", "uf", "motivo", "detalhe"], lineterminator="\n")
        w.writeheader()
        w.writerows(lista_a_parte)
    with open(os.path.join(AQUI, "diario-fev-jun.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["codigo", "data", "estacao_mm", "imerg_mm", "prectotcorr_mm"])
        w.writerows(diario_csv)

    # as medidas
    marcadas = {x["codigo"] for x in lista_a_parte}
    res = {"calculado_em": agora_local(), "gerado_com": "IA (Claude)"}
    for uf in UFS:
        entram = [e for e in tabela if e["uf"] == uf and e["entra_na_conta"]]
        res[uf] = {"estacoes_nos_arquivos": sum(1 for e in tabela if e["uf"] == uf),
                   "entram_na_conta": [e["codigo"] for e in entram],
                   "nao_entram": [(e["codigo"], e["janelas_comparaveis"]) for e in tabela
                                  if e["uf"] == uf and not e["entra_na_conta"]],
                   "medidas": medidas(entram),
                   "medidas_sem_a_lista_a_parte": medidas([e for e in entram if e["codigo"] not in marcadas]),
                   "na_lista_a_parte_e_na_conta": sorted({e["codigo"] for e in entram if e["codigo"] in marcadas})}
    # conferência: Rio Verde (A025) igual à série de antes, nos dias de 2016 a 2025
    if os.path.exists(RIO_VERDE_ANTES) and "A025" in est:
        antes = {}
        with open(RIO_VERDE_ANTES, encoding="utf-8") as f:
            for linha in csv.DictReader(f):
                antes[linha["data"]] = numero(linha["chuva_mm"])
        horas = {}
        for ano, caminho in sorted(est["A025"]["arquivos"]):
            for k, v in ler_bruto(caminho)[1].items():
                horas.setdefault(k, v)
        agora = por_dia(horas)
        comuns = [d for d in dias_entre(datetime.date(2016, 1, 1), datetime.date(2025, 12, 31))
                  if d.isoformat() in antes]
        diferentes = [d.isoformat() for d in comuns if agora.get(d) != antes[d.isoformat()]]
        res["conferencia_a025"] = {"dias_comparados": len(comuns), "dias_diferentes": len(diferentes),
                                   "exemplos": diferentes[:5]}
    with open(os.path.join(AQUI, "resultado.json"), "w", encoding="utf-8") as f:
        json.dump({"medidas": res, "estacoes": tabela}, f, ensure_ascii=False, indent=1, default=str)
        f.write("\n")
    escrever_tabelas_no_leia_me(tabela, res, lista_a_parte)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


def br(v, casas=1):
    return "--" if v is None else f"{v:.{casas}f}".replace(".", ",")


def escrever_tabelas_no_leia_me(tabela, res, lista_a_parte):
    """Troca o trecho entre as duas marcas do LEIA-ME pelas tabelas desta rodada (nenhum número à mão)."""
    caminho = os.path.join(AQUI, "LEIA-ME.md")
    inicio, fim = "<!-- tabelas: geradas pelo calcular -->", "<!-- fim das tabelas -->"
    with open(caminho, encoding="utf-8") as f:
        texto = f.read()
    if inicio not in texto or fim not in texto:
        return
    L = []
    for uf, titulo in (("GO", "Goiás"), ("DF", "Distrito Federal (à parte)")):
        L.append(f"### As estações de {titulo}")
        L.append("")
        L.append("| código | nome | lat | lon | janelas comparáveis | entra? | erro do satélite (%) | erro do modelo (%) "
                 "| mais perto | modelo em % da estação: até 2020 (n) | de 2021 em diante (n) | satélite: até 2020 "
                 "| de 2021 em diante | lista à parte? |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for e in [x for x in tabela if x["uf"] == uf]:
            if e["entra_na_conta"]:
                perto = ("satélite" if e["erro_imerg"] < e["erro_power"] else
                         "modelo" if e["erro_power"] < e["erro_imerg"] else "empate")
            else:
                perto = "--"
            L.append(f"| {e['codigo']} | {e['nome']} | {br(e['latitude'], 4)} | {br(e['longitude'], 4)} | "
                     f"{e['janelas_comparaveis']} | {'sim' if e['entra_na_conta'] else 'não'} | {br(e['erro_imerg'])} | "
                     f"{br(e['erro_power'])} | {perto} | {br(e['power_ate_2020'], 0)} ({e['n_ate_2020']}) | "
                     f"{br(e['power_2021_em_diante'], 0)} ({e['n_2021_em_diante']}) | {br(e['imerg_ate_2020'], 0)} | "
                     f"{br(e['imerg_2021_em_diante'], 0)} | {'sim' if e['na_lista_a_parte'] else 'não'} |")
        L.append("")
        for rotulo, chave in (("todas as que entram", "medidas"),
                              ("sem as da lista à parte", "medidas_sem_a_lista_a_parte")):
            m = res[uf][chave]
            if not m["n_estacoes"]:
                L.append(f"**{titulo}, {rotulo}:** nenhuma estação.")
                L.append("")
                continue
            p, s = m["power"], m["imerg"]
            L.append(f"**{titulo}, {rotulo} ({m['n_estacoes']} estações):**")
            L.append(f"- (b) o satélite fica mais perto da estação em **{m['satelite_mais_perto']} de "
                     f"{m['n_estacoes']}**; a chuva de modelo em {m['modelo_mais_perto']}; empates: {m['empates']}.")
            L.append(f"- (c) a mediana do erro: satélite **{br(m['mediana_erro_imerg'])}%**, chuva de modelo "
                     f"**{br(m['mediana_erro_power'])}%**.")
            L.append(f"- (d) a chuva de modelo em % da estação, na mediana: **{br(p['mediana_ate_2020'], 0)}%** até "
                     f"2020 ({p['n_ate_2020']} estações) e **{br(p['mediana_2021_em_diante'], 0)}%** de 2021 em diante "
                     f"({p['n_2021_em_diante']} estações). Nas {p['estacoes_com_os_dois']} que têm os dois períodos, "
                     f"caiu em {p['caiu_em']}; a mediana da diferença é {br(p['mediana_da_diferenca'], 0)} pontos.")
            L.append(f"- (d, controle) o satélite em % da estação, na mediana: {br(s['mediana_ate_2020'], 0)}% até 2020 "
                     f"e {br(s['mediana_2021_em_diante'], 0)}% de 2021 em diante; caiu em {s['caiu_em']} das "
                     f"{s['estacoes_com_os_dois']}; mediana da diferença {br(s['mediana_da_diferenca'], 0)} pontos.")
            L.append("")
    L.append("### A lista à parte (dado estranho na estação; quem está aqui continua nas medidas)")
    L.append("")
    if lista_a_parte:
        L.append("| código | nome | UF | motivo | detalhe |")
        L.append("|---|---|---|---|---|")
        for x in lista_a_parte:
            L.append(f"| {x['codigo']} | {x['nome']} | {x['uf']} | {x['motivo']} | {x['detalhe']} |")
    else:
        L.append("Nenhuma estação.")
    L.append("")
    if "conferencia_a025" in res:
        c = res["conferencia_a025"]
        L.append(f"**Conferência:** a série diária de Rio Verde (A025) feita aqui e a de "
                 f"`data/orbita/validacao/chuva/inmet.csv` foram comparadas em {c['dias_comparados']} dias de 2016 a "
                 f"2025: {c['dias_diferentes']} dias diferentes.")
        L.append("")
    novo = texto.split(inicio)[0] + inicio + "\n" + "\n".join(L) + fim + texto.split(fim)[1]
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(novo)


# ------------------------------------------------------------------ testes

def testar():
    h = datetime.timedelta(hours=1)
    assert numero("-9999") is None and numero("") is None and numero(",2") == 0.2 and numero("0") == 0.0
    t0 = datetime.datetime(2020, 1, 1, 4)
    horas = {t0 + i * h: 1.0 for i in range(24)}
    horas[datetime.datetime(2020, 1, 1, 3)] = 5.0                       # 23h-24h de 31/12 em Brasília
    d = por_dia(horas)
    assert d[datetime.date(2020, 1, 1)] == 24.0 and d[datetime.date(2019, 12, 31)] is None
    d19 = por_dia({**{t0 + i * h: 2.0 for i in range(19)}, **{t0 + i * h: None for i in range(19, 24)}})
    assert d19[datetime.date(2020, 1, 1)] is None
    assert por_dia({t0 + i * h: 2.0 for i in range(20)})[datetime.date(2020, 1, 1)] == 40.0
    # a janela: o dia em branco da estação não entra na soma da fonte; 11 brancos: não compara
    a, b = datetime.date(2020, 2, 1), datetime.date(2020, 2, 20)
    est = {x: 10.0 for x in dias_entre(a, b)}
    est[a] = None
    fontes = {"imerg": {x: 5.0 for x in dias_entre(a, b)}, "power": {x: 20.0 for x in dias_entre(a, b)}}
    j = comparar_janela(est, fontes, a, b)
    assert j["brancos"] == 1 and j["estacao_mm"] == 190.0 and j["imerg_mm"] == 95.0 and j["imerg_pct"] == 50.0
    assert j["power_pct"] == 200.0 and j["comparavel"]
    for x in list(dias_entre(a, b))[:11]:
        est[x] = None
    j = comparar_janela(est, fontes, a, b)
    assert j["brancos"] == 11 and not j["passa_nos_brancos"] and not j["comparavel"]
    # fonte sem dado em mais de 10 dias com dado na estação: sem %
    est = {x: 10.0 for x in dias_entre(a, b)}
    falha = {x: (None if i < 11 else 5.0) for i, x in enumerate(dias_entre(a, b))}
    j = comparar_janela(est, {"imerg": falha, "power": fontes["power"]}, a, b)
    assert j["imerg_pct"] is None and j["power_pct"] == 200.0 and not j["comparavel"]
    # o erro médio é a média de |% - 100|
    s = resumo_da_estacao([{"comparavel": True, "ano": 2019, "imerg_pct": 90.0, "power_pct": 50.0},
                           {"comparavel": True, "ano": 2022, "imerg_pct": 120.0, "power_pct": 150.0},
                           {"comparavel": False, "ano": 2023, "imerg_pct": None, "power_pct": None}])
    assert s["erro_imerg"] == 15.0 and s["erro_power"] == 50.0 and s["janelas_comparaveis"] == 2
    assert s["power_ate_2020"] == 50.0 and s["power_2021_em_diante"] == 150.0
    m = medidas([{"erro_imerg": 10.0, "erro_power": 30.0, "power_ate_2020": 90.0, "power_2021_em_diante": 50.0,
                  "imerg_ate_2020": 100.0, "imerg_2021_em_diante": 95.0},
                 {"erro_imerg": 40.0, "erro_power": 20.0, "power_ate_2020": 80.0, "power_2021_em_diante": None,
                  "imerg_ate_2020": 100.0, "imerg_2021_em_diante": None},
                 {"erro_imerg": 5.0, "erro_power": 5.0, "power_ate_2020": None, "power_2021_em_diante": 60.0,
                  "imerg_ate_2020": None, "imerg_2021_em_diante": 100.0}])
    assert m["satelite_mais_perto"] == 1 and m["modelo_mais_perto"] == 1 and m["empates"] == 1
    assert m["mediana_erro_imerg"] == 10.0 and m["mediana_erro_power"] == 20.0
    assert m["power"]["mediana_ate_2020"] == 85.0 and m["power"]["mediana_2021_em_diante"] == 55.0
    assert m["power"]["estacoes_com_os_dois"] == 1 and m["power"]["caiu_em"] == 1
    assert m["power"]["mediana_da_diferenca"] == -40.0
    # a lista à parte
    diario = {x: 0.0 for x in dias_entre(datetime.date(2018, 1, 1), datetime.date(2018, 12, 31))}
    diario[datetime.date(2018, 5, 5)] = 250.0
    tipos = {t for t, _ in marcas("X", diario, [{"latitude": 0, "longitude": 0}, {"latitude": 0.1, "longitude": 0}],
                                  [{"passa_nos_brancos": True, "estacao_mm": 30.0, "ano": 2018, "brancos": 0}])}
    assert tipos == {"seca_longa_no_auge", "dia_extremo", "janela_baixa", "mudou_de_lugar"}, tipos
    assert abs(distancia_km(0, 0, 1, 0) - 111.19) < 0.01
    print("testes: tudo certo")


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "testar":
        testar()
    elif len(sys.argv) == 2 and sys.argv[1] == "baixar":
        fonte = ler_fonte()
        baixar_zips(fonte)
        baixar_power(fonte)
    elif len(sys.argv) == 2 and sys.argv[1] == "calcular":
        calcular()
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
