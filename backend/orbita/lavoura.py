# Gerado com IA (Claude)
"""A lavoura hoje: o acompanhamento durante a safra, com todos os indicadores que o motor já tem (2026-11-15).

O "como está hoje" (`hoje.py`) responde só a água. Este painel junta seis itens, no último dia com dado:
1. a fase da cultura (o calendário e as fases da tabela da FAO, as mesmas do consumo de água e do calor);
2. a água (os números do "como está hoje", mais há quantos dias seguidos a lavoura está com sede);
3. o calor (os dias com a máxima acima do limite da cultura desde o plantio e na fase atual, ao lado do mesmo
   número, no mesmo dia do ciclo, nas 10 safras guardadas);
4. o verde do satélite (a imagem mais recente contra a mesma época dos outros anos guardados);
5. a terra coberta (há quantos dias seguidos a terra está com planta viva, ou sem, pelo calendário);
6. o aviso de sede (se não chover, em quantos dias a água chega ao nível de sede: a mesma conta da água, seguida
   para a frente com chuva zero e com o tempo dos últimos 7 dias com dado). Não é previsão do tempo.
Cada item leva a situação (tranquilo, atenção, alerta ou sem dado) por uma regra fixa, escrita em `REGRAS`, uma
frase em palavras de produtor e a data do último dado que usou, dizendo de qual dado é.

Nenhum número novo: os limites, as fases e os parâmetros são os que o motor já tem com fonte. O que é escolha desta
peça (as regras de situação, os 7 dias, os 30 dias e os 3 anos do verde) está em `REGRAS` e no `LEIA-ME-motor.md`.
O motor não baixa nada na hora da pergunta: lê o que está guardado.
"""
import datetime
import statistics

from orbita import balanco, calor, clima, ndvi, parametros, rotacoes
from orbita import hoje as retrato_de_hoje
from orbita.explicacao import _grau, data_br

UM_DIA = datetime.timedelta(days=1)
JANELA_DO_CONSUMO_DIAS = 7          # os últimos dias com dado que dão o tempo da conta para a frente (escolha)
HORIZONTE_SEM_CHUVA_DIAS = 30       # até onde a conta para a frente vai, sem chuva nenhuma (escolha)
MINIMO_DE_ANOS_DO_VERDE = 3         # com menos anos na mesma época, o verde não é comparado (escolha)
ITENS = ("fase", "agua", "calor", "verde", "terra_coberta", "aviso_de_sede")
SITUACOES = ("tranquilo", "atencao", "alerta", "sem_dado")
NOMES_DAS_SITUACOES = {"tranquilo": "tranquilo", "atencao": "atenção", "alerta": "alerta", "sem_dado": "sem dado"}
PESO = {"sem_dado": 0, "tranquilo": 1, "atencao": 2, "alerta": 3}
TITULOS = {"fase": "A fase da cultura", "agua": "A água", "calor": "O calor", "verde": "O verde do satélite",
           "terra_coberta": "A terra coberta", "aviso_de_sede": "O aviso de sede"}
NOMES_DOS_ITENS = {"fase": "a fase da cultura", "agua": "a água", "calor": "o calor", "verde": "o verde do satélite",
                   "terra_coberta": "a terra coberta", "aviso_de_sede": "o aviso de sede"}
# As quatro fases da tabela da FAO (FAO-56, Tabela 11), na ordem; a do meio é a fase crítica do motor (`calor.py`).
FASES = (("inicial", "no começo do ciclo"), ("crescimento", "em crescimento"),
         ("critica", "na fase crítica (a floração e o enchimento do grão)"), ("final", "no fim do ciclo (a maturação)"))
NA_TERRA = retrato_de_hoje.NA_TERRA
PLANTADA = {"soja": "plantada", "milho": "plantado", "sorgo": "plantado"}
REGRAS = {
    "fase": "Atenção: a cultura está na fase crítica (a floração e o enchimento do grão), quando a falta de água e "
            "o calor mais pesam. Tranquilo: nas outras fases, ou sem cultura na terra.",
    "agua": "Alerta: a cultura está com sede no último dia com dado (a água fácil de tirar da terra acabou). "
            "Tranquilo: sem sede, ou sem cultura na terra. A água não tem 'atenção': quem avisa antes é o aviso de "
            "sede.",
    "calor": "Alerta: já houve dia de calor forte (a máxima acima do limite da cultura) dentro da fase crítica desta "
             "safra. Atenção: sem isso, mas os dias de calor forte desde o plantio passam do valor do meio das "
             "safras guardadas no mesmo dia do ciclo. Tranquilo: o resto, ou sem cultura na terra.",
    "verde": "Abaixo do normal: o verde da imagem mais recente fica abaixo do menor valor da mesma época nos outros "
             "anos guardados; acima do normal: acima do maior; dentro do normal: entre os dois. Atenção: abaixo do "
             "normal com cultura na terra no fim da imagem. Tranquilo: dentro ou acima, ou abaixo sem cultura na "
             "terra. Sem dado: sem imagem com medida boa, ou menos de 3 outros anos na mesma época. O verde nunca "
             "dá alerta sozinho: os pontos são da região, não da lavoura.",
    "terra_coberta": "Tranquilo: a terra está com planta viva pelo calendário. Atenção: a terra está sem planta "
                     "viva.",
    "aviso_de_sede": "Alerta: a cultura já está com sede. Atenção: sem chuva, a sede chega em até 7 dias. "
                     "Tranquilo: mais de 7 dias, não chega nos 30 dias da conta, ou sem cultura na terra.",
}
AVISO = (retrato_de_hoje.AVISO + " A fase vem do calendário e da tabela da FAO, não de visita à lavoura. O verde do "
         "satélite é de pontos da região, escolhidos no mapa, não da lavoura. O aviso de sede não usa previsão do "
         "tempo: é a conta seguida para a frente sem chuva nenhuma.")
