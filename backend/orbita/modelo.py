# Gerado com IA (Claude)
"""O encaixe da IA: o modelo de mentira (para os testes) e o modelo de verdade (OpenRouter), no mesmo formato.

O agente só conhece uma chamada:

    resposta = modelo.responder(mensagens, ferramentas)
    # resposta = {"texto": "...", "chamadas": [{"id": "...", "nome": "...", "argumentos": {...}}], "uso": {...},
    #             "cortado": True se o texto parou no meio por falta de espaço}

`mensagens` é a conversa, em ordem. Cada uma tem `de` (quem fala) e o resto:
    {"de": "sistema", "texto": ...}       as regras do agente
    {"de": "produtor", "texto": ...}      a fala do produtor
    {"de": "programa", "texto": ...}      um aviso do programa à IA (o produtor não vê)
    {"de": "agente", "texto": ..., "chamadas": [...]}                      o que a IA disse ou pediu antes
    {"de": "ferramenta", "id": ..., "nome": ..., "resultado": {...}}      o que a ferramenta devolveu
`ferramentas` é a lista do que a IA pode pedir: {"nome", "descricao", "parametros" (um JSON Schema)}.

- `ModeloDeMentira(respostas)`: devolve respostas fixas, na ordem. Não usa chave nem internet. Quando a lista
  acaba, devolve texto vazio (e o agente responde com as frases prontas).
- `ModeloOpenRouter(chave, modelo)`: fala com o OpenRouter (https://openrouter.ai), só com a biblioteca padrão.
- `do_ambiente()`: o modelo de verdade, com a chave lida da variável de ambiente `OPENROUTER_API_KEY` e o nome do
  modelo de `ORBITA_MODELO`, só na hora de rodar. A chave nunca é escrita em arquivo, em registro nem em erro.

Uso de IA declarado: o texto do agente é escrito por um modelo de linguagem (por padrão, Claude Haiku, da Anthropic,
pelo OpenRouter); os números do texto são conferidos contra a conta antes de aparecer (`conferencia.py`).
"""
import copy
import json
import os
import time
import urllib.error
import urllib.request

VARIAVEL_DA_CHAVE = "OPENROUTER_API_KEY"
VARIAVEL_DO_MODELO = "ORBITA_MODELO"
MODELO_PADRAO = "anthropic/claude-haiku-5.5"
MODELO_RESERVA = "deepseek/deepseek-v4.1-flash"
ENDERECO = "https://openrouter.ai/api/v1/chat/completions"
ESPERA = 45                     # segundos por pedido
TENTATIVAS = 2                  # um pedido que falha por demora ou por erro do outro lado é repetido uma vez
PAUSA = 1.5                     # segundos entre as tentativas
TEMPERATURA = 0.2               # baixa: a IA explica a conta, não inventa
TAMANHO_DA_RESPOSTA = 4000      # o máximo de fichas (tokens) por pedido: o raciocínio da IA também gasta daqui
RACIOCINIO = {"effort": "low"}  # quanto a IA pensa antes de escrever: pouco (medido: sem teto, ela gasta o espaço
                                # todo pensando e o texto sai cortado no meio)
REPETE = (408, 409, 425, 429, 500, 502, 503, 504, 520, 522, 524, 529)


class ErroDoModelo(Exception):
    """A IA não respondeu (rede, limite, chave recusada, resposta torta). A frase não traz a chave."""


class SemChave(ErroDoModelo):
    """Não há chave de IA no ambiente: o agente não pode chamar o modelo de verdade."""


def chamada(nome, identificador=None, **argumentos):
    """Uma chamada de ferramenta, para montar as respostas do modelo de mentira."""
    return {"id": identificador or f"chamada_{nome}", "nome": nome, "argumentos": argumentos}


def fala(texto="", *chamadas, cortado=False):
    """Uma resposta do modelo de mentira: um texto, ou pedidos de ferramenta."""
    return {"texto": texto, "chamadas": list(chamadas), "uso": {}, "cortado": cortado}


