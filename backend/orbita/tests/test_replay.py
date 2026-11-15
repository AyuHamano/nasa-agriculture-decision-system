# Gerado com IA (Claude)
"""Testes das funções que o agente chama: o clima do lugar e o replay da safra, dia a dia."""
import datetime
import json
import unittest

from orbita import conferencia, motor

ENTRADA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media"}
RESPOSTA = motor.responder(ENTRADA)
REPLAY = motor.replay_da_safra(ENTRADA, "2015-16")
CAMPOS_DO_DIA = {"data", "cultura", "chuva_mm", "agua_na_terra_mm", "pedido_mm", "bebido_mm", "falta_mm", "com_sede",
                 "tmax_c", "calor_forte"}
TIPOS_DE_MARCO = {"plantio", "agua_acabou", "agua_no_fundo", "calor_forte", "colheita"}   # agua_no_fundo: 2026-11-15


class ClimaDoLugar(unittest.TestCase):
    def test_devolve_o_lugar_as_fontes_a_regra_dos_anos_e_o_calor(self):
        for cidade in motor.CIDADES:
            lugar = motor.clima_do_lugar(cidade)
            self.assertEqual(lugar["local"]["id"], cidade)
            for chave in ("chuva", "temperatura", "primeiro_dia", "ultimo_dia", "avisos"):
                self.assertIn(chave, lugar["clima"])
            self.assertIn(lugar["regra_dos_anos"]["pior_ano"], lugar["regra_dos_anos"]["chuva_por_safra_mm"])
            self.assertIn(lugar["regra_dos_anos"]["ano_normal"], lugar["regra_dos_anos"]["chuva_por_safra_mm"])
            self.assertEqual(set(lugar["calor"]["limites"]), {"soja", "milho", "sorgo"})
            self.assertEqual(len(lugar["chuva_da_safra_mm"]), 10)
            self.assertEqual(conferencia.conferir_texto(lugar["frase"], lugar), [])
            json.dumps(lugar, ensure_ascii=False)

    def test_bate_com_a_resposta_do_motor(self):
        lugar = motor.clima_do_lugar("rio_verde")
        self.assertEqual(lugar["regra_dos_anos"], RESPOSTA["regra_dos_anos"])
        self.assertEqual(lugar["clima"], RESPOSTA["clima"])
        self.assertEqual(lugar["calor"]["por_cultura"], RESPOSTA["calor"]["por_cultura"])

    def test_cidade_que_nao_existe_e_erro_em_portugues(self):
        with self.assertRaises(ValueError) as erro:
            motor.clima_do_lugar("sorriso")
        self.assertTrue(str(erro.exception).startswith("Entrada fora do formato:"))


