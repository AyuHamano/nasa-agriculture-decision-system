# Gerado com IA (Claude)
"""Os 7 achados da revisão da outra IA (GPT, 2026-11-15, 01h25), cada um com o teste que falhava antes do conserto.

A resposta da revisão ficou com a coordenação do projeto (respostas-das-ias/2026-11-15-0125-revisar-gpt-sol.md).
"""
import datetime
import json
import os
import pathlib
import shutil
import tempfile
import unittest
from unittest import mock

from orbita import balanco, clima, conferencia, motor, parametros

D = datetime.date
ENTRADA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media"}
SERIE = clima.ler_serie_com_aviso("imerg")


def cortada(ate):
    """A série guardada de Rio Verde cortada num dia: imita o dado que ainda não chegou."""
    dias, avisos = SERIE
    return mock.patch.object(motor, "_serie", lambda entrada: ([d for d in dias if d.data <= ate], list(avisos)))


class DadoQueAindaNaoChegou(unittest.TestCase):
    def test_1_o_registro_nao_quebra_quando_a_safra_mais_recente_nao_chegou_a_segunda_safra(self):
        with cortada(D(2026, 1, 31)):                       # a safra 2025-26 só tem a soja
            antigo = motor.registro_da_safra(ENTRADA, "2015-16")
            parcial = motor.registro_da_safra(ENTRADA, "2025-26")
        entre = antigo["entre_as_safras_guardadas"]
        self.assertEqual(entre["de"], 10)                   # só as safras em que a 2ª safra fechou o ciclo
        self.assertNotIn("2025-26", entre["por_safra_pct"])
        self.assertIsNone(parcial["entre_as_safras_guardadas"]["posicao"])
        self.assertFalse(parcial["periodo"]["completa"])
        self.assertEqual([p["cultura"] for p in parcial["o_que_foi_plantado"]], ["soja"])
        self.assertEqual(conferencia.conferir_texto(parcial["frase"], parcial), [])

    def test_2_nao_ha_marco_de_colheita_com_a_cultura_ainda_crescendo(self):
        with cortada(D(2016, 5, 15)):                       # o milho de 2016 sai da terra em junho
            replay = motor.replay_da_safra(ENTRADA, "2015-16")
        colheitas = [m["cultura"] for m in replay["marcos"] if m["tipo"] == "colheita"]
        self.assertEqual(colheitas, ["soja"])
        self.assertFalse(replay["resumo"]["milho"]["ciclo_completo"])
        self.assertTrue(replay["resumo"]["soja"]["ciclo_completo"])
        self.assertTrue(any("milho" in aviso and "ciclo" in aviso for aviso in replay["avisos"]))
        inteiro = motor.replay_da_safra(ENTRADA, "2015-16")
        self.assertEqual([m["cultura"] for m in inteiro["marcos"] if m["tipo"] == "colheita"], ["soja", "milho"])

    def test_7_safra_sem_o_ultimo_dia_nao_e_completa(self):
        with cortada(D(2016, 8, 30)):                       # 365 dias, mas falta 31 de agosto (ano bissexto)
            replay = motor.replay_da_safra(ENTRADA, "2015-16")
        self.assertEqual(len(replay["dias"]), 365)
        self.assertFalse(replay["completa"])
        self.assertTrue(motor.replay_da_safra(ENTRADA, "2015-16")["completa"])
        self.assertTrue(motor.replay_da_safra(ENTRADA, "2016-17")["completa"])

    def test_safra_sem_nenhum_dia_guardado_e_erro_em_portugues(self):
        with cortada(D(2025, 8, 31)):
            with self.assertRaises(ValueError) as erro:
                motor.replay_da_safra(ENTRADA, "2025-26")
        self.assertTrue(str(erro.exception).startswith("Entrada fora do formato:"))


class ArquivoAtualizado(unittest.TestCase):
    def test_3_o_clima_e_lido_de_novo_quando_o_arquivo_muda(self):
        origem = clima.pastas_da_cidade("jatai")
        with tempfile.TemporaryDirectory() as pasta:
            pasta = pathlib.Path(pasta)
            shutil.copy(origem["nasa_power"] / "resposta.json", pasta / "resposta.json")
            shutil.copy(origem["chuva"] / "imerg.csv", pasta / "imerg.csv")
            antes = clima.ler_serie(pasta)
            com_chuva = clima._serie_com_aviso("imerg", str(pasta), str(pasta), "X", clima.marca_dos_arquivos(
                pasta / "resposta.json", pasta / "imerg.csv"))[0]
            bruto = json.loads((pasta / "resposta.json").read_text(encoding="utf-8"))
            for serie in bruto["properties"]["parameter"].values():       # tira os 5 últimos dias da temperatura
                for dia in sorted(serie)[-5:]:
                    del serie[dia]
            (pasta / "resposta.json").write_text(json.dumps(bruto), encoding="utf-8")
            linhas = (pasta / "imerg.csv").read_text(encoding="utf-8").splitlines()
            (pasta / "imerg.csv").write_text("\n".join(linhas[:-400]) + "\n", encoding="utf-8")   # e 400 da chuva
            for arquivo in (pasta / "resposta.json", pasta / "imerg.csv"):
                os.utime(arquivo, ns=(os.stat(arquivo).st_atime_ns, os.stat(arquivo).st_mtime_ns + 5_000_000_000))
            depois = clima.ler_serie(pasta)
            com_chuva_depois = clima._serie_com_aviso("imerg", str(pasta), str(pasta), "X", clima.marca_dos_arquivos(
                pasta / "resposta.json", pasta / "imerg.csv"))[0]
        self.assertLess(len(depois), len(antes))            # os últimos dias do arquivo podem estar sem dado: não são 5
        self.assertLess(depois[-1].data, antes[-1].data)
        self.assertLess(com_chuva_depois[-1].data, com_chuva[-1].data)


