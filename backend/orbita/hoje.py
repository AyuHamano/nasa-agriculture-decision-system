# Gerado com IA (Claude)
"""O "durante": como está a água da lavoura hoje, perto do ano normal e do pior ano no mesmo dia do calendário.

O problema: a chuva do satélite GPM IMERG entregue pela NASA POWER (a que o motor usa nas safras guardadas) chega
com cerca de 2 meses de atraso. Desde 2026-11-15 os dias recentes vêm da chuva do dia: o GPM IMERG V07 em mm, somado
no dia de Brasília, na versão Late e, nos dias em que ela ainda não chegou, na Early (as duas rápidas; a NASA ainda
corrige). Os arquivos ficam em `data/orbita/chuva-do-dia/<cidade>/chuva-do-dia.csv`, baixados por
`data/orbita/chuva-do-dia/baixar_chuva_do_dia.py` da cópia dos arquivos da NASA que a dynamical.org mantém (licença
CC BY 4.0, "NASA IMERG from dynamical.org"; o `LEIA-ME.md` de lá conta a regra do dia e a conferência).

O que isso quer dizer para a conta:
- a água na terra sai como um número só, o da conta com essa chuva; a mesma conta com a chuva de modelo da NASA POWER
  (PRECTOTCORR) continua ao lado, em `com_a_chuva_de_modelo`, só para comparar;
- o dia do retrato continua preso à temperatura guardada da NASA POWER: a chuva chegar a ontem não basta;
- antes disso a chuva recente era lida da cor da imagem diária do NASA GIBS (`data/orbita/recente/`): essa leitura
  não entra mais na conta e fica só no registro da conferência (`conferencia_em_mm`).
O motor não baixa nada na hora da pergunta: lê o que está guardado. Para atualizar, rodar o programa de baixar.
"""
import csv
import datetime
import json

from orbita import balanco, clima, parametros, rotacoes
from orbita.explicacao import data_br

PASTA_DA_CHUVA_RECENTE = clima.PASTA_DOS_DADOS / "recente"          # a leitura da cor (só a conferência)
PASTA_DA_CHUVA_DO_DIA = clima.PASTA_DOS_DADOS / "chuva-do-dia"      # a chuva do satélite por dia, em mm
JANELA_DO_CONSUMO_DIAS = 7      # os dias com temperatura que dão o tempo dos dias em que ela ainda não chegou
AVISO = ("A chuva dos dias recentes é a chuva medida por satélite da NASA (o GPM IMERG), em mm de cada dia, nas "
         "versões rápidas (a Late e, nos dias em que ela ainda não chegou, a Early), que a NASA ainda corrige; vem da "
         "cópia dos arquivos da NASA que a dynamical.org mantém. A temperatura é a da NASA POWER, de um quadrado de "
         "uns 50 km, e chega com uns 3 dias de atraso: nos dias em que ela ainda não chegou, a conta usa a chuva "
         "do satélite e, para o consumo da cultura, o tempo médio dos 7 dias anteriores com temperatura. É um retrato para conversar com o agrônomo, não uma medida da lavoura.")

# A leitura do produtor (decisão do dono, 2026-11-15): o `aviso` é esta linha curta, e a `frase` leva só a data do
# dado, sem tratar a data como defeito. O texto de antes fica inteiro em `aviso_tecnico` (o AVISO acima) e em
# `detalhe_tecnico` (o que saiu da frase): é a leitura do agrônomo.
AVISO_DO_PRODUTOR = "Converse com o agrônomo antes de decidir."

# As duas datas que se chamam "último dia com dado" são de dados diferentes: cada uma diz de qual, ao lado.
DIA_DA_CONTA = ("da conta: o último dia com a chuva do satélite em mm, sem dia faltando no meio. Nos dias em que a "
                "temperatura (a da NASA POWER) ainda não chegou, o consumo da cultura é o do tempo médio dos 7 dias "
                "anteriores com temperatura; a chuva é a do satélite. É o dia do retrato: o que está na terra, a "
                "água e a sede valem neste dia.")
DIA_DA_CHUVA_RAPIDA = ("só da chuva rápida do satélite: o último dia com chuva no arquivo baixado. Pode passar do "
                       "dia do retrato, que também precisa da temperatura.")


