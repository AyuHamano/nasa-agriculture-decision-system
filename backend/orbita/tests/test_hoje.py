# Gerado com IA (Claude)
"""Testes do "como está hoje": a chuva recente guardada, a série esticada e o retrato do último dia com dado."""
import datetime
import json
import pathlib
import tempfile
import unittest

from orbita import clima, conferencia, hoje, motor

D = datetime.date
ENTRADA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media"}
DIA_DO_TESTE = D(2026, 11, 15)
RETRATO = motor.como_esta_hoje(ENTRADA, hoje=DIA_DO_TESTE)


class ChuvaRecente(unittest.TestCase):
    def test_cada_cidade_tem_a_chuva_recente_com_o_endereco_e_a_hora(self):
        for cidade in motor.CIDADES:
            valores, fonte = hoje.ler_chuva_recente(cidade)
            self.assertGreater(len(valores), 30, cidade)
            # Desde 2026-11-15 a chuva recente é a chuva do dia: o GPM IMERG em mm (o Late e, onde falta, o Early).
            bruto = json.loads((hoje.PASTA_DA_CHUVA_DO_DIA / cidade / "fonte.json").read_text(encoding="utf-8"))
            self.assertAlmostEqual(bruto["ponto"]["latitude"], motor.CIDADES[cidade]["latitude"])
            for consulta in bruto["consultas"]:
                self.assertTrue(consulta["endereco"].startswith("https://dynamical-nasa-imerg.s3"), cidade)
                self.assertTrue(consulta["hora_utc"])
            self.assertEqual((fonte["licenca"], fonte["citacao"]), ("CC BY 4.0", "NASA IMERG from dynamical.org"))
            self.assertIn(fonte["versao_do_ultimo_dia"], ("late", "early"))
            self.assertGreater(len(hoje.ler_chuva_da_cor(cidade)[0]), 30, cidade)      # a leitura da cor fica guardada

    def test_a_chuva_do_dia_vale_o_late_e_onde_falta_o_early_e_dia_em_branco_nao_vira_zero(self):
        with tempfile.TemporaryDirectory() as pasta:
            (pathlib.Path(pasta) / "x").mkdir()
            (pathlib.Path(pasta) / "x" / "chuva-do-dia.csv").write_text(
                "data,chuva_early_mm,chuva_late_mm\n2026-11-12,2.87,3.22\n2026-11-13,0.00,0.00\n"
                "2026-11-14,23.67,\n2026-11-15,,\n", encoding="utf-8")
            valores, fonte = hoje.ler_chuva_recente("x", pathlib.Path(pasta))
        self.assertEqual(valores, {D(2026, 11, 12): 3.22, D(2026, 11, 13): 0.0, D(2026, 11, 14): 23.67,
                                   D(2026, 11, 15): None})
        self.assertEqual((fonte["ultimo_dia_com_dado"], fonte["versao_do_ultimo_dia"],
                          fonte["ultimo_dia_da_versao_late"]), ("2026-11-14", "early", "2026-11-13"))

    def test_esticar_para_no_primeiro_dia_sem_dado_e_nunca_poe_zero(self):
        dia = lambda data, chuva: clima.Dia(data, chuva, 30.0, 20.0, 4.0)  # noqa: E731
        guardados = [dia(D(2026, 9, 13), 1.0), dia(D(2026, 9, 14), 2.0)]
        temperatura = [dia(D(2026, 9, 13) + datetime.timedelta(days=i), 9.0) for i in range(8)]
        recente = {D(2026, 9, 14): 99.0, D(2026, 9, 15): 5.0, D(2026, 9, 16): 0.0, D(2026, 9, 17): None,
                   D(2026, 9, 18): 7.0}
        com_recente, com_modelo = hoje.esticar(guardados, temperatura, recente)
        self.assertEqual([d.data.day for d in com_recente], [13, 14, 15, 16])       # parou no dia 17, em branco
        self.assertEqual([d.chuva for d in com_recente], [1.0, 2.0, 5.0, 0.0])      # o dia guardado não é trocado
        self.assertEqual([d.chuva for d in com_modelo], [1.0, 2.0, 9.0, 9.0])
        self.assertEqual(len(hoje.esticar(guardados, temperatura, {})[0]), 2)       # sem chuva recente, não estica


