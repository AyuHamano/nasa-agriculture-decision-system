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
Cada cobertura tem a sua profundidade de raízes, e por isso a sua caixa. Na troca de cobertura, a caixa nova
começa com a mesma fração de água da anterior (hipótese: a terra está igual em toda a profundidade).
A disputa do capim com o milho (hipótese, em faixa): nos dias em que a cobertura devolve um 4º valor (o fator), o
conjunto milho + capim pede (1 + fator) x o pedido do milho; o freio da sede é o mesmo para os dois, e a água que o
capim bebe sai da mesma caixa. O pedido do milho não muda: o que muda é a terra, que seca mais depressa.
Fora da conta (limites): a enxurrada (toda chuva entra até encher), a subida de água do lençol e a irrigação.
"""
import collections
import datetime

from orbita import parametros, rotacoes
from orbita.rotacoes import BRAQUIARIA, CULTURAS, SEM_PLANTA  # noqa: F401 (reexportados)

Registro = collections.namedtuple("Registro", "data tipo chuva eto pedido bebido ks agua_na_terra percolacao taw "
                                  "falta_em_cima bebido_do_capim", defaults=(0.0,))
CAMADA_DE_CIMA_M = 0.10  # a camada que a evaporação seca: os TEW da Tabela 19 do FAO-56 valem para Ze = 0,10 m
SAFRAS_DO_ESTUDO = tuple(f"{ano}-{(ano + 1) % 100:02d}" for ano in range(2015, 2025))
TIPOS = ("soja", "milho", "sorgo", BRAQUIARIA, SEM_PLANTA)


def balanco_diario(dias, cobertura, taw, tew, rew, ajustar_p=True, fracao_inicial=0.5, parte_de_cima=None):
    """Roda a caixa-d'água em todos os dias, em sequência. `cobertura(data)` devolve (tipo, Kc, p).

    `taw` é um número (a mesma caixa para tudo) ou um dicionário tipo -> TAW (cada cobertura com a sua raiz).
    `parte_de_cima`: tipo -> a parte do que a planta bebe que sai da camada de cima (sem isso, tudo). A camada de
    cima tem o seu próprio balanço (FAO-56, eq. 77): a troca de cobertura não mexe nela; terra cheia, camada cheia.
    Se a cobertura devolver um 4º valor (o fator da disputa), o capim junto da cultura bebe da mesma caixa.
    """
    parte_de_cima = parte_de_cima or {}
    taws = dict(taw) if isinstance(taw, dict) else {tipo: float(taw) for tipo in TIPOS}
    taws.setdefault("sorgo", taws.get("milho"))     # sem a caixa do sorgo, vale a do milho (as duas são da 2ª safra)
    if any(valor <= 0 for valor in taws.values()) or tew <= rew or rew < 0:
        raise ValueError("A terra precisa de TAW acima de zero e de TEW maior que REW.")
    if not 0.0 <= fracao_inicial <= 1.0:
        raise ValueError("A água do começo é uma fração entre 0 (terra seca) e 1 (terra cheia).")
    vazio = 1.0 - fracao_inicial        # a fração da caixa que está vazia
    de = None                           # a falta na camada de cima (mm)
    registros = []
    for dia in dias:
        tipo, kc, p_da_tabela, *resto = cobertura(dia.data)
        junto = 1.0 + (resto[0] if resto else 0.0)      # o conjunto pede `junto` vezes o pedido da cultura
        caixa = taws[tipo]
        dr = vazio * caixa              # a falta na zona das raízes (mm)
        if de is None:
            de = min(tew, dr)
        pedido = kc * dia.eto
        if tipo == SEM_PLANTA:
            ks = 1.0 if de <= rew else max(0.0, (tew - de) / (tew - rew))
        else:
            p = p_da_tabela
            if ajustar_p:
                p = min(0.8, max(0.1, p_da_tabela + 0.04 * (5.0 - pedido * junto)))
            ks = 1.0 if dr <= p * caixa else max(0.0, (caixa - dr) / ((1.0 - p) * caixa))
        saiu = max(0.0, min(ks * pedido * junto, caixa - dr + dia.chuva))   # o que a cultura e o capim beberam
        bebido = saiu / junto
        novo = dr - dia.chuva + saiu
        percolacao = max(0.0, -novo)
        dr = min(caixa, max(0.0, novo))
        parte = 1.0 if tipo == SEM_PLANTA else parte_de_cima.get(tipo, 1.0)
        de = 0.0 if dr == 0.0 else min(tew, max(0.0, de - dia.chuva + saiu * parte))
        vazio = dr / caixa
        registros.append(Registro(dia.data, tipo, dia.chuva, dia.eto, pedido, bebido, ks, caixa - dr, percolacao,
                                  caixa, de, saiu - bebido))
    return registros


def agua_da_terra(par, terra, cal=None):
    """A água que a terra segura por cobertura (TAW, eq. 82), mais TEW e REW da opção de terra."""
    if terra not in par["terra"]:
        raise ValueError(f"Terra desconhecida: '{terra}'. Use pouca, media ou muita (quanta água a terra segura).")
    cal = cal or rotacoes.calendario(par)
    por_metro = parametros.valor(par, "terra", terra, "agua_mm_por_m")
    return {"taw": {tipo: por_metro * raiz for tipo, raiz in cal.raizes.items()},
            "tew": parametros.valor(par, "terra", terra, "tew_mm"),
            "rew": parametros.valor(par, "terra", terra, "rew_mm"),
            "agua_mm_por_m": por_metro, "raizes_m": dict(cal.raizes)}


def simular(dias, com_braquiaria, par=None, terra="media", fracao_inicial=0.5, disputa=0.0, cal=None,
            segunda="milho"):
    """A simulação contínua de uma rotação em todos os dias da série.

    `disputa`: o fator a mais no pedido de água enquanto o milho e o capim crescem juntos (só na alternativa).
    `cal`: o calendário já montado (com a data de plantio do produtor); sem ele, vale o de costume.
    `segunda`: a cultura da 2ª safra da rotação (milho ou sorgo).
    """
    if disputa < 0 or (disputa and not com_braquiaria):
        raise ValueError("A disputa do capim com o milho é um fator de zero para cima e só vale na alternativa "
                         "(a rotação com braquiária).")
    par = par or parametros.carregar()
    cal = cal or rotacoes.calendario(par)
    agua = agua_da_terra(par, terra, cal)
    return balanco_diario(dias, lambda data: rotacoes.cobertura_do_dia(data, com_braquiaria, cal, disputa, segunda),
                          agua["taw"], agua["tew"], agua["rew"],
                          ajustar_p=parametros.valor(par, "ajustar_p_pela_demanda"), fracao_inicial=fracao_inicial,
                          parte_de_cima={tipo: min(1.0, CAMADA_DE_CIMA_M / raiz) for tipo, raiz in cal.raizes.items()})


def nome_da_safra(data):
    """A safra vai de 1 de setembro a 31 de agosto: 2015-09-01 a 2016-08-31 é a safra 2015-16."""
    ano = data.year if data.month >= 9 else data.year - 1
    return f"{ano}-{(ano + 1) % 100:02d}"


def _zero():
    return {"pedido_mm": 0.0, "bebido_mm": 0.0, "dias": 0, "dias_de_sede": 0, "bebido_do_capim_mm": 0.0}


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
        conta["bebido_do_capim_mm"] += r.bebido_do_capim
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
    """Por safra: a água (mm) na zona das raízes da soja no dia do plantio, antes da chuva do dia."""
    saida = {}
    for anterior, atual in zip(registros, registros[1:]):
        if atual.tipo == "soja" and anterior.tipo != "soja":
            saida[nome_da_safra(atual.data)] = anterior.agua_na_terra / anterior.taw * atual.taw
    return saida


def chuva_da_janela(dias, ano, inicio=(2, 1), fim=(6, 30)):
    """A chuva somada de 1/fev a 30/jun do ano (a janela da 2ª safra)."""
    a, b = datetime.date(ano, *inicio), datetime.date(ano, *fim)
    return sum(d.chuva for d in dias if a <= d.data <= b)
