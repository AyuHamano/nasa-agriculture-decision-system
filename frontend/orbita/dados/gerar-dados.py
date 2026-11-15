# Gerado com IA (Claude)
"""Gera os dados do site do Órbita Rural, ao lado deste programa: dados/respostas.js (e respostas.json),
dados/complementos.js e dados/validacao.js.

O site só desenha: não faz conta nenhuma. Tudo o que ele mostra está nesses arquivos, e tudo o que está
neles sai do motor (backend/orbita, importado daqui) ou dos arquivos de dados dele (data/orbita/).
Rodar de novo sempre que o motor ou os dados mudarem (Python 3, só a biblioteca padrão):

    python3 -B frontend/dados/gerar-dados.py                      (com a pasta backend/ ao lado de frontend/)
    python3 -B frontend/dados/gerar-dados.py --backend <pasta>    (com o motor em outro lugar)

O -B é para o Python não criar __pycache__ dentro do repositório (o programa também desliga isso sozinho).

O que sai:
- respostas.js e respostas.json: quem grava é o próprio motor (orbita.exportar.exportar): as 3 respostas inteiras
  (pouca, media, muita), puras, com todas as notas iguais a 3.
- complementos.js: window.ORBITA_COMPLEMENTOS = {...}, o que é preparado fora do motor a partir dessas mesmas 3
  respostas: o ano da terra dia a dia (rotacoes.cobertura_do_dia), a chuva por mês de cada safra (a mesma série
  que o motor usou) e, por terra, a água recebida em % (100 menos a falta em % da própria resposta, com a faixa
  do milho na alternativa), o nível da sede forte em água recebida e o texto curto (orbita.mensagem.texto).
- validacao.js: window.ORBITA_VALIDACAO = {...}, com os mesmos números que `python3 -B -m orbita.validar` imprime
  (a chuva contra a estação do INMET, a ETo contra o Open-Meteo e a falta do milho contra a colheita do IBGE).

Dia sem dado nunca vira zero: fica fora da soma e é contado à parte; número que não existe sai como null.
Os arquivos são montados numa pasta provisória e trocados no fim: se algo falhar, os de antes ficam como estavam.
"""
import argparse
import csv
import datetime
import json
import os
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True  # nada de __pycache__ dentro do repositório, mesmo sem o -B

AQUI = Path(__file__).resolve().parent
GERADO_POR = "frontend/dados/gerar-dados.py"
MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
ANO_DO_DESENHO = 2021  # o ano da terra vai de 1/set/2021 a 31/ago/2022, os mesmos anos que o motor usa no resumo
#                        do calendário (rotacoes.resumo_do_calendario); 2022 não é bissexto: 365 dias


def ligar_o_motor(backend):
    """Põe a pasta backend/ no caminho do Python e importa os módulos do motor."""
    global balanco, clima, exportar, mensagem, motor, parametros, rotacoes, validar
    sys.path.insert(0, str(backend))
    from orbita import balanco, clima, exportar, mensagem, motor, parametros, rotacoes, validar


def _r(numero, casas=1):
    """Arredonda só para mostrar, como o motor faz. Sem número, fica None (nunca zero)."""
    if numero is None:
        return None
    return int(round(numero)) if casas == 0 else round(float(numero), casas) + 0.0


# ---------------------------------------------------------------- respostas.js: quem grava é o motor

def as_respostas_do_motor(pasta):
    """Manda o motor gravar o respostas.js e o respostas.json na pasta e devolve as 3 respostas gravadas."""
    exportar.exportar(pasta)
    gravadas = json.loads((Path(pasta) / "respostas.json").read_text(encoding="utf-8"))["respostas"]
    for terra in exportar.TERRAS:  # a conferência: o que foi gravado é o que o motor responde agora
        de_novo = json.loads(json.dumps(motor.responder(dict(exportar.PERGUNTA, terra=terra)), ensure_ascii=False))
        if gravadas.get(terra) != de_novo:
            raise ValueError(f"a resposta gravada pelo exportar para a terra '{terra}' não é igual à que o motor "
                             "dá agora para a mesma pergunta")
    return gravadas


# ---------------------------------------------------------------- complementos.js: o que é preparado fora do motor

def _id_da_cobertura(tipo, com_braquiaria):
    """Do tipo que o motor devolve para o nome que o site desenha."""
    if tipo == "milho" and com_braquiaria:
        return "milho_com_capim"
    if tipo == rotacoes.BRAQUIARIA:
        return "capim"
    return tipo  # soja, milho ou sem_planta


