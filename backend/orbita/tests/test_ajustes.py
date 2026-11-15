# Gerado com IA (Claude)
"""Testes dos ajustes de 2026-11-14: a palha, a disputa do capim com o milho, o veredito pela faixa e a sede forte.

De onde vêm os valores esperados (de fora do código):
- A palha: FAO-56, cap. 10 (https://www.fao.org/4/X0490E/x0490e0g.htm): com 50% da terra coberta, a evaporação cai
  "about 25%", e "one would reduce Kc ini by about 25%".
- Os números "de antes": a saída do motor no commit 210b973 (o ramo jose antes destes ajustes; terra média, chuva do
  IMERG), guardada na prova: a falta do milho de 220,6 mm (49,6%) na safra 2015-16 e de 142,8 mm (34,7%) na 2019-20,
  iguais nas duas rotações; a terra com 26,5 mm (hoje) e 10,6 mm (alternativa) no plantio da soja de 2015-16.
- A sede forte: o arquivo do IBGE (data/orbita/validacao/ibge/rendimento_rio_verde.csv), lido aqui pelo teste.
"""
import copy
import csv
import json
import pathlib
import re
import statistics
import unittest

from orbita import balanco, clima, conferencia, explicacao, motor, parametros, rotacoes

ENTRADA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"],
           "prioridades": {"agua": 5, "solo": 4, "renda": 2, "erosao": 3}, "terra": "media"}
RESPOSTA = motor.responder(ENTRADA)
DIAS, _ = clima.ler_serie_com_aviso("imerg")
CENARIOS = ("sem_disputa", "meio", "alta")


def par_com(cobertura_hoje=None, cobertura_alternativa=None):
    par = copy.deepcopy(parametros.carregar())
    if cobertura_hoje is not None:
        par["palha"]["cobertura_do_milho_solteiro"]["valor"] = cobertura_hoje
    if cobertura_alternativa is not None:
        par["palha"]["cobertura_do_milho_com_braquiaria"]["valor"] = cobertura_alternativa
    return par


def evaporacao(registros, cal):
    """A água que saiu nos dias em que a palha age: os dias sem planta e a fase inicial da soja."""
    total = 0.0
    for r in registros:
        if r.tipo == balanco.SEM_PLANTA:
            total += r.bebido
        elif r.tipo == "soja":
            for ano in (r.data.year, r.data.year - 1):
                if 0 <= (r.data - cal.plantio_da_soja(ano)).days < cal.soja_fases[0]:
                    total += r.bebido
    return total


class Palha(unittest.TestCase):
    def test_a_regra_do_fao_56(self):
        # 50% da terra coberta = 25% a menos de evaporação (o exemplo do FAO-56, cap. 10).
        self.assertAlmostEqual(rotacoes.fator_da_palha(0.5, 0.5), 0.75)
        self.assertAlmostEqual(rotacoes.fator_da_palha(0.0, 0.5), 1.0)
        self.assertEqual(parametros.valor(parametros.carregar(), "palha", "reducao_por_cobertura"), 0.5)

    def test_o_kc_cai_so_nos_dias_sem_planta_e_na_fase_inicial_da_soja(self):
        sem, com = rotacoes.calendario(par_com(0.0, 0.0)), rotacoes.calendario(par_com(0.5, 0.5))
        D = __import__("datetime").date
        for data, razao in ((D(2021, 9, 1), 0.75), (D(2021, 10, 20), 0.75),     # sem planta; soja no 5º dia
                            (D(2021, 12, 15), 1.0), (D(2021, 4, 1), 1.0)):       # soja no meio; milho
            antes = rotacoes.cobertura_do_dia(data, False, sem)
            depois = rotacoes.cobertura_do_dia(data, False, com)
            self.assertEqual(antes[0], depois[0])
            self.assertAlmostEqual(depois[1], razao * antes[1], msg=str(data))

    def test_com_mais_palha_a_evaporacao_nunca_sobe(self):
        for com_braquiaria in (False, True):
            anterior = None
            for cobertura in (0.0, 0.3, 0.6, 0.9, 1.0):
                par = par_com(cobertura, cobertura)
                saiu = evaporacao(balanco.simular(DIAS, com_braquiaria, par), rotacoes.calendario(par))
                if anterior is not None:
                    self.assertLessEqual(saiu, anterior + 1e-9, f"cobertura {cobertura}")
                anterior = saiu
            self.assertLess(saiu, evaporacao(balanco.simular(DIAS, com_braquiaria, par_com(0.0, 0.0)),
                                             rotacoes.calendario(par_com(0.0, 0.0))))

    def test_a_palha_entra_nas_duas_rotacoes_e_a_do_capim_cobre_mais(self):
        hoje, alternativa = RESPOSTA["rotacoes"]["atual"]["palha"], RESPOSTA["rotacoes"]["alternativa"]["palha"]
        self.assertGreater(hoje["cobertura_pct"], 0)
        self.assertGreater(alternativa["cobertura_pct"], hoje["cobertura_pct"])
        self.assertLessEqual(alternativa["cobertura_pct"], 100)
        for palha in (hoje, alternativa):
            self.assertAlmostEqual(palha["evaporacao_a_menos_pct"], palha["cobertura_pct"] * 0.5, places=1)