class Retrato(unittest.TestCase):
    def test_devolve_o_ultimo_dia_o_atraso_a_agua_e_as_comparacoes(self):
        self.assertTrue(RETRATO["disponivel"])
        ultimo = D.fromisoformat(RETRATO["ultimo_dia_com_dado"])
        self.assertEqual(RETRATO["hoje"], "2026-11-15")
        self.assertEqual(RETRATO["atraso_dias"], (DIA_DO_TESTE - ultimo).days)
        self.assertGreater(ultimo, D(2026, 9, 14))                     # foi além da chuva guardada
        self.assertLessEqual(RETRATO["atraso_dias"], 10)
        self.assertEqual(RETRATO["safra"], "2026-27")
        self.assertTrue(0 <= RETRATO["agua_na_terra_mm"] <= RETRATO["agua_que_a_terra_segura_mm"])
        for chave in ("no_ano_normal", "no_pior_ano"):
            outro = RETRATO[chave]
            data = D.fromisoformat(outro["data"])
            self.assertEqual((data.month, data.day), (ultimo.month, ultimo.day))
            self.assertEqual(outro["diferenca_mm"], round(RETRATO["agua_na_terra_mm"] - outro["agua_na_terra_mm"], 1))
        resposta = motor.responder(ENTRADA)
        self.assertEqual(RETRATO["no_pior_ano"]["safra"], resposta["comparacao"]["pior_ano"])
        self.assertEqual(RETRATO["no_ano_normal"]["safra"], resposta["comparacao"]["ano_normal"])
        self.assertTrue(RETRATO["aviso"])
        json.dumps(RETRATO, ensure_ascii=False)

    def test_a_chuva_recente_vai_com_a_de_modelo_ao_lado_e_a_faixa(self):
        chuva, faixa = RETRATO["chuva_recente"], RETRATO["faixa_da_agua_na_terra_mm"]
        self.assertEqual(chuva["de"], "2026-09-15")
        self.assertEqual(chuva["ate"], RETRATO["ultimo_dia_com_dado"])
        self.assertGreater(chuva["satelite_rapido_mm"], 0)
        self.assertGreater(chuva["modelo_da_nasa_power_mm"], 0)
        # Desde 2026-11-15 a água sai como um número só (a conta com a chuva do dia): a faixa tem as duas pontas
        # iguais, a conta com a chuva de modelo fica ao lado só para comparar, e a frase diz até onde vai a chuva.
        self.assertEqual(faixa, {"de": RETRATO["agua_na_terra_mm"], "ate": RETRATO["agua_na_terra_mm"]})
        self.assertIn("agua_na_terra_mm", RETRATO["com_a_chuva_de_modelo"])
        self.assertNotIn("modelo", RETRATO["frase"])
        # Desde 2026-11-15 (a leitura do produtor) até onde vai a chuva fica no detalhe técnico, não na frase.
        self.assertIn(f"vai até {hoje.data_br(chuva['fonte']['ultimo_dia_com_dado'])}", RETRATO["detalhe_tecnico"])
        self.assertIn("chuva-do-dia", chuva["origem"])

    def test_cada_ultimo_dia_com_dado_diz_de_qual_dado_e(self):
        # Na mesma resposta há duas datas com esse nome: a da conta (precisa da temperatura e da chuva) e a da chuva
        # rápida do satélite sozinha, que pode ir além (em 2026-11-15: 11/11/2026 e 13/11/2026).
        da_chuva = RETRATO["chuva_recente"]["fonte"]
        self.assertEqual(RETRATO["ultimo_dia_com_dado_de"], hoje.DIA_DA_CONTA)
        self.assertEqual(da_chuva["ultimo_dia_com_dado_de"], hoje.DIA_DA_CHUVA_RAPIDA)
        self.assertIn("temperatura", hoje.DIA_DA_CONTA)
        self.assertTrue(hoje.DIA_DA_CHUVA_RAPIDA.startswith("só da chuva rápida do satélite"))
        self.assertGreaterEqual(da_chuva["ultimo_dia_com_dado"], RETRATO["ultimo_dia_com_dado"])
        temperatura = clima.ler_serie(clima.pastas_da_cidade("rio_verde")["nasa_power"])
        chuva, _ = hoje.ler_chuva_recente("rio_verde")
        com_chuva = max(dia for dia, mm in chuva.items() if mm is not None and dia <= DIA_DO_TESTE)
        self.assertEqual(da_chuva["ultimo_dia_com_dado"], com_chuva.isoformat())
        # Desde 2026-11-15 a conta segue até o último dia com chuva do satélite: onde a temperatura ainda não chegou,
        # o consumo é o do tempo dos 7 dias anteriores, e a resposta diz qual é o último dia com temperatura.
        com_temperatura = min(com_chuva, temperatura[-1].data)
        self.assertEqual(RETRATO["ultimo_dia_com_dado"], com_chuva.isoformat())
        self.assertEqual(RETRATO["ultimo_dia_com_temperatura"], com_temperatura.isoformat())
        self.assertEqual(RETRATO["dias_com_o_consumo_estimado"], (com_chuva - com_temperatura).days)
        self.assertEqual(RETRATO["janela_do_consumo_dias"], 7)
        self.assertEqual(RETRATO["com_a_chuva_de_modelo"]["data"], com_temperatura.isoformat())
        if RETRATO["dias_com_o_consumo_estimado"]:
            self.assertEqual(RETRATO["consumo_estimado_desde"], (com_temperatura + datetime.timedelta(days=1)).isoformat())
            self.assertIn("o consumo da cultura é o dos 7 dias anteriores", RETRATO["detalhe_tecnico"])

    def test_a_conta_segue_ate_o_ultimo_dia_com_chuva_com_o_tempo_dos_7_dias_anteriores(self):
        dia = lambda n, tmax, eto: clima.Dia(D(2026, 11, 1) + datetime.timedelta(days=n), 1.0, tmax, 20.0, eto)  # noqa: E731
        serie = [dia(n, 30.0 + n, 4.0 + n) for n in range(10)]                    # a temperatura vai até 10/11
        chuva = {D(2026, 11, 10): 99.0, D(2026, 11, 11): 12.5, D(2026, 11, 12): 0.0, D(2026, 11, 13): None,
                 D(2026, 11, 14): 30.0}
        seguida, estimados = hoje.seguir_com_a_chuva(serie, chuva)
        self.assertEqual(estimados, [D(2026, 11, 11), D(2026, 11, 12)])           # para no dia 13, em branco
        self.assertEqual(seguida[:10], serie)                                     # o que já havia não muda
        self.assertEqual([d.chuva for d in seguida[10:]], [12.5, 0.0])            # a chuva de verdade do satélite
        for novo in seguida[10:]:                                                 # o tempo médio dos últimos 7 dias
            self.assertAlmostEqual(novo.tmax, sum(30.0 + n for n in range(3, 10)) / 7)
            self.assertAlmostEqual(novo.eto, sum(4.0 + n for n in range(3, 10)) / 7)
            self.assertAlmostEqual(novo.tmin, 20.0)
        self.assertEqual(hoje.seguir_com_a_chuva(serie, chuva, ate=D(2026, 11, 11))[1], [D(2026, 11, 11)])
        self.assertEqual(hoje.seguir_com_a_chuva(serie, {}), (serie, []))

    def test_a_frase_so_tem_numero_da_conta(self):
        self.assertEqual(conferencia.conferir_texto(RETRATO["frase"], RETRATO), [])
        self.assertIn("Rio Verde", RETRATO["frase"])

    def test_segue_a_cidade_a_rotacao_e_a_data_do_produtor(self):
        outro = motor.como_esta_hoje({"cidade_id": "jatai", "rotacao_atual": ["soja", "sorgo"],
                                      "plantio_da_soja": "2026-11-20"}, hoje=DIA_DO_TESTE)
        self.assertEqual(outro["rotacao"]["id"], "soja_sorgo_pousio")
        self.assertEqual(outro["local"]["id"], "jatai")
        self.assertEqual(outro["o_que_esta_na_terra"], "sem_planta")     # a soja dele só entra em 20 de novembro
        self.assertEqual(RETRATO["o_que_esta_na_terra"], "soja")         # no calendário de costume, entrou em 15/10

    def test_sem_a_chuva_recente_guardada_diz_o_que_falta(self):
        with tempfile.TemporaryDirectory() as pasta:
            vazio = hoje.como_esta_hoje(ENTRADA, hoje=DIA_DO_TESTE, pasta_da_chuva_recente=pathlib.Path(pasta))
        self.assertFalse(vazio["disponivel"])
        self.assertIn("baixar_chuva_do_dia.py", vazio["aviso"])

    def test_entrada_errada_e_erro_em_portugues(self):
        with self.assertRaises(ValueError) as erro:
            motor.como_esta_hoje(dict(ENTRADA, cidade_id="sorriso"))
        self.assertTrue(str(erro.exception).startswith("Entrada fora do formato:"))


