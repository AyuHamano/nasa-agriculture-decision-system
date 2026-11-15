# Gerado com IA (Claude)
"""O "depois": o registro da safra, depois da colheita. O que foi plantado, como foi a água, o calor e a terra coberta.

Tudo sai da mesma conta do replay (`motor.replay_da_safra`), na rotação de hoje do produtor, mais o que o satélite viu
da terra naquele ano, onde há medida. O registro de uma safra ao lado do de outra é o histórico da lavoura.
"""
import datetime
import statistics

from orbita import balanco, clima, parametros, rotacoes

NOMES = {"soja": "soja", "milho": "milho de 2ª safra", "sorgo": "sorgo de 2ª safra"}
AVISO = ("É o registro da conta com o clima guardado da NASA para o ponto da cidade, na rotação informada: não é a "
         "medida da lavoura nem a colheita. Converse com o agrônomo.")


def _n(numero):
    return f"{numero:.1f}".replace(".", ",")


def _verde_do_ano(cidade_id, ano, par):
    """Os dias sem planta verde que o satélite viu no ano (de junho em diante), nos pontos medidos. Sem medida: None."""
    from orbita import motor, ndvi
    pasta = None
    if cidade_id != motor.CIDADE_DA_PROVA:
        pasta = clima.pastas_da_cidade(cidade_id)["ndvi"]
        if not pasta.is_dir() or not list(pasta.glob("*.csv")):
            return None
    try:
        resumo = ndvi.resumo(parametros.valor(par, "ndvi", "fracao_da_amplitude"), pasta)
    except (OSError, ValueError, KeyError):
        return None
    valores = [anos[str(ano)] for anos in resumo["dias_sem_planta_verde"].values() if str(ano) in anos]
    if not valores:
        return None
    mediana = statistics.median(valores)
    return {"ano": ano, "dias_sem_planta_verde": int(mediana) if float(mediana).is_integer() else mediana,
            "menor": min(valores), "maior": max(valores), "pontos": len(valores),
            "aviso": ndvi.AVISO + " " + ndvi.AVISO_DOS_PONTOS}


