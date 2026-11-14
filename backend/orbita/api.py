# Gerado com IA (Claude)
"""A API: a porta para outro programa perguntar ao motor, só com a biblioteca padrão (`http.server`).

De dentro de backend/:
    python3 -m orbita.api                      (liga em http://127.0.0.1:8000)
    python3 -m orbita.api --porta 8123         (outra porta; 0 = uma porta livre)
    python3 -m orbita.api --endereco 0.0.0.0   (abre para a rede: não há senha; só atrás de uma proteção)

As rotas (o `API.md` desta pasta traz um exemplo de cada uma):
    GET  /saude          -> {"ok": true, ...}
    POST /recomendacao   -> a resposta inteira do motor          (corpo: cidade_id, rotacao_atual, prioridades, terra)
    POST /mensagem       -> {"texto": o texto curto}             (o mesmo corpo)
    POST /conversa       -> {"estado": ..., "resposta": ...}     (corpo: {"estado": ..., "texto": ...})

Os cuidados: o corpo tem limite de tamanho e só entra JSON; os erros saem em português, com o código certo (400 para
entrada errada, 404, 405, 408, 411, 413, 415); nada que vem de fora escolhe arquivo (a fonte da chuva e a regra dos anos,
que o comando `perguntar` deixa trocar, não entram por aqui); nada é guardado, nem o corpo dos pedidos no registro.
Nenhum WhatsApp está ligado: a rota /conversa só devolve texto para quem chamou.
"""
import argparse
import json
import signal
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from orbita import conversa, mensagem, motor

LIMITE_DO_CORPO = 16 * 1024               # bytes: a pergunta e o estado da conversa cabem com muita folga
DESCARTE_MAXIMO = 1024 * 1024             # até quanto de um corpo recusado é lido e jogado fora antes de responder
ESPERA = 15                               # segundos sem chegar nada: a ligação é fechada
PRAZO_DO_CORPO = 10                       # segundos para o corpo inteiro chegar (mandar aos poucos não adianta)
ROTAS = {"/saude": "GET", "/recomendacao": "POST", "/mensagem": "POST", "/conversa": "POST"}
CAMPOS_DA_PERGUNTA = ("cidade_id", "rotacao_atual", "prioridades", "terra")
CAMPOS_DA_CONVERSA = ("estado", "texto")
EXEMPLO = ('{"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "prioridades": {"agua": 5, '
           '"solo": 4, "renda": 2, "erosao": 3}, "terra": "media"}')
ERROS_DO_SERVIDOR = {
    400: "O pedido não está no formato do HTTP.",
    408: "O pedido demorou demais para chegar.",
    414: "O endereço do pedido é grande demais.",
    431: "Os cabeçalhos do pedido são grandes demais.",
    501: "Método não aceito. Use GET em /saude e POST em /recomendacao, /mensagem e /conversa.",
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
    """Monta a entrada só com os 4 campos da pergunta e chama a função pública do motor."""
    _so_estes_campos(corpo, CAMPOS_DA_PERGUNTA)
    for campo in ("cidade_id", "terra"):
        if corpo.get(campo) is not None and not isinstance(corpo[campo], str):
            raise ErroDaApi(400, f'Entrada fora do formato: {campo} tem de ser um texto entre aspas, como '
                                 f'"{"rio_verde" if campo == "cidade_id" else "media"}".')
    try:
        return motor.responder({campo: corpo[campo] for campo in CAMPOS_DA_PERGUNTA if campo in corpo})
    except ValueError as erro:
        if str(erro).startswith("Entrada fora do formato"):       # o erro de entrada do motor, já em português
            raise ErroDaApi(400, str(erro)) from None
        raise                                                      # qualquer outro erro é de dentro: vira 500


def rota_saude():
    return {"ok": True, "servico": "Órbita Rural · a API do motor (provisória)",
            "aviso": "Vale só para Rio Verde (GO). Não é recomendação agronômica: valide com o agrônomo.",
            "rotas": [f"{metodo} {caminho}" for caminho, metodo in ROTAS.items()],
            "limite_do_corpo_bytes": LIMITE_DO_CORPO}


def rota_recomendacao(corpo):
    """A resposta inteira do motor."""
    return _perguntar_ao_motor(corpo)


def rota_mensagem(corpo):
    """O texto curto, pronto para mensagem."""
    return {"texto": mensagem.texto(_perguntar_ao_motor(corpo))}


def rota_conversa(corpo):
    """Um passo da conversa: quem chama guarda o estado e devolve na fala seguinte."""
    _so_estes_campos(corpo, CAMPOS_DA_CONVERSA)
    if not isinstance(corpo.get("texto"), str):
        raise ErroDaApi(400, 'Entrada fora do formato: falta o texto (a frase que a pessoa escreveu). Exemplo: '
                             '{"estado": null, "texto": "oi"}')
    estado = corpo.get("estado")
    if estado is not None and not isinstance(estado, dict):
        raise ErroDaApi(400, "Entrada fora do formato: o estado tem de ser o que a chamada anterior devolveu, ou "
                             'null no começo. Exemplo: {"estado": null, "texto": "oi"}')
    estado, resposta = conversa.passo(estado, corpo["texto"])
    return {"estado": estado, "resposta": resposta}


ACOES = {"/recomendacao": rota_recomendacao, "/mensagem": rota_mensagem, "/conversa": rota_conversa}


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
                    raise ErroDaApi(404, "Essa rota não existe. As rotas: GET /saude, POST /recomendacao, "
                                         "POST /mensagem e POST /conversa.")
                if self.command == "OPTIONS":                          # o navegador pede licença antes do POST
                    return self._enviar(204, None, (("Access-Control-Allow-Methods", f"{ROTAS[caminho]}, OPTIONS"),
                                                    ("Access-Control-Allow-Headers", "Content-Type"),
                                                    ("Access-Control-Max-Age", "600")))
                if self.command != ROTAS[caminho]:
                    raise ErroDaApi(405, f"A rota {caminho} só aceita {ROTAS[caminho]}.",
                                    (("Allow", f"{ROTAS[caminho]}, OPTIONS"),))
                resposta = rota_saude() if caminho == "/saude" else ACOES[caminho](self._ler_corpo())
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

    def __init__(self, onde, origem="*", silencioso=False):
        self.origem, self.silencioso, self.prazo_do_corpo = origem, silencioso, PRAZO_DO_CORPO
        super().__init__(onde, Porta)


def criar_servidor(endereco="127.0.0.1", porta=8000, origem="*", silencioso=False):
    """O servidor pronto para `serve_forever()`. Porta 0 = uma porta livre (está em `server_address`)."""
    return Servidor((endereco, porta), origem=origem, silencioso=silencioso)


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
    print("Rotas: GET /saude · POST /recomendacao · POST /mensagem · POST /conversa. Nenhum WhatsApp está ligado.",
          flush=True)
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
