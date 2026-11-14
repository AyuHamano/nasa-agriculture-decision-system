# Gerado com IA (Claude)
"""Testes do comando validar (a validação cruzada) e da correlação de postos (Spearman)."""
import datetime
import io
import tempfile
import unittest

from orbita import validar


class Postos(unittest.TestCase):
    def test_postos_com_empate(self):
        self.assertEqual(validar.postos([10, 20, 20, 5]), [2.0, 3.5, 3.5, 1.0])

    def test_spearman_nos_extremos(self):
        self.assertAlmostEqual(validar.spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(validar.spearman([1, 2, 3, 4], [9, 7, 5, 1]), -1.0)

    def test_spearman_na_mao(self):
        # x = 1..5 e y = 5, 6, 7, 8, 7. Postos de y: 1, 2, 3,5, 5, 3,5. Soma dos produtos dos desvios = 8;
        # somas dos quadrados = 10 e 9,5. Correlação = 8 / raiz(95) = 0,8208.
        self.assertAlmostEqual(validar.spearman([1, 2, 3, 4, 5], [5, 6, 7, 8, 7]), 0.8208, places=4)

    def test_sem_variacao_nao_tem_correlacao(self):
        self.assertIsNone(validar.spearman([1, 2, 3], [4, 4, 4]))


class Janela(unittest.TestCase):
    def test_dia_em_branco_nao_vira_zero_e_e_contado(self):
        d = datetime.date
        valores = {d(2020, 2, 1): 10.0, d(2020, 2, 2): None, d(2020, 2, 3): 5.0}
        soma, brancos = validar.soma_da_janela(valores, d(2020, 2, 1), d(2020, 2, 4))
        self.assertEqual(soma, 15.0)
        self.assertEqual(brancos, 2)   # o dia 2 (em branco) e o dia 4 (fora do arquivo)


class Comando(unittest.TestCase):
    def test_roda_com_os_dados_guardados(self):
        saida = io.StringIO()
        self.assertEqual(validar.main([], saida=saida), 0)
        texto = saida.getvalue()
        for trecho in ("1. A CHUVA", "2. A NASA POWER CONTRA A ESTAÇÃO", "3. A ETo", "4. A FALTA DE ÁGUA", "5. O NDVI",
                       "imerg", "correlação de postos"):
            self.assertIn(trecho, texto)
        self.assertNotIn("FALTA:", texto)

    def test_sem_os_arquivos_diz_o_que_falta_sem_quebrar(self):
        saida = io.StringIO()
        with tempfile.TemporaryDirectory() as pasta:
            self.assertEqual(validar.main([], pasta=pasta, saida=saida), 0)
        self.assertIn("FALTA:", saida.getvalue())
        self.assertIn("open-meteo.csv", saida.getvalue())
        self.assertIn("rendimento_rio_verde.csv", saida.getvalue())


if __name__ == "__main__":
    unittest.main()
