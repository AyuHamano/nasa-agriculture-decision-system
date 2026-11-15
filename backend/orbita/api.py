# Gerado com IA (Claude)
"""A API: a porta para outro programa perguntar ao motor, só com a biblioteca padrão (`http.server`).

De dentro de backend/:
    python3 -m orbita.api                      (liga em http://127.0.0.1:8000)
    python3 -m orbita.api --porta 8123         (outra porta; 0 = uma porta livre)
    python3 -m orbita.api --endereco 0.0.0.0   (abre para a rede: não há senha; só atrás de uma proteção)

As rotas (o `API.md` desta pasta traz um exemplo de cada uma):
    GET  /saude          -> {"ok": true, ...}
    POST /recomendacao   -> a resposta inteira do motor          (corpo: cidade_id, rotacao_atual, terra)
    POST /mensagem       -> {"texto": o texto curto}             (o mesmo corpo)
    POST /conversa       -> {"estado": ..., "resposta": ...}     (corpo: {"estado": ..., "texto": ...})
    POST /agente         -> {"estado": ..., "resposta": ..., "comparacao": [...], ...}   (o mesmo corpo do /conversa)
    POST /lavoura-hoje   -> a lavoura hoje, em seis itens        (corpo: cidade_id, rotacao_atual, terra, plantio_da_soja)
    POST /replay         -> a safra dia a dia e os marcos        (corpo: cidade_id, safra; e rotacao_atual, terra, plantio)
    POST /registro       -> o registro da safra, depois da colheita   (o mesmo corpo do /replay)

A tela usa quatro rotas direto, sem IA: /recomendacao, /lavoura-hoje, /replay e /registro. A IA fica só para a
pergunta livre (/agente). As notas de 1 a 5 saíram (decisão do dono, 2026-11-15): quem ainda manda `prioridades` no
/recomendacao e no /mensagem não quebra, mas a API não repassa o campo ao motor, e a resposta não traz nota.

A rota /agente é a conversa com a IA (`agente.py`; o manual é o `LEIA-ME-agente.md`). Ela precisa da chave da IA
numa variável de ambiente (`OPENROUTER_API_KEY`); sem a chave, ou se a IA não responder, a rota devolve 503 e quem
chama usa as conversas guardadas. As outras rotas não usam IA nem chave.

Os cuidados: o corpo tem limite de tamanho e só entra JSON; os erros saem em português, com o código certo (400 para
entrada errada, 404, 405, 408, 411, 413, 415); nada que vem de fora escolhe arquivo (a fonte da chuva e a regra dos anos,
que o comando `perguntar` deixa trocar, não entram por aqui); nada é guardado, nem o corpo dos pedidos no registro.
Nenhum WhatsApp está ligado: as rotas /conversa e /agente só devolvem texto para quem chamou.
"""
import argparse
import json
import signal
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from orbita import agente, conversa, ferramentas, mensagem, motor
from orbita.modelo import ErroDoModelo, SemChave, do_ambiente

LIMITE_DO_CORPO = 16 * 1024               # bytes: a pergunta e o estado da conversa cabem com muita folga
DESCARTE_MAXIMO = 1024 * 1024             # até quanto de um corpo recusado é lido e jogado fora antes de responder
ESPERA = 15                               # segundos sem chegar nada: a ligação é fechada
PRAZO_DO_CORPO = 10                       # segundos para o corpo inteiro chegar (mandar aos poucos não adianta)
ROTAS = {"/saude": "GET", "/recomendacao": "POST", "/mensagem": "POST", "/conversa": "POST", "/agente": "POST",
         "/lavoura-hoje": "POST", "/replay": "POST", "/registro": "POST"}
CAMPOS_DA_LAVOURA = ("cidade_id", "rotacao_atual", "terra", "plantio_da_soja")      # os campos da /lavoura-hoje
CAMPOS_DA_PERGUNTA = ("cidade_id", "rotacao_atual", "prioridades", "terra", "plantio_da_soja", "preocupacao")
CAMPOS_QUE_NAO_VAO_AO_MOTOR = ("prioridades",)       # as notas de 1 a 5 saíram (2026-11-15): aceitas e deixadas de lado
CAMPOS_DA_SAFRA = ("cidade_id", "safra", "rotacao_atual", "terra", "plantio", "plantio_da_soja")   # /replay e /registro
ANOS_POR_NOME = ("pior_ano", "ano_normal")           # a safra pelo nome: resolve-se pela regra dos anos do lugar
TEXTOS_DA_SAFRA = {"cidade_id": "rio_verde", "safra": "2015-16", "terra": "media", "plantio": "2015-10-20",
                   "plantio_da_soja": "2015-10-20"}
