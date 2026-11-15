# Gerado com IA (Claude)
"""O calor: os dias de calor forte na fase crítica de cada cultura, com a temperatura máxima da NASA POWER.

- "Dia de calor forte" = dia da fase crítica da cultura com a temperatura máxima (T2M_MAX) ACIMA do limite da cultura.
- O limite de cada cultura vem de fonte publicada (a Embrapa e a FAO), com o link e o trecho, em
  `parametros.py` e em `data/orbita/parametros-com-fonte.json` (a seção "calor"). O critério da escolha foi escrito
  antes de ver os números (2026-11-15): de cada cultura, o limite publicado mais diretamente ligado à fase crítica
  (a floração e o enchimento dos grãos). Onde há outro limite publicado, a conta mostra os dois, lado a lado.
- A fase crítica, no calendário, é a fase do meio do FAO-56 (Tabela 11): vai da cobertura cheia ao começo da
  maturação e pega a floração e a maior parte do enchimento. Isso é hipótese desta versão, dita na resposta.
- As fontes dizem "temperaturas acima de" e não dizem se é a máxima ou a média do dia: usar a máxima é hipótese.

Nada aqui muda a conta da água: o calor é uma contagem à parte, sobre os mesmos dias e o mesmo calendário.
"""
import datetime

from orbita import clima, parametros

CULTURAS = ("soja", "milho", "sorgo")
NOMES = {"soja": "a soja", "milho": "o milho", "sorgo": "o sorgo"}
O_QUE_E = ("dia de calor forte = dia da fase crítica da cultura com a temperatura máxima do dia acima do limite "
           "publicado da cultura")
AVISO = ("A temperatura é a da NASA POWER (um quadrado de uns 50 km), não a da lavoura. As fontes dos limites dizem "
         "'temperaturas acima de' e não dizem se é a máxima ou a média do dia; e a fase crítica, na conta, é a fase "
         "do meio da tabela da FAO (o órgão da ONU para a agricultura). Dia de calor forte não é perda de safra: é sinal para olhar com o agrônomo.")


def limites(par):
    """O limite de calor de cada cultura, com a fonte, o trecho e a etiqueta; e o outro limite publicado, se houver."""
    saida = {}
    for cultura in CULTURAS:
        folhas = par.get("calor", {}).get(cultura)
        if not folhas:
            continue
        limite, outro, fase = folhas["limite_c"], folhas.get("outro_limite_c"), folhas["fase_critica"]
        saida[cultura] = {
            "limite_c": limite["valor"], "etiqueta": limite["etiqueta"], "fonte": limite["fonte"],
            "trecho": limite["trecho"],
            "outro_limite_publicado": None if outro is None else {
                "limite_c": outro["valor"], "etiqueta": outro["etiqueta"], "fonte": outro["fonte"],
                "trecho": outro["trecho"]},
            "fase_critica": {"na_conta": "a fase do meio do FAO-56 (da cobertura cheia ao começo da maturação)",
                             "etiqueta": fase["etiqueta"], "fonte": fase["fonte"], "trecho": fase["trecho"]}}
    return saida


def janela_critica(cal, cultura, safra):
    """O primeiro dia e o dia depois do último da fase crítica (a fase do meio) da cultura na safra ("2015-16")."""
    ano = int(safra[:4])
    if cultura == "soja":
        plantio, fases = cal.plantio_da_soja(ano), cal.soja_fases
    else:
        plantio, fases = cal.plantio_da_segunda(ano + 1, cultura), cal.segundas[cultura]["fases"]
    inicio = plantio + datetime.timedelta(days=fases[0] + fases[1])
    return inicio, inicio + datetime.timedelta(days=fases[2])


def na_fase_critica(cal, cultura, data):
    """Se o dia cai na fase crítica da cultura (em qualquer safra)."""
    for ano in (data.year - 1, data.year):
        inicio, fim = janela_critica(cal, cultura, f"{ano}-{(ano + 1) % 100:02d}")
        if inicio <= data < fim:
            return True
    return False


