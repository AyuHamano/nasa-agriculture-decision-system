# Gerado com IA (Claude)
"""O texto curto para mensagem (WhatsApp ou outro): a resposta do motor em poucas linhas, em português simples.

Uso:
    from orbita import mensagem, motor
    texto = mensagem.texto(motor.responder(entrada))

O texto traz, nesta ordem: a pergunta, a resposta, o resultado nas prioridades de maior nota, um número de prova de
cada medida mostrada (com a fonte dita em palavras), o risco em uma frase e "valide com o agrônomo". Não tem tabela nem
markdown e cabe em uns 900 caracteres.

Não há IA aqui: são frases prontas, preenchidas só com o que está na resposta do motor. Todo número do texto está na
resposta (o teste confere com `orbita.conferencia.conferir_texto`).

A resposta do motor pode ganhar campos novos; os nomes de hoje não mudam. Por isso cada campo é lido com cuidado: se
um campo esperado faltar (ou vier de outro tipo), o texto sai sem aquele trecho, sem quebrar.
"""
import math

LIMITE = 900                    # o tamanho que o texto não passa com as respostas de hoje (o teste confere)
QUANTAS_PRIORIDADES = 2         # quantas prioridades, da maior nota para a menor, entram no texto
QUEM = {"atual": "a rotação de hoje se saiu melhor", "alternativa": "a alternativa se saiu melhor",
        "empate": "empate", "não medido": "não medido (a conta não tem preço, custo nem produtividade)"}
# O veredito da água pela faixa (os ajustes de 2026-11-14): se a prioridade trouxer `veredito_pela_faixa`, é ele que
# vai no texto; sem esse campo, vale o `melhor`, como antes.
PELA_FAIXA = {"alternativa_melhor": "a alternativa se saiu melhor", "alternativa_pior": "a alternativa se saiu pior",
              "empate": "empate",
              "depende_da_hipotese": "depende da hipótese"}
RISCO_DA_BRAQUIARIA = ("O risco: a braquiária também bebe água depois do milho, e a terra pode chegar mais seca ao "
                       "plantio da soja.")
FECHO = "Isto é uma conta, não uma recomendação: valide com o agrônomo antes de decidir."


def _pega(coisa, *caminho):
    """O valor que está no fim do caminho, ou None se algum pedaço do caminho faltar."""
    for chave in caminho:
        if not isinstance(coisa, dict) or not isinstance(chave, str) or chave not in coisa:
            return None
        coisa = coisa[chave]
    return coisa


def _frase(valor):
    """O texto, se for mesmo um texto com alguma coisa escrita; senão, None."""
    return valor.strip() if isinstance(valor, str) and valor.strip() else None


def _inteiro(valor):
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