DE_QUAL_DADO = {
    "fase": "o calendário da rotação e as fases da tabela da FAO (não é medida da lavoura), contados até o último "
            "dia com dado da conta da água",
    "agua": "a conta da água: o último dia em que há a temperatura (a da NASA POWER) e a chuva do satélite em mm "
            "de cada dia (o GPM IMERG), as duas",
    "calor": "a temperatura máxima de cada dia, da NASA POWER (um quadrado de uns 50 km), até o último dia com dado "
             "da conta da água",
    "verde": "a imagem mais recente do satélite com medida boa nos pontos da região (o produto MOD13Q1, da NASA, "
             "que junta 16 dias a partir desta data)",
    "terra_coberta": "o calendário da rotação (não é medida da lavoura), contado até o último dia com dado da conta "
                     "da água",
    "aviso_de_sede": "a conta da água até este dia; daí para a frente é a conta sem chuva nenhuma, não é dado",
}
O_QUE_E_O_VERDE = ("O verde do satélite é um índice de 0 a 1: perto de 1, muita planta verde; perto de 0,2, quase "
                   "nenhuma. Cada imagem junta 16 dias.")


def _n(numero):
    return f"{numero:.1f}".replace(".", ",")


def _v(numero):
    """O verde, com duas casas: 0.4414 -> "0,44"."""
    return f"{numero:.2f}".replace(".", ",")


def _dias(numero):
    """Dias em palavras: "nenhum dia", "1 dia", "12 dias", "2,5 dias"."""
    if numero == 0:
        return "nenhum dia"
    return "1 dia" if numero == 1 else f"{ndvi._br(numero)} dias"


def _quantos_dias(numero):
    """Dias com o número sempre escrito: "0 dias", "1 dia", "2,5 dias"."""
    return "1 dia" if numero == 1 else f"{ndvi._br(numero)} dias"


def _meio(valores):
    return ndvi._inteiro_se_der(statistics.median(valores))


def pior_situacao(situacoes):
    """A situação do topo: a pior dos itens (alerta, depois atenção, depois tranquilo). "Sem dado" não conta."""
    com_dado = [s for s in situacoes if PESO[s]]
    return max(com_dado, key=PESO.get) if com_dado else "tranquilo"


# ------------------------------------------------------------------------------------------------ 1. a fase
def fase_no_dia(cal, segunda, data):
    """A cultura que está na terra no dia, pelo calendário: o plantio, os dias desde o plantio e a fase. Sem
    cultura (pousio, capim ou o intervalo entre a soja e a 2ª safra): None.

    As fases são as quatro da tabela da FAO que o motor já usa no consumo de água; a do meio é a fase crítica.
    """
    candidatos = [("soja", cal.plantio_da_soja(ano), cal.soja_fases) for ano in (data.year, data.year - 1)]
    candidatos += [(segunda, cal.plantio_da_segunda(ano, segunda), cal.segundas[segunda]["fases"])
                   for ano in (data.year, data.year + 1)]
    for cultura, plantio, fases in candidatos:
        n = (data - plantio).days
        if not 0 <= n < sum(fases):
            continue
        critica_de = plantio + datetime.timedelta(days=fases[0] + fases[1])
        comeco = 0
        for (ident, nome), tamanho in zip(FASES, fases):
            if n < comeco + tamanho:
                return {"cultura": cultura, "plantio": plantio.isoformat(), "dias_desde_o_plantio": n,
                        "ciclo_dias": sum(fases), "fase": ident, "fase_nome": nome,
                        "fase_comecou_em": (plantio + datetime.timedelta(days=comeco)).isoformat(),
                        "dia_da_fase": n - comeco + 1, "dias_da_fase": tamanho, "fase_critica": ident == "critica",
                        "fase_critica_de": critica_de.isoformat(),
                        "fase_critica_ate": (critica_de + datetime.timedelta(days=fases[2] - 1)).isoformat(),
                        "dias_para_a_fase_critica": max(0, (critica_de - data).days),
                        "sai_da_terra_em": (plantio + datetime.timedelta(days=sum(fases))).isoformat()}
            comeco += tamanho
    return None


def proximo_plantio(cal, segunda, data):
    """O próximo plantio do calendário depois do dia: a cultura, a data e quantos dias faltam."""
    plantios = [("soja", cal.plantio_da_soja(ano)) for ano in (data.year, data.year + 1)]
    plantios += [(segunda, cal.plantio_da_segunda(ano, segunda)) for ano in (data.year, data.year + 1)]
    cultura, dia = min((p for p in plantios if p[1] > data), key=lambda p: p[1])
    return {"cultura": cultura, "data": dia.isoformat(), "faltam_dias": (dia - data).days}


def situacao_da_fase(fase_critica):
    return "atencao" if fase_critica else "tranquilo"


