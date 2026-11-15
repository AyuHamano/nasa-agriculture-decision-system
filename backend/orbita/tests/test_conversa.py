# Gerado com IA (Claude)
"""Testes da conversa em passos: do começo ao resultado, a resposta fora do esperado, o recomeço e o estado."""
import copy
import json
import unittest

from orbita import conferencia, conversa, mensagem, motor

# As 4 notas de 1 a 5 saíram da conversa (decisão do dono, 2026-11-15): fica a saudação -> a terra -> o resultado.
ENTRADA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media"}
RESPOSTA = motor.responder(ENTRADA)
FALAS = ("oi", "2")
ANTIGOS = ({"etapa": "agua", "terra": "media", "notas": {}},                # o estado de quem estava no meio das notas
           {"etapa": "solo", "terra": "media", "notas": {"agua": 5}},
           {"etapa": "renda", "terra": "pouca", "notas": {"agua": 5, "solo": 4}},
           {"etapa": "erosao", "terra": "muita", "notas": {"agua": 5, "solo": 4, "renda": 2}})
RECADO = "meu nome é João da Silva, telefone 64 99999-0000"


def conversar(falas, estado=None):
    """Roda as falas em ordem e devolve [(estado, resposta)] de cada passo."""
    passos = []
    for fala in falas:
        estado, resposta = conversa.passo(estado, fala)
        passos.append((estado, resposta))
    return passos


class ConversaInteira(unittest.TestCase):
    def test_da_saudacao_ao_resultado(self):
        passos = conversar(FALAS)
        saudacao = passos[0][1]
        self.assertIn("Órbita Rural", saudacao)
        self.assertIn("só para Rio Verde", saudacao)
        self.assertIn("braquiária", saudacao)                              # o que a ferramenta faz
        for opcao in ("1 (pouca)", "2 (média)", "3 (muita)"):
            self.assertIn(opcao, saudacao)
        self.assertIn("É 1 pergunta rápida.", saudacao)                    # a saudação diz quantas são de verdade
        self.assertEqual(saudacao.count("?"), 1)
        self.assertNotIn("De 1 a 5", saudacao)                             # as notas saíram (2026-11-15)
        self.assertEqual([estado for estado, _ in passos], [{"etapa": "terra"}, {"etapa": "fim"}])
        resultado = passos[1][1]
        self.assertNotIn("nota", resultado.lower())
        self.assertTrue(resultado.startswith(mensagem.texto(RESPOSTA)))    # o mesmo texto do mensagem.py
        self.assertIn("mande 'de novo' para recomeçar", resultado.lower())
        self.assertEqual(conferencia.conferir_texto(resultado, RESPOSTA), [])

    def test_de_novo_recomeca_do_fim_e_do_meio(self):
        fim = conversar(FALAS)[-1][0]
        for estado in (fim, conversar(FALAS[:1])[-1][0]) + ANTIGOS:
            for fala in ("de novo", "De novo!", " DE NOVO "):
                novo, resposta = conversa.passo(estado, fala)
                self.assertEqual(novo, {"etapa": "terra"})
                self.assertIn("só para Rio Verde", resposta)

    def test_depois_do_resultado_outra_fala_ensina_a_recomecar(self):
        fim = conversar(FALAS)[-1][0]
        estado, resposta = conversa.passo(fim, "obrigado")
        self.assertEqual(estado, fim)
        self.assertIn("de novo", resposta)

    def test_aceita_a_resposta_por_extenso(self):
        for fala, terra in (("Média", "media"), ("muita água", "muita"), ("1.", "pouca")):
            estado, resultado = conversar(("oi", fala))[-1]
            self.assertEqual(estado, {"etapa": "fim"})
            esperado = mensagem.texto(motor.responder(dict(ENTRADA, terra=terra)))
            self.assertTrue(resultado.startswith(esperado), fala)


