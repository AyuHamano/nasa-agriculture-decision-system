#!/usr/bin/env python3
# Gerado com IA (Claude). Órbita Rural (NASA Space Apps 2026).
"""Teste do ler.py. Sem internet e sem biblioteca de fora.

Como rodar (da raiz do repositório):  python3 -I data/orbita/chuva-do-dia/test_ler.py
"""
import datetime
import pathlib
import sys
import tempfile
import unittest

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import ler  # noqa: E402

D = datetime.date
ARQUIVO_DE_TESTE = ("data,chuva_early_mm,chuva_late_mm\n"
                    "2026-11-10,0.00,0.00\n"
                    "2026-11-11,7.10,2.24\n"
                    "2026-11-12,,3.22\n"
                    "2026-11-13,1.50,\n"
                    "2026-11-14,,\n")


class LerUmArquivoDeTeste(unittest.TestCase):
    def setUp(self):
        self.temporaria = tempfile.TemporaryDirectory()
        self.pasta = pathlib.Path(self.temporaria.name)
        (self.pasta / "cidade_de_teste").mkdir()
        (self.pasta / "cidade_de_teste" / ler.ARQUIVO).write_text(ARQUIVO_DE_TESTE, encoding="utf-8")

    def tearDown(self):
        self.temporaria.cleanup()

    def test_o_late_vale_onde_existe_e_o_early_onde_o_late_ainda_nao_chegou(self):
        chuva = ler.chuva_por_dia("cidade_de_teste", pasta=self.pasta)
        self.assertEqual(chuva, {D(2026, 11, 10): 0.0, D(2026, 11, 11): 2.24, D(2026, 11, 12): 3.22,
                                 D(2026, 11, 13): 1.5, D(2026, 11, 14): None})

    def test_cada_versao_sozinha(self):
        early = ler.chuva_por_dia("cidade_de_teste", "early", self.pasta)
        late = ler.chuva_por_dia("cidade_de_teste", "late", self.pasta)
        self.assertEqual(early[D(2026, 11, 11)], 7.1)
        self.assertEqual(late[D(2026, 11, 11)], 2.24)
        self.assertIsNone(early[D(2026, 11, 12)])
        self.assertIsNone(late[D(2026, 11, 13)])

    def test_dia_em_branco_vira_none_e_zero_continua_zero(self):
        chuva = ler.chuva_por_dia("cidade_de_teste", pasta=self.pasta)
        self.assertIsNone(chuva[D(2026, 11, 14)])
        self.assertEqual(chuva[D(2026, 11, 10)], 0.0)
        self.assertIsNotNone(chuva[D(2026, 11, 10)])

    def test_o_ultimo_dia_com_dado_de_cada_versao(self):
        self.assertEqual(ler.ultimo_dia_com_dado("cidade_de_teste", pasta=self.pasta), D(2026, 11, 13))
        self.assertEqual(ler.ultimo_dia_com_dado("cidade_de_teste", "early", self.pasta), D(2026, 11, 13))
        self.assertEqual(ler.ultimo_dia_com_dado("cidade_de_teste", "late", self.pasta), D(2026, 11, 12))

    def test_as_linhas_saem_na_ordem_das_datas(self):
        (self.pasta / "cidade_de_teste" / ler.ARQUIVO).write_text(
            "data,chuva_early_mm,chuva_late_mm\n2026-11-12,1.00,\n2026-11-10,2.00,\n", encoding="utf-8")
        self.assertEqual([l["data"] for l in ler.ler_linhas("cidade_de_teste", self.pasta)],
                         [D(2026, 11, 10), D(2026, 11, 12)])

    def test_cidade_sem_arquivo_devolve_none(self):
        self.assertIsNone(ler.ler_linhas("nao_existe", self.pasta))
        self.assertIsNone(ler.chuva_por_dia("nao_existe", pasta=self.pasta))
        self.assertIsNone(ler.ultimo_dia_com_dado("nao_existe", pasta=self.pasta))
        self.assertIsNone(ler.ficha_da_fonte("nao_existe", self.pasta))

    def test_versao_desconhecida_e_recusada(self):
        with self.assertRaises(ValueError):
            ler.chuva_por_dia("cidade_de_teste", "final", self.pasta)


class OsArquivosGuardados(unittest.TestCase):
    """O que está guardado no repositório: três cidades, datas sem buraco, sem valor negativo, com a fonte."""

    def test_as_tres_cidades(self):
        for cidade in ("rio_verde", "jatai", "silvania"):
            with self.subTest(cidade=cidade):
                linhas = ler.ler_linhas(cidade)
                self.assertIsNotNone(linhas, "rode o baixar_chuva_do_dia.py")
                self.assertGreaterEqual(len(linhas), 90)
                datas = [l["data"] for l in linhas]
                self.assertEqual(datas, [datas[0] + datetime.timedelta(days=n) for n in range(len(datas))])
                for l in linhas:
                    for versao in ("early", "late"):
                        self.assertTrue(l[versao] is None or l[versao] >= 0.0)
                ficha = ler.ficha_da_fonte(cidade)
                self.assertEqual(ficha["licenca"], "CC BY 4.0")
                self.assertIn("dynamical.org", ficha["de_onde_vem"])
                self.assertEqual(ficha["ultimo_dia_com_dado"], ler.ultimo_dia_com_dado(cidade, "early").isoformat())
                self.assertTrue(all(c.get("hora_utc") and c.get("endereco") for c in ficha["consultas"]))

    def test_o_total_de_rio_verde_bate_com_o_teste_de_2026_11_15(self):
        """De 01/09 a 30/10/2026 (60 dias), o teste da chuva recente registrou Early 353,0 mm e Late 347,4 mm."""
        dias = [D(2026, 9, 1) + datetime.timedelta(days=n) for n in range(60)]
        early, late = ler.chuva_por_dia("rio_verde", "early"), ler.chuva_por_dia("rio_verde", "late")
        self.assertAlmostEqual(sum(early[d] for d in dias), 353.0, delta=0.05)
        self.assertAlmostEqual(sum(late[d] for d in dias), 347.4, delta=0.05)


if __name__ == "__main__":
    unittest.main()