def _item_da_fase(cal, rotacao, tipo, ultimo, hoje):
    fase = fase_no_dia(cal, rotacao["segunda"], ultimo) if tipo in rotacoes.CULTURAS else None
    if fase is None:
        proximo = proximo_plantio(cal, rotacao["segunda"], ultimo)
        estado = "com a braquiária (o capim) viva" if tipo == rotacoes.BRAQUIARIA else "sem planta viva"
        frase = (f"Em {data_br(ultimo)}, o último dia com dado, a terra estava {estado}. Pelo calendário, "
                 f"{NA_TERRA[proximo['cultura']]} entra em {data_br(proximo['data'])}: faltavam "
                 f"{_dias(proximo['faltam_dias'])}.")
        return {"situacao": situacao_da_fase(False), "frase": frase, "o_que_esta_na_terra": tipo, "cultura": None,
                "proximo_plantio": proximo}
    na_consulta = fase_no_dia(cal, rotacao["segunda"], hoje)
    if na_consulta is not None and na_consulta["plantio"] == fase["plantio"]:
        na_consulta = {"data": hoje.isoformat(), "dias_desde_o_plantio": na_consulta["dias_desde_o_plantio"],
                       "fase": na_consulta["fase"], "fase_critica": na_consulta["fase_critica"]}
    else:
        na_consulta = None
    nome = NA_TERRA[fase["cultura"]]
    frase = (f"Na terra está {nome}, {PLANTADA[fase['cultura']]} em {data_br(fase['plantio'])}. Em {data_br(ultimo)}, "
             f"o último dia com dado, fazia {_dias(fase['dias_desde_o_plantio'])} do plantio e a lavoura estava "
             f"{fase['fase_nome']}, no dia {fase['dia_da_fase']} dos {fase['dias_da_fase']} dessa fase.")
    if fase["fase_critica"]:
        frase += (f" É a fase em que a falta de água e o calor mais pesam; ela vai até "
                  f"{data_br(fase['fase_critica_ate'])}.")
    elif fase["fase"] != "final":
        frase += (f" A fase crítica (a floração e o enchimento do grão) começa em {data_br(fase['fase_critica_de'])}, "
                  f"pelo calendário.")
    if na_consulta is not None and hoje != ultimo:
        frase += (f" No dia desta consulta ({data_br(hoje)}), {_dias(na_consulta['dias_desde_o_plantio'])} do "
                  "plantio.")
    return dict(fase, situacao=situacao_da_fase(fase["fase_critica"]), frase=frase, o_que_esta_na_terra=tipo,
                no_dia_da_consulta=na_consulta, proximo_plantio=None)


# ------------------------------------------------------------------------------------------------ 2. a água
def com_sede(r):
    """O dia de sede do motor: há cultura na terra e o freio da sede está puxado (a água fácil de tirar acabou)."""
    return r.tipo in rotacoes.CULTURAS and r.ks < 1.0


def dias_seguidos(registros, condicao):
    """Quantos dias seguidos cumprem a condição, contando para trás a partir do último dia."""
    quantos = 0
    for r in reversed(registros):
        if not condicao(r):
            break
        quantos += 1
    return quantos


def situacao_da_agua(ha_cultura, sede):
    return "alerta" if ha_cultura and sede else "tranquilo"


def _item_da_agua(retrato, contas, ultimo):
    tipo, ha_cultura = retrato["o_que_esta_na_terra"], retrato["o_que_esta_na_terra"] in rotacoes.CULTURAS
    sede = dias_seguidos(contas["registros"], com_sede)
    pelo_modelo = retrato["com_a_chuva_de_modelo"]
    normal, pior = retrato["no_ano_normal"], retrato["no_pior_ano"]
    chuva_ate = (retrato["chuva_recente"]["fonte"] or {}).get("ultimo_dia_com_dado")
    onde = "ao alcance da planta" if ha_cultura else "na terra"
    frase = (f"Em {data_br(ultimo)}, a conta dava {_n(retrato['agua_na_terra_mm'])} mm de água {onde}, "
             f"{_n(retrato['agua_na_terra_pct'])}% do que a terra segura: ")
    if not ha_cultura:
        frase += "não havia cultura na terra para passar sede."
    elif sede:
        frase += f"{NA_TERRA[tipo]} estava com sede havia {_dias(sede)} seguidos."
    else:
        frase += f"{NA_TERRA[tipo]} não estava com sede."
    frase += (f" No mesmo dia do ano normal (safra {normal['safra']}) havia {_n(normal['agua_na_terra_mm'])} mm; "
              f"no do pior ano (safra {pior['safra']}), {_n(pior['agua_na_terra_mm'])} mm.")
    if chuva_ate:
        frase += f" A chuva do satélite já guardada vai até {data_br(chuva_ate)}."
    campos = ("data", "safra", "agua_na_terra_mm", "agua_na_terra_pct", "com_sede", "diferenca_mm", "leitura")
    return {"situacao": situacao_da_agua(ha_cultura, bool(sede)), "frase": frase,
            "o_que_esta_na_terra": tipo, "agua_na_terra_mm": retrato["agua_na_terra_mm"],
            "agua_que_a_terra_segura_mm": retrato["agua_que_a_terra_segura_mm"],
            "agua_na_terra_pct": retrato["agua_na_terra_pct"], "com_sede": retrato["com_sede"],
            "dias_seguidos_de_sede": sede, "chuva_do_satelite_ate": chuva_ate,
            "com_a_chuva_de_modelo": {"agua_na_terra_mm": pelo_modelo["agua_na_terra_mm"],
                                      "agua_na_terra_pct": pelo_modelo["agua_na_terra_pct"],
                                      "com_sede": pelo_modelo["com_sede"],
                                      "o_que_e": "só para comparar: a mesma conta com a chuva estimada por modelo de "
                                                 "computador (a da NASA POWER) nos dias recentes"},
            "faixa_da_agua_na_terra_mm": retrato["faixa_da_agua_na_terra_mm"],
            "chuva_desde_1_de_setembro_mm": retrato["chuva_desde_1_de_setembro_mm"],
            "no_ano_normal": {campo: normal[campo] for campo in campos},
            "no_pior_ano": {campo: pior[campo] for campo in campos}}


