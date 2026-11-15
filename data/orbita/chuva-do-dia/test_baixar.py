#!/usr/bin/env python3
# Gerado com IA (Claude). Órbita Rural (NASA Space Apps 2026).
"""Teste das contas do baixar_chuva_do_dia.py (a regra do dia, de onde recomeçar, como juntar). Sem internet e sem as
quatro bibliotecas: elas só são chamadas na hora de baixar.

Como rodar (da raiz do repositório):  python3 -I data/orbita/chuva-do-dia/test_baixar.py
"""
import ast
import datetime
import pathlib
import sys
import unittest

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import baixar_chuva_do_dia as baixar  # noqa: E402

D = datetime.date
DT = datetime.datetime
MEIA = datetime.timedelta(minutes=30)
UM_MM_POR_HORA = 1.0 / 3600.0               # em mm por segundo


def meias_horas(inicio, quantas, taxa=UM_MM_POR_HORA):
    return [(inicio + n * MEIA, taxa) for n in range(quantas)]


class ARegraDoDia(unittest.TestCase):
    def test_a_meia_hora_das_02h30_utc_e_do_dia_anterior_em_brasilia(self):
        self.assertEqual(baixar.dia_de_brasilia(DT(2026, 11, 15, 2, 30)), D(2026, 11, 14))
        self.assertEqual(baixar.dia_de_brasilia(DT(2026, 11, 15, 3, 0)), D(2026, 11, 15))
        self.assertEqual(baixar.dia_de_brasilia(DT(2026, 11, 14, 3, 0)), D(2026, 11, 14))

    def test_48_meias_horas_a_1_mm_por_hora_dao_24_mm(self):
        dias = baixar.somar_por_dia(meias_horas(DT(2026, 11, 14, 3, 0), 48))
        self.assertEqual(dias, {D(2026, 11, 14): 24.0})

    def test_dia_com_menos_de_48_meias_horas_fica_em_branco(self):
        dias = baixar.somar_por_dia(meias_horas(DT(2026, 11, 14, 3, 0), 48 + 6))     # o dia 15 só tem 6
        self.assertEqual(dias[D(2026, 11, 14)], 24.0)
        self.assertIsNone(dias[D(2026, 11, 15)])

    def test_meia_hora_vazia_deixa_o_dia_em_branco_e_nao_vira_zero(self):
        meias = meias_horas(DT(2026, 11, 14, 3, 0), 48)
        meias[10] = (meias[10][0], None)
        self.assertIsNone(baixar.somar_por_dia(meias)[D(2026, 11, 14)])

    def test_a_chuva_da_noite_fica_no_dia_certo(self):
        """Chuva só das 21h00 às 23h59 de Brasília do dia 14 (00:00 a 02:59 UTC do dia 15): é do dia 14."""
        meias = [(inicio, UM_MM_POR_HORA if DT(2026, 11, 15, 0, 0) <= inicio < DT(2026, 11, 15, 3, 0) else 0.0)
                 for inicio, _ in meias_horas(DT(2026, 11, 14, 3, 0), 96)]
        dias = baixar.somar_por_dia(meias)
        self.assertEqual(dias[D(2026, 11, 14)], 3.0)
        self.assertEqual(dias[D(2026, 11, 15)], 0.0)


class DeOndeRecomecar(unittest.TestCase):
    HOJE = D(2026, 11, 15)

    def linhas(self, primeiro, ultimo, sem_late=1):
        dias = [primeiro + datetime.timedelta(days=n) for n in range((ultimo - primeiro).days + 1)]
        return [{"data": d, "early": 1.0, "late": None if d > ultimo - datetime.timedelta(days=sem_late) else 1.0}
                for d in dias]

    def test_sem_arquivo_baixa_90_dias(self):
        self.assertEqual(baixar.desde_quando(None, self.HOJE), D(2026, 8, 17))
        self.assertEqual(baixar.desde_quando([], self.HOJE), D(2026, 8, 17))

    def test_com_arquivo_refaz_os_ultimos_3_dias(self):
        linhas = self.linhas(D(2026, 8, 17), D(2026, 11, 14))
        self.assertEqual(baixar.desde_quando(linhas, self.HOJE), D(2026, 11, 12))

    def test_dia_em_branco_mais_antigo_puxa_o_comeco_para_tras(self):
        linhas = self.linhas(D(2026, 8, 17), D(2026, 11, 14))
        linhas[60]["late"] = None                                                   # 16/10 sem o Late
        self.assertEqual(baixar.desde_quando(linhas, self.HOJE), D(2026, 10, 16))

    def test_buraco_com_mais_de_90_dias_nao_e_buscado_de_novo(self):
        linhas = self.linhas(D(2026, 6, 1), D(2026, 11, 14))
        linhas[0]["early"] = None                                                   # 01/06, fora dos 90 dias
        self.assertEqual(baixar.desde_quando(linhas, self.HOJE), D(2026, 11, 12))


