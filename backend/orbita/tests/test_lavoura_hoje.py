# Gerado com IA (Claude)
"""Testes do "a lavoura hoje": os seis itens do acompanhamento da safra (a fase, a água, o calor, o verde do satélite,
a terra coberta e o aviso de sede), com uma data fixa de "hoje" (2026-11-15) e só com os dados guardados."""
import contextlib
import datetime
import io
import json
import pathlib
import statistics
import tempfile
import threading
import unittest
import urllib.request

from orbita import api, balanco, calor, clima, conferencia, hoje, lavoura, motor, parametros, perguntar, rotacoes

D = datetime.date
UM_DIA = datetime.timedelta(days=1)
ENTRADA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media"}
DIA_DO_TESTE = D(2026, 11, 15)
PAINEL = motor.lavoura_hoje(ENTRADA, hoje=DIA_DO_TESTE)
RETRATO = motor.como_esta_hoje(ENTRADA, hoje=DIA_DO_TESTE)
ITENS = {item["id"]: item for item in PAINEL["itens"]}
ULTIMO = D.fromisoformat(PAINEL["ultimo_dia_com_dado"])                       # o último dia com chuva do satélite
ULTIMO_COM_TEMPERATURA = D.fromisoformat(PAINEL["ultimo_dia_com_temperatura"])  # o calor só conta até aqui
PAR = parametros.carregar()
CAL = rotacoes.calendario(PAR)


def registro(data, tipo="soja", ks=1.0, agua=30.0):
    return balanco.Registro(data, tipo, 0.0, 4.0, 3.0, 3.0 * ks, ks, agua, 0.0, 66.0, 0.0)


