# Gerado com IA (Claude)
"""Testes da comparação das rotações (comparacao_das_rotacoes), do calor e da terra coberta."""
import datetime
import json
import unittest

from orbita import calor, conferencia, explicacao, motor, parametros, rotacoes

PAR = parametros.carregar()
ENTRADA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media"}
RESPOSTA = motor.responder(ENTRADA)
COM_SORGO = motor.responder({"cidade_id": "jatai", "rotacao_atual": ["soja", "sorgo"],
                             "plantio_da_soja": "2026-11-20", "preocupacao": "calor"})
FRASES = ("evidencia", "beneficio", "risco", "falta_saber")


def por_id(resposta):
    return {item["id"]: item for item in resposta["comparacao_das_rotacoes"]}


class Comparacao(unittest.TestCase):
    def test_tres_rotacoes_contando_a_de_hoje_que_vem_primeiro(self):
        for resposta, de_hoje in ((RESPOSTA, "soja_milho_pousio"), (COM_SORGO, "soja_sorgo_pousio")):
            itens = resposta["comparacao_das_rotacoes"]
            self.assertEqual(len(itens), 3)
            self.assertEqual([item["id"] for item in itens if item["de_hoje"]], [de_hoje])
            self.assertEqual(itens[0]["id"], de_hoje)
            self.assertEqual({item["id"] for item in itens}, set(rotacoes.CARDAPIO))

    def test_cada_item_tem_o_formato_combinado(self):
        for item in RESPOSTA["comparacao_das_rotacoes"] + COM_SORGO["comparacao_das_rotacoes"]:
            # Ganhou um campo em 2026-11-15, pelos acertos: como a falta do pior ano ficou contra a do ano normal (o
            # pior ano é o da pior colheita, não o de maior falta de água na conta).
            self.assertEqual(set(item["agua"]) - {"em_faixa"},
                             {"falta_no_ano_normal_mm", "falta_no_pior_ano_mm", "dias_de_sede_no_pior_ano",
                              "pior_ano_contra_o_normal"})
            self.assertIn(item["agua"]["pior_ano_contra_o_normal"], ("maior", "menor", "igual", "cruza"))
            for chave in ("dias_de_calor_forte_no_pior_ano", "limite_c", "etiqueta"):
                self.assertIn(chave, item["calor"])
            self.assertIn(item["calor"]["etiqueta"], ("publicado", "hipótese"))
            # Ganhou um campo em 2026-11-15, pela revisão: os dias do ano inteiro, contando o intervalo entre a soja e
            # a 2ª safra (o campo de sempre conta só os dias seguidos antes do plantio da soja).
            self.assertEqual(set(item["terra_coberta"]),
                             {"dias_sem_planta_viva", "dias_sem_planta_viva_no_ano", "pelo_satelite"})
            for frase in FRASES:
                self.assertIsInstance(item[frase], str)
                self.assertGreater(len(item[frase]), 20)
            self.assertIsInstance(item["nome"], str)

    def test_os_numeros_da_comparacao_sao_os_da_conta(self):
        itens, pior, normal = por_id(RESPOSTA), RESPOSTA["comparacao"]["pior_ano"], RESPOSTA["comparacao"]["ano_normal"]
        hoje = RESPOSTA["rotacoes"]["atual"]["safras"]
        self.assertEqual(itens["soja_milho_pousio"]["agua"]["falta_no_pior_ano_mm"], hoje[pior]["total"]["falta_mm"])
        self.assertEqual(itens["soja_milho_pousio"]["agua"]["falta_no_ano_normal_mm"], hoje[normal]["total"]["falta_mm"])
        self.assertEqual(itens["soja_milho_pousio"]["agua"]["dias_de_sede_no_pior_ano"],
                         hoje[pior]["total"]["dias_de_sede"])
        sorgo = RESPOSTA["rotacoes"]["com_sorgo"]["safras"]
        self.assertEqual(itens["soja_sorgo_pousio"]["agua"]["falta_no_pior_ano_mm"], sorgo[pior]["total"]["falta_mm"])
        for chave, rotacao in rotacoes.ROTACOES.items():
            self.assertEqual(itens[rotacao["id"]]["terra_coberta"]["dias_sem_planta_viva"],
                             RESPOSTA["rotacoes"][chave]["sem_planta_viva"]["dias_sem_planta_viva"])

    def test_a_rotacao_com_capim_sai_em_faixa(self):
        capim = por_id(RESPOSTA)["soja_milho_braquiaria"]["agua"]
        faixa = RESPOSTA["rotacoes"]["alternativa"]["faixa"][RESPOSTA["comparacao"]["pior_ano"]]
        self.assertEqual(capim["falta_no_pior_ano_mm"],
                         {"de": faixa["falta_total_mm"]["menor"], "ate": faixa["falta_total_mm"]["maior"]})
        self.assertEqual(set(capim["dias_de_sede_no_pior_ano"]), {"de", "ate"})
        self.assertLessEqual(capim["falta_no_ano_normal_mm"]["de"], capim["falta_no_ano_normal_mm"]["ate"])
        self.assertTrue(capim["em_faixa"])
        self.assertFalse(por_id(RESPOSTA)["soja_sorgo_pousio"]["agua"]["em_faixa"])

    def test_as_frases_so_tem_numero_da_conta(self):
        for resposta in (RESPOSTA, COM_SORGO):
            for item in resposta["comparacao_das_rotacoes"]:
                for frase in FRASES:
                    self.assertEqual(conferencia.conferir_texto(item[frase], resposta), [], (item["id"], frase))
            self.assertEqual(conferencia.conferir_texto(explicacao.texto(resposta), resposta), [])
            self.assertIn("AS ROTAÇÕES LADO A LADO", explicacao.texto(resposta))

    def test_o_beneficio_e_o_risco_saem_da_posicao_contra_as_outras(self):
        for item in RESPOSTA["comparacao_das_rotacoes"]:
            ganhou = any(v == "melhor" for outra in item["contra_as_outras"].values() for v in outra.values())
            perdeu = any(v == "pior" for outra in item["contra_as_outras"].values() for v in outra.values())
            self.assertEqual("ficou na frente de" in item["beneficio"], ganhou, item["id"])
            self.assertEqual("ficou atrás de" in item["risco"], perdeu, item["id"])

    def test_quem_ganha_com_numero_e_com_faixa(self):
        self.assertEqual(motor.quem_ganha(100.0, 120.0, 5.0), "melhor")
        self.assertEqual(motor.quem_ganha(120.0, 100.0, 5.0), "pior")
        self.assertEqual(motor.quem_ganha(100.0, 103.0, 5.0), "empate")
        self.assertEqual(motor.quem_ganha({"de": 90.0, "ate": 110.0}, 100.0, 5.0), "depende")
        self.assertEqual(motor.quem_ganha({"de": 80.0, "ate": 90.0}, 100.0, 5.0), "melhor")
        self.assertEqual(motor.quem_ganha(100.0, {"de": 80.0, "ate": 90.0}, 5.0), "pior")
        self.assertEqual(motor.quem_ganha({"de": 99.0, "ate": 101.0}, 100.0, 5.0), "empate")
        self.assertEqual(motor.quem_ganha(30, 122, 1), "melhor")
        self.assertEqual(motor.quem_ganha(122, 122, 1), "empate")

    def test_a_resposta_inteira_vira_json(self):
        json.dumps(COM_SORGO, ensure_ascii=False)