EXEMPLO_DA_SAFRA = '{"cidade_id": "rio_verde", "safra": "2015-16"}'
TEXTOS_DA_PERGUNTA = {"cidade_id": "rio_verde", "terra": "media", "plantio_da_soja": "2026-11-05",
                      "preocupacao": "agua"}                     # os campos que são texto, com um exemplo de cada
CAMPOS_DA_CONVERSA = ("estado", "texto")
TODAS_AS_ROTAS = ("GET /saude, POST /recomendacao, POST /mensagem, POST /conversa, POST /agente, "
                  "POST /lavoura-hoje, POST /replay e POST /registro")
EXEMPLO_DA_CONVERSA = '{"estado": null, "texto": "oi"}'
EXEMPLO = '{"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media"}'
ERROS_DO_SERVIDOR = {
    400: "O pedido não está no formato do HTTP.",
    408: "O pedido demorou demais para chegar.",
    414: "O endereço do pedido é grande demais.",
    431: "Os cabeçalhos do pedido são grandes demais.",
    501: "Método não aceito. Use GET em /saude e POST em /recomendacao, /mensagem, /conversa, /agente, "
         "/lavoura-hoje, /replay e /registro.",
    505: "Versão do HTTP não aceita.",
}


class ErroDaApi(Exception):
    """Um erro que vira resposta: o código do HTTP, a mensagem em português e os cabeçalhos a mais."""

    def __init__(self, codigo, mensagem_do_erro, cabecalhos=()):
        super().__init__(mensagem_do_erro)
        self.codigo, self.mensagem, self.cabecalhos = codigo, mensagem_do_erro, tuple(cabecalhos)


def _recusar_constante(nome):
    raise ValueError(f"{nome} não é número de JSON")


def ler_json(corpo):
    """O corpo (bytes) vira um objeto. Só aceita JSON em UTF-8 e só um objeto ({...})."""
    try:
        dado = json.loads(corpo.decode("utf-8"), parse_constant=_recusar_constante)
    except (ValueError, RecursionError):      # texto que não é UTF-8, JSON torto, fundo demais ou número sem fim
        raise ErroDaApi(400, f"O corpo não é um JSON válido (em UTF-8). Exemplo: {EXEMPLO}") from None
    if not isinstance(dado, dict):
        raise ErroDaApi(400, f"O corpo tem de ser um objeto JSON, entre chaves. Exemplo: {EXEMPLO}")
    return dado


def _so_estes_campos(corpo, campos):
    if not isinstance(corpo, dict):
        raise ErroDaApi(400, f"O corpo tem de ser um objeto JSON, entre chaves. Exemplo: {EXEMPLO}")
    sobras = sorted(str(campo)[:40] for campo in corpo if campo not in campos)
    if sobras:
        raise ErroDaApi(400, f"Campo que a API não aceita: {', '.join(sobras)}. Ela aceita só: {', '.join(campos)}.")


def _perguntar_ao_motor(corpo):
    """Monta a entrada só com os campos da pergunta e chama a função pública do motor.

    As notas de 1 a 5 (`prioridades`) saíram por decisão do dono (2026-11-15): o campo ainda é aceito, para quem já
    manda não quebrar, mas não vai ao motor, venha o que vier nele.
    """
    _so_estes_campos(corpo, CAMPOS_DA_PERGUNTA)
    for campo, exemplo in TEXTOS_DA_PERGUNTA.items():
        if corpo.get(campo) is not None and not isinstance(corpo[campo], str):
            raise ErroDaApi(400, f'Entrada fora do formato: {campo} tem de ser um texto entre aspas, como '
                                 f'"{exemplo}".')
    try:
        return motor.responder({campo: corpo[campo] for campo in CAMPOS_DA_PERGUNTA
                                if campo in corpo and campo not in CAMPOS_QUE_NAO_VAO_AO_MOTOR})
    except ValueError as erro:
        if str(erro).startswith("Entrada fora do formato"):       # o erro de entrada do motor, já em português
            raise ErroDaApi(400, str(erro)) from None
        raise                                                      # qualquer outro erro é de dentro: vira 500