class OPainel(unittest.TestCase):
    def test_os_seis_itens_na_ordem_cada_um_com_situacao_regra_frase_e_ultimo_dado(self):
        self.assertTrue(PAINEL["disponivel"])
        self.assertEqual([item["id"] for item in PAINEL["itens"]],
                         ["fase", "agua", "calor", "verde", "terra_coberta", "aviso_de_sede"])
        self.assertEqual(tuple(item["id"] for item in PAINEL["itens"]), lavoura.ITENS)
        for item in PAINEL["itens"]:
            self.assertIn(item["situacao"], lavoura.SITUACOES, item["id"])
            self.assertEqual(item["situacao_nome"], lavoura.NOMES_DAS_SITUACOES[item["situacao"]])
            self.assertEqual(item["regra_da_situacao"], lavoura.REGRAS[item["id"]])
            self.assertTrue(item["titulo"] and item["frase"], item["id"])
            D.fromisoformat(item["ultimo_dado"]["data"])
            self.assertTrue(item["ultimo_dado"]["de"], item["id"])
        self.assertEqual(PAINEL["regras"], lavoura.REGRAS)
        self.assertEqual((PAINEL["hoje"], PAINEL["safra"]), ("2026-11-15", "2026-27"))
        self.assertEqual(PAINEL["atraso_dias"], (DIA_DO_TESTE - ULTIMO).days)
        self.assertTrue(PAINEL["frase"] and PAINEL["aviso"])
        json.dumps(PAINEL, ensure_ascii=False)

    def test_a_situacao_do_topo_e_a_pior_dos_itens_e_a_frase_diz_o_que_pede_atencao(self):
        peso = lavoura.PESO
        pior = max((item["situacao"] for item in PAINEL["itens"]), key=peso.get)
        self.assertEqual(PAINEL["situacao"], pior if peso[pior] else "tranquilo")
        self.assertIn("Rio Verde", PAINEL["frase"])
        self.assertIn(lavoura.data_br(ULTIMO), PAINEL["frase"])
        for item in PAINEL["itens"]:
            if item["situacao"] in ("atencao", "alerta"):
                self.assertIn(lavoura.NOMES_DOS_ITENS[item["id"]], PAINEL["frase"])
        self.assertEqual(lavoura.pior_situacao(["tranquilo", "sem_dado", "atencao"]), "atencao")
        self.assertEqual(lavoura.pior_situacao(["alerta", "atencao"]), "alerta")
        self.assertEqual(lavoura.pior_situacao(["sem_dado", "sem_dado"]), "tranquilo")

    def test_cada_frase_so_tem_numero_da_conta_e_data_do_jeito_brasileiro(self):
        self.assertEqual(conferencia.conferir_texto(PAINEL["frase"], PAINEL), [])
        for item in PAINEL["itens"]:
            self.assertEqual(conferencia.conferir_texto(item["frase"], item), [], item["id"])
            self.assertNotRegex(item["frase"], r"\d{4}-\d{2}-\d{2}", item["id"])      # nenhuma data em ano-mês-dia
            for termo in ("NDVI", "Ks", "Kc", "ETo", "TAW", "mediana", "MODIS"):
                self.assertNotIn(termo, item["frase"], item["id"])

    def test_as_tres_cidades_respondem_com_os_seis_itens(self):
        for cidade in motor.CIDADES:
            painel = motor.lavoura_hoje(dict(ENTRADA, cidade_id=cidade), hoje=DIA_DO_TESTE)
            self.assertTrue(painel["disponivel"], cidade)
            self.assertEqual(len(painel["itens"]), 6, cidade)
            self.assertEqual(conferencia.conferir_texto(painel["frase"], painel), [], cidade)
            for item in painel["itens"]:
                self.assertEqual(conferencia.conferir_texto(item["frase"], item), [], (cidade, item["id"]))

    def test_segue_a_rotacao_e_a_data_de_plantio_do_produtor(self):
        painel = motor.lavoura_hoje({"cidade_id": "jatai", "rotacao_atual": ["soja", "sorgo"],
                                     "plantio_da_soja": "2026-11-20"}, hoje=DIA_DO_TESTE)
        itens = {item["id"]: item for item in painel["itens"]}
        self.assertEqual(painel["rotacao"]["id"], "soja_sorgo_pousio")
        self.assertEqual(itens["fase"]["o_que_esta_na_terra"], "sem_planta")       # a soja dele só entra em 20/11
        self.assertEqual(itens["fase"]["proximo_plantio"], {"cultura": "soja", "data": "2026-11-20",
                                                            "faltam_dias": (D(2026, 11, 20) - ULTIMO).days})
        self.assertIn("20/11/2026", itens["fase"]["frase"])
        self.assertEqual(itens["terra_coberta"]["com_planta_viva"], False)
        self.assertEqual(itens["terra_coberta"]["situacao"], "atencao")
        self.assertIsNone(itens["calor"]["limite_c"])
        self.assertEqual((itens["aviso_de_sede"]["ja_com_sede"], itens["aviso_de_sede"]["dias_ate_a_sede"]), (False, None))
        for nome in ("fase", "agua", "calor", "aviso_de_sede"):
            self.assertEqual(itens[nome]["situacao"], "tranquilo", nome)
            self.assertEqual(conferencia.conferir_texto(itens[nome]["frase"], itens[nome]), [], nome)

    def test_sem_a_chuva_recente_guardada_diz_o_que_falta(self):
        with tempfile.TemporaryDirectory() as pasta:
            vazio = lavoura.lavoura_hoje(ENTRADA, hoje=DIA_DO_TESTE, pasta_da_chuva_recente=pathlib.Path(pasta))
        self.assertFalse(vazio["disponivel"])
        self.assertIn("baixar_chuva_do_dia.py", vazio["aviso"])

    def test_entrada_errada_e_erro_em_portugues(self):
        with self.assertRaises(ValueError) as erro:
            motor.lavoura_hoje(dict(ENTRADA, cidade_id="sorriso"))
        self.assertTrue(str(erro.exception).startswith("Entrada fora do formato:"))

    def test_o_como_esta_hoje_continua_com_os_campos_de_sempre(self):
        # Nenhum campo de antes saiu; os 4 a mais entraram quando a conta passou a seguir até o último dia de chuva.
        novos = ["ultimo_dia_com_temperatura", "dias_com_o_consumo_estimado", "consumo_estimado_desde",
                 "janela_do_consumo_dias"]
        self.assertEqual(sorted(RETRATO), sorted(novos + [
            "disponivel", "local", "rotacao", "terra", "plantio_da_soja_informado", "hoje", "ultimo_dia_com_dado",
            "ultimo_dia_com_dado_de", "atraso_dias", "safra", "o_que_esta_na_terra", "agua_na_terra_mm",
            "agua_que_a_terra_segura_mm", "agua_na_terra_pct", "com_sede", "chuva_desde_1_de_setembro_mm",
            "faixa_da_agua_na_terra_mm", "com_a_chuva_de_modelo", "no_ano_normal", "no_pior_ano", "chuva_recente",
            "frase", "aviso"]))


