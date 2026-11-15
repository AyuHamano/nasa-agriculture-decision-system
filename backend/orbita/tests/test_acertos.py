# Gerado com IA (Claude)
"""Testes dos acertos de 2026-11-15 no motor: cada um falhava no código de antes."""
import unittest

from orbita import balanco, conferencia, explicacao, mensagem, motor, parametros, rotacoes

HOJE = ["soja", "milho", "pousio"]
JATAI = {"cidade_id": "jatai", "rotacao_atual": HOJE, "terra": "media"}
RIO_VERDE = {"cidade_id": "rio_verde", "rotacao_atual": HOJE, "terra": "media"}
RIO_VERDE_TARDE = dict(RIO_VERDE, plantio_da_soja="2026-11-20")


def _por_id(resposta):
    return {item["id"]: item for item in resposta["comparacao_das_rotacoes"]}


class APiorColheitaNaoEAMaiorFaltaDeAgua(unittest.TestCase):
    """O pior ano é o da pior colheita da região (IBGE). Quando a conta dá menos falta de água nele que no ano
    normal, a frase diz isso, em vez de soar ao contrário."""

    @classmethod
    def setUpClass(cls):
        cls.jatai, cls.tarde, cls.rio_verde = (motor.responder(e) for e in (JATAI, RIO_VERDE_TARDE, RIO_VERDE))

    def test_em_jatai_a_frase_diz_que_o_pior_ano_teve_menos_falta_que_o_normal(self):
        hoje = _por_id(self.jatai)["soja_milho_pousio"]
        self.assertEqual((hoje["agua"]["falta_no_pior_ano_mm"], hoje["agua"]["falta_no_ano_normal_mm"]), (162.4, 224.2))
        self.assertEqual(hoje["agua"]["pior_ano_contra_o_normal"], "menor")
        self.assertIn("o pior ano é o da pior colheita da região (safra 2015-16), não o de maior falta de água na "
                      "conta", hoje["evidencia"])
        self.assertIn("faltaram 162,4 mm", hoje["evidencia"])
        self.assertIn("menos que no ano normal (safra 2021-22), que teve 224,2 mm", hoje["evidencia"])

    def test_em_rio_verde_com_o_plantio_em_20_de_novembro_tambem(self):
        itens = _por_id(self.tarde)
        hoje, capim = itens["soja_milho_pousio"], itens["soja_milho_braquiaria"]
        self.assertEqual((hoje["agua"]["falta_no_pior_ano_mm"], hoje["agua"]["falta_no_ano_normal_mm"]), (256.0, 260.4))
        self.assertIn("menos que no ano normal (safra 2019-20), que teve 260,4 mm", hoje["evidencia"])
        # na faixa do capim, a ponta de cima é igual nos dois anos: a frase não diz "menos", diz "não mais"
        self.assertEqual(capim["agua"]["pior_ano_contra_o_normal"], "menor")
        self.assertIn("não mais que no ano normal (safra 2019-20), que teve de 260,4 a 266,8 mm", capim["evidencia"])

    def test_nesses_casos_nenhuma_frase_fala_do_pior_ano_como_o_de_mais_falta(self):
        for resposta in (self.jatai, self.tarde):
            for item in resposta["comparacao_das_rotacoes"]:
                self.assertNotEqual(item["agua"]["pior_ano_contra_o_normal"], "maior", item["id"])
                self.assertNotIn("no pior ano (safra", item["evidencia"])
                for chave in ("evidencia", "beneficio", "risco", "falta_saber"):
                    self.assertNotIn("do pior ano", item[chave], (item["id"], chave))
                    self.assertEqual(conferencia.conferir_texto(item[chave], resposta), [], (item["id"], chave))
            self.assertIn("da pior colheita da região", resposta["comparacao_das_rotacoes"][0]["risco"])
            inteiro, curto = explicacao.texto(resposta), mensagem.texto(resposta)
            self.assertIn("não o de maior falta de água na conta", inteiro)
            self.assertNotIn("No pior ano (safra", inteiro)
            self.assertIn("no ano da pior colheita da região (safra 2015-16)", curto)
            self.assertNotIn("no pior ano", curto)
            self.assertLessEqual(len(curto), mensagem.LIMITE)
            self.assertEqual(conferencia.conferir_texto(curto, resposta), [])

    def test_onde_o_pior_ano_tem_mais_falta_a_frase_fica_como_era(self):
        for item in self.rio_verde["comparacao_das_rotacoes"]:
            self.assertEqual(item["agua"]["pior_ano_contra_o_normal"], "maior", item["id"])
        hoje = _por_id(self.rio_verde)["soja_milho_pousio"]
        self.assertIn("no pior ano (safra 2015-16) faltaram 225,9 mm de água para as culturas, com 73 dias de sede; "
                      "no ano normal (safra 2019-20), 152,8 mm.", hoje["evidencia"])
        self.assertIn("Na água do pior ano, ficou atrás de", hoje["risco"])
        self.assertIn("No pior ano (safra 2015-16), faltaram", explicacao.texto(self.rio_verde))
        self.assertIn("no pior ano (safra 2015-16), faltaram", mensagem.texto(self.rio_verde))

    def test_a_comparacao_dos_dois_anos_vale_para_numero_e_para_faixa(self):
        self.assertEqual(explicacao.pior_contra_normal(225.9, 152.8), "maior")
        self.assertEqual(explicacao.pior_contra_normal(162.4, 224.2), "menor")
        self.assertEqual(explicacao.pior_contra_normal(100.0, 100.0), "igual")
        self.assertEqual(explicacao.pior_contra_normal({"de": 256.0, "ate": 266.8}, {"de": 260.4, "ate": 266.8}), "menor")
        self.assertEqual(explicacao.pior_contra_normal({"de": 250.0, "ate": 270.0}, {"de": 255.0, "ate": 265.0}), "cruza")


