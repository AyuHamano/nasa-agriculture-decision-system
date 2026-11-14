# Gerado com IA (Claude)
"""O motor: recebe a entrada, roda as duas rotações no clima guardado e devolve a resposta com os números.

A regra dos anos, o critério de "safra com sede" e a regra do veredito foram fixados antes de ver o resultado
(o guia do motor, 2026-11-14). As prioridades só mudam a ordem e o destaque da explicação: nenhum número muda.
"""
import statistics

from orbita import balanco, clima, parametros, rotacoes

CIDADES = {"rio_verde": {"nome": "Rio Verde (GO)", "latitude": -17.79, "longitude": -50.92}}
ROTACAO_DE_HOJE = ["soja", "milho", "pousio"]
TERRAS = ("pouca", "media", "muita")
ORDEM_DE_DESEMPATE = ("agua", "solo", "erosao", "renda")
NOMES = {"agua": "Água", "solo": "Solo", "erosao": "Erosão", "renda": "Renda"}
NAO_MEDIDO = "não medido"
SAFRA_A_PARTE = "2025-26"
LIMITES = [
    "É um caso só: Rio Verde (GO), uma rotação de hoje e uma alternativa, com um calendário fixo (as mesmas datas "
    "de plantio em todos os anos).",
    "O clima é o do quadrado da NASA POWER (uns 50 km), não o da fazenda. A evaporação de referência (ETo) vem de "
    "Hargreaves, que só usa a temperatura; o FAO-56 avisa que ela pode errar com vento forte ou ar muito úmido.",
    "A conta não mede renda, preço, custo nem produtividade: falta de água não é quebra de safra.",
    "A conta não mede o efeito da palha do capim (menos evaporação, mais chuva entrando na terra) nem a enxurrada: "
    "toda chuva entra na terra até encher. Só entra o lado em que a braquiária bebe água.",
    "Enquanto o milho está na terra, a braquiária debaixo dele não aumenta o pedido de água (hipótese).",
    "A raiz vale com a profundidade final desde o dia do plantio; por isso a sede do começo da soja pode sair maior "
    "do que é.",
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
    if problemas:
        raise ValueError("Entrada fora do formato: " + "; ".join(problemas) + ".")
    return {"cidade_id": cidade, "rotacao_atual": list(ROTACAO_DE_HOJE),
            "prioridades": {nome: notas[nome] for nome in ("agua", "solo", "renda", "erosao")}, "terra": terra}


def escolher_anos(chuvas):
    """A regra dos anos. `chuvas`: safra -> chuva de 1/fev a 30/jun (mm), em ordem de tempo.

    O ano mais seco é a menor chuva. O ano normal é a chuva mais perto da mediana. Com número par de safras, as duas
    do meio ficam sempre à mesma distância da mediana: vale a mais antiga (desempate fixado antes de ver o resultado).
    """
    mediana = statistics.median(chuvas.values())
    menor = min(abs(v - mediana) for v in chuvas.values())
    empatadas = [s for s, v in chuvas.items() if abs(abs(v - mediana) - menor) < 1e-9]
    return {"janela": "de 1/fev a 30/jun (a janela da 2ª safra), na NASA POWER",
            "chuva_por_safra_mm": {s: r1(v) for s, v in chuvas.items()},
            "mediana_mm": r1(mediana),
            "ano_mais_seco": min(chuvas, key=chuvas.get),
            "ano_normal": empatadas[0],
            "empate_do_ano_normal": empatadas if len(empatadas) > 1 else [],
            "desempate": "com 10 safras, a 5ª e a 6ª ficam à mesma distância da mediana; vale a mais antiga"}


def comparar_agua(falta_atual, falta_alternativa, sede_atual, sede_alternativa, empate_mm):
    """Quem se saiu melhor na água, por duas medidas: a falta no ano mais seco (mm) e as safras com sede."""
    diferenca = falta_alternativa - falta_atual
    por_falta = "empate" if abs(diferenca) < empate_mm else ("alternativa" if diferenca < 0 else "atual")
    por_sede = "empate" if sede_alternativa == sede_atual else (
        "alternativa" if sede_alternativa < sede_atual else "atual")
    discordam = "empate" not in (por_falta, por_sede) and por_falta != por_sede
    melhor = "empate" if discordam else (por_sede if por_falta == "empate" else por_falta)
    return {"melhor": melhor, "pela_falta_no_ano_mais_seco": por_falta, "pelas_safras_com_sede": por_sede,
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


def _ndvi(par):
    try:
        from orbita import ndvi
    except ImportError:
        return {"disponivel": False, "aviso": "A peça do NDVI (o verde visto pelo satélite) ainda não foi ligada."}
    try:
        return dict(ndvi.resumo(par), disponivel=True)
    except (OSError, ValueError, KeyError) as erro:
        return {"disponivel": False, "aviso": f"O NDVI não pôde ser lido: {erro}"}


def responder(entrada, par=None, dias=None):
    """A resposta inteira do motor, pronta para virar JSON."""
    entrada = validar_entrada(entrada)
    par = par or parametros.carregar()
    dias = dias if dias is not None else clima.ler_serie()
    cidade = CIDADES[entrada["cidade_id"]]
    chuvas = {s: balanco.chuva_da_janela(dias, int(s[:4]) + 1) for s in balanco.SAFRAS_DO_ESTUDO}
    regra = escolher_anos(chuvas)
    regra["segunda_mais_seca"] = sorted(chuvas, key=chuvas.get)[1]
    if regra["ano_mais_seco"] == "2024-25":
        regra["chuva_de_2025_mm"] = r1(sum(d.chuva for d in dias if d.data.year == 2025))
        regra["aviso_do_ano_mais_seco"] = (
            "a janela desta safra (fevereiro a junho de 2025) cai no ano em que a chuva da NASA POWER é suspeita "
            "de baixa; confira nas outras fontes (python3 -m orbita.validar)")
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
    seco, normal = regra["ano_mais_seco"], regra["ano_normal"]
    comparacao_da_agua = comparar_agua(
        rot["atual"]["safras"][seco]["total"]["falta_mm"], rot["alternativa"]["safras"][seco]["total"]["falta_mm"],
        rot["atual"]["safras_com_sede"]["quantas"], rot["alternativa"]["safras_com_sede"]["quantas"],
        parametros.valor(par, "regras", "empate_mm"))
    dias_hoje = calendario["atual"]["dias_sem_planta_viva"]
    dias_alternativa = calendario["alternativa"]["dias_sem_planta_viva"]
    solo = "empate" if dias_hoje == dias_alternativa else ("alternativa" if dias_alternativa < dias_hoje else "atual")
    melhores = {"agua": comparacao_da_agua["melhor"], "solo": solo, "erosao": solo, "renda": NAO_MEDIDO}
    notas = entrada["prioridades"]
    ordem = sorted(ORDEM_DE_DESEMPATE, key=lambda p: -notas[p])
    medidas = {"agua": "a falta de água da soja e do milho no ano mais seco e as safras em que o milho passou sede",
               "solo": "os dias do ano sem planta viva na terra (o mesmo número da erosão)",
               "erosao": "os dias do ano sem planta viva na terra (o mesmo número do solo)",
               "renda": "não medido: o motor não tem preço, custo nem produtividade"}
    prioridades = [{"id": p, "nome": NOMES[p], "nota": notas[p], "melhor": melhores[p], "medida": medidas[p]}
                   for p in ordem]
    primeira_medida = next(p for p in prioridades if p["melhor"] != NAO_MEDIDO)
    return {
        "aviso": "Motor provisório, sem site. Não é recomendação agronômica: valide com o agrônomo.",
        "pergunta": "Com o clima que a NASA registrou na minha região, vale trocar a minha rotação de hoje por outra?",
        "entrada": entrada,
        "local": dict(cidade, id=entrada["cidade_id"]),
        "clima": dict(clima.origem_da_serie(), primeiro_dia=dias[0].data.isoformat(),
                      ultimo_dia=dias[-1].data.isoformat(),
                      conta="FAO-56: ETo de Hargreaves (eq. 52), Kc por fase, balanço diário da água (cap. 8)"),
        "terra": {"opcao": entrada["terra"], "classe": parametros.valor(par, "terra", entrada["terra"], "classe"),
                  "agua_que_segura_mm": r1(agua["taw"]), "agua_por_metro_mm": r1(agua["agua_mm_por_m"]),
                  "raizes_m": agua["raizes_m"]},
        "calendario": {k: calendario[k] for k in ("soja", "milho", "braquiaria", "entre_a_soja_e_o_milho_dias")},
        "regra_dos_anos": regra,
        "rotacoes": rot,
        "comparacao": {"ano_normal": normal, "ano_mais_seco": seco, "agua": comparacao_da_agua,
                       "solo_e_erosao": {"melhor": solo, "dias_sem_planta_viva_hoje": dias_hoje,
                                         "dias_sem_planta_viva_alternativa": dias_alternativa}},
        "prioridades": prioridades,
        "destaque": {"prioridade": primeira_medida["id"], "nota": primeira_medida["nota"],
                     "melhor": primeira_medida["melhor"]},
        "veredito": veredito(melhores),
        "safra_2025_26": dict(a_parte, aviso="a conferir: a chuva de 2025 na NASA POWER é suspeita de baixa; esta "
                              "safra fica fora das 10 e fora da regra dos anos", chuva_da_janela_mm=r1(chuva_a_parte)),
        "ndvi": _ndvi(par),
        "parametros": [{"parametro": c, "valor": p["valor"], "etiqueta": p["etiqueta"], "fonte": p["fonte"],
                        "trecho": p["trecho"]} for c, p in parametros.folhas(par)],
        "hipoteses": len(parametros.hipoteses(par)),
        "limites": list(LIMITES),
    }