class Disputa(unittest.TestCase):
    def test_com_a_disputa_em_zero_e_sem_palha_os_numeros_sao_os_de_antes(self):
        par = par_com(0.0, 0.0)
        for com_braquiaria, agua_no_plantio in ((False, 26.5), (True, 10.6)):
            registros = balanco.simular(DIAS, com_braquiaria, par, "media", disputa=0.0)
            safras = balanco.numeros_por_safra(registros)
            for safra, falta, pct in (("2015-16", 220.6, 49.6), ("2019-20", 142.8, 34.7)):
                self.assertAlmostEqual(safras[safra]["milho"]["falta_mm"], falta, delta=0.05)
                self.assertAlmostEqual(safras[safra]["milho"]["falta_relativa_pct"], pct, delta=0.05)
            self.assertAlmostEqual(balanco.agua_no_plantio_da_soja(registros)["2015-16"], agua_no_plantio, delta=0.05)

    def test_com_a_disputa_em_zero_o_capim_nao_tira_nada_do_milho(self):
        par = parametros.carregar()
        self.assertEqual(balanco.simular(DIAS, True, par), balanco.simular(DIAS, True, par, disputa=0.0))
        self.assertTrue(all(r.bebido_do_capim == 0.0 for r in balanco.simular(DIAS, True, par, disputa=0.0)))

    def test_a_disputa_nao_muda_o_pedido_do_milho_e_nunca_diminui_a_falta(self):
        par = parametros.carregar()
        sem = balanco.numeros_por_safra(balanco.simular(DIAS, True, par, disputa=0.0))
        registros = balanco.simular(DIAS, True, par, disputa=0.08)
        com = balanco.numeros_por_safra(registros)
        self.assertGreater(sum(r.bebido_do_capim for r in registros if r.tipo == "milho"), 0.0)
        self.assertEqual(sum(r.bebido_do_capim for r in registros if r.tipo != "milho"), 0.0)
        for safra in balanco.SAFRAS_DO_ESTUDO:
            self.assertAlmostEqual(com[safra]["milho"]["pedido_mm"], sem[safra]["milho"]["pedido_mm"], places=9)
            self.assertGreaterEqual(com[safra]["milho"]["falta_mm"], sem[safra]["milho"]["falta_mm"] - 1e-9)
        self.assertGreater(sum(com[s]["milho"]["falta_mm"] for s in com), sum(sem[s]["milho"]["falta_mm"] for s in sem))

    def test_com_a_disputa_a_agua_nao_some_nem_aparece(self):
        r = balanco.simular(DIAS[:800], True, parametros.carregar(), disputa=0.08)
        for ontem, hoje in zip(r, r[1:]):
            antes = ontem.agua_na_terra / ontem.taw * hoje.taw
            self.assertAlmostEqual(antes + hoje.chuva - hoje.bebido - hoje.bebido_do_capim - hoje.percolacao,
                                   hoje.agua_na_terra, places=6)

    def test_a_disputa_so_vale_na_alternativa(self):
        with self.assertRaises(ValueError):
            balanco.simular(DIAS[:10], False, parametros.carregar(), disputa=0.08)

    def test_os_fatores_em_ordem_e_abaixo_do_teto_do_fao_56(self):
        par = parametros.carregar()
        fatores = [parametros.valor(par, "disputa_com_o_milho", c) for c in CENARIOS]
        self.assertEqual(fatores[0], 0.0)
        self.assertLess(fatores[0], fatores[1])
        self.assertLess(fatores[1], fatores[2])
        # FAO-56, cap. 7: "Kc max ranges from about 1.05 to 1.30": o milho com o capim não passa disso.
        self.assertLessEqual(parametros.valor(par, "culturas", "milho_2a_safra", "kc_meio") * (1 + fatores[2]), 1.30 + 1e-9)


