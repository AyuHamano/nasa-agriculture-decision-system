# Gerado com IA (Claude)
"""A ficha fechada do produtor: o lugar, o que planta hoje, o tipo de terra, a data do plantio e o que mais preocupa.

A IA conversa e propõe os valores; quem aceita é este arquivo. Só entra valor que está na lista, e as listas vêm do
motor (`ferramentas.listas()`), não se escrevem aqui. O produtor confirma a ficha antes de a conta rodar.

    from orbita import ferramentas, ficha
    listas = ferramentas.listas()
    f = ficha.nova()
    f, aceitos, recusados = ficha.anotar(f, {"cidade_id": "jatai", "terra": "barro"}, listas)
    # aceitos = {"cidade_id": "jatai"}; recusados = {"terra": "... as opções: pouca, media, muita"}
    ficha.falta(f)                 # os campos obrigatórios que ainda estão vazios
    ficha.resumo(f, listas)        # o texto pronto para o produtor conferir

Os campos (os nomes são os da entrada do motor): `cidade_id`, `rotacao_atual` (a lista das culturas), `terra`,
`plantio_da_soja` (opcional, AAAA-MM-DD) e `preocupacao`. Mudar um valor desfaz a confirmação: a ficha nova tem de
ser confirmada de novo. Nenhum dado pessoal é pedido (nome, telefone, CPF, endereço).
"""
import datetime
import re

CAMPOS = ("cidade_id", "rotacao_atual", "terra", "plantio_da_soja", "preocupacao")
OBRIGATORIOS = ("cidade_id", "rotacao_atual", "terra", "preocupacao")
DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PRIMEIRO_ANO = 2000
TERRAS_EM_PALAVRAS = {"pouca": "segura pouca água, como a terra mais arenosa",
                      "media": "segura uma quantidade média de água, como a de textura média",
                      "muita": "segura muita água, como a terra mais argilosa"}
NOMES_DAS_TERRAS = {"pouca": "pouca", "media": "média", "muita": "muita"}
TERRAS_NA_PERGUNTA = {"pouca": "pouca (terra mais arenosa)", "media": "média (textura média)",
                      "muita": "muita (terra mais argilosa)"}
PREOCUPACOES_EM_PALAVRAS = {"agua": "a falta de água", "calor": "o calor forte",
                            "terra": "a terra descoberta (sem planta viva)"}
CONFIRMAR = 'Está certo? Responda "sim" para eu fazer a conta, ou diga o que corrigir.'


def nova():
    return {"cidade_id": None, "rotacao_atual": None, "terra": None, "plantio_da_soja": None, "preocupacao": None,
            "confirmada": False}


def _opcoes(nomes):
    return ", ".join(nomes)


def _uma_ou_outra(nomes):
    """As opções numa frase: "a, b ou c"."""
    nomes = list(nomes)
    return nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " ou " + nomes[-1]


def _ler_rotacao(valor, listas):
    cardapio = listas["rotacoes"]
    if isinstance(valor, str) and valor in cardapio:
        return list(cardapio[valor]["culturas"]), None
    if isinstance(valor, (list, tuple)) and all(isinstance(x, str) for x in valor):
        pedida = [x.strip().lower() for x in valor]
        for item in cardapio.values():
            if list(item["culturas"]) == pedida:
                return pedida, None
    return None, "essa rotação não está no cardápio; as opções: " + _opcoes(
        f'{ident} ({item["nome"]})' for ident, item in cardapio.items())


def _ler_data(valor, hoje):
    if isinstance(valor, str) and DATA.match(valor.strip()):
        try:
            dia = datetime.date.fromisoformat(valor.strip())
        except ValueError:
            dia = None
        if dia and PRIMEIRO_ANO <= dia.year <= (hoje or datetime.date.today()).year + 1:
            return dia.isoformat(), None
    return None, "a data do plantio tem de ser um dia que existe, no formato AAAA-MM-DD (por exemplo, 2026-11-10)"


def _ler(campo, valor, listas, hoje=None):
    """(o valor aceito, None) ou (None, o motivo da recusa, em português)."""
    if campo == "rotacao_atual":
        return _ler_rotacao(valor, listas)
    if campo == "plantio_da_soja":
        return _ler_data(valor, hoje)
    opcoes = {"cidade_id": listas["cidades"], "terra": listas["terras"], "preocupacao": listas["preocupacoes"]}[campo]
    if isinstance(valor, str) and valor in opcoes:
        return valor, None
    return None, "esse valor não está na lista; as opções: " + _opcoes(opcoes)


def anotar(ficha, campos, listas, hoje=None):
    """Põe na ficha os campos que estão na lista. Devolve (a ficha nova, os aceitos, os recusados com o motivo).

    Valor vazio não muda nada. Se algum valor mudou, a ficha deixa de estar confirmada.
    """
    if not isinstance(campos, dict):
        return dict(ficha), {}, {"ficha": "os campos têm de vir num objeto, com o nome de cada campo"}
    aceitos, recusados = {}, {}
    for campo, valor in campos.items():
        if campo not in CAMPOS:
            recusados[str(campo)[:40]] = "esse campo não existe na ficha; os campos: " + _opcoes(CAMPOS)
        elif valor is not None and valor != "" and valor != []:
            certo, motivo = _ler(campo, valor, listas, hoje)
            if certo is None:
                recusados[campo] = motivo
            else:
                aceitos[campo] = certo
    nova_ficha = dict(ficha)
    if any(ficha.get(campo) != valor for campo, valor in aceitos.items()):
        nova_ficha.update(aceitos)
        nova_ficha["confirmada"] = False
    return nova_ficha, aceitos, recusados


