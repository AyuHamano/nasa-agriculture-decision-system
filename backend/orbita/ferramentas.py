# Gerado com IA (Claude)
"""As 4 ferramentas do agente: o clima do lugar, o ensaio da rotação, o verde do satélite e a lavoura hoje (o painel).

Cada ferramenta chama uma função do motor e devolve o que a IA pode ler. A IA não faz conta: ela pede, o motor
responde, e o texto dela é conferido depois contra o que saiu daqui (`agente.py`).

    from orbita import ferramentas
    ferramentas.listas()                                  # as listas fechadas da ficha, lidas do motor
    ferramentas.ensaio_da_rotacao(ficha)                  # a comparação de 3 rotações ou mais
    ferramentas.ensaio_da_rotacao(ficha, "pior_ano")      # ... mais o replay daquela safra, dia a dia
    ferramentas.clima_do_lugar(ficha, hoje=True)          # ... mais "como está hoje", se o motor tiver
    ferramentas.verde_do_satelite(ficha, "2015-16")       # ... mais o registro daquela safra

Os três momentos do produtor cabem nas três: antes (o ensaio), durante (o replay de uma safra e o "como está
hoje") e depois (o verde do satélite e o registro da safra).

O que o motor oferece está combinado no mapa do projeto (seção 7.2): `motor.responder` com a chave
`comparacao_das_rotacoes`, `motor.clima_do_lugar`, `motor.verde_do_satelite`, `motor.replay_da_safra`,
`motor.como_esta_hoje` e `motor.registro_da_safra`. Nos testes, um dublê no mesmo formato entra no lugar de
`ferramentas.motor`. Se o motor não tiver uma função, a ferramenta diz isso em português (`ContaIndisponivel`); o
"como está hoje" e o registro são opcionais e viram um aviso dentro da resposta.
"""
import json
import re

from orbita import motor, rotacoes

NOMES = ("clima_do_lugar", "ensaio_da_rotacao", "verde_do_satelite", "lavoura_hoje")
PREOCUPACOES = ("agua", "calor", "terra")           # o mapa, seção 7.2; vale a lista do motor, se ele tiver uma
MINIMO_DE_ROTACOES = 3                              # contando a de hoje (a condição do desafio)
FRASES_DA_ROTACAO = ("evidencia", "beneficio", "risco", "falta_saber")
SAFRA = re.compile(r"^(?:19|20)\d{2}-\d{2}$")
ANOS_POR_NOME = ("pior_ano", "ano_normal")
TETO_PARA_A_IA = 24000                              # caracteres de JSON que uma consulta entrega à IA
PESADOS = ("dias", "parametros", "safras", "limites", "serie")     # o que não vai à IA (vai à tela, se for o caso)
AVISO_SEM_HOJE = "O acompanhamento do dia de hoje ainda não está ligado: é o próximo passo."
AVISO_SEM_REGISTRO = "O registro da safra ainda não está ligado: é o próximo passo."
AVISO_SEM_LAVOURA = "O painel da lavoura hoje ainda não está ligado: é o próximo passo."
CAMPOS_DA_LAVOURA = ("cidade_id", "rotacao_atual", "terra", "plantio_da_soja")     # o que motor.lavoura_hoje aceita
TETO_DO_PAINEL = 6000                               # caracteres de JSON que o painel entrega à IA
TEXTO_CURTO = 40                                    # texto maior que isto, fora a `frase`, não vai à IA no painel
# O que não vai à IA no painel: a data da consulta e o atraso do dado (não viram ressalva) e as explicações longas.
FORA_DO_PAINEL = ("hoje", "atraso_dias", "dia_da_consulta", "dias_ja_passados_ate_a_consulta", "sem_chuva_a_partir_de",
                  "janela_dias", "horizonte_dias", "janela_do_consumo_dias", "dias_do_consumo", "dias_por_imagem",
                  "ultimo_dia_com_temperatura", "dias_com_o_consumo_estimado", "consumo_estimado_desde",
                  "situacao", "titulo")


class ContaIndisponivel(Exception):
    """O motor não tem (ainda) o que a ferramenta precisa. A frase é em português e pode ir a quem chamou."""


class FichaRecusada(ValueError):
    """O motor recusou a ficha (data fora da janela, rotação que ele não conhece). A frase é a do motor."""


def _copia(coisa):
    """O mesmo dado, como ele fica depois de virar JSON (sem tupla, sem data solta)."""
    return json.loads(json.dumps(coisa, ensure_ascii=False, default=str))


def _culturas(ident, dados):
    """A lista de culturas de um item do cardápio do motor, ou None se o item não serve de rotação de hoje."""
    for chave in ("culturas", "rotacao", "rotacao_atual", "sequencia"):
        valor = dados.get(chave) if isinstance(dados, dict) else None
        if isinstance(valor, (list, tuple)) and valor and all(isinstance(x, str) for x in valor):
            return [x.strip().lower() for x in valor]
    if ident == "atual":                            # o formato de antes: só a rotação de hoje podia entrar
        return [str(x) for x in getattr(motor, "ROTACAO_DE_HOJE", ())] or None
    return None