class Faixa(unittest.TestCase):
    def test_a_faixa_sai_em_ordem(self):
        alternativa = RESPOSTA["rotacoes"]["alternativa"]
        cenarios = alternativa["disputa_com_o_milho"]["cenarios"]
        self.assertEqual(list(cenarios), list(CENARIOS))
        for safra, faixa in alternativa["faixa"].items():
            faltas = [cenarios[c]["safras"][safra]["milho"]["falta_mm"] for c in CENARIOS]
            self.assertEqual(faltas, sorted(faltas), safra)
            for medida in ("falta_do_milho_mm", "falta_do_milho_pct", "falta_total_mm"):
                self.assertLessEqual(faixa[medida]["menor"], faixa[medida]["maior"], safra)
            self.assertEqual(faixa["falta_do_milho_mm"], {"menor": faltas[0], "maior": faltas[-1]})
        self.assertEqual(list(alternativa["faixa"]), list(alternativa["safras"]))

    def test_os_campos_antigos_da_alternativa_sao_os_do_cenario_dito(self):
        alternativa = RESPOSTA["rotacoes"]["alternativa"]
        em_uso = alternativa["disputa_com_o_milho"]["nos_campos_antigos"]
        self.assertIn(em_uso, CENARIOS)
        self.assertEqual(alternativa["safras"], alternativa["disputa_com_o_milho"]["cenarios"][em_uso]["safras"])

    def test_nenhum_campo_antigo_sumiu(self):
        antigos = json.loads((pathlib.Path(__file__).parent / "campos_de_antes.json").read_text(encoding="utf-8"))
        agora = set()

        def anda(coisa, caminho):
            if isinstance(coisa, dict):
                for chave, valor in coisa.items():
                    anda(valor, caminho + ["<safra>" if re.fullmatch(r"\d{4}-\d{2}", chave) else chave])
            elif isinstance(coisa, list):
                agora.add(".".join(caminho))
                for item in coisa[:1]:
                    if isinstance(item, (dict, list)):
                        anda(item, caminho + ["[]"])
            else:
                agora.add(".".join(caminho))

        anda(RESPOSTA, [])
        # As notas de 1 a 5 saíram do motor (decisão do dono, 2026-11-15: "tira isso"), e com elas as chaves que
        # as guardavam: entrada.prioridades (com as 4 notas), prioridades[].nota e destaque.nota. Nenhum outro
        # campo de antes saiu.
        das_notas = ("prioridades.[].nota", "destaque.nota")
        self.assertNotIn("prioridades", RESPOSTA["entrada"])
        for campo in das_notas:
            self.assertNotIn(campo, agora)
        # A lista dos quatro pontos medidos e o ponto do destaque continuam, com o nome que diz o que são (2026-11-15):
        # `prioridades` virou `pontos_medidos` e `destaque.prioridade` virou `destaque.ponto`, com o mesmo conteúdo.
        def de_agora(campo):
            if campo == "destaque.prioridade":
                return "destaque.ponto"
            return re.sub(r"^prioridades(?=$|\.)", "pontos_medidos", campo)
        self.assertNotIn("prioridades", RESPOSTA)
        self.assertNotIn("prioridade", RESPOSTA["destaque"])
        self.assertEqual([campo for campo in antigos["campos"] if de_agora(campo) not in agora
                          and campo not in das_notas and not campo.startswith("entrada.prioridades.")], [])
        for p in RESPOSTA["pontos_medidos"]:   # o vocabulário antigo do campo "melhor" continua o mesmo
            self.assertIn(p["melhor"], ("atual", "alternativa", "empate", "não medido"))