class JuntarOQueChegou(unittest.TestCase):
    def test_acrescenta_os_dias_novos_corrige_os_ultimos_e_deixa_hoje_fora(self):
        antes = [{"data": D(2026, 11, 10), "early": 5.0, "late": 4.0},
                 {"data": D(2026, 11, 11), "early": 7.0, "late": 2.0},
                 {"data": D(2026, 11, 12), "early": 3.0, "late": None}]
        novos = {"early": {D(2026, 11, 10): 99.0, D(2026, 11, 11): 7.1, D(2026, 11, 12): 2.9, D(2026, 11, 13): 0.0,
                           D(2026, 11, 14): 23.7, D(2026, 11, 15): None},
                 "late": {D(2026, 11, 11): 2.2, D(2026, 11, 12): 3.2, D(2026, 11, 13): 0.0, D(2026, 11, 14): None}}
        saida = baixar.juntar(antes, novos, D(2026, 11, 11), D(2026, 11, 15))
        self.assertEqual(saida, [
            {"data": D(2026, 11, 10), "early": 5.0, "late": 4.0},            # antes do começo: não muda
            {"data": D(2026, 11, 11), "early": 7.1, "late": 2.2},            # corrigido
            {"data": D(2026, 11, 12), "early": 2.9, "late": 3.2},            # o Late chegou
            {"data": D(2026, 11, 13), "early": 0.0, "late": 0.0},            # dia novo
            {"data": D(2026, 11, 14), "early": 23.7, "late": None}])         # ontem: o Late ainda não chegou

    def test_valor_novo_em_branco_nao_apaga_o_que_ja_estava(self):
        antes = [{"data": D(2026, 11, 13), "early": 1.5, "late": 1.0}]
        saida = baixar.juntar(antes, {"early": {D(2026, 11, 13): None}, "late": {}}, D(2026, 11, 13), D(2026, 11, 14))
        self.assertEqual(saida, [{"data": D(2026, 11, 13), "early": 1.5, "late": 1.0}])

    def test_dia_que_faltou_entra_em_branco_e_a_lista_nao_tem_buraco(self):
        saida = baixar.juntar(None, {"early": {D(2026, 11, 12): 1.0, D(2026, 11, 14): 2.0}, "late": {}},
                              D(2026, 11, 12), D(2026, 11, 15))
        self.assertEqual([l["data"] for l in saida], [D(2026, 11, 12), D(2026, 11, 13), D(2026, 11, 14)])
        self.assertIsNone(saida[1]["early"])


class AsCidadesSaoAsDoMotor(unittest.TestCase):
    def test_as_coordenadas_sao_as_de_backend_orbita_motor(self):
        """Lê o dicionário CIDADES do motor sem importar o motor (só o texto do arquivo)."""
        motor = AQUI.parents[2] / "backend" / "orbita" / "motor.py"
        if not motor.exists():
            self.skipTest("o motor não está nesta cópia")
        for no in ast.parse(motor.read_text(encoding="utf-8")).body:
            if isinstance(no, ast.Assign) and getattr(no.targets[0], "id", None) == "CIDADES":
                self.assertEqual(ast.literal_eval(no.value), baixar.CIDADES)
                return
        self.fail("não achei CIDADES em backend/orbita/motor.py")


if __name__ == "__main__":
    unittest.main()
