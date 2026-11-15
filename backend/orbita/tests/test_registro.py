# Gerado com IA (Claude)
"""Testes do registro da safra (o "depois"): o que foi plantado, a água, o calor e a terra coberta."""
import json
import unittest

from orbita import conferencia, motor

ENTRADA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media"}
RESPOSTA = motor.responder(ENTRADA)
REGISTRO = motor.registro_da_safra(ENTRADA, "2015-16")


class Registro(unittest.TestCase):
    def test_o_que_foi_plantado_com_as_datas_da_conta(self):
        self.assertEqual([(p["cultura"], p["entra"], p["dias"]) for p in REGISTRO["o_que_foi_plantado"]],
                         [("soja", "2015-10-15", 115), ("milho", "2016-02-10", 125)])
        sorgo = motor.registro_da_safra({"cidade_id": "jatai", "rotacao_atual": ["soja", "sorgo"]}, "2020-21")
        self.assertEqual([p["cultura"] for p in sorgo["o_que_foi_plantado"]], ["soja", "sorgo"])
        capim = motor.registro_da_safra(dict(ENTRADA, rotacao_atual=["soja", "milho", "braquiaria"]), "2015-16")
        self.assertEqual([p["cultura"] for p in capim["o_que_foi_plantado"]], ["soja", "milho", "braquiaria"])
        self.assertLess(capim["terra_coberta"]["dias_sem_planta_viva"],
                        REGISTRO["terra_coberta"]["dias_sem_planta_viva"])

    def test_a_agua_e_o_calor_sao_os_da_conta(self):
        safra = RESPOSTA["rotacoes"]["atual"]["safras"]["2015-16"]
        self.assertEqual(REGISTRO["agua"]["falta_mm"], safra["total"]["falta_mm"])
        self.assertEqual(REGISTRO["agua"]["dias_de_sede"], safra["total"]["dias_de_sede"])
        self.assertEqual(REGISTRO["agua"]["por_cultura"]["milho"]["falta_relativa_pct"],
                         safra["milho"]["falta_relativa_pct"])
        calor = RESPOSTA["calor"]["por_cultura"]
        self.assertEqual(REGISTRO["calor"]["por_cultura"]["milho"]["dias"],
                         calor["milho"]["por_safra"]["2015-16"]["dias_de_calor_forte"])
        self.assertEqual(REGISTRO["calor"]["dias_de_calor_forte"],
                         sum(c["dias"] for c in REGISTRO["calor"]["por_cultura"].values()))

    def test_a_posicao_entre_as_safras_sai_da_falta_da_segunda_safra(self):
        entre = REGISTRO["entre_as_safras_guardadas"]
        self.assertEqual(entre["de"], 11)
        maiores = sum(1 for valor in entre["por_safra_pct"].values() if valor > entre["falta_da_2a_safra_pct"])
        self.assertEqual(entre["posicao"], maiores + 1)
        self.assertLessEqual(entre["posicao"], 3)                 # a safra da pior colheita fica entre as de mais sede
        for safra, numeros in RESPOSTA["rotacoes"]["atual"]["safras"].items():
            self.assertEqual(entre["por_safra_pct"][safra], numeros["milho"]["falta_relativa_pct"], safra)

    def test_o_satelite_entra_so_onde_e_quando_ha_medida(self):
        self.assertIsNone(REGISTRO["terra_coberta"]["pelo_satelite"])          # em 2016 o verde ainda não era medido
        com_medida = motor.registro_da_safra(ENTRADA, "2018-19")["terra_coberta"]["pelo_satelite"]
        self.assertEqual(com_medida["ano"], 2019)
        self.assertEqual(com_medida["pontos"], 6)
        self.assertTrue(com_medida["menor"] <= com_medida["dias_sem_planta_verde"] <= com_medida["maior"])
        fora = motor.registro_da_safra(dict(ENTRADA, cidade_id="silvania"), "2018-19")
        self.assertIsNone(fora["terra_coberta"]["pelo_satelite"])

    def test_as_frases_so_tem_numero_da_conta_e_o_registro_vira_json(self):
        for safra in ("2015-16", "2018-19", "2025-26"):
            registro = motor.registro_da_safra(ENTRADA, safra)
            self.assertEqual(conferencia.conferir_texto(registro["frase"], registro), [], safra)
            self.assertIn(f"Safra {safra}", registro["frase"])
            json.dumps(registro, ensure_ascii=False)
        self.assertTrue(REGISTRO["aviso"])
        self.assertTrue(REGISTRO["marcos"])

    def test_safra_ou_entrada_errada_e_erro_em_portugues(self):
        for chamada in (lambda: motor.registro_da_safra(ENTRADA, "2030-31"),
                        lambda: motor.registro_da_safra(dict(ENTRADA, rotacao_atual=["trigo"]), "2015-16")):
            with self.assertRaises(ValueError) as erro:
                chamada()
            self.assertTrue(str(erro.exception).startswith("Entrada fora do formato:"))


if __name__ == "__main__":
    unittest.main()
