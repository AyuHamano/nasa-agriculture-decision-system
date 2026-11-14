# Gerado com IA (Claude)
"""O motor: recebe a entrada, roda as duas rotações no clima guardado e devolve a resposta com os números.

O critério de "safra com sede" e a regra do veredito foram fixados antes de ver o resultado (o guia do motor,
2026-11-14). As prioridades só mudam a ordem e o destaque da explicação: nenhum número muda.

A chuva e a regra dos anos são parâmetros. O padrão (a decisão do dono do projeto, 2026-11-14, depois da validação
cruzada): a chuva do satélite GPM IMERG e o pior ano pela colheita do IBGE. A chuva de modelo da NASA POWER e a
regra pela chuva (a do guia) continuam como opção, para comparar.
"""
import csv
import statistics

from orbita import balanco, clima, parametros, rotacoes

CIDADES = {"rio_verde": {"nome": "Rio Verde (GO)", "latitude": -17.79, "longitude": -50.92}}
ROTACAO_DE_HOJE = ["soja", "milho", "pousio"]
TERRAS = ("pouca", "media", "muita")
ORDEM_DE_DESEMPATE = ("agua", "solo", "erosao", "renda")
NOMES = {"agua": "Água", "solo": "Solo", "erosao": "Erosão", "renda": "Renda"}
NAO_MEDIDO = "não medido"
SAFRA_A_PARTE = "2025-26"
CHUVA_PADRAO, REGRA_PADRAO = "imerg", "rendimento"
REGRAS = ("rendimento", "chuva")
ARQUIVO_DO_IBGE = clima.PASTA_DOS_DADOS / "validacao" / "ibge" / "rendimento_rio_verde.csv"
LIMITES = [
    "É um caso só: Rio Verde (GO), uma rotação de hoje e uma alternativa, com um calendário fixo (as mesmas datas "
    "de plantio em todos os anos).",
    "O clima é o de quadrados do mapa (a temperatura da NASA POWER, uns 50 km), não o da fazenda. A evaporação de "
    "referência (ETo) vem de Hargreaves, que só usa a temperatura; o FAO-56 avisa que ela pode errar com vento "
    "forte ou ar muito úmido.",
    "A conta não mede renda, preço, custo nem produtividade: falta de água não é quebra de safra.",
    "A conta não mede o efeito da palha do capim (menos evaporação, mais chuva entrando na terra) nem a enxurrada: "
    "toda chuva entra na terra até encher. Só entra o lado em que a braquiária bebe água.",
    "Enquanto o milho está na terra, a braquiária debaixo dele não aumenta o pedido de água (hipótese).",
    "A raiz vale com a profundidade final desde o dia do plantio, e na troca de cultura a caixa nova começa com a "
    "mesma fração de água da anterior; por isso a sede do começo da soja pode sair diferente do que é.",
]


def r1(numero):
    return round(float(numero), 1) + 0.0


def validar_entrada(entrada):
    """Confere a entrada e devolve-a completa (sem terra, vale media). Fora do formato: erro dizendo o que falta."""
    if not isinstance(entrada, dict):
        raise ValueError('Entrada fora do formato: tem de ser um objeto com cidade_id, rotacao_atual, prioridades '
                         'e terra (opcional), como {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", '
                         '"pousio"], "prioridades": {"agua": 5, "solo": 4, "renda": 2, "erosao": 3}, "terra": "media"}.')
    problemas = []
    cidade = entrada.get("cidade_id")
    if cidade is None:
        problemas.append('falta cidade_id (por enquanto, só "rio_verde")')
    elif cidade not in CIDADES:
        problemas.append(f'cidade_id "{cidade}" ainda não existe: o motor só tem "rio_verde"')
    rotacao = entrada.get("rotacao_atual")
    if rotacao is None:
        problemas.append('falta rotacao_atual (por enquanto, só ["soja", "milho", "pousio"])')
    elif not isinstance(rotacao, list) or [str(x).strip().lower() for x in rotacao] != ROTACAO_DE_HOJE:
        problemas.append(f'rotacao_atual {rotacao!r} ainda não existe: o motor só conhece ["soja", "milho", "pousio"]')
    notas = entrada.get("prioridades")
    if not isinstance(notas, dict):
        problemas.append("faltam as prioridades (agua, solo, renda e erosao, cada uma com nota de 1 a 5)")
    else:
        for nome in ("agua", "solo", "renda", "erosao"):
            nota = notas.get(nome)
            if nota is None:
                problemas.append(f"falta a nota de {nome} em prioridades (de 1 a 5)")
            elif isinstance(nota, bool) or not isinstance(nota, int) or not 1 <= nota <= 5:
                problemas.append(f"a nota de {nome} tem de ser um número inteiro de 1 a 5 (veio {nota!r})")
    terra = entrada.get("terra") or "media"
    if terra not in TERRAS:
        problemas.append(f'terra "{terra}" não existe: use pouca, media ou muita (quanta água a terra segura)')
    chuva = entrada.get("chuva") or CHUVA_PADRAO
    if chuva not in clima.FONTES_DE_CHUVA:
        problemas.append(f'chuva "{chuva}" não existe: use imerg, chirps, era5 ou power (a fonte da chuva)')
    regra = entrada.get("regra") or REGRA_PADRAO
    if regra not in REGRAS:
        problemas.append(f'regra "{regra}" não existe: use rendimento (o pior ano pela colheita do IBGE) ou chuva '
                         "(o ano mais seco pela chuva de fevereiro a junho)")
    if problemas:
        raise ValueError("Entrada fora do formato: " + "; ".join(problemas) + ".")
    return {"cidade_id": cidade, "rotacao_atual": list(ROTACAO_DE_HOJE),
            "prioridades": {nome: notas[nome] for nome in ("agua", "solo", "renda", "erosao")}, "terra": terra,
            "chuva": chuva, "regra": regra}