class ORegistroEAComparacaoUsamAMesmaRegra(unittest.TestCase):
    """O registro dizia 126 dias sem planta viva e "11 safras"; a comparação, 125 dias e 10 safras. As causas: a
    safra 2015-16 tem 366 dias (o ano bissexto) e o registro punha a safra mais recente, que a conta deixa à parte,
    entre as do estudo."""

    @classmethod
    def setUpClass(cls):
        cls.resposta = motor.responder(RIO_VERDE)
        cls.registro = motor.registro_da_safra(RIO_VERDE, "2015-16")

    def test_os_dias_sem_planta_viva_trazem_o_numero_da_comparacao_e_a_frase_diz_por_que_diferem(self):
        terra = self.registro["terra_coberta"]
        da_comparacao = _por_id(self.resposta)["soja_milho_pousio"]["terra_coberta"]["dias_sem_planta_viva_no_ano"]
        self.assertEqual((terra["dias_sem_planta_viva"], terra["dias_da_safra"]), (126, 366))    # o campo de sempre
        self.assertEqual(terra["dias_sem_planta_viva_no_ano"], da_comparacao)
        self.assertEqual(da_comparacao, 125)
        self.assertIn("A terra ficou 126 dias sem planta viva: na comparação das rotações são 125, contados num ano "
                      "comum, e esta safra tem o dia a mais do ano bissexto.", self.registro["frase"])
        comum = motor.registro_da_safra(RIO_VERDE, "2016-17")
        self.assertEqual((comum["terra_coberta"]["dias_sem_planta_viva"], comum["terra_coberta"]["dias_da_safra"],
                          comum["terra_coberta"]["dias_sem_planta_viva_no_ano"]), (125, 365, 125))
        self.assertIn("A terra ficou 125 dias sem planta viva.", comum["frase"])
        self.assertNotIn("bissexto", comum["frase"])

    def test_a_posicao_sai_das_mesmas_10_safras_da_conta(self):
        entre = self.registro["entre_as_safras_guardadas"]
        self.assertEqual(list(entre["por_safra_pct"]), list(self.resposta["rotacoes"]["atual"]["safras"]))
        self.assertEqual((entre["de"], entre["a_parte"]), (10, False))
        self.assertEqual(entre["posicao"],
                         1 + sum(1 for v in entre["por_safra_pct"].values() if v > entre["falta_da_2a_safra_pct"]))
        self.assertIn("entre as 10 safras do estudo (as mesmas da comparação das rotações)", self.registro["frase"])
        self.assertNotIn("11 safras", self.registro["frase"])
        self.assertEqual(conferencia.conferir_texto(self.registro["frase"], self.registro), [])

    def test_a_safra_mais_recente_fica_a_parte_como_na_conta_e_e_posta_ao_lado_das_10(self):
        recente = motor.registro_da_safra(RIO_VERDE, motor.SAFRA_A_PARTE)
        entre = recente["entre_as_safras_guardadas"]
        self.assertEqual((entre["de"], entre["a_parte"]), (10, True))
        self.assertNotIn(motor.SAFRA_A_PARTE, entre["por_safra_pct"])
        self.assertEqual(entre["falta_da_2a_safra_pct"],
                         self.resposta["safra_2025_26"]["atual"]["milho"]["falta_relativa_pct"])
        self.assertEqual(entre["posicao"],
                         1 + sum(1 for v in entre["por_safra_pct"].values() if v > entre["falta_da_2a_safra_pct"]))
        self.assertIn("Esta safra fica à parte, como na conta", recente["frase"])
        self.assertIn("ao lado das 10 safras do estudo", recente["frase"])
        self.assertEqual(conferencia.conferir_texto(recente["frase"], recente), [])


