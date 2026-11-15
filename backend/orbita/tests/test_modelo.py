# Gerado com IA (Claude)
"""Testes do encaixe da IA: o modelo de mentira e o modelo de verdade, sem chave de verdade e sem internet."""
import io
import json
import unittest
import urllib.error

from orbita import modelo
from orbita.modelo import ErroDoModelo, ModeloDeMentira, ModeloOpenRouter, SemChave, chamada, fala

CHAVE = "sk-or-chave-de-mentira-0123456789"
MENSAGENS = [{"de": "sistema", "texto": "as regras"}, {"de": "produtor", "texto": "oi"},
             {"de": "agente", "texto": "", "chamadas": [chamada("ensaio_da_rotacao", "c1", safra="2015-16")]},
             {"de": "ferramenta", "id": "c1", "nome": "ensaio_da_rotacao", "resultado": {"falta_mm": 232.9}},
             {"de": "agente", "texto": "Faltaram 999 mm."}, {"de": "programa", "texto": "o 999 não está na conta"}]
FERRAMENTAS = [{"nome": "ensaio_da_rotacao", "descricao": "o ensaio", "parametros": {"type": "object"}}]
RESPOSTA = {"choices": [{"message": {"content": " Faltaram 232,9 mm. ", "tool_calls": None}}],
            "usage": {"prompt_tokens": 900, "completion_tokens": 40, "cost": 0.00011}}


def erro_http(codigo):
    return urllib.error.HTTPError("https://openrouter.ai", codigo, "erro", {}, io.BytesIO(b'{"error": {"message": "x"}}'))


class Fio:
    """O lugar do envio pela internet: guarda o que foi mandado e devolve as respostas da lista, na ordem."""

    def __init__(self, *respostas):
        self.respostas, self.pedidos = list(respostas), []

    def __call__(self, endereco, corpo, cabecalhos, espera):
        self.pedidos.append((endereco, corpo, cabecalhos, espera))
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


class OModeloDeMentira(unittest.TestCase):
    def test_devolve_as_respostas_na_ordem_e_guarda_o_que_recebeu(self):
        ia = ModeloDeMentira([fala("", chamada("clima_do_lugar", hoje=True)), fala("pronto")])
        primeira = ia.responder(MENSAGENS[:2], FERRAMENTAS)
        self.assertEqual(primeira["chamadas"], [{"id": "chamada_clima_do_lugar", "nome": "clima_do_lugar",
                                                 "argumentos": {"hoje": True}}])
        self.assertEqual(ia.responder(MENSAGENS, FERRAMENTAS)["texto"], "pronto")
        self.assertEqual(len(ia.pedidos), 2)
        self.assertEqual(ia.pedidos[0], (MENSAGENS[:2], FERRAMENTAS))

    def test_acabou_a_lista_devolve_texto_vazio(self):
        self.assertEqual(ModeloDeMentira().responder(MENSAGENS, []),
                         {"texto": "", "chamadas": [], "uso": {}, "cortado": False})

    def test_a_resposta_pode_ser_uma_funcao_ou_um_erro(self):
        ia = ModeloDeMentira([lambda mensagens, ferramentas: fala(mensagens[-1]["texto"].upper()),
                              ErroDoModelo("a IA caiu")])
        self.assertEqual(ia.responder(MENSAGENS[:2], [])["texto"], "OI")
        with self.assertRaises(ErroDoModelo):
            ia.responder(MENSAGENS, [])