class AFase(unittest.TestCase):
    def test_a_fase_sai_do_calendario_e_das_fases_que_o_motor_ja_usa(self):
        # A soja de costume: plantio em 15/10, fases de 20, 20, 55 e 20 dias (a do meio é a fase crítica do motor).
        self.assertEqual(CAL.soja_fases, [20, 20, 55, 20])
        fase = lavoura.fase_no_dia(CAL, "milho", D(2026, 11, 11))
        self.assertEqual((fase["cultura"], fase["plantio"], fase["dias_desde_o_plantio"]), ("soja", "2026-10-15", 27))
        self.assertEqual((fase["fase"], fase["dia_da_fase"], fase["dias_da_fase"]), ("crescimento", 8, 20))
        self.assertEqual((fase["fase_critica"], fase["fase_critica_de"], fase["fase_critica_ate"]),
                         (False, "2026-11-24", "2027-01-17"))
        self.assertEqual(fase["dias_para_a_fase_critica"], 13)
        self.assertEqual((fase["fase_critica_de"], fase["fase_critica_ate"]), tuple(
            d.isoformat() for d in (calor.janela_critica(CAL, "soja", "2026-27")[0],
                                    calor.janela_critica(CAL, "soja", "2026-27")[1] - UM_DIA)))
        self.assertEqual(lavoura.fase_no_dia(CAL, "milho", D(2026, 10, 15))["fase"], "inicial")
        critica = lavoura.fase_no_dia(CAL, "milho", D(2026, 12, 1))
        self.assertEqual((critica["fase"], critica["fase_critica"], critica["dia_da_fase"]), ("critica", True, 8))
        self.assertEqual(lavoura.fase_no_dia(CAL, "milho", D(2027, 1, 20))["fase"], "final")
        milho = lavoura.fase_no_dia(CAL, "milho", D(2027, 3, 1))
        self.assertEqual((milho["cultura"], milho["plantio"], milho["dias_desde_o_plantio"], milho["fase"]),
                         ("milho", "2027-02-10", 19, "inicial"))
        self.assertEqual(lavoura.fase_no_dia(CAL, "sorgo", D(2027, 3, 1))["cultura"], "sorgo")
        self.assertIsNone(lavoura.fase_no_dia(CAL, "milho", D(2026, 8, 1)))            # o pousio: sem cultura
        self.assertEqual(lavoura.proximo_plantio(CAL, "milho", D(2026, 8, 1)),
                         {"cultura": "soja", "data": "2026-10-15", "faltam_dias": 75})
        self.assertEqual(lavoura.proximo_plantio(CAL, "milho", D(2027, 2, 8))["cultura"], "milho")

    def test_o_item_da_fase_no_dia_do_teste(self):
        item = ITENS["fase"]
        self.assertEqual(item["o_que_esta_na_terra"], RETRATO["o_que_esta_na_terra"])
        self.assertEqual((item["cultura"], item["plantio"]), ("soja", "2026-10-15"))
        self.assertEqual(item["dias_desde_o_plantio"], (ULTIMO - D(2026, 10, 15)).days)
        self.assertEqual(item["no_dia_da_consulta"], {"data": "2026-11-15", "dias_desde_o_plantio": 31,
                                                      "fase": "crescimento", "fase_critica": False})
        self.assertEqual(item["situacao"], "tranquilo")
        self.assertEqual(lavoura.situacao_da_fase(True), "atencao")
        self.assertEqual(lavoura.situacao_da_fase(False), "tranquilo")
        self.assertIn("15/10/2026", item["frase"])


