# Gerado com IA (Claude)
"""Testes da API: as funções direto e uma ida e volta de verdade por HTTP, numa porta livre do 127.0.0.1."""
import http.client
import json
import os
import socket
import threading
import unittest
from unittest import mock

from orbita import api, ferramentas, mensagem, motor
from orbita.modelo import ErroDoModelo, ModeloDeMentira, chamada, fala
from orbita.tests.duble_do_motor import Duble

# As notas de 1 a 5 saíram das rotas (decisão do dono, 2026-11-15): a pergunta de sempre vai sem `prioridades`.
ENTRADA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media"}
COM_NOTAS = dict(ENTRADA, prioridades={"agua": 5, "solo": 4, "renda": 2, "erosao": 3})   # quem ainda manda as notas
DA_SAFRA = {"cidade_id": "rio_verde", "safra": "2015-16"}       # o corpo do /replay e do /registro, só o obrigatório
RESPOSTA = json.loads(json.dumps(motor.responder(ENTRADA)))     # como ela chega depois de virar JSON
JSON = {"Content-Type": "application/json"}


def ate_o_fim(fio):
    """Tudo o que o servidor mandou por uma ligação crua, até ele fechar."""
    pedacos = []
    while True:
        pedaco = fio.recv(4096)
        if not pedaco:
            return b"".join(pedacos).decode("utf-8")
        pedacos.append(pedaco)


def sem_a_hora(registro):
    """O registro da safra sem `registrado_em` (a hora da chamada, que muda de uma chamada para a outra)."""
    return {campo: valor for campo, valor in registro.items() if campo != "registrado_em"}


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
                 (api.rota_conversa, {"estado": None}, "texto"),
                 (api.rota_conversa, {"estado": None, "texto": 5}, "texto"),
                 (api.rota_conversa, {"estado": "solo", "texto": "4"}, "estado"),
                 (api.rota_conversa, {"estado": None, "texto": "oi", "telefone": "64999990000"}, "telefone"))
        for funcao, corpo, pedaco in casos:
            erro = erro_de(funcao, corpo)
            self.assertEqual(erro.codigo, 400, corpo)
            self.assertIn(pedaco, erro.mensagem)

    def test_as_notas_de_1_a_5_sairam_quem_ainda_manda_nao_quebra_e_a_resposta_nao_devolve_nota(self):
        # decisão do dono, 2026-11-15 ("tira isso"): o corpo pode trazer `prioridades`, a API não repassa ao motor
        for notas in (COM_NOTAS["prioridades"], {"agua": 9}, "muitas", None):
            self.assertEqual(api.rota_recomendacao(dict(ENTRADA, prioridades=notas)), motor.responder(ENTRADA))
            self.assertEqual(api.rota_mensagem(dict(ENTRADA, prioridades=notas)), api.rota_mensagem(dict(ENTRADA)))
        resposta = api.rota_recomendacao(dict(COM_NOTAS))
        self.assertIsNone(resposta["entrada"].get("prioridades"))
        self.assertEqual([p.get("nota") for p in resposta["prioridades"]], [None] * len(resposta["prioridades"]))
        self.assertNotIn("nota", api.rota_mensagem(dict(COM_NOTAS))["texto"].lower())
        self.assertNotIn("prioridades", api.EXEMPLO)

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


