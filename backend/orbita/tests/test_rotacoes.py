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
        self.assertAlmostEqual(rotacoes.kc_da_fase(14, fases, *kc), 0.4)                    # dia 15: ainda no início
        self.assertAlmostEqual(rotacoes.kc_da_fase(27, fases, *kc), 0.4 + 13 / 25 * 0.75)   # dia 28: 0,79
        self.assertAlmostEqual(rotacoes.kc_da_fase(39, fases, *kc), 1.15)                   # dia 40: fim da subida
        self.assertAlmostEqual(rotacoes.kc_da_fase(89, fases, *kc), 1.15)                   # dia 90: fim do meio
        self.assertAlmostEqual(rotacoes.kc_da_fase(100, fases, *kc), 1.15 - 11 / 20 * 0.65)  # dia 101: 0,7925


    def test_exemplo_28_do_fao56(self):
        # FAO-56, cap. 6, Exemplo 28 (feijão seco; fases 25/25/30/20; Kc 0,15 / 1,19 / 0,35): no dia 40 do ciclo
        # Kc = 0,77 e no dia 95, Kc = 0,56. O dia 1 é o do plantio (aqui, n = 0).
        fases, kc = [25, 25, 30, 20], (0.15, 1.19, 0.35)
        self.assertAlmostEqual(rotacoes.kc_da_fase(39, fases, *kc), 0.77, delta=0.005)
        self.assertAlmostEqual(rotacoes.kc_da_fase(94, fases, *kc), 0.56, delta=0.005)
        self.assertAlmostEqual(rotacoes.kc_da_fase(99, fases, *kc), 0.35)   # o último dia chega ao Kc final


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

    def test_terra_sem_planta_usa_o_coeficiente_de_superficie_molhada(self):
        # Achado da revisão: o valor de solo seco (0,2), junto com o freio Kr, freava a evaporação duas vezes.
        par = parametros.carregar()
        self.assertGreaterEqual(par["culturas"]["solo_nu"]["kc"]["valor"], 0.9)
        self.assertEqual(par["culturas"]["solo_nu"]["kc"]["etiqueta"], "hipótese")
        self.assertEqual(rotacoes.calendario(par).solo_nu_kc, par["culturas"]["solo_nu"]["kc"]["valor"])
        if parametros.ARQUIVO_CONFERIDO.exists():
            self.assertLess(par["culturas"]["solo_nu"]["kc_seco"]["valor"], 0.5)

    def test_as_3_terras_em_ordem(self):
        par = parametros.carregar()
        agua = [par["terra"][t]["agua_mm_por_m"]["valor"] for t in ("pouca", "media", "muita")]
        self.assertEqual(agua, sorted(agua))
        self.assertLess(agua[0], agua[2])


if __name__ == "__main__":
    unittest.main()