class OTetoIgualDaFaixaECoincidencia(unittest.TestCase):
    """Rio Verde com o plantio em 20 de novembro: o teto da faixa da rotação com braquiária sai 266,8 mm no ano
    normal e também no pior ano. Não é defeito (este teste já passava): são duas contas diferentes, com parcelas
    diferentes, que arredondam para o mesmo número. Fica aqui a prova."""

    def test_os_dois_tetos_sao_contas_diferentes_que_arredondam_igual(self):
        par = parametros.carregar()
        entrada = motor.validar_entrada(RIO_VERDE_TARDE)
        dias, _ = motor._serie(entrada)
        cal = rotacoes.calendario(par, entrada["plantio_da_soja"])
        alta = parametros.valor(par, "disputa_com_o_milho", "alta")      # o teto da faixa é a disputa alta
        numeros = balanco.numeros_por_safra(balanco.simular(dias, True, par, "media", disputa=alta, cal=cal))
        normal, pior = numeros["2019-20"], numeros["2015-16"]
        self.assertEqual((motor.r1(normal["total"]["falta_mm"]), motor.r1(pior["total"]["falta_mm"])), (266.8, 266.8))
        self.assertGreater(abs(normal["total"]["falta_mm"] - pior["total"]["falta_mm"]), 0.05)   # 266,788 e 266,843
        self.assertGreater(abs(normal["milho"]["pedido_mm"] - pior["milho"]["pedido_mm"]), 20)   # 396,5 e 417,8
        self.assertGreater(abs(normal["milho"]["bebido_mm"] - pior["milho"]["bebido_mm"]), 20)   # 129,7 e 151,9
        self.assertEqual(normal["soja"]["falta_mm"], 0.0)                                        # a soja: 0 e 0,97
        self.assertGreater(pior["soja"]["falta_mm"], 0.9)
        agua = _por_id(motor.responder(RIO_VERDE_TARDE))["soja_milho_braquiaria"]["agua"]
        self.assertEqual((agua["falta_no_ano_normal_mm"]["ate"], agua["falta_no_pior_ano_mm"]["ate"]), (266.8, 266.8))


COMECOS_DO_FUNDO = {"acabou": "Neste dia a água que a planta alcança acabou",
                    "perto_do_fundo": "Neste dia a água que a planta alcança ficou perto do fundo",
                    "seca_no_plantio": "No dia do plantio d"}