def cardapio():
    """As rotações que o produtor pode dizer que planta hoje: id -> {"nome", "culturas"}. Vem do motor."""
    fonte = getattr(motor, "ROTACOES", None) or rotacoes.ROTACOES
    itens = {}
    for chave, dados in fonte.items():
        culturas = _culturas(chave, dados)
        if culturas:
            ident = (dados.get("id") if isinstance(dados, dict) else None) or chave     # o id do cardápio, se houver
            nome = dados.get("nome") if isinstance(dados, dict) else None
            itens[str(ident)] = {"nome": nome or " → ".join(culturas), "culturas": culturas}
    return itens


def listas():
    """As listas fechadas da ficha. Nenhuma é escrita aqui: todas saem do motor."""
    cidades = {str(ident): (dados.get("nome") if isinstance(dados, dict) else None) or str(ident)
               for ident, dados in motor.CIDADES.items()}
    onde = {str(ident): (dados["latitude"], dados["longitude"]) for ident, dados in motor.CIDADES.items()
            if isinstance(dados, dict) and isinstance(dados.get("latitude"), (int, float))
            and isinstance(dados.get("longitude"), (int, float))}
    return {"cidades": cidades, "onde": onde, "rotacoes": cardapio(), "terras": tuple(motor.TERRAS),
            "preocupacoes": tuple(getattr(motor, "PREOCUPACOES", PREOCUPACOES))}


def entrada_do_motor(ficha):
    """A ficha no formato da entrada do motor (o mapa, seção 7.2). Campo opcional vazio não vai."""
    entrada = {"cidade_id": ficha.get("cidade_id"), "rotacao_atual": list(ficha.get("rotacao_atual") or ()),
               "terra": ficha.get("terra")}
    for campo in ("plantio_da_soja", "preocupacao"):
        if ficha.get(campo):
            entrada[campo] = ficha[campo]
    return entrada


def _chamar_o_motor(nome, *argumentos):
    funcao = getattr(motor, nome, None)
    if funcao is None:
        raise ContaIndisponivel(f"O motor ainda não tem a função {nome}: essa parte da conta não está ligada.")
    try:
        return _copia(funcao(*argumentos))
    except ValueError as erro:
        if str(erro).startswith("Entrada fora do formato"):
            raise FichaRecusada(str(erro)) from None
        raise


def conferir_comparacao(lista):
    """A comparação do motor, se ela cumpre o combinado: 3 rotações ou mais, a de hoje entre elas, cada uma com as
    quatro frases (a evidência, o benefício, o risco e o que falta saber). Senão, `ContaIndisponivel`."""
    if not isinstance(lista, list) or len(lista) < MINIMO_DE_ROTACOES:
        quantas = len(lista) if isinstance(lista, list) else 0
        raise ContaIndisponivel(f"A conta trouxe {quantas} rotações para comparar; o agente só responde com "
                                f"{MINIMO_DE_ROTACOES} ou mais, contando a de hoje.")
    for item in lista:
        if not isinstance(item, dict) or not isinstance(item.get("nome"), str) or not item["nome"].strip():
            raise ContaIndisponivel("A conta trouxe uma rotação sem nome na comparação.")
        faltam = [f for f in FRASES_DA_ROTACAO if not isinstance(item.get(f), str) or not item[f].strip()]
        if faltam:
            raise ContaIndisponivel(f'A rotação "{item["nome"]}" veio sem: {", ".join(faltam)}.')
    if not any(item.get("de_hoje") is True for item in lista):
        raise ContaIndisponivel("A comparação veio sem a rotação de hoje do produtor.")
    return lista


def _qual_safra(safra, anos):
    """A safra pedida: "2015-16", ou o nome "pior_ano" / "ano_normal", que se resolve pela regra dos anos."""
    if safra in ANOS_POR_NOME:
        safra = (anos or {}).get(safra)
    if not isinstance(safra, str) or not SAFRA.match(safra):
        raise FichaRecusada('Entrada fora do formato: a safra tem de ser como "2015-16", ou "pior_ano", ou '
                            '"ano_normal".')
    return safra