class AAgua(unittest.TestCase):
    def test_os_numeros_da_agua_sao_os_do_como_esta_hoje(self):
        item = ITENS["agua"]
        for chave in ("agua_na_terra_mm", "agua_que_a_terra_segura_mm", "agua_na_terra_pct", "com_sede",
                      "faixa_da_agua_na_terra_mm", "chuva_desde_1_de_setembro_mm"):
            self.assertEqual(item[chave], RETRATO[chave], chave)
        for chave in ("no_ano_normal", "no_pior_ano"):
            for campo in ("safra", "data", "agua_na_terra_mm", "diferenca_mm", "leitura"):
                self.assertEqual(item[chave][campo], RETRATO[chave][campo], (chave, campo))
        self.assertEqual(item["com_a_chuva_de_modelo"]["agua_na_terra_mm"],
                         RETRATO["com_a_chuva_de_modelo"]["agua_na_terra_mm"])
        self.assertEqual(item["ultimo_dado"]["data"], RETRATO["ultimo_dia_com_dado"])
        if not item["com_sede"]:
            self.assertEqual(item["dias_seguidos_de_sede"], 0)

    def test_os_dias_seguidos_contam_para_tras_a_partir_do_ultimo_dia(self):
        dia = D(2026, 11, 1)
        linhas = [registro(dia, ks=0.5), registro(dia + UM_DIA, ks=1.0), registro(dia + 2 * UM_DIA, ks=0.9),
                  registro(dia + 3 * UM_DIA, ks=0.2)]
        self.assertEqual(lavoura.dias_seguidos(linhas, lavoura.com_sede), 2)
        self.assertEqual(lavoura.dias_seguidos(linhas[:2], lavoura.com_sede), 0)
        self.assertEqual(lavoura.dias_seguidos([registro(dia, "sem_planta", ks=0.1)], lavoura.com_sede), 0)

    def test_a_regra_da_situacao_da_agua(self):
        self.assertEqual(lavoura.situacao_da_agua(True, True), "alerta")
        self.assertEqual(lavoura.situacao_da_agua(True, False), "tranquilo")
        self.assertEqual(lavoura.situacao_da_agua(False, False), "tranquilo")             # sem cultura na terra
        self.assertEqual(ITENS["agua"]["faixa_da_agua_na_terra_mm"],                      # um número só
                         {"de": ITENS["agua"]["agua_na_terra_mm"], "ate": ITENS["agua"]["agua_na_terra_mm"]})
        self.assertEqual(ITENS["agua"]["chuva_do_satelite_ate"], RETRATO["chuva_recente"]["fonte"]["ultimo_dia_com_dado"])
        self.assertIn(lavoura.data_br(ITENS["agua"]["chuva_do_satelite_ate"]), ITENS["agua"]["frase"])


class OCalor(unittest.TestCase):
    def test_conta_os_dias_acima_do_limite_e_nao_inventa_dia_sem_temperatura(self):
        dia = D(2026, 11, 1)
        maximas = {dia: 40.0, dia + UM_DIA: 40.1, dia + 2 * UM_DIA: 35.0, dia + 3 * UM_DIA: 41.0}
        self.assertEqual(lavoura.dias_acima(maximas, dia, dia + 3 * UM_DIA, 40.0), 2)      # 40,0 não passa de 40
        self.assertEqual(lavoura.dias_acima(maximas, dia, dia, 40.0), 0)
        self.assertIsNone(lavoura.dias_acima(maximas, dia, dia + 4 * UM_DIA, 40.0))        # falta um dia

    def test_o_item_do_calor_bate_com_a_temperatura_guardada_e_com_as_10_safras(self):
        item = ITENS["calor"]
        limite = calor.limites(PAR)["soja"]["limite_c"]
        self.assertEqual((item["cultura"], item["limite_c"]), ("soja", limite))
        maximas = {d.data: d.tmax for d in clima.ler_serie(clima.pastas_da_cidade("rio_verde")["nasa_power"])}
        plantio = D(2026, 10, 15)
        dias = [plantio + i * UM_DIA for i in range((ULTIMO_COM_TEMPERATURA - plantio).days + 1)]
        self.assertEqual(item["dias_de_calor_forte_desde_o_plantio"], sum(maximas[d] > limite for d in dias))
        self.assertLessEqual(item["dias_de_calor_forte_na_fase_atual"], item["dias_de_calor_forte_desde_o_plantio"])
        self.assertEqual(item["dias_de_calor_forte_na_fase_critica"], 0)        # a fase crítica só começa em 24/11
        self.assertEqual(item["maxima_desde_o_plantio_c"], round(max(maximas[d] for d in dias), 1))
        guardadas = item["nas_safras_guardadas"]
        self.assertEqual((guardadas["safras"], sorted(guardadas["por_safra"])), (10, sorted(balanco.SAFRAS_DO_ESTUDO)))
        na_mao = []
        for safra in balanco.SAFRAS_DO_ESTUDO:
            comeco = D(int(safra[:4]), 10, 15)
            na_mao.append(sum(maximas[comeco + i * UM_DIA] > limite for i in range(len(dias))))
            self.assertEqual(guardadas["por_safra"][safra]["desde_o_plantio"], na_mao[-1], safra)
        self.assertEqual(guardadas["desde_o_plantio"]["valor_do_meio"], statistics.median(na_mao))
        # O calor só conta até o último dia com temperatura medida, e diz a data dele (a conta da água vai além).
        self.assertEqual(item["ultimo_dado"]["data"], ULTIMO_COM_TEMPERATURA.isoformat())
        self.assertIn(f"até {lavoura.data_br(ULTIMO_COM_TEMPERATURA)}, o último dia com temperatura medida", item["frase"])
        self.assertLessEqual(item["dia_da_maxima"], ULTIMO_COM_TEMPERATURA.isoformat())

    def test_a_regra_da_situacao_do_calor(self):
        self.assertEqual(lavoura.situacao_do_calor(na_fase_critica=1, desde_o_plantio=1, valor_do_meio=5), "alerta")
        self.assertEqual(lavoura.situacao_do_calor(na_fase_critica=0, desde_o_plantio=3, valor_do_meio=2.5), "atencao")
        self.assertEqual(lavoura.situacao_do_calor(na_fase_critica=0, desde_o_plantio=2, valor_do_meio=2), "tranquilo")
        self.assertEqual(lavoura.situacao_do_calor(na_fase_critica=0, desde_o_plantio=0, valor_do_meio=None), "tranquilo")
        self.assertEqual(lavoura.situacao_do_calor(na_fase_critica=0, desde_o_plantio=1, valor_do_meio=None), "atencao")


