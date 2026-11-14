# Gerado com IA (Claude)
"""Testes do balanço da água na terra (FAO-56, cap. 8: https://www.fao.org/4/X0490E/x0490e0e.htm).

Os valores esperados dos testes "na mão" saem das fórmulas do FAO-56 feitas no papel, não do código:
- TAW = 100 mm, p = 0,5 (RAW = 50 mm), a planta pede 5 mm por dia, sem chuva, terra cheia no começo:
  dias 1 a 11 sem freio (a falta acumulada na terra passa de 50 só no fim do dia 11, com 55 mm);
  no dia 12, Ks = (100 - 55) / ((1 - 0,5) x 100) = 0,9 (eq. 84) e a planta bebe 4,5 mm.
- O ajuste de p pela demanda (cap. 8): p = p da tabela + 0,04 x (5 - ETc); com ETc = 3, p = 0,58.
"""
import datetime
import unittest

from orbita import balanco, clima, parametros


def dias_iguais(n, chuva, eto, inicio=datetime.date(2020, 1, 1)):
    return [clima.Dia(inicio + datetime.timedelta(days=i), chuva, 30.0, 20.0, eto) for i in range(n)]


def sempre_soja(_data):
    return ("soja", 1.0, 0.5)


def sempre_sem_planta(_data):
    return (balanco.SEM_PLANTA, 1.0, None)


def falta_total(registros):
    return sum(r.pedido - r.bebido for r in registros if r.tipo in balanco.CULTURAS)


class ContaNaMao(unittest.TestCase):
    def test_freio_da_sede_no_dia_12(self):
        r = balanco.balanco_diario(dias_iguais(12, 0.0, 5.0), sempre_soja, taw=100.0, tew=20.0, rew=8.0,
                                   ajustar_p=False, fracao_inicial=1.0)
        self.assertTrue(all(x.ks == 1.0 for x in r[:11]))
        self.assertAlmostEqual(r[9].agua_na_terra, 50.0)
        self.assertAlmostEqual(r[10].agua_na_terra, 45.0)
        self.assertAlmostEqual(r[11].ks, 0.9)
        self.assertAlmostEqual(r[11].bebido, 4.5)
        self.assertAlmostEqual(r[11].agua_na_terra, 40.5)

    def test_ajuste_de_p_pela_demanda(self):
        r = balanco.balanco_diario(dias_iguais(22, 0.0, 3.0), sempre_soja, taw=100.0, tew=20.0, rew=8.0,
                                   ajustar_p=True, fracao_inicial=1.0)
        self.assertEqual(r[19].ks, 1.0)             # começou o dia com 57 mm de falta, abaixo de 58
        self.assertAlmostEqual(r[20].ks, 40 / 42)   # começou com 60: Ks = (100 - 60) / (0,42 x 100)

    def test_a_chuva_que_passa_de_encher_se_perde(self):
        r = balanco.balanco_diario(dias_iguais(3, 30.0, 5.0), sempre_soja, taw=100.0, tew=20.0, rew=8.0,
                                   ajustar_p=False, fracao_inicial=1.0)
        self.assertAlmostEqual(r[0].percolacao, 25.0)
        self.assertAlmostEqual(r[0].agua_na_terra, 100.0)

    def test_a_agua_nao_some_nem_aparece(self):
        # Em cada dia: água de hoje = água de ontem (na caixa de hoje) + chuva - bebido - o que escorreu para baixo.
        r = balanco.simular(clima.ler_serie()[:800], com_braquiaria=True)
        for ontem, hoje in zip(r, r[1:]):
            antes = ontem.agua_na_terra / ontem.taw * hoje.taw
            self.assertAlmostEqual(antes + hoje.chuva - hoje.bebido - hoje.percolacao, hoje.agua_na_terra, places=6)

    def test_cada_cobertura_com_a_sua_raiz(self):
        par = parametros.carregar()
        agua = balanco.agua_da_terra(par, "media")
        por_metro = parametros.valor(par, "terra", "media", "agua_mm_por_m")
        self.assertAlmostEqual(agua["taw"]["soja"], por_metro * parametros.valor(par, "culturas", "soja", "raiz_m"))
        self.assertEqual(agua["taw"][balanco.SEM_PLANTA], max(agua["taw"].values()))
        r = balanco.balanco_diario(dias_iguais(3, 0.0, 5.0), sempre_soja, taw={"soja": 80.0, "milho": 50.0,
                                   "braquiaria": 100.0, "sem_planta": 100.0}, tew=20.0, rew=8.0, fracao_inicial=1.0)
        self.assertAlmostEqual(r[2].agua_na_terra, 65.0)
        self.assertEqual(r[2].taw, 80.0)