def ler_chuva_da_cor(cidade_id, pasta=None):
    """A chuva lida da cor da imagem do NASA GIBS (a que a conta usou até 2026-11-15): (data -> mm ou None, a ficha).

    Fica só para a conferência (`conferencia_em_mm`). Sem arquivo: (None, None).
    """
    pasta = (pasta or PASTA_DA_CHUVA_RECENTE) / cidade_id
    arquivo = pasta / "chuva-recente.csv"
    if not arquivo.exists():
        return None, None
    valores = {}
    with open(arquivo, encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            texto = (linha.get("chuva_mm") or "").strip()
            valores[datetime.date.fromisoformat(linha["data"].strip())] = float(texto) if texto else None
    fonte = {}
    if (pasta / "fonte.json").exists():
        bruto = json.loads((pasta / "fonte.json").read_text(encoding="utf-8"))
        fonte = {chave: bruto.get(chave) for chave in ("o_que_e", "conta", "ressalvas", "ponto", "tabela_de_cores",
                                                        "comecou_em_utc", "terminou_em_utc", "ultimo_dia_com_dado")}
        if fonte.get("ultimo_dia_com_dado"):
            fonte["ultimo_dia_com_dado_de"] = DIA_DA_CHUVA_RAPIDA
    return valores, fonte


def ler_chuva_recente(cidade_id, pasta=None):
    """A chuva do dia guardada da cidade: (data -> mm ou None, a ficha da fonte). Sem arquivo: (None, None).

    É a chuva do satélite GPM IMERG em mm, por dia de Brasília: vale a versão Late e, onde ela ainda não chegou, a
    Early. Dia em branco no arquivo vira None, nunca zero. `pasta` é onde ficam as pastas das cidades.
    """
    pasta = (pasta or PASTA_DA_CHUVA_DO_DIA) / cidade_id
    arquivo = pasta / "chuva-do-dia.csv"
    if not arquivo.exists():
        return None, None
    valores, versoes = {}, {}
    with open(arquivo, encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            late, early = (linha.get("chuva_late_mm") or "").strip(), (linha.get("chuva_early_mm") or "").strip()
            dia = datetime.date.fromisoformat(linha["data"].strip())
            valores[dia] = float(late or early) if (late or early) else None
            versoes[dia] = "late" if late else ("early" if early else None)
    fonte = {}
    if (pasta / "fonte.json").exists():
        bruto = json.loads((pasta / "fonte.json").read_text(encoding="utf-8"))
        fonte = {chave: bruto.get(chave) for chave in ("o_que_e", "de_onde_vem", "licenca", "citacao", "versao_do_dado",
                                                        "conta", "regra_do_dia", "ponto", "ultima_rodada_utc")}
    com_dado = [dia for dia, mm in valores.items() if mm is not None]
    if com_dado:
        fonte["ultimo_dia_com_dado"] = max(com_dado).isoformat()
        fonte["ultimo_dia_com_dado_de"] = DIA_DA_CHUVA_RAPIDA
        fonte["versao_do_ultimo_dia"] = versoes[max(com_dado)]
        do_late = [dia for dia in com_dado if versoes[dia] == "late"]
        fonte["ultimo_dia_da_versao_late"] = max(do_late).isoformat() if do_late else None
    return valores, fonte


def conferencia_em_mm(cidade_id, chuva_recente, pasta=None):
    """Confere a chuva lida da cor contra a mesma chuva do satélite em mm, somada de 5 em 5 dias. Sem arquivo: None.

    O arquivo `chuva-5-dias.csv` (inicio,fim,chuva_mm) é o GPM IMERG Late V07 somado por pêntada, baixado por
    data/orbita/recente/baixar_imerg_5_dias.py. Só entram os períodos em que há o valor em mm e todos os dias da
    leitura da cor: período com buraco fica de fora, nunca vira zero. Serve de conferência; a conta não usa.
    """
    arquivo = (pasta or PASTA_DA_CHUVA_RECENTE) / cidade_id / "chuva-5-dias.csv"
    if not arquivo.exists():
        return None
    pares = []
    with open(arquivo, encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            texto = (linha.get("chuva_mm") or "").strip()
            if not texto:
                continue
            comeco = datetime.date.fromisoformat(linha["inicio"].strip())
            fim = datetime.date.fromisoformat(linha["fim"].strip())
            dias = [chuva_recente.get(comeco + datetime.timedelta(days=n)) for n in range((fim - comeco).days + 1)]
            if all(valor is not None for valor in dias):
                pares.append((comeco, fim, float(texto), sum(dias)))
    if not pares:
        return None
    em_mm, da_cor = sum(par[2] for par in pares), sum(par[3] for par in pares)
    return {"periodos_de_5_dias": len(pares), "de": pares[0][0].isoformat(), "ate": pares[-1][1].isoformat(),
            "satelite_em_mm": round(em_mm, 1) + 0.0, "satelite_lido_da_cor_mm": round(da_cor, 1) + 0.0,
            "diferenca_pct": round(100.0 * (da_cor - em_mm) / em_mm, 1) + 0.0 if em_mm else None,
            "o_que_e": "A soma da chuva lida da cor da imagem do NASA GIBS (a que a conta usou até 2026-11-15) ao "
                       "lado da mesma chuva do satélite em mm (GPM IMERG Late V07, somado de 5 em 5 dias), nos "
                       "períodos em que as duas existem. Fica como registro: a conta hoje usa a chuva em mm de cada "
                       "dia.",
            "origem": f"data/orbita/recente/{cidade_id}/chuva-5-dias.csv (o endereço e a hora de cada consulta "
                      "estão em fonte-5-dias.json, na mesma pasta)"}


def esticar(dias_guardados, dias_da_temperatura, chuva_recente):
    """Estica a série guardada com os dias recentes. Devolve (a série com a chuva recente, a com a chuva de modelo).

    `dias_guardados`: a série do motor (temperatura da NASA POWER e chuva do IMERG guardado), que acaba onde o IMERG
    guardado acaba. `dias_da_temperatura`: a série inteira da NASA POWER (com a chuva de modelo). Os dias seguintes
    entram enquanto houver temperatura e chuva recente, um atrás do outro: dia sem dado nunca vira zero.
    """
    ultimo = dias_guardados[-1].data
    com_recente, com_modelo = list(dias_guardados), list(dias_guardados)
    for dia in dias_da_temperatura:
        if dia.data <= ultimo:
            continue
        if dia.data != com_recente[-1].data + datetime.timedelta(days=1) or chuva_recente.get(dia.data) is None:
            break
        com_recente.append(dia._replace(chuva=chuva_recente[dia.data]))
        com_modelo.append(dia)
    return com_recente, com_modelo


def seguir_com_a_chuva(serie, chuva_recente, ate=None, janela=JANELA_DO_CONSUMO_DIAS):
    """Segue a série até o último dia com chuva do satélite, nos dias em que a temperatura ainda não chegou.

    Cada dia a mais entra com a chuva de verdade do satélite e com o tempo médio dos últimos `janela` dias com
    temperatura (a média da máxima, da mínima e da evaporação de referência): a mesma regra do aviso de sede. Para
    no primeiro dia sem chuva guardada (dia sem dado nunca vira zero) e nunca passa de `ate` (o dia da consulta).
    Devolve (a série seguida, os dias em que o consumo é estimado).
    """
    ultimos = serie[-janela:]
    media = lambda campo: sum(getattr(dia, campo) for dia in ultimos) / len(ultimos)  # noqa: E731
    tmax, tmin, eto = media("tmax"), media("tmin"), media("eto")
    seguida, estimados, dia = list(serie), [], serie[-1].data + datetime.timedelta(days=1)
    while (ate is None or dia <= ate) and chuva_recente.get(dia) is not None:
        seguida.append(clima.Dia(dia, chuva_recente[dia], tmax, tmin, eto))
        estimados.append(dia)
        dia += datetime.timedelta(days=1)
    return seguida, estimados


def _no_dia(registros, data):
    for r in reversed(registros):
        if r.data == data:
            return r
    return None


def _mesmo_dia(data, safra):
    """O mesmo dia do calendário dentro de outra safra ("2015-16"): 11 de novembro de 2026 -> 11 de novembro de 2015."""
    ano = int(safra[:4]) + (0 if data.month >= 9 else 1)
    try:
        return data.replace(year=ano)
    except ValueError:              # 29 de fevereiro em ano que não é bissexto
        return data.replace(year=ano, day=28)


def _retrato(registros, data):
    """A água na terra e a chuva desde o começo da safra (1 de setembro) no dia `data`."""
    r = _no_dia(registros, data)
    if r is None:
        return None
    comeco = datetime.date(data.year if data.month >= 9 else data.year - 1, 9, 1)
    chuva = sum(x.chuva for x in registros if comeco <= x.data <= data)
    return {"data": data.isoformat(), "o_que_esta_na_terra": r.tipo, "agua_na_terra_mm": round(r.agua_na_terra, 1) + 0.0,
            "agua_que_a_terra_segura_mm": round(r.taw, 1) + 0.0,
            "agua_na_terra_pct": round(100.0 * r.agua_na_terra / r.taw, 1) + 0.0,
            "com_sede": bool(r.tipo in rotacoes.CULTURAS and r.ks < 1.0),
            "chuva_desde_1_de_setembro_mm": round(chuva, 1) + 0.0}


def contas_de_hoje(entrada, par, chuva_recente, hoje=None):
    """A conta da água até o último dia com dado, com as duas chuvas: a base do "como está hoje" e do "a lavoura hoje".

    `entrada` já conferida (`motor.validar_entrada`). Devolve as séries (a guardada, a esticada com a chuva rápida do
    satélite e a esticada com a chuva de modelo), os registros da conta com cada uma, o calendário, a rotação e a
    regra dos anos (o ano normal e o pior ano).
    """
    from orbita import motor
    guardados, _ = motor._serie(entrada)
    temperatura = clima.ler_serie(clima.pastas_da_cidade(entrada["cidade_id"])["nasa_power"])
    com_temperatura, com_modelo = esticar(guardados, temperatura, chuva_recente)
    # Desde 2026-11-15 a conta segue até o último dia com chuva do satélite: onde a temperatura ainda não chegou, o
    # consumo é o do tempo médio dos 7 dias anteriores. A conta com a chuva de modelo para no último dia dela.
    com_recente, estimados = seguir_com_a_chuva(com_temperatura, chuva_recente, ate=hoje)
    cal = rotacoes.calendario(par, entrada["plantio_da_soja"])
    registros, rotacao = motor.simular_a_rotacao_de_hoje(entrada, par, com_recente, cal)
    registros_do_modelo, _ = motor.simular_a_rotacao_de_hoje(entrada, par, com_modelo, cal)
    _, regra = motor._regra_dos_anos(entrada, guardados)
    return {"guardados": guardados, "com_recente": com_recente, "com_modelo": com_modelo, "cal": cal,
            "com_temperatura": com_temperatura, "dias_estimados": estimados,
            "registros": registros, "registros_do_modelo": registros_do_modelo, "rotacao": rotacao, "regra": regra}


NA_TERRA = {"soja": "a soja", "milho": "o milho de 2ª safra", "sorgo": "o sorgo de 2ª safra",
            "braquiaria": "a braquiária", "sem_planta": "nenhuma planta viva"}


def _n(numero):
    return f"{numero:.1f}".replace(".", ",")


def como_esta_hoje(entrada, par=None, hoje=None, pasta_da_chuva_recente=None):
    """Como está a água da lavoura no último dia com dado, na rotação de hoje do produtor.

    Compara com o mesmo dia do calendário no ano normal e no pior ano da cidade. `hoje` (uma data) serve para os
    testes; sem ele, vale o dia em que a função é chamada. Sem a chuva recente guardada, diz o que falta.
    """
    from orbita import motor
    entrada = motor.validar_entrada(dict(entrada, chuva=None))      # o "hoje" usa sempre a chuva padrão (o satélite)
    par = par or parametros.carregar()
    hoje = hoje or datetime.date.today()
    cidade = motor.CIDADES[entrada["cidade_id"]]
    recente, fonte = ler_chuva_recente(entrada["cidade_id"], pasta_da_chuva_recente)
    if recente is None:
        return {"disponivel": False, "local": dict(cidade, id=entrada["cidade_id"]),
                "aviso": f"A chuva do dia de {cidade['nome']} não está guardada: rode data/orbita/chuva-do-dia/"
                         "baixar_chuva_do_dia.py para o ponto da cidade."}
    contas = contas_de_hoje(entrada, par, recente, hoje)
    guardados, com_recente, com_modelo = contas["guardados"], contas["com_recente"], contas["com_modelo"]
    registros, registros_do_modelo = contas["registros"], contas["registros_do_modelo"]
    rotacao, regra = contas["rotacao"], contas["regra"]
    ultimo = com_recente[-1].data
    agora = _retrato(registros, ultimo)
    pelo_modelo = _retrato(registros_do_modelo, com_modelo[-1].data)     # o último dia com a chuva de modelo
    com_temperatura, estimados = contas["com_temperatura"][-1].data, contas["dias_estimados"]
    antes = "1 dia" if (hoje - ultimo).days == 1 else f"{(hoje - ultimo).days} dias"
    estimado = (f"; de {data_br(estimados[0])} em diante a temperatura ainda não chegou, e o consumo da cultura é o "
                f"dos {JANELA_DO_CONSUMO_DIAS} dias anteriores" if estimados else "")
    # O que saiu da frase do produtor em 2026-11-15 (a data do dado contra o dia da consulta e até onde vai cada dado).
    detalhe = (f"O último dia com dado é {data_br(ultimo)}, {antes} antes do dia desta consulta ({data_br(hoje)}). "
               f"A chuva do satélite, em mm de cada dia, vai até {data_br(fonte['ultimo_dia_com_dado'])}{estimado}.")
    normal = _retrato(registros, _mesmo_dia(ultimo, regra["ano_normal"]))
    pior = _retrato(registros, _mesmo_dia(ultimo, regra["pior_ano"]))
    primeiro_recente = guardados[-1].data + datetime.timedelta(days=1)
    soma = lambda dias: round(sum(d.chuva for d in dias if d.data >= primeiro_recente), 1) + 0.0  # noqa: E731
    pontas = (agora["agua_na_terra_mm"], agora["agua_na_terra_mm"])     # um número só: a conta com a chuva do dia

    def contra(outro):
        diferenca = round(agora["agua_na_terra_mm"] - outro["agua_na_terra_mm"], 1) + 0.0
        return {"diferenca_mm": diferenca, "leitura": "igual" if abs(diferenca) < 0.05 else (
            "mais água na terra" if diferenca > 0 else "menos água na terra")}

    na_terra = ("a terra estava sem planta viva" if agora["o_que_esta_na_terra"] == "sem_planta"
                else f"na terra estava {NA_TERRA[agora['o_que_esta_na_terra']]}")
    # A data do dado vai escrita: a frase continua verdadeira quando é lida depois (numa conversa guardada).
    frase = (f"Em {cidade['nome']}, em {data_br(ultimo)}, {na_terra} e a conta dava "
             f"{_n(agora['agua_na_terra_mm'])} mm de água na camada de terra onde ficam as raízes, "
             f"{_n(agora['agua_na_terra_pct'])}% do que a terra segura. No mesmo dia do ano normal (safra {regra['ano_normal']}) "
             f"havia {_n(normal['agua_na_terra_mm'])} mm; no do pior ano (safra {regra['pior_ano']}), "
             f"{_n(pior['agua_na_terra_mm'])} mm.")
    return {
        "disponivel": True, "local": dict(cidade, id=entrada["cidade_id"]),
        "rotacao": {"id": rotacao["id"], "nome": rotacao["nome"]}, "terra": entrada["terra"],
        "plantio_da_soja_informado": entrada["plantio_da_soja"],
        "hoje": hoje.isoformat(), "ultimo_dia_com_dado": ultimo.isoformat(), "ultimo_dia_com_dado_de": DIA_DA_CONTA,
        "atraso_dias": (hoje - ultimo).days,
        "ultimo_dia_com_temperatura": com_temperatura.isoformat(), "dias_com_o_consumo_estimado": len(estimados),
        "consumo_estimado_desde": estimados[0].isoformat() if estimados else None,
        "janela_do_consumo_dias": JANELA_DO_CONSUMO_DIAS,
        "safra": balanco.nome_da_safra(ultimo),
        "o_que_esta_na_terra": agora["o_que_esta_na_terra"], "agua_na_terra_mm": agora["agua_na_terra_mm"],
        "agua_que_a_terra_segura_mm": agora["agua_que_a_terra_segura_mm"],
        "agua_na_terra_pct": agora["agua_na_terra_pct"], "com_sede": agora["com_sede"],
        "chuva_desde_1_de_setembro_mm": agora["chuva_desde_1_de_setembro_mm"],
        "faixa_da_agua_na_terra_mm": {"de": pontas[0], "ate": pontas[1]},
        "com_a_chuva_de_modelo": pelo_modelo,
        "no_ano_normal": dict(normal, safra=regra["ano_normal"], **contra(normal)),
        "no_pior_ano": dict(pior, safra=regra["pior_ano"], **contra(pior)),
        "chuva_recente": {
            "de": primeiro_recente.isoformat(), "ate": ultimo.isoformat(), "dias": (ultimo - primeiro_recente).days + 1,
            "satelite_rapido_mm": soma(com_recente), "modelo_da_nasa_power_mm": soma(com_modelo),
            "fonte": fonte, "origem": f"data/orbita/chuva-do-dia/{entrada['cidade_id']}/chuva-do-dia.csv (o endereço "
                                      "e a hora de cada consulta estão em fonte.json, na mesma pasta)",
            "chuva_guardada_ate": guardados[-1].data.isoformat(),
            "conferencia_em_mm": conferencia_em_mm(entrada["cidade_id"],
                                                   ler_chuva_da_cor(entrada["cidade_id"])[0] or {})},
        "frase": frase, "aviso": AVISO_DO_PRODUTOR, "aviso_tecnico": AVISO, "detalhe_tecnico": detalhe}