class AsRotasDaSafra(unittest.TestCase):
    """POST /replay e POST /registro: contas do motor, sem IA, para a tela."""

    def test_replay_e_o_que_o_motor_devolve_com_os_padroes(self):
        # sem rotacao_atual e sem terra valem soja -> milho -> pousio e a terra media
        saida = api.rota_replay(dict(DA_SAFRA))
        self.assertEqual(saida, motor.replay_da_safra(ENTRADA, "2015-16"))
        self.assertEqual((saida["safra"], saida["terra"]), ("2015-16", "media"))
        self.assertGreater(len(saida["dias"]), 300)
        self.assertTrue(saida["marcos"])

    def test_registro_e_o_que_o_motor_devolve_com_os_padroes(self):
        saida = api.rota_registro(dict(DA_SAFRA))
        self.assertEqual(sem_a_hora(saida), sem_a_hora(motor.registro_da_safra(ENTRADA, "2015-16")))
        self.assertIn("o_que_foi_plantado", saida)
        self.assertIn("registrado_em", saida)

    def test_a_rotacao_a_terra_e_o_plantio_vao_ao_motor(self):
        corpo = dict(DA_SAFRA, rotacao_atual=["soja", "sorgo"], terra="pouca", plantio="2015-11-20")
        entrada = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "sorgo"], "terra": "pouca",
                   "plantio_da_soja": "2015-11-20"}
        self.assertEqual(api.rota_replay(dict(corpo)), motor.replay_da_safra(entrada, "2015-16"))
        self.assertEqual(sem_a_hora(api.rota_registro(dict(corpo))),
                         sem_a_hora(motor.registro_da_safra(entrada, "2015-16")))
        # `plantio_da_soja` (o nome da /lavoura-hoje) é sinônimo de `plantio`
        sinonimo = dict(DA_SAFRA, rotacao_atual=["soja", "sorgo"], terra="pouca", plantio_da_soja="2015-11-20")
        self.assertEqual(api.rota_replay(sinonimo), api.rota_replay(dict(corpo)))
        self.assertEqual(api.rota_replay(dict(corpo))["plantio_da_soja_informado"], "2015-11-20")

    def test_a_safra_aceita_pior_ano_e_ano_normal(self):
        anos = motor.clima_do_lugar("rio_verde")["regra_dos_anos"]
        for nome in ("pior_ano", "ano_normal"):
            for rota in (api.rota_replay, api.rota_registro):
                self.assertEqual(rota(dict(DA_SAFRA, safra=nome))["safra"], anos[nome], nome)

    def test_entrada_errada_e_400_em_portugues(self):
        casos = (({"cidade_id": "rio_verde"}, "safra"), ({"safra": "2015-16"}, "cidade_id"),
                 (dict(DA_SAFRA, safra="1990-91"), "safra"), (dict(DA_SAFRA, safra="2015"), "safra"),
                 (dict(DA_SAFRA, safra=2015), "safra"), (dict(DA_SAFRA, cidade_id="sorriso"), "cidade_id"),
                 (dict(DA_SAFRA, cidade_id=["rio_verde"]), "cidade_id"), (dict(DA_SAFRA, terra="barro"), "terra"),
                 (dict(DA_SAFRA, rotacao_atual=["soja", "algodao"]), "rotacao_atual"),
                 (dict(DA_SAFRA, plantio="20/11/2015"), "plantio"), (dict(DA_SAFRA, plantio=5), "plantio"),
                 (dict(DA_SAFRA, plantio="2015-11-20", plantio_da_soja="2015-10-20"), "plantio"),
                 (dict(DA_SAFRA, chuva="power"), "chuva"), (dict(DA_SAFRA, prioridades={"agua": 5}), "prioridades"),
                 (dict(DA_SAFRA, safra="pior_ano", cidade_id="sorriso"), "cidade_id"))
        for rota in (api.rota_replay, api.rota_registro):
            for corpo, pedaco in casos:
                erro = erro_de(rota, dict(corpo))
                self.assertEqual(erro.codigo, 400, corpo)
                self.assertIn(pedaco, erro.mensagem, corpo)

    def test_as_rotas_novas_estao_em_todos_os_lugares(self):
        for caminho, acao in (("/replay", api.rota_replay), ("/registro", api.rota_registro)):
            self.assertEqual(api.ROTAS[caminho], "POST")
            self.assertIs(api.ACOES[caminho], acao)
            self.assertIn(f"POST {caminho}", api.TODAS_AS_ROTAS)
            self.assertIn(caminho, api.ERROS_DO_SERVIDOR[501])
            self.assertIn(f"POST {caminho}", api.rota_saude()["rotas"])
            self.assertIn(f"POST {caminho}", api.__doc__)


