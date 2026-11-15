# Gerado com IA (Claude)
"""O motor: recebe a entrada, roda as duas rotações no clima guardado e devolve a resposta com os números.

O critério de "safra com sede" e a regra do veredito foram fixados antes de ver o resultado (o guia do motor,
2026-11-14). As prioridades só mudam a ordem e o destaque da explicação: nenhum número muda.

A chuva e a regra dos anos são parâmetros. O padrão (a decisão do dono do projeto, 2026-11-14, depois da validação
cruzada): a chuva do satélite GPM IMERG e o pior ano pela colheita do IBGE. A chuva de modelo da NASA POWER e a
regra pela chuva (a do guia) continuam como opção, para comparar.

Os ajustes de 2026-11-14 (a pedido do dono, depois da prova): a palha entra nas duas rotações; a alternativa sai
como faixa, pela hipótese da disputa do capim com o milho; o veredito da água sai dessa faixa (melhor, pior, empate
ou "depende da hipótese"); e a "sede forte" usa o nível tirado das safras de quebra no IBGE. Nenhuma vencedora está
escrita aqui: tudo sai dos números.
"""
import csv
import datetime
import json
import statistics

from orbita import balanco, calor, clima, explicacao, parametros, rotacoes

CIDADES = {"rio_verde": {"nome": "Rio Verde (GO)", "latitude": -17.79, "longitude": -50.92},
           "jatai": {"nome": "Jataí (GO)", "latitude": -17.88, "longitude": -51.71},
           "silvania": {"nome": "Silvânia (GO)", "latitude": -16.66, "longitude": -48.61}}
CIDADE_DA_PROVA = clima.CIDADE_DE_REFERENCIA    # Rio Verde: a única com a estação em terra (o verde do satélite já existe nas três)
ROTACAO_DE_HOJE = ["soja", "milho", "pousio"]
TERRAS = ("pouca", "media", "muita")
ORDEM_DE_DESEMPATE = ("agua", "solo", "erosao", "renda")
NOMES = {"agua": "Água", "solo": "Solo", "erosao": "Erosão", "renda": "Renda", "calor": "Calor"}
PREOCUPACOES = ("agua", "calor", "terra")       # o que mais preocupa o produtor: só muda a ordem e o destaque
PERNAS = ("agua", "calor", "terra")             # as três pernas do projeto, na ordem de costume
NA_FRENTE = {"agua": ("agua",), "terra": ("solo", "erosao"), "calor": ()}   # a preocupação nas prioridades antigas
NAO_MEDIDO = "não medido"
SAFRA_A_PARTE = "2025-26"
CHUVA_PADRAO, REGRA_PADRAO = "imerg", "rendimento"
REGRAS = ("rendimento", "chuva")
CENARIOS = ("sem_disputa", "meio", "alta")      # a faixa da disputa do capim com o milho, do menor ao maior efeito
CENARIO_DOS_CAMPOS_ANTIGOS = "meio"             # o cenário que enche os campos antigos da alternativa
NOMES_DOS_CENARIOS = {"sem_disputa": "sem disputa do capim com o milho", "meio": "com a disputa do meio",
                      "alta": "com a disputa alta"}
TERRA_DE_REFERENCIA = "media"                   # a terra da conta que dá o nível de sede forte
AGUA_PELA_FAIXA = {"alternativa_melhor": "alternativa", "alternativa_pior": "atual", "empate": "empate",
                   "depende_da_hipotese": "empate"}   # como a água entra no veredito geral (o "depende" tem frase própria)
AVISO_DA_SEDE_FORTE = ("O nível de sede forte foi tirado de poucas safras e de uma conta só (a rotação de hoje, a "
                       "terra média e a chuva padrão): pode haver alarme falso (safra com falta alta e colheita boa) "
                       "e quebra que a conta não vê. Rendimento também depende de praga, adubo, semente e data de "
                       "plantio.")
ARQUIVO_DO_IBGE = clima.PASTA_DOS_DADOS / "validacao" / "ibge" / "rendimento_rio_verde.csv"
LIMITES = [
    "São três cidades de Goiás (Rio Verde, Jataí e Silvânia) e três rotações do cardápio. O calendário é o de "
    "costume ou anda inteiro com a data de plantio da soja que o produtor informa; em qualquer caso, as mesmas datas "
    "em todos os anos. A estação em terra e o verde do satélite só foram conferidos em Rio Verde.",
    "O clima é o de quadrados do mapa (a temperatura da NASA POWER, uns 50 km), não o da fazenda. A evaporação de "
    "referência (ETo) vem de Hargreaves, que só usa a temperatura; o FAO-56 avisa que ela pode errar com vento "
    "forte ou ar muito úmido.",
    "A conta não mede renda, preço, custo nem produtividade: falta de água não é quebra de safra.",
    "A palha entra nas duas rotações só pelo lado da evaporação (FAO-56, cap. 10), nos dias sem planta viva e na "
    "fase inicial da soja, com uma cobertura fixa em cada rotação: a palha não se desfaz com o tempo na conta, e o "
    "quanto de terra ela cobre é hipótese. A conta não mede a chuva a mais que entra na terra com palha nem a "
    "enxurrada: toda chuva entra na terra até encher.",
    "O quanto o capim disputa água com o milho enquanto os dois crescem juntos não foi medido: é hipótese, e por "
    "isso a alternativa sai como faixa (sem disputa, meio e alta). O freio da sede é o mesmo para o milho e para o "
    "capim, e o capim bebe da mesma camada de terra do milho.",
    "O nível de sede forte sai de poucas safras de quebra no IBGE: é régua de comparação, não previsão de quebra.",
    "A raiz vale com a profundidade final desde o dia do plantio, e na troca de cultura a caixa nova começa com a "
    "mesma fração de água da anterior; por isso a sede do começo da soja pode sair diferente do que é.",
    "O sorgo entra com as fases da tabela geral da FAO (sem linha de 2ª safra em Goiás), no mesmo dia de plantio do "
    "milho e com a mesma profundidade de raiz do milho: a diferença entre os dois, na conta, vem do quanto cada um "
    "pede de água.",
    "O calor é uma contagem à parte: os dias da fase crítica com a temperatura máxima acima do limite publicado de "
    "cada cultura. A temperatura é a de um quadrado grande do mapa, a fase crítica é a fase do meio da tabela da "
    "FAO, e dia de calor forte não é perda de safra.",
]


def r1(numero):
    return round(float(numero), 1) + 0.0


def validar_entrada(entrada):
    """Confere a entrada e devolve-a completa (sem terra, vale media). Fora do formato: erro dizendo o que falta."""
    if not isinstance(entrada, dict):
        raise ValueError('Entrada fora do formato: tem de ser um objeto com cidade_id e rotacao_atual (e, se quiser, '
                         'terra, plantio_da_soja e preocupacao), como {"cidade_id": "rio_verde", "rotacao_atual": '
                         '["soja", "milho", "pousio"], "terra": "media", "plantio_da_soja": "2026-11-05", '
                         '"preocupacao": "agua"}.')
    problemas = []
    cidade = entrada.get("cidade_id")
    if cidade is None:
        problemas.append("falta cidade_id (" + ", ".join(CIDADES) + ")")
    elif cidade not in CIDADES:
        problemas.append(f'cidade_id "{cidade}" ainda não existe: o motor tem ' + ", ".join(CIDADES))
    rotacao = entrada.get("rotacao_atual")
    cardapio = "; ".join(json.dumps(item["culturas"], ensure_ascii=False) for item in rotacoes.CARDAPIO.values())
    do_cardapio = None
    if rotacao is None:
        problemas.append(f"falta rotacao_atual (uma das rotações do cardápio: {cardapio})")
    else:
        do_cardapio = rotacoes.achar_rotacao(rotacao)
        if do_cardapio is None:
            problemas.append(f"rotacao_atual {rotacao!r} ainda não existe: o motor conhece {cardapio}")
    notas = entrada.get("prioridades")
    if notas is None:
        pass    # as notas de 1 a 5 saíram (decisão do dono, 2026-11-14): sem elas, vale a ordem de costume
    elif not isinstance(notas, dict):
        problemas.append("as prioridades, quando vêm, são as 4 notas (agua, solo, renda e erosao, cada uma de 1 a "
                         "5); sem notas, não mande o campo")
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
    elif cidade in CIDADES and cidade != CIDADE_DA_PROVA and chuva not in clima.chuvas_guardadas(cidade):
        problemas.append(f'a chuva "{chuva}" não está guardada para {CIDADES[cidade]["nome"]}: use '
                         + " ou ".join(clima.chuvas_guardadas(cidade)))
    regra = entrada.get("regra") or None
    if regra is not None and regra not in REGRAS:
        problemas.append(f'regra "{regra}" não existe: use rendimento (o pior ano pela colheita do IBGE) ou chuva '
                         "(o ano mais seco pela chuva de fevereiro a junho)")
    elif cidade in CIDADES:
        tem_colheita = clima.pastas_da_cidade(cidade)["ibge"].exists()
        if regra == "rendimento" and not tem_colheita:
            problemas.append(f'a regra "rendimento" pede a colheita do IBGE de {CIDADES[cidade]["nome"]}, que não '
                             'está guardada: use a regra "chuva"')
        regra = regra or (REGRA_PADRAO if tem_colheita else "chuva")   # sem a colheita, vale a menor chuva
    plantio = entrada.get("plantio_da_soja") or None
    if plantio is not None:
        try:
            plantio = rotacoes.ler_plantio_da_soja(plantio).isoformat()
        except ValueError as erro:
            problemas.append(str(erro))
    preocupacao = entrada.get("preocupacao") or None
    if preocupacao is not None and preocupacao not in PREOCUPACOES:
        problemas.append(f'preocupacao "{preocupacao}" não existe: use agua, calor ou terra (o que mais preocupa)')
    if problemas:
        raise ValueError("Entrada fora do formato: " + "; ".join(problemas) + ".")
    return {"cidade_id": cidade, "rotacao_atual": list(do_cardapio["culturas"]), "rotacao_id": do_cardapio["id"],
            "prioridades": None if notas is None else {nome: notas[nome] for nome in ("agua", "solo", "renda", "erosao")},
            "terra": terra, "chuva": chuva, "regra": regra, "plantio_da_soja": plantio, "preocupacao": preocupacao}