def _enxugar(coisa, teto=TETO_PARA_A_IA):
    """O que vai à IA: sem as listas pesadas e, se ainda passar do teto, sem os pedaços maiores (diz quais saíram)."""
    if isinstance(coisa, dict):
        coisa = {chave: _enxugar(valor, teto) for chave, valor in coisa.items() if chave not in PESADOS}
        cortados = []
        while len(json.dumps(coisa, ensure_ascii=False)) > teto and len(coisa) > 1:
            maior = max((c for c in coisa if c not in ("cortado_por_tamanho", "rotacoes")),   # a comparação fica
                        key=lambda c: len(json.dumps(coisa[c], ensure_ascii=False)), default=None)
            if maior is None:
                break
            del coisa[maior]
            cortados.append(maior)
            coisa["cortado_por_tamanho"] = cortados
        return coisa
    if isinstance(coisa, list):
        return [_enxugar(item, teto) for item in coisa]
    return coisa


def para_a_ia(resultado):
    """O resultado de uma ferramenta como a IA o lê (o replay sem os dias, um por um; os marcos ficam)."""
    return _enxugar(_copia(resultado))


def ensaio_da_rotacao(ficha, safra=None):
    """Replanta a rotação de hoje e as alternativas no ano normal e no pior ano. Com `safra`, traz o replay dela."""
    resposta = _chamar_o_motor("responder", entrada_do_motor(ficha))
    anos = resposta.get("regra_dos_anos") if isinstance(resposta.get("regra_dos_anos"), dict) else {}
    local = resposta.get("local") if isinstance(resposta.get("local"), dict) else {}
    resultado = {"lugar": local.get("nome") or ficha.get("cidade_id"),
                 "pior_ano": anos.get("pior_ano"), "ano_normal": anos.get("ano_normal")}
    if isinstance(resposta.get("calendario"), dict):          # as datas de cada cultura, como o motor mandou: com a
        resultado["calendario"] = resposta["calendario"]      # data de plantio do produtor, o calendário inteiro anda
    resultado["rotacoes"] = conferir_comparacao(resposta.get("comparacao_das_rotacoes"))
    if safra is not None:
        qual = _qual_safra(safra, anos)
        replay = _chamar_o_motor("replay_da_safra", entrada_do_motor(ficha), qual)
        resultado["replay"] = dict(replay, safra=qual, cidade_id=ficha.get("cidade_id"),      # o que o motor mandou,
                                   dias=replay.get("dias") or [], marcos=replay.get("marcos") or [])   # inteiro
    return resultado


def _anos_do_lugar(ficha):
    try:
        return _chamar_o_motor("clima_do_lugar", ficha.get("cidade_id")).get("regra_dos_anos") or {}
    except ContaIndisponivel:
        return {}


def clima_do_lugar(ficha, hoje=False):
    """O que os satélites registraram no lugar. Com `hoje`, mais o "como está hoje" (se o motor tiver)."""
    resultado = _chamar_o_motor("clima_do_lugar", ficha.get("cidade_id"))
    if hoje:
        try:
            resultado["hoje"] = _chamar_o_motor("como_esta_hoje", entrada_do_motor(ficha))
        except ContaIndisponivel:
            resultado["hoje"] = {"disponivel": False, "aviso": AVISO_SEM_HOJE}
    return resultado


def verde_do_satelite(ficha, safra=None):
    """O que o satélite viu na terra do lugar. Com `safra`, mais o registro daquela safra (se o motor tiver)."""
    resultado = _chamar_o_motor("verde_do_satelite", ficha.get("cidade_id"))
    if safra is not None:
        qual = _qual_safra(safra, _anos_do_lugar(ficha))
        try:
            resultado["registro"] = dict(_chamar_o_motor("registro_da_safra", entrada_do_motor(ficha), qual),
                                         safra=qual)
        except ContaIndisponivel:
            resultado["registro"] = {"disponivel": False, "safra": qual, "aviso": AVISO_SEM_REGISTRO}
    return resultado


def _item_do_painel(item, com_numeros=True):
    """Um item do painel como a IA o lê: o nome, a situação, a frase e os números soltos (sem as explicações)."""
    enxuto = {"id": item.get("id"), "situacao": item.get("situacao_nome") or item.get("situacao"),
              "frase": item.get("frase")}
    for chave, valor in item.items() if com_numeros else ():
        if chave in enxuto or chave in FORA_DO_PAINEL or chave == "situacao_nome" or valor is None:
            continue
        if isinstance(valor, (bool, int, float)) or (isinstance(valor, str) and len(valor) <= TEXTO_CURTO):
            enxuto[chave] = valor
    return enxuto