class OVerde(unittest.TestCase):
    def pontos(self, deste_ano, outros):
        """Dois pontos: `deste_ano` e `outros` são {data: (valor do ponto a, valor do ponto b)}."""
        juntos = {**outros, **deste_ano}
        return {nome: {"boas": sorted((dia, par[i]) for dia, par in juntos.items() if par[i] is not None),
                       "ultima_data": max(juntos), "medidas": len(juntos), "lat": 0.0, "lon": 0.0}
                for i, nome in enumerate(("a", "b"))}

    def test_o_valor_mais_recente_contra_a_mesma_epoca_dos_outros_anos(self):
        outros = {D(2021, 10, 16): (0.30, 0.34), D(2022, 10, 16): (0.40, 0.44), D(2023, 10, 16): (0.50, 0.54),
                  D(2023, 9, 30): (0.90, 0.90)}                                   # outra época: não entra
        verde = lavoura.verde_de_agora(self.pontos({D(2026, 10, 16): (0.45, 0.47)}, outros))
        self.assertEqual((verde["imagem"], verde["imagem_ate"]), ("2026-10-16", "2026-10-31"))
        self.assertEqual((verde["verde"], verde["pontos_com_medida"], verde["pontos"]), (0.46, 2, 2))
        self.assertEqual(verde["outros_anos"], {"anos": [2021, 2022, 2023], "quantos": 3, "valor_do_meio": 0.42, "menor": 0.32,
                                                "maior": 0.52, "por_ano": {"2021": 0.32, "2022": 0.42, "2023": 0.52}})
        self.assertEqual(verde["leitura"], "dentro")
        self.assertEqual(lavoura.verde_de_agora(self.pontos({D(2026, 10, 16): (0.60, 0.62)}, outros))["leitura"], "acima")
        self.assertEqual(lavoura.verde_de_agora(self.pontos({D(2026, 10, 16): (0.20, 0.22)}, outros))["leitura"], "abaixo")

    def test_ano_bissexto_ponto_com_nuvem_poucos_anos_e_o_corte_no_dia_da_consulta(self):
        # Em ano bissexto a mesma medida do satélite cai um dia antes no calendário (15/10): vale o dia do ano.
        outros = {D(2020, 10, 15): (0.30, 0.30), D(2021, 10, 16): (0.40, 0.40), D(2022, 10, 16): (0.50, 0.50)}
        verde = lavoura.verde_de_agora(self.pontos({D(2026, 10, 16): (0.45, None)}, outros))     # o ponto b com nuvem
        self.assertEqual((verde["verde"], verde["pontos_com_medida"]), (0.45, 1))
        self.assertEqual(verde["outros_anos"]["anos"], [2020, 2021, 2022])
        poucos = lavoura.verde_de_agora(self.pontos({D(2026, 10, 16): (0.45, 0.45)}, dict(list(outros.items())[:2])))
        self.assertEqual((poucos["leitura"], lavoura.MINIMO_DE_ANOS_DO_VERDE), ("sem_comparacao", 3))
        cortado = lavoura.verde_de_agora(self.pontos({D(2026, 10, 16): (0.45, 0.45), D(2026, 11, 1): (0.7, 0.7)},
                                                     outros), ate=D(2026, 10, 31))
        self.assertEqual(cortado["imagem"], "2026-10-16")
        self.assertIsNone(lavoura.verde_de_agora({}))

    def test_a_regra_da_situacao_do_verde(self):
        self.assertEqual(lavoura.situacao_do_verde("abaixo", True), "atencao")
        self.assertEqual(lavoura.situacao_do_verde("abaixo", False), "tranquilo")
        self.assertEqual(lavoura.situacao_do_verde("dentro", True), "tranquilo")
        self.assertEqual(lavoura.situacao_do_verde("acima", True), "tranquilo")
        self.assertEqual(lavoura.situacao_do_verde("sem_comparacao", True), "sem_dado")
        self.assertEqual(lavoura.situacao_do_verde(None, True), "sem_dado")

    def test_o_item_do_verde_das_tres_cidades_e_sem_arquivo(self):
        for cidade in motor.CIDADES:
            item = {i["id"]: i for i in motor.lavoura_hoje(dict(ENTRADA, cidade_id=cidade), hoje=DIA_DO_TESTE)["itens"]}[
                "verde"]
            self.assertEqual(item["imagem"], "2026-10-16", cidade)               # a imagem mais recente guardada
            self.assertEqual(item["ultimo_dado"]["data"], "2026-10-16", cidade)
            self.assertIn(item["leitura"], ("acima", "dentro", "abaixo"), cidade)
            self.assertTrue(0 < item["verde"] < 1, cidade)
            self.assertGreaterEqual(len(item["outros_anos"]["anos"]), 3, cidade)
            self.assertNotIn(2026, item["outros_anos"]["anos"])
            self.assertIn("16/10/2026", item["frase"])
            self.assertIn("não é a sua lavoura", item["frase"])
        with tempfile.TemporaryDirectory() as pasta:
            sem = lavoura.lavoura_hoje(ENTRADA, hoje=DIA_DO_TESTE, pasta_do_verde=pathlib.Path(pasta))
        item = {i["id"]: i for i in sem["itens"]}["verde"]
        self.assertEqual((item["situacao"], item["verde"]), ("sem_dado", None))