def o_ano_da_terra(par):
    """O que está na terra em cada dia de um ano de 1/set a 31/ago, nas duas rotações, em trechos de dias iguais."""
    cal = rotacoes.calendario(par)
    primeiro, ultimo = datetime.date(ANO_DO_DESENHO, 9, 1), datetime.date(ANO_DO_DESENHO + 1, 8, 31)
    datas = [primeiro + datetime.timedelta(days=n) for n in range((ultimo - primeiro).days + 1)]
    if len(datas) != 365:
        raise ValueError(f"o ano do desenho tem de ter 365 dias (não bissexto) e veio com {len(datas)}")
    meses, dias_por_mes = [], []
    for data in datas:
        if not meses or meses[-1] != MESES[data.month - 1]:
            meses.append(MESES[data.month - 1])
            dias_por_mes.append(0)
        dias_por_mes[-1] += 1
    saida = {"meses": meses, "dias_por_mes": dias_por_mes, "dias_do_ano": len(datas)}
    for nome, info in rotacoes.ROTACOES.items():
        trechos = []
        for n, data in enumerate(datas):
            tipo = rotacoes.cobertura_do_dia(data, info["com_braquiaria"], cal)[0]
            cobertura = _id_da_cobertura(tipo, info["com_braquiaria"])
            if trechos and trechos[-1]["cobertura"] == cobertura:
                trechos[-1]["dias"] += 1
                trechos[-1]["ate"] = f"{data:%d/%m}"
            else:
                trechos.append({"cobertura": cobertura, "do_dia": n, "dias": 1,
                                "de": f"{data:%d/%m}", "ate": f"{data:%d/%m}"})
        saida[nome] = trechos
    return saida


def chuva_por_mes(fonte):
    """A chuva de cada mês de cada safra (de set a ago), da mesma série diária que o motor usou nas respostas."""
    dias, _ = clima.ler_serie_com_aviso(fonte)  # é assim que o motor.responder lê a chuva
    chuva = {dia.data: dia.chuva for dia in dias}
    contas = {safra: {"soma": [0.0] * 12, "com_dado": [0] * 12, "sem_dado": 0} for safra in validar.SAFRAS}
    data = datetime.date(min(int(s[:4]) for s in contas), 9, 1)
    ultimo = datetime.date(max(int(s[:4]) for s in contas) + 1, 8, 31)
    while data <= ultimo:
        conta = contas.get(balanco.nome_da_safra(data))  # a safra de cada dia é o motor que diz
        if conta is not None:
            mes = (data.month - 9) % 12  # 0 = setembro ... 11 = agosto
            valor = chuva.get(data)
            if valor is None:
                conta["sem_dado"] += 1
            else:
                conta["soma"][mes] += valor
                conta["com_dado"][mes] += 1
        data += datetime.timedelta(days=1)
    safras = {}
    for safra, conta in contas.items():
        mm = [_r(soma) if com_dado else None for soma, com_dado in zip(conta["soma"], conta["com_dado"])]
        safras[safra] = {"mm": mm, "total_mm": _r(sum(conta["soma"])) if any(conta["com_dado"]) else None,
                         "dias_sem_dado": conta["sem_dado"]}
    return {"fonte": fonte,
            "maior_mes_mm": max(valor for s in safras.values() for valor in s["mm"] if valor is not None),
            "safras": safras}


def _faixa_recebida(faixa):
    """Da faixa da falta do milho ({menor, maior}, em %) para a faixa da água recebida; sem a faixa, None."""
    falta = faixa.get("falta_do_milho_pct") if isinstance(faixa, dict) else None
    if not isinstance(falta, dict) or falta.get("menor") is None or falta.get("maior") is None:
        return None
    return {"menor": _r(100 - falta["maior"]), "maior": _r(100 - falta["menor"])}


def agua_recebida_pct(resposta):
    """Por rotação, safra e cultura: 100 menos a falta de água em % que a própria resposta traz.

    Onde a resposta traz a faixa da falta do milho (a alternativa), entra também milho_faixa (menor e maior).
    """
    a_parte = resposta["safra_2025_26"]
    saida = {}
    for rotacao, dados in resposta["rotacoes"].items():
        tabela = dict(dados["safras"])
        tabela[a_parte["safra"]] = a_parte[rotacao]
        faixas = dict(dados.get("faixa") or {})
        if rotacao == "alternativa":
            faixas[a_parte["safra"]] = a_parte.get("faixa_da_alternativa")
        saida[rotacao] = {}
        for safra, numeros in tabela.items():
            linha = {cultura: _r(100 - numeros[cultura]["falta_relativa_pct"]) if numeros[cultura]["dias"] else None
                     for cultura in rotacoes.CULTURAS}
            faixa = _faixa_recebida(faixas.get(safra))
            if faixa:
                linha["milho_faixa"] = faixa
            saida[rotacao][safra] = linha
    return saida