def _onde_vale():
    """As cidades que o motor tem, numa frase."""
    nomes = [str(dados.get("nome") or ident) if isinstance(dados, dict) else str(ident)
             for ident, dados in motor.CIDADES.items()]
    if len(nomes) == 1:
        return f"Vale só para {nomes[0]}."
    return "Vale para " + ", ".join(nomes[:-1]) + " e " + nomes[-1] + "."


def _ia_do_agente(modelo=None):
    """Se a IA do agente está ligada (há chave no ambiente) e com que modelo. A chave nunca aparece."""
    try:
        modelo = modelo or do_ambiente()
    except SemChave:
        return {"ligada": False, "modelo": None}
    return {"ligada": True, "modelo": getattr(modelo, "nome", None)}


def rota_saude(modelo=None):
    return {"ok": True, "servico": "Órbita Rural · a API do motor (provisória)",
            "aviso": _onde_vale() + " Não é recomendação agronômica: valide com o agrônomo.",
            "rotas": [f"{metodo} {caminho}" for caminho, metodo in ROTAS.items()],
            "limite_do_corpo_bytes": LIMITE_DO_CORPO, "ia_do_agente": _ia_do_agente(modelo)}


def rota_recomendacao(corpo):
    """A resposta inteira do motor."""
    return _perguntar_ao_motor(corpo)


def rota_mensagem(corpo):
    """O texto curto, pronto para mensagem."""
    return {"texto": mensagem.texto(_perguntar_ao_motor(corpo))}


def _estado_e_texto(corpo):
    """O corpo de um passo de conversa, conferido: (o estado, o texto)."""
    _so_estes_campos(corpo, CAMPOS_DA_CONVERSA)
    if not isinstance(corpo.get("texto"), str):
        raise ErroDaApi(400, "Entrada fora do formato: falta o texto (a frase que a pessoa escreveu). Exemplo: "
                             + EXEMPLO_DA_CONVERSA)
    estado = corpo.get("estado")
    if estado is not None and not isinstance(estado, dict):
        raise ErroDaApi(400, "Entrada fora do formato: o estado tem de ser o que a chamada anterior devolveu, ou "
                             "null no começo. Exemplo: " + EXEMPLO_DA_CONVERSA)
    return estado, corpo["texto"]


def rota_conversa(corpo):
    """Um passo da conversa: quem chama guarda o estado e devolve na fala seguinte."""
    estado, texto = _estado_e_texto(corpo)
    estado, resposta = conversa.passo(estado, texto)
    return {"estado": estado, "resposta": resposta}


def rota_agente(corpo, modelo=None):
    """Um passo da conversa com a IA (`agente.passo`): quem chama guarda o estado e devolve na fala seguinte.

    `modelo` é a IA; sem ele, vale o modelo de verdade, com a chave lida do ambiente na hora. Sem chave, IA que não
    responde ou conta que o motor não tem: 503 (quem chama mantém o estado e usa as conversas guardadas).
    """
    estado, texto = _estado_e_texto(corpo)
    try:
        estado, saida = agente.passo(estado, texto, modelo or do_ambiente())
    except SemChave:
        raise ErroDaApi(503, "A IA do agente não está ligada neste servidor: falta a chave no ambiente "
                             "(OPENROUTER_API_KEY). Use as conversas guardadas.") from None
    except ErroDoModelo as erro:
        raise ErroDaApi(503, f"{erro} Nada foi guardado: mantenha o estado e tente de novo, ou use as conversas "
                             "guardadas.") from None
    except ferramentas.ContaIndisponivel as erro:
        raise ErroDaApi(503, f"A conta não está pronta para o agente. {erro}") from None
    return agente.resposta_da_rota(estado, saida)


