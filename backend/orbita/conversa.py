# Gerado com IA (Claude)
"""A conversa em passos, sem guardar nada: a saudação, a terra e o resultado.

Uso:
    from orbita import conversa
    estado, resposta = conversa.passo(None, "oi")          # o começo: o estado é None
    estado, resposta = conversa.passo(estado, "2")         # depois, o estado que a chamada anterior devolveu

O programa de fora (um serviço de mensagem, o site) guarda o `estado` de cada conversa e devolve na fala seguinte.
Aqui dentro nada fica guardado: a mesma entrada dá sempre a mesma saída. O estado é um dicionário pequeno, que vira
JSON: só a etapa. Nenhum telefone nem nome é pedido, e o que a pessoa escreveu não volta no estado nem na resposta.

A ordem: a saudação (o que a ferramenta faz e o aviso de que vale só para Rio Verde) -> a terra (1, 2 ou 3) -> o
resultado (o texto do `mensagem.py`). As 4 notas de 1 a 5 (água, solo, renda e erosão) saíram por decisão do dono
(2026-11-15): a conversa não pergunta nem guarda nota.
Resposta fora do esperado: a pergunta volta, com um exemplo. "de novo", em qualquer ponto, recomeça.
Estado que chega estragado (etapa que não existe) ou antigo (parado no meio das notas): a conversa recomeça pela
saudação.
"""
import re
import unicodedata

from orbita import mensagem, motor

CIDADE, ROTACAO = "rio_verde", ("soja", "milho", "pousio")
ETAPAS = ("terra", "fim")                                      # as notas de 1 a 5 saíram (2026-11-15)
TERRAS = {"1": "pouca", "2": "media", "3": "muita"}
TERRAS_POR_EXTENSO = {"pouca": "pouca", "pouco": "pouca", "media": "media", "medio": "media", "muita": "muita",
                      "muito": "muita"}
DE_NOVO = ("de novo", "denovo", "recomecar", "comecar de novo")

SAUDACAO = (
    "Olá! Aqui é o Órbita Rural. Eu comparo a rotação soja → milho safrinha → pousio (terra parada) com soja → milho "
    "com braquiária (capim) e digo se vale testar a troca: por quê, com que prova e com que risco. Uso o clima que a "
    "NASA registrou e a conta de água da FAO.\n"
    "Aviso: por enquanto a conta vale só para Rio Verde (GO), e não é recomendação: valide com o agrônomo. Não peço "
    "nem guardo nome ou telefone.\n\n"
    "É 1 pergunta rápida.")
PERGUNTAS = {
    "terra": "Quanta água a sua terra segura? Responda 1 (pouca), 2 (média) ou 3 (muita). Se não souber, responda 2.",
}
EXEMPLOS = {"terra": "2"}
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


def _conferir(estado):
    """O estado limpo (só o que a conversa conhece), ou None se veio vazio ou estragado: aí a conversa recomeça."""
    if not isinstance(estado, dict):
        return None
    etapa = estado.get("etapa")
    if not isinstance(etapa, str) or etapa not in ETAPAS:
        return None
    return {"etapa": etapa}       # o estado antigo, parado numa nota ("agua", "solo"...), já caiu acima: recomeça


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
    if estado["etapa"] == "fim":
        return estado, "A conta já foi feita. " + RECOMECO
    terra = _ler_terra(fala)
    if terra is None:
        return estado, f"Não entendi. {PERGUNTAS['terra']} Exemplo: {EXEMPLOS['terra']}"
    resposta = motor.responder({"cidade_id": CIDADE, "rotacao_atual": list(ROTACAO), "terra": terra})
    return {"etapa": "fim"}, mensagem.texto(resposta) + "\n\n" + RECOMECO