class OMarcoDaAguaNoFundo(unittest.TestCase):
    """O marco "agua_acabou" é o começo da sede (a água fácil de tirar acabou), não o dia em que a água acabou de
    fato. O replay ganha o marco "agua_no_fundo": o primeiro dia em que a água na terra chega ao menor valor do
    ciclo da cultura, só quando nesse dia a planta não conseguiu beber nada."""
    DE_ANTES = [("2015-10-15", "plantio", "soja", False), ("2015-10-18", "agua_acabou", "soja", False),
                ("2016-02-06", "colheita", "soja", False), ("2016-02-10", "plantio", "milho", False),
                ("2016-04-04", "agua_acabou", "milho", True), ("2016-04-08", "calor_forte", "milho", False),
                ("2016-06-13", "colheita", "milho", False)]

    @classmethod
    def setUpClass(cls):
        cls.replay = motor.replay_da_safra(RIO_VERDE, "2015-16")

    def test_os_marcos_de_antes_ficam_exatamente_como_estavam(self):
        antes = [m for m in self.replay["marcos"] if m["tipo"] != "agua_no_fundo"]
        self.assertEqual([(m["data"], m["tipo"], m["cultura"], m["principal"]) for m in antes], self.DE_ANTES)
        self.assertIn({"data": "2016-04-04", "tipo": "agua_acabou", "cultura": "milho", "dias_seguidos": 60,
                       "agua_na_terra_mm": 17.2, "principal": True,
                       # a frase começa pela sede (antes começava por "a água fácil de tirar da terra acabou", e
                       # quem resumia dizia "a água acabou" no dia 4, vinte dias antes de ela acabar de fato)
                       "frase": "Neste dia começou a sede mais longa do milho de 2ª safra: a água fácil de tirar da "
                                "terra acabou, e foram 60 dias seguidos de sede."}, antes)

    def test_o_marco_novo_sai_no_dia_em_que_a_agua_chega_ao_fundo(self):
        marcos = self.replay["marcos"]
        novos = [m for m in marcos if m["tipo"] == "agua_no_fundo"]
        self.assertEqual(novos, [{
            "data": "2016-04-24", "tipo": "agua_no_fundo", "cultura": "milho", "agua_na_terra_mm": 0.1,
            "situacao": "acabou",       # campo novo (2026-11-15): diz o que aconteceu; a frase deste caso não mudou
            "frase": "Neste dia a água que a planta alcança acabou para o milho de 2ª safra: sobrou 0,1 mm na "
                     "terra, o menor valor do ciclo, e a planta não conseguiu beber nada.", "principal": False}])
        self.assertEqual(list(novos[0]), ["data", "tipo", "cultura", "agua_na_terra_mm", "situacao", "frase", "principal"])
        self.assertEqual([m["data"] for m in marcos], sorted(m["data"] for m in marcos))     # em ordem de data
        self.assertEqual(sum(1 for m in marcos if m["principal"]), 1)
        self.assertEqual(conferencia.conferir_texto(novos[0]["frase"], self.replay), [])
        self.assertEqual(motor.registro_da_safra(RIO_VERDE, "2015-16")["marcos"], marcos)

    def test_cada_frase_diz_o_dia_pelo_nome_a_sede_comeca_num_e_a_agua_acaba_no_outro(self):
        for cidade in ("rio_verde", "jatai", "silvania"):
            for safra in ("2015-16", "2019-20", "2021-22"):
                replay = motor.replay_da_safra(dict(RIO_VERDE, cidade_id=cidade), safra)
                for marco in replay["marcos"]:
                    if marco["tipo"] == "agua_acabou":                  # o começo da sede: "acabou" só a água fácil
                        self.assertTrue(marco["frase"].startswith("Neste dia começou a sede mais longa d"), marco)
                        self.assertNotIn("alcança acabou", marco["frase"])
                    # Este teste mudou de sentido em 2026-11-15: a frase só diz "acabou" quando sobrou até 0,1 mm;
                    # no dia do plantio ela diz que a terra já estava seca, e com mais água, que ficou perto do fundo.
                    if marco["tipo"] == "agua_no_fundo":
                        self.assertTrue(marco["frase"].startswith(COMECOS_DO_FUNDO[marco["situacao"]]), marco)
                        self.assertEqual("alcança acabou" in marco["frase"], marco["situacao"] == "acabou", marco)
                    self.assertEqual(conferencia.conferir_texto(marco["frase"], replay), [], marco)

    def test_a_terra_que_ja_chega_seca_ao_plantio_nao_sai_como_agua_que_acabou(self):
        # Silvânia 2015-16 e Rio Verde 2020-21: o marco caía no dia do plantio da soja e dizia "a água acabou".
        for cidade, safra, sobrou in (("silvania", "2015-16", "0,0"), ("rio_verde", "2020-21", "0,5")):
            replay = motor.replay_da_safra(dict(RIO_VERDE, cidade_id=cidade), safra)
            marco = next(m for m in replay["marcos"] if m["tipo"] == "agua_no_fundo" and m["cultura"] == "soja")
            plantio = next(m for m in replay["marcos"] if m["tipo"] == "plantio" and m["cultura"] == "soja")
            self.assertEqual((marco["data"], marco["situacao"]), (plantio["data"], "seca_no_plantio"))
            self.assertTrue(marco["frase"].startswith("No dia do plantio da soja a terra já estava seca: havia "
                                                      f"{sobrou} mm"), marco["frase"])
            self.assertNotIn("acabou", marco["frase"])
            self.assertEqual(conferencia.conferir_texto(marco["frase"], replay), [])

    def test_com_mais_de_um_decimo_de_mm_a_frase_diz_perto_do_fundo(self):
        # Rio Verde 2018-19: o menor valor do milho é 0,5 mm, a 2 dias do fim do ciclo. Não é "a água acabou".
        replay = motor.replay_da_safra(RIO_VERDE, "2018-19")
        marco = next(m for m in replay["marcos"] if m["tipo"] == "agua_no_fundo" and m["cultura"] == "milho")
        self.assertEqual((marco["data"], marco["agua_na_terra_mm"], marco["situacao"]),
                         ("2019-06-13", 0.5, "perto_do_fundo"))
        self.assertIn("ficou perto do fundo para o milho de 2ª safra, sem acabar: sobraram 0,5 mm", marco["frase"])
        self.assertNotIn("alcança acabou", marco["frase"])
        self.assertEqual(conferencia.conferir_texto(marco["frase"], replay), [])

    def test_a_situacao_sai_da_agua_que_sobrou_e_do_dia_em_todas_as_safras(self):
        for cidade in motor.CIDADES:
            for safra in balanco.SAFRAS_DO_ESTUDO:
                replay = motor.replay_da_safra(dict(RIO_VERDE, cidade_id=cidade), safra)
                plantios = {m["cultura"]: m["data"] for m in replay["marcos"] if m["tipo"] == "plantio"}
                for marco in (m for m in replay["marcos"] if m["tipo"] == "agua_no_fundo"):
                    esperada = ("seca_no_plantio" if marco["data"] == plantios[marco["cultura"]] else
                                "acabou" if marco["agua_na_terra_mm"] <= 0.1 else "perto_do_fundo")
                    self.assertEqual(marco["situacao"], esperada, marco)

    def test_em_qualquer_cidade_e_safra_o_marco_so_sai_quando_a_agua_acabou_de_fato(self):
        vistos = 0
        for cidade in motor.CIDADES:
            for safra in balanco.SAFRAS_DO_ESTUDO + (motor.SAFRA_A_PARTE,):
                replay = motor.replay_da_safra(dict(RIO_VERDE, cidade_id=cidade), safra)
                fundo = {m["cultura"]: m for m in replay["marcos"] if m["tipo"] == "agua_no_fundo"}
                for cultura in ("soja", "milho"):
                    dias = [d for d in replay["dias"] if d["cultura"] == cultura]
                    menor = min(d["agua_na_terra_mm"] for d in dias)
                    primeiro = next(d for d in dias if d["agua_na_terra_mm"] == menor)
                    acabou = primeiro["bebido_mm"] == 0.0 and primeiro["pedido_mm"] > 0
                    self.assertEqual(cultura in fundo, acabou and replay["resumo"][cultura]["ciclo_completo"],
                                     (cidade, safra, cultura))
                    if cultura in fundo:
                        vistos += 1
                        self.assertEqual((fundo[cultura]["data"], fundo[cultura]["agua_na_terra_mm"]),
                                         (primeiro["data"], menor), (cidade, safra, cultura))
                        self.assertFalse(fundo[cultura]["principal"])
        self.assertGreater(vistos, 0)


if __name__ == "__main__":
    unittest.main()