def registro_da_safra(entrada, safra, par=None):
    """O registro de uma safra guardada ("2015-16"), na rotação de hoje do produtor.

    Devolve o que foi plantado (com as datas da conta), a falta de água, os dias de calor forte e os dias sem planta
    viva; a posição da safra entre as guardadas; e, onde há medida, o que o satélite viu da terra naquele ano.
    """
    from orbita import motor
    par = par or parametros.carregar()
    replay = motor.replay_da_safra(entrada, safra, par)
    entrada = motor.validar_entrada(entrada)
    dias, resumo = replay["dias"], replay["resumo"]
    plantado = []
    for cultura in ("soja", "milho", "sorgo", "braquiaria"):
        datas = [dia["data"] for dia in dias if dia["cultura"] == cultura]
        if datas:
            plantado.append({"cultura": cultura, "entra": datas[0], "sai": datas[-1], "dias": len(datas)})
    sem_planta = sum(1 for dia in dias if dia["cultura"] == "sem_planta")
    culturas = [c for c in ("soja", "milho", "sorgo") if c in resumo]
    limites = replay["limites_de_calor_c"]
    # A posição entre as safras guardadas, pela medida que a conta usa para a sede: a falta de água da cultura da 2ª
    # safra, em % do que ela pediu (1 = a de maior falta). A mesma conta roda em todas as safras.
    # Entram só as safras em que a 2ª safra fechou o ciclo nos dados guardados, e a ordem sai dos números sem
    # arredondar (14,6445% é mais falta que 14,6006%, embora os dois apareçam como 14,6).
    segunda = replay["rotacao"]["segunda"]
    cal = rotacoes.calendario(par, entrada["plantio_da_soja"])
    registros, _ = motor.simular_a_rotacao_de_hoje(entrada, par, motor._serie(entrada)[0], cal)
    numeros = balanco.numeros_por_safra(registros)
    exatas = {}
    for outra in balanco.SAFRAS_DO_ESTUDO + (motor.SAFRA_A_PARTE,):
        da_segunda = numeros.get(outra, {}).get(segunda)
        if da_segunda and da_segunda["dias"] == cal.segundas[segunda]["ciclo"]:
            exatas[outra] = da_segunda["falta_relativa_pct"]
    faltas = {s: motor.r1(v) for s, v in exatas.items()}
    posicao = 1 + sum(1 for v in exatas.values() if v > exatas[safra]) if safra in exatas else None
    empatadas = sorted(s for s, v in exatas.items() if s != safra and safra in exatas and v == exatas[safra])
    ano_da_seca = int(safra[:4]) + 1
    verde = _verde_do_ano(entrada["cidade_id"], ano_da_seca, par)
    mediana = motor.r1(statistics.median(exatas.values())) if exatas else None
    nomes = " e ".join(NOMES[c] for c in culturas)
    frase = (f"Safra {safra} em {replay['local']['nome']}, com {nomes}: faltaram {_n(resumo['total']['falta_mm'])} mm "
             f"de água para as culturas, com {resumo['total']['dias_de_sede']} dias de sede e "
             f"{resumo['total']['dias_de_calor_forte']} dias de calor forte na fase crítica. A terra ficou "
             f"{sem_planta} dias sem planta viva.")
    if posicao is not None:
        frase += (f" A falta de água do {NOMES[segunda]} foi de {_n(faltas[safra])}% do que ele pediu: entre as "
                  f"{len(faltas)} safras guardadas com a 2ª safra completa, a {posicao}ª maior (a mediana é "
                  f"{_n(mediana)}%).")
    else:
        frase += (f" O {NOMES[segunda]} ainda não fechou o ciclo nos dados guardados desta safra: ela fica fora da "
                  "comparação com as outras.")
    if verde is not None:
        frase += (f" Em {verde['ano']}, o satélite viu {verde['dias_sem_planta_verde']} dias seguidos sem planta "
                  "verde na região (a mediana dos pontos medidos).")
    return {
        "safra": safra, "local": replay["local"], "rotacao": replay["rotacao"], "terra": replay["terra"],
        "plantio_da_soja_informado": replay["plantio_da_soja_informado"],
        "periodo": {"de": replay["primeiro_dia"], "ate": replay["ultimo_dia"], "completa": replay["completa"]},
        "o_que_foi_plantado": plantado,
        "agua": {"falta_mm": resumo["total"]["falta_mm"], "dias_de_sede": resumo["total"]["dias_de_sede"],
                 "chuva_da_safra_mm": resumo["total"]["chuva_mm"],
                 "por_cultura": {c: {"falta_mm": resumo[c]["falta_mm"],
                                     "falta_relativa_pct": resumo[c]["falta_relativa_pct"],
                                     "dias_de_sede": resumo[c]["dias_de_sede"],
                                     "maior_sequencia_de_sede_dias": resumo[c].get("maior_sequencia_de_sede_dias", 0)}
                                 for c in culturas}},
        "calor": {"dias_de_calor_forte": resumo["total"]["dias_de_calor_forte"],
                  "por_cultura": {c: {"dias": resumo[c]["dias_de_calor_forte"], "limite_c": limites.get(c)}
                                  for c in culturas}},
        "terra_coberta": {"dias_sem_planta_viva": sem_planta, "pelo_satelite": verde,
                          "nota": "Os dias sem planta viva são os da conta, de 1 de setembro a 31 de agosto. O "
                                  "satélite prova só a rotação de hoje da região (soja, milho e pousio)."},
        "entre_as_safras_guardadas": {
            "medida": f"a falta de água do {NOMES[segunda]}, em % do que ele pediu",
            "posicao": posicao, "de": len(faltas), "mediana_pct": mediana,
            "falta_da_2a_safra_pct": faltas.get(safra), "por_safra_pct": faltas, "empatadas": empatadas,
            "nota": "Entram só as safras em que a 2ª safra fechou o ciclo nos dados guardados; a ordem sai dos "
                    "números sem arredondar."},
        "marcos": replay["marcos"],
        "registrado_em": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "frase": frase, "aviso": AVISO}