class ATerraCoberta(unittest.TestCase):
    def test_conta_os_dias_seguidos_pelo_calendario(self):
        atual = rotacoes.ROTACOES["atual"]
        terra = lavoura.terra_no_dia(CAL, atual, D(2026, 11, 11))
        self.assertEqual((terra["com_planta_viva"], terra["desde"], terra["dias_seguidos"]), (True, "2026-10-15", 28))
        self.assertEqual(terra["antes"], {"com_planta_viva": False, "de": "2026-06-15", "ate": "2026-10-14",
                                          "dias_seguidos": 122})                 # os 122 dias do pousio, como no motor
        self.assertEqual(terra["na_safra"], {"desde": "2026-09-01", "dias_com_planta_viva": 28,
                                             "dias_sem_planta_viva": 44})
        pousio = lavoura.terra_no_dia(CAL, atual, D(2026, 8, 1))
        self.assertEqual((pousio["com_planta_viva"], pousio["desde"], pousio["dias_seguidos"]),
                         (False, "2026-06-15", 48))
        capim = lavoura.terra_no_dia(CAL, rotacoes.ROTACOES["alternativa"], D(2026, 8, 1))
        self.assertTrue(capim["com_planta_viva"])                                 # a braquiária está viva

    def test_o_item_da_terra_coberta(self):
        item = ITENS["terra_coberta"]
        self.assertEqual((item["com_planta_viva"], item["desde"]), (True, "2026-10-15"))
        self.assertEqual(item["dias_seguidos"], (ULTIMO - D(2026, 10, 15)).days + 1)
        self.assertEqual(item["situacao"], "tranquilo")
        self.assertEqual(lavoura.situacao_da_terra(False), "atencao")


