# Gerado com IA (Claude)
"""A conferência da chuva recente: a leitura da cor (NASA GIBS) ao lado do GPM IMERG Late em mm, de 5 em 5 dias."""
import csv
import datetime
import json
import tempfile
import unittest
from pathlib import Path

from orbita import hoje, motor

ENTRADA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"]}
DIA = datetime.date(2026, 9, 1)


def _pasta(linhas):
    pasta = Path(tempfile.mkdtemp())
    (pasta / "x").mkdir()
    (pasta / "x" / "chuva-5-dias.csv").write_text("inicio,fim,chuva_mm\n" + "".join(linhas), encoding="utf-8")
    return pasta


class ChuvaDe5Dias(unittest.TestCase):
    def test_soma_so_os_periodos_em_que_os_dois_existem(self):
        da_cor = {DIA + datetime.timedelta(days=n): 2.0 for n in range(15)}
        da_cor[DIA + datetime.timedelta(days=12)] = None                 # buraco no terceiro período
        pasta = _pasta(["2026-09-01,2026-09-05,12.5\n", "2026-09-06,2026-09-10,\n", "2026-09-11,2026-09-15,30\n"])
        saida = hoje.conferencia_em_mm("x", da_cor, pasta)
        self.assertEqual(saida["periodos_de_5_dias"], 1)                  # o 2º não tem mm; o 3º tem dia sem leitura
        self.assertEqual((saida["de"], saida["ate"]), ("2026-09-01", "2026-09-05"))
        self.assertEqual((saida["satelite_em_mm"], saida["satelite_lido_da_cor_mm"]), (12.5, 10.0))
        self.assertEqual(saida["diferenca_pct"], -20.0)

    def test_sem_arquivo_ou_sem_periodo_comum_nao_inventa(self):
        self.assertIsNone(hoje.conferencia_em_mm("x", {}, Path(tempfile.mkdtemp())))
        self.assertIsNone(hoje.conferencia_em_mm("x", {}, _pasta(["2026-09-01,2026-09-05,12.5\n"])))

    def test_os_arquivos_guardados_tem_a_fonte_ao_lado(self):
        for cidade in motor.CIDADES:
            pasta = hoje.PASTA_DA_CHUVA_RECENTE / cidade
            fonte = json.loads((pasta / "fonte-5-dias.json").read_text(encoding="utf-8"))
            with (pasta / "chuva-5-dias.csv").open(encoding="utf-8", newline="") as f:
                linhas = list(csv.DictReader(f))
            self.assertEqual(len(linhas), len(fonte["consultas"]), cidade)
            for linha, consulta in zip(linhas, fonte["consultas"]):
                self.assertTrue(consulta["endereco"].startswith("https://data.chc.ucsb.edu/products/EWX2/IMERGlatev7/"))
                self.assertTrue(consulta["consultado_em_utc"])
                self.assertEqual(linha["chuva_mm"] == "", consulta["chuva_mm"] is None)   # sem arquivo: em branco
                self.assertEqual(linha["chuva_mm"] == "", consulta["http"] != 200)

    def test_o_hoje_traz_a_conferencia_e_a_conta_nao_muda(self):
        for cidade in motor.CIDADES:
            resposta = motor.como_esta_hoje(dict(ENTRADA, cidade_id=cidade), hoje=datetime.date(2026, 11, 15))
            conferencia = resposta["chuva_recente"]["conferencia_em_mm"]
            self.assertGreaterEqual(conferencia["periodos_de_5_dias"], 10, cidade)
            self.assertLess(abs(conferencia["diferenca_pct"]), 15.0, cidade)   # a cor e o mm discordam menos de 15%
        rio_verde = motor.como_esta_hoje(ENTRADA, hoje=datetime.date(2026, 11, 15))
        self.assertEqual(rio_verde["chuva_recente"]["conferencia_em_mm"]["satelite_em_mm"], 437.2)
        self.assertEqual(rio_verde["chuva_recente"]["conferencia_em_mm"]["satelite_lido_da_cor_mm"], 397.8)
        self.assertEqual(rio_verde["chuva_recente"]["satelite_rapido_mm"], 411.0)   # a conta segue com a mesma chuva


if __name__ == "__main__":
    unittest.main()