class Calor(unittest.TestCase):
    def test_a_fase_critica_e_a_fase_do_meio(self):
        cal = rotacoes.calendario(PAR)
        inicio, fim = calor.janela_critica(cal, "milho", "2015-16")
        self.assertEqual(inicio, cal.plantio_do_milho(2016) + datetime.timedelta(days=sum(cal.milho_fases[:2])))
        self.assertEqual((fim - inicio).days, cal.milho_fases[2])
        inicio, fim = calor.janela_critica(cal, "soja", "2015-16")
        self.assertEqual(inicio, cal.plantio_da_soja(2015) + datetime.timedelta(days=sum(cal.soja_fases[:2])))
        self.assertTrue(calor.na_fase_critica(cal, "soja", inicio))
        self.assertFalse(calor.na_fase_critica(cal, "soja", fim))

    def test_conta_so_os_dias_acima_do_limite_dentro_da_fase(self):
        cal = rotacoes.calendario(PAR)
        inicio, fim = calor.janela_critica(cal, "milho", "2015-16")
        maximas = {inicio + datetime.timedelta(days=i): 30.0 for i in range(-5, (fim - inicio).days + 5)}
        maximas[inicio - datetime.timedelta(days=1)] = 45.0          # fora da fase: não conta
        maximas[inicio] = 33.0                                       # igual ao limite: não é "acima"
        maximas[inicio + datetime.timedelta(days=1)] = 33.1
        maximas[fim - datetime.timedelta(days=1)] = 36.0
        maximas[fim] = 45.0                                          # fora da fase: não conta
        conta = calor.contar(maximas, cal, "milho", 33.0, "2015-16")
        self.assertEqual(conta["dias_de_calor_forte"], 2)
        self.assertEqual(conta["maxima_da_fase_c"], 36.0)
        self.assertEqual(conta["primeiro_dia_de_calor_forte"], (inicio + datetime.timedelta(days=1)).isoformat())
        del maximas[inicio + datetime.timedelta(days=3)]             # dia sem temperatura: não inventa
        self.assertIsNone(calor.contar(maximas, cal, "milho", 33.0, "2015-16"))

    def test_o_bloco_do_calor_na_resposta(self):
        bloco = RESPOSTA["calor"]
        self.assertEqual(set(bloco["limites"]), {"soja", "milho", "sorgo"})
        for cultura, limite in bloco["limites"].items():
            self.assertEqual(limite["etiqueta"], "publicado")
            self.assertTrue(limite["fonte"].startswith("http"), cultura)
            self.assertTrue(limite["trecho"])
            self.assertEqual(limite["limite_c"], PAR["calor"][cultura]["limite_c"]["valor"])
        self.assertEqual(len(bloco["por_cultura"]["milho"]["por_safra"]), 11)       # as 10 safras e a de 2025-26
        self.assertIn("com_o_outro_limite", bloco["por_cultura"]["milho"]["por_safra"]["2015-16"])
        pior = RESPOSTA["comparacao"]["pior_ano"]
        for item in RESPOSTA["comparacao_das_rotacoes"]:
            self.assertEqual(item["calor"]["dias_de_calor_forte_no_pior_ano"],
                             bloco["por_rotacao"][item["id"]]["dias_no_pior_ano"])
            self.assertEqual(item["calor"]["dias_de_calor_forte_no_pior_ano"],
                             sum(c["dias"] for c in item["calor"]["por_cultura"].values()))
            segunda = rotacoes.CARDAPIO[item["id"]]["segunda"]
            self.assertEqual(item["calor"]["limite_c"], PAR["calor"][segunda]["limite_c"]["valor"])
            self.assertEqual(item["calor"]["por_cultura"][segunda]["dias"],
                             bloco["por_cultura"][segunda]["por_safra"][pior]["dias_de_calor_forte"])
        self.assertTrue(bloco["aviso"])
        self.assertEqual(len(bloco["hipoteses"]), 2)

    def test_o_calor_nao_muda_a_conta_da_agua(self):
        par = parametros.carregar()
        par["calor"]["milho"]["limite_c"]["valor"] = 20.0
        quente = motor.responder(ENTRADA, par=par)
        self.assertEqual(quente["rotacoes"], RESPOSTA["rotacoes"])
        self.assertGreater(quente["calor"]["por_cultura"]["milho"]["soma_das_safras"],
                           RESPOSTA["calor"]["por_cultura"]["milho"]["soma_das_safras"])

    def test_a_preocupacao_com_o_calor_vira_o_destaque(self):
        self.assertEqual(COM_SORGO["destaque"]["prioridade"], "calor")
        self.assertEqual(COM_SORGO["ordem_das_pernas"][0], "calor")
        self.assertIn("calor", explicacao.texto(COM_SORGO).lower())