class SemChaveDeIa(unittest.TestCase):
    """As quatro rotas que a tela usa direto respondem sem a chave da IA, nas três cidades do motor."""

    def test_recomendacao_lavoura_hoje_replay_e_registro_respondem_200_sem_chave_nas_tres_cidades(self):
        ambiente = {nome: valor for nome, valor in os.environ.items() if nome != "OPENROUTER_API_KEY"}
        with mock.patch.dict(os.environ, ambiente, clear=True):
            servidor = api.criar_servidor("127.0.0.1", 0, silencioso=True)
            fio = threading.Thread(target=servidor.serve_forever, daemon=True)
            fio.start()
            try:
                self.assertEqual(len(motor.CIDADES), 3)
                for cidade in motor.CIDADES:
                    pergunta = {"cidade_id": cidade, "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media"}
                    for caminho, corpo in (("/recomendacao", pergunta), ("/lavoura-hoje", pergunta),
                                           ("/replay", {"cidade_id": cidade, "safra": "2015-16"}),
                                           ("/registro", {"cidade_id": cidade, "safra": "2015-16"})):
                        ligacao = http.client.HTTPConnection("127.0.0.1", servidor.server_address[1], timeout=30)
                        try:
                            ligacao.request("POST", caminho, body=json.dumps(corpo).encode("utf-8"), headers=JSON)
                            resposta = ligacao.getresponse()
                            saida = json.loads(resposta.read().decode("utf-8"))
                        finally:
                            ligacao.close()
                        self.assertEqual(resposta.status, 200, (cidade, caminho, saida))
                        self.assertNotIn("erro", saida, (cidade, caminho))
            finally:
                servidor.shutdown()
                servidor.server_close()
                fio.join(5)


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
        for rota in ("POST /replay", "POST /registro"):
            self.assertIn(rota, corpo["rotas"])

    def test_replay_e_registro_por_http(self):
        codigo, _, corpo = self.pedir("POST", "/replay", DA_SAFRA)
        self.assertEqual(codigo, 200)
        self.assertEqual(corpo, json.loads(json.dumps(motor.replay_da_safra(ENTRADA, "2015-16"))))
        codigo, _, corpo = self.pedir("POST", "/registro", DA_SAFRA)
        self.assertEqual(codigo, 200)
        self.assertEqual(sem_a_hora(corpo),
                         sem_a_hora(json.loads(json.dumps(motor.registro_da_safra(ENTRADA, "2015-16")))))
        for caminho in ("/replay", "/registro"):
            codigo, _, corpo = self.pedir("POST", caminho, dict(DA_SAFRA, safra="1990-91"))
            self.assertEqual((codigo, set(corpo)), (400, {"erro"}))
            self.assertIn("safra", corpo["erro"])
            codigo, _, corpo = self.pedir("POST", caminho, dict(DA_SAFRA, arquivo="x"))
            self.assertEqual((codigo, "arquivo" in corpo["erro"]), (400, True))

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
        for fala in ("oi", "terra boa", "2"):        # a conversa já não pergunta as notas (decisão do dono, 2026-11-15)
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
                                       ("GET", "/replay", "POST"), ("GET", "/registro", "POST"),
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
            resposta = ate_o_fim(fio)
        self.assertIn(" 411 ", resposta.split("\r\n")[0])

    def test_corpo_que_chega_aos_poucos_nao_segura_a_ligacao(self):
        prazo, self.servidor.prazo_do_corpo = self.servidor.prazo_do_corpo, 0.4
        try:
            for rota, tipo, codigo, pedaco in (("/recomendacao", "application/json", 408, "demorou"),
                                               ("/nada", "application/json", 404, "não existe"),   # o corpo jogado
                                               ("/mensagem", "text/plain", 415, "application/json")):   # fora
                with socket.create_connection(("127.0.0.1", self.porta), timeout=3) as fio:
                    fio.sendall(f"POST {rota} HTTP/1.1\r\nHost: x\r\nContent-Type: {tipo}\r\n"
                                "Content-Length: 500\r\n\r\n{".encode("utf-8"))      # promete 500 bytes, manda 1
                    resposta = ate_o_fim(fio)                                           # sem o prazo, isto esperaria 15 s
                self.assertIn(f" {codigo} ", resposta.split("\r\n")[0], rota)
                self.assertIn(pedaco, resposta)                       # o erro chega inteiro e em português
        finally:
            self.servidor.prazo_do_corpo = prazo
        self.assertLessEqual(prazo, 15)

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
            torto = ate_o_fim(fio)
        self.assertIn('"erro"', torto)
        self.assertNotIn("Error response", torto)


# ------------------------------------------------------------------------------------ a rota POST /agente
# O agente por dentro é testado em test_agente.py. Aqui, a rota: as funções direto e uma ida e volta por HTTP, com
# o modelo de mentira (sem chave e sem internet) e o dublê do motor.

ANOTA = chamada("anotar_na_ficha", cidade_id="jatai", rotacao_atual="soja_milho_pousio", terra="media",
                preocupacao="agua")
ENSAIO = chamada("ensaio_da_rotacao")
BOA = "No pior ano faltaram 232,9 mm de água com o milho e 187,5 mm com o sorgo."
GERAL = "Trocar de cultura ajuda a quebrar o ciclo de algumas pragas."
ROTEIRO = (fala("", ANOTA), fala("", ENSAIO), fala(BOA), fala(GERAL))      # a conversa inteira, na ordem dos pedidos
FALAS = ("oi", "Planto soja e milho em Jataí, terra média; tenho medo da seca. Vale o sorgo?", "sim",
         "E as pragas?")
CAMPOS_DA_SAIDA = {"estado", "resposta", "momento", "ficha", "comparacao", "apoio", "conferencia", "aviso",
                   "texto_de", "consultas", "replay"}