def ler_rendimento_do_milho(arquivo=None):
    """O rendimento do milho de 2ª safra no IBGE, por safra (kg/ha). O ano N do IBGE é a safra (N-1)/N.

    Sem `arquivo`, o de Rio Verde (o ARQUIVO_DO_IBGE do momento da chamada, que os testes podem trocar).
    """
    arquivo = ARQUIVO_DO_IBGE if arquivo is None else arquivo
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


def escolher_pelo_rendimento(rendimentos, chuvas, lugar="Rio Verde"):
    """A regra pela colheita: o pior ano é a safra do pior rendimento do milho de 2ª safra no IBGE."""
    faltam = [s for s in chuvas if s not in rendimentos]
    if faltam:
        raise ValueError("A regra do rendimento precisa do rendimento do milho de 2ª safra no IBGE em todas as "
                         "safras; faltam: " + ", ".join(faltam) + ".")
    valores = {s: rendimentos[s] for s in chuvas}
    pior, normal, empatadas, mediana = _pior_e_normal(valores)
    pela_chuva = escolher_anos(chuvas)
    empatadas_no_pior = [s for s, v in valores.items() if v == valores[pior]]
    return {"regra": "rendimento",
            "empate_do_pior_ano": empatadas_no_pior if len(empatadas_no_pior) > 1 else [],
            "criterio": f"o pior ano é a safra do pior rendimento do milho de 2ª safra em {lugar} no IBGE (o ano N "
                        "do IBGE é a safra (N-1)/N); o ano normal é a do rendimento mais perto da mediana",
            "fonte_do_rendimento": f"IBGE, Produção Agrícola Municipal (SIDRA), {lugar} (GO), milho de 2ª safra",
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


def nivel_de_sede_forte(rendimentos, faltas_pct, fracao):
    """O nível de "sede forte", tirado da colheita: a menor falta do milho (%) entre as safras de quebra.

    `rendimentos`: safra -> kg/ha (o IBGE); `faltas_pct`: safra -> falta relativa do milho na conta de referência.
    Safra de quebra = rendimento abaixo de `fracao` x a mediana das safras. Sem safra de quebra, não há nível.
    """
    safras = [s for s in faltas_pct if s in rendimentos]
    if not safras:
        return {"nivel_pct": None, "safras_de_quebra": [], "mediana_kg_ha": None, "limite_kg_ha": None,
                "alarmes_falsos": [], "maior_falta_sem_quebra": None}
    mediana = statistics.median(rendimentos[s] for s in safras)
    limite = fracao * mediana
    quebras = [s for s in safras if rendimentos[s] < limite]
    nivel = min(faltas_pct[s] for s in quebras) if quebras else None
    sem_quebra = [s for s in safras if s not in quebras]
    maior = max(sem_quebra, key=lambda s: faltas_pct[s]) if sem_quebra else None
    return {"nivel_pct": nivel, "safras_de_quebra": quebras, "mediana_kg_ha": r1(mediana), "limite_kg_ha": r1(limite),
            "alarmes_falsos": [s for s in sem_quebra if nivel is not None and faltas_pct[s] >= nivel],
            "maior_falta_sem_quebra": None if maior is None else {
                "safra": maior, "falta_do_milho_pct": faltas_pct[maior], "rendimento_kg_ha": int(rendimentos[maior])}}


def veredito_da_agua_pela_faixa(falta_atual, faltas_da_alternativa, empate_mm):
    """O veredito da água pelas duas pontas da faixa. `faltas_da_alternativa`: cenário -> falta de água (mm).

    Em cada cenário a alternativa fica "melhor" (falta menor por `empate_mm` ou mais), "pior" ou em "empate". Se dá o
    mesmo nas duas pontas, é esse o veredito; se muda dentro da faixa, "depende da hipótese".
    """
    def classe(diferenca):
        return "empate" if abs(diferenca) < empate_mm else ("melhor" if diferenca < 0 else "pior")

    # As pontas e a classe saem da diferença sem arredondar (4,96 mm é empate; 5,04 mm não é); só a saída arredonda.
    por_cenario = {c: {"falta_mm": r1(f), "diferenca_mm": r1(f - falta_atual), "classe": classe(f - falta_atual)}
                   for c, f in faltas_da_alternativa.items()}
    menor = min(faltas_da_alternativa, key=faltas_da_alternativa.get)
    maior = max(faltas_da_alternativa, key=faltas_da_alternativa.get)
    a, b = por_cenario[menor]["diferenca_mm"], por_cenario[maior]["diferenca_mm"]
    n = lambda x: f"{abs(x):.1f}".replace(".", ",")  # noqa: E731
    nome = lambda c: NOMES_DOS_CENARIOS.get(c, c)  # noqa: E731

    def ponta(cenario, x):
        if abs(x) < 0.05:
            return f"{nome(cenario)}, a mesma falta de água da rotação de hoje"
        return f"{nome(cenario)}, {n(x)} mm de falta de água {'a menos' if x < 0 else 'a mais'} que na rotação de hoje"

    pontas = f"{ponta(menor, a)}; {ponta(maior, b)}"
    classes = {por_cenario[menor]["classe"], por_cenario[maior]["classe"]}
    if classes == {"melhor"}:
        codigo, frase = "alternativa_melhor", f"Na água, a alternativa se saiu melhor nas duas pontas da faixa: {pontas}."
    elif classes == {"pior"}:
        codigo, frase = "alternativa_pior", f"Na água, a alternativa se saiu pior nas duas pontas da faixa: {pontas}."
    elif classes == {"empate"}:
        codigo = "empate"
        frase = (f"Na água, empate: a diferença é pequena (menos de {n(empate_mm)} mm) nas duas pontas da faixa: "
                 f"{pontas}.")
    else:
        codigo = "depende_da_hipotese"
        frase = (f"Na água, depende da hipótese: o resultado muda dentro da faixa da disputa do capim com o milho: "
                 f"{pontas}.")
    return {"codigo": codigo, "frase": frase, "diferenca_mm": {"menor": a, "maior": b},
            "cenario_do_menor_efeito": menor, "cenario_do_maior_efeito": maior, "falta_na_rotacao_de_hoje_mm":
            r1(falta_atual), "por_cenario": por_cenario, "empate_abaixo_de_mm": empate_mm}


def veredito(melhores, agua_pela_faixa=None):
    """A resposta em uma linha, só pelo que foi medido (água, solo e erosão). Não depende das notas."""
    if agua_pela_faixa is not None:     # na água vale o veredito pela faixa, não a comparação de um cenário só
        melhores = dict(melhores, agua=AGUA_PELA_FAIXA[agua_pela_faixa])
    a_favor = [p for p in ("agua", "solo", "erosao") if melhores[p] == "alternativa"]
    contra = [p for p in ("agua", "solo", "erosao") if melhores[p] == "atual"]
    nomes = lambda lista: " e ".join(NOMES[p].lower() for p in lista)  # noqa: E731
    if agua_pela_faixa == "depende_da_hipotese":
        codigo = "depende"
        partes = ([f"a alternativa se saiu melhor em {nomes(a_favor)}"] if a_favor else []) + (
            [f"se saiu pior em {nomes(contra)}"] if contra else [])
        frase = ("Depende: " + (" e ".join(partes) + ", mas na água" if partes else "na água") + " o resultado muda "
                 "com a hipótese da disputa do capim com o milho.")
    elif a_favor and not contra:
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


def _safra(numeros, agua_no_plantio, chuva, com_braquiaria, segunda="milho"):
    saida = {"chuva_da_janela_mm": r1(chuva), "soja": _conta(numeros["soja"]), segunda: _conta(numeros[segunda]),
             "total": _conta(numeros["total"]),
             "agua_na_terra_no_plantio_da_soja_mm": None if agua_no_plantio is None else r1(agua_no_plantio)}
    if com_braquiaria:
        saida["braquiaria"] = {"bebido_mm": r1(numeros[balanco.BRAQUIARIA]["bebido_mm"]),
                               "dias": numeros[balanco.BRAQUIARIA]["dias"],
                               "bebido_junto_com_o_milho_mm": r1(numeros["milho"]["bebido_do_capim_mm"])}
    return saida


def _com_sede_forte(faltas_do_milho, nivel, quebras=()):
    """As safras com falta do milho igual ou maior que o nível de sede forte (sem nível, não conta).

    `faltas_do_milho` (safra -> %) e `nivel` vêm sem arredondar: 49,56% não chega a um nível de 49,64%, embora os
    dois apareçam como 49,6. Só a saída arredonda.
    `alarmes_falsos`: safras no nível ou acima, sem quebra no IBGE; `quebras_abaixo_do_nivel`: o contrário.
    """
    quais = [] if nivel is None else [s for s, falta in faltas_do_milho.items() if falta >= nivel]
    return {"nivel_pct": None if nivel is None else r1(nivel), "quantas": None if nivel is None else len(quais),
            "quais": quais, "alarmes_falsos": [s for s in quais if s not in quebras],
            "quebras_abaixo_do_nivel": [] if nivel is None else [
                s for s in quebras if s in faltas_do_milho and s not in quais]}


def _numeros_da_rotacao(dias, com_braquiaria, par, terra, chuvas, chuva_a_parte, criterio, disputa=0.0, cal=None,
                        segunda="milho"):
    """As 10 safras de uma rotação (num cenário de disputa), a safra mais recente à parte e a falta sem arredondar.

    `segunda`: a cultura da 2ª safra (milho ou sorgo); os nomes dos campos acompanham (falta_do_sorgo_mm).
    """
    registros = balanco.simular(dias, com_braquiaria, par, terra, disputa=disputa, cal=cal, segunda=segunda)
    numeros = balanco.numeros_por_safra(registros)
    no_plantio = balanco.agua_no_plantio_da_soja(registros)
    tabela = {s: _safra(numeros[s], no_plantio.get(s), chuvas[s], com_braquiaria, segunda)
              for s in balanco.SAFRAS_DO_ESTUDO}
    bloco = {"safras": tabela,
             "safras_com_sede": _com_sede({s: numeros[s][segunda]["falta_relativa_pct"] for s in tabela}, criterio),
             "soma_das_10_safras": {
                 "falta_da_soja_mm": r1(sum(numeros[s]["soja"]["falta_mm"] for s in tabela)),
                 f"falta_do_{segunda}_mm": r1(sum(numeros[s][segunda]["falta_mm"] for s in tabela)),
                 "dias_de_sede": sum(numeros[s]["total"]["dias_de_sede"] for s in tabela)}}
    sem_arredondar = {"total_mm": {s: numeros[s]["total"]["falta_mm"] for s in tabela},      # para comparar: 4,96 mm
                      "milho_pct": {s: numeros[s][segunda]["falta_relativa_pct"] for s in tabela},   # não é 5
                      "dias_de_sede": {s: numeros[s]["total"]["dias_de_sede"] for s in tabela}}
    return (bloco, _safra(numeros[SAFRA_A_PARTE], no_plantio.get(SAFRA_A_PARTE), chuva_a_parte, com_braquiaria,
                          segunda), sem_arredondar)


def _menor_e_maior(valores):
    return {"menor": min(valores), "maior": max(valores)}


def _sede_forte(par, entrada, dias, dias_injetados, rendimentos):
    """O nível de sede forte: sai do IBGE e da conta de referência (rotação de hoje, terra média, chuva padrão).

    Devolve o bloco da resposta (arredondado) e o nível sem arredondar, que é o que se usa para contar.
    """
    fracao = parametros.valor(par, "regras", "quebra_fracao_da_mediana")
    saida = {"o_que_e": "safra com sede forte = falta de água do milho igual ou maior que o nível; o nível é a menor "
                        "falta do milho entre as safras de quebra",
             "safra_de_quebra": f"rendimento do milho de 2ª safra no IBGE abaixo de {round(100 * fracao)}% da mediana "
                                "das safras do estudo (o ano N do IBGE é a safra (N-1)/N)",
             "fracao_da_mediana": fracao,
             "referencia": {"rotacao": "atual", "terra": TERRA_DE_REFERENCIA, "chuva": CHUVA_PADRAO},
             "fonte_do_rendimento": f"IBGE, Produção Agrícola Municipal (SIDRA), {_lugar(entrada)} (GO), milho de "
                                    "2ª safra",
             "aviso": AVISO_DA_SEDE_FORTE}
    try:
        if rendimentos is None:
            rendimentos = ler_rendimento_do_milho(_arquivo_do_ibge(entrada))
        if dias_injetados or entrada["chuva"] == CHUVA_PADRAO:
            dias_da_referencia = dias
        else:
            dias_da_referencia, _ = clima.ler_serie_com_aviso(CHUVA_PADRAO, cidade_id=entrada["cidade_id"],
                                                               lugar=_lugar(entrada))
    except (OSError, ValueError) as erro:
        return dict(saida, nivel_pct=None, safras_de_quebra=[], alarmes_falsos_na_referencia=[],
                    aviso=f"Não deu para tirar o nível de sede forte: {erro}"), None
    numeros = balanco.numeros_por_safra(balanco.simular(dias_da_referencia, False, par, TERRA_DE_REFERENCIA))
    faltas = {s: numeros[s]["milho"]["falta_relativa_pct"] for s in balanco.SAFRAS_DO_ESTUDO}   # sem arredondar
    nivel = nivel_de_sede_forte(rendimentos, faltas, fracao)
    quebras, perto = nivel["safras_de_quebra"], nivel["maior_falta_sem_quebra"]
    saida.update(nivel_pct=None if nivel["nivel_pct"] is None else r1(nivel["nivel_pct"]),
                 safras_de_quebra=quebras, quantas_safras_de_quebra=len(quebras),
                 mediana_kg_ha=nivel["mediana_kg_ha"], limite_kg_ha=nivel["limite_kg_ha"],
                 rendimento_das_safras_de_quebra_kg_ha={s: int(rendimentos[s]) for s in quebras},
                 falta_do_milho_na_referencia_pct={s: r1(falta) for s, falta in faltas.items()},
                 alarmes_falsos_na_referencia=nivel["alarmes_falsos"],
                 maior_falta_sem_quebra=perto and dict(perto, falta_do_milho_pct=r1(perto["falta_do_milho_pct"])))
    if not quebras:
        saida["aviso"] = ("Nenhuma safra do estudo ficou abaixo do limite de quebra no IBGE: não há nível de sede "
                          "forte para contar.")
    return saida, nivel["nivel_pct"]


def _lugar(entrada):
    """O nome da cidade sem o estado: "Rio Verde", "Jataí"."""
    return CIDADES[entrada["cidade_id"]]["nome"].split(" (")[0]


def _arquivo_do_ibge(entrada):
    """O arquivo da colheita do IBGE da cidade (o de Rio Verde é o de sempre, que os testes podem trocar)."""
    if entrada["cidade_id"] == CIDADE_DA_PROVA:
        return None
    return clima.pastas_da_cidade(entrada["cidade_id"])["ibge"]


def _com_sede(faltas_do_milho, criterio):
    """`faltas_do_milho`: safra -> falta relativa do milho em %, sem arredondar (19,96% não é 20%)."""
    quais = [s for s, falta in faltas_do_milho.items() if falta >= criterio]
    return {"criterio_pct": criterio, "quantas": len(quais), "quais": quais,
            "com_10_pct": sum(1 for falta in faltas_do_milho.values() if falta >= 10),
            "com_30_pct": sum(1 for falta in faltas_do_milho.values() if falta >= 30)}


def _ndvi(par, dias_pelo_calendario, cidade_id=CIDADE_DA_PROVA):
    """O verde visto pelo satélite: prova só da rotação de hoje. Sem a peça ou sem os dados, diz o que falta."""
    try:
        from orbita import ndvi
    except ImportError:
        return {"disponivel": False, "aviso": "A peça do NDVI (o verde visto pelo satélite) ainda não foi ligada."}
    pasta = None
    if cidade_id != CIDADE_DA_PROVA:
        pasta = clima.pastas_da_cidade(cidade_id)["ndvi"]
        if not pasta.is_dir() or not list(pasta.glob("*.csv")):
            return {"disponivel": False, "aviso": f"Não há medida do verde do satélite (NDVI) guardada para "
                                                  f"{CIDADES[cidade_id]['nome']}: a prova pelo satélite só existe "
                                                  f"em {CIDADES[CIDADE_DA_PROVA]['nome']}."}
    try:
        folha = par["ndvi"]["fracao_da_amplitude"]
        resumo = ndvi.resumo(folha["valor"], pasta, CIDADES[cidade_id]["nome"])
        comparacao = ndvi.comparar_com_calendario(dias_pelo_calendario, resumo)
    except (OSError, ValueError, KeyError) as erro:
        return {"disponivel": False, "aviso": f"O NDVI não pôde ser lido: {erro}"}
    regra = dict(resumo["regra"], etiqueta_da_fracao=folha["etiqueta"], fonte_da_fracao=folha["fonte"])
    return {"disponivel": True, "prova_de": "só da rotação de hoje", "fonte": resumo["fonte"], "regra": regra,
            "comparacao": comparacao, "limites_por_ponto": resumo["limites"],
            "dias_sem_planta_verde": resumo["dias_sem_planta_verde"], "anos_de_fora": resumo["anos_de_fora"],
            "ano_em_andamento": resumo["ano_em_andamento"],
            "frases": [comparacao["frase"], comparacao["nota"], ndvi.AVISO, resumo["aviso_dos_pontos"]]}


def _faixa(valores):
    """A faixa de uma lista de números, do jeito da comparação: {"de": o menor, "ate": o maior}."""
    return {"de": min(valores), "ate": max(valores)}


def _pontas(valor):
    return (valor["de"], valor["ate"]) if isinstance(valor, dict) else (valor, valor)


def quem_ganha(a, b, margem):
    """Compara dois números (ou faixas) em que menos é melhor: "melhor", "pior", "empate" ou "depende".

    `a` é "melhor" se fica abaixo de `b` por `margem` ou mais mesmo na pior ponta; "pior", o contrário. Se as
    pontas das faixas dão respostas diferentes, "depende" (da hipótese que abre a faixa).
    """
    a1, a2 = _pontas(a)
    b1, b2 = _pontas(b)
    if b1 - a2 >= margem:
        return "melhor"
    if a1 - b2 >= margem:
        return "pior"
    if max(abs(a1 - b1), abs(a2 - b2), abs(a1 - b2), abs(a2 - b1)) < margem:
        return "empate"
    return "empate" if (a1 == a2 and b1 == b2) else "depende"


def _comparacao_das_rotacoes(entrada, rot, calendario, bloco_do_calor, verde, pior, normal, empate_mm, r_parcial,
                             faltas_exatas=None, no_ano=None):
    """A lista `comparacao_das_rotacoes`: cada rotação do cardápio com a água, o calor, a terra coberta e as frases.

    A rotação de hoje do produtor vem primeiro, marcada com `de_hoje`. Na rotação com capim, os números da água
    saem em faixa ({"de", "ate"}), pela hipótese da disputa do capim com o milho.
    `faltas_exatas`: id -> a falta do pior ano sem arredondar (número ou faixa): é sobre ela que vale a margem do
    empate (4,99 mm não é 5). `no_ano`: id -> os dias sem planta viva no ano inteiro, contados dia a dia.
    """
    faltas_exatas, no_ano = faltas_exatas or {}, no_ano or {}
    itens = []
    for chave, rotacao in rotacoes.ROTACOES.items():
        if chave not in rot:
            continue
        bloco = rot[chave]
        if rotacao["com_braquiaria"]:
            agua = {"falta_no_ano_normal_mm": {"de": bloco["faixa"][normal]["falta_total_mm"]["menor"],
                                               "ate": bloco["faixa"][normal]["falta_total_mm"]["maior"]},
                    "falta_no_pior_ano_mm": {"de": bloco["faixa"][pior]["falta_total_mm"]["menor"],
                                             "ate": bloco["faixa"][pior]["falta_total_mm"]["maior"]},
                    "dias_de_sede_no_pior_ano": {"de": bloco["faixa"][pior]["dias_de_sede"]["menor"],
                                                 "ate": bloco["faixa"][pior]["dias_de_sede"]["maior"]},
                    "em_faixa": True}
        else:
            agua = {"falta_no_ano_normal_mm": bloco["safras"][normal]["total"]["falta_mm"],
                    "falta_no_pior_ano_mm": bloco["safras"][pior]["total"]["falta_mm"],
                    "dias_de_sede_no_pior_ano": bloco["safras"][pior]["total"]["dias_de_sede"], "em_faixa": False}
        # O pior ano sai da colheita (ou da chuva), não da falta de água: aqui vai como a falta dele ficou contra a
        # do ano normal na conta ("maior", "menor", "igual" ou, nas faixas, "cruza").
        agua["pior_ano_contra_o_normal"] = explicacao.pior_contra_normal(agua["falta_no_pior_ano_mm"],
                                                                         agua["falta_no_ano_normal_mm"])
        culturas = [c for c in ("soja", rotacao["segunda"]) if c in bloco_do_calor["por_cultura"]]
        segunda = bloco_do_calor["por_cultura"].get(rotacao["segunda"])
        do_calor = {
            "dias_de_calor_forte_no_pior_ano": bloco_do_calor["por_rotacao"][rotacao["id"]]["dias_no_pior_ano"],
            "dias_de_calor_forte_no_ano_normal": bloco_do_calor["por_rotacao"][rotacao["id"]]["dias_no_ano_normal"],
            "limite_c": None if segunda is None else segunda["limite_c"],
            "cultura_do_limite": rotacao["segunda"],
            "etiqueta": ("publicado" if culturas and all(
                bloco_do_calor["por_cultura"][c]["etiqueta"] == "publicado" for c in culturas) else "hipótese"),
            "por_cultura": {c: {"dias": bloco_do_calor["por_cultura"][c]["por_safra"][pior]["dias_de_calor_forte"],
                                "limite_c": bloco_do_calor["por_cultura"][c]["limite_c"],
                                "etiqueta": bloco_do_calor["por_cultura"][c]["etiqueta"],
                                "maxima_da_fase_c": bloco_do_calor["por_cultura"][c]["por_safra"][pior][
                                    "maxima_da_fase_c"]}
                            for c in culturas if pior in bloco_do_calor["por_cultura"][c]["por_safra"]}}
        pelo_satelite = verde["dias_pelo_satelite"] if rotacao["id"] == "soja_milho_pousio" else None
        itens.append({"id": rotacao["id"], "nome": rotacao["nome"], "apelido": rotacao["apelido"],
                      "de_hoje": rotacao["id"] == entrada["rotacao_id"], "agua": agua, "calor": do_calor,
                      "terra_coberta": {"dias_sem_planta_viva": calendario[chave]["dias_sem_planta_viva"],
                                        "dias_sem_planta_viva_no_ano": no_ano.get(rotacao["id"]),
                                        "pelo_satelite": pelo_satelite}})
    itens.sort(key=lambda item: not item["de_hoje"])        # a de hoje primeiro; as outras, na ordem do cardápio
    for item in itens:
        item["contra_as_outras"] = {
            outro["id"]: {
                "agua": quem_ganha(faltas_exatas.get(item["id"], item["agua"]["falta_no_pior_ano_mm"]),
                                   faltas_exatas.get(outro["id"], outro["agua"]["falta_no_pior_ano_mm"]), empate_mm),
                "calor": quem_ganha(item["calor"]["dias_de_calor_forte_no_pior_ano"],
                                    outro["calor"]["dias_de_calor_forte_no_pior_ano"], 1),
                "terra_coberta": quem_ganha(item["terra_coberta"]["dias_sem_planta_viva"],
                                            outro["terra_coberta"]["dias_sem_planta_viva"], 1)}
            for outro in itens if outro["id"] != item["id"]}
    for item in itens:
        item.update(explicacao.frases_da_rotacao(item, itens, r_parcial))
    return itens


def verde_do_satelite(cidade_id, dias_pelo_calendario=None, par=None):
    """O que o satélite viu na terra da região: os dias sem planta verde, contra os dias pelo calendário.

    Para o agente (a ferramenta "o que o satélite viu"). Sem medida guardada para a cidade, a leitura é "sem_medida".
    O satélite prova só a rotação de hoje da região (soja, milho e pousio): é o que está no chão nos pontos medidos.
    """
    if cidade_id not in CIDADES:
        raise ValueError(f'Entrada fora do formato: cidade_id "{cidade_id}" ainda não existe: o motor tem '
                         + ", ".join(CIDADES) + ".")
    par = par or parametros.carregar()
    if dias_pelo_calendario is None:
        dias_pelo_calendario = rotacoes.resumo_do_calendario(par)["atual"]["dias_sem_planta_viva"]
    bruto = _ndvi(par, dias_pelo_calendario, cidade_id)
    saida = {"local": dict(CIDADES[cidade_id], id=cidade_id), "dias_pelo_calendario": dias_pelo_calendario,
             "dias_pelo_satelite": None, "leitura": "sem_medida", "menor": None, "maior": None, "quantos": 0,
             "prova_de": "só da rotação de hoje da região (soja, milho e pousio)"}
    if not bruto["disponivel"]:
        return dict(saida, frase=f"Pelo calendário, a terra fica {dias_pelo_calendario} dias seguidos sem planta "
                                 f"viva antes do plantio da soja. {bruto['aviso']}", aviso=bruto["aviso"])
    comparacao = bruto["comparacao"]
    return dict(saida, dias_pelo_satelite=comparacao["dias_pelo_satelite"], leitura=comparacao["leitura"],
                menor=comparacao["menor"], maior=comparacao["maior"], quantos=comparacao["quantos"],
                diferenca=comparacao["diferenca"], frase=comparacao["frase"],
                aviso=comparacao["aviso"] + " " + bruto["frases"][-1], fonte=bruto["fonte"])


def _serie(entrada):
    """Os dias do clima da cidade da entrada, com a chuva da fonte pedida, e os avisos."""
    return clima.ler_serie_com_aviso(entrada["chuva"], cidade_id=entrada["cidade_id"], lugar=_lugar(entrada))


def _regra_dos_anos(entrada, dias):
    """A chuva da janela de cada safra e a regra dos anos (o pior ano e o ano normal) da cidade da entrada."""
    chuvas = {s: balanco.chuva_da_janela(dias, int(s[:4]) + 1) for s in balanco.SAFRAS_DO_ESTUDO}
    if entrada["regra"] == "rendimento":
        return chuvas, escolher_pelo_rendimento(ler_rendimento_do_milho(_arquivo_do_ibge(entrada)), chuvas,
                                                _lugar(entrada))
    regra = escolher_anos(chuvas)
    regra["segunda_mais_seca"] = sorted(chuvas, key=chuvas.get)[1]
    if entrada["chuva"] == "power" and regra["pior_ano"] == "2024-25":
        regra["chuva_de_2025_mm"] = r1(sum(d.chuva for d in dias if d.data.year == 2025))
        regra["aviso_do_ano_mais_seco"] = (
            "a janela desta safra (fevereiro a junho de 2025) cai no ano em que a chuva de modelo da NASA POWER "
            "é suspeita de baixa; confira nas outras fontes (python3 -m orbita.validar)")
    return chuvas, regra


def _clima(entrada, dias, avisos):
    """O bloco `clima` da resposta: de onde vêm a chuva e a temperatura, o período e os avisos."""
    pastas = clima.pastas_da_cidade(entrada["cidade_id"])
    temperatura = clima.origem_da_serie(pastas["nasa_power"])
    return {"chuva": {"id": entrada["chuva"], "fonte": clima.ORIGENS_DA_CHUVA[entrada["chuva"]],
                      "origem": f"{pastas['texto']} (LEIA-ME.md)" if entrada["chuva"] == "power"
                                else f"{pastas['texto_da_chuva']}{entrada['chuva']}.csv (o endereço e a hora "
                                     "da consulta estão em fonte.json, na mesma pasta)"},
            "temperatura": {"fonte": clima.ORIGEM_DA_TEMPERATURA, "consulta": temperatura["consulta"],
                            "baixado_em": temperatura["baixado_em"]},
            "primeiro_dia": dias[0].data.isoformat(), "ultimo_dia": dias[-1].data.isoformat(),
            "avisos": list(avisos),
            "conta": "FAO-56: ETo de Hargreaves (eq. 52), Kc por fase, balanço diário da água (cap. 8)"}


def clima_do_lugar(cidade_id, par=None):
    """Os fatos do clima do lugar, tirados dos dados da NASA guardados: para o agente (a ferramenta "o clima do lugar").

    Devolve o lugar, de onde vêm a chuva e a temperatura, a regra dos anos (o pior ano e o ano normal), a chuva de
    cada safra e o calor (os dias de calor forte na fase crítica, no calendário de costume). Não roda a conta da água.
    """
    entrada = validar_entrada({"cidade_id": cidade_id, "rotacao_atual": list(ROTACAO_DE_HOJE)})
    par = par or parametros.carregar()
    dias, avisos = _serie(entrada)
    chuvas, regra = _regra_dos_anos(entrada, dias)
    pior, normal = regra["pior_ano"], regra["ano_normal"]
    cal = rotacoes.calendario(par)
    safras = balanco.SAFRAS_DO_ESTUDO + (SAFRA_A_PARTE,)
    bloco_do_calor = calor.bloco(dias, cal, par, safras, pior, normal, {
        rotacao["id"]: ["soja", rotacao["segunda"]] for rotacao in rotacoes.ROTACOES.values()})
    chuva_da_safra = {s: r1(sum(d.chuva for d in dias if balanco.nome_da_safra(d.data) == s))
                      for s in balanco.SAFRAS_DO_ESTUDO}
    nome = CIDADES[entrada["cidade_id"]]["nome"]
    criterio = ("a pior colheita do milho de 2ª safra no IBGE" if regra["regra"] == "rendimento"
                else "a menor chuva de fevereiro a junho")
    frase = (f"Em {nome}, nas {len(chuvas)} safras guardadas, o pior ano foi a safra {pior} ({criterio}) e o ano "
             f"normal, a safra {normal}. Na janela da 2ª safra (fevereiro a junho) choveu {_n(chuvas[pior])} mm no "
             f"pior ano e {_n(chuvas[normal])} mm no ano normal.")
    return {"local": dict(CIDADES[entrada["cidade_id"]], id=entrada["cidade_id"]),
            "clima": _clima(entrada, dias, avisos), "regra_dos_anos": regra,
            "chuva_da_safra_mm": chuva_da_safra, "calor": bloco_do_calor, "frase": frase,
            "aviso": "São fatos do clima guardado da NASA para o ponto da cidade, não da fazenda. Converse com o "
                     "agrônomo antes de decidir."}


def _n(numero):
    """Número em português, com uma casa e vírgula (o mesmo arredondamento da resposta)."""
    return f"{r1(numero):.1f}".replace(".", ",")


def _maior_sequencia(marcas):
    """A maior sequência de dias seguidos marcados: (o índice do primeiro dia, o tamanho). Sem nenhum: (None, 0)."""
    melhor, tamanho, inicio = None, 0, None
    for i, marca in enumerate(list(marcas) + [False]):
        if marca and inicio is None:
            inicio = i
        elif not marca and inicio is not None:
            if i - inicio > tamanho:
                melhor, tamanho = inicio, i - inicio
            inicio = None
    return melhor, tamanho


NOMES_NO_REPLAY = {"soja": "a soja", "milho": "o milho de 2ª safra", "sorgo": "o sorgo de 2ª safra"}


def _safra_completa(linhas, safra):
    """Se os dias vão, sem buraco, de 1 de setembro a 31 de agosto da safra (366 dias quando há 29 de fevereiro)."""
    inicio, fim = datetime.date(int(safra[:4]), 9, 1), datetime.date(int(safra[:4]) + 1, 8, 31)
    return bool(linhas) and (linhas[0]["data"], linhas[-1]["data"]) == (inicio.isoformat(), fim.isoformat()) \
        and len(linhas) == (fim - inicio).days + 1


def conferir_safra(safra):
    """Confere o nome da safra ("2015-16"): tem de ser uma das guardadas. Fora disso, erro em português."""
    safras = balanco.SAFRAS_DO_ESTUDO + (SAFRA_A_PARTE,)
    if safra not in safras:
        raise ValueError(f'Entrada fora do formato: safra "{safra}" não está guardada: use uma de {safras[0]} a '
                         f"{safras[-1]}, como 2015-16.")
    return safra


def simular_a_rotacao_de_hoje(entrada, par, dias, cal=None):
    """A conta da água, dia a dia, da rotação que o produtor faz hoje (a da entrada). Devolve (registros, a rotação).

    Na rotação com capim vale a hipótese do meio da disputa do capim com o milho (a mesma dos campos de sempre).
    """
    rotacao = rotacoes.CARDAPIO[entrada["rotacao_id"]]
    cal = cal or rotacoes.calendario(par, entrada["plantio_da_soja"])
    disputa = parametros.valor(par, "disputa_com_o_milho", CENARIO_DOS_CAMPOS_ANTIGOS) if rotacao["com_braquiaria"] else 0.0
    return balanco.simular(dias, rotacao["com_braquiaria"], par, entrada["terra"], disputa=disputa, cal=cal,
                           segunda=rotacao["segunda"]), rotacao


AGUA_QUE_CONTA_COMO_ACABADA_MM = 0.1     # a última casa que a conta mostra: até aqui o marco diz "a água acabou"


def replay_da_safra(entrada, safra="2015-16", par=None):
    """A safra dia a dia, na rotação de hoje do produtor: os dias e os marcos, para a tela passar como um filme.

    Cada dia: a data, o que está na terra, a chuva, a água na terra, o que a planta pediu, bebeu e o que faltou, se
    passou sede, a temperatura máxima e se foi dia de calor forte. Cada marco: a data, o tipo (plantio, agua_acabou,
    agua_no_fundo, calor_forte ou colheita) e uma frase pronta. As datas dos marcos saem da conta.

    "agua_acabou" é o começo da maior sequência de sede (a água fácil de tirar acabou). "agua_no_fundo" é o dia em
    que a água acabou de fato: o primeiro dia em que a água na terra chega ao menor valor do ciclo da cultura, só
    quando nesse dia a planta não conseguiu beber nada (e só com o ciclo completo nos dados guardados). A
    `situacao` dele diz o que aconteceu: "acabou" (sobrou até 0,1 mm), "perto_do_fundo" (sobrou mais que isso) ou
    "seca_no_plantio" (o dia é o do plantio: a terra já chegou seca).
    """
    entrada = validar_entrada(entrada)
    conferir_safra(safra)
    par = par or parametros.carregar()
    dias, avisos = _serie(entrada)
    cal = rotacoes.calendario(par, entrada["plantio_da_soja"])
    registros, rotacao = simular_a_rotacao_de_hoje(entrada, par, dias, cal)
    maximas = {dia.data: dia.tmax for dia in dias}
    limites = calor.limites(par)
    da_safra = [r for r in registros if balanco.nome_da_safra(r.data) == safra]
    if not da_safra:
        raise ValueError(f'Entrada fora do formato: a safra "{safra}" ainda não tem nenhum dia com dado guardado.')
    linhas, marcos, incompletas = [], [], []
    for r in da_safra:
        cultura = r.tipo in rotacoes.CULTURAS
        quente = bool(cultura and r.tipo in limites and calor.na_fase_critica(cal, r.tipo, r.data)
                      and maximas[r.data] > limites[r.tipo]["limite_c"])
        linhas.append({"data": r.data.isoformat(), "cultura": r.tipo, "chuva_mm": r1(r.chuva),
                       "agua_na_terra_mm": r1(r.agua_na_terra), "pedido_mm": r1(r.pedido), "bebido_mm": r1(r.bebido),
                       "falta_mm": r1(r.pedido - r.bebido) if cultura else 0.0,
                       "com_sede": bool(cultura and r.ks < 1.0), "tmax_c": r1(maximas[r.data]),
                       "calor_forte": quente})
    resumo = {}
    for tipo in ("soja", rotacao["segunda"]):
        indices = [i for i, r in enumerate(da_safra) if r.tipo == tipo]
        if not indices:
            continue
        nome, primeiro, ultimo = NOMES_NO_REPLAY[tipo], indices[0], indices[-1]
        falta = sum(da_safra[i].pedido - da_safra[i].bebido for i in indices)
        pedido = sum(da_safra[i].pedido for i in indices)
        sede = [da_safra[i].ks < 1.0 for i in indices]
        quentes = [i for i in indices if linhas[i]["calor_forte"]]
        ciclo = cal.soja_ciclo if tipo == "soja" else cal.segundas[tipo]["ciclo"]
        resumo[tipo] = {"falta_mm": r1(falta), "pedido_mm": r1(pedido),
                        "falta_relativa_pct": r1(100.0 * falta / pedido) if pedido > 0 else 0.0,
                        "dias": len(indices), "dias_de_sede": sum(sede), "dias_de_calor_forte": len(quentes),
                        "ciclo_completo": len(indices) == ciclo}
        marcos.append({"data": linhas[primeiro]["data"], "tipo": "plantio", "cultura": tipo,
                       "frase": f"Plantio: entra {nome}."})
        comeco, tamanho = _maior_sequencia(sede)
        if tamanho:
            dia = linhas[indices[comeco]]
            resumo[tipo]["maior_sequencia_de_sede_dias"] = tamanho
            marcos.append({"data": dia["data"], "tipo": "agua_acabou", "cultura": tipo, "dias_seguidos": tamanho,
                           "agua_na_terra_mm": dia["agua_na_terra_mm"],
                           "frase": f"Neste dia começou a sede mais longa d{nome}: a água fácil de tirar da terra "
                                    f"acabou, e foram {tamanho} dias seguidos de sede."})
        # A água no fundo: o primeiro dia em que a água na terra chega ao menor valor do ciclo, só quando nesse dia
        # a planta pediu água e não conseguiu beber nada (se a água não acabou de fato, não há marco). Os números
        # são os dos dias do replay (os que a tela mostra). Com o ciclo pela metade, o menor valor ainda não se sabe.
        menor = min(linhas[i]["agua_na_terra_mm"] for i in indices)
        fundo = next(linhas[i] for i in indices if linhas[i]["agua_na_terra_mm"] == menor)
        if resumo[tipo]["ciclo_completo"] and fundo["bebido_mm"] == 0.0 and fundo["pedido_mm"] > 0:
            # A frase diz o que aconteceu (`situacao`): no dia do plantio, a terra já chegou seca (não foi a cultura
            # que secou a terra); com até 0,1 mm (a última casa que a conta mostra), a água acabou; com mais que
            # isso, a água ficou perto do fundo, sem acabar.
            if fundo is linhas[primeiro]:
                situacao = "seca_no_plantio"
                frase = (f"No dia do plantio d{nome} a terra já estava seca: havia {_n(menor)} mm de água ao alcance "
                         "da planta, o menor valor do ciclo, e nesse dia ela não conseguiu beber nada. A terra "
                         "chegou assim ao plantio; depois deste dia a água não ficou abaixo disso.")
            elif menor <= AGUA_QUE_CONTA_COMO_ACABADA_MM:
                situacao = "acabou"
                frase = (f"Neste dia a água que a planta alcança acabou para {nome}: sobrou {_n(menor)} mm na terra, "
                         "o menor valor do ciclo, e a planta não conseguiu beber nada.")
            else:
                situacao = "perto_do_fundo"
                frase = (f"Neste dia a água que a planta alcança ficou perto do fundo para {nome}, sem acabar: "
                         f"sobraram {_n(menor)} mm na terra, o menor valor do ciclo, e a planta não conseguiu beber "
                         "nada.")
            marcos.append({"data": fundo["data"], "tipo": "agua_no_fundo", "cultura": tipo, "agua_na_terra_mm": menor,
                           "situacao": situacao, "frase": frase})
        if quentes:
            dia = linhas[quentes[0]]
            marcos.append({"data": dia["data"], "tipo": "calor_forte", "cultura": tipo, "tmax_c": dia["tmax_c"],
                           "limite_c": limites[tipo]["limite_c"], "dias_na_safra": len(quentes),
                           "frase": f"Primeiro dia de calor forte na fase crítica d{nome}: máxima de "
                                    f"{_n(dia['tmax_c'])} °C, acima do limite de "
                                    f"{explicacao._grau(limites[tipo]['limite_c'])} °C. Foram {len(quentes)} dias de "
                                    "calor forte nesta safra."})
        if not resumo[tipo]["ciclo_completo"]:      # os dados acabam com a cultura ainda na terra: sem colheita
            incompletas.append(f"Os dados guardados acabam em {explicacao.data_br(linhas[-1]['data'])}, antes do fim do ciclo d{nome}: "
                               "os números desta cultura são só até esse dia, e não há marco de colheita.")
            continue
        marcos.append({"data": linhas[ultimo]["data"], "tipo": "colheita", "cultura": tipo,
                       "falta_mm": resumo[tipo]["falta_mm"], "dias_de_sede": resumo[tipo]["dias_de_sede"],
                       "frase": f"Fim do ciclo: sai {nome}. Nesta safra faltaram {_n(falta)} mm de água para a "
                                f"cultura, com {sum(sede)} dias de sede."})
    principal = max((m for m in marcos if m["tipo"] == "agua_acabou"), key=lambda m: m["dias_seguidos"], default=None)
    for marco in marcos:
        marco["principal"] = marco is principal
    marcos.sort(key=lambda m: (m["data"], ("plantio", "agua_acabou", "agua_no_fundo", "calor_forte",
                                           "colheita").index(m["tipo"])))
    resumo["total"] = {"falta_mm": r1(sum(r.pedido - r.bebido for r in da_safra if r.tipo in rotacoes.CULTURAS)),
                       "dias_de_sede": sum(1 for r in da_safra if r.tipo in rotacoes.CULTURAS and r.ks < 1.0),
                       "dias_de_calor_forte": sum(1 for linha in linhas if linha["calor_forte"]),
                       "chuva_mm": r1(sum(r.chuva for r in da_safra))}
    nota = ("Na rotação com capim, o filme mostra a hipótese do meio da disputa do capim com o milho."
            if rotacao["com_braquiaria"] else None)
    return {"safra": safra, "cidade_id": entrada["cidade_id"], "local": dict(CIDADES[entrada["cidade_id"]],
                                                                             id=entrada["cidade_id"]),
            "rotacao": {"id": rotacao["id"], "nome": rotacao["nome"], "segunda": rotacao["segunda"]},
            "terra": entrada["terra"], "plantio_da_soja_informado": entrada["plantio_da_soja"],
            "primeiro_dia": linhas[0]["data"] if linhas else None, "ultimo_dia": linhas[-1]["data"] if linhas else None,
            "completa": _safra_completa(linhas, safra), "dias": linhas, "marcos": marcos, "resumo": resumo,
            "limites_de_calor_c": {c: limites[c]["limite_c"] for c in ("soja", rotacao["segunda"]) if c in limites},
            "avisos": list(avisos) + ([nota] if nota else []) + incompletas + [
                "A água fácil de tirar acabar não é a terra secar de todo: é o ponto em que a planta começa a passar "
                "sede (a regra é a do manual de irrigação da FAO, o órgão da ONU para a agricultura).", calor.AVISO]}


def como_esta_hoje(entrada, par=None, hoje=None):
    """O "durante": como está a água da lavoura no último dia com dado (ver `hoje.py`)."""
    from orbita import hoje as peca
    return peca.como_esta_hoje(entrada, par, hoje)


def lavoura_hoje(entrada, par=None, hoje=None):
    """O "durante" inteiro: a lavoura hoje em seis itens (a fase, a água, o calor, o verde, a terra coberta e o aviso
    de sede), cada um com a situação, a frase e a data do último dado (ver `lavoura.py`)."""
    from orbita import lavoura
    return lavoura.lavoura_hoje(entrada, par, hoje)


def registro_da_safra(entrada, safra, par=None):
    """O "depois": o registro da safra, depois da colheita (ver `registro.py`)."""
    from orbita import registro
    return registro.registro_da_safra(entrada, safra, par)


def _plantio_informado(entrada, cal):
    """O que a data de plantio do produtor fez no calendário (sem data, o calendário de costume, que é fixo)."""
    if entrada["plantio_da_soja"] is None:
        return {"plantio_da_soja_informado": None, "deslocamento_dias": 0,
                "nota_do_plantio": "Sem a data de plantio do produtor: vale o calendário de costume, com as mesmas "
                                   "datas em todos os anos."}
    return {"plantio_da_soja_informado": entrada["plantio_da_soja"], "deslocamento_dias": cal.deslocamento_dias,
            "nota_do_plantio": "A soja entra no dia e mês que o produtor informou, em todas as safras do ensaio, e a "
                               "2ª safra entra depois de a soja sair, com o mesmo intervalo do calendário de "
                               "costume: o calendário inteiro anda junto com a data dele."}


def responder(entrada, par=None, dias=None, rendimentos=None):
    """A resposta inteira do motor, pronta para virar JSON.

    `rendimentos` (safra -> kg/ha) troca o arquivo do IBGE só no nível de sede forte: serve para os testes.
    """
    entrada = validar_entrada(entrada)
    par = par or parametros.carregar()
    avisos = []
    dias_injetados = dias is not None
    if dias is None:
        dias, avisos = clima.ler_serie_com_aviso(entrada["chuva"], cidade_id=entrada["cidade_id"],
                                                 lugar=_lugar(entrada))
    cidade = CIDADES[entrada["cidade_id"]]
    pastas = clima.pastas_da_cidade(entrada["cidade_id"])
    chuvas, regra = _regra_dos_anos(entrada, dias)
    criterio = parametros.valor(par, "regras", "sede_da_2a_safra_pct")
    calendario = rotacoes.resumo_do_calendario(par, entrada["plantio_da_soja"])
    cal = rotacoes.calendario(par, entrada["plantio_da_soja"])
    agua = balanco.agua_da_terra(par, entrada["terra"], cal)
    chuva_a_parte = balanco.chuva_da_janela(dias, int(SAFRA_A_PARTE[:4]) + 1)
    sede_forte, nivel = _sede_forte(par, entrada, dias, dias_injetados, rendimentos)
    reducao = parametros.valor(par, "palha", "reducao_por_cobertura")

    def palha(com_braquiaria, de_que, chave):
        cobertura = cal.cobertura_de_palha[com_braquiaria]
        return {"de_que": de_que, "cobertura_pct": r1(100 * cobertura),
                "evaporacao_a_menos_pct": r1(100 * reducao * cobertura),
                "onde_vale": "nos dias sem planta viva e na fase inicial da soja",
                "regra": "FAO-56, cap. 10: a evaporação da terra cai uns 5% a cada 10% de terra coberta por palha",
                "etiqueta_da_cobertura": par["palha"][chave]["etiqueta"]}

    def numeros(com_braquiaria, disputa=0.0):
        bloco, parte, falta = _numeros_da_rotacao(dias, com_braquiaria, par, entrada["terra"], chuvas,
                                                   chuva_a_parte, criterio, disputa, cal)
        bloco["safras_com_sede_forte"] = _com_sede_forte(falta["milho_pct"], nivel, sede_forte["safras_de_quebra"])
        return bloco, parte, falta

    rot, a_parte = {}, {}
    bloco, a_parte["atual"], falta_de_hoje = numeros(False)
    rot["atual"] = dict({"nome": rotacoes.ROTACOES["atual"]["nome"], "sem_planta_viva": calendario["atual"]}, **bloco,
                        palha=palha(False, "a palha do milho", "cobertura_do_milho_solteiro"))
    cenarios, a_parte_por_cenario, falta_por_cenario = {}, {}, {}
    for cenario in CENARIOS:
        fator = parametros.valor(par, "disputa_com_o_milho", cenario)
        bloco, a_parte_por_cenario[cenario], falta_por_cenario[cenario] = numeros(True, fator)
        cenarios[cenario] = dict({"fator": fator, "pedido_a_mais_pct": r1(100 * fator)}, **bloco)
    base = cenarios[CENARIO_DOS_CAMPOS_ANTIGOS]
    faixa = {}
    for s in balanco.SAFRAS_DO_ESTUDO:
        linhas = [cenarios[c]["safras"][s] for c in CENARIOS]
        faixa[s] = {"falta_do_milho_mm": _menor_e_maior([x["milho"]["falta_mm"] for x in linhas]),
                    "falta_do_milho_pct": _menor_e_maior([x["milho"]["falta_relativa_pct"] for x in linhas]),
                    "falta_total_mm": _menor_e_maior([x["total"]["falta_mm"] for x in linhas]),
                    "dias_de_sede": _menor_e_maior([x["total"]["dias_de_sede"] for x in linhas])}
    forte = dict(base["safras_com_sede_forte"])
    if nivel is not None:
        forte["faixa"] = _menor_e_maior([cenarios[c]["safras_com_sede_forte"]["quantas"] for c in CENARIOS])
    rot["alternativa"] = {
        "nome": rotacoes.ROTACOES["alternativa"]["nome"], "sem_planta_viva": calendario["alternativa"],
        "safras": base["safras"], "safras_com_sede": base["safras_com_sede"],
        "soma_das_10_safras": base["soma_das_10_safras"], "safras_com_sede_forte": forte,
        "palha": palha(True, "a palha do milho e do capim", "cobertura_do_milho_com_braquiaria"),
        "disputa_com_o_milho": {
            "o_que_e": "enquanto o milho e o capim crescem juntos, o conjunto pede (1 + fator) vezes a água que o "
                       "milho pede sozinho; o quanto é esse fator não foi medido, e por isso a alternativa sai em "
                       "três cenários, do menor ao maior efeito",
            "etiqueta": "hipótese", "nos_campos_antigos": CENARIO_DOS_CAMPOS_ANTIGOS, "cenarios": cenarios},
        "faixa": faixa,
        "faixa_da_soma_das_10_safras": {
            chave: _menor_e_maior([cenarios[c]["soma_das_10_safras"][chave] for c in CENARIOS])
            for chave in ("falta_da_soja_mm", "falta_do_milho_mm", "dias_de_sede")}}
    if "sorgo" in cal.segundas:     # a terceira rotação: a mesma conta, com o sorgo no lugar do milho
        bloco, a_parte["com_sorgo"], falta_com_sorgo = _numeros_da_rotacao(
            dias, False, par, entrada["terra"], chuvas, chuva_a_parte, criterio, 0.0, cal, "sorgo")
        rot["com_sorgo"] = dict(
            {"nome": rotacoes.ROTACOES["com_sorgo"]["nome"], "sem_planta_viva": calendario["com_sorgo"]}, **bloco,
            palha=dict(palha(False, "a palha do sorgo", "cobertura_do_milho_solteiro"),
                       nota="a cobertura da palha do sorgo não tem número próprio: vale a do milho solteiro, que "
                            "já é hipótese"),
            nota_da_sede_forte="o nível de sede forte sai da colheita do milho no IBGE: não vale para o sorgo")
    a_parte["alternativa"] = a_parte_por_cenario[CENARIO_DOS_CAMPOS_ANTIGOS]
    a_parte["faixa_da_alternativa"] = {"falta_do_milho_pct": _menor_e_maior(
        [a_parte_por_cenario[c]["milho"]["falta_relativa_pct"] for c in CENARIOS])}
    pior, normal = regra["pior_ano"], regra["ano_normal"]
    falta_no_pior_ano = {"atual": falta_de_hoje["total_mm"][pior],
                         "alternativa": falta_por_cenario[CENARIO_DOS_CAMPOS_ANTIGOS]["total_mm"][pior]}
    comparacao_da_agua = comparar_agua(
        falta_no_pior_ano["atual"], falta_no_pior_ano["alternativa"],
        rot["atual"]["safras_com_sede"]["quantas"], rot["alternativa"]["safras_com_sede"]["quantas"],
        parametros.valor(par, "regras", "empate_mm"))

    def pela_faixa(safra):
        return veredito_da_agua_pela_faixa(falta_de_hoje["total_mm"][safra],
                                           {c: falta_por_cenario[c]["total_mm"][safra] for c in CENARIOS},
                                           parametros.valor(par, "regras", "empate_mm"))

    agua_pela_faixa = dict(pela_faixa(pior), medida="a falta de água da soja e do milho no pior ano, nas duas pontas "
                           "da faixa da disputa do capim com o milho", safra=pior)
    no_ano_normal = pela_faixa(normal)
    comparacao_da_agua.update(
        pela_faixa=agua_pela_faixa,
        no_ano_normal={"safra": normal, "codigo": no_ano_normal["codigo"], "diferenca_mm": no_ano_normal["diferenca_mm"],
                       "por_cenario": no_ano_normal["por_cenario"]},
        nota="os campos antigos (melhor, pela_falta_no_pior_ano, pelas_safras_com_sede, diferenca_mm) comparam a "
             "rotação de hoje com a alternativa na hipótese do meio, como antes comparavam com a alternativa única; "
             "o veredito da água, que olha as duas pontas da faixa, está em 'pela_faixa'")
    dias_hoje = calendario["atual"]["dias_sem_planta_viva"]
    dias_alternativa = calendario["alternativa"]["dias_sem_planta_viva"]
    solo = "empate" if dias_hoje == dias_alternativa else ("alternativa" if dias_alternativa < dias_hoje else "atual")
    melhores = {"agua": comparacao_da_agua["melhor"], "solo": solo, "erosao": solo, "renda": NAO_MEDIDO}
    notas = entrada["prioridades"]
    na_frente = NA_FRENTE.get(entrada["preocupacao"], ())
    if notas is None:       # sem as notas: a ordem de costume, com a preocupação do produtor na frente
        ordem = list(na_frente) + [p for p in ORDEM_DE_DESEMPATE if p not in na_frente]
    else:                   # com as notas, como antes: a maior nota primeiro (a preocupação só desempata)
        ordem = sorted(ORDEM_DE_DESEMPATE, key=lambda p: (-notas[p], p not in na_frente))
    medidas = {"agua": "a falta de água da soja e do milho no pior ano, com a alternativa em faixa (a disputa do "
                       "capim com o milho), e as safras de sede forte",
               "solo": "os dias do ano sem planta viva na terra (o mesmo número da erosão)",
               "erosao": "os dias do ano sem planta viva na terra (o mesmo número do solo)",
               "renda": "não medido: o motor não tem preço, custo nem produtividade"}
    prioridades = [{"id": p, "nome": NOMES[p], "nota": None if notas is None else notas[p], "melhor": melhores[p],
                    "medida": medidas[p]} for p in ordem]
    for p in prioridades:
        if p["id"] == "agua":
            p["veredito_pela_faixa"] = agua_pela_faixa["codigo"]
    primeira_medida = next(p for p in prioridades if p["melhor"] != NAO_MEDIDO)
    safras_do_calor = balanco.SAFRAS_DO_ESTUDO + (SAFRA_A_PARTE,)
    bloco_do_calor = calor.bloco(dias, cal, par, safras_do_calor, pior, normal, {
        rotacao["id"]: ["soja", rotacao["segunda"]] for chave, rotacao in rotacoes.ROTACOES.items() if chave in rot})
    if notas is None and entrada["preocupacao"] == "calor":    # a preocupação é o calor: ele vira o destaque
        por_rotacao = bloco_do_calor["por_rotacao"]
        compara = quem_ganha(por_rotacao["soja_milho_braquiaria"]["dias_no_pior_ano"],
                             por_rotacao["soja_milho_pousio"]["dias_no_pior_ano"], 1)
        primeira_medida = {"id": "calor", "nome": NOMES["calor"], "nota": None,
                           "melhor": {"melhor": "alternativa", "pior": "atual"}.get(compara, "empate")}
    verde = verde_do_satelite(entrada["cidade_id"], dias_hoje, par)
    terra_coberta = {
        "o_que_e": "dias_sem_planta_viva: os dias seguidos sem planta viva antes do plantio da soja, pelo calendário de "
                   "cada rotação (o número de sempre, o que se compara com o satélite); dias_sem_planta_viva_no_ano: "
                   "o ano inteiro, contando também o intervalo entre a soja e a 2ª safra; e, onde há medida, os dias "
                   "seguidos sem planta verde vistos pelo satélite",
        "por_rotacao": {rotacoes.ROTACOES[chave]["id"]: dict(calendario[chave], dias_sem_planta_viva_no_ano=(
            rotacoes.dias_sem_planta_no_ano(cal, rotacoes.ROTACOES[chave]["com_braquiaria"],
                                            rotacoes.ROTACOES[chave]["segunda"]))) for chave in rot},
        "pelo_satelite": verde,
        "aviso": "O satélite prova só a rotação de hoje da região (soja, milho e pousio): é o que está no chão nos "
                 "pontos medidos. Nas outras rotações, os dias sem planta viva vêm só do calendário."}
    temperatura = clima.origem_da_serie(pastas["nasa_power"])    # a hora da temperatura, para os textos de antes
    if entrada["chuva"] == "power":
        aviso_a_parte = ("a conferir: a chuva de 2025 na NASA POWER é suspeita de baixa; esta safra fica fora das 10 "
                         "e fora da regra dos anos")
    else:
        aviso_a_parte = ("a conferir: é a safra mais recente, com o dado ainda provisório; fica fora das 10 e fora "
                         "da regra dos anos")
    resposta = {
        "aviso": "Motor provisório, sem site. Não é recomendação agronômica: valide com o agrônomo.",
        "pergunta": "Com o clima que a NASA registrou na minha região, vale trocar a minha rotação de hoje por outra?",
        "entrada": entrada,
        "local": dict(cidade, id=entrada["cidade_id"]),
        "clima": _clima(entrada, dias, avisos),
        "terra": {"opcao": entrada["terra"], "classe": parametros.valor(par, "terra", entrada["terra"], "classe"),
                  "agua_por_metro_mm": r1(agua["agua_mm_por_m"]),
                  "raizes_m": {tipo: raiz for tipo, raiz in agua["raizes_m"].items()},
                  "agua_que_segura_mm": {tipo: r1(valor) for tipo, valor in agua["taw"].items()}},
        "calendario": dict({k: calendario[k] for k in ("soja", "milho", "sorgo", "braquiaria",
                                                       "entre_a_soja_e_o_milho_dias") if k in calendario},
                           **_plantio_informado(entrada, cal)),
        "rotacao_de_hoje": {"id": entrada["rotacao_id"], "nome": rotacoes.CARDAPIO[entrada["rotacao_id"]]["nome"],
                            "chave": rotacoes.CARDAPIO[entrada["rotacao_id"]]["chave"],
                            "nota": "As chaves de sempre (rotacoes.atual, rotacoes.alternativa, comparacao, veredito, "
                                    "prioridades e destaque) comparam soja-milho-pousio com soja-milho-braquiária, "
                                    "no lugar, na terra e na data do produtor; a rotação que ele faz hoje é esta, e "
                                    "a comparação das três está em comparacao_das_rotacoes."},
        "regra_dos_anos": regra,
        "rotacoes": rot,
        "comparacao": {"ano_normal": normal, "pior_ano": pior, "agua": comparacao_da_agua,
                       "solo_e_erosao": {"melhor": solo, "dias_sem_planta_viva_hoje": dias_hoje,
                                         "dias_sem_planta_viva_alternativa": dias_alternativa}},
        "prioridades": prioridades,
        "preocupacao": entrada["preocupacao"],
        "ordem_das_pernas": [p for p in PERNAS if p == entrada["preocupacao"]] + [
            p for p in PERNAS if p != entrada["preocupacao"]],
        "sede_forte": sede_forte,
        "destaque": dict({"prioridade": primeira_medida["id"], "nome": primeira_medida["nome"],
                          "nota": primeira_medida["nota"], "melhor": primeira_medida["melhor"]},
                         **({"veredito_pela_faixa": agua_pela_faixa["codigo"]} if primeira_medida["id"] == "agua"
                            else {})),
        "veredito": veredito(melhores, agua_pela_faixa["codigo"]),
        "safra_2025_26": dict(a_parte, safra=SAFRA_A_PARTE, aviso=aviso_a_parte,
                              chuva_da_janela_mm=r1(chuva_a_parte)),
        "ndvi": _ndvi(par, dias_hoje, entrada["cidade_id"]),
        "parametros": [{"parametro": c, "valor": p["valor"], "etiqueta": p["etiqueta"], "fonte": p["fonte"],
                        "trecho": p["trecho"]} for c, p in parametros.folhas(par)],
        "hipoteses": len(parametros.hipoteses(par)),
        "limites": list(LIMITES),
        "calor": bloco_do_calor,
        "terra_coberta": terra_coberta,
    }
    da_alternativa = [falta_por_cenario[c]["total_mm"][pior] for c in CENARIOS]
    faltas_exatas = {"soja_milho_pousio": falta_de_hoje["total_mm"][pior],
                     "soja_milho_braquiaria": {"de": min(da_alternativa), "ate": max(da_alternativa)}}
    if "com_sorgo" in rot:
        faltas_exatas["soja_sorgo_pousio"] = falta_com_sorgo["total_mm"][pior]
    resposta["comparacao_das_rotacoes"] = _comparacao_das_rotacoes(
        entrada, rot, calendario, bloco_do_calor, verde, pior, normal, parametros.valor(par, "regras", "empate_mm"),
        resposta, faltas_exatas,
        {ident: bloco["dias_sem_planta_viva_no_ano"] for ident, bloco in terra_coberta["por_rotacao"].items()})
    return resposta