class TerraCoberta(unittest.TestCase):
    def test_os_dias_pelo_calendario_em_cada_rotacao_e_o_satelite_so_na_de_hoje(self):
        bloco, itens = RESPOSTA["terra_coberta"], por_id(RESPOSTA)
        self.assertEqual(set(bloco["por_rotacao"]), set(rotacoes.CARDAPIO))
        self.assertEqual(bloco["por_rotacao"]["soja_milho_braquiaria"]["dias_sem_planta_viva"], 30)
        self.assertEqual(itens["soja_milho_pousio"]["terra_coberta"]["pelo_satelite"],
                         RESPOSTA["ndvi"]["comparacao"]["dias_pelo_satelite"])
        self.assertIsNone(itens["soja_milho_braquiaria"]["terra_coberta"]["pelo_satelite"])
        self.assertIsNone(itens["soja_sorgo_pousio"]["terra_coberta"]["pelo_satelite"])
        self.assertIn("só a rotação de hoje", bloco["aviso"])

    def test_verde_do_satelite_para_o_agente(self):
        verde = motor.verde_do_satelite("rio_verde")
        self.assertEqual(verde["dias_pelo_calendario"], 122)
        self.assertEqual(verde["dias_pelo_satelite"], RESPOSTA["ndvi"]["comparacao"]["dias_pelo_satelite"])
        self.assertIn(verde["leitura"], ("bate", "dentro_da_faixa", "fora_da_faixa"))
        self.assertEqual(conferencia.conferir_texto(verde["frase"], verde), [])
        self.assertTrue(verde["aviso"])
        # Silvânia ganhou o verde do satélite em 2026-11-15: o caso "sem medida" está em test_verde_das_cidades.py
        self.assertNotEqual(motor.verde_do_satelite("silvania")["leitura"], "sem_medida")
        with self.assertRaises(ValueError) as erro:
            motor.verde_do_satelite("sorriso")
        self.assertTrue(str(erro.exception).startswith("Entrada fora do formato:"))