class NumerosDaComparacao(unittest.TestCase):
    def test_4_os_dias_sem_planta_viva_no_ano_contam_o_intervalo_entre_a_soja_e_a_segunda_safra(self):
        resposta = motor.responder(ENTRADA)
        itens = {item["id"]: item for item in resposta["comparacao_das_rotacoes"]}
        for ident, rotacao, seguidos in (("soja_milho_pousio", ["soja", "milho", "pousio"], 122),
                                         ("soja_milho_braquiaria", ["soja", "milho", "braquiaria"], 30),
                                         ("soja_sorgo_pousio", ["soja", "sorgo"], 122)):
            terra = itens[ident]["terra_coberta"]
            replay = motor.replay_da_safra(dict(ENTRADA, rotacao_atual=rotacao), "2016-17")       # ano de 365 dias
            contados = sum(1 for dia in replay["dias"] if dia["cultura"] == "sem_planta")
            self.assertEqual(terra["dias_sem_planta_viva"], seguidos, ident)                      # o campo de sempre
            self.assertEqual(terra["dias_sem_planta_viva_no_ano"], contados, ident)
            self.assertEqual(terra["dias_sem_planta_viva_no_ano"], seguidos + 3, ident)
            self.assertEqual(resposta["terra_coberta"]["por_rotacao"][ident]["dias_sem_planta_viva_no_ano"], contados)
            self.assertNotIn("dias por ano sem planta viva", itens[ident]["evidencia"])
            self.assertIn(f"{seguidos} dias seguidos sem planta viva", itens[ident]["evidencia"])
            self.assertIn(f"{contados} dias no ano", itens[ident]["evidencia"])
            for frase in ("evidencia", "beneficio", "risco", "falta_saber"):
                self.assertNotIn("dias por ano", itens[ident][frase])
                self.assertEqual(conferencia.conferir_texto(itens[ident][frase], resposta), [])

    def test_5_a_posicao_no_registro_sai_dos_numeros_sem_arredondar(self):
        entrada = dict(ENTRADA, terra="pouca", plantio_da_soja="2026-09-09")
        a, b = motor.registro_da_safra(entrada, "2023-24"), motor.registro_da_safra(entrada, "2017-18")
        entre_a, entre_b = a["entre_as_safras_guardadas"], b["entre_as_safras_guardadas"]
        self.assertEqual(entre_a["falta_da_2a_safra_pct"], entre_b["falta_da_2a_safra_pct"])     # iguais no arredondado
        self.assertLess(entre_a["posicao"], entre_b["posicao"])       # 14,6445% é mais falta que 14,6006%
        self.assertEqual(entre_a["empatadas"], [])

    def test_6_a_margem_da_comparacao_vale_sobre_os_numeros_sem_arredondar(self):
        par = parametros.carregar()
        dias = SERIE[0]
        pior = motor.responder(ENTRADA)["comparacao"]["pior_ano"]

        def falta(segunda):
            numeros = balanco.numeros_por_safra(balanco.simular(dias, False, par, "media", segunda=segunda))
            return numeros[pior]["total"]["falta_mm"]

        exata = falta("milho") - falta("sorgo")
        arredondada = round(falta("milho"), 1) - round(falta("sorgo"), 1)
        self.assertGreater(abs(exata - arredondada), 0.001)           # o arredondamento mexe na diferença
        margem = (exata + arredondada) / 2                            # uma margem entre as duas diferenças
        par["regras"]["empate_mm"]["valor"] = margem
        itens = {item["id"]: item for item in motor.responder(ENTRADA, par=par)["comparacao_das_rotacoes"]}
        esperado = "melhor" if exata >= margem else "empate"
        self.assertEqual(itens["soja_sorgo_pousio"]["contra_as_outras"]["soja_milho_pousio"]["agua"], esperado)
        self.assertEqual(itens["soja_milho_pousio"]["contra_as_outras"]["soja_sorgo_pousio"]["agua"],
                         {"melhor": "pior", "empate": "empate"}[esperado])


if __name__ == "__main__":
    unittest.main()