def rota_lavoura_hoje(corpo):
    """A lavoura hoje (`motor.lavoura_hoje`): a fase, a água, o calor, o verde, a terra coberta e o aviso de sede."""
    _so_estes_campos(corpo, CAMPOS_DA_LAVOURA)
    for campo in CAMPOS_DA_LAVOURA:
        if campo in TEXTOS_DA_PERGUNTA and corpo.get(campo) is not None and not isinstance(corpo[campo], str):
            raise ErroDaApi(400, f'Entrada fora do formato: {campo} tem de ser um texto entre aspas, como '
                                 f'"{TEXTOS_DA_PERGUNTA[campo]}".')
    try:
        return motor.lavoura_hoje({campo: corpo[campo] for campo in CAMPOS_DA_LAVOURA if campo in corpo})
    except ValueError as erro:
        if str(erro).startswith("Entrada fora do formato"):       # o erro de entrada do motor, já em português
            raise ErroDaApi(400, str(erro)) from None
        raise


def _conta_da_safra(nome_da_conta, corpo):
    """O corpo do /replay e do /registro vira (a entrada do motor, a safra), e a conta do motor responde.

    `cidade_id` e `safra` são obrigatórios. Sem `rotacao_atual`, vale soja -> milho -> pousio (o motor exige a
    rotação); sem `terra`, vale "media" (o padrão do motor). `plantio` é a data do plantio da soja e vai ao motor como
    `plantio_da_soja` (o nome que a /lavoura-hoje usa, aceito aqui como sinônimo). A safra é como "2015-16", ou
    "pior_ano" / "ano_normal", que se resolvem pela regra dos anos do lugar (`motor.clima_do_lugar`).
    """
    _so_estes_campos(corpo, CAMPOS_DA_SAFRA)
    for campo, exemplo in TEXTOS_DA_SAFRA.items():
        if corpo.get(campo) is not None and not isinstance(corpo[campo], str):
            raise ErroDaApi(400, f'Entrada fora do formato: {campo} tem de ser um texto entre aspas, como '
                                 f'"{exemplo}".')
    safra = corpo.get("safra")
    if not safra:
        raise ErroDaApi(400, 'Entrada fora do formato: falta a safra (como "2015-16", ou "pior_ano", ou '
                             f'"ano_normal"). Exemplo: {EXEMPLO_DA_SAFRA}')
    plantio, sinonimo = corpo.get("plantio"), corpo.get("plantio_da_soja")
    if plantio and sinonimo and plantio != sinonimo:
        raise ErroDaApi(400, "Entrada fora do formato: plantio e plantio_da_soja são o mesmo campo (a data do "
                             "plantio da soja); mande um só.")
    rotacao = corpo.get("rotacao_atual")
    entrada = {"cidade_id": corpo.get("cidade_id"),
               "rotacao_atual": list(motor.ROTACAO_DE_HOJE) if rotacao is None else rotacao}
    if corpo.get("terra") is not None:
        entrada["terra"] = corpo["terra"]
    if plantio or sinonimo:
        entrada["plantio_da_soja"] = plantio or sinonimo
    try:
        if safra in ANOS_POR_NOME:
            safra = motor.clima_do_lugar(entrada["cidade_id"])["regra_dos_anos"][safra]
        return getattr(motor, nome_da_conta)(entrada, safra)
    except ValueError as erro:
        if str(erro).startswith("Entrada fora do formato"):       # o erro de entrada do motor, já em português
            raise ErroDaApi(400, str(erro)) from None
        raise


def rota_replay(corpo):
    """A safra dia a dia (`motor.replay_da_safra`): os dias e os marcos, para a tela passar como um filme. Sem IA."""
    return _conta_da_safra("replay_da_safra", corpo)


def rota_registro(corpo):
    """O registro da safra, depois da colheita (`motor.registro_da_safra`). Sem IA."""
    return _conta_da_safra("registro_da_safra", corpo)


ACOES = {"/recomendacao": rota_recomendacao, "/mensagem": rota_mensagem, "/conversa": rota_conversa,
         "/agente": rota_agente, "/lavoura-hoje": rota_lavoura_hoje, "/replay": rota_replay,
         "/registro": rota_registro}


