# Gerado com IA (Claude).
"""Testes do verde visto pelo satélite (orbita/ndvi.py).

As séries daqui são pequenas e inventadas dentro do próprio teste, para o valor
esperado sair de conta feita à mão (escrita no comentário de cada teste). Só o
último grupo roda nos dados reais, e confere apenas a forma da resposta.

Rodar, de `backend/`: python3 -m unittest discover -s orbita/tests -t .
"""
import csv
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from orbita import conferencia, ndvi


def de_16_em_16(ano, quantas, inicio=(6, 10)):
    """As datas das medidas: de 16 em 16 dias a partir de 10 de junho.

    Com 13 medidas: 10/jun, 26/jun, 12/jul, 28/jul, 13/ago, 29/ago, 14/set,
    30/set, 16/out, 1/nov, 17/nov, 3/dez e 19/dez.
    """
    primeira = date(ano, *inicio)
    return [primeira + timedelta(days=16 * i) for i in range(quantas)]


def serie(ano, valores, inicio=(6, 10)):
    """Uma série boa inventada: [(data, ndvi)], uma medida a cada 16 dias."""
    return list(zip(de_16_em_16(ano, len(valores), inicio), valores))


def gravar_csv(pasta, nome, linhas, lat=-17.0, lon=-50.0):
    """Grava um CSV no formato dos dados reais. linhas: [(data, bruto, qualidade)]."""
    with (Path(pasta) / f"{nome}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "ndvi_bruto", "pixel_reliability", "item", "lat", "lon"])
        for d, bruto, qualidade in linhas:
            w.writerow([d.isoformat(), bruto, qualidade, "inventado", lat, lon])


def linhas_do_ano(ano, brutos, qualidades=None):
    datas = de_16_em_16(ano, len(brutos))
    qualidades = qualidades or [0] * len(brutos)
    return list(zip(datas, brutos, qualidades))


class Leitura(unittest.TestCase):
    def test_divide_por_10000_e_tira_o_que_nao_vale(self):
        # 5 linhas: boa (0), aceitável (1), neve (2), nuvem (3) e "sem dado" (-3000).
        # Só as duas primeiras valem: 5000 -> 0,5 e 3000 -> 0,3.
        with tempfile.TemporaryDirectory() as pasta:
            gravar_csv(pasta, "ponto", [
                (date(2021, 6, 10), 5000, 0),
                (date(2021, 6, 26), 3000, 1),
                (date(2021, 7, 12), 4000, 2),
                (date(2021, 7, 28), 8000, 3),
                (date(2021, 8, 13), -3000, 0),
            ], lat=-17.5, lon=-50.5)
            ponto = ndvi.ler_csv(Path(pasta) / "ponto.csv")
        self.assertEqual(ponto["boas"], [(date(2021, 6, 10), 0.5), (date(2021, 6, 26), 0.3)])
        self.assertEqual(ponto["medidas"], 5)
        self.assertEqual(ponto["ultima_data"], date(2021, 8, 13))
        self.assertEqual((ponto["lat"], ponto["lon"]), (-17.5, -50.5))

    def test_pasta_sem_csv_diz_o_que_falta(self):
        with tempfile.TemporaryDirectory() as pasta:
            with self.assertRaises(FileNotFoundError) as erro:
                ndvi.ler_pontos(pasta)
        self.assertIn("CSV", str(erro.exception))


class Limite(unittest.TestCase):
    def test_minimo_mais_20_por_cento_da_amplitude(self):
        # mínimo 0,2; máximo 0,9; amplitude 0,7. 0,2 + 0,20 x 0,7 = 0,34.
        self.assertAlmostEqual(ndvi.limite_sem_planta_verde([0.5, 0.2, 0.9]), 0.34)

    def test_a_fracao_e_trocavel(self):
        # 0,2 + 0,50 x 0,7 = 0,55.
        self.assertAlmostEqual(ndvi.limite_sem_planta_verde([0.5, 0.2, 0.9], fracao=0.5), 0.55)

    def test_serie_vazia_ou_fracao_fora_de_0_a_1_da_erro(self):
        with self.assertRaises(ValueError):
            ndvi.limite_sem_planta_verde([])
        with self.assertRaises(ValueError):
            ndvi.limite_sem_planta_verde([0.2, 0.9], fracao=1.5)


class DiasSeguidos(unittest.TestCase):
    def test_a_maior_sequencia_vezes_16(self):
        # Limite 0,34. Abaixo dele: 3 medidas seguidas (26/jun a 28/jul) e depois 1 (29/ago).
        # A maior sequência tem 3 medidas: 3 x 16 = 48 dias.
        s = serie(2021, [0.8, 0.3, 0.3, 0.3, 0.8, 0.3, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8])
        self.assertEqual(ndvi.dias_sem_planta_verde(s, 2021, 0.34), 48)

    def test_o_que_vem_antes_de_junho_nao_conta(self):
        # 9/mai e 25/mai abaixo do limite (não contam), 10/jun abaixo (1 medida), 26/jun verde,
        # 12/jul e 28/jul abaixo (2 medidas). A maior de junho em diante: 2 x 16 = 32 dias.
        # Se maio contasse, seriam 3 x 16 = 48.
        s = serie(2021, [0.25, 0.25, 0.25, 0.8, 0.3, 0.3, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8],
                  inicio=(5, 9))
        self.assertEqual(s[2][0], date(2021, 6, 10))
        self.assertEqual(ndvi.dias_sem_planta_verde(s, 2021, 0.34), 32)

    def test_igual_ao_limite_nao_e_abaixo(self):
        s = serie(2021, [0.34] * 13)
        self.assertEqual(ndvi.dias_sem_planta_verde(s, 2021, 0.34), 0)

    def test_so_conta_o_ano_pedido(self):
        # 2020 inteiro abaixo (13 medidas), 2021 inteiro verde: 2021 dá zero.
        s = serie(2020, [0.2] * 13) + serie(2021, [0.8] * 13)
        self.assertEqual(ndvi.dias_sem_planta_verde(s, 2020, 0.34), 13 * 16)
        self.assertEqual(ndvi.dias_sem_planta_verde(s, 2021, 0.34), 0)


class AnoCompleto(unittest.TestCase):
    def setUp(self):
        self.datas = de_16_em_16(2021, 13)
        self.fim = date(2022, 12, 19)  # a série segue no ano seguinte

    def test_serie_inteira_e_completa(self):
        self.assertEqual(ndvi.situacao_do_ano(self.datas, 2021, self.fim), ("completo", ""))

    def test_uma_medida_faltando_ainda_e_completo(self):
        # Sem 28/jul: de 12/jul a 13/ago são 32 dias. "Mais de 32" não aconteceu.
        datas = [d for d in self.datas if d != date(2021, 7, 28)]
        self.assertEqual(ndvi.situacao_do_ano(datas, 2021, self.fim)[0], "completo")

    def test_duas_medidas_faltando_tiram_o_ano(self):
        # Sem 28/jul e 13/ago: de 12/jul a 29/ago são 48 dias.
        datas = [d for d in self.datas if d not in (date(2021, 7, 28), date(2021, 8, 13))]
        situacao, motivo = ndvi.situacao_do_ano(datas, 2021, self.fim)
        self.assertEqual(situacao, "de_fora")
        self.assertIn("48 dias", motivo)
        self.assertIn("2021-07-12", motivo)
        self.assertIn("2021-08-29", motivo)

    def test_comeco_tarde_tira_o_ano(self):
        # A primeira medida em 12/jul: 41 dias depois de 1/jun.
        situacao, motivo = ndvi.situacao_do_ano(self.datas[2:], 2021, self.fim)
        self.assertEqual(situacao, "de_fora")
        self.assertIn("41 dias", motivo)

    def test_comeco_em_26_de_junho_ainda_vale(self):
        # A primeira medida em 26/jun: 25 dias depois de 1/jun.
        self.assertEqual(ndvi.situacao_do_ano(self.datas[1:], 2021, self.fim)[0], "completo")

    def test_fim_cedo_com_a_serie_seguindo_tira_o_ano(self):
        # A última medida boa em 17/nov: 44 dias até 31/dez, e a série continua em 2022.
        situacao, motivo = ndvi.situacao_do_ano(self.datas[:11], 2021, self.fim)
        self.assertEqual(situacao, "de_fora")
        self.assertIn("44 dias", motivo)

    def test_ano_sem_medida_fica_de_fora(self):
        situacao, motivo = ndvi.situacao_do_ano([], 2021, self.fim)
        self.assertEqual(situacao, "de_fora")
        self.assertIn("nenhuma medida boa", motivo)

    def test_serie_que_acaba_em_outubro_e_ano_em_andamento(self):
        # A série inteira acaba em 16/out/2021 (76 dias antes de 31/dez): o ano não fechou.
        datas = self.datas[:9]
        situacao, motivo = ndvi.situacao_do_ano(datas, 2021, date(2021, 10, 16))
        self.assertEqual(situacao, "em_andamento")
        self.assertIn("2021-10-16", motivo)
        self.assertIn("76 dias", motivo)


class ResumoInventado(unittest.TestCase):
    """Dois pontos inventados, com a conta inteira feita à mão.

    Ponto "a" (mínimo 0,2; máximo 1,0; limite 0,2 + 0,20 x 0,8 = 0,36):
      2020: 0,8 | 0,2 0,2 0,2 0,2 | 0,5 | 0,3 0,3 | 0,8 ...   -> 4 medidas = 64 dias
      2021: 0,8 0,8 | 0,3 x 6 | 0,8 ...                        -> 6 medidas = 96 dias
      2022: só 10/jun, 26/jun, 17/nov, 3/dez e 19/dez          -> buraco de 144 dias: de fora
      2023: até 16/out, as 3 últimas abaixo                    -> em andamento: 48 dias, ainda aberto
    Ponto "b" (mínimo 0,1; máximo 0,9; limite 0,1 + 0,20 x 0,8 = 0,26):
      2020: 0,9 | 0,1 0,1 | 0,9 ...                            -> 2 medidas = 32 dias
      2021: tudo 0,9                                           -> 0 dias
      2022: 0,9 | 0,1 | (nuvem, 0,95) | 0,1 0,1 | 0,9 ...      -> 3 medidas = 48 dias
      2023: até 16/out, 0,9 | 0,1 0,1 | 0,9 ...                -> em andamento: 32 dias, fechado
    Anos completos: 64, 96, 32, 0, 48 -> em ordem 0, 32, 48, 64, 96 -> mediana 48.
    Com a fração 0,50: limites 0,6 e 0,5; o 0,5 do ponto "a" em 2020 passa a contar:
      4 + 1 + 2 = 7 medidas = 112 dias.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pasta = self._tmp.name
        a = []
        a += linhas_do_ano(2020, [8000, 2000, 2000, 2000, 2000, 5000, 3000, 3000,
                                  8000, 8000, 8000, 10000, 8000])
        a += linhas_do_ano(2021, [8000, 8000, 3000, 3000, 3000, 3000, 3000, 3000,
                                  8000, 8000, 8000, 8000, 8000])
        a += [(date(2022, 6, 10), 8000, 0), (date(2022, 6, 26), 8000, 0), (date(2022, 11, 17), 8000, 0),
              (date(2022, 12, 3), 8000, 0), (date(2022, 12, 19), 8000, 0)]
        a += linhas_do_ano(2023, [8000, 8000, 8000, 8000, 8000, 8000, 3000, 3000, 3000])
        b = []
        b += linhas_do_ano(2020, [9000, 1000, 1000] + [9000] * 10)
        b += linhas_do_ano(2021, [9000] * 13)
        b += linhas_do_ano(2022, [9000, 1000, 9500, 1000, 1000] + [9000] * 7 + [-3000],
                           [0, 0, 3, 0, 0] + [0] * 7 + [0])
        b += linhas_do_ano(2023, [9000, 1000, 1000] + [9000] * 6)
        gravar_csv(self.pasta, "a", a, lat=-17.1, lon=-50.1)
        gravar_csv(self.pasta, "b", b, lat=-17.2, lon=-50.2)
        self.resumo = ndvi.resumo(pasta=self.pasta)

    def tearDown(self):
        self._tmp.cleanup()

    def test_o_limite_de_cada_ponto(self):
        self.assertEqual(self.resumo["limites"], {"a": 0.36, "b": 0.26})
        self.assertEqual(self.resumo["pontos"]["b"]["maximo"], 0.9)   # a nuvem (0,95) ficou de fora
        self.assertEqual(self.resumo["pontos"]["b"]["minimo"], 0.1)   # o "sem dado" (-0,3) também
        self.assertEqual(self.resumo["pontos"]["b"]["medidas"], 48)
        self.assertEqual(self.resumo["pontos"]["b"]["medidas_boas"], 46)
        self.assertEqual(self.resumo["pontos"]["a"]["lat"], -17.1)

    def test_os_dias_por_ponto_e_ano(self):
        self.assertEqual(self.resumo["dias_sem_planta_verde"],
                         {"a": {"2020": 64, "2021": 96}, "b": {"2020": 32, "2021": 0, "2022": 48}})

    def test_mediana_menor_e_maior(self):
        self.assertEqual(self.resumo["quantos"], 5)
        self.assertEqual(self.resumo["mediana"], 48)
        self.assertEqual(self.resumo["menor"], 0)
        self.assertEqual(self.resumo["maior"], 96)

    def test_os_anos_de_fora_e_o_porque(self):
        fora = self.resumo["anos_de_fora"]
        self.assertEqual([(f["ano"], f["pontos"]) for f in fora], [(2022, ["a"])])
        self.assertIn("144 dias", fora[0]["motivo"])
        self.assertIn("2022-06-26", fora[0]["motivo"])
        self.assertIn("2022-11-17", fora[0]["motivo"])

    def test_o_ano_em_andamento_fica_a_parte(self):
        andamento = self.resumo["ano_em_andamento"]
        self.assertEqual(andamento["ano"], 2023)
        self.assertEqual(andamento["ultima_medida"], "2023-10-16")
        self.assertEqual(andamento["dias_ate_a_ultima_medida"], {"a": 48, "b": 32})
        self.assertEqual(andamento["ainda_sem_planta_verde_na_ultima_medida"], ["a"])
        self.assertNotIn("2023", self.resumo["dias_sem_planta_verde"]["a"])

    def test_a_fracao_trocada_muda_o_limite_e_os_dias(self):
        r = ndvi.resumo(fracao=0.5, pasta=self.pasta)
        self.assertEqual(r["limites"], {"a": 0.6, "b": 0.5})
        self.assertEqual(r["dias_sem_planta_verde"]["a"]["2020"], 112)
        self.assertEqual(r["regra"]["fracao"], 0.5)

    def test_a_mesma_entrada_da_a_mesma_saida(self):
        self.assertEqual(self.resumo, ndvi.resumo(pasta=self.pasta))


class Comparacao(unittest.TestCase):
    RESUMO = {"mediana": 96, "menor": 16, "maior": 160, "quantos": 36}

    def test_a_diferenca_e_calendario_menos_satelite(self):
        # 120 pelo calendário, 96 pelo satélite: 120 - 96 = 24. Mais que 16, dentro de 16 a 160.
        c = ndvi.comparar_com_calendario(120, self.RESUMO)
        self.assertEqual(c["diferenca"], 24)
        self.assertEqual(c["leitura"], "dentro_da_faixa")
        for pedaco in ("120", "96", "24", "a mais"):
            self.assertIn(pedaco, c["frase"])

    def test_ate_uma_medida_de_diferenca_bate(self):
        # 100 - 96 = 4 dias; 84 - 96 = -12 dias: os dois cabem numa medida (16 dias).
        self.assertEqual(ndvi.comparar_com_calendario(100, self.RESUMO)["leitura"], "bate")
        c = ndvi.comparar_com_calendario(84, self.RESUMO)
        self.assertEqual(c["diferenca"], -12)
        self.assertEqual(c["leitura"], "bate")
        self.assertIn("a menos", c["frase"])

    def test_fora_da_faixa(self):
        # 200 - 96 = 104, e 200 passa do maior (160).
        c = ndvi.comparar_com_calendario(200, self.RESUMO)
        self.assertEqual(c["diferenca"], 104)
        self.assertEqual(c["leitura"], "fora_da_faixa")

    def test_a_frase_so_tem_numeros_da_propria_resposta(self):
        for dias in (0, 84, 100, 120, 200, 97.5):
            c = ndvi.comparar_com_calendario(dias, self.RESUMO)
            self.assertEqual(conferencia.conferir_texto(c["frase"], c), [], c["frase"])

    def test_a_frase_nao_diz_terra_descoberta_como_fato(self):
        c = ndvi.comparar_com_calendario(120, self.RESUMO)
        self.assertIn("sem planta verde", c["frase"])
        self.assertIn("palha", c["aviso"])

    def test_sem_ano_completo_nao_inventa_diferenca(self):
        c = ndvi.comparar_com_calendario(120, {"mediana": None, "menor": None, "maior": None, "quantos": 0})
        self.assertIsNone(c["diferenca"])
        self.assertEqual(c["leitura"], "sem_medida")

    def test_entrada_errada_da_erro_em_portugues(self):
        for errado in (-5, "cem", None, True):
            with self.assertRaises(ValueError):
                ndvi.comparar_com_calendario(errado, self.RESUMO)


class DadosReais(unittest.TestCase):
    """Só a forma da resposta: os números reais não ficam fixados aqui."""

    @classmethod
    def setUpClass(cls):
        cls.resumo = ndvi.resumo()

    def test_as_chaves(self):
        for chave in ("fonte", "aviso", "aviso_dos_pontos", "regra", "limites", "pontos", "dias_sem_planta_verde",
                      "quantos", "mediana", "menor", "maior", "anos_de_fora", "ano_em_andamento"):
            self.assertIn(chave, self.resumo)

    def test_os_6_pontos_e_os_limites(self):
        nomes = ["leste", "noroeste", "norte", "oeste", "sudoeste", "sul"]
        self.assertEqual(sorted(self.resumo["limites"]), nomes)
        self.assertEqual(sorted(self.resumo["dias_sem_planta_verde"]), nomes)
        for nome in nomes:
            ponto = self.resumo["pontos"][nome]
            self.assertTrue(0 < ponto["minimo"] < ponto["limite"] < ponto["maximo"] <= 1)
            self.assertEqual(self.resumo["limites"][nome], ponto["limite"])

    def test_os_dias_sao_multiplos_de_16(self):
        todos = [d for anos in self.resumo["dias_sem_planta_verde"].values() for d in anos.values()]
        self.assertEqual(len(todos), self.resumo["quantos"])
        self.assertGreater(len(todos), 0)
        for d in todos:
            self.assertIsInstance(d, int)
            self.assertEqual(d % 16, 0)
            self.assertTrue(0 <= d <= 224)   # de junho a dezembro cabem 14 medidas
        self.assertEqual(self.resumo["menor"], min(todos))
        self.assertEqual(self.resumo["maior"], max(todos))
        self.assertTrue(self.resumo["menor"] <= self.resumo["mediana"] <= self.resumo["maior"])

    def test_2024_e_2025_ficam_de_fora_com_o_motivo(self):
        fora = {f["ano"]: f for f in self.resumo["anos_de_fora"]}
        for ano in (2024, 2025):
            self.assertIn(ano, fora)
            self.assertTrue(fora[ano]["motivo"])
            self.assertEqual(len(fora[ano]["pontos"]), 6)
            for anos in self.resumo["dias_sem_planta_verde"].values():
                self.assertNotIn(str(ano), anos)

    def test_a_fonte_e_o_aviso(self):
        self.assertIn("MOD13Q1", self.resumo["fonte"]["produto"])
        self.assertTrue(self.resumo["fonte"]["link"].startswith("https://"))
        self.assertIn("sem planta verde", self.resumo["aviso"])
        self.assertIn("palha", self.resumo["aviso"])
        self.assertIn(self.resumo["regra"]["etiqueta_da_fracao"], ("publicado", "hipótese"))

    def test_vira_json(self):
        self.assertEqual(json.loads(json.dumps(self.resumo, ensure_ascii=False)), self.resumo)


if __name__ == "__main__":
    unittest.main()