class ALeituraDoProdutor(unittest.TestCase):
    """A rodada do alinhamento (decisão do dono, 2026-11-15): a frase leva só a data do dado, o aviso é a linha
    curta, e o que saiu fica em `detalhe_tecnico` e `aviso_tecnico` (a leitura do agrônomo)."""

    def test_a_frase_e_o_aviso_nao_tratam_a_data_como_defeito(self):
        self.assertEqual(RETRATO["aviso"], "Converse com o agrônomo antes de decidir.")
        self.assertEqual(RETRATO["aviso_tecnico"], hoje.AVISO)
        self.assertIn(f"em {hoje.data_br(RETRATO['ultimo_dia_com_dado'])}", RETRATO["frase"])
        for termo in ("aproximad", "atraso", "ainda não entrou", "ainda não chegou", "último dia com dado",
                      "dia desta consulta"):
            self.assertNotIn(termo, RETRATO["frase"], termo)
            self.assertNotIn(termo, RETRATO["aviso"], termo)

    def test_o_que_saiu_da_frase_esta_no_detalhe_tecnico(self):
        detalhe = RETRATO["detalhe_tecnico"]
        self.assertIn(f"O último dia com dado é {hoje.data_br(RETRATO['ultimo_dia_com_dado'])}", detalhe)
        self.assertIn(f"dia desta consulta ({hoje.data_br(DIA_DO_TESTE)})", detalhe)
        self.assertEqual(conferencia.conferir_texto(detalhe, RETRATO), [])


if __name__ == "__main__":
    unittest.main()