class ComODubleDoMotor(unittest.TestCase):
    def setUp(self):
        troca = mock.patch.object(ferramentas, "motor", Duble())
        troca.start()
        self.addCleanup(troca.stop)
        sem_chave = mock.patch.dict(os.environ)                  # nenhum teste lê a chave de verdade
        sem_chave.start()
        self.addCleanup(sem_chave.stop)
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ.pop("ORBITA_MODELO", None)


class ARotaDoAgente(ComODubleDoMotor):
    def test_a_conversa_inteira_pela_funcao_da_rota(self):
        modelo, estado = ModeloDeMentira(ROTEIRO), None
        saidas = []
        for texto in FALAS:
            saida = api.rota_agente({"estado": estado, "texto": texto}, modelo)
            self.assertEqual(set(saida), CAMPOS_DA_SAIDA)
            self.assertEqual(saida["aviso"], "Converse com o agrônomo antes de decidir.")
            estado = saida["estado"]
            saidas.append(saida)
        oi, com_a_ficha, com_a_conta, sem_conta = saidas
        self.assertEqual((oi["comparacao"], com_a_ficha["comparacao"]), (None, None))
        self.assertFalse(com_a_ficha["ficha"]["confirmada"])
        self.assertEqual((com_a_conta["resposta"], com_a_conta["apoio"], com_a_conta["texto_de"]), (BOA, "conta", "ia"))
        self.assertEqual(len(com_a_conta["comparacao"]), 3)
        self.assertEqual(com_a_conta["conferencia"], {"passou": True, "sobras": [], "tentativas": 1})
        self.assertEqual(sem_conta["apoio"], "conhecimento_geral")
        self.assertIn("conhecimento geral", sem_conta["resposta"])
        self.assertEqual(len(sem_conta["comparacao"]), 3)
        self.assertEqual(api.rota_agente({"texto": "oi"}, modelo)["resposta"], oi["resposta"])    # sem estado é o começo

    def test_sem_chave_no_servidor_e_503(self):
        erro = erro_de(api.rota_agente, {"estado": None, "texto": "Planto soja em Jataí."})
        self.assertEqual(erro.codigo, 503)
        self.assertIn("OPENROUTER_API_KEY", erro.mensagem)
        self.assertIn("conversas guardadas", erro.mensagem)
        self.assertEqual(api.rota_saude()["ia_do_agente"], {"ligada": False, "modelo": None})

    def test_com_chave_no_ambiente_a_saude_diz_o_modelo_e_nao_a_chave(self):
        os.environ["OPENROUTER_API_KEY"] = "sk-or-chave-de-mentira-0123456789"
        saude = api.rota_saude()
        self.assertEqual(saude["ia_do_agente"], {"ligada": True, "modelo": "anthropic/claude-haiku-5.5"})
        self.assertNotIn("chave-de-mentira", json.dumps(saude))
        self.assertIn("POST /agente", saude["rotas"])
        for cidade in motor.CIDADES.values():                    # o aviso diz todas as cidades que o motor tem
            self.assertIn(cidade["nome"], saude["aviso"])

    def test_a_ia_que_nao_responde_e_a_conta_que_falta_sao_503(self):
        caiu = ModeloDeMentira([ErroDoModelo("A IA não respondeu: a chave está sem saldo ou venceu (código 402).")])
        erro = erro_de(api.rota_agente, {"estado": None, "texto": "Planto soja em Jataí."}, caiu)
        self.assertEqual(erro.codigo, 503)
        self.assertIn("venceu", erro.mensagem)
        self.assertIn("mantenha o estado", erro.mensagem)
        estado = api.rota_agente({"estado": None, "texto": FALAS[1]}, ModeloDeMentira(ROTEIRO))["estado"]
        ferramentas.motor.quantas = 2                            # o motor só traz 2 rotações: o agente não responde
        erro = erro_de(api.rota_agente, {"estado": estado, "texto": "sim"}, ModeloDeMentira(ROTEIRO[1:]))
        self.assertEqual(erro.codigo, 503)
        self.assertIn("2 rotações", erro.mensagem)

    def test_entrada_errada_e_400_em_portugues(self):
        modelo = ModeloDeMentira()
        casos = (({"estado": None}, "texto"), ({"estado": None, "texto": 5}, "texto"),
                 ({"estado": "ficha", "texto": "oi"}, "estado"), ({"estado": [], "texto": "oi"}, "estado"),
                 ({"estado": None, "texto": "oi", "telefone": "64999990000"}, "telefone"),
                 ({"estado": None, "texto": "oi", "modelo": "outro/modelo"}, "modelo"))
        for corpo, pedaco in casos:
            erro = erro_de(api.rota_agente, corpo, modelo)
            self.assertEqual(erro.codigo, 400, corpo)
            self.assertIn(pedaco, erro.mensagem)
        self.assertEqual(modelo.pedidos, [])

    def test_a_recomendacao_aceita_a_data_do_plantio_e_a_preocupacao(self):
        for campo in ("plantio_da_soja", "preocupacao"):
            self.assertIn(campo, api.CAMPOS_DA_PERGUNTA)
            erro = erro_de(api.rota_recomendacao, dict(ENTRADA, **{campo: 5}))
            self.assertEqual(erro.codigo, 400)
            self.assertIn(campo, erro.mensagem)