class Replay(unittest.TestCase):
    def test_a_safra_inteira_dia_a_dia_no_formato_combinado(self):
        self.assertEqual(REPLAY["safra"], "2015-16")
        self.assertEqual(REPLAY["cidade_id"], "rio_verde")
        self.assertEqual(len(REPLAY["dias"]), 366)                      # de 2015-09-01 a 2016-08-31 (ano bissexto)
        self.assertEqual((REPLAY["dias"][0]["data"], REPLAY["dias"][-1]["data"]), ("2015-09-01", "2016-08-31"))
        for dia in REPLAY["dias"]:
            self.assertEqual(set(dia), CAMPOS_DO_DIA)
            self.assertIn(dia["cultura"], ("soja", "milho", "sem_planta"))
            self.assertIsInstance(dia["com_sede"], bool)
            self.assertIsInstance(dia["calor_forte"], bool)
        datas = [datetime.date.fromisoformat(dia["data"]) for dia in REPLAY["dias"]]
        self.assertEqual([(b - a).days for a, b in zip(datas, datas[1:])], [1] * 365)
        json.dumps(REPLAY, ensure_ascii=False)

    def test_os_totais_do_replay_sao_os_da_conta(self):
        safra = RESPOSTA["rotacoes"]["atual"]["safras"]["2015-16"]
        self.assertEqual(REPLAY["resumo"]["total"]["falta_mm"], safra["total"]["falta_mm"])
        self.assertEqual(REPLAY["resumo"]["total"]["dias_de_sede"], safra["total"]["dias_de_sede"])
        self.assertEqual(REPLAY["resumo"]["milho"]["falta_mm"], safra["milho"]["falta_mm"])
        self.assertEqual(sum(dia["com_sede"] for dia in REPLAY["dias"]), safra["total"]["dias_de_sede"])
        self.assertAlmostEqual(sum(dia["falta_mm"] for dia in REPLAY["dias"]), safra["total"]["falta_mm"], delta=6)
        calor = RESPOSTA["calor"]["por_cultura"]["milho"]["por_safra"]["2015-16"]["dias_de_calor_forte"]
        self.assertEqual(sum(dia["calor_forte"] for dia in REPLAY["dias"] if dia["cultura"] == "milho"), calor)
        self.assertEqual(REPLAY["resumo"]["milho"]["dias_de_calor_forte"], calor)

    def test_os_marcos_saem_da_conta(self):
        por_data = {dia["data"]: dia for dia in REPLAY["dias"]}
        self.assertTrue({m["tipo"] for m in REPLAY["marcos"]} <= TIPOS_DE_MARCO)
        self.assertEqual([m["data"] for m in REPLAY["marcos"]], sorted(m["data"] for m in REPLAY["marcos"]))
        plantios = [m for m in REPLAY["marcos"] if m["tipo"] == "plantio"]
        self.assertEqual([(m["cultura"], m["data"]) for m in plantios], [("soja", "2015-10-15"), ("milho", "2016-02-10")])
        principais = [m for m in REPLAY["marcos"] if m["principal"]]
        self.assertEqual(len(principais), 1)
        marco = principais[0]
        self.assertEqual(marco["tipo"], "agua_acabou")
        self.assertTrue(por_data[marco["data"]]["com_sede"])
        comeco = datetime.date.fromisoformat(marco["data"])
        vespera = por_data[(comeco - datetime.timedelta(days=1)).isoformat()]
        self.assertFalse(vespera["com_sede"])
        for i in range(marco["dias_seguidos"]):
            self.assertTrue(por_data[(comeco + datetime.timedelta(days=i)).isoformat()]["com_sede"])
        for m in REPLAY["marcos"]:
            self.assertEqual(conferencia.conferir_texto(m["frase"], REPLAY), [], m["frase"])
            self.assertEqual(por_data[m["data"]]["cultura"], m["cultura"])
        quentes = [m for m in REPLAY["marcos"] if m["tipo"] == "calor_forte"]
        for m in quentes:
            self.assertTrue(por_data[m["data"]]["calor_forte"])
            self.assertGreater(m["tmax_c"], m["limite_c"])

    def test_o_replay_segue_a_rotacao_a_cidade_e_a_data_do_produtor(self):
        sorgo = motor.replay_da_safra({"cidade_id": "jatai", "rotacao_atual": ["soja", "sorgo"],
                                       "plantio_da_soja": "2026-11-20"}, "2020-21")
        self.assertEqual(sorgo["rotacao"]["id"], "soja_sorgo_pousio")
        self.assertIn("sorgo", {dia["cultura"] for dia in sorgo["dias"]})
        self.assertNotIn("milho", {dia["cultura"] for dia in sorgo["dias"]})
        plantios = {m["cultura"]: m["data"] for m in sorgo["marcos"] if m["tipo"] == "plantio"}
        self.assertEqual(plantios, {"soja": "2020-11-20", "sorgo": "2021-03-18"})
        capim = motor.replay_da_safra(dict(ENTRADA, rotacao_atual=["soja", "milho", "braquiaria"]), "2015-16")
        self.assertIn("braquiaria", {dia["cultura"] for dia in capim["dias"]})
        self.assertTrue(any("hipótese do meio" in aviso for aviso in capim["avisos"]))

    def test_safra_que_nao_esta_guardada_e_erro_em_portugues(self):
        for ruim in ("1999-00", "2016", None):
            with self.assertRaises(ValueError) as erro:
                motor.replay_da_safra(ENTRADA, ruim)
            self.assertTrue(str(erro.exception).startswith("Entrada fora do formato:"))
        with self.assertRaises(ValueError):
            motor.replay_da_safra(dict(ENTRADA, cidade_id="sorriso"), "2015-16")

    def test_a_safra_mais_recente_guardada_tambem_passa(self):
        recente = motor.replay_da_safra(ENTRADA, "2025-26")
        self.assertEqual((recente["primeiro_dia"], recente["ultimo_dia"]), ("2025-09-01", "2026-08-31"))
        self.assertTrue(recente["completa"])
        self.assertEqual(recente["resumo"]["total"]["falta_mm"], RESPOSTA["safra_2025_26"]["atual"]["total"]["falta_mm"])


if __name__ == "__main__":
    unittest.main()