# ------------------------------------------------------------------------------------------------ 3. o calor
def dias_acima(maximas, de, ate, limite):
    """Os dias de `de` a `ate` (os dois contam) com a máxima acima do limite. `maximas`: data -> °C.

    Devolve None se algum dia não tem temperatura guardada (a conta não inventa clima).
    """
    datas = [de + datetime.timedelta(days=i) for i in range((ate - de).days + 1)]
    if any(data not in maximas for data in datas):
        return None
    return sum(1 for data in datas if maximas[data] > limite)


def situacao_do_calor(na_fase_critica, desde_o_plantio, valor_do_meio):
    if na_fase_critica:
        return "alerta"
    return "atencao" if desde_o_plantio > (valor_do_meio or 0) else "tranquilo"


def _item_do_calor(par, cal, serie, fase, ultimo):
    if fase.get("cultura") is None or fase["cultura"] not in calor.limites(par):
        return {"situacao": "tranquilo", "cultura": None, "limite_c": None,
                "frase": f"Em {data_br(ultimo)} não havia cultura na terra: o calor é contado do plantio em diante."}
    cultura, limite = fase["cultura"], calor.limites(par)[fase["cultura"]]
    maximas = {dia.data: dia.tmax for dia in serie}
    plantio, comeco = datetime.date.fromisoformat(fase["plantio"]), datetime.date.fromisoformat(fase["fase_comecou_em"])
    critica_de = datetime.date.fromisoformat(fase["fase_critica_de"])
    critica_ate = min(ultimo, datetime.date.fromisoformat(fase["fase_critica_ate"]))
    desde = dias_acima(maximas, plantio, ultimo, limite["limite_c"])
    na_fase = dias_acima(maximas, comeco, ultimo, limite["limite_c"])
    na_critica = dias_acima(maximas, critica_de, critica_ate, limite["limite_c"]) if critica_ate >= critica_de else 0
    datas = [plantio + datetime.timedelta(days=i) for i in range((ultimo - plantio).days + 1)]
    dia_da_maxima = max(datas, key=lambda d: maximas[d])
    passo, ate_a_fase = (ultimo - plantio).days, (comeco - plantio).days
    por_safra = {}
    for safra in balanco.SAFRAS_DO_ESTUDO:          # o mesmo dia do ciclo em cada safra guardada
        ano = int(safra[:4])
        p = cal.plantio_da_soja(ano) if cultura == "soja" else cal.plantio_da_segunda(ano + 1, cultura)
        fim = p + datetime.timedelta(days=passo)
        a, b = dias_acima(maximas, p, fim, limite["limite_c"]), dias_acima(
            maximas, p + datetime.timedelta(days=ate_a_fase), fim, limite["limite_c"])
        if a is not None:
            por_safra[safra] = {"desde_o_plantio": a, "na_fase_atual": b}

    def resumo(chave):
        valores = [numeros[chave] for numeros in por_safra.values()]
        return {"valor_do_meio": _meio(valores), "menor": min(valores), "maior": max(valores)} if valores else None

    guardadas = {"safras": len(por_safra), "desde_o_plantio": resumo("desde_o_plantio"),
                 "na_fase_atual": resumo("na_fase_atual"), "por_safra": por_safra,
                 "o_que_e": "os dias com a máxima acima do limite da cultura até o mesmo dia do ciclo, em cada safra "
                            "guardada, com o mesmo calendário"}
    meio = guardadas["desde_o_plantio"]["valor_do_meio"] if por_safra else None
    nome, grau = NA_TERRA[cultura], _grau(limite["limite_c"])
    teve = f"teve {_dias(desde)}" if desde else "não teve nenhum dia"
    frase = (f"Do plantio até {data_br(ultimo)}, {nome} {teve} de calor forte (a máxima do dia acima de {grau} °C, "
             "o limite da cultura)")
    if desde:
        frase += f", {_dias(na_fase)} na fase atual"
    frase += "."
    if por_safra:
        menor, maior = guardadas["desde_o_plantio"]["menor"], guardadas["desde_o_plantio"]["maior"]
        frase += f" Nas {len(por_safra)} safras guardadas, até o mesmo dia do ciclo, "
        frase += (f"foram {_quantos_dias(menor)} em todas." if menor == maior else
                  f"o valor do meio foi de {_quantos_dias(meio)} (do menor, {menor}, ao maior, {maior}).")
    frase += (f" A máxima mais alta desde o plantio foi {_n(maximas[dia_da_maxima])} °C, em "
              f"{data_br(dia_da_maxima)}.")
    if na_critica:
        frase += f" Dentro da fase crítica já foram {_dias(na_critica)} de calor forte."
    return {"situacao": situacao_do_calor(na_critica, desde, meio), "frase": frase, "cultura": cultura,
            "limite_c": limite["limite_c"], "fonte_do_limite": limite["fonte"], "etiqueta_do_limite": limite["etiqueta"],
            "dias_de_calor_forte_desde_o_plantio": desde, "dias_de_calor_forte_na_fase_atual": na_fase,
            "dias_de_calor_forte_na_fase_critica": na_critica, "fase_atual": fase["fase"],
            "maxima_desde_o_plantio_c": round(maximas[dia_da_maxima], 1) + 0.0,
            "dia_da_maxima": dia_da_maxima.isoformat(), "nas_safras_guardadas": guardadas,
            "o_que_e": "dia de calor forte, aqui = dia com a temperatura máxima acima do limite publicado da cultura, "
                       "em qualquer fase (na comparação das rotações o motor conta só os da fase crítica)",
            "aviso": calor.AVISO}


