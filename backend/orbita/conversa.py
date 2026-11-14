# Gerado com IA (Claude)
"""A conversa em passos, sem guardar nada: a saudação, a terra, as 4 notas e o resultado.

Uso:
    from orbita import conversa
    estado, resposta = conversa.passo(None, "oi")          # o começo: o estado é None
    estado, resposta = conversa.passo(estado, "2")         # depois, o estado que a chamada anterior devolveu

O programa de fora (um serviço de mensagem, o site) guarda o `estado` de cada conversa e devolve na fala seguinte.
Aqui dentro nada fica guardado: a mesma entrada dá sempre a mesma saída. O estado é um dicionário pequeno, que vira
JSON: só a etapa, a terra e as notas já dadas. Nenhum telefone nem nome é pedido, e o que a pessoa escreveu não volta
no estado nem na resposta.

A ordem: a saudação (o que a ferramenta faz e o aviso de que vale só para Rio Verde) -> a terra (1, 2 ou 3) -> as
notas de 1 a 5 para água, solo, renda e erosão (uma pergunta por vez) -> o resultado (o texto do `mensagem.py`).
Resposta fora do esperado: a pergunta volta, com um exemplo. "de novo", em qualquer ponto, recomeça.
Estado que chega estragado (etapa que não existe, nota fora de 1 a 5): a conversa recomeça pela saudação.
"""
import re
import unicodedata

from orbita import mensagem, motor

CIDADE, ROTACAO = "rio_verde", ("soja", "milho", "pousio")
NOTAS = ("agua", "solo", "renda", "erosao")                    # a ordem das perguntas
ETAPAS = ("terra",) + NOTAS + ("fim",)
TERRAS = {"1": "pouca", "2": "media", "3": "muita"}
TERRAS_POR_EXTENSO = {"pouca": "pouca", "pouco": "pouca", "media": "media", "medio": "media", "muita": "muita",
                      "muito": "muita"}
NOTAS_POR_EXTENSO = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5}
DE_NOVO = ("de novo", "denovo", "recomecar", "comecar de novo")

SAUDACAO = (
    "Olá! Aqui é o Órbita Rural. Eu comparo a rotação soja → milho safrinha → pousio (terra parada) com soja → milho "
    "com braquiária (capim) e digo se vale testar a troca: por quê, com que prova e com que risco. Uso o clima que a "
    "NASA registrou e a conta de água da FAO.\n"
    "Aviso: por enquanto a conta vale só para Rio Verde (GO), e não é recomendação: valide com o agrônomo. Não peço "
    "nem guardo nome ou telefone.\n\n"
    "São 5 perguntas rápidas.")
PERGUNTAS = {
    "terra": "Quanta água a sua terra segura? Responda 1 (pouca), 2 (média) ou 3 (muita). Se não souber, responda 2.",
    "agua": "De 1 a 5, quanto pesa para você a água (a lavoura não passar sede)? 1 é pouco, 5 é muito.",
    "solo": "De 1 a 5, quanto pesa o solo (a terra não ficar sem planta)?",
    "renda": "De 1 a 5, quanto pesa a renda (o dinheiro da safra)?",
    "erosao": "De 1 a 5, quanto pesa a erosão (a chuva não levar a terra)?",
}
EXEMPLOS = {"terra": "2", "agua": "5", "solo": "4", "renda": "3", "erosao": "3"}
RECOMECO = "Mande 'de novo' para recomeçar."


def _limpar(texto):
    """A fala em minúsculas, sem acento, sem espaço sobrando e sem pontuação nas pontas."""
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return " ".join(sem_acento.lower().split()).strip(" .!?,;:'\"()")


def _um_numero(fala):
    """O número inteiro da fala, se ela tiver um só; senão, None ("1 a 5", "4,5" e "-3" não valem)."""
    numeros = re.findall(r"-?\d+", fala)
    return int(numeros[0]) if len(numeros) == 1 and len(numeros[0]) <= 3 else None


def _ler_terra(fala):
    if re.search(r"\d", fala):
        return TERRAS.get(str(_um_numero(fala)))
    achadas = {TERRAS_POR_EXTENSO[palavra] for palavra in fala.split() if palavra in TERRAS_POR_EXTENSO}
    return achadas.pop() if len(achadas) == 1 else None


def _ler_nota(fala):
    if re.search(r"\d", fala):
        nota = _um_numero(fala)
        return nota if nota is not None and 1 <= nota <= 5 else None
    return NOTAS_POR_EXTENSO.get(fala[5:] if fala.startswith("nota ") else fala)


def _conferir(estado):
    """O estado limpo (só o que a conversa conhece), ou None se veio vazio ou estragado: aí a conversa recomeça."""
    if not isinstance(estado, dict):
        return None
    etapa = estado.get("etapa")
    if not isinstance(etapa, str) or etapa not in ETAPAS:
        return None
    if etapa in ("terra", "fim"):
        return {"etapa": etapa}
    terra, notas, dadas = estado.get("terra"), estado.get("notas"), NOTAS[:NOTAS.index(etapa)]
    if not isinstance(terra, str) or terra not in TERRAS.values() or not isinstance(notas, dict):
        return None
    if len(notas) != len(dadas) or any(
            isinstance(notas.get(nome), bool) or not isinstance(notas.get(nome), int) or not 1 <= notas[nome] <= 5
            for nome in dadas):
        return None
    return {"etapa": etapa, "terra": terra, "notas": {nome: notas[nome] for nome in dadas}}


def passo(estado, texto):
    """Um passo da conversa: recebe o estado anterior (None no começo) e a fala; devolve (estado novo, resposta)."""
    if estado is not None and not isinstance(estado, dict):
        raise ValueError("Conversa fora do formato: o estado tem de ser o que a chamada anterior devolveu (um objeto) "
                         "ou vazio (null), no começo.")
    if not isinstance(texto, str):
        raise ValueError("Conversa fora do formato: o texto tem de ser a frase que a pessoa escreveu.")
    estado, fala = _conferir(estado), _limpar(texto)
    if estado is None or fala in DE_NOVO:
        return {"etapa": "terra"}, SAUDACAO + "\n\n" + PERGUNTAS["terra"]
    etapa = estado["etapa"]
    if etapa == "fim":
        return estado, "A conta já foi feita. " + RECOMECO
    if etapa == "terra":
        terra = _ler_terra(fala)
        if terra is None:
            return estado, f"Não entendi. {PERGUNTAS['terra']} Exemplo: {EXEMPLOS['terra']}"
        return {"etapa": "agua", "terra": terra, "notas": {}}, PERGUNTAS["agua"]
    nota = _ler_nota(fala)
    if nota is None:
        return estado, f"Não entendi. {PERGUNTAS[etapa]} Responda só com um número de 1 a 5. Exemplo: {EXEMPLOS[etapa]}"
    notas = dict(estado["notas"], **{etapa: nota})
    seguinte = ETAPAS[ETAPAS.index(etapa) + 1]
    if seguinte != "fim":
        return {"etapa": seguinte, "terra": estado["terra"], "notas": notas}, PERGUNTAS[seguinte]
    resposta = motor.responder({"cidade_id": CIDADE, "rotacao_atual": list(ROTACAO), "prioridades": notas,
                                "terra": estado["terra"]})
    return {"etapa": "fim"}, mensagem.texto(resposta) + "\n\n" + RECOMECO
