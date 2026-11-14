# Gerado com IA (Claude)
"""Testes da radiação no topo da atmosfera (Ra) e da evaporação de referência (ETo).

Os valores esperados vêm de fora do código: os exemplos resolvidos do FAO-56
(Allen et al., 1998, FAO Irrigation and Drainage Paper 56).
- Exemplo 8 (cap. 3, https://www.fao.org/4/X0490E/x0490e07.htm): Ra em 3 de setembro, a 20°S = 32,2 MJ/m²/dia,
  igual a 13,1 mm/dia; no caminho, dr = 0,985, declinação = 0,120 rad, ângulo do pôr do sol = 1,527 rad.
- Exemplo 20 (cap. 4, https://www.fao.org/4/X0490E/x0490e08.htm): Lyon (45°43'N), 15 de julho (dia 196),
  Ra = 40,55 MJ/m²/dia, Tmax = 26,6 °C, Tmin = 14,8 °C; o texto diz: "the Hargreaves equation (Equation 52)
  predicts ETo = 5.0 mm/day".
"""
import datetime
import unittest

from orbita import clima


class RaDoFao56(unittest.TestCase):
    def test_exemplo_8_passos_do_caminho(self):
        self.assertAlmostEqual(clima.distancia_relativa_terra_sol(246), 0.985, delta=0.001)
        self.assertAlmostEqual(clima.declinacao_solar(246), 0.120, delta=0.001)
        self.assertAlmostEqual(clima.angulo_do_por_do_sol(-20.0, 246), 1.527, delta=0.001)

    def test_exemplo_8_ra_em_mj(self):
        self.assertAlmostEqual(clima.ra_mj(-20.0, 246), 32.2, delta=0.1)

    def test_exemplo_8_ra_em_mm(self):
        self.assertAlmostEqual(clima.mj_para_mm(clima.ra_mj(-20.0, 246)), 13.1, delta=0.05)

    def test_exemplo_20_ra_de_lyon(self):
        latitude = 45 + 43 / 60
        self.assertAlmostEqual(clima.ra_mj(latitude, 196), 40.55, delta=0.1)

    def test_dia_do_ano_de_3_de_setembro(self):
        # Tabela 2.5 do FAO-56 (anexo 2): 3 de setembro é o dia 246 (ano comum).
        self.assertEqual(clima.dia_do_ano(datetime.date(2015, 9, 3)), 246)


class EtoDeHargreaves(unittest.TestCase):
    def test_exemplo_20_hargreaves_com_a_ra_do_exemplo(self):
        ra_mm = clima.mj_para_mm(40.55)
        self.assertAlmostEqual(clima.eto_hargreaves(26.6, 14.8, ra_mm), 5.0, delta=0.05)

    def test_exemplo_20_de_ponta_a_ponta(self):
        latitude = 45 + 43 / 60
        ra_mm = clima.mj_para_mm(clima.ra_mj(latitude, 196))
        self.assertAlmostEqual(clima.eto_hargreaves(26.6, 14.8, ra_mm), 5.0, delta=0.05)

    def test_maxima_igual_a_minima_da_zero(self):
        self.assertEqual(clima.eto_hargreaves(20.0, 20.0, 15.0), 0.0)

    def test_maxima_menor_que_minima_e_erro(self):
        with self.assertRaises(ValueError):
            clima.eto_hargreaves(10.0, 20.0, 15.0)


class LeituraDaNasaPower(unittest.TestCase):
    def test_serie_guardada_comeca_em_2014_07_01_e_nao_tem_buraco(self):
        dias = clima.ler_serie()
        self.assertEqual(dias[0].data, datetime.date(2014, 7, 1))
        for anterior, atual in zip(dias, dias[1:]):
            self.assertEqual((atual.data - anterior.data).days, 1)
        self.assertGreaterEqual(dias[-1].data, datetime.date(2026, 10, 31))
        for d in dias:
            self.assertGreaterEqual(d.chuva, 0.0)
            self.assertGreater(d.eto, 0.0)

    def test_chuva_de_2025_bate_com_o_aviso_do_guia(self):
        # O guia avisa: a chuva de 2025 na NASA POWER soma 678 mm (suspeita de baixa).
        dias = clima.ler_serie()
        total = sum(d.chuva for d in dias if d.data.year == 2025)
        self.assertAlmostEqual(total, 678, delta=1)

    def test_dia_sem_dado_no_meio_e_erro_em_portugues(self):
        bruto = {"properties": {"parameter": {
            "PRECTOTCORR": {"20200101": 1.0, "20200102": -999.0, "20200103": 2.0},
            "T2M_MAX": {"20200101": 30.0, "20200102": 30.0, "20200103": 30.0},
            "T2M_MIN": {"20200101": 20.0, "20200102": 20.0, "20200103": 20.0}}},
            "geometry": {"coordinates": [-50.92, -17.79, 625.31]}}
        with self.assertRaises(ValueError) as erro:
            clima.serie_do_json(bruto, datetime.date(2020, 1, 1))
        self.assertIn("sem dado", str(erro.exception))

    def test_dias_sem_dado_no_fim_sao_cortados(self):
        bruto = {"properties": {"parameter": {
            "PRECTOTCORR": {"20200101": 1.0, "20200102": 3.0, "20200103": -999.0},
            "T2M_MAX": {"20200101": 30.0, "20200102": 30.0, "20200103": -999.0},
            "T2M_MIN": {"20200101": 20.0, "20200102": 20.0, "20200103": -999.0}}},
            "geometry": {"coordinates": [-50.92, -17.79, 625.31]}}
        dias = clima.serie_do_json(bruto, datetime.date(2020, 1, 1))
        self.assertEqual([d.data.day for d in dias], [1, 2])


if __name__ == "__main__":
    unittest.main()