class VereditoDaAgua(unittest.TestCase):
    def codigo(self, hoje, alternativa):
        return motor.veredito_da_agua_pela_faixa(hoje, dict(zip(CENARIOS, alternativa)), 5.0)["codigo"]

    def test_depende_da_hipotese_quando_o_sinal_muda(self):
        self.assertEqual(self.codigo(100.0, (90.0, 100.0, 110.0)), "depende_da_hipotese")
        v = motor.veredito_da_agua_pela_faixa(100.0, dict(zip(CENARIOS, (90.0, 100.0, 110.0))), 5.0)
        self.assertIn("depende da hipótese", v["frase"])
        self.assertEqual((v["diferenca_mm"]["menor"], v["diferenca_mm"]["maior"]), (-10.0, 10.0))

    def test_melhor_pior_e_empate_pedem_as_duas_pontas(self):
        self.assertEqual(self.codigo(100.0, (80.0, 85.0, 90.0)), "alternativa_melhor")
        self.assertEqual(self.codigo(100.0, (110.0, 115.0, 120.0)), "alternativa_pior")
        self.assertEqual(self.codigo(100.0, (98.0, 100.0, 103.0)), "empate")
        self.assertEqual(self.codigo(100.0, (99.0, 104.0, 109.0)), "depende_da_hipotese")   # empate numa ponta só
        for alternativa, palavra in (((80.0, 85.0, 90.0), "melhor"), ((110.0, 115.0, 120.0), "pior"),
                                     ((98.0, 100.0, 103.0), "empate")):
            self.assertIn(palavra, motor.veredito_da_agua_pela_faixa(100.0, dict(zip(CENARIOS, alternativa)), 5.0)["frase"])

    def test_na_resposta_o_veredito_sai_dos_numeros_da_propria_resposta(self):
        r = RESPOSTA
        pela_faixa, pior = r["comparacao"]["agua"]["pela_faixa"], r["comparacao"]["pior_ano"]
        cenarios = r["rotacoes"]["alternativa"]["disputa_com_o_milho"]["cenarios"]
        hoje = r["rotacoes"]["atual"]["safras"][pior]["total"]["falta_mm"]
        for c in CENARIOS:      # a diferença de cada cenário é a dos números mostrados (a menos do arredondamento)
            self.assertAlmostEqual(pela_faixa["por_cenario"][c]["diferenca_mm"],
                                   cenarios[c]["safras"][pior]["total"]["falta_mm"] - hoje, delta=0.11)
        pontas = {pela_faixa["por_cenario"][pela_faixa[ponta]]["classe"]
                  for ponta in ("cenario_do_menor_efeito", "cenario_do_maior_efeito")}
        esperado = {frozenset({"melhor"}): "alternativa_melhor", frozenset({"pior"}): "alternativa_pior",
                    frozenset({"empate"}): "empate"}.get(frozenset(pontas), "depende_da_hipotese")
        self.assertEqual(pela_faixa["codigo"], esperado)
        self.assertIn(pela_faixa["frase"], explicacao.texto(r))

    def test_os_campos_antigos_da_agua_guardam_a_comparacao_antiga(self):
        # Achado 1 da revisão: "depende da hipótese" não pode virar "empate" nos campos antigos. Eles comparam a
        # rotação de hoje com a alternativa na hipótese do meio, como antes comparavam com a alternativa única.
        r = RESPOSTA
        agua, pior = r["comparacao"]["agua"], r["comparacao"]["pior_ano"]
        meio = (r["rotacoes"]["alternativa"]["safras"][pior]["total"]["falta_mm"]
                - r["rotacoes"]["atual"]["safras"][pior]["total"]["falta_mm"])
        self.assertEqual(agua["pela_faixa"]["codigo"], "depende_da_hipotese")
        self.assertGreater(meio, agua["empate_abaixo_de_mm"] + 0.2)      # no meio, a alternativa fica pior
        self.assertEqual(agua["pela_falta_no_pior_ano"], "atual")
        self.assertEqual(agua["melhor"], "atual")
        self.assertAlmostEqual(agua["diferenca_mm"], meio, delta=0.11)
        por_id = {p["id"]: p for p in r["pontos_medidos"]}
        self.assertEqual(por_id["agua"]["melhor"], "atual")
        self.assertEqual(por_id["agua"]["veredito_pela_faixa"], "depende_da_hipotese")

    def test_o_veredito_geral_usa_a_faixa_e_nao_o_campo_antigo(self):
        v = motor.veredito({"agua": "atual", "solo": "alternativa", "erosao": "alternativa"},
                           agua_pela_faixa="depende_da_hipotese")
        self.assertEqual((v["codigo"], v["contra_a_troca"]), ("depende", []))
        self.assertNotIn("pior em água", v["frase"])
        v = motor.veredito({"agua": "empate", "solo": "alternativa", "erosao": "alternativa"},
                           agua_pela_faixa="alternativa_pior")
        self.assertEqual((v["codigo"], v["contra_a_troca"]), ("depende", ["agua"]))
        v = motor.veredito({"agua": "atual", "solo": "alternativa", "erosao": "alternativa"}, agua_pela_faixa="empate")
        self.assertEqual(v["codigo"], "vale_testar_a_troca")

    def test_as_pontas_se_escolhem_sem_arredondar(self):
        # Achado 2 da revisão: 4,96 mm é empate e 5,04 mm é pior, embora os dois apareçam como 5,0.
        self.assertEqual(self.codigo(100.0, (104.96, 105.00, 105.04)), "depende_da_hipotese")
        self.assertEqual(self.codigo(100.0, (95.04, 95.00, 94.96)), "depende_da_hipotese")

    def test_se_a_agua_depende_da_hipotese_a_resposta_nao_diz_que_nao_ficou_pior(self):
        v = motor.veredito({"agua": "empate", "solo": "alternativa", "erosao": "alternativa"},
                           agua_pela_faixa="depende_da_hipotese")
        self.assertEqual(v["codigo"], "depende")
        self.assertIn("hipótese", v["frase"])
        self.assertNotIn("não ficou pior", v["frase"])


