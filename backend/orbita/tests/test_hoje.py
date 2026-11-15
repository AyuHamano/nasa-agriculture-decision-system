# Gerado com IA (Claude)
"""Testes do "como está hoje": a chuva recente guardada, a série esticada e o retrato do último dia com dado."""
import datetime
import json
import pathlib
import tempfile
import unittest

from orbita import clima, conferencia, hoje, motor

D = datetime.date
ENTRADA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media"}
DIA_DO_TESTE = D(2026, 11, 15)
RETRATO = motor.como_esta_hoje(ENTRADA, hoje=DIA_DO_TESTE)


class ChuvaRecente(unittest.TestCase):
    def test_cada_cidade_tem_a_chuva_recente_com_o_endereco_e_a_hora(self):
        for cidade in motor.CIDADES:
            valores, fonte = hoje.ler_chuva_recente(cidade)
            self.assertGreater(len(valores), 30, cidade)
            bruto = json.loads((hoje.PASTA_DA_CHUVA_RECENTE / cidade / "fonte.json").read_text(encoding="utf-8"))
            self.assertAlmostEqual(bruto["ponto"]["latitude"], motor.CIDADES[cidade]["latitude"])
            for consulta in bruto["consultas"]:
                self.assertTrue(consulta["endereco"].startswith("https://gibs.earthdata.nasa.gov/"), cidade)
                self.assertTrue(consulta["consultado_em_utc"])
            self.assertTrue(fonte["ressalvas"])

    def test_esticar_para_no_primeiro_dia_sem_dado_e_nunca_poe_zero(self):
        dia = lambda data, chuva: clima.Dia(data, chuva, 30.0, 20.0, 4.0)  # noqa: E731
        guardados = [dia(D(2026, 9, 13), 1.0), dia(D(2026, 9, 14), 2.0)]
        temperatura = [dia(D(2026, 9, 13) + datetime.timedelta(days=i), 9.0) for i in range(8)]
        recente = {D(2026, 9, 14): 99.0, D(2026, 9, 15): 5.0, D(2026, 9, 16): 0.0, D(2026, 9, 17): None,
                   D(2026, 9, 18): 7.0}
        com_recente, com_modelo = hoje.esticar(guardados, temperatura, recente)
        self.assertEqual([d.data.day for d in com_recente], [13, 14, 15, 16])       # parou no dia 17, em branco
        self.assertEqual([d.chuva for d in com_recente], [1.0, 2.0, 5.0, 0.0])      # o dia guardado não é trocado
        self.assertEqual([d.chuva for d in com_modelo], [1.0, 2.0, 9.0, 9.0])
        self.assertEqual(len(hoje.esticar(guardados, temperatura, {})[0]), 2)       # sem chuva recente, não estica


class Retrato(unittest.TestCase):
    def test_devolve_o_ultimo_dia_o_atraso_a_agua_e_as_comparacoes(self):
        self.assertTrue(RETRATO["disponivel"])
        ultimo = D.fromisoformat(RETRATO["ultimo_dia_com_dado"])
        self.assertEqual(RETRATO["hoje"], "2026-11-15")
        self.assertEqual(RETRATO["atraso_dias"], (DIA_DO_TESTE - ultimo).days)
        self.assertGreater(ultimo, D(2026, 9, 14))                     # foi além da chuva guardada
        self.assertLessEqual(RETRATO["atraso_dias"], 10)
        self.assertEqual(RETRATO["safra"], "2026-27")
        self.assertTrue(0 <= RETRATO["agua_na_terra_mm"] <= RETRATO["agua_que_a_terra_segura_mm"])
        for chave in ("no_ano_normal", "no_pior_ano"):
            outro = RETRATO[chave]
            data = D.fromisoformat(outro["data"])
            self.assertEqual((data.month, data.day), (ultimo.month, ultimo.day))
            self.assertEqual(outro["diferenca_mm"], round(RETRATO["agua_na_terra_mm"] - outro["agua_na_terra_mm"], 1))
        resposta = motor.responder(ENTRADA)
        self.assertEqual(RETRATO["no_pior_ano"]["safra"], resposta["comparacao"]["pior_ano"])
        self.assertEqual(RETRATO["no_ano_normal"]["safra"], resposta["comparacao"]["ano_normal"])
        self.assertTrue(RETRATO["aviso"])
        json.dumps(RETRATO, ensure_ascii=False)

    def test_a_chuva_recente_vai_com_a_de_modelo_ao_lado_e_a_faixa(self):
        chuva, faixa = RETRATO["chuva_recente"], RETRATO["faixa_da_agua_na_terra_mm"]
        self.assertEqual(chuva["de"], "2026-09-15")
        self.assertEqual(chuva["ate"], RETRATO["ultimo_dia_com_dado"])
        self.assertGreater(chuva["satelite_rapido_mm"], 0)
        self.assertGreater(chuva["modelo_da_nasa_power_mm"], 0)
        self.assertEqual({faixa["de"], faixa["ate"]},
                         {RETRATO["agua_na_terra_mm"], RETRATO["com_a_chuva_de_modelo"]["agua_na_terra_mm"]})
        self.assertLessEqual(faixa["de"], faixa["ate"])

    def test_a_frase_so_tem_numero_da_conta(self):
        self.assertEqual(conferencia.conferir_texto(RETRATO["frase"], RETRATO), [])
        self.assertIn("Rio Verde", RETRATO["frase"])

    def test_segue_a_cidade_a_rotacao_e_a_data_do_produtor(self):
        outro = motor.como_esta_hoje({"cidade_id": "jatai", "rotacao_atual": ["soja", "sorgo"],
                                      "plantio_da_soja": "2026-11-20"}, hoje=DIA_DO_TESTE)
        self.assertEqual(outro["rotacao"]["id"], "soja_sorgo_pousio")
        self.assertEqual(outro["local"]["id"], "jatai")
        self.assertEqual(outro["o_que_esta_na_terra"], "sem_planta")     # a soja dele só entra em 20 de novembro
        self.assertEqual(RETRATO["o_que_esta_na_terra"], "soja")         # no calendário de costume, entrou em 15/10

    def test_sem_a_chuva_recente_guardada_diz_o_que_falta(self):
        with tempfile.TemporaryDirectory() as pasta:
            vazio = hoje.como_esta_hoje(ENTRADA, hoje=DIA_DO_TESTE, pasta_da_chuva_recente=pathlib.Path(pasta))
        self.assertFalse(vazio["disponivel"])
        self.assertIn("baixar_chuva_recente.py", vazio["aviso"])

    def test_entrada_errada_e_erro_em_portugues(self):
        with self.assertRaises(ValueError) as erro:
            motor.como_esta_hoje(dict(ENTRADA, cidade_id="sorriso"))
        self.assertTrue(str(erro.exception).startswith("Entrada fora do formato:"))


if __name__ == "__main__":
    unittest.main()
