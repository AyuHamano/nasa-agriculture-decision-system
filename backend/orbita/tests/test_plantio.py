# Gerado com IA (Claude)
"""Testes da data do plantio da soja (o campo opcional `plantio_da_soja` da entrada)."""
import collections
import datetime
import unittest

from orbita import motor, parametros, rotacoes

D = datetime.date
ENTRADA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"],
           "prioridades": {"agua": 5, "solo": 4, "renda": 2, "erosao": 3}, "terra": "media"}
SEM_DATA = motor.responder(ENTRADA)
ATRASADA = motor.responder(dict(ENTRADA, plantio_da_soja="2026-11-20"))


def erro_de(entrada):
    with unittest.TestCase().assertRaises(ValueError) as erro:
        motor.validar_entrada(entrada)
    return str(erro.exception)


class Entrada(unittest.TestCase):
    def test_sem_a_data_vale_o_calendario_de_costume(self):
        self.assertIsNone(motor.validar_entrada(ENTRADA)["plantio_da_soja"])
        self.assertEqual(SEM_DATA["calendario"]["soja"]["plantio"], "15/10")
        self.assertEqual(SEM_DATA["calendario"]["deslocamento_dias"], 0)
        self.assertIsNone(SEM_DATA["calendario"]["plantio_da_soja_informado"])

    def test_a_data_de_costume_nao_muda_nenhum_numero(self):
        igual = motor.responder(dict(ENTRADA, plantio_da_soja="2025-10-15"))
        for chave in ("rotacoes", "comparacao", "veredito", "regra_dos_anos", "sede_forte"):
            self.assertEqual(igual[chave], SEM_DATA[chave], chave)

    def test_erros_em_portugues(self):
        for ruim in ("5 de novembro", "2026-13-01", "20/11/2026", 20261120):
            erro = erro_de(dict(ENTRADA, plantio_da_soja=ruim))
            self.assertTrue(erro.startswith("Entrada fora do formato:"), erro)
            self.assertIn("plantio_da_soja", erro)
            self.assertIn("2026-11-05", erro)          # o exemplo do formato
        fora = erro_de(dict(ENTRADA, plantio_da_soja="2026-03-10"))
        self.assertIn("1 de setembro a 31 de dezembro", fora)

    def test_as_pontas_da_janela_valem(self):
        for ponta in ("2026-09-01", "2026-12-31"):
            self.assertEqual(motor.validar_entrada(dict(ENTRADA, plantio_da_soja=ponta))["plantio_da_soja"], ponta)


class CalendarioQueAnda(unittest.TestCase):
    def test_a_soja_e_a_segunda_safra_andam_o_mesmo_numero_de_dias(self):
        cal = ATRASADA["calendario"]
        self.assertEqual(cal["plantio_da_soja_informado"], "2026-11-20")
        self.assertEqual(cal["deslocamento_dias"], 36)                  # de 15/10 a 20/11
        self.assertEqual(cal["soja"]["plantio"], "20/11")
        self.assertEqual(cal["milho"]["plantio"], "18/03")              # 10/02 mais 36 dias
        self.assertEqual(cal["entre_a_soja_e_o_milho_dias"], SEM_DATA["calendario"]["entre_a_soja_e_o_milho_dias"])
        self.assertEqual(cal["soja"]["ciclo_dias"], SEM_DATA["calendario"]["soja"]["ciclo_dias"])

    def test_os_dias_sem_planta_viva_nao_mudam_com_a_data(self):
        for rotacao in ("atual", "alternativa"):
            self.assertEqual(ATRASADA["rotacoes"][rotacao]["sem_planta_viva"]["dias_sem_planta_viva"],
                             SEM_DATA["rotacoes"][rotacao]["sem_planta_viva"]["dias_sem_planta_viva"])

    def test_plantar_tarde_muda_a_agua_da_segunda_safra(self):
        pior = SEM_DATA["comparacao"]["pior_ano"]
        antes = SEM_DATA["rotacoes"]["atual"]["safras"][pior]["milho"]["falta_mm"]
        depois = ATRASADA["rotacoes"]["atual"]["safras"][pior]["milho"]["falta_mm"]
        self.assertNotEqual(antes, depois)
        self.assertEqual(ATRASADA["rotacoes"]["atual"]["safras"][pior]["milho"]["dias"],
                         SEM_DATA["rotacoes"]["atual"]["safras"][pior]["milho"]["dias"])   # o ciclo é o mesmo

    def test_cada_dia_do_ano_tem_uma_cobertura_so_em_qualquer_data(self):
        par = parametros.carregar()
        for plantio in (None, "2026-09-01", "2026-11-20", "2026-12-31"):
            cal = rotacoes.calendario(par, plantio)
            for com_braquiaria in (False, True):
                conta = collections.Counter()
                dia = D(2021, 9, 1)
                while dia < D(2022, 9, 1):
                    conta[rotacoes.cobertura_do_dia(dia, com_braquiaria, cal)[0]] += 1
                    dia += datetime.timedelta(days=1)
                self.assertEqual(conta["soja"], cal.soja_ciclo, (plantio, com_braquiaria))
                self.assertEqual(conta["milho"], cal.milho_ciclo, (plantio, com_braquiaria))
                self.assertEqual(sum(conta.values()), 365)
                if com_braquiaria:
                    self.assertEqual(conta["sem_planta"], cal.dessecacao_dias + 3, plantio)   # 3: entre a soja e o milho

    def test_soja_plantada_cedo_a_segunda_safra_entra_em_dezembro(self):
        cal = rotacoes.calendario(parametros.carregar(), "2026-09-01")
        self.assertEqual(cal.plantio_do_milho(2022), D(2021, 12, 28))
        self.assertEqual(rotacoes.cobertura_do_dia(D(2021, 12, 30), False, cal)[0], "milho")
        self.assertEqual(rotacoes.cobertura_do_dia(D(2021, 12, 26), False, cal)[0], "sem_planta")


if __name__ == "__main__":
    unittest.main()
