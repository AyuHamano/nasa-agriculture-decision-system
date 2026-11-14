# Gerado com IA (Claude)
"""Testes da API: as funções direto e uma ida e volta de verdade por HTTP, numa porta livre do 127.0.0.1."""
import http.client
import json
import socket
import threading
import unittest

from orbita import api, mensagem, motor

ENTRADA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"],
           "prioridades": {"agua": 5, "solo": 4, "renda": 2, "erosao": 3}, "terra": "media"}
RESPOSTA = json.loads(json.dumps(motor.responder(ENTRADA)))     # como ela chega depois de virar JSON
JSON = {"Content-Type": "application/json"}


def erro_de(funcao, *argumentos):
    with unittest.TestCase().assertRaises(api.ErroDaApi) as erro:
        funcao(*argumentos)
    return erro.exception


class AsFuncoes(unittest.TestCase):
    def test_recomendacao_e_a_resposta_inteira_do_motor(self):
        self.assertEqual(api.rota_recomendacao(dict(ENTRADA)), motor.responder(ENTRADA))

    def test_mensagem_e_o_texto_curto(self):
        self.assertEqual(api.rota_mensagem(dict(ENTRADA)), {"texto": mensagem.texto(motor.responder(ENTRADA))})

    def test_conversa_devolve_o_estado_e_a_resposta(self):
        saida = api.rota_conversa({"estado": None, "texto": "oi"})
        self.assertEqual(saida["estado"], {"etapa": "terra"})
        self.assertIn("só para Rio Verde", saida["resposta"])
        self.assertEqual(api.rota_conversa({"texto": "oi"}), saida)            # sem estado é o começo

    def test_entrada_errada_e_400_em_portugues(self):
        casos = ((api.rota_recomendacao, dict(ENTRADA, terra="barro"), "terra"),
                 (api.rota_recomendacao, {}, "cidade_id"),
                 (api.rota_recomendacao, dict(ENTRADA, cidade_id=["rio_verde"]), "cidade_id"),
                 (api.rota_recomendacao, dict(ENTRADA, terra=["media"]), "terra"),
                 (api.rota_mensagem, dict(ENTRADA, prioridades={"agua": 9}), "1 a 5"),
                 (api.rota_conversa, {"estado": None}, "texto"),
                 (api.rota_conversa, {"estado": None, "texto": 5}, "texto"),
                 (api.rota_conversa, {"estado": "solo", "texto": "4"}, "estado"),
                 (api.rota_conversa, {"estado": None, "texto": "oi", "telefone": "64999990000"}, "telefone"))
        for funcao, corpo, pedaco in casos:
            erro = erro_de(funcao, corpo)
            self.assertEqual(erro.codigo, 400, corpo)
            self.assertIn(pedaco, erro.mensagem)

    def test_nada_de_fora_escolhe_arquivo(self):
        # a fonte da chuva e a regra dos anos (que escolhem o arquivo lido) não entram pela API
        for campo, valor in (("chuva", "power"), ("chuva", "../../../etc/passwd"), ("regra", "chuva"), ("arquivo", "x")):
            erro = erro_de(api.rota_recomendacao, dict(ENTRADA, **{campo: valor}))
            self.assertEqual(erro.codigo, 400)
            self.assertIn(campo, erro.mensagem)

    def test_ler_json_so_aceita_um_objeto_em_utf8(self):
        self.assertEqual(api.ler_json(b'{"terra": "m\xc3\xa9dia"}'), {"terra": "média"})
        for corpo in (b"", b"oi", b"[1, 2]", b'"soja"', b"7", b"{", b"\xff\xfe", b'{"a": NaN}', b'{"a": Infinity}',
                      b"[" * 5000, b'{"a": ' + b"9" * 6000 + b"}"):
            self.assertEqual(erro_de(api.ler_json, corpo).codigo, 400, corpo[:20])

    def test_liga_no_127_0_0_1_por_padrao_e_a_porta_e_opcao(self):
        self.assertEqual((api.ler_opcoes([]).endereco, api.ler_opcoes([]).porta), ("127.0.0.1", 8000))
        opcoes = api.ler_opcoes(["--porta", "8123", "--endereco", "0.0.0.0"])
        self.assertEqual((opcoes.endereco, opcoes.porta), ("0.0.0.0", 8123))


class PorHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servidor = api.criar_servidor("127.0.0.1", 0, silencioso=True)      # porta 0 = uma porta livre
        cls.porta = cls.servidor.server_address[1]
        cls.fio = threading.Thread(target=cls.servidor.serve_forever, daemon=True)
        cls.fio.start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        cls.fio.join(5)

    def pedir(self, metodo, caminho, corpo=None, cabecalhos=JSON):
        """Devolve (o código, os cabeçalhos, o JSON da resposta)."""
        if corpo is not None and not isinstance(corpo, bytes):
            corpo = json.dumps(corpo).encode("utf-8")
        ligacao = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=10)
        try:
            ligacao.request(metodo, caminho, body=corpo, headers=cabecalhos if corpo is not None else {})
            resposta = ligacao.getresponse()
            bruto = resposta.read()
            self.assertEqual(resposta.getheader("Access-Control-Allow-Origin"), "*", caminho)
            if resposta.status == 204 or metodo == "HEAD":
                return resposta.status, resposta, None
            self.assertEqual(resposta.getheader("Content-Type"), "application/json; charset=utf-8")
            return resposta.status, resposta, json.loads(bruto.decode("utf-8"))
        finally:
            ligacao.close()

    def test_o_servidor_do_teste_so_escuta_no_127_0_0_1(self):
        self.assertEqual(self.servidor.server_address[0], "127.0.0.1")

    def test_saude(self):
        codigo, _, corpo = self.pedir("GET", "/saude")
        self.assertEqual(codigo, 200)
        self.assertIs(corpo["ok"], True)
        self.assertIn("/conversa", json.dumps(corpo))

    def test_recomendacao_por_http_e_a_resposta_inteira_do_motor(self):
        codigo, _, corpo = self.pedir("POST", "/recomendacao", ENTRADA)
        self.assertEqual(codigo, 200)
        self.assertEqual(corpo, RESPOSTA)
        self.assertEqual(self.pedir("POST", "/recomendacao?x=1", ENTRADA)[0], 200)

    def test_mensagem_por_http(self):
        codigo, _, corpo = self.pedir("POST", "/mensagem", ENTRADA)
        self.assertEqual(codigo, 200)
        self.assertEqual(corpo, {"texto": mensagem.texto(RESPOSTA)})

    def test_a_conversa_inteira_por_http(self):
        estado = None
        for fala in ("oi", "terra boa", "2", "5", "4", "2", "3"):
            codigo, _, corpo = self.pedir("POST", "/conversa", {"estado": estado, "texto": fala})
            self.assertEqual(codigo, 200)
            self.assertEqual(set(corpo), {"estado", "resposta"})
            estado = corpo["estado"]
        self.assertEqual(estado, {"etapa": "fim"})
        self.assertTrue(corpo["resposta"].startswith(mensagem.texto(RESPOSTA)))
        codigo, _, corpo = self.pedir("POST", "/conversa", {"estado": estado, "texto": "de novo"})
        self.assertEqual(corpo["estado"], {"etapa": "terra"})

    def test_entrada_errada_e_400_com_o_erro_em_portugues(self):
        casos = ((b"{isto nao e json", "JSON"), (b"[1, 2, 3]", "objeto"), (dict(ENTRADA, terra="barro"), "terra"),
                 ({"cidade_id": "rio_verde"}, "rotacao_atual"), (dict(ENTRADA, chuva="power"), "chuva"))
        for corpo, pedaco in casos:
            codigo, _, saida = self.pedir("POST", "/recomendacao", corpo)
            self.assertEqual(codigo, 400, corpo)
            self.assertEqual(set(saida), {"erro"})
            self.assertIn(pedaco, saida["erro"])
        codigo, _, saida = self.pedir("POST", "/conversa", {"estado": None, "texto": 5})
        self.assertEqual((codigo, "texto" in saida["erro"]), (400, True))
        self.assertEqual(self.pedir("POST", "/mensagem", {"terra": "media"})[0], 400)

    def test_rota_que_nao_existe_e_404(self):
        for metodo, caminho in (("GET", "/"), ("GET", "/nada"), ("POST", "/nada"), ("GET", "/saude/"),
                                ("GET", "/../../etc/passwd"), ("GET", "/data/orbita/parametros-com-fonte.json"),
                                ("GET", "//[x"), ("DELETE", "/nada")):
            codigo, _, saida = self.pedir(metodo, caminho, {} if metodo == "POST" else None)
            self.assertEqual(codigo, 404, caminho)
            self.assertIn("não existe", saida["erro"])

    def test_metodo_errado_e_405_e_diz_o_certo(self):
        for metodo, caminho, certo in (("GET", "/recomendacao", "POST"), ("GET", "/mensagem", "POST"),
                                       ("GET", "/conversa", "POST"), ("POST", "/saude", "GET"),
                                       ("PUT", "/recomendacao", "POST"), ("DELETE", "/saude", "GET")):
            codigo, resposta, saida = self.pedir(metodo, caminho, ENTRADA if metodo in ("POST", "PUT") else None)
            self.assertEqual(codigo, 405, caminho)
            self.assertIn(certo, resposta.getheader("Allow"))
            self.assertIn(certo, saida["erro"])

    def test_corpo_grande_e_413(self):
        grande = dict(ENTRADA, terra="m" * (api.LIMITE_DO_CORPO + 1))
        for corpo in (grande, b"x" * 300000):
            codigo, _, saida = self.pedir("POST", "/recomendacao", corpo)
            self.assertEqual(codigo, 413)
            self.assertIn(str(api.LIMITE_DO_CORPO), saida["erro"])
        self.assertLessEqual(api.LIMITE_DO_CORPO, 64 * 1024)

    def test_so_json_o_resto_e_415(self):
        corpo = json.dumps(ENTRADA).encode("utf-8")
        for tipo in ("text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x"):
            codigo, _, saida = self.pedir("POST", "/recomendacao", corpo, {"Content-Type": tipo})
            self.assertEqual(codigo, 415, tipo)
            self.assertIn("application/json", saida["erro"])
        self.assertEqual(self.pedir("POST", "/recomendacao", corpo,
                                    {"Content-Type": "Application/JSON; charset=utf-8"})[0], 200)

    def test_sem_o_tamanho_do_corpo_e_411(self):
        with socket.create_connection(("127.0.0.1", self.porta), timeout=10) as fio:
            fio.sendall(b"POST /recomendacao HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n\r\n")
            resposta = fio.recv(4096).decode("utf-8")
        self.assertIn(" 411 ", resposta.split("\r\n")[0])

    def test_o_site_pode_ler_cors_e_o_pedido_de_licenca(self):
        codigo, resposta, _ = self.pedir("OPTIONS", "/recomendacao")
        self.assertEqual(codigo, 204)
        self.assertIn("POST", resposta.getheader("Access-Control-Allow-Methods"))
        self.assertIn("Content-Type", resposta.getheader("Access-Control-Allow-Headers"))
        self.assertEqual(self.pedir("GET", "/nada")[1].getheader("Access-Control-Allow-Origin"), "*")   # no erro também

    def test_nao_conta_a_versao_do_python_e_pedido_torto_vem_em_portugues(self):
        _, resposta, _ = self.pedir("GET", "/saude")
        self.assertNotIn("Python", resposta.getheader("Server") or "")
        with socket.create_connection(("127.0.0.1", self.porta), timeout=10) as fio:
            fio.sendall(b"ISTO NAO E HTTP\r\n\r\n")
            torto = fio.recv(4096).decode("utf-8")
        self.assertIn('"erro"', torto)
        self.assertNotIn("Error response", torto)


if __name__ == "__main__":
    unittest.main()
