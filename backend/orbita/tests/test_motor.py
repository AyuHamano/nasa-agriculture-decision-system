# Gerado com IA (Claude)
"""Testes do motor: a entrada, a regra dos anos, as 10 safras, as prioridades, a explicação e o comando perguntar."""
import contextlib
import copy
import io
import json
import unittest

from orbita import explicacao, motor, perguntar

ENTRADA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"],
           "prioridades": {"agua": 5, "solo": 4, "renda": 2, "erosao": 3}, "terra": "media"}
RESPOSTA = motor.responder(ENTRADA)


def erro_de(entrada):
    with unittest.TestCase().assertRaises(ValueError) as erro:
        motor.validar_entrada(entrada)
    return str(erro.exception)


class Entrada(unittest.TestCase):
    def test_sem_terra_vale_media(self):
        entrada = {k: v for k, v in ENTRADA.items() if k != "terra"}
        self.assertEqual(motor.validar_entrada(entrada)["terra"], "media")

    def test_erros_em_portugues_dizendo_o_que_falta(self):
        self.assertIn("prioridades", erro_de({k: v for k, v in ENTRADA.items() if k != "prioridades"}))
        sem_agua = copy.deepcopy(ENTRADA)
        del sem_agua["prioridades"]["agua"]
        self.assertIn("agua", erro_de(sem_agua))
        nota_6 = copy.deepcopy(ENTRADA)
        nota_6["prioridades"]["solo"] = 6
        self.assertIn("1 a 5", erro_de(nota_6))
        self.assertIn("terra", erro_de(dict(ENTRADA, terra="barro")))
        self.assertIn("cidade_id", erro_de(dict(ENTRADA, cidade_id="sorriso")))
        self.assertIn("rotacao_atual", erro_de(dict(ENTRADA, rotacao_atual=["soja", "algodao"])))
        self.assertIn("cidade_id", erro_de({}))
        self.assertIn("formato", erro_de("soja"))


class RegraDosAnos(unittest.TestCase):
    def test_o_mais_seco_e_o_mais_perto_da_mediana(self):
        chuvas = {"2015-16": 500.0, "2016-17": 300.0, "2017-18": 455.0, "2018-19": 610.0, "2019-20": 700.0}
        regra = motor.escolher_anos(chuvas)
        self.assertEqual(regra["ano_mais_seco"], "2016-17")
        self.assertEqual(regra["mediana_mm"], 500.0)
        self.assertEqual(regra["ano_normal"], "2015-16")

    def test_com_numero_par_de_safras_as_duas_do_meio_empatam_e_vale_a_mais_antiga(self):
        # Com 10 safras a mediana é a média da 5ª e da 6ª: as duas ficam à mesma distância, sempre.
        chuvas = {"2015-16": 510.0, "2016-17": 300.0, "2017-18": 440.0, "2018-19": 610.0}
        regra = motor.escolher_anos(chuvas)
        self.assertEqual(regra["mediana_mm"], 475.0)
        self.assertEqual(regra["empate_do_ano_normal"], ["2015-16", "2017-18"])
        self.assertEqual(regra["ano_normal"], "2015-16")

    def test_na_serie_guardada(self):
        regra = RESPOSTA["regra_dos_anos"]
        chuvas = regra["chuva_por_safra_mm"]
        self.assertEqual(len(chuvas), 10)
        self.assertEqual(regra["ano_mais_seco"], min(chuvas, key=chuvas.get))
        self.assertNotEqual(regra["ano_normal"], regra["ano_mais_seco"])
        self.assertEqual(regra["segunda_mais_seca"], sorted(chuvas, key=chuvas.get)[1])

    def test_ano_mais_seco_em_2025_leva_o_aviso_da_chuva_suspeita(self):
        regra = RESPOSTA["regra_dos_anos"]
        if regra["ano_mais_seco"] == "2024-25":
            self.assertIn("suspeita", regra["aviso_do_ano_mais_seco"])
            self.assertAlmostEqual(regra["chuva_de_2025_mm"], 678, delta=1)
            self.assertIn("Segunda safra mais seca", explicacao.texto(RESPOSTA))
        else:
            self.assertNotIn("aviso_do_ano_mais_seco", regra)