class RespostaForaDoEsperado(unittest.TestCase):
    def test_repete_a_pergunta_com_um_exemplo_e_nao_anda(self):
        na_terra = conversar(("oi",))[-1][0]
        for estado, falas in ((na_terra, ("barro", "4", "", "1 ou 2", "0", "1 a 5", "4,5", "-3", "10", RECADO)),):
            for fala in falas:
                novo, resposta = conversa.passo(estado, fala)
                self.assertEqual(novo, estado, fala)
                self.assertIn("Exemplo:", resposta, fala)
                self.assertIn("?", resposta, fala)                         # a pergunta vem de novo
                self.assertNotIn("João", resposta)                         # e o que foi escrito não volta

    def test_estado_estragado_recomeca_pela_saudacao(self):
        estragados = ANTIGOS + ({}, {"etapa": "lua"}, {"etapa": "solo"}, {"etapa": 3}, {"etapa": ["solo"]},
                      {"etapa": "solo", "terra": "barro", "notas": {"agua": 5}},
                      {"etapa": "solo", "terra": "media", "notas": {"agua": 9}},
                      {"etapa": "solo", "terra": "media", "notas": {"agua": True}},
                      {"etapa": "solo", "terra": "media", "notas": {"agua": 5.0}},
                      {"etapa": "solo", "terra": "media", "notas": {}},
                      {"etapa": "solo", "terra": "media", "notas": {"agua": 5, "erosao": 1}},
                      {"etapa": "renda", "terra": "media", "notas": "5"})
        for estado in estragados:
            novo, resposta = conversa.passo(estado, "4")
            self.assertEqual(novo, {"etapa": "terra"}, estado)
            self.assertIn("só para Rio Verde", resposta)

    def test_estado_ou_texto_de_outro_tipo_da_erro_em_portugues(self):
        for estado, texto in (("solo", "4"), ([], "4"), (7, "4"), (None, 4), (None, None), ({"etapa": "terra"}, ["2"])):
            with self.assertRaises(ValueError) as erro:
                conversa.passo(estado, texto)
            self.assertIn("conversa", str(erro.exception).lower())


class OEstado(unittest.TestCase):
    def test_e_pequeno_vira_json_e_so_tem_a_etapa(self):
        for estado, _ in conversar(FALAS):
            self.assertEqual(set(estado), {"etapa"})                       # sem as notas, nem a terra fica guardada
            self.assertLess(len(json.dumps(estado)), 120)
            self.assertEqual(json.loads(json.dumps(estado)), estado)
        self.assertEqual(conversar(FALAS)[-1][0], {"etapa": "fim"})         # no fim, nem as notas ficam

    def test_o_estado_que_volta_de_um_json_continua_a_conversa(self):
        estado = None
        for fala in FALAS:
            estado, resposta = conversa.passo(json.loads(json.dumps(estado)), fala)
        self.assertTrue(resposta.startswith(mensagem.texto(RESPOSTA)))

    def test_nao_mexe_no_estado_recebido_e_nao_guarda_nada_entre_as_chamadas(self):
        estado = conversar(("oi",))[-1][0]
        copia = copy.deepcopy(estado)
        primeira = conversa.passo(estado, "2")
        self.assertEqual(estado, copia)
        self.assertEqual(conversa.passo(estado, "2"), primeira)             # a mesma entrada dá a mesma saída
        self.assertEqual(conversa.passo(None, "oi"), conversa.passo(None, "outra pessoa"))

    def test_os_nomes_que_o_agente_usa_continuam_e_os_das_notas_sairam(self):
        self.assertEqual(conversa._limpar("  De NOVO! "), "de novo")       # o agente.py usa estes dois nomes
        self.assertIn("de novo", conversa.DE_NOVO)
        for nome in ("NOTAS", "NOTAS_POR_EXTENSO", "_ler_nota"):
            self.assertFalse(hasattr(conversa, nome), nome)
        self.assertEqual(set(conversa.PERGUNTAS), {"terra"})

    def test_nome_e_telefone_nao_sao_pedidos_nem_guardados(self):
        estado, resposta = conversa.passo({"etapa": "terra", "telefone": "64999990000", "nome": "João"}, "2")
        self.assertEqual(estado, {"etapa": "fim"})                          # o que veio a mais não volta
        self.assertNotIn("João", resposta)
        estado = None
        for fala in (RECADO, RECADO, "2", RECADO):
            estado, resposta = conversa.passo(estado, fala)
            self.assertNotIn("João", json.dumps(estado, ensure_ascii=False) + resposta)
            self.assertNotIn("99999", json.dumps(estado) + resposta)
            self.assertNotRegex(resposta.lower(), r"(qual|diga|informe|mande)[^.?]*(seu nome|telefone|celular|cpf)")
        self.assertEqual(estado, {"etapa": "fim"})


if __name__ == "__main__":
    unittest.main()