class Porta(BaseHTTPRequestHandler):
    """Atende um pedido. Não guarda nada entre um pedido e outro."""

    server_version, sys_version = "OrbitaRural", ""        # não conta a versão do Python a quem pergunta
    timeout = ESPERA
    wbufsize = 64 * 1024                                   # os cabeçalhos e o corpo saem juntos, de uma vez

    def version_string(self):
        return self.server_version

    def _enviar(self, codigo, objeto=None, cabecalhos=()):
        corpo = b"" if objeto is None else json.dumps(objeto, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Access-Control-Allow-Origin", self.server.origem)        # o site pode ler a resposta
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        if objeto is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        for nome, valor in cabecalhos:
            self.send_header(nome, valor)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(corpo)
        self.wfile.flush()

    def _tamanho_do_corpo(self):
        """O Content-Length do pedido; None se não veio ou não é um número."""
        try:
            tamanho = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return None
        return tamanho if tamanho >= 0 else None

    def _ler_do_fio(self, tamanho, guardar=True):
        """Lê `tamanho` bytes do corpo, com um prazo para o corpo inteiro: quem manda aos poucos não segura a ligação."""
        fim, pedacos, falta = time.monotonic() + self.server.prazo_do_corpo, [], tamanho
        try:
            while falta > 0:
                resta = fim - time.monotonic()
                if resta <= 0:
                    raise TimeoutError
                self.connection.settimeout(resta)
                pedaco = self.rfile.read1(min(falta, 65536))
                if not pedaco:
                    break
                falta -= len(pedaco)
                if guardar:
                    pedacos.append(pedaco)
        except TimeoutError:
            raise ErroDaApi(408, "O corpo do pedido demorou demais para chegar.") from None
        finally:
            self.connection.settimeout(ESPERA)
        return b"".join(pedacos)

    def _descartar_corpo(self):
        """Lê e joga fora o corpo de um pedido recusado (até um teto), para a resposta chegar inteira a quem pediu."""
        self._corpo_lido = True
        try:
            self._ler_do_fio(min(self._tamanho_do_corpo() or 0, DESCARTE_MAXIMO), guardar=False)
        except ErroDaApi:                  # o corpo recusado demorou: o erro que vale é o do pedido, e ele sai já
            pass

    def _ler_corpo(self):
        tipo = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if tipo != "application/json":
            raise ErroDaApi(415, "Só JSON: mande o cabeçalho Content-Type: application/json e o corpo em JSON.")
        tamanho = self._tamanho_do_corpo()
        if tamanho is None or self.headers.get("Transfer-Encoding"):
            raise ErroDaApi(411, "Falta o tamanho do corpo (o cabeçalho Content-Length, com um número).")
        if tamanho > LIMITE_DO_CORPO:
            raise ErroDaApi(413, f"Corpo grande demais: o limite é de {LIMITE_DO_CORPO} bytes.")
        self._corpo_lido = True
        corpo = self._ler_do_fio(tamanho)
        if len(corpo) != tamanho:
            raise ErroDaApi(400, "O corpo chegou incompleto.")
        return ler_json(corpo)

    def _atender(self):
        self._corpo_lido = False
        self.close_connection = True                                   # um pedido por ligação
        try:
            try:
                caminho = self.path.split("?", 1)[0].split("#", 1)[0]
                if caminho not in ROTAS:
                    raise ErroDaApi(404, f"Essa rota não existe. As rotas: {TODAS_AS_ROTAS}.")
                if self.command == "OPTIONS":                          # o navegador pede licença antes do POST
                    return self._enviar(204, None, (("Access-Control-Allow-Methods", f"{ROTAS[caminho]}, OPTIONS"),
                                                    ("Access-Control-Allow-Headers", "Content-Type"),
                                                    ("Access-Control-Max-Age", "600")))
                if self.command != ROTAS[caminho]:
                    raise ErroDaApi(405, f"A rota {caminho} só aceita {ROTAS[caminho]}.",
                                    (("Allow", f"{ROTAS[caminho]}, OPTIONS"),))
                if caminho == "/saude":
                    resposta = rota_saude(self.server.modelo)
                elif caminho == "/agente":
                    resposta = rota_agente(self._ler_corpo(), self.server.modelo)
                else:
                    resposta = ACOES[caminho](self._ler_corpo())
                self._enviar(200, resposta)
            except ErroDaApi as erro:
                if not self._corpo_lido:
                    self._descartar_corpo()
                self._enviar(erro.codigo, {"erro": erro.mensagem}, erro.cabecalhos)
        except OSError:                                                # quem pediu sumiu ou demorou demais
            pass
        except Exception:                                              # um defeito de dentro: fala como gente
            if not self.server.silencioso:
                traceback.print_exc(file=sys.stderr)
            try:
                self._enviar(500, {"erro": "A conta falhou do lado de dentro. Nada foi guardado; tente de novo "
                                           "daqui a pouco."})
            except OSError:
                pass

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _atender

    def send_error(self, code, message=None, explain=None):
        """Os erros que o próprio http.server dá (pedido torto, método que não existe) também saem em português."""
        self.close_connection = True
        try:
            self._enviar(int(code), {"erro": ERROS_DO_SERVIDOR.get(int(code), "O pedido não pôde ser atendido.")})
        except OSError:
            pass

    def log_request(self, code="-", size="-"):
        """O registro de cada pedido: só o método, a rota e o código. Nem o corpo, nem o endereço de quem pediu."""
        if not self.server.silencioso:
            caminho = (getattr(self, "path", "") or "").split("?", 1)[0][:60]
            codigo = getattr(code, "value", code)
            sys.stderr.write(f"{self.log_date_time_string()} {self.command or '?'} {caminho} {codigo}\n")

    def log_message(self, format, *args):                              # noqa: A002 (o nome vem do http.server)
        pass


class Servidor(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, onde, origem="*", silencioso=False, modelo=None):
        self.origem, self.silencioso, self.prazo_do_corpo = origem, silencioso, PRAZO_DO_CORPO
        self.modelo = modelo                  # a IA do /agente; None = o modelo de verdade, com a chave do ambiente
        super().__init__(onde, Porta)


def criar_servidor(endereco="127.0.0.1", porta=8000, origem="*", silencioso=False, modelo=None):
    """O servidor pronto para `serve_forever()`. Porta 0 = uma porta livre (está em `server_address`).

    `modelo` troca a IA do /agente (serve aos testes, que usam o modelo de mentira).
    """
    return Servidor((endereco, porta), origem=origem, silencioso=silencioso, modelo=modelo)


def ler_opcoes(argv=None):
    leitor = argparse.ArgumentParser(prog="python3 -m orbita.api", description="Liga a API do motor do Órbita Rural.")
    leitor.add_argument("--porta", type=int, default=8000, help="a porta (padrão 8000; 0 = uma porta livre)")
    leitor.add_argument("--endereco", default="127.0.0.1",
                        help="o endereço em que a API escuta (padrão 127.0.0.1: só esta máquina)")
    leitor.add_argument("--origem", default="*",
                        help="o site que pode ler as respostas pelo navegador (CORS; padrão *: qualquer um)")
    return leitor.parse_args(argv)


def _desligar(*_):
    raise KeyboardInterrupt


def main(argv=None):
    opcoes = ler_opcoes(argv)
    try:
        servidor = criar_servidor(opcoes.endereco, opcoes.porta, opcoes.origem)
    except (OSError, OverflowError) as erro:
        print(f"Não deu para ligar a API em {opcoes.endereco}:{opcoes.porta} ({erro}). A porta pode estar em uso: "
              "tente outra com --porta.", file=sys.stderr)
        return 1
    endereco, porta = servidor.server_address[:2]
    print(f"Órbita Rural · a API está ligada em http://{endereco}:{porta} (Ctrl+C desliga).", flush=True)
    print("Rotas: GET /saude · POST /recomendacao · POST /mensagem · POST /conversa · POST /agente · "
          "POST /lavoura-hoje · POST /replay · POST /registro. Nenhum WhatsApp está ligado.", flush=True)
    ia = _ia_do_agente()
    print(f"A IA do agente: ligada (modelo {ia['modelo']})." if ia["ligada"] else
          "A IA do agente: sem chave no ambiente (OPENROUTER_API_KEY); a rota /agente responde 503, e as outras "
          "rotas respondem sem IA.", flush=True)
    if endereco not in ("127.0.0.1", "::1", "localhost"):
        print("Atenção: fora do 127.0.0.1 a API fica aberta para a rede, e não há senha nem limite de pedidos.",
              file=sys.stderr, flush=True)
    try:
        signal.signal(signal.SIGTERM, _desligar)        # o `kill` desliga com o mesmo cuidado do Ctrl+C
    except ValueError:                                  # fora do fio principal não dá para pôr o sinal
        pass
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    print("API desligada.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
