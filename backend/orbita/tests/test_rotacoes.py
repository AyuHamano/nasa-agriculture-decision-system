# Gerado com IA (Claude)
"""Testes do calendário das duas rotações, da curva do Kc (FAO-56, cap. 6, eq. 66) e dos parâmetros com fonte."""
import copy
import datetime
import unittest

from orbita import parametros, rotacoes

D = datetime.date


class CurvaDoKc(unittest.TestCase):
    def test_fases_15_25_50_20(self):
        fases, kc = [15, 25, 50, 20], (0.4, 1.15, 0.5)
        self.assertAlmostEqual(rotacoes.kc_da_fase(0, fases, *kc), 0.4)
        self.assertAlmostEqual(rotacoes.kc_da_fase(15, fases, *kc), 0.4)
        self.assertAlmostEqual(rotacoes.kc_da_fase(27, fases, *kc), 0.4 + 12 / 25 * 0.75)   # = 0,76
        self.assertAlmostEqual(rotacoes.kc_da_fase(40, fases, *kc), 1.15)
        self.assertAlmostEqual(rotacoes.kc_da_fase(90, fases, *kc), 1.15)
        self.assertAlmostEqual(rotacoes.kc_da_fase(100, fases, *kc), 1.15 - 10 / 20 * 0.65)  # = 0,825


class Calendario(unittest.TestCase):
    def setUp(self):
        self.cal = rotacoes.calendario(parametros.carregar())

    def tipo(self, data, com_braquiaria):
        return rotacoes.cobertura_do_dia(data, com_braquiaria, self.cal)[0]

    def test_soja_e_milho_iguais_nas_duas_rotacoes(self):
        for com in (False, True):
            self.assertEqual(self.tipo(D(2020, 11, 20), com), "soja")
            self.assertEqual(self.tipo(D(2021, 4, 1), com), "milho")

    def test_depois_do_milho_pousio_ou_braquiaria(self):
        self.assertEqual(self.tipo(D(2021, 8, 1), False), "sem_planta")
        self.assertEqual(self.tipo(D(2021, 8, 1), True), "braquiaria")

    def test_depois_de_secar_a_braquiaria_nao_ha_planta_viva(self):
        plantio = self.cal.plantio_da_soja(2021)
        vespera = plantio - datetime.timedelta(days=1)
        self.assertEqual(self.tipo(vespera, True), "sem_planta")
        self.assertEqual(self.tipo(plantio, True), "soja")

    def test_dias_sem_planta_viva(self):
        resumo = rotacoes.resumo_do_calendario(parametros.carregar())
        plantio, fim_do_milho = self.cal.plantio_da_soja(2021), self.cal.fim_do_milho(2021)
        self.assertEqual(resumo["atual"]["dias_sem_planta_viva"], (plantio - fim_do_milho).days)
        self.assertEqual(resumo["alternativa"]["dias_sem_planta_viva"], self.cal.dessecacao_dias)
        self.assertGreater(resumo["atual"]["dias_sem_planta_viva"], resumo["alternativa"]["dias_sem_planta_viva"])

    def test_milho_plantado_antes_de_colher_a_soja_e_erro(self):
        par = copy.deepcopy(parametros.carregar())
        par["culturas"]["milho_2a_safra"]["plantio_mes_dia"]["valor"] = "01-05"
        with self.assertRaises(ValueError) as erro:
            rotacoes.calendario(par)
        self.assertIn("soja", str(erro.exception))


class ParametrosComFonte(unittest.TestCase):
    def test_todo_parametro_tem_fonte_trecho_e_etiqueta(self):
        folhas = parametros.folhas(parametros.carregar())
        self.assertGreater(len(folhas), 20)
        for caminho, p in folhas:
            self.assertIn(p["etiqueta"], ("publicado", "hipótese"), caminho)
            self.assertTrue(p["trecho"], caminho)
            if p["etiqueta"] == "publicado":
                self.assertTrue(str(p["fonte"]).startswith("http"), caminho)

    def test_as_3_terras_em_ordem(self):
        par = parametros.carregar()
        agua = [par["terra"][t]["agua_mm_por_m"]["valor"] for t in ("pouca", "media", "muita")]
        self.assertEqual(agua, sorted(agua))
        self.assertLess(agua[0], agua[2])


if __name__ == "__main__":
    unittest.main()