def contar(maximas, cal, cultura, limite, safra):
    """Os dias de calor forte da cultura na safra. `maximas`: data -> temperatura máxima (°C).

    Devolve None se algum dia da fase crítica não tem temperatura guardada (a conta não inventa clima).
    """
    inicio, fim = janela_critica(cal, cultura, safra)
    datas = [inicio + datetime.timedelta(days=i) for i in range((fim - inicio).days)]
    if any(data not in maximas for data in datas):
        return None
    quentes = [data for data in datas if maximas[data] > limite]
    return {"dias_de_calor_forte": len(quentes), "maxima_da_fase_c": round(max(maximas[d] for d in datas), 1) + 0.0,
            "fase_critica": {"de": inicio.isoformat(), "ate": (fim - datetime.timedelta(days=1)).isoformat(),
                             "dias": len(datas)},
            "primeiro_dia_de_calor_forte": quentes[0].isoformat() if quentes else None}


def por_cultura(dias, cal, par, safras):
    """Para cada cultura do calendário: o limite e os dias de calor forte em cada safra (e com o outro limite)."""
    maximas = {dia.data: dia.tmax for dia in dias}
    saida = {}
    for cultura, limite in limites(par).items():
        if cultura != "soja" and cultura not in cal.segundas:
            continue
        outro = limite["outro_limite_publicado"]
        tabela = {}
        for safra in safras:
            conta = contar(maximas, cal, cultura, limite["limite_c"], safra)
            if conta is None:
                continue
            if outro is not None:
                conta["com_o_outro_limite"] = contar(maximas, cal, cultura, outro["limite_c"], safra)[
                    "dias_de_calor_forte"]
            tabela[safra] = conta
        saida[cultura] = {
            "limite_c": limite["limite_c"], "etiqueta": limite["etiqueta"],
            "outro_limite_c": None if outro is None else outro["limite_c"],
            "por_safra": tabela,
            "soma_das_safras": sum(c["dias_de_calor_forte"] for c in tabela.values()),
            "safras_com_calor_forte": [s for s, c in tabela.items() if c["dias_de_calor_forte"] > 0]}
    return saida


def da_rotacao(culturas_da_rotacao, contas, safra):
    """Os dias de calor forte de uma rotação numa safra: a soma das culturas dela (cada uma com o seu limite)."""
    partes = {c: contas[c]["por_safra"][safra]["dias_de_calor_forte"] for c in culturas_da_rotacao
              if c in contas and safra in contas[c]["por_safra"]}
    return {"dias": sum(partes.values()), "por_cultura": partes}


def bloco(dias, cal, par, safras, pior, normal, rotacoes_do_cardapio):
    """O bloco `calor` da resposta: os limites, a conta por cultura e por rotação, e os avisos.

    `rotacoes_do_cardapio`: id -> a lista das culturas que contam (["soja", "milho"]).
    """
    contas = por_cultura(dias, cal, par, safras)
    por_rotacao = {}
    for ident, culturas in rotacoes_do_cardapio.items():
        culturas = [c for c in culturas if c in contas]
        por_rotacao[ident] = {
            "culturas": culturas,
            "dias_no_pior_ano": da_rotacao(culturas, contas, pior)["dias"],
            "dias_no_ano_normal": da_rotacao(culturas, contas, normal)["dias"],
            "soma_das_safras": sum(contas[c]["soma_das_safras"] for c in culturas)}
    return {"o_que_e": O_QUE_E, "fonte_da_temperatura": clima.ORIGEM_DA_TEMPERATURA,
            "pior_ano": pior, "ano_normal": normal, "limites": limites(par), "por_cultura": contas,
            "por_rotacao": por_rotacao,
            "hipoteses": [parametros.valor(par, "calor", "maxima_do_dia") and par["calor"]["maxima_do_dia"]["trecho"],
                          parametros.FASE_DO_MEIO],
            "aviso": AVISO}