class ALeituraDoProdutor(unittest.TestCase):
    """A rodada do alinhamento (decisão do dono, 2026-11-15): o risco e o que falta saber saem em UMA frase só (a
    da perna que preocupa o produtor, se ele disse qual e a rotação tem frase nela; senão, a primeira da ordem de
    sempre). O texto de antes vai, inteiro, para `risco_detalhe` e `falta_saber_detalhe` (a leitura do agrônomo)."""
    ROTULOS = {"agua": "Na água", "calor": "No calor", "terra": "Na terra coberta"}
    PERNAS = {"agua": "agua", "calor": "calor", "terra": "terra_coberta"}

    def test_uma_frase_so_e_o_texto_de_antes_no_detalhe(self):
        for resposta in (RESPOSTA, COM_SORGO):
            for item in resposta["comparacao_das_rotacoes"]:
                for curto in ("risco", "falta_saber"):
                    frase, longo = item[curto], item[curto + "_detalhe"]
                    self.assertTrue(frase.strip() and longo.strip(), (item["id"], curto))
                    self.assertTrue(frase.endswith("."), (item["id"], curto))
                    self.assertNotIn(". ", frase, (item["id"], curto))          # uma frase só
                    self.assertIn(frase, longo, (item["id"], curto))            # tirada do texto de antes
                    self.assertEqual(conferencia.conferir_texto(longo, resposta), [], (item["id"], curto))
        hoje = por_id(RESPOSTA)["soja_milho_pousio"]
        for pedaco in ("Na água do pior ano, ficou atrás de", "Na terra coberta, ficou atrás de"):
            self.assertIn(pedaco, hoje["risco_detalhe"])
        self.assertIn("O quanto de terra a palha do milho cobre é hipótese.", hoje["falta_saber_detalhe"])
        self.assertTrue(hoje["risco"].startswith("Na água do pior ano, ficou atrás de"))    # sem preocupação: a 1ª

    def test_o_risco_e_o_da_preocupacao_quando_a_rotacao_perde_nela(self):
        for preocupacao in ("agua", "calor", "terra"):
            resposta = motor.responder(dict(ENTRADA, preocupacao=preocupacao))
            for item in resposta["comparacao_das_rotacoes"]:
                perde = any(contra[self.PERNAS[preocupacao]] == "pior" for contra in item["contra_as_outras"].values())
                if perde:
                    self.assertTrue(item["risco"].startswith(self.ROTULOS[preocupacao]), (preocupacao, item["id"]))
                    self.assertIn("ficou atrás de", item["risco"])
                else:       # não perde nela: vale a primeira frase da ordem de sempre
                    self.assertTrue(item["risco_detalhe"].startswith(item["risco"]), (preocupacao, item["id"]))
                self.assertEqual(item["risco_detalhe"], por_id(RESPOSTA)[item["id"]]["risco_detalhe"])

    def test_a_regra_da_frase_principal(self):
        frases = [("agua", "A."), ("terra_coberta", "B."), (None, "C.")]
        self.assertEqual(explicacao.frase_principal(frases), "A.")
        self.assertEqual(explicacao.frase_principal(frases, "terra"), "B.")
        self.assertEqual(explicacao.frase_principal(frases, "calor"), "A.")