def lavoura_hoje(ficha):
    """O painel da lavoura hoje, enxuto: o resumo e os 6 itens (a fase, a água, o calor, o verde do satélite, a
    terra coberta e o aviso de sede), cada um com a frase, a situação e os números. Sem a função no motor, um aviso."""
    entrada = {campo: valor for campo, valor in entrada_do_motor(ficha).items() if campo in CAMPOS_DA_LAVOURA}
    try:
        painel = _chamar_o_motor("lavoura_hoje", entrada)
    except ContaIndisponivel:
        return {"disponivel": False, "aviso": AVISO_SEM_LAVOURA}
    if not isinstance(painel, dict) or painel.get("disponivel") is False or not isinstance(painel.get("itens"), list):
        aviso = painel.get("aviso") if isinstance(painel, dict) and isinstance(painel.get("aviso"), str) else None
        return {"disponivel": False, "aviso": (aviso or AVISO_SEM_LAVOURA)[:300]}
    local = painel.get("local") if isinstance(painel.get("local"), dict) else {}
    itens = [item for item in painel["itens"] if isinstance(item, dict)]
    for com_numeros in (True, False):               # passou do teto: saem os números soltos (as frases já os dizem)
        enxuto = {"disponivel": True, "lugar": local.get("nome") or ficha.get("cidade_id"),
                  "data_do_dado": painel.get("ultimo_dia_com_dado"),
                  "situacao": painel.get("situacao_nome") or painel.get("situacao"), "frase": painel.get("frase"),
                  "itens": [_item_do_painel(item, com_numeros) for item in itens]}
        if len(json.dumps(enxuto, ensure_ascii=False)) <= TETO_DO_PAINEL:
            break
    return enxuto


def definicoes():
    """O que a IA lê de cada ferramenta: o nome, para que serve e o que ela pode pedir."""
    safra = {"type": "string", "description": 'Uma safra, como "2015-16". Também vale "pior_ano" (a pior safra da '
                                              'região) ou "ano_normal". Use só quando o produtor pedir para ver '
                                              'uma safra (o dia a dia dela, ou o registro dela).'}
    return [
        {"nome": "clima_do_lugar",
         "descricao": "O que os satélites da NASA registraram no lugar da ficha: de onde vêm a chuva e a "
                      "temperatura, de que dia a que dia, qual foi o pior ano, qual é o ano normal e o calor. Serve "
                      "também quando o lugar do produtor não está guardado: é o clima do lugar guardado mais próximo.",
         "parametros": {"type": "object", "additionalProperties": False, "properties": {}}},
        {"nome": "ensaio_da_rotacao",
         "descricao": "Replanta a rotação de hoje do produtor e as alternativas no ano normal e no pior ano da "
                      "região. Devolve a comparação: de cada rotação, a água que faltou, os dias de calor forte, os "
                      "dias sem planta viva, a evidência, o benefício, o risco e o que falta saber; e o calendário "
                      "usado na conta (quando cada cultura entra e sai da terra, já com a data de plantio que o "
                      "produtor informou). Com safra, "
                      "traz também o replay daquela safra: os marcos, com a data (o plantio, o dia em que a água "
                      "acabou, o calor forte, a colheita).",
         "parametros": {"type": "object", "additionalProperties": False, "properties": {"safra": safra}}},
        {"nome": "verde_do_satelite",
         "descricao": "O que o satélite viu na terra do lugar: os dias sem planta viva pelo calendário das "
                      "culturas e pelo satélite (o NDVI, um índice do verde das folhas). Com safra, traz também o "
                      "registro daquela safra: o que foi plantado, a falta de água, os dias de calor forte e os "
                      "dias sem planta viva.",
         "parametros": {"type": "object", "additionalProperties": False, "properties": {"safra": safra}}},
        {"nome": "lavoura_hoje",
         "descricao": "Como a lavoura do produtor está agora, durante a safra: o resumo e os seis indicadores do "
                      "painel (a fase da cultura, a água na terra, o calor, o verde do satélite, a terra coberta e o "
                      "aviso de sede), cada um com a frase, a situação (tranquilo, atenção ou alerta) e os números. "
                      "Use para \"como está a lavoura?\" e \"como está hoje?\".",
         "parametros": {"type": "object", "additionalProperties": False, "properties": {}}},
    ]


def chamar(nome, ficha, argumentos):
    """Roda a ferramenta que a IA pediu. Pedido torto devolve {"erro": ...}, que volta para a IA ler."""
    argumentos = argumentos if isinstance(argumentos, dict) else {}
    safra = argumentos.get("safra") or None
    if safra is not None and not isinstance(safra, str):
        return {"erro": 'A safra tem de ser um texto, como "2015-16".'}
    try:
        if nome == "clima_do_lugar":
            return clima_do_lugar(ficha, hoje=argumentos.get("hoje") is True)
        if nome == "ensaio_da_rotacao":
            return ensaio_da_rotacao(ficha, safra)
        if nome == "verde_do_satelite":
            return verde_do_satelite(ficha, safra)
        if nome == "lavoura_hoje":
            return lavoura_hoje(ficha)
    except FichaRecusada as erro:
        if safra is not None and "safra" in str(erro):      # a safra pedida não serve: a IA lê e pede outra
            return {"erro": str(erro)}
        raise
    return {"erro": f"A ferramenta {nome} não existe. As que existem: {', '.join(NOMES)}."}