def ler_rendimento_do_milho(arquivo=ARQUIVO_DO_IBGE):
    """O rendimento do milho de 2ª safra em Rio Verde no IBGE, por safra (kg/ha). O ano N do IBGE é a safra (N-1)/N."""
    rendimentos = {}
    with open(arquivo, encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            if linha["produto"].strip() == "milho_2a_safra" and linha["rendimento_kg_ha"].strip():
                ano = int(linha["ano"])
                rendimentos[f"{ano - 1}-{ano % 100:02d}"] = float(linha["rendimento_kg_ha"])
    return rendimentos


def _pior_e_normal(valores):
    """Do dicionário safra -> valor: (a safra do menor valor, a mais perto da mediana, as empatadas, a mediana)."""
    mediana = statistics.median(valores.values())
    menor = min(abs(v - mediana) for v in valores.values())
    empatadas = [s for s, v in valores.items() if abs(abs(v - mediana) - menor) < 1e-9]
    return min(valores, key=valores.get), empatadas[0], (empatadas if len(empatadas) > 1 else []), mediana


def escolher_anos(chuvas):
    """A regra pela chuva (a do guia). `chuvas`: safra -> chuva de 1/fev a 30/jun (mm), em ordem de tempo.

    O pior ano é o mais seco (a menor chuva). O ano normal é a chuva mais perto da mediana. Com número par de safras,
    as duas do meio ficam sempre à mesma distância da mediana: vale a mais antiga (desempate fixado antes do resultado).
    """
    pior, normal, empatadas, mediana = _pior_e_normal(chuvas)
    return {"regra": "chuva",
            "criterio": "o pior ano é o mais seco: a menor chuva de 1/fev a 30/jun (a janela da 2ª safra); o ano "
                        "normal é o da chuva mais perto da mediana",
            "chuva_por_safra_mm": {s: r1(v) for s, v in chuvas.items()},
            "mediana_mm": r1(mediana), "pior_ano": pior, "ano_normal": normal, "empate_do_ano_normal": empatadas,
            "desempate": "com 10 safras, a 5ª e a 6ª ficam à mesma distância da mediana; vale a mais antiga"}


def escolher_pelo_rendimento(rendimentos, chuvas):
    """A regra pela colheita: o pior ano é a safra do pior rendimento do milho de 2ª safra no IBGE."""
    faltam = [s for s in chuvas if s not in rendimentos]
    if faltam:
        raise ValueError("A regra do rendimento precisa do rendimento do milho de 2ª safra no IBGE em todas as "
                         "safras; faltam: " + ", ".join(faltam) + ".")
    valores = {s: rendimentos[s] for s in chuvas}
    pior, normal, empatadas, mediana = _pior_e_normal(valores)
    pela_chuva = escolher_anos(chuvas)
    return {"regra": "rendimento",
            "criterio": "o pior ano é a safra do pior rendimento do milho de 2ª safra em Rio Verde no IBGE (o ano N "
                        "do IBGE é a safra (N-1)/N); o ano normal é a do rendimento mais perto da mediana",
            "fonte_do_rendimento": "IBGE, Produção Agrícola Municipal (SIDRA), Rio Verde (GO), milho de 2ª safra",
            "rendimento_por_safra_kg_ha": {s: int(v) for s, v in valores.items()},
            "mediana_kg_ha": r1(mediana),
            "chuva_por_safra_mm": pela_chuva["chuva_por_safra_mm"], "mediana_mm": pela_chuva["mediana_mm"],
            "pior_ano": pior, "ano_normal": normal, "empate_do_ano_normal": empatadas,
            "desempate": pela_chuva["desempate"],
            "pela_chuva_seria": {"pior_ano": pela_chuva["pior_ano"], "ano_normal": pela_chuva["ano_normal"]}}


def comparar_agua(falta_atual, falta_alternativa, sede_atual, sede_alternativa, empate_mm):
    """Quem se saiu melhor na água, por duas medidas: a falta no pior ano (mm) e as safras com sede."""
    diferenca = falta_alternativa - falta_atual
    por_falta = "empate" if abs(diferenca) < empate_mm else ("alternativa" if diferenca < 0 else "atual")
    por_sede = "empate" if sede_alternativa == sede_atual else (
        "alternativa" if sede_alternativa < sede_atual else "atual")
    discordam = "empate" not in (por_falta, por_sede) and por_falta != por_sede
    melhor = "empate" if discordam else (por_sede if por_falta == "empate" else por_falta)
    return {"melhor": melhor, "pela_falta_no_pior_ano": por_falta, "pelas_safras_com_sede": por_sede,
            "as_medidas_discordam": discordam, "diferenca_mm": r1(diferenca), "empate_abaixo_de_mm": empate_mm}


def veredito(melhores):
    """A resposta em uma linha, só pelo que foi medido (água, solo e erosão). Não depende das notas."""
    a_favor = [p for p in ("agua", "solo", "erosao") if melhores[p] == "alternativa"]
    contra = [p for p in ("agua", "solo", "erosao") if melhores[p] == "atual"]
    nomes = lambda lista: " e ".join(NOMES[p].lower() for p in lista)  # noqa: E731
    if a_favor and not contra:
        codigo = "vale_testar_a_troca"
        frase = (f"Pelo que foi medido, vale testar a troca: a alternativa se saiu melhor em {nomes(a_favor)} e não "
                 "ficou pior em nada do que foi medido.")
    elif a_favor and contra:
        codigo = "depende"
        frase = (f"Depende do que pesa mais para você: a alternativa se saiu melhor em {nomes(a_favor)} e pior em "
                 f"{nomes(contra)}.")
    elif contra:
        codigo = "fique_como_esta"
        frase = (f"Pelo que foi medido, fique como está: a alternativa ficou pior em {nomes(contra)} e não ganhou "
                 "em nada.")
    else:
        codigo = "fique_como_esta"
        frase = "Pelo que foi medido, fique como está: as duas rotações empataram e a troca não mostrou ganho."
    return {"codigo": codigo, "frase": frase, "a_favor_da_troca": a_favor, "contra_a_troca": contra}


def _conta(c):
    return {"pedido_mm": r1(c["pedido_mm"]), "bebido_mm": r1(c["bebido_mm"]), "falta_mm": r1(c["falta_mm"]),
            "falta_relativa_pct": r1(c["falta_relativa_pct"]), "dias": c["dias"], "dias_de_sede": c["dias_de_sede"]}


def _safra(numeros, agua_no_plantio, chuva, com_braquiaria):
    saida = {"chuva_da_janela_mm": r1(chuva), "soja": _conta(numeros["soja"]), "milho": _conta(numeros["milho"]),
             "total": _conta(numeros["total"]),
             "agua_na_terra_no_plantio_da_soja_mm": None if agua_no_plantio is None else r1(agua_no_plantio)}
    if com_braquiaria:
        saida["braquiaria"] = {"bebido_mm": r1(numeros[balanco.BRAQUIARIA]["bebido_mm"]),
                               "dias": numeros[balanco.BRAQUIARIA]["dias"]}
    return saida


def _com_sede(tabela, criterio):
    quais = [s for s, n in tabela.items() if n["milho"]["falta_relativa_pct"] >= criterio]
    return {"criterio_pct": criterio, "quantas": len(quais), "quais": quais,
            "com_10_pct": sum(1 for n in tabela.values() if n["milho"]["falta_relativa_pct"] >= 10),
            "com_30_pct": sum(1 for n in tabela.values() if n["milho"]["falta_relativa_pct"] >= 30)}


def _ndvi(par, dias_pelo_calendario):
    """O verde visto pelo satélite: prova só da rotação de hoje. Sem a peça ou sem os dados, diz o que falta."""
    try:
        from orbita import ndvi
    except ImportError:
        return {"disponivel": False, "aviso": "A peça do NDVI (o verde visto pelo satélite) ainda não foi ligada."}
    try:
        folha = par["ndvi"]["fracao_da_amplitude"]
        resumo = ndvi.resumo(folha["valor"])
        comparacao = ndvi.comparar_com_calendario(dias_pelo_calendario, resumo)
    except (OSError, ValueError, KeyError) as erro:
        return {"disponivel": False, "aviso": f"O NDVI não pôde ser lido: {erro}"}
    regra = dict(resumo["regra"], etiqueta_da_fracao=folha["etiqueta"], fonte_da_fracao=folha["fonte"])
    return {"disponivel": True, "prova_de": "só da rotação de hoje", "fonte": ndvi.FONTE, "regra": regra,
            "comparacao": comparacao, "limites_por_ponto": resumo["limites"],
            "dias_sem_planta_verde": resumo["dias_sem_planta_verde"], "anos_de_fora": resumo["anos_de_fora"],
            "ano_em_andamento": resumo["ano_em_andamento"],
            "frases": [comparacao["frase"], comparacao["nota"], ndvi.AVISO, ndvi.AVISO_DOS_PONTOS]}


def responder(entrada, par=None, dias=None):
    """A resposta inteira do motor, pronta para virar JSON."""
    entrada = validar_entrada(entrada)
    par = par or parametros.carregar()
    avisos = []
    if dias is None:
        dias, avisos = clima.ler_serie_com_aviso(entrada["chuva"])
    cidade = CIDADES[entrada["cidade_id"]]
    chuvas = {s: balanco.chuva_da_janela(dias, int(s[:4]) + 1) for s in balanco.SAFRAS_DO_ESTUDO}
    if entrada["regra"] == "rendimento":
        regra = escolher_pelo_rendimento(ler_rendimento_do_milho(), chuvas)
    else:
        regra = escolher_anos(chuvas)
        regra["segunda_mais_seca"] = sorted(chuvas, key=chuvas.get)[1]
        if entrada["chuva"] == "power" and regra["pior_ano"] == "2024-25":
            regra["chuva_de_2025_mm"] = r1(sum(d.chuva for d in dias if d.data.year == 2025))
            regra["aviso_do_ano_mais_seco"] = (
                "a janela desta safra (fevereiro a junho de 2025) cai no ano em que a chuva de modelo da NASA POWER "
                "é suspeita de baixa; confira nas outras fontes (python3 -m orbita.validar)")
    criterio = parametros.valor(par, "regras", "sede_da_2a_safra_pct")
    calendario = rotacoes.resumo_do_calendario(par)
    agua = balanco.agua_da_terra(par, entrada["terra"])
    chuva_a_parte = balanco.chuva_da_janela(dias, int(SAFRA_A_PARTE[:4]) + 1)
    rot, a_parte = {}, {}
    for nome, info in rotacoes.ROTACOES.items():
        registros = balanco.simular(dias, info["com_braquiaria"], par, entrada["terra"])
        numeros = balanco.numeros_por_safra(registros)
        no_plantio = balanco.agua_no_plantio_da_soja(registros)
        tabela = {s: _safra(numeros[s], no_plantio.get(s), chuvas[s], info["com_braquiaria"])
                  for s in balanco.SAFRAS_DO_ESTUDO}
        rot[nome] = {"nome": info["nome"], "sem_planta_viva": calendario[nome], "safras": tabela,
                     "safras_com_sede": _com_sede(tabela, criterio),
                     "soma_das_10_safras": {
                         "falta_da_soja_mm": r1(sum(numeros[s]["soja"]["falta_mm"] for s in tabela)),
                         "falta_do_milho_mm": r1(sum(numeros[s]["milho"]["falta_mm"] for s in tabela)),
                         "dias_de_sede": sum(numeros[s]["total"]["dias_de_sede"] for s in tabela)}}
        a_parte[nome] = _safra(numeros[SAFRA_A_PARTE], no_plantio.get(SAFRA_A_PARTE), chuva_a_parte,
                               info["com_braquiaria"])
    pior, normal = regra["pior_ano"], regra["ano_normal"]
    comparacao_da_agua = comparar_agua(
        rot["atual"]["safras"][pior]["total"]["falta_mm"], rot["alternativa"]["safras"][pior]["total"]["falta_mm"],
        rot["atual"]["safras_com_sede"]["quantas"], rot["alternativa"]["safras_com_sede"]["quantas"],
        parametros.valor(par, "regras", "empate_mm"))
    dias_hoje = calendario["atual"]["dias_sem_planta_viva"]
    dias_alternativa = calendario["alternativa"]["dias_sem_planta_viva"]
    solo = "empate" if dias_hoje == dias_alternativa else ("alternativa" if dias_alternativa < dias_hoje else "atual")
    melhores = {"agua": comparacao_da_agua["melhor"], "solo": solo, "erosao": solo, "renda": NAO_MEDIDO}
    notas = entrada["prioridades"]
    ordem = sorted(ORDEM_DE_DESEMPATE, key=lambda p: -notas[p])
    medidas = {"agua": "a falta de água da soja e do milho no pior ano e as safras em que o milho passou sede",
               "solo": "os dias do ano sem planta viva na terra (o mesmo número da erosão)",
               "erosao": "os dias do ano sem planta viva na terra (o mesmo número do solo)",
               "renda": "não medido: o motor não tem preço, custo nem produtividade"}
    prioridades = [{"id": p, "nome": NOMES[p], "nota": notas[p], "melhor": melhores[p], "medida": medidas[p]}
                   for p in ordem]
    primeira_medida = next(p for p in prioridades if p["melhor"] != NAO_MEDIDO)
    temperatura = clima.origem_da_serie()
    if entrada["chuva"] == "power":
        aviso_a_parte = ("a conferir: a chuva de 2025 na NASA POWER é suspeita de baixa; esta safra fica fora das 10 "
                         "e fora da regra dos anos")
    else:
        aviso_a_parte = ("a conferir: é a safra mais recente, com o dado ainda provisório; fica fora das 10 e fora "
                         "da regra dos anos")
    return {
        "aviso": "Motor provisório, sem site. Não é recomendação agronômica: valide com o agrônomo.",
        "pergunta": "Com o clima que a NASA registrou na minha região, vale trocar a minha rotação de hoje por outra?",
        "entrada": entrada,
        "local": dict(cidade, id=entrada["cidade_id"]),
        "clima": {"chuva": {"id": entrada["chuva"], "fonte": clima.ORIGENS_DA_CHUVA[entrada["chuva"]],
                            "origem": "data/orbita/nasa-power/ (LEIA-ME.md)" if entrada["chuva"] == "power"
                                      else f"data/orbita/validacao/chuva/{entrada['chuva']}.csv (o endereço e a hora "
                                           "da consulta estão em fonte.json, na mesma pasta)"},
                  "temperatura": {"fonte": clima.ORIGEM_DA_TEMPERATURA, "consulta": temperatura["consulta"],
                                  "baixado_em": temperatura["baixado_em"]},
                  "primeiro_dia": dias[0].data.isoformat(), "ultimo_dia": dias[-1].data.isoformat(),
                  "avisos": list(avisos),
                  "conta": "FAO-56: ETo de Hargreaves (eq. 52), Kc por fase, balanço diário da água (cap. 8)"},
        "terra": {"opcao": entrada["terra"], "classe": parametros.valor(par, "terra", entrada["terra"], "classe"),
                  "agua_por_metro_mm": r1(agua["agua_mm_por_m"]),
                  "raizes_m": {tipo: raiz for tipo, raiz in agua["raizes_m"].items()},
                  "agua_que_segura_mm": {tipo: r1(valor) for tipo, valor in agua["taw"].items()}},
        "calendario": {k: calendario[k] for k in ("soja", "milho", "braquiaria", "entre_a_soja_e_o_milho_dias")},
        "regra_dos_anos": regra,
        "rotacoes": rot,
        "comparacao": {"ano_normal": normal, "pior_ano": pior, "agua": comparacao_da_agua,
                       "solo_e_erosao": {"melhor": solo, "dias_sem_planta_viva_hoje": dias_hoje,
                                         "dias_sem_planta_viva_alternativa": dias_alternativa}},
        "prioridades": prioridades,
        "destaque": {"prioridade": primeira_medida["id"], "nome": primeira_medida["nome"],
                     "nota": primeira_medida["nota"], "melhor": primeira_medida["melhor"]},
        "veredito": veredito(melhores),
        "safra_2025_26": dict(a_parte, safra=SAFRA_A_PARTE, aviso=aviso_a_parte,
                              chuva_da_janela_mm=r1(chuva_a_parte)),
        "ndvi": _ndvi(par, dias_hoje),
        "parametros": [{"parametro": c, "valor": p["valor"], "etiqueta": p["etiqueta"], "fonte": p["fonte"],
                        "trecho": p["trecho"]} for c, p in parametros.folhas(par)],
        "hipoteses": len(parametros.hipoteses(par)),
        "limites": list(LIMITES),
    }