def da_terra(resposta):
    """O que muda com a terra: a água recebida, o nível da sede forte em água recebida e o texto curto."""
    saida = {"agua_recebida_pct": agua_recebida_pct(resposta)}
    nivel = (resposta.get("sede_forte") or {}).get("nivel_pct")
    if nivel is not None:
        saida["sede_forte_recebido_pct"] = _r(100 - nivel)
    saida["mensagem"] = mensagem.texto(resposta)
    saida["notas_da_mensagem"] = resposta["entrada"]["prioridades"]
    return saida


def montar_complementos(respostas, agora):
    fontes = {resposta["clima"]["chuva"]["id"] for resposta in respostas.values()}
    if len(fontes) != 1:
        raise ValueError(f"as respostas das terras vieram com fontes de chuva diferentes ({sorted(fontes)})")
    return {"gerado_por": GERADO_POR, "gerado_em": agora,
            "o_ano_da_terra": o_ano_da_terra(parametros.carregar()),  # o calendário não depende da terra
            "chuva_por_mes": chuva_por_mes(fontes.pop()),             # nem a chuva
            "por_terra": {terra: da_terra(resposta) for terra, resposta in respostas.items()}}


def conferir_os_dias_sem_planta(resposta, ano):
    """Compara os dias sem planta do desenho com os números da resposta (só relata; não força nada)."""
    linhas = []
    entre = resposta["calendario"]["entre_a_soja_e_o_milho_dias"]
    for rotacao in resposta["rotacoes"]:
        desenho = sum(t["dias"] for t in ano[rotacao] if t["cobertura"] == rotacoes.SEM_PLANTA)
        do_motor = resposta["rotacoes"][rotacao]["sem_planta_viva"]["dias_sem_planta_viva"]
        linhas.append(f"  dias sem planta ({rotacao}): {desenho} no desenho; o motor diz {do_motor} + {entre} entre a "
                      f"soja e o milho = {do_motor + entre} ({'bate' if desenho == do_motor + entre else 'NÃO BATE'})")
    return linhas


# ---------------------------------------------------------------- validacao.js: os números do orbita.validar

def _nome_da_estacao():
    """A estação do INMET como o arquivo da fonte diz (chuva/fonte-inmet.json); sem ele, como o validar a chama."""
    try:
        estacao = json.loads((validar.PASTA / "chuva" / "fonte-inmet.json").read_text(encoding="utf-8"))["estacao"]
        return f"estação automática do INMET {estacao['codigo']}, {estacao['nome'].title()} ({estacao['uf']})"
    except (OSError, ValueError, KeyError):
        return "estação do INMET de Rio Verde (a chuva medida em terra)"