class OModeloDeVerdade(unittest.TestCase):
    def test_manda_a_conversa_no_formato_do_openrouter(self):
        fio = Fio(RESPOSTA)
        ia = ModeloOpenRouter(CHAVE, "anthropic/claude-haiku-5.5", enviar=fio)
        resposta = ia.responder(MENSAGENS, FERRAMENTAS)
        self.assertEqual(resposta, {"texto": "Faltaram 232,9 mm.", "chamadas": [], "cortado": False,
                                    "uso": {"entrada": 900, "saida": 40, "custo_usd": 0.00011}})
        endereco, corpo, cabecalhos, _ = fio.pedidos[0]
        self.assertEqual(endereco, modelo.ENDERECO)
        self.assertTrue(endereco.startswith("https://"))
        self.assertEqual(cabecalhos["Authorization"], "Bearer " + CHAVE)
        self.assertEqual(corpo["model"], "anthropic/claude-haiku-5.5")
        self.assertEqual([m["role"] for m in corpo["messages"]], ["system", "user", "assistant", "tool", "assistant", "user"])
        pedido = corpo["messages"][2]["tool_calls"][0]
        self.assertEqual((pedido["id"], pedido["type"], pedido["function"]["name"]), ("c1", "function", "ensaio_da_rotacao"))
        self.assertEqual(json.loads(pedido["function"]["arguments"]), {"safra": "2015-16"})
        self.assertEqual(corpo["messages"][3], {"role": "tool", "tool_call_id": "c1", "content": '{"falta_mm": 232.9}'})
        self.assertIn("o produtor não vê", corpo["messages"][5]["content"])
        self.assertEqual(corpo["tools"], [{"type": "function", "function": {
            "name": "ensaio_da_rotacao", "description": "o ensaio", "parameters": {"type": "object"}}}])
        self.assertNotIn(CHAVE, json.dumps(corpo))                       # a chave só vai no cabeçalho

    def test_le_os_pedidos_de_ferramenta_e_soma_o_gasto(self):
        com_pedido = {"choices": [{"message": {"content": None, "tool_calls": [
            {"id": "a1", "type": "function", "function": {"name": "anotar_na_ficha", "arguments": '{"terra": "media"}'}},
            {"id": "a2", "type": "function", "function": {"name": "clima_do_lugar", "arguments": "isto não é json"}},
            {"type": "function", "function": {"name": "verde_do_satelite", "arguments": "[1]"}}]}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 10, "cost": 0.5}}
        ia = ModeloOpenRouter(CHAVE, enviar=Fio(com_pedido, RESPOSTA))
        resposta = ia.responder(MENSAGENS[:2], FERRAMENTAS)
        self.assertEqual(resposta["texto"], "")
        self.assertEqual(resposta["chamadas"], [
            {"id": "a1", "nome": "anotar_na_ficha", "argumentos": {"terra": "media"}},
            {"id": "a2", "nome": "clima_do_lugar", "argumentos": {}},
            {"id": "chamada_2", "nome": "verde_do_satelite", "argumentos": {}}])
        ia.responder(MENSAGENS[:2], FERRAMENTAS)
        self.assertEqual(ia.uso["pedidos"], 2)
        self.assertEqual((ia.uso["entrada"], ia.uso["saida"]), (1000, 50))
        self.assertAlmostEqual(ia.uso["custo_usd"], 0.50011)

    def test_texto_cortado_por_falta_de_espaco_e_pedido_de_novo_com_o_dobro(self):
        cortada = {"choices": [{"finish_reason": "length", "message": {"content": "No pior ano faltaram 232"}}]}
        inteira = dict(RESPOSTA, choices=[dict(RESPOSTA["choices"][0], finish_reason="stop")])
        fio = Fio(cortada, inteira)
        resposta = ModeloOpenRouter(CHAVE, enviar=fio).responder(MENSAGENS[:2], FERRAMENTAS)
        self.assertEqual((resposta["texto"], resposta["cortado"]), ("Faltaram 232,9 mm.", False))
        primeiro, segundo = fio.pedidos[0][1], fio.pedidos[1][1]
        self.assertEqual(primeiro["max_tokens"], modelo.TAMANHO_DA_RESPOSTA)
        self.assertEqual(segundo["max_tokens"], 2 * modelo.TAMANHO_DA_RESPOSTA)
        self.assertEqual(primeiro["reasoning"], {"effort": "low"})         # a IA pensa pouco: sobra espaço para o texto
        fio = Fio(cortada, cortada)                                        # cortou de novo: volta marcado, sem repetir
        resposta = ModeloOpenRouter(CHAVE, enviar=fio).responder(MENSAGENS[:2], FERRAMENTAS)
        self.assertEqual((resposta["cortado"], len(fio.pedidos)), (True, 2))

    def test_o_texto_em_pedacos_tambem_e_lido(self):
        em_pedacos = {"choices": [{"message": {"content": [{"type": "text", "text": "Faltaram "},
                                                           {"type": "text", "text": "232,9 mm."}]}}]}
        self.assertEqual(ModeloOpenRouter(CHAVE, enviar=Fio(em_pedacos)).responder(MENSAGENS[:2], [])["texto"],
                         "Faltaram 232,9 mm.")

    def test_erro_do_servico_vira_frase_em_portugues_sem_a_chave(self):
        casos = ((erro_http(401), "recusada"), (erro_http(402), "sem saldo ou venceu"), (erro_http(404), "não existe"),
                 (OSError("sem rede"), "sem ligação"), ({"error": {"message": "modelo fora do ar"}}, "fora do ar"),
                 ({"choices": []}, "não deu para ler"))
        for resposta, pedaco in casos:
            ia = ModeloOpenRouter(CHAVE, enviar=Fio(resposta, resposta), pausa=0)
            with self.assertRaises(ErroDoModelo) as erro:
                ia.responder(MENSAGENS[:2], FERRAMENTAS)
            self.assertIn(pedaco, str(erro.exception))
            self.assertNotIn(CHAVE, str(erro.exception))
            self.assertNotIn(CHAVE, repr(erro.exception))

    def test_falha_passageira_e_tentada_de_novo_uma_vez(self):
        for falha in (erro_http(429), erro_http(503), TimeoutError("demorou")):
            fio = Fio(falha, RESPOSTA)
            self.assertEqual(ModeloOpenRouter(CHAVE, enviar=fio, pausa=0).responder(MENSAGENS[:2], [])["texto"],
                             "Faltaram 232,9 mm.")
            self.assertEqual(len(fio.pedidos), 2)
        fio = Fio(erro_http(401), RESPOSTA)                               # chave recusada não adianta repetir
        with self.assertRaises(ErroDoModelo):
            ModeloOpenRouter(CHAVE, enviar=fio, pausa=0).responder(MENSAGENS[:2], [])
        self.assertEqual(len(fio.pedidos), 1)

    def test_a_chave_vem_do_ambiente_so_na_hora_e_nao_aparece(self):
        for ambiente in ({}, {"OPENROUTER_API_KEY": ""}, {"OPENROUTER_API_KEY": "   "}, {"ORBITA_MODELO": "x/y"}):
            with self.assertRaises(SemChave) as erro:
                modelo.do_ambiente(ambiente)
            self.assertIn("OPENROUTER_API_KEY", str(erro.exception))
        ia = modelo.do_ambiente({"OPENROUTER_API_KEY": CHAVE})
        self.assertEqual(ia.nome, modelo.MODELO_PADRAO)
        self.assertEqual(modelo.do_ambiente({"OPENROUTER_API_KEY": CHAVE, "ORBITA_MODELO": modelo.MODELO_RESERVA}).nome,
                         "deepseek/deepseek-v4.1-flash")
        self.assertNotIn(CHAVE, repr(ia))
        self.assertNotIn(CHAVE, str(vars(ia).get("nome")))
        self.assertTrue(issubclass(SemChave, ErroDoModelo))
        with self.assertRaises(SemChave):
            ModeloOpenRouter("")

    def test_mensagem_de_quem_nao_existe_e_recusada(self):
        with self.assertRaises(ValueError):
            ModeloOpenRouter(CHAVE, enviar=Fio(RESPOSTA)).responder([{"de": "alguem", "texto": "oi"}], [])


if __name__ == "__main__":
    unittest.main()