class ModeloDeMentira:
    """Faz o papel da IA nos testes: respostas fixas, na ordem. Guarda o que recebeu, para o teste olhar."""

    nome = "modelo-de-mentira"

    def __init__(self, respostas=()):
        self.respostas = list(respostas)
        self.pedidos = []                     # [(as mensagens, as ferramentas)] de cada chamada

    def responder(self, mensagens, ferramentas):
        self.pedidos.append((copy.deepcopy(mensagens), copy.deepcopy(ferramentas)))
        if not self.respostas:
            return fala("")
        resposta = self.respostas.pop(0)
        if callable(resposta):
            resposta = resposta(mensagens, ferramentas)
        if isinstance(resposta, Exception):
            raise resposta
        return {"texto": resposta.get("texto") or "", "chamadas": copy.deepcopy(resposta.get("chamadas") or []),
                "uso": dict(resposta.get("uso") or {}), "cortado": resposta.get("cortado") is True}


def _para_o_fio(mensagens):
    """As mensagens no formato do OpenRouter (o mesmo da OpenAI)."""
    saida = []
    for m in mensagens:
        de = m.get("de")
        if de == "sistema":
            saida.append({"role": "system", "content": m["texto"]})
        elif de == "produtor":
            saida.append({"role": "user", "content": m["texto"]})
        elif de == "programa":
            saida.append({"role": "user", "content": "[Aviso do programa; o produtor não vê] " + m["texto"]})
        elif de == "agente":
            item = {"role": "assistant", "content": m.get("texto") or None}
            if m.get("chamadas"):
                item["tool_calls"] = [{"id": c["id"], "type": "function", "function": {
                    "name": c["nome"], "arguments": json.dumps(c.get("argumentos") or {}, ensure_ascii=False)}}
                    for c in m["chamadas"]]
            elif item["content"] is None:
                item["content"] = ""
            saida.append(item)
        elif de == "ferramenta":
            saida.append({"role": "tool", "tool_call_id": m["id"],
                          "content": json.dumps(m.get("resultado"), ensure_ascii=False)})
        else:
            raise ValueError(f"Mensagem de quem? {de!r} não é sistema, produtor, programa, agente nem ferramenta.")
    return saida


def _ferramentas_no_fio(ferramentas):
    return [{"type": "function", "function": {"name": f["nome"], "description": f["descricao"],
                                              "parameters": f["parametros"]}} for f in ferramentas]


def _texto_do_conteudo(conteudo):
    """O texto da resposta: o OpenRouter manda um texto, ou uma lista de pedaços com texto."""
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, list):
        return "".join(p.get("text", "") for p in conteudo if isinstance(p, dict) and p.get("type") == "text")
    return ""


def _ler_resposta(dado):
    """A resposta do OpenRouter no formato do encaixe. Resposta torta: `ErroDoModelo`."""
    try:
        escolha = dado["choices"][0]
        mensagem = escolha["message"]
    except (KeyError, IndexError, TypeError):
        erro = dado.get("error") if isinstance(dado, dict) else None
        detalhe = str(erro.get("message"))[:200] if isinstance(erro, dict) else "resposta sem mensagem"
        raise ErroDoModelo(f"A IA devolveu uma resposta que não deu para ler ({detalhe}).") from None
    chamadas = []
    for numero, pedido in enumerate(mensagem.get("tool_calls") or []):
        funcao = pedido.get("function") or {}
        try:
            argumentos = json.loads(funcao.get("arguments") or "{}")
        except ValueError:
            argumentos = None
        chamadas.append({"id": pedido.get("id") or f"chamada_{numero}", "nome": str(funcao.get("name") or ""),
                         "argumentos": argumentos if isinstance(argumentos, dict) else {}})
    uso = dado.get("usage") if isinstance(dado.get("usage"), dict) else {}
    return {"texto": _texto_do_conteudo(mensagem.get("content")).strip(), "chamadas": chamadas,
            "uso": {"entrada": uso.get("prompt_tokens") or 0, "saida": uso.get("completion_tokens") or 0,
                    "custo_usd": uso.get("cost") or 0.0},
            "cortado": escolha.get("finish_reason") == "length"}       # parou por falta de espaço, no meio do texto