class OAgentePorHttp(ComODubleDoMotor):
    def ligar(self, modelo):
        servidor = api.criar_servidor("127.0.0.1", 0, silencioso=True, modelo=modelo)
        fio = threading.Thread(target=servidor.serve_forever, daemon=True)
        fio.start()
        self.addCleanup(fio.join, 5)
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        return servidor.server_address[1]

    def pedir(self, porta, metodo, caminho, corpo=None):
        ligacao = http.client.HTTPConnection("127.0.0.1", porta, timeout=10)
        try:
            dados = None if corpo is None else json.dumps(corpo).encode("utf-8")
            ligacao.request(metodo, caminho, body=dados, headers=JSON if dados is not None else {})
            resposta = ligacao.getresponse()
            bruto = resposta.read()
            return resposta.status, resposta, (json.loads(bruto.decode("utf-8")) if bruto else None)
        finally:
            ligacao.close()

    def test_a_conversa_inteira_por_http_do_oi_ate_a_comparacao_e_uma_pergunta_sem_conta(self):
        porta, estado = self.ligar(ModeloDeMentira(ROTEIRO)), None
        for texto in FALAS:
            codigo, resposta, corpo = self.pedir(porta, "POST", "/agente", {"estado": estado, "texto": texto})
            self.assertEqual(codigo, 200, corpo)
            self.assertEqual(resposta.getheader("Access-Control-Allow-Origin"), "*")
            self.assertEqual(set(corpo), CAMPOS_DA_SAIDA)
            estado = corpo["estado"]                             # quem chama guarda o estado; a API não guarda nada
        self.assertTrue(corpo["ficha"]["confirmada"])
        self.assertEqual((corpo["apoio"], len(corpo["comparacao"])), ("conhecimento_geral", 3))
        self.assertEqual([f["de"] for f in estado["falas"]], ["produtor", "agente"] * 3)

    def test_sem_chave_por_http_e_503_e_as_outras_rotas_continuam(self):
        porta = self.ligar(None)
        codigo, _, corpo = self.pedir(porta, "POST", "/agente", {"estado": None, "texto": "Planto soja em Jataí."})
        self.assertEqual((codigo, set(corpo)), (503, {"erro"}))
        self.assertIn("OPENROUTER_API_KEY", corpo["erro"])
        codigo, _, corpo = self.pedir(porta, "POST", "/agente", {"estado": None, "texto": "oi"})
        self.assertEqual(codigo, 503)                            # sem chave, nem a saudação: a tela usa as guardadas
        codigo, _, corpo = self.pedir(porta, "GET", "/saude")
        self.assertEqual((codigo, corpo["ia_do_agente"]["ligada"]), (200, False))
        self.assertEqual(self.pedir(porta, "POST", "/conversa", {"estado": None, "texto": "oi"})[0], 200)

    def test_os_cuidados_da_api_valem_para_a_rota_do_agente(self):
        porta = self.ligar(ModeloDeMentira())
        codigo, resposta, corpo = self.pedir(porta, "GET", "/agente")
        self.assertEqual((codigo, "POST" in resposta.getheader("Allow")), (405, True))
        codigo, resposta, _ = self.pedir(porta, "OPTIONS", "/agente")
        self.assertEqual((codigo, "POST" in resposta.getheader("Access-Control-Allow-Methods")), (204, True))
        codigo, _, corpo = self.pedir(porta, "POST", "/agente", {"estado": None, "texto": "a" * (api.LIMITE_DO_CORPO + 1)})
        self.assertEqual(codigo, 413)
        codigo, _, corpo = self.pedir(porta, "POST", "/agente", {"estado": None})
        self.assertEqual((codigo, "texto" in corpo["erro"]), (400, True))
        codigo, _, corpo = self.pedir(porta, "GET", "/nada")
        self.assertEqual((codigo, "POST /agente" in corpo["erro"]), (404, True))


if __name__ == "__main__":
    unittest.main()