# ------------------------------------------------------------------------------------------------ 4. o verde
def verde_de_agora(pontos, ate=None):
    """O verde mais recente dos pontos da cidade contra a mesma época dos outros anos guardados.

    `pontos`: o que `ndvi.ler_pontos` devolve. `ate`: só valem as imagens até esse dia (o dia da consulta).
    O valor de cada imagem é o valor do meio dos pontos com medida boa. A "mesma época" é a mesma medida do
    satélite nos outros anos (o mesmo dia do ano em que os 16 dias começam). Sem medida boa: None.
    """
    por_data = {}
    for nome, ponto in pontos.items():
        for dia, valor in ponto["boas"]:
            if ate is None or dia <= ate:
                por_data.setdefault(dia, {})[nome] = valor
    if not por_data:
        return None
    imagem = max(por_data)
    do_ano = imagem.timetuple().tm_yday
    por_ano = {dia.year: round(statistics.median(valores.values()), 4) for dia, valores in sorted(por_data.items())
               if dia.year != imagem.year and dia.timetuple().tm_yday == do_ano}
    agora = round(statistics.median(por_data[imagem].values()), 4)
    saida = {"imagem": imagem.isoformat(),
             "imagem_ate": (imagem + datetime.timedelta(days=ndvi.DIAS_POR_MEDIDA - 1)).isoformat(),
             "dias_por_imagem": ndvi.DIAS_POR_MEDIDA, "verde": agora, "pontos_com_medida": len(por_data[imagem]),
             "pontos": len(pontos), "leitura": "sem_comparacao", "outros_anos": None}
    if len(por_ano) >= MINIMO_DE_ANOS_DO_VERDE:
        menor, maior = min(por_ano.values()), max(por_ano.values())
        saida["outros_anos"] = {"anos": sorted(por_ano), "quantos": len(por_ano), "valor_do_meio": round(statistics.median(por_ano.values()), 4),
                                "menor": menor, "maior": maior, "por_ano": {str(a): v for a, v in por_ano.items()}}
        saida["leitura"] = "acima" if agora > maior else ("abaixo" if agora < menor else "dentro")
    return saida


def situacao_do_verde(leitura, ha_cultura):
    if leitura not in ("acima", "dentro", "abaixo"):
        return "sem_dado"
    return "atencao" if leitura == "abaixo" and ha_cultura else "tranquilo"


def _item_do_verde(cidade_id, nome_da_cidade, cal, rotacao, hoje, pasta=None):
    if pasta is None and cidade_id != clima.CIDADE_DE_REFERENCIA:
        pasta = clima.pastas_da_cidade(cidade_id)["ndvi"]
    try:
        verde = verde_de_agora(ndvi.ler_pontos(pasta), ate=hoje)
    except (OSError, ValueError, KeyError):
        verde = None
    if verde is None:
        return {"situacao": "sem_dado", "verde": None, "imagem": None, "leitura": None, "o_que_e": O_QUE_E_O_VERDE,
                "frase": f"Não há imagem do satélite com medida boa guardada para {nome_da_cidade}."}
    fim = datetime.date.fromisoformat(verde["imagem_ate"])
    na_terra = rotacoes.cobertura_do_dia(fim, rotacao["com_braquiaria"], cal, segunda=rotacao["segunda"])[0]
    frase = (f"A imagem mais recente do satélite é de {data_br(verde['imagem'])} (junta {verde['dias_por_imagem']} "
             f"dias, até {data_br(fim)}): o verde deu {_v(verde['verde'])}, numa medida que vai de 0 a 1, em "
             f"{verde['pontos_com_medida']} dos {verde['pontos']} pontos da região de {nome_da_cidade}.")
    outros = verde["outros_anos"]
    if outros is None:
        frase += " Não há anos guardados bastantes na mesma época para comparar."
    else:
        leitura = {"acima": "acima do normal", "dentro": "dentro do normal", "abaixo": "abaixo do normal"}[verde["leitura"]]
        frase += (f" Na mesma época dos outros {outros['quantos']} anos guardados, o valor do meio foi "
                  f"{_v(outros['valor_do_meio'])} (do menor, {_v(outros['menor'])}, ao maior, {_v(outros['maior'])}): "
                  f"este ano está {leitura}.")
    frase += " O satélite olha pontos da região: não é a sua lavoura."
    return dict(verde, situacao=situacao_do_verde(verde["leitura"], na_terra in rotacoes.CULTURAS), frase=frase,
                o_que_estava_na_terra_no_fim_da_imagem=na_terra, o_que_e=O_QUE_E_O_VERDE, fonte=ndvi.fonte(pasta),
                aviso=ndvi.aviso_dos_pontos(nome_da_cidade) + " " + ndvi.AVISO)