class SedeForte(unittest.TestCase):
    def test_o_nivel_e_a_menor_falta_entre_as_safras_de_quebra(self):
        rendimentos = {"a": 100.0, "b": 50.0, "c": 90.0, "d": 110.0}    # mediana 95; 80% = 76; quebra: só b
        faltas = {"a": 10.0, "b": 40.0, "c": 20.0, "d": 45.0}
        nivel = motor.nivel_de_sede_forte(rendimentos, faltas, 0.8)
        self.assertEqual(nivel["safras_de_quebra"], ["b"])
        self.assertEqual(nivel["nivel_pct"], 40.0)
        self.assertEqual(nivel["limite_kg_ha"], 76.0)
        self.assertEqual(nivel["alarmes_falsos"], ["d"])                # falta alta e colheita boa
        outro = motor.nivel_de_sede_forte(dict(rendimentos, c=60.0), faltas, 0.8)   # mediana 80; 80% = 64
        self.assertEqual(outro["safras_de_quebra"], ["b", "c"])
        self.assertEqual(outro["nivel_pct"], 20.0)

    def test_a_sede_forte_conta_sem_arredondar(self):
        # Achado 3 da revisão: com o nível em 49,64%, a falta de 49,56% fica abaixo, embora as duas apareçam como 49,6.
        forte = motor._com_sede_forte({"a": 49.56, "b": 49.64, "c": 60.0}, 49.64, ["b"])
        self.assertEqual(forte["quais"], ["b", "c"])
        self.assertEqual(forte["nivel_pct"], 49.6)
        self.assertEqual(forte["alarmes_falsos"], ["c"])
        nivel = motor.nivel_de_sede_forte({"a": 100.0, "b": 50.0, "c": 90.0}, {"a": 49.56, "b": 49.64, "c": 10.0}, 0.8)
        self.assertEqual(nivel["nivel_pct"], 49.64)
        self.assertEqual(nivel["alarmes_falsos"], [])

    def test_sem_safra_de_quebra_nao_ha_nivel(self):
        nivel = motor.nivel_de_sede_forte({"a": 100.0, "b": 95.0, "c": 90.0}, {"a": 10.0, "b": 40.0, "c": 20.0}, 0.8)
        self.assertEqual(nivel["safras_de_quebra"], [])
        self.assertIsNone(nivel["nivel_pct"])

    def test_sem_quebra_no_ibge_a_resposta_diz_que_nao_ha_nivel(self):
        r = motor.responder(ENTRADA, rendimentos={s: 7000.0 for s in balanco.SAFRAS_DO_ESTUDO})
        self.assertIsNone(r["sede_forte"]["nivel_pct"])
        self.assertIsNone(r["rotacoes"]["atual"]["safras_com_sede_forte"]["quantas"])
        self.assertEqual(r["rotacoes"]["alternativa"]["safras_com_sede_forte"]["quais"], [])
        texto = explicacao.texto(r)
        self.assertIn("não há nível", texto)
        self.assertEqual(conferencia.conferir_texto(texto, r), [])

    def test_o_nivel_sai_do_ibge_e_nao_esta_escrito_a_mao(self):
        rendimento = {}
        with open(motor.ARQUIVO_DO_IBGE, encoding="utf-8", newline="") as f:
            for linha in csv.DictReader(f):
                if linha["produto"] == "milho_2a_safra":
                    ano = int(linha["ano"])
                    rendimento[f"{ano - 1}-{ano % 100:02d}"] = float(linha["rendimento_kg_ha"])
        rendimento = {s: rendimento[s] for s in balanco.SAFRAS_DO_ESTUDO}
        limite = 0.8 * statistics.median(rendimento.values())
        quebras = [s for s in rendimento if rendimento[s] < limite]
        sede = RESPOSTA["sede_forte"]
        self.assertEqual(sede["safras_de_quebra"], quebras)
        self.assertTrue(quebras)
        hoje = RESPOSTA["rotacoes"]["atual"]["safras"]                  # a resposta padrão é a referência
        self.assertEqual(sede["nivel_pct"], min(hoje[s]["milho"]["falta_relativa_pct"] for s in quebras))
        # Com outro rendimento, outro nível: a quebra passa a ser só a safra de menor falta do milho.
        menor = min(hoje, key=lambda s: hoje[s]["milho"]["falta_relativa_pct"])
        trocado = {s: (1000.0 if s == menor else 7000.0) for s in rendimento}
        outra = motor.responder(ENTRADA, rendimentos=trocado)
        self.assertEqual(outra["sede_forte"]["safras_de_quebra"], [menor])
        self.assertEqual(outra["sede_forte"]["nivel_pct"], hoje[menor]["milho"]["falta_relativa_pct"])
        self.assertEqual(outra["rotacoes"]["atual"]["safras_com_sede_forte"]["quantas"], 10)

    def test_cada_rotacao_conta_as_safras_no_nivel_e_diz_quais(self):
        par, quebras = parametros.carregar(), RESPOSTA["sede_forte"]["safras_de_quebra"]
        referencia = balanco.numeros_por_safra(balanco.simular(DIAS, False, par, "media"))
        nivel = min(referencia[s]["milho"]["falta_relativa_pct"] for s in quebras)      # sem arredondar
        self.assertAlmostEqual(RESPOSTA["sede_forte"]["nivel_pct"], nivel, delta=0.05)
        meio = parametros.valor(par, "disputa_com_o_milho", "meio")
        for nome, com_braquiaria, disputa in (("atual", False, 0.0), ("alternativa", True, meio)):
            numeros = balanco.numeros_por_safra(balanco.simular(DIAS, com_braquiaria, par, "media", disputa=disputa))
            quais = [s for s in balanco.SAFRAS_DO_ESTUDO if numeros[s]["milho"]["falta_relativa_pct"] >= nivel]
            rot = RESPOSTA["rotacoes"][nome]
            self.assertEqual(rot["safras_com_sede_forte"]["quais"], quais)
            self.assertEqual(rot["safras_com_sede_forte"]["quantas"], len(quais))
            self.assertEqual(rot["safras_com_sede_forte"]["nivel_pct"], RESPOSTA["sede_forte"]["nivel_pct"])
            self.assertEqual(rot["safras_com_sede_forte"]["alarmes_falsos"], [s for s in quais if s not in quebras])
            self.assertEqual(rot["safras_com_sede_forte"]["quebras_abaixo_do_nivel"],
                             [s for s in quebras if s not in quais])
            self.assertEqual(rot["safras_com_sede"]["criterio_pct"], 20)          # os campos antigos continuam
            self.assertIn("com_10_pct", rot["safras_com_sede"])
            self.assertIn("com_30_pct", rot["safras_com_sede"])
        faixa = RESPOSTA["rotacoes"]["alternativa"]["safras_com_sede_forte"]["faixa"]
        self.assertLessEqual(faixa["menor"], faixa["maior"])

    def test_o_nivel_e_o_mesmo_em_qualquer_terra_e_leva_o_aviso(self):
        pouca = motor.responder(dict(ENTRADA, terra="pouca"))
        self.assertEqual(pouca["sede_forte"]["nivel_pct"], RESPOSTA["sede_forte"]["nivel_pct"])
        forte = pouca["rotacoes"]["atual"]["safras_com_sede_forte"]      # o alarme falso aparece com o nome da safra
        if forte["alarmes_falsos"]:
            self.assertIn("alarme falso (sede forte na conta, sem quebra no IBGE): " + forte["alarmes_falsos"][0],
                          explicacao.texto(pouca))
        aviso = RESPOSTA["sede_forte"]["aviso"]
        self.assertIn("alarme falso", aviso)
        self.assertIn("poucas safras", aviso)
        texto = explicacao.texto(RESPOSTA)
        self.assertIn("alarme falso", texto)
        self.assertIn("sede forte", texto)


