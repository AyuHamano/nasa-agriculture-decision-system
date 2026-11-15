# Gerado com IA (Claude)
"""Testes dos acertos de 2026-11-15 no motor: cada um falhava no código de antes."""
import unittest

from orbita import conferencia, explicacao, mensagem, motor

HOJE = ["soja", "milho", "pousio"]
JATAI = {"cidade_id": "jatai", "rotacao_atual": HOJE, "terra": "media"}
RIO_VERDE = {"cidade_id": "rio_verde", "rotacao_atual": HOJE, "terra": "media"}
RIO_VERDE_TARDE = dict(RIO_VERDE, plantio_da_soja="2026-11-20")


def _por_id(resposta):
    return {item["id"]: item for item in resposta["comparacao_das_rotacoes"]}


class APiorColheitaNaoEAMaiorFaltaDeAgua(unittest.TestCase):
    """O pior ano é o da pior colheita da região (IBGE). Quando a conta dá menos falta de água nele que no ano
    normal, a frase diz isso, em vez de soar ao contrário."""

    @classmethod
    def setUpClass(cls):
        cls.jatai, cls.tarde, cls.rio_verde = (motor.responder(e) for e in (JATAI, RIO_VERDE_TARDE, RIO_VERDE))

    def test_em_jatai_a_frase_diz_que_o_pior_ano_teve_menos_falta_que_o_normal(self):
        hoje = _por_id(self.jatai)["soja_milho_pousio"]
        self.assertEqual((hoje["agua"]["falta_no_pior_ano_mm"], hoje["agua"]["falta_no_ano_normal_mm"]), (162.4, 224.2))
        self.assertEqual(hoje["agua"]["pior_ano_contra_o_normal"], "menor")
        self.assertIn("o pior ano é o da pior colheita da região (safra 2015-16), não o de maior falta de água na "
                      "conta", hoje["evidencia"])
        self.assertIn("faltaram 162,4 mm", hoje["evidencia"])
        self.assertIn("menos que no ano normal (safra 2021-22), que teve 224,2 mm", hoje["evidencia"])

    def test_em_rio_verde_com_o_plantio_em_20_de_novembro_tambem(self):
        itens = _por_id(self.tarde)
        hoje, capim = itens["soja_milho_pousio"], itens["soja_milho_braquiaria"]
        self.assertEqual((hoje["agua"]["falta_no_pior_ano_mm"], hoje["agua"]["falta_no_ano_normal_mm"]), (256.0, 260.4))
        self.assertIn("menos que no ano normal (safra 2019-20), que teve 260,4 mm", hoje["evidencia"])
        # na faixa do capim, a ponta de cima é igual nos dois anos: a frase não diz "menos", diz "não mais"
        self.assertEqual(capim["agua"]["pior_ano_contra_o_normal"], "menor")
        self.assertIn("não mais que no ano normal (safra 2019-20), que teve de 260,4 a 266,8 mm", capim["evidencia"])

    def test_nesses_casos_nenhuma_frase_fala_do_pior_ano_como_o_de_mais_falta(self):
        for resposta in (self.jatai, self.tarde):
            for item in resposta["comparacao_das_rotacoes"]:
                self.assertNotEqual(item["agua"]["pior_ano_contra_o_normal"], "maior", item["id"])
                self.assertNotIn("no pior ano (safra", item["evidencia"])
                for chave in ("evidencia", "beneficio", "risco", "falta_saber"):
                    self.assertNotIn("do pior ano", item[chave], (item["id"], chave))
                    self.assertEqual(conferencia.conferir_texto(item[chave], resposta), [], (item["id"], chave))
            self.assertIn("da pior colheita da região", resposta["comparacao_das_rotacoes"][0]["risco"])
            inteiro, curto = explicacao.texto(resposta), mensagem.texto(resposta)
            self.assertIn("não o de maior falta de água na conta", inteiro)
            self.assertNotIn("No pior ano (safra", inteiro)
            self.assertIn("no ano da pior colheita da região (safra 2015-16)", curto)
            self.assertNotIn("no pior ano", curto)
            self.assertLessEqual(len(curto), mensagem.LIMITE)
            self.assertEqual(conferencia.conferir_texto(curto, resposta), [])

    def test_onde_o_pior_ano_tem_mais_falta_a_frase_fica_como_era(self):
        for item in self.rio_verde["comparacao_das_rotacoes"]:
            self.assertEqual(item["agua"]["pior_ano_contra_o_normal"], "maior", item["id"])
        hoje = _por_id(self.rio_verde)["soja_milho_pousio"]
        self.assertIn("no pior ano (safra 2015-16) faltaram 225,9 mm de água para as culturas, com 73 dias de sede; "
                      "no ano normal (safra 2019-20), 152,8 mm.", hoje["evidencia"])
        self.assertIn("Na água do pior ano, ficou atrás de", hoje["risco"])
        self.assertIn("No pior ano (safra 2015-16), faltaram", explicacao.texto(self.rio_verde))
        self.assertIn("no pior ano (safra 2015-16), faltaram", mensagem.texto(self.rio_verde))

    def test_a_comparacao_dos_dois_anos_vale_para_numero_e_para_faixa(self):
        self.assertEqual(explicacao.pior_contra_normal(225.9, 152.8), "maior")
        self.assertEqual(explicacao.pior_contra_normal(162.4, 224.2), "menor")
        self.assertEqual(explicacao.pior_contra_normal(100.0, 100.0), "igual")
        self.assertEqual(explicacao.pior_contra_normal({"de": 256.0, "ate": 266.8}, {"de": 260.4, "ate": 266.8}), "menor")
        self.assertEqual(explicacao.pior_contra_normal({"de": 250.0, "ate": 270.0}, {"de": 255.0, "ate": 265.0}), "cruza")


if __name__ == "__main__":
    unittest.main()