# ------------------------------------------------------------------------------------------------ 5. a terra coberta
def terra_no_dia(cal, rotacao, data):
    """Há quantos dias seguidos a terra está com planta viva (ou sem) no dia, pelo calendário da rotação.

    Planta viva é a cultura ou o capim (a braquiária). Devolve também a sequência de antes (a do estado contrário)
    e os dias de cada estado na safra corrente (de 1 de setembro até o dia).
    """
    def viva(dia):
        return rotacoes.cobertura_do_dia(dia, rotacao["com_braquiaria"], cal,
                                         segunda=rotacao["segunda"])[0] != rotacoes.SEM_PLANTA

    def sequencia(fim, estado):
        quantos = 0
        while viva(fim - datetime.timedelta(days=quantos)) == estado and quantos < 800:
            quantos += 1
        return quantos

    estado = viva(data)
    seguidos = sequencia(data, estado)
    desde = data - datetime.timedelta(days=seguidos - 1)
    antes = sequencia(desde - UM_DIA, not estado)
    comeco = datetime.date(data.year if data.month >= 9 else data.year - 1, 9, 1)
    vivos = sum(viva(comeco + datetime.timedelta(days=i)) for i in range((data - comeco).days + 1))
    return {"com_planta_viva": estado, "desde": desde.isoformat(), "dias_seguidos": seguidos,
            "antes": {"com_planta_viva": not estado, "de": (desde - datetime.timedelta(days=antes)).isoformat(),
                      "ate": (desde - UM_DIA).isoformat(), "dias_seguidos": antes},
            "na_safra": {"desde": comeco.isoformat(), "dias_com_planta_viva": vivos,
                         "dias_sem_planta_viva": (data - comeco).days + 1 - vivos}}


def situacao_da_terra(com_planta_viva):
    return "tranquilo" if com_planta_viva else "atencao"


def _item_da_terra(cal, rotacao, ultimo):
    terra = terra_no_dia(cal, rotacao, ultimo)
    estado, contrario = (("com planta viva", "sem planta viva") if terra["com_planta_viva"]
                         else ("sem planta viva", "com planta viva"))
    antes = terra["antes"]
    frase = (f"Em {data_br(ultimo)}, pelo calendário, a terra estava {estado} desde {data_br(terra['desde'])}: "
             f"{_dias(terra['dias_seguidos'])} seguidos, contando o primeiro. Antes disso ficou "
             f"{_dias(antes['dias_seguidos'])} seguidos {contrario}, de {data_br(antes['de'])} a "
             f"{data_br(antes['ate'])}. Nesta safra, desde {data_br(terra['na_safra']['desde'])}, foram "
             f"{_quantos_dias(terra['na_safra']['dias_com_planta_viva'])} com planta viva e "
             f"{_quantos_dias(terra['na_safra']['dias_sem_planta_viva'])} sem.")
    return dict(terra, situacao=situacao_da_terra(terra["com_planta_viva"]), frase=frase,
                aviso="É o calendário da rotação, não medida: a palha que fica na terra não entra nesta contagem.")


# ------------------------------------------------------------------------------------------------ 6. o aviso de sede
def para_a_frente(entrada, par, serie, cal, janela=JANELA_DO_CONSUMO_DIAS, horizonte=HORIZONTE_SEM_CHUVA_DIAS):
    """A mesma conta da água do motor, seguida para a frente com chuva zero: os registros dos dias seguintes.

    Cada dia seguinte entra sem chuva e com o tempo dos últimos `janela` dias com dado (a média da temperatura e da
    evaporação de referência); o que a cultura pede em cada dia segue o calendário e as fases, como na conta.
    """
    from orbita import motor
    ultimos = serie[-janela:]
    media = lambda campo: sum(getattr(dia, campo) for dia in ultimos) / len(ultimos)  # noqa: E731
    futuro = [clima.Dia(serie[-1].data + datetime.timedelta(days=k), 0.0, media("tmax"), media("tmin"), media("eto"))
              for k in range(1, horizonte + 1)]
    registros, _ = motor.simular_a_rotacao_de_hoje(entrada, par, list(serie) + futuro, cal)
    return registros[-horizonte:]


def dias_ate_a_sede(futuros, tipo):
    """Em quantos dias a cultura `tipo` começa a passar sede nos registros da conta para a frente.

    Devolve (os dias, None) ou (None, o motivo): "a_cultura_sai_da_terra" ou "nao_chega_no_horizonte".
    """
    for k, r in enumerate(futuros, 1):
        if r.tipo != tipo:
            return None, "a_cultura_sai_da_terra"
        if r.ks < 1.0:
            return k, None
    return None, "nao_chega_no_horizonte"


def situacao_do_aviso(ha_cultura, ja_com_sede, dias):
    if not ha_cultura:
        return "tranquilo"
    if ja_com_sede:
        return "alerta"
    return "atencao" if dias is not None and dias <= JANELA_DO_CONSUMO_DIAS else "tranquilo"


