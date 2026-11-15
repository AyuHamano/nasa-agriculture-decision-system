# Gerado com IA (Claude)
"""Testes do cardápio das rotações e da terceira rotação (soja e sorgo de 2ª safra)."""
import datetime
import json
import unittest

from orbita import balanco, clima, motor, parametros, rotacoes

D = datetime.date
PAR = parametros.carregar()
ENTRADA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "sorgo", "pousio"], "terra": "media"}
RESPOSTA = motor.responder(ENTRADA)
DE_SEMPRE = motor.responder(dict(ENTRADA, rotacao_atual=["soja", "milho", "pousio"]))


class Cardapio(unittest.TestCase):
    def test_tres_rotacoes_com_id_culturas_e_segunda_safra(self):
        self.assertEqual(list(rotacoes.ROTACOES), ["atual", "alternativa", "com_sorgo"])
        self.assertEqual(list(rotacoes.CARDAPIO), ["soja_milho_pousio", "soja_milho_braquiaria", "soja_sorgo_pousio"])
        for rotacao in rotacoes.ROTACOES.values():
            self.assertEqual(rotacao["culturas"][0], "soja")
            self.assertIn(rotacao["segunda"], ("milho", "sorgo"))

    def test_a_rotacao_de_hoje_pode_ser_qualquer_uma_do_cardapio(self):
        for dita, ident in ((["soja", "milho", "pousio"], "soja_milho_pousio"),
                            (["Soja", " Milho ", "Braquiária"], "soja_milho_braquiaria"),
                            (["soja", "sorgo"], "soja_sorgo_pousio"), ("soja_sorgo_pousio", "soja_sorgo_pousio")):
            entrada = motor.validar_entrada(dict(ENTRADA, rotacao_atual=dita))
            self.assertEqual(entrada["rotacao_id"], ident)
            self.assertEqual(entrada["rotacao_atual"], rotacoes.CARDAPIO[ident]["culturas"])

    def test_rotacao_fora_do_cardapio_e_erro_que_mostra_o_cardapio(self):
        for ruim in (["soja", "algodao"], ["milho"], "soja e milho", 3, []):
            with self.assertRaises(ValueError) as erro:
                motor.validar_entrada(dict(ENTRADA, rotacao_atual=ruim))
            texto = str(erro.exception)
            self.assertTrue(texto.startswith("Entrada fora do formato:"), texto)
            self.assertIn('["soja", "sorgo", "pousio"]', texto)


class ParametrosDoSorgo(unittest.TestCase):
    def test_cada_valor_do_sorgo_e_do_calor_tem_fonte_trecho_e_etiqueta(self):
        folhas = dict(parametros.folhas(PAR))
        do_sorgo = [c for c in folhas if c.startswith("culturas.sorgo_2a_safra.")]
        do_calor = [c for c in folhas if c.startswith("calor.")]
        self.assertEqual(len(do_sorgo), 7)
        self.assertGreaterEqual(len(do_calor), 9)
        for caminho in do_sorgo + do_calor:
            p = folhas[caminho]
            self.assertIn(p["etiqueta"], ("publicado", "hipótese"), caminho)
            self.assertTrue(p["trecho"], caminho)
            if p["etiqueta"] == "publicado":
                self.assertTrue(p["fonte"].startswith("http"), caminho)

    def test_o_que_nao_esta_escrito_na_fonte_fica_como_hipotese(self):
        sorgo = PAR["culturas"]["sorgo_2a_safra"]
        self.assertEqual(sorgo["kc_meio"]["etiqueta"], "hipótese")       # a fonte dá a faixa de 1,00 a 1,10
        self.assertEqual(sorgo["raiz_m"]["etiqueta"], "hipótese")        # vale a raiz do milho, para comparar igual
        self.assertEqual(sorgo["kc_fim"]["etiqueta"], "publicado")
        self.assertEqual(PAR["calor"]["maxima_do_dia"]["etiqueta"], "hipótese")
        for cultura in ("soja", "milho", "sorgo"):
            self.assertEqual(PAR["calor"][cultura]["limite_c"]["etiqueta"], "publicado")
            self.assertEqual(PAR["calor"][cultura]["fase_critica"]["etiqueta"], "hipótese")

    def test_o_arquivo_conferido_e_o_programa_dizem_o_mesmo(self):
        arquivo = json.loads(parametros.ARQUIVO_CONFERIDO.read_text(encoding="utf-8"))
        sorgo, padrao = arquivo["culturas"]["sorgo_2a_safra"], parametros.PADRAO["culturas"]["sorgo_2a_safra"]
        self.assertEqual(sorgo["kc_med"]["valor"], padrao["kc_meio"]["valor"])
        self.assertEqual([sorgo[f"fase_{nome}_dias"]["valor"] for nome in ("inicial", "crescimento", "media", "final")],
                         padrao["fases_dias"]["valor"])
        for cultura in ("soja", "milho", "sorgo"):
            self.assertEqual(arquivo["calor"][cultura]["limite_c"]["valor"],
                             parametros.PADRAO["calor"][cultura]["limite_c"]["valor"])