if __name__ == "__main__":
    unittest.main()


class ORiscoCurto(unittest.TestCase):
    """A frase de risco que a tela do produtor mostra (`risco_curto`): o risco do caminho com um número só (o mesmo
    da tabela do Ensaiar; no milho com capim, o do meio) e a comparação com outro caminho em palavras simples, sem
    "ficou atrás de" e sem o nome comprido da rotação. A faixa do capim fica na prova (`risco`, `risco_detalhe`)."""
    FICHAS = [dict(cidade_id=cidade, rotacao_atual=rotacao, **extra)
              for cidade in motor.CIDADES
              for rotacao, extra in ((["soja", "milho", "pousio"], {}),
                                     (["soja", "milho", "pousio"], {"plantio_da_soja": "2026-11-10"}),
                                     (["soja", "sorgo"], {"plantio_da_soja": "2026-10-28"}))]
    COMECOS = {"agua": "Num ano ruim, faltam ", "calor": "Num ano ruim, ", "terra_coberta": "A terra fica "}
    NOMES = {"soja_milho_pousio": ("milho", "milho sem capim"), "soja_milho_braquiaria": ("capim",),
             "soja_sorgo_pousio": ("sorgo",)}

    @staticmethod
    def da_tabela(item, perna, resposta):
        """O número que a tabela do Ensaiar mostra: na água em faixa, o do meio da disputa do capim com o milho."""
        valor = explicacao._valor_da_perna(item, perna)
        if isinstance(valor, dict):
            valor = resposta["comparacao"]["agua"]["pela_faixa"]["por_cenario"]["meio"]["falta_mm"]
        return explicacao.n(valor)

    def test_as_tres_frases_de_rio_verde(self):
        curtas = {ident: item["risco_curto"] for ident, item in por_id(RESPOSTA).items()}
        hoje, capim, sorgo = (por_id(RESPOSTA)[i] for i in ("soja_milho_pousio", "soja_milho_braquiaria",
                                                              "soja_sorgo_pousio"))
        do_meio = RESPOSTA["comparacao"]["agua"]["pela_faixa"]["por_cenario"]["meio"]["falta_mm"]
        do_sorgo = explicacao.n(sorgo["agua"]["falta_no_pior_ano_mm"])
        self.assertEqual(curtas["soja_milho_pousio"], f"Num ano ruim, faltam "
                         f"{explicacao.n(hoje['agua']['falta_no_pior_ano_mm'])} mm de água. Com sorgo faltariam "
                         f"{do_sorgo} mm.")
        self.assertEqual(curtas["soja_milho_braquiaria"], f"Num ano ruim, faltam {explicacao.n(do_meio)} mm de água. "
                         f"Com sorgo faltariam {do_sorgo} mm.")
        self.assertEqual(curtas["soja_sorgo_pousio"], f"A terra fica {sorgo['terra_coberta']['dias_sem_planta_viva']} "
                         f"dias seguidos sem planta viva. Com capim seriam "
                         f"{capim['terra_coberta']['dias_sem_planta_viva']}.")
        faixa = capim["agua"]["falta_no_pior_ano_mm"]
        self.assertTrue(faixa["de"] <= do_meio <= faixa["ate"])              # o do meio é da conta, dentro da faixa

    def test_nas_tres_cidades_um_numero_so_da_conta_e_palavras_simples(self):
        for ficha in self.FICHAS:
            resposta = motor.responder(ficha)
            itens = por_id(resposta)
            for item in resposta["comparacao_das_rotacoes"]:
                frase, onde = item["risco_curto"], (ficha, item["id"])
                self.assertEqual(conferencia.conferir_texto(frase, resposta), [], onde)
                self.assertLessEqual(len(frase), 90, onde)                      # cabe em duas linhas no celular
                self.assertTrue(frase.endswith("."), onde)
                self.assertNotIn("ficou atrás", frase, onde)
                self.assertNotRegex(frase, r"\d a \d", onde)                    # sem faixa: um número só
                for outro in resposta["comparacao_das_rotacoes"]:
                    self.assertNotIn(outro["apelido"], frase, onde)
                    self.assertNotIn(outro["nome"], frase, onde)
                perdas = [(perna, ident) for ident, contra in item["contra_as_outras"].items()
                          for perna in ("agua", "calor", "terra_coberta") if contra[perna] == "pior"]
                if not perdas:
                    self.assertNotRegex(frase, r"\d", onde)
                    continue
                perna = next(p for p in self.COMECOS if frase.startswith(self.COMECOS[p]) and (
                    p != "calor" or "calor forte" in frase))
                self.assertEqual(perna, next(p for p in ("agua", "calor", "terra_coberta")
                                             if any(p == de for de, _ in perdas)), onde)      # a 1ª perna em que perde
                meu = self.da_tabela(item, perna, resposta)
                self.assertIn(f"{meu} ", frase.split(". ")[0], onde)
                # a comparação é com o melhor dos caminhos de que este ficou atrás nessa perna
                melhor = min((ident for de, ident in perdas if de == perna),
                             key=lambda ident: float(self.da_tabela(itens[ident], perna, resposta).replace(",", ".")))
                segunda = frase.split(". ")[1]
                self.assertTrue(any(segunda.startswith(f"Com {nome} ") for nome in self.NOMES[melhor]), onde)
                do_outro = self.da_tabela(itens[melhor], perna, resposta)
                self.assertTrue(f" {do_outro}" in segunda or (do_outro == "0" and "nenhum" in segunda), onde)

    def test_segue_a_preocupacao_do_produtor(self):
        for preocupacao, pedaco in (("calor", "de calor forte"), ("terra", "sem planta viva"), ("agua", "mm de água")):
            resposta = motor.responder(dict(ENTRADA, preocupacao=preocupacao))
            hoje = resposta["comparacao_das_rotacoes"][0]
            self.assertIn(pedaco, hoje["risco_curto"], preocupacao)
            self.assertEqual(conferencia.conferir_texto(hoje["risco_curto"], resposta), [], preocupacao)
        calor = por_id(motor.responder(dict(ENTRADA, preocupacao="calor")))["soja_milho_pousio"]
        dias = calor["calor"]["dias_de_calor_forte_no_pior_ano"]
        self.assertEqual(calor["risco_curto"], f"Num ano ruim, são {dias} dias de calor forte na fase crítica. "
                                               "Com sorgo não teria nenhum.")

    def test_a_frase_de_cada_perna_e_a_de_quem_nao_perde(self):
        curta = explicacao.frase_curta_do_risco
        self.assertEqual(curta("agua", 225.9, "sorgo", 191.3), "Num ano ruim, faltam 225,9 mm de água. Com sorgo "
                                                               "faltariam 191,3 mm.")
        self.assertEqual(curta("calor", 2, "sorgo", 1), "Num ano ruim, são 2 dias de calor forte na fase crítica. "
                                                        "Com sorgo seria 1.")
        self.assertEqual(curta("calor", 1, "sorgo", 0), "Num ano ruim, é 1 dia de calor forte na fase crítica. "
                                                        "Com sorgo não teria nenhum.")
        self.assertEqual(curta("terra_coberta", 122, "capim", 30), "A terra fica 122 dias seguidos sem planta viva. "
                                                                   "Com capim seriam 30.")
        self.assertEqual(curta("terra_coberta", 1, "capim", 0), "A terra fica 1 dia sem planta viva. Com capim não "
                                                                "teria nenhum.")
        # quem não fica atrás de ninguém: o risco próprio do capim, ou a frase de que a conta não achou risco
        sem_perda = dict(por_id(RESPOSTA)["soja_milho_braquiaria"])
        sem_perda["contra_as_outras"] = {ident: dict.fromkeys(("agua", "calor", "terra_coberta"), "melhor")
                                         for ident in rotacoes.CARDAPIO}
        frases = explicacao.frases_da_rotacao(sem_perda, RESPOSTA["comparacao_das_rotacoes"], RESPOSTA)
        self.assertEqual(frases["risco_curto"], explicacao.RISCOS_PROPRIOS_CURTOS["soja_milho_braquiaria"])
        self.assertNotRegex(frases["risco_curto"], r"\d")
        sem_perda["id"] = "soja_sorgo_pousio"
        frases = explicacao.frases_da_rotacao(sem_perda, RESPOSTA["comparacao_das_rotacoes"], RESPOSTA)
        self.assertEqual(frases["risco_curto"], explicacao.SEM_RISCO_CURTO)