def chuva_depois(chuva_recente, ultimo, hoje):
    """A chuva rápida do satélite já guardada nos dias seguintes ao último dia da conta (até o dia da consulta).

    A conta ainda não usou esses dias, porque falta a temperatura deles. Só entram dias seguidos, sem buraco: dia
    sem dado nunca vira zero. Sem nenhum dia: None.
    """
    dias, dia = [], ultimo + UM_DIA
    while dia <= hoje and chuva_recente.get(dia) is not None:
        dias.append(chuva_recente[dia])
        dia += UM_DIA
    if not dias:
        return None
    return {"de": (ultimo + UM_DIA).isoformat(), "ate": (dia - UM_DIA).isoformat(), "dias": len(dias),
            "satelite_rapido_mm": round(sum(dias), 1) + 0.0,
            "o_que_e": "a chuva rápida do satélite já guardada depois do último dia da conta; a conta ainda não usou "
                       "esses dias, porque falta a temperatura deles"}


def _item_do_aviso(entrada, par, contas, tipo, ultimo, hoje, chuva_recente):
    depois = chuva_depois(chuva_recente, ultimo, hoje)
    base = {"chuva_depois_do_ultimo_dia": depois, "janela_dias": JANELA_DO_CONSUMO_DIAS, "horizonte_dias": HORIZONTE_SEM_CHUVA_DIAS,
            "sem_chuva_a_partir_de": (ultimo + UM_DIA).isoformat(), "dia_da_consulta": hoje.isoformat(),
            "dias_ja_passados_ate_a_consulta": (hoje - ultimo).days}
    if tipo not in rotacoes.CULTURAS:
        return dict(base, situacao=situacao_do_aviso(False, False, None), ja_com_sede=False,
                    dias_seguidos_de_sede=0, dias_ate_a_sede=None, data_da_sede=None,
                    frase=f"Em {data_br(ultimo)} não havia cultura na terra: não há aviso de sede.")

    def lado(registros, serie):
        sede = dias_seguidos(registros, com_sede)
        dias, motivo = (None, "ja_com_sede") if sede else dias_ate_a_sede(para_a_frente(entrada, par, serie, contas["cal"]), tipo)
        return {"ja_com_sede": bool(sede), "dias_seguidos_de_sede": sede, "dias_ate_a_sede": dias,
                "data_da_sede": None if dias is None else (ultimo + datetime.timedelta(days=dias)).isoformat(),
                "sem_sede_porque": motivo if dias is None and not sede else None}

    satelite = lado(contas["registros"], contas["com_recente"])
    da_cultura = [r for r in contas["registros"][-JANELA_DO_CONSUMO_DIAS:] if r.tipo == tipo]
    consumo = round(sum(r.bebido for r in da_cultura) / len(da_cultura), 1) + 0.0
    nome = NA_TERRA[tipo]

    def em_palavras(conta):
        if conta["ja_com_sede"]:
            return f"{nome} já estava com sede havia {_dias(conta['dias_seguidos_de_sede'])} seguidos"
        if conta["dias_ate_a_sede"] is not None:
            return (f"{nome} começa a passar sede em {_dias(conta['dias_ate_a_sede'])}, em "
                    f"{data_br(conta['data_da_sede'])}")
        if conta["sem_sede_porque"] == "a_cultura_sai_da_terra":
            return f"{nome} sai da terra antes de a sede chegar"
        return f"a água ao alcance da planta não chega ao nível de sede nos {HORIZONTE_SEM_CHUVA_DIAS} dias seguintes"

    if satelite["ja_com_sede"]:
        frase = f"Em {data_br(ultimo)}, {em_palavras(satelite)}. Sem chuva, a sede continua."
    else:
        frase = f"Se não chover nada depois de {data_br(ultimo)}, {em_palavras(satelite)}."
    frase += (f" A conta segue a água da terra para a frente com o tempo dos últimos {JANELA_DO_CONSUMO_DIAS} dias "
              f"com dado, em que a lavoura bebeu em média {_n(consumo)} mm por dia.")
    if hoje > ultimo:
        frase += (f" Até o dia desta consulta ({data_br(hoje)}) já se passaram {_dias((hoje - ultimo).days)} que a "
                  "conta ainda não fechou")
        frase += "." if depois is None else (
            f"; de {data_br(depois['de'])} a {data_br(depois['ate'])} o satélite já marcou "
            f"{_n(depois['satelite_rapido_mm'])} mm de chuva, que ainda não entraram na conta.")
    frase += " Não é previsão do tempo: a chuva que cair muda a conta."
    return dict(base, situacao=situacao_do_aviso(True, satelite["ja_com_sede"], satelite["dias_ate_a_sede"]),
                frase=frase, **satelite, consumo_medio_mm_por_dia=consumo,
                dias_do_consumo=len(da_cultura), agua_na_terra_mm=round(contas["registros"][-1].agua_na_terra, 1) + 0.0,
                nivel_de_sede="o dia em que a água fácil de tirar da terra acaba e a planta começa a passar sede "
                              "(a mesma regra dos dias de sede do motor)")