class Texto(unittest.TestCase):
    def test_todo_numero_do_texto_esta_na_conta_nas_3_terras(self):
        for terra in ("pouca", "media", "muita"):
            resposta = motor.responder(dict(ENTRADA, terra=terra))
            self.assertEqual(conferencia.conferir_texto(explicacao.texto(resposta), resposta), [], terra)

    def test_o_texto_mostra_a_alternativa_como_faixa_e_os_limites_novos(self):
        texto = explicacao.texto(RESPOSTA)
        for trecho in ("palha", "disputa", "sem disputa", "hipótese"):
            self.assertIn(trecho, texto)
        self.assertFalse(any("não mede o efeito da palha" in limite for limite in RESPOSTA["limites"]))


class MensagemCurta(unittest.TestCase):
    """O texto curto da API (mensagem.py) não pode contradizer o veredito da água pela faixa."""

    def test_a_mensagem_diz_o_veredito_pela_faixa_e_cabe_no_limite(self):
        from orbita import mensagem
        # Sem "(nota 5)" desde 2026-11-15: as notas de 1 a 5 saíram do motor (decisão do dono).
        palavras = {"alternativa_melhor": "Água: a alternativa se saiu melhor.",
                    "alternativa_pior": "Água: a alternativa se saiu pior.", "empate": "Água: empate.",
                    "depende_da_hipotese": "Água: depende da hipótese"}
        for terra in ("pouca", "media", "muita"):
            r = motor.responder(dict(ENTRADA, terra=terra))
            texto = mensagem.texto(r)
            self.assertLessEqual(len(texto), mensagem.LIMITE, terra)
            self.assertIn(palavras[r["comparacao"]["agua"]["pela_faixa"]["codigo"]], texto, terra)
            faixa = r["rotacoes"]["alternativa"]["faixa"][r["comparacao"]["pior_ano"]]["falta_total_mm"]
            self.assertIn(f"de {explicacao.n(faixa['menor'])} a {explicacao.n(faixa['maior'])} mm na alternativa", texto)
            self.assertEqual(conferencia.conferir_texto(texto, r), [], terra)

    def test_sem_os_campos_novos_a_mensagem_sai_como_antes(self):
        from orbita import mensagem
        r = copy.deepcopy(RESPOSTA)
        del r["rotacoes"]["alternativa"]["faixa"]
        for p in r["pontos_medidos"]:
            p.pop("veredito_pela_faixa", None)
        texto = mensagem.texto(r)
        self.assertIn(mensagem.QUEM[RESPOSTA["comparacao"]["agua"]["melhor"]], texto)
        self.assertNotIn("Água (nota 5): depende", texto)


if __name__ == "__main__":
    unittest.main()