def chuva_contra_a_estacao():
    """As partes 1 e 2 do validar: o total de cada fonte na janela e em % da estação, safra por safra."""
    fontes = validar._chuvas(validar.PASTA)
    if "inmet" not in fontes:
        raise ValueError("falta o arquivo chuva/inmet.csv (a estação do INMET) nos dados da validação")
    inmet = fontes["inmet"]
    nomes = [nome for nome in clima.FONTES_DE_CHUVA if nome in fontes]
    tolerados = validar.BRANCOS_TOLERADOS
    safras, razoes_por_safra = [], []
    for safra in validar.SAFRAS:
        inicio, fim = validar._janela(safra)
        _, brancos = validar.soma_da_janela(inmet, inicio, fim)
        linha = {"safra": safra, "comparada": brancos <= tolerados}
        validos = [d for d in inmet if inicio <= d <= fim and inmet[d] is not None]
        if linha["comparada"]:
            linha["estacao_mm"] = _r(sum(inmet[d] for d in validos), 0)
        linha["dias_em_branco"] = brancos
        linha["fonte_mm"] = {}
        for nome in nomes:  # a parte 1: a janela inteira da fonte (mais de 10 dias em branco: sem número)
            soma, sem_dado = validar.soma_da_janela(fontes[nome], inicio, fim)
            linha["fonte_mm"][nome] = _r(soma, 0) if sem_dado <= tolerados else None
        if linha["comparada"]:  # a parte 2: a fonte somada só nos dias em que a estação tem dado
            razoes = {}
            for nome in nomes:
                dias = [d for d in validos if fontes[nome].get(d) is not None]
                medido = sum(inmet[d] for d in dias)
                if len(dias) >= len(validos) - tolerados and medido > 0:
                    razoes[nome] = 100 * sum(fontes[nome][d] for d in dias) / medido
            linha["pct_da_estacao"] = {nome: _r(razoes.get(nome), 0) for nome in nomes}
            razoes_por_safra.append(razoes)
        if safra == motor.SAFRA_A_PARTE:
            linha["a_parte"] = True
        safras.append(linha)
    erros, quantas = {}, {}
    for nome in nomes:  # como no validar: entram todas as safras comparadas, a 2025-26 também
        distancias = [abs(razoes[nome] - 100) for razoes in razoes_por_safra if nome in razoes]
        if distancias:
            erros[nome], quantas[nome] = sum(distancias) / len(distancias), len(distancias)
    saida = {"janela": "de 1/fev a 30/jun", "estacao": _nome_da_estacao(), "fontes": nomes, "safras": safras,
             "erro_medio_pct": {nome: _r(erro) for nome, erro in erros.items()},
             "safras_comparadas": min(quantas.values()) if quantas else 0,
             "mais_perto": min(erros, key=erros.get) if erros else None}
    if len(set(quantas.values())) > 1:  # se um dia as fontes não tiverem o mesmo número de safras comparadas
        saida["safras_comparadas_por_fonte"] = quantas
    return saida


def eto_contra_o_open_meteo():
    """A parte 3 do validar: a ETo do motor (Hargreaves) contra a coluna eto_mm dos arquivos do Open-Meteo."""
    do_motor_por_dia = {dia.data: dia.eto for dia in clima.ler_serie()}
    saida = []
    for nome in ("open-meteo", "era5"):
        arquivo = validar.PASTA / "chuva" / f"{nome}.csv"
        if not arquivo.exists():
            continue
        pares = []
        with open(arquivo, encoding="utf-8", newline="") as f:
            for linha in csv.DictReader(f):
                texto = (linha.get("eto_mm") or "").strip()
                dia = datetime.date.fromisoformat(linha["data"].strip())
                if texto and dia in do_motor_por_dia:
                    pares.append((do_motor_por_dia[dia], float(texto)))
        if not pares:
            continue
        do_motor, de_fora = [a for a, _ in pares], [b for _, b in pares]
        media_motor, media_fora = sum(do_motor) / len(pares), sum(de_fora) / len(pares)
        saida.append({"fonte": nome, "dias": len(pares), "motor_mm_dia": _r(media_motor, 2),
                      "outra_mm_dia": _r(media_fora, 2),
                      "motor_acima_pct": _r(100 * (media_motor / media_fora - 1)),  # negativo = o motor fica abaixo
                      "correlacao": _r(validar.pearson(do_motor, de_fora), 2)})
    return saida


def falta_contra_a_colheita():
    """A parte 4 do validar: a falta de água do milho (rotação de hoje, terra média) contra o rendimento no IBGE."""
    rendimento = motor.ler_rendimento_do_milho(validar.PASTA / "ibge" / "rendimento_rio_verde.csv")
    par = parametros.carregar()
    faltas = {}
    for fonte in clima.FONTES_DE_CHUVA:
        try:
            dias, _ = clima.ler_serie_com_aviso(fonte, validar.PASTA / "chuva")
        except ValueError as erro:
            print(f"Aviso: a chuva '{fonte}' ficou fora da validação ({erro})", file=sys.stderr)
            continue
        numeros = balanco.numeros_por_safra(balanco.simular(dias, False, par, "media"))
        faltas[fonte] = {s: numeros[s]["milho"]["falta_relativa_pct"] for s in balanco.SAFRAS_DO_ESTUDO}
    safras = [s for s in balanco.SAFRAS_DO_ESTUDO if s in rendimento]
    correlacoes = {f: validar.spearman([faltas[f][s] for s in safras], [rendimento[s] for s in safras])
                   for f in faltas}
    validas = {f: c for f, c in correlacoes.items() if c is not None}
    pior_colheita = min(safras, key=lambda s: rendimento[s])
    maior_falta = {f: max(safras, key=lambda s: faltas[f][s]) for f in faltas}
    return {"terra": "media", "rotacao": "atual", "fontes": list(faltas),
            "safras": [{"safra": s, "ibge_kg_ha": _r(rendimento[s], 0),
                        "falta_do_milho_pct": {f: _r(faltas[f][s]) for f in faltas}} for s in safras],
            "correlacao_de_postos": {f: _r(c, 2) for f, c in correlacoes.items()},
            "que_mais_acompanha": min(validas, key=validas.get) if validas else None,
            "pior_colheita": {"safra": pior_colheita, "kg_ha": _r(rendimento[pior_colheita], 0)},
            "maior_falta": {f: {"safra": s, "pct": _r(faltas[f][s])} for f, s in maior_falta.items()}}