class SorgoNaConta(unittest.TestCase):
    def test_o_sorgo_entra_no_dia_do_milho_e_pede_menos_agua(self):
        cal = rotacoes.calendario(PAR)
        self.assertEqual(cal.plantio_da_segunda(2022, "sorgo"), cal.plantio_do_milho(2022))
        self.assertEqual(rotacoes.cobertura_do_dia(D(2022, 4, 20), False, cal, segunda="sorgo")[0], "sorgo")
        self.assertEqual(rotacoes.cobertura_do_dia(D(2022, 4, 20), False, cal)[0], "milho")
        self.assertLess(rotacoes.cobertura_do_dia(D(2022, 4, 20), False, cal, segunda="sorgo")[1],
                        rotacoes.cobertura_do_dia(D(2022, 4, 20), False, cal)[1])          # Kc 1,05 contra 1,20
        for safra, numeros in RESPOSTA["rotacoes"]["com_sorgo"]["safras"].items():
            milho = RESPOSTA["rotacoes"]["atual"]["safras"][safra]["milho"]
            self.assertLess(numeros["sorgo"]["pedido_mm"], milho["pedido_mm"], safra)
            self.assertEqual(numeros["sorgo"]["dias"], milho["dias"], safra)
            self.assertNotIn("milho", numeros)

    def test_o_total_da_rotacao_com_sorgo_e_a_soja_mais_o_sorgo(self):
        for safra, numeros in RESPOSTA["rotacoes"]["com_sorgo"]["safras"].items():
            self.assertAlmostEqual(numeros["total"]["falta_mm"], numeros["soja"]["falta_mm"]
                                   + numeros["sorgo"]["falta_mm"], delta=0.11, msg=safra)

    def test_o_sorgo_nao_mexe_nos_numeros_das_outras_rotacoes(self):
        for chave in ("atual", "alternativa"):
            self.assertEqual(RESPOSTA["rotacoes"][chave], DE_SEMPRE["rotacoes"][chave])
        for chave in ("comparacao", "veredito", "regra_dos_anos", "sede_forte"):
            self.assertEqual(RESPOSTA[chave], DE_SEMPRE[chave], chave)
        dias, _ = clima.ler_serie_com_aviso("imerg")
        agua = balanco.agua_da_terra(PAR, "media")
        self.assertEqual(agua["raizes_m"]["sem_planta"], 1.0)             # a caixa da terra sem planta não mudou
        self.assertEqual(agua["raizes_m"]["sorgo"], agua["raizes_m"]["milho"])

    def test_a_rotacao_de_hoje_fica_marcada(self):
        self.assertEqual(RESPOSTA["rotacao_de_hoje"]["id"], "soja_sorgo_pousio")
        self.assertEqual(RESPOSTA["rotacao_de_hoje"]["chave"], "com_sorgo")
        self.assertEqual(DE_SEMPRE["rotacao_de_hoje"]["id"], "soja_milho_pousio")
        self.assertEqual(RESPOSTA["calendario"]["sorgo"]["plantio"], RESPOSTA["calendario"]["milho"]["plantio"])
        self.assertEqual(RESPOSTA["rotacoes"]["com_sorgo"]["sem_planta_viva"]["dias_sem_planta_viva"], 122)


if __name__ == "__main__":
    unittest.main()