# ------------------------------------------------------------------------------------------------ o painel
def _resumo(cidade, ultimo, itens):
    fase, agua = itens["fase"], itens["agua"]
    if fase["cultura"] is None:
        estado = ("com a braquiária (o capim) viva" if fase["o_que_esta_na_terra"] == rotacoes.BRAQUIARIA
                  else "sem planta viva")
        frase = (f"Em {cidade}, em {data_br(ultimo)} (o último dia com dado), a terra estava {estado}, com "
                 f"{_n(agua['agua_na_terra_mm'])} mm de água; {NA_TERRA[fase['proximo_plantio']['cultura']]} entra em "
                 f"{data_br(fase['proximo_plantio']['data'])}.")
    else:
        sede = (f"com sede havia {_dias(agua['dias_seguidos_de_sede'])} seguidos" if agua["dias_seguidos_de_sede"]
                else "sem sede")
        frase = (f"Em {cidade}, em {data_br(ultimo)} (o último dia com dado), {NA_TERRA[fase['cultura']]} tinha "
                 f"{_dias(fase['dias_desde_o_plantio'])} e estava {fase['fase_nome']}, {sede}, com "
                 f"{_n(agua['agua_na_terra_mm'])} mm de água ao alcance da planta.")
    for situacao, comeco in (("alerta", "Em alerta"), ("atencao", "Pede atenção")):
        nomes = [NOMES_DOS_ITENS[ident] for ident in ITENS if itens[ident]["situacao"] == situacao]
        if nomes:
            comeco = "Pedem atenção" if situacao == "atencao" and len(nomes) > 1 else comeco
            frase += f" {comeco}: {nomes[0] if len(nomes) == 1 else ', '.join(nomes[:-1]) + ' e ' + nomes[-1]}."
    sem_dado = [NOMES_DOS_ITENS[ident] for ident in ITENS if itens[ident]["situacao"] == "sem_dado"]
    if all(itens[ident]["situacao"] in ("tranquilo", "sem_dado") for ident in ITENS):
        frase += " Nada pede atenção nos itens com dado."
    if sem_dado:
        frase += f" Sem dado: {', '.join(sem_dado)}."
    return frase


def lavoura_hoje(entrada, par=None, hoje=None, pasta_da_chuva_recente=None, pasta_do_verde=None):
    """A lavoura hoje, na rotação e na data de plantio do produtor: os seis itens e a frase que resume.

    `hoje` (uma data) serve para os testes; sem ele, vale o dia da chamada. Sem a chuva recente guardada, devolve
    `disponivel: False` com o que falta, como o "como está hoje". O "como está hoje" não muda.
    """
    from orbita import motor
    par = par or parametros.carregar()
    hoje = hoje or datetime.date.today()
    retrato = retrato_de_hoje.como_esta_hoje(entrada, par, hoje, pasta_da_chuva_recente)
    if not retrato["disponivel"]:
        return retrato
    entrada = motor.validar_entrada(dict(entrada, chuva=None))
    recente, _ = retrato_de_hoje.ler_chuva_recente(entrada["cidade_id"], pasta_da_chuva_recente)
    contas = retrato_de_hoje.contas_de_hoje(entrada, par, recente)
    cal, rotacao = contas["cal"], contas["rotacao"]
    ultimo, tipo = contas["com_recente"][-1].data, retrato["o_que_esta_na_terra"]
    cidade = retrato["local"]["nome"]
    fase = _item_da_fase(cal, rotacao, tipo, ultimo, hoje)
    itens = {"fase": fase, "agua": _item_da_agua(retrato, contas, ultimo),
             "calor": _item_do_calor(par, cal, contas["com_recente"], fase, ultimo),
             "verde": _item_do_verde(entrada["cidade_id"], cidade, cal, rotacao, hoje, pasta_do_verde),
             "terra_coberta": _item_da_terra(cal, rotacao, ultimo),
             "aviso_de_sede": _item_do_aviso(entrada, par, contas, tipo, ultimo, hoje, recente)}
    lista = []
    for ident in ITENS:
        item = itens[ident]
        data = item.get("imagem") if ident == "verde" else ultimo.isoformat()
        lista.append(dict({"id": ident, "titulo": TITULOS[ident], "situacao": item["situacao"],
                           "situacao_nome": NOMES_DAS_SITUACOES[item["situacao"]], "frase": item["frase"],
                           "ultimo_dado": {"data": data, "de": DE_QUAL_DADO[ident]},
                           "regra_da_situacao": REGRAS[ident]},
                          **{chave: valor for chave, valor in item.items() if chave not in ("situacao", "frase")}))
    situacao = pior_situacao(item["situacao"] for item in lista)
    return {"disponivel": True, "local": retrato["local"], "rotacao": retrato["rotacao"], "terra": retrato["terra"],
            "plantio_da_soja_informado": retrato["plantio_da_soja_informado"], "hoje": retrato["hoje"],
            "ultimo_dia_com_dado": retrato["ultimo_dia_com_dado"],
            "ultimo_dia_com_dado_de": retrato["ultimo_dia_com_dado_de"], "atraso_dias": retrato["atraso_dias"],
            "safra": retrato["safra"], "situacao": situacao, "situacao_nome": NOMES_DAS_SITUACOES[situacao],
            "frase": _resumo(cidade, ultimo, itens), "itens": lista, "regras": dict(REGRAS),
            "janela_do_consumo_dias": JANELA_DO_CONSUMO_DIAS, "horizonte_sem_chuva_dias": HORIZONTE_SEM_CHUVA_DIAS,
            "aviso": AVISO}