class OAvisoDeSede(unittest.TestCase):
    def test_a_conta_para_a_frente_e_a_do_motor_com_chuva_zero(self):
        entrada = motor.validar_entrada(ENTRADA)
        recente, _ = hoje.ler_chuva_recente("rio_verde")
        contas = hoje.contas_de_hoje(entrada, PAR, recente)
        futuros = lavoura.para_a_frente(entrada, PAR, contas["com_recente"], contas["cal"])
        self.assertEqual(len(futuros), lavoura.HORIZONTE_SEM_CHUVA_DIAS)
        self.assertEqual(futuros[0].data, contas["com_recente"][-1].data + UM_DIA)
        self.assertTrue(all(r.chuva == 0.0 for r in futuros))
        self.assertTrue(all(b.data == a.data + UM_DIA for a, b in zip(futuros, futuros[1:])))
        ultimos = contas["com_temperatura"][-lavoura.JANELA_DO_CONSUMO_DIAS:]
        medido = lavoura.para_a_frente(entrada, PAR, contas["com_recente"], contas["cal"], base=contas["com_temperatura"])
        self.assertAlmostEqual(medido[0].eto, sum(d.eto for d in ultimos) / 7)    # o tempo dos últimos 7 dias medidos
        agua = [contas["registros"][-1].agua_na_terra] + [r.agua_na_terra for r in futuros if r.tipo == "soja"]
        self.assertTrue(all(depois <= antes + 1e-9 for antes, depois in zip(agua, agua[1:])))   # sem chuva, só desce

    def test_em_quantos_dias_a_sede_chega(self):
        dia = D(2026, 11, 12)
        seca = [registro(dia + i * UM_DIA, ks=1.0 if i < 4 else 0.8) for i in range(10)]
        self.assertEqual(lavoura.dias_ate_a_sede(seca, "soja"), (5, None))
        self.assertEqual(lavoura.dias_ate_a_sede([registro(dia + i * UM_DIA) for i in range(30)], "soja"),
                         (None, "nao_chega_no_horizonte"))
        sai = [registro(dia), registro(dia + UM_DIA, "sem_planta", ks=0.5)]
        self.assertEqual(lavoura.dias_ate_a_sede(sai, "soja"), (None, "a_cultura_sai_da_terra"))

    def test_o_item_do_aviso_no_dia_do_teste(self):
        item = ITENS["aviso_de_sede"]
        self.assertEqual((item["janela_dias"], item["horizonte_dias"]), (7, 30))
        self.assertEqual(item["ja_com_sede"], RETRATO["com_sede"])
        self.assertEqual(item["sem_chuva_a_partir_de"], (ULTIMO + UM_DIA).isoformat())
        if item["dias_ate_a_sede"] is not None:
            self.assertTrue(1 <= item["dias_ate_a_sede"] <= 30)
            self.assertEqual(item["data_da_sede"], (ULTIMO + item["dias_ate_a_sede"] * UM_DIA).isoformat())
        self.assertGreater(item["consumo_medio_mm_por_dia"], 0)
        self.assertNotIn("modelo", item["frase"])
        self.assertNotIn("previsão do tempo é", item["frase"])
        self.assertIn("Não é previsão do tempo", item["frase"])

    def test_a_chuva_que_o_satelite_ja_marcou_depois_do_ultimo_dia_da_conta(self):
        dia = D(2026, 11, 11)
        chuva = {dia: 9.0, dia + UM_DIA: 0.0, dia + 2 * UM_DIA: 12.5, dia + 3 * UM_DIA: None, dia + 4 * UM_DIA: 30.0}
        self.assertEqual({k: v for k, v in lavoura.chuva_depois(chuva, dia, D(2026, 11, 15)).items() if k != "o_que_e"},
                         {"de": "2026-11-12", "ate": "2026-11-13", "dias": 2, "satelite_rapido_mm": 12.5})
        self.assertEqual(lavoura.chuva_depois(chuva, dia, dia + UM_DIA)["dias"], 1)      # nunca passa do dia da consulta
        self.assertIsNone(lavoura.chuva_depois(chuva, dia + 2 * UM_DIA, D(2026, 11, 15)))  # dia sem dado não vira zero
        # No painel a conta já vai até o último dia com chuva do satélite: não sobra chuva fora da conta.
        self.assertIsNone(ITENS["aviso_de_sede"]["chuva_depois_do_ultimo_dia"])

    def test_a_conta_vai_ate_o_ultimo_dia_com_chuva_e_cada_item_diz_a_data_do_seu_dado(self):
        self.assertEqual(PAINEL["ultimo_dia_com_dado"], RETRATO["chuva_recente"]["fonte"]["ultimo_dia_com_dado"])
        self.assertEqual(PAINEL["dias_com_o_consumo_estimado"], (ULTIMO - ULTIMO_COM_TEMPERATURA).days)
        for nome in ("fase", "agua", "terra_coberta", "aviso_de_sede"):
            self.assertEqual(ITENS[nome]["ultimo_dado"]["data"], ULTIMO.isoformat(), nome)
            self.assertIn(lavoura.data_br(ULTIMO), ITENS[nome]["frase"], nome)
        agua = ITENS["agua"]
        self.assertEqual((agua["ultimo_dia_com_temperatura"], agua["janela_do_consumo_dias"]),
                         (ULTIMO_COM_TEMPERATURA.isoformat(), 7))
        if PAINEL["dias_com_o_consumo_estimado"]:
            self.assertEqual(agua["consumo_estimado_desde"], (ULTIMO_COM_TEMPERATURA + UM_DIA).isoformat())
            self.assertIn("o consumo da cultura é o do tempo dos 7 dias anteriores", agua["frase"])
            entrada = motor.validar_entrada(ENTRADA)
            contas = hoje.contas_de_hoje(entrada, PAR, hoje.ler_chuva_recente("rio_verde")[0], DIA_DO_TESTE)
            recente = hoje.ler_chuva_recente("rio_verde")[0]
            for dia in contas["com_recente"][len(contas["com_temperatura"]):]:
                self.assertEqual(dia.chuva, recente[dia.data])                    # a chuva de verdade do satélite
                self.assertAlmostEqual(dia.eto, sum(d.eto for d in contas["com_temperatura"][-7:]) / 7)

    def test_a_regra_da_situacao_do_aviso(self):
        s = lavoura.situacao_do_aviso
        self.assertEqual(s(ha_cultura=True, ja_com_sede=True, dias=None), "alerta")
        self.assertEqual(s(ha_cultura=True, ja_com_sede=False, dias=7), "atencao")
        self.assertEqual(s(ha_cultura=True, ja_com_sede=False, dias=8), "tranquilo")
        self.assertEqual(s(ha_cultura=True, ja_com_sede=False, dias=None), "tranquilo")
        self.assertEqual(s(ha_cultura=False, ja_com_sede=False, dias=None), "tranquilo")