class Numeros(unittest.TestCase):
    def test_as_10_safras_nas_duas_rotacoes_e_a_2025_26_a_parte(self):
        for rotacao in ("atual", "alternativa"):
            safras = RESPOSTA["rotacoes"][rotacao]["safras"]
            self.assertEqual(list(safras), list(RESPOSTA["regra_dos_anos"]["chuva_por_safra_mm"]))
            self.assertNotIn("2025-26", safras)
        self.assertIn("a conferir", RESPOSTA["safra_2025_26"]["aviso"])
        self.assertIn("atual", RESPOSTA["safra_2025_26"])

    def test_safras_com_sede_batem_com_a_falta_relativa_do_milho(self):
        for rotacao in ("atual", "alternativa"):
            r = RESPOSTA["rotacoes"][rotacao]
            for criterio, chave in ((20, "quantas"), (10, "com_10_pct"), (30, "com_30_pct")):
                n = sum(1 for s in r["safras"].values() if s["milho"]["falta_relativa_pct"] >= criterio)
                self.assertEqual(r["safras_com_sede"][chave], n)
            self.assertEqual(r["safras_com_sede"]["criterio_pct"], 20)

    def test_a_falta_e_o_pedido_menos_o_bebido(self):
        for rotacao in ("atual", "alternativa"):
            for s in RESPOSTA["rotacoes"][rotacao]["safras"].values():
                for cultura in ("soja", "milho", "total"):
                    c = s[cultura]
                    self.assertAlmostEqual(c["falta_mm"], c["pedido_mm"] - c["bebido_mm"], delta=0.11)
                    self.assertGreaterEqual(c["falta_mm"], 0.0)
                    self.assertLessEqual(c["dias_de_sede"], c["dias"])

    def test_a_resposta_vira_json(self):
        self.assertEqual(json.loads(json.dumps(RESPOSTA, ensure_ascii=False))["entrada"]["terra"], "media")


class Prioridades(unittest.TestCase):
    def test_so_mudam_a_ordem_nenhum_numero_muda(self):
        outra = motor.responder(dict(ENTRADA, prioridades={"agua": 1, "solo": 2, "renda": 5, "erosao": 4}))
        for chave in ("rotacoes", "regra_dos_anos", "safra_2025_26", "veredito"):
            self.assertEqual(outra[chave], RESPOSTA[chave])
        self.assertEqual([p["id"] for p in RESPOSTA["prioridades"]], ["agua", "solo", "erosao", "renda"])
        self.assertEqual([p["id"] for p in outra["prioridades"]], ["renda", "erosao", "solo", "agua"])
        self.assertEqual({p["id"]: p["melhor"] for p in outra["prioridades"]},
                         {p["id"]: p["melhor"] for p in RESPOSTA["prioridades"]})

    def test_cada_prioridade_diz_quem_se_saiu_melhor(self):
        por_id = {p["id"]: p for p in RESPOSTA["prioridades"]}
        for p in por_id.values():
            self.assertIn(p["melhor"], ("atual", "alternativa", "empate", "não medido"))
        self.assertEqual(por_id["renda"]["melhor"], "não medido")
        self.assertEqual(por_id["solo"]["melhor"], por_id["erosao"]["melhor"])

    def test_o_veredito_sai_das_comparacoes(self):
        self.assertEqual(motor.veredito({"agua": "alternativa", "solo": "alternativa", "erosao": "empate"})["codigo"],
                         "vale_testar_a_troca")
        self.assertEqual(motor.veredito({"agua": "atual", "solo": "empate", "erosao": "empate"})["codigo"],
                         "fique_como_esta")
        self.assertEqual(motor.veredito({"agua": "empate", "solo": "empate", "erosao": "empate"})["codigo"],
                         "fique_como_esta")
        self.assertEqual(motor.veredito({"agua": "atual", "solo": "alternativa", "erosao": "alternativa"})["codigo"],
                         "depende")

    def test_comparar_agua(self):
        self.assertEqual(motor.comparar_agua(100.0, 97.0, 3, 3, 5.0)["melhor"], "empate")
        self.assertEqual(motor.comparar_agua(100.0, 120.0, 3, 3, 5.0)["melhor"], "atual")
        self.assertEqual(motor.comparar_agua(100.0, 80.0, 3, 2, 5.0)["melhor"], "alternativa")
        self.assertEqual(motor.comparar_agua(100.0, 120.0, 3, 2, 5.0)["melhor"], "empate")  # as medidas discordam


class Explicacao(unittest.TestCase):
    def test_texto_tem_o_porque_a_prova_o_risco_e_o_agronomo(self):
        texto = explicacao.texto(RESPOSTA)
        for trecho in ("RESPOSTA", "A PROVA", "O RISCO", "alide com o agrônomo", "não medido", "NASA POWER", "FAO-56",
                       RESPOSTA["regra_dos_anos"]["ano_mais_seco"], RESPOSTA["regra_dos_anos"]["ano_normal"]):
            self.assertIn(trecho, texto)
        self.assertNotIn("terra descoberta", texto.lower())

    def test_perguntar_em_texto_e_em_json(self):
        args = ["--agua", "5", "--solo", "4", "--renda", "2", "--erosao", "3", "--terra", "media"]
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            self.assertEqual(perguntar.main(args), 0)
        self.assertIn("RESPOSTA", saida.getvalue())
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            self.assertEqual(perguntar.main(args + ["--json"]), 0)
        self.assertEqual(json.loads(saida.getvalue())["veredito"], RESPOSTA["veredito"])

    def test_perguntar_sem_uma_nota_diz_o_que_falta(self):
        erro = io.StringIO()
        with contextlib.redirect_stderr(erro), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(perguntar.main(["--agua", "5", "--solo", "4", "--renda", "2"]), 2)
        self.assertIn("erosao", erro.getvalue())


if __name__ == "__main__":
    unittest.main()
