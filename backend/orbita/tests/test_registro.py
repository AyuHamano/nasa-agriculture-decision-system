# Gerado com IA (Claude)
"""Testes do registro da safra (o "depois"): o que foi plantado, a água, o calor e a terra coberta."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orbita import clima, conferencia, motor, parametros, registro

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
        # Eram 11 até 2026-11-15: o registro punha a safra mais recente (2025-26) entre as do estudo, e a conta a
        # deixa à parte. Agora valem as mesmas 10 safras da comparação das rotações.
        self.assertEqual(entre["de"], 10)
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
        # Silvânia ganhou o verde do satélite em 2026-11-15: o registro de lá passa a trazer os pontos de lá
        de_la = motor.registro_da_safra(dict(ENTRADA, cidade_id="silvania"), "2018-19")["terra_coberta"]["pelo_satelite"]
        self.assertEqual((de_la["ano"], de_la["pontos"]), (2019, 6))
        self.assertIn("perto de Silvânia (GO)", de_la["aviso"])
        self.assertNotIn("Rio Verde", de_la["aviso"])
        with tempfile.TemporaryDirectory() as vazia, mock.patch.object(clima, "PASTA_DAS_CIDADES", Path(vazia) / "x"):
            self.assertIsNone(registro._verde_do_ano("silvania", 2019, parametros.carregar()))

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


class ASafraQueAindaNaoFechou(unittest.TestCase):
    def test_a_frase_diz_a_data_do_ultimo_dia_e_nao_fala_de_dado_nem_de_atraso(self):
        inteiro = motor.replay_da_safra(ENTRADA, "2015-16")
        cortado = dict(inteiro, dias=inteiro["dias"][:300], completa=False)        # a safra só até 26/06/2016
        self.assertEqual(cortado["dias"][-1]["data"], "2016-06-26")
        with mock.patch.object(motor, "replay_da_safra", return_value=cortado):
            do_meio = registro.registro_da_safra(ENTRADA, "2015-16")
        sem_planta = do_meio["terra_coberta"]["dias_sem_planta_viva"]
        self.assertIn(f" Até 26/06/2016, a terra ficou {sem_planta} dias sem planta viva (a safra ainda não fechou;",
                      do_meio["frase"])
        self.assertIn("de 1 de setembro a 26/06/2016, na safra que ainda não fechou", do_meio["terra_coberta"]["nota"])
        self.assertIn("(de 1 de setembro a 31 de agosto)", REGISTRO["terra_coberta"]["nota"])
        for registro_ in (do_meio, REGISTRO):
            for texto in (registro_["frase"], registro_["terra_coberta"]["nota"], registro_["aviso"]):
                for proibido in ("último dia com dado", "atras", "aproximad"):
                    self.assertNotIn(proibido, texto.lower())


if __name__ == "__main__":
    unittest.main()