class Propriedades(unittest.TestCase):
    def test_com_chuva_de_sobra_a_falta_e_zero(self):
        # Terra cheia no começo: o freio do dia olha a água do fim do dia anterior (a chuva do dia entra depois).
        r = balanco.balanco_diario(dias_iguais(200, 50.0, 6.0), sempre_soja, taw=130.0, tew=17.5, rew=8.0,
                                   fracao_inicial=1.0)
        self.assertEqual(falta_total(r), 0.0)
        self.assertTrue(all(x.ks == 1.0 for x in r))

    def test_sem_chuva_a_falta_cresce(self):
        r = balanco.balanco_diario(dias_iguais(120, 0.0, 5.0), sempre_soja, taw=130.0, tew=17.5, rew=8.0,
                                   fracao_inicial=1.0)
        acumulada, anterior = 0.0, 0.0
        for x in r:
            acumulada += x.pedido - x.bebido
            self.assertGreaterEqual(acumulada, anterior)
            anterior = acumulada
        self.assertGreater(acumulada, 300.0)  # pediu 600 mm e a terra só tinha 130
        self.assertLess(sum(x.bebido for x in r), 130.0 + 1e-9)

    def test_serie_real_sem_chuva_tem_mais_falta_que_com_chuva(self):
        dias = clima.ler_serie()
        secos = [d._replace(chuva=0.0) for d in dias]
        self.assertGreater(falta_total(balanco.simular(secos, False)), falta_total(balanco.simular(dias, False)))

    def test_terra_que_segura_menos_nunca_mostra_falta_menor_na_secagem(self):
        faltas = [falta_total(balanco.balanco_diario(dias_iguais(150, 0.0, 5.0), sempre_soja, taw=t, tew=17.5,
                                                     rew=8.0, fracao_inicial=1.0)) for t in (90.0, 130.0, 160.0)]
        self.assertGreaterEqual(faltas[0], faltas[1])
        self.assertGreaterEqual(faltas[1], faltas[2])

    def test_terra_que_segura_menos_nunca_mostra_falta_menor_na_serie_real(self):
        dias = clima.ler_serie()
        for com_braquiaria in (False, True):
            por_terra = []
            for terra in ("pouca", "media", "muita"):
                safras = balanco.numeros_por_safra(balanco.simular(dias, com_braquiaria, terra=terra))
                por_terra.append(sum(safras[s]["total"]["falta_mm"] for s in balanco.SAFRAS_DO_ESTUDO))
            self.assertGreaterEqual(por_terra[0], por_terra[1])
            self.assertGreaterEqual(por_terra[1], por_terra[2])

    def test_a_mesma_entrada_da_a_mesma_saida(self):
        dias = clima.ler_serie()
        self.assertEqual(balanco.simular(dias, True), balanco.simular(dias, True))

    def test_o_comeco_da_simulacao_nao_muda_as_safras_do_estudo(self):
        dias = clima.ler_serie()
        for com_braquiaria in (False, True):
            cheia = balanco.simular(dias, com_braquiaria, fracao_inicial=1.0)
            vazia = balanco.simular(dias, com_braquiaria, fracao_inicial=0.0)
            for a, b in zip(cheia, vazia):
                if a.data >= datetime.date(2015, 9, 1):
                    self.assertAlmostEqual(a.agua_na_terra, b.agua_na_terra, places=6)

    def test_terra_sem_planta_evapora_mas_so_a_camada_de_cima(self):
        r = balanco.balanco_diario(dias_iguais(90, 0.0, 5.0), sempre_sem_planta, taw=130.0, tew=17.5, rew=8.0,
                                   fracao_inicial=1.0)
        evaporado = sum(x.bebido for x in r)
        self.assertGreater(evaporado, 8.0)
        self.assertLessEqual(evaporado, 17.5 + 1e-9)

    def test_a_braquiaria_bebe_agua(self):
        safras = balanco.numeros_por_safra(balanco.simular(clima.ler_serie(), True))
        for s in balanco.SAFRAS_DO_ESTUDO:
            self.assertGreater(safras[s]["braquiaria"]["bebido_mm"], 0.0)


class NumerosPorSafra(unittest.TestCase):
    def test_nome_da_safra(self):
        self.assertEqual(balanco.nome_da_safra(datetime.date(2015, 9, 1)), "2015-16")
        self.assertEqual(balanco.nome_da_safra(datetime.date(2016, 8, 31)), "2015-16")
        self.assertEqual(balanco.nome_da_safra(datetime.date(1999, 12, 1)), "1999-00")

    def test_as_10_safras_do_estudo(self):
        self.assertEqual(len(balanco.SAFRAS_DO_ESTUDO), 10)
        self.assertEqual(balanco.SAFRAS_DO_ESTUDO[0], "2015-16")
        self.assertEqual(balanco.SAFRAS_DO_ESTUDO[-1], "2024-25")

    def test_falta_dias_de_sede_e_falta_relativa(self):
        r = balanco.balanco_diario(dias_iguais(12, 0.0, 5.0), sempre_soja, taw=100.0, tew=20.0, rew=8.0,
                                   ajustar_p=False, fracao_inicial=1.0)
        s = balanco.numeros_por_safra(r)["2019-20"]
        self.assertAlmostEqual(s["soja"]["pedido_mm"], 60.0)
        self.assertAlmostEqual(s["soja"]["falta_mm"], 0.5)
        self.assertEqual(s["soja"]["dias_de_sede"], 1)
        self.assertAlmostEqual(s["soja"]["falta_relativa_pct"], 100 * 0.5 / 60.0)
        self.assertAlmostEqual(s["total"]["falta_mm"], 0.5)


if __name__ == "__main__":
    unittest.main()