def _enviar(endereco, corpo, cabecalhos, espera):
    """Um POST com JSON, pela biblioteca padrão. Devolve o objeto da resposta."""
    pedido = urllib.request.Request(endereco, data=json.dumps(corpo).encode("utf-8"), headers=cabecalhos,
                                    method="POST")
    with urllib.request.urlopen(pedido, timeout=espera) as resposta:      # noqa: S310 (o endereço é fixo, https)
        return json.loads(resposta.read().decode("utf-8"))


class ModeloOpenRouter:
    """O modelo de verdade, pelo OpenRouter. Soma o que gastou em `uso` (pedidos, fichas e dólares)."""

    def __init__(self, chave, modelo=MODELO_PADRAO, endereco=ENDERECO, espera=ESPERA, enviar=None, pausa=PAUSA):
        if not isinstance(chave, str) or not chave.strip():
            raise SemChave(f"Falta a chave da IA: a variável de ambiente {VARIAVEL_DA_CHAVE} está vazia.")
        self._chave = chave.strip()
        self.nome, self.endereco, self.espera, self.pausa = modelo or MODELO_PADRAO, endereco, espera, pausa
        self._enviar = enviar or _enviar
        self.uso = {"pedidos": 0, "entrada": 0, "saida": 0, "custo_usd": 0.0}

    def __repr__(self):                                   # a chave não aparece nem por engano
        return f"ModeloOpenRouter(modelo={self.nome!r})"

    def responder(self, mensagens, ferramentas):
        corpo = {"model": self.nome, "messages": _para_o_fio(mensagens), "temperature": TEMPERATURA,
                 "max_tokens": TAMANHO_DA_RESPOSTA, "reasoning": dict(RACIOCINIO)}
        if ferramentas:
            corpo["tools"] = _ferramentas_no_fio(ferramentas)
        resposta = self._pedir(corpo)
        if resposta["cortado"]:                           # faltou espaço: pede de novo, uma vez, com o dobro
            resposta = self._pedir(dict(corpo, max_tokens=2 * TAMANHO_DA_RESPOSTA))
        return resposta

    def _pedir(self, corpo):
        cabecalhos = {"Authorization": "Bearer " + self._chave, "Content-Type": "application/json",
                      "X-Title": "Orbita Rural"}
        for tentativa in range(1, TENTATIVAS + 1):
            try:
                dado = self._enviar(self.endereco, corpo, cabecalhos, self.espera)
                break
            except urllib.error.HTTPError as erro:
                if erro.code in REPETE and tentativa < TENTATIVAS:
                    time.sleep(self.pausa)
                    continue
                motivo = {401: "a chave foi recusada", 402: "a chave está sem saldo ou venceu",
                          403: "a chave não tem licença para esse modelo", 404: "esse modelo não existe",
                          429: "passou do limite de pedidos"}.get(erro.code, "o serviço da IA deu erro")
                raise ErroDoModelo(f"A IA não respondeu: {motivo} (código {erro.code}).") from None
            except (OSError, ValueError):                 # sem rede, demora, resposta que não é JSON
                if tentativa < TENTATIVAS:
                    time.sleep(self.pausa)
                    continue
                raise ErroDoModelo("A IA não respondeu: sem ligação com o serviço, ou ele demorou demais.") from None
        resposta = _ler_resposta(dado)
        self.uso["pedidos"] += 1
        for chave in ("entrada", "saida", "custo_usd"):
            self.uso[chave] += resposta["uso"].get(chave) or 0
        return resposta


def do_ambiente(ambiente=None):
    """O modelo de verdade, com a chave e o nome do modelo lidos do ambiente na hora. Sem chave: `SemChave`."""
    ambiente = os.environ if ambiente is None else ambiente
    chave = (ambiente.get(VARIAVEL_DA_CHAVE) or "").strip()
    if not chave:
        raise SemChave(f"Falta a chave da IA: a variável de ambiente {VARIAVEL_DA_CHAVE} está vazia.")
    return ModeloOpenRouter(chave, (ambiente.get(VARIAVEL_DO_MODELO) or "").strip() or MODELO_PADRAO)