def conferir(ficha, listas, hoje=None):
    """A ficha limpa, a partir de uma que veio de fora: valor fora da lista some, e só fica confirmada se completa."""
    limpa = nova()
    if not isinstance(ficha, dict):
        return limpa
    for campo in CAMPOS:
        valor = ficha.get(campo)
        if valor is not None:
            limpa[campo] = _ler(campo, valor, listas, hoje)[0]
    limpa["confirmada"] = ficha.get("confirmada") is True and completa(limpa)
    return limpa


def falta(ficha):
    return [campo for campo in OBRIGATORIOS if not ficha.get(campo)]


def completa(ficha):
    return not falta(ficha)


def confirmar(ficha):
    if not completa(ficha):
        raise ValueError("A ficha ainda não está completa: falta " + _opcoes(falta(ficha)) + ".")
    return dict(ficha, confirmada=True)


def publica(ficha):
    """A ficha como sai na resposta da rota: os 5 campos, `confirmada` e `falta` (o que ainda não foi dito)."""
    return dict({campo: ficha.get(campo) for campo in CAMPOS}, confirmada=ficha.get("confirmada") is True,
                falta=falta(ficha))


def nome_do_lugar(ficha, listas):
    return listas["cidades"].get(ficha.get("cidade_id"))


def nome_da_rotacao(ficha, listas):
    for item in listas["rotacoes"].values():
        if list(item["culturas"]) == list(ficha.get("rotacao_atual") or ()):
            return item["nome"]
    return None


def _data_por_extenso(iso):
    dia = datetime.date.fromisoformat(iso)
    return f"{dia.day:02d}/{dia.month:02d}/{dia.year}"


def resumo(ficha, listas):
    """A ficha em texto, para o produtor conferir. Frases prontas: só o que está na ficha."""
    plantio = ficha.get("plantio_da_soja")
    linhas = ["Confira a sua ficha:",
              f"• Lugar: {nome_do_lugar(ficha, listas)}",
              f"• O que planta hoje: {nome_da_rotacao(ficha, listas)}",
              f"• Terra: {NOMES_DAS_TERRAS.get(ficha['terra'], ficha['terra'])}"
              + (f" ({TERRAS_EM_PALAVRAS[ficha['terra']]})" if ficha["terra"] in TERRAS_EM_PALAVRAS else ""),
              "• Plantio da soja: " + (_data_por_extenso(plantio) if plantio else "pelo calendário da região"),
              f"• O que mais preocupa: {PREOCUPACOES_EM_PALAVRAS.get(ficha['preocupacao'], ficha['preocupacao'])}",
              CONFIRMAR]
    return "\n".join(linhas)


def pergunta_do_que_falta(ficha, listas):
    """A pergunta pronta do que ainda falta na ficha, com as opções de cada campo."""
    perguntas = {
        "cidade_id": "Onde fica a lavoura: " + _uma_ou_outra(listas["cidades"].values()) + "?",
        "rotacao_atual": "O que você planta hoje? As opções: "
                         + "; ".join(item["nome"] for item in listas["rotacoes"].values()) + ".",
        "terra": "Quanta água a sua terra segura: " + _uma_ou_outra(
            TERRAS_NA_PERGUNTA.get(t, t) for t in listas["terras"]) + "? Se não souber, diga média.",
        "preocupacao": "O que mais preocupa você: " + _uma_ou_outra(
            PREOCUPACOES_EM_PALAVRAS.get(p, p) for p in listas["preocupacoes"]) + "?",
    }
    return "Para fazer a conta, preciso saber:\n" + "\n".join("• " + perguntas[campo] for campo in falta(ficha))


def definicao(listas):
    """O que a IA lê da ficha: a ferramenta `anotar_na_ficha`, com as listas fechadas de cada campo."""
    cidades = "; ".join(f"{ident} = {nome}" for ident, nome in listas["cidades"].items())
    cardapio = "; ".join(f'{ident} = {item["nome"]}' for ident, item in listas["rotacoes"].items())
    terras = "; ".join(f"{t} = {TERRAS_EM_PALAVRAS.get(t, t)}" for t in listas["terras"])
    preocupacoes = "; ".join(f"{p} = {PREOCUPACOES_EM_PALAVRAS.get(p, p)}" for p in listas["preocupacoes"])
    return {
        "nome": "anotar_na_ficha",
        "descricao": "Anota na ficha do produtor o que ele disse. Só mande o campo que ele disse nesta conversa; "
                     "não invente nem complete por conta. O programa confere cada valor contra a lista e devolve "
                     "o que entrou, o que foi recusado e o que ainda falta.",
        "parametros": {"type": "object", "additionalProperties": False, "properties": {
            "cidade_id": {"type": "string", "enum": list(listas["cidades"]),
                          "description": "Onde fica a lavoura. " + cidades},
            "rotacao_atual": {"type": "string", "enum": list(listas["rotacoes"]),
                              "description": "O que ele planta hoje, no ano inteiro. " + cardapio},
            "terra": {"type": "string", "enum": list(listas["terras"]),
                      "description": "Quanta água a terra segura. " + terras},
            "plantio_da_soja": {"type": "string",
                                "description": "O dia em que ele plantou (ou vai plantar) a soja, AAAA-MM-DD. Só "
                                               "se ele disser a data."},
            "preocupacao": {"type": "string", "enum": list(listas["preocupacoes"]),
                            "description": "O que mais preocupa o produtor. " + preocupacoes},
        }},
    }
