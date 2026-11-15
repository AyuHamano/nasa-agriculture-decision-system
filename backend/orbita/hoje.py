# Gerado com IA (Claude)
"""O "durante": como está a água da lavoura hoje, perto do ano normal e do pior ano no mesmo dia do calendário.

O problema: a chuva do satélite GPM IMERG entregue pela NASA POWER (a que o motor usa) chega com cerca de 2 meses de
atraso. O caminho rápido, testado em 2026-11-15: a camada diária IMERG_Precipitation_Rate do NASA GIBS (o serviço de
imagens da NASA), sem login, com 2 dias de atraso. O GIBS só entrega imagem; o programa
`data/orbita/recente/baixar_chuva_recente.py` lê a cor do ponto e traduz pela tabela de cores oficial.

O que isso quer dizer para a conta (está tudo em `data/orbita/recente/LEIA-ME.md`):
- a chuva recente é APROXIMADA: vem em faixas de cor, e dia com menos de 2,4 mm sai como zero;
- os dias recentes do GIBS são da versão rápida do IMERG (Early), que a NASA corrige depois; nos 213 dias em que deu
  para comparar com a chuva guardada, a soma ficou 7% abaixo;
- por isso a resposta traz também a mesma conta com a chuva de modelo da NASA POWER (PRECTOTCORR) nos dias recentes:
  os dois números dão a faixa. A chuva de modelo ficou bem abaixo da estação em terra em Rio Verde de 2021 para cá.
O motor não baixa nada na hora da pergunta: lê o que está guardado. Para atualizar, rodar o programa de baixar.
"""
import csv
import datetime
import json

from orbita import balanco, clima, parametros, rotacoes

PASTA_DA_CHUVA_RECENTE = clima.PASTA_DOS_DADOS / "recente"
AVISO = ("A chuva dos dias recentes é aproximada: é a versão rápida do satélite GPM IMERG, lida da cor da imagem "
         "diária do NASA GIBS (dia com menos de 2,4 mm sai como zero), e a NASA ainda corrige esse dado. Ao lado vai "
         "a mesma conta com a chuva de modelo da NASA POWER, para dar a faixa. A temperatura é a de um quadrado de "
         "uns 50 km. É um retrato para conversar com o agrônomo, não uma medida da lavoura.")


def ler_chuva_recente(cidade_id, pasta=None):
    """A chuva recente guardada da cidade: (data -> mm ou None, a ficha da fonte). Sem arquivo: (None, None)."""
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
    return valores, fonte


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
                "aviso": f"A chuva recente de {cidade['nome']} não está guardada: rode data/orbita/recente/"
                         "baixar_chuva_recente.py para o ponto da cidade."}
    guardados, _ = motor._serie(entrada)
    temperatura = clima.ler_serie(clima.pastas_da_cidade(entrada["cidade_id"])["nasa_power"])
    com_recente, com_modelo = esticar(guardados, temperatura, recente)
    cal = rotacoes.calendario(par, entrada["plantio_da_soja"])
    registros, rotacao = motor.simular_a_rotacao_de_hoje(entrada, par, com_recente, cal)
    registros_do_modelo, _ = motor.simular_a_rotacao_de_hoje(entrada, par, com_modelo, cal)
    _, regra = motor._regra_dos_anos(entrada, guardados)
    ultimo = com_recente[-1].data
    agora = _retrato(registros, ultimo)
    pelo_modelo = _retrato(registros_do_modelo, ultimo)
    normal = _retrato(registros, _mesmo_dia(ultimo, regra["ano_normal"]))
    pior = _retrato(registros, _mesmo_dia(ultimo, regra["pior_ano"]))
    primeiro_recente = guardados[-1].data + datetime.timedelta(days=1)
    soma = lambda dias: round(sum(d.chuva for d in dias if d.data >= primeiro_recente), 1) + 0.0  # noqa: E731
    pontas = sorted((agora["agua_na_terra_mm"], pelo_modelo["agua_na_terra_mm"]))

    def contra(outro):
        diferenca = round(agora["agua_na_terra_mm"] - outro["agua_na_terra_mm"], 1) + 0.0
        return {"diferenca_mm": diferenca, "leitura": "igual" if abs(diferenca) < 0.05 else (
            "mais água na terra" if diferenca > 0 else "menos água na terra")}

    frase = (f"Em {cidade['nome']}, o último dia com dado é {ultimo.isoformat()}, {(hoje - ultimo).days} dias antes "
             f"de hoje. Na terra está {NA_TERRA[agora['o_que_esta_na_terra']]}. A conta dá "
             f"{_n(agora['agua_na_terra_mm'])} mm de água na zona das raízes, {_n(agora['agua_na_terra_pct'])}% do "
             f"que a terra segura (com a chuva de modelo no lugar da chuva rápida do satélite, "
             f"{_n(pelo_modelo['agua_na_terra_mm'])} mm). No mesmo dia do ano normal (safra {regra['ano_normal']}) "
             f"havia {_n(normal['agua_na_terra_mm'])} mm; no do pior ano (safra {regra['pior_ano']}), "
             f"{_n(pior['agua_na_terra_mm'])} mm.")
    return {
        "disponivel": True, "local": dict(cidade, id=entrada["cidade_id"]),
        "rotacao": {"id": rotacao["id"], "nome": rotacao["nome"]}, "terra": entrada["terra"],
        "plantio_da_soja_informado": entrada["plantio_da_soja"],
        "hoje": hoje.isoformat(), "ultimo_dia_com_dado": ultimo.isoformat(), "atraso_dias": (hoje - ultimo).days,
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
            "fonte": fonte, "origem": f"data/orbita/recente/{entrada['cidade_id']}/chuva-recente.csv (o endereço e "
                                      "a hora de cada consulta estão em fonte.json, na mesma pasta)",
            "chuva_guardada_ate": guardados[-1].data.isoformat()},
        "frase": frase, "aviso": AVISO}
