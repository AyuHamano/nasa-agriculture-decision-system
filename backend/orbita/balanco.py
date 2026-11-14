# Gerado com IA (Claude)
"""A água na terra, dia a dia (FAO-56, cap. 8: https://www.fao.org/4/X0490E/x0490e0e.htm).

A terra é uma caixa-d'água na zona das raízes:
- TAW, a água que a terra segura = água por metro x profundidade das raízes (eq. 82);
- RAW, a parte fácil de tirar = p x TAW (eq. 83);
- Ks, o freio da sede: 1 enquanto a falta na caixa (Dr) não passa de RAW; depois, (TAW - Dr) / ((1 - p) x TAW) (eq. 84);
- o dia: Dr de hoje = Dr de ontem - chuva + o que a planta bebeu + o que escorreu para baixo (eq. 85), entre 0 e TAW
  (eq. 86); a chuva que passa de encher a caixa se perde (eq. 88).
O que a planta pede = Kc x ETo; o que bebe = Ks x o que pede; a falta de água = pedido - bebido.

Terra sem planta viva: a evaporação não é zero, mas só seca a camada de cima (FAO-56, cap. 7, eq. 74: o freio Kr
cai de 1 a 0 entre REW e TEW, a água que a evaporação consegue tirar; Tabela 19).
Fora da conta (limites): a enxurrada (toda chuva entra até encher), a subida de água do lençol e a irrigação.
"""
import collections
import datetime

from orbita import parametros, rotacoes
from orbita.rotacoes import BRAQUIARIA, CULTURAS, SEM_PLANTA  # noqa: F401 (reexportados)

Registro = collections.namedtuple("Registro", "data tipo chuva eto pedido bebido ks agua_na_terra percolacao")
SAFRAS_DO_ESTUDO = tuple(f"{ano}-{(ano + 1) % 100:02d}" for ano in range(2015, 2025))
TIPOS = ("soja", "milho", BRAQUIARIA, SEM_PLANTA)


def balanco_diario(dias, cobertura, taw, tew, rew, ajustar_p=True, fracao_inicial=0.5):
    """Roda a caixa-d'água em todos os dias, em sequência. `cobertura(data)` devolve (tipo, Kc, p)."""
    if taw <= 0 or tew <= rew or rew < 0:
        raise ValueError("A terra precisa de TAW acima de zero e de TEW maior que REW.")
    if not 0.0 <= fracao_inicial <= 1.0:
        raise ValueError("A água do começo é uma fração entre 0 (terra seca) e 1 (terra cheia).")
    dr = taw * (1.0 - fracao_inicial)   # a falta na zona das raízes
    de = min(tew, dr)                   # a falta na camada de cima
    registros = []
    for dia in dias:
        tipo, kc, p_da_tabela = cobertura(dia.data)
        pedido = kc * dia.eto
        if tipo == SEM_PLANTA:
            ks = 1.0 if de <= rew else max(0.0, (tew - de) / (tew - rew))
        else:
            p = p_da_tabela
            if ajustar_p:
                p = min(0.8, max(0.1, p_da_tabela + 0.04 * (5.0 - pedido)))
            ks = 1.0 if dr <= p * taw else max(0.0, (taw - dr) / ((1.0 - p) * taw))
        bebido = max(0.0, min(ks * pedido, taw - dr + dia.chuva))
        novo = dr - dia.chuva + bebido
        percolacao = max(0.0, -novo)
        dr = min(taw, max(0.0, novo))
        de = min(tew, max(0.0, de - dia.chuva + bebido), dr)
        registros.append(Registro(dia.data, tipo, dia.chuva, dia.eto, pedido, bebido, ks, taw - dr, percolacao))
    return registros


def agua_da_terra(par, terra):
    """TAW, TEW e REW da opção de terra (pouca, media ou muita)."""
    if terra not in par["terra"]:
        raise ValueError(f"Terra desconhecida: '{terra}'. Use pouca, media ou muita (quanta água a terra segura).")
    por_metro = parametros.valor(par, "terra", terra, "agua_mm_por_m")
    raizes = parametros.valor(par, "raizes_m")
    return {"taw": por_metro * raizes, "tew": parametros.valor(par, "terra", terra, "tew_mm"),
            "rew": parametros.valor(par, "terra", terra, "rew_mm"), "agua_mm_por_m": por_metro, "raizes_m": raizes}


def simular(dias, com_braquiaria, par=None, terra="media", fracao_inicial=0.5):
    """A simulação contínua de uma rotação em todos os dias da série."""
    par = par or parametros.carregar()
    cal = rotacoes.calendario(par)
    agua = agua_da_terra(par, terra)
    return balanco_diario(dias, lambda data: rotacoes.cobertura_do_dia(data, com_braquiaria, cal),
                          agua["taw"], agua["tew"], agua["rew"],
                          ajustar_p=parametros.valor(par, "ajustar_p_pela_demanda"), fracao_inicial=fracao_inicial)


def nome_da_safra(data):
    """A safra vai de 1 de setembro a 31 de agosto: 2015-09-01 a 2016-08-31 é a safra 2015-16."""
    ano = data.year if data.month >= 9 else data.year - 1
    return f"{ano}-{(ano + 1) % 100:02d}"


def _zero():
    return {"pedido_mm": 0.0, "bebido_mm": 0.0, "dias": 0, "dias_de_sede": 0}


def _fechar(conta):
    conta["falta_mm"] = conta["pedido_mm"] - conta["bebido_mm"]
    conta["falta_relativa_pct"] = 100.0 * conta["falta_mm"] / conta["pedido_mm"] if conta["pedido_mm"] > 0 else 0.0
    return conta


def numeros_por_safra(registros):
    """Por safra e por tipo de cobertura: o pedido, o bebido, a falta (mm e %), os dias e os dias de sede (Ks < 1).

    "total" soma só as culturas (soja e milho). A braquiária e a terra sem planta ficam à parte.
    """
    safras = {}
    for r in registros:
        safra = safras.setdefault(nome_da_safra(r.data), {tipo: _zero() for tipo in TIPOS})
        conta = safra[r.tipo]
        conta["pedido_mm"] += r.pedido
        conta["bebido_mm"] += r.bebido
        conta["dias"] += 1
        if r.ks < 1.0:
            conta["dias_de_sede"] += 1
    for safra in safras.values():
        total = _zero()
        for cultura in CULTURAS:
            for chave in total:
                total[chave] += safra[cultura][chave]
        for tipo in TIPOS:
            _fechar(safra[tipo])
        safra["total"] = _fechar(total)
    return safras


def agua_no_plantio_da_soja(registros):
    """Por safra: a água na terra (mm) no fim do dia anterior ao plantio da soja."""
    saida = {}
    for anterior, atual in zip(registros, registros[1:]):
        if atual.tipo == "soja" and anterior.tipo != "soja":
            saida[nome_da_safra(atual.data)] = anterior.agua_na_terra
    return saida


def chuva_da_janela(dias, ano, inicio=(2, 1), fim=(6, 30)):
    """A chuva somada de 1/fev a 30/jun do ano (a janela da 2ª safra)."""
    a, b = datetime.date(ano, *inicio), datetime.date(ano, *fim)
    return sum(d.chuva for d in dias if a <= d.data <= b)
