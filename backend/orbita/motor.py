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
    "É um caso só: Rio Verde (GO), uma rotação de hoje e uma alternativa, com um calendário fixo (as mesmas datas "
    "de plantio em todos os anos).",
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
                 "conforme a hipótese da disputa do capim com o milho (a conta mostra as duas pontas da faixa).")
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


def _safra(numeros, agua_no_plantio, chuva, com_braquiaria):
    saida = {"chuva_da_janela_mm": r1(chuva), "soja": _conta(numeros["soja"]), "milho": _conta(numeros["milho"]),
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


def _numeros_da_rotacao(dias, com_braquiaria, par, terra, chuvas, chuva_a_parte, criterio, disputa=0.0):
    """As 10 safras de uma rotação (num cenário de disputa), a safra mais recente à parte e a falta sem arredondar."""
    registros = balanco.simular(dias, com_braquiaria, par, terra, disputa=disputa)
    numeros = balanco.numeros_por_safra(registros)
    no_plantio = balanco.agua_no_plantio_da_soja(registros)
    tabela = {s: _safra(numeros[s], no_plantio.get(s), chuvas[s], com_braquiaria) for s in balanco.SAFRAS_DO_ESTUDO}
    bloco = {"safras": tabela,
             "safras_com_sede": _com_sede({s: numeros[s]["milho"]["falta_relativa_pct"] for s in tabela}, criterio),
             "soma_das_10_safras": {
                 "falta_da_soja_mm": r1(sum(numeros[s]["soja"]["falta_mm"] for s in tabela)),
                 "falta_do_milho_mm": r1(sum(numeros[s]["milho"]["falta_mm"] for s in tabela)),
                 "dias_de_sede": sum(numeros[s]["total"]["dias_de_sede"] for s in tabela)}}
    sem_arredondar = {"total_mm": {s: numeros[s]["total"]["falta_mm"] for s in tabela},      # para comparar: 4,96 mm
                      "milho_pct": {s: numeros[s]["milho"]["falta_relativa_pct"] for s in tabela}}   # não é 5
    return (bloco, _safra(numeros[SAFRA_A_PARTE], no_plantio.get(SAFRA_A_PARTE), chuva_a_parte, com_braquiaria),
            sem_arredondar)


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
             "fonte_do_rendimento": "IBGE, Produção Agrícola Municipal (SIDRA), Rio Verde (GO), milho de 2ª safra",
             "aviso": AVISO_DA_SEDE_FORTE}
    try:
        if rendimentos is None:
            rendimentos = ler_rendimento_do_milho()
        if dias_injetados or entrada["chuva"] == CHUVA_PADRAO:
            dias_da_referencia = dias
        else:
            dias_da_referencia, _ = clima.ler_serie_com_aviso(CHUVA_PADRAO)
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


def _com_sede(faltas_do_milho, criterio):
    """`faltas_do_milho`: safra -> falta relativa do milho em %, sem arredondar (19,96% não é 20%)."""
    quais = [s for s, falta in faltas_do_milho.items() if falta >= criterio]
    return {"criterio_pct": criterio, "quantas": len(quais), "quais": quais,
            "com_10_pct": sum(1 for falta in faltas_do_milho.values() if falta >= 10),
            "com_30_pct": sum(1 for falta in faltas_do_milho.values() if falta >= 30)}


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


def responder(entrada, par=None, dias=None, rendimentos=None):
    """A resposta inteira do motor, pronta para virar JSON.

    `rendimentos` (safra -> kg/ha) troca o arquivo do IBGE só no nível de sede forte: serve para os testes.
    """
    entrada = validar_entrada(entrada)
    par = par or parametros.carregar()
    avisos = []
    dias_injetados = dias is not None
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
    sede_forte, nivel = _sede_forte(par, entrada, dias, dias_injetados, rendimentos)
    cal = rotacoes.calendario(par)
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
                                                   chuva_a_parte, criterio, disputa)
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
    ordem = sorted(ORDEM_DE_DESEMPATE, key=lambda p: -notas[p])
    medidas = {"agua": "a falta de água da soja e do milho no pior ano, com a alternativa em faixa (a disputa do "
                       "capim com o milho), e as safras de sede forte",
               "solo": "os dias do ano sem planta viva na terra (o mesmo número da erosão)",
               "erosao": "os dias do ano sem planta viva na terra (o mesmo número do solo)",
               "renda": "não medido: o motor não tem preço, custo nem produtividade"}
    prioridades = [{"id": p, "nome": NOMES[p], "nota": notas[p], "melhor": melhores[p], "medida": medidas[p]}
                   for p in ordem]
    for p in prioridades:
        if p["id"] == "agua":
            p["veredito_pela_faixa"] = agua_pela_faixa["codigo"]
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
        "sede_forte": sede_forte,
        "destaque": dict({"prioridade": primeira_medida["id"], "nome": primeira_medida["nome"],
                          "nota": primeira_medida["nota"], "melhor": primeira_medida["melhor"]},
                         **({"veredito_pela_faixa": agua_pela_faixa["codigo"]} if primeira_medida["id"] == "agua"
                            else {})),
        "veredito": veredito(melhores, agua_pela_faixa["codigo"]),
        "safra_2025_26": dict(a_parte, safra=SAFRA_A_PARTE, aviso=aviso_a_parte,
                              chuva_da_janela_mm=r1(chuva_a_parte)),
        "ndvi": _ndvi(par, dias_hoje),
        "parametros": [{"parametro": c, "valor": p["valor"], "etiqueta": p["etiqueta"], "fonte": p["fonte"],
                        "trecho": p["trecho"]} for c, p in parametros.folhas(par)],
        "hipoteses": len(parametros.hipoteses(par)),
        "limites": list(LIMITES),
    }