def _numero(valor):
    """O número em português (inteiro sem casa; o resto com uma casa e vírgula). O que não é número devolve None."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        return None
    return str(valor) if isinstance(valor, int) else f"{valor:.1f}".replace(".", ",")


def _pergunta(r):
    hoje, alternativa = _frase(_pega(r, "rotacoes", "atual", "nome")), _frase(_pega(r, "rotacoes", "alternativa", "nome"))
    if hoje and alternativa:
        return f'Pergunta: vale trocar "{hoje}" por "{alternativa}"?'
    pergunta = _frase(_pega(r, "pergunta"))
    return f"Pergunta: {pergunta}" if pergunta else None


def _prioridades(r, quantas):
    """As prioridades de maior nota: [(o id, a linha)]. A que vier sem nome ou sem resultado fica de fora."""
    lista = _pega(r, "prioridades")
    validas = []
    for p in lista if isinstance(lista, list) else []:
        nome, quem = _frase(_pega(p, "nome")), _frase(_pega(p, "melhor"))
        if nome and quem in QUEM:
            pela_faixa = PELA_FAIXA.get(_frase(_pega(p, "veredito_pela_faixa")))
            validas.append((_inteiro(_pega(p, "nota")), _frase(_pega(p, "id")), nome, pela_faixa or QUEM[quem]))
    validas.sort(key=lambda p: -p[0] if p[0] is not None else 1)       # a maior nota primeiro; o empate fica como veio
    return [(ident, f"{nome}{'' if nota is None else f' (nota {nota})'}: {quem}.")
            for nota, ident, nome, quem in validas[:max(quantas, 0)]]


def _titulo_das_prioridades(r):
    """Com as notas, "Nas suas maiores notas"; sem elas (as notas saíram), o que mais preocupa ou o que foi medido."""
    lista = _pega(r, "prioridades")
    if isinstance(lista, list) and any(_inteiro(_pega(p, "nota")) is not None for p in lista):
        return "Nas suas maiores notas:"
    return "No que mais preocupa:" if _frase(_pega(r, "preocupacao")) else "No que foi medido:"


def _fonte_da_agua(r):
    """De onde vem o número da água, em palavras (sem link): a chuva e a conta."""
    chuva = _frase(_pega(r, "clima", "chuva", "fonte"))
    chuva = _frase(chuva.split(" (")[0]) if chuva else None             # sem o detalhe técnico entre parênteses
    return f"Fontes: {chuva} (a chuva) e a FAO (a conta de água)." if chuva else "Fonte: a conta de água da FAO."


def _prova_da_agua(r):
    pior = _frase(_pega(r, "comparacao", "pior_ano"))
    hoje = _numero(_pega(r, "rotacoes", "atual", "safras", pior, "total", "falta_mm"))
    alternativa = _numero(_pega(r, "rotacoes", "alternativa", "safras", pior, "total", "falta_mm"))
    if not (pior and hoje and alternativa):
        return None
    quando = "no ano mais seco" if _pega(r, "regra_dos_anos", "regra") == "chuva" else "no pior ano"
    # O pior ano é o da pior colheita, não o de maior falta de água: se a conta deu nele menos falta (ou a mesma)
    # que no ano normal, o texto chama o ano pelo que ele é.
    do_pior = _pega(r, "rotacoes", "atual", "safras", pior, "total", "falta_mm")
    do_normal = _pega(r, "rotacoes", "atual", "safras", _frase(_pega(r, "comparacao", "ano_normal")), "total", "falta_mm")
    if quando == "no pior ano" and _numero(do_pior) and _numero(do_normal) and do_pior <= do_normal:
        quando = "no ano da pior colheita da região"
    menor = _numero(_pega(r, "rotacoes", "alternativa", "faixa", pior, "falta_total_mm", "menor"))
    maior = _numero(_pega(r, "rotacoes", "alternativa", "faixa", pior, "falta_total_mm", "maior"))
    if menor and maior and menor != maior:      # a alternativa em faixa, pela disputa do capim com o milho
        return (f"{quando} (safra {pior}), faltaram {hoje} mm de água na rotação de hoje e de {menor} a {maior} mm na "
                f"alternativa. {_fonte_da_agua(r)}")
    return (f"{quando} (safra {pior}), faltaram {hoje} mm de água na rotação de hoje e {alternativa} mm na "
            f"alternativa. {_fonte_da_agua(r)}")


def _prova_do_calendario(r):
    hoje = _inteiro(_pega(r, "comparacao", "solo_e_erosao", "dias_sem_planta_viva_hoje"))
    alternativa = _inteiro(_pega(r, "comparacao", "solo_e_erosao", "dias_sem_planta_viva_alternativa"))
    if hoje is None or alternativa is None:
        return None
    return (f"pelo calendário das culturas, a terra fica {hoje} dias por ano sem planta viva hoje e "
            f"{alternativa} na alternativa.")


def _prova(r, ids):
    """Um número de prova de cada medida mostrada, com a fonte em palavras. Sem prioridade medida, vai a do destaque."""
    medidas = [i for i in ids if i in ("agua", "solo", "erosao")] or [_frase(_pega(r, "destaque", "prioridade"))]
    frases = [_prova_da_agua(r) if "agua" in medidas else None,
              _prova_do_calendario(r) if "solo" in medidas or "erosao" in medidas else None]
    frases = [f for f in frases if f] or [f for f in (_prova_da_agua(r), _prova_do_calendario(r)) if f][:1]
    if not frases:
        return None
    return "A prova: " + " ".join([frases[0]] + [f[0].upper() + f[1:] for f in frases[1:]])


def _risco(r):
    alternativa = _frase(_pega(r, "rotacoes", "alternativa", "nome")) or ""
    return RISCO_DA_BRAQUIARIA if "braquiária" in alternativa.lower() else None


def texto(resposta, quantas=QUANTAS_PRIORIDADES):
    """O texto curto, a partir da resposta do motor (`motor.responder`). Nunca quebra por campo que falta."""
    r = resposta if isinstance(resposta, dict) else {}
    local, veredito = _frase(_pega(r, "local", "nome")), _frase(_pega(r, "veredito", "frase"))
    prioridades = _prioridades(r, quantas if _inteiro(quantas) is not None else QUANTAS_PRIORIDADES)
    blocos = [[f"Órbita Rural · {local}" if local else "Órbita Rural", _pergunta(r)],
              [f"Resposta: {veredito}" if veredito else None],
              ([_titulo_das_prioridades(r)] + [linha for _, linha in prioridades]) if prioridades else [],
              [_prova(r, [ident for ident, _ in prioridades])],
              [_risco(r)],
              [FECHO]]
    return "\n\n".join("\n".join(linha for linha in bloco if linha) for bloco in blocos if any(bloco))