class ALinhaDeComandoEARota(unittest.TestCase):
    def test_a_linha_de_comando_mostra_o_resumo_e_os_seis_itens(self):
        saida, erro = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
            codigo = perguntar.main(["--lavoura-hoje", "--cidade", "jatai", "--plantio", "2026-10-20"])
        self.assertEqual((codigo, erro.getvalue()), (0, ""))                # a conferência dos números não reclamou
        texto = saida.getvalue()
        for titulo in lavoura.TITULOS.values():
            self.assertIn(titulo, texto)
        self.assertIn("Jataí", texto)
        self.assertIn("20/10/2026", texto)
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            self.assertEqual(perguntar.main(["--lavoura-hoje", "--json"]), 0)
        self.assertEqual([i["id"] for i in json.loads(saida.getvalue())["itens"]], list(lavoura.ITENS))
        with contextlib.redirect_stderr(io.StringIO()) as erro:
            self.assertEqual(perguntar.main(["--lavoura-hoje", "--plantio", "20/11"]), 2)
        self.assertIn("plantio_da_soja", erro.getvalue())

    def test_a_rota_devolve_o_painel_e_recusa_o_que_nao_e_dela(self):
        self.assertEqual(api.ROTAS["/lavoura-hoje"], "POST")
        self.assertIn("POST /lavoura-hoje", api.rota_saude()["rotas"])
        painel = api.rota_lavoura_hoje({"cidade_id": "silvania", "rotacao_atual": ["soja", "milho", "pousio"],
                                        "plantio_da_soja": "2026-10-25"})
        self.assertEqual((painel["local"]["id"], len(painel["itens"])), ("silvania", 6))
        for corpo in ({"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho"], "chuva": "power"},
                      {"cidade_id": "sorriso", "rotacao_atual": ["soja", "milho"]},
                      {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho"], "plantio_da_soja": 20261105}):
            with self.assertRaises(api.ErroDaApi) as erro:
                api.rota_lavoura_hoje(corpo)
            self.assertEqual(erro.exception.codigo, 400)

    def test_a_rota_por_http(self):
        servidor = api.criar_servidor(porta=0, silencioso=True)
        fio = threading.Thread(target=servidor.serve_forever, daemon=True)
        fio.start()
        try:
            pedido = urllib.request.Request(
                f"http://127.0.0.1:{servidor.server_address[1]}/lavoura-hoje", method="POST",
                data=json.dumps(ENTRADA).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(pedido, timeout=30) as resposta:
                corpo = json.loads(resposta.read().decode("utf-8"))
                self.assertEqual(resposta.status, 200)
        finally:
            servidor.shutdown()
            servidor.server_close()
        self.assertEqual([i["id"] for i in corpo["itens"]], list(lavoura.ITENS))
        self.assertEqual(corpo["local"]["id"], "rio_verde")


if __name__ == "__main__":
    unittest.main()