def montar_validacao(agora):
    return {"gerado_por": GERADO_POR, "gerado_em": agora, "chuva_contra_a_estacao": chuva_contra_a_estacao(),
            "eto": eto_contra_o_open_meteo(), "falta_contra_a_colheita": falta_contra_a_colheita()}


# ---------------------------------------------------------------- gravar

def texto_do_js(variavel, dados, o_que_e, agora, comando):
    objeto = json.dumps(dados, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    objeto = objeto.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")  # como o exportar do motor faz
    return ("/* Gerado com IA (Claude) */\n"
            f"/* {o_que_e}\n"
            f"   Gerado em {agora} por {GERADO_POR} com:\n"
            f"   {comando}\n"
            "   Não editar à mão: o site só mostra o que está aqui. */\n"
            f"window.{variavel} = {objeto};\n")


def main():
    leitor = argparse.ArgumentParser(description="Gera dados/respostas.js, dados/complementos.js e "
                                                 "dados/validacao.js a partir do motor do Órbita Rural.")
    leitor.add_argument("--backend", default=None, help="a pasta backend/ do motor (padrão: a que fica ao lado "
                                                        "de frontend/)")
    pedido = leitor.parse_args().backend
    backend = Path(pedido).expanduser().resolve() if pedido else Path(__file__).resolve().parents[2] / "backend"
    if not (backend / "orbita" / "motor.py").exists():
        print(f"Não achei o motor em {backend} (falta a pasta orbita/ com o motor.py). Nada foi gravado. "
              "Rode de novo com --backend <a pasta backend/ do repositório>.", file=sys.stderr)
        return 1
    comando = f"python3 -B {GERADO_POR}" + (" --backend <a pasta backend/ do motor>" if pedido else "")
    agora = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        ligar_o_motor(backend)
        validacao = montar_validacao(agora)
        with tempfile.TemporaryDirectory(dir=AQUI, prefix=".gerando-") as provisoria:
            provisoria = Path(provisoria)
            respostas = as_respostas_do_motor(provisoria)  # o motor grava o respostas.js e o respostas.json
            complementos = montar_complementos(respostas, agora)
            (provisoria / "complementos.js").write_text(texto_do_js(
                "ORBITA_COMPLEMENTOS", complementos,
                "O que o site mostra e o motor ainda não entrega pronto, preparado a partir das mesmas 3 respostas "
                "do respostas.js (o ano da terra, a chuva por mês e, por terra, a água recebida e o texto curto).",
                agora, comando), encoding="utf-8")
            (provisoria / "validacao.js").write_text(texto_do_js(
                "ORBITA_VALIDACAO", validacao,
                "Os números da validação cruzada, os mesmos que `python3 -B -m orbita.validar` imprime.",
                agora, comando), encoding="utf-8")
            gravados = sorted(arquivo.name for arquivo in provisoria.iterdir())
            for nome in gravados:  # só agora, com tudo pronto, os arquivos novos tomam o lugar dos de antes
                os.replace(provisoria / nome, AQUI / nome)
    except (ImportError, ValueError, OSError, KeyError) as erro:
        print(f"Não deu para gerar os dados: {erro}. Nada foi trocado: os arquivos de antes continuam como estavam. "
              "Confira se o motor roda sozinho (de dentro de backend/: python3 -B -m orbita.validar).",
              file=sys.stderr)
        return 1
    for nome in gravados:
        print(f"Gravado: {AQUI / nome} ({(AQUI / nome).stat().st_size} bytes)")
    print(f"O motor veio de {backend}. Conferência do ano da terra:")
    for linha in conferir_os_dias_sem_planta(respostas["media"], complementos["o_ano_da_terra"]):
        print(linha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
