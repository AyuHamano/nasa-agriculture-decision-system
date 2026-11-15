# Gerado com IA (Claude)
"""Testes da ficha fechada: só entra valor da lista, e a ficha mudada tem de ser confirmada de novo."""
import datetime
import unittest
from unittest import mock

from orbita import conferencia, ferramentas, ficha
from orbita.tests.duble_do_motor import Duble

HOJE = datetime.date(2026, 11, 15)
COMPLETA = {"cidade_id": "jatai", "rotacao_atual": "soja_milho_pousio", "terra": "media", "preocupacao": "agua"}


class AFicha(unittest.TestCase):
    def setUp(self):
        troca = mock.patch.object(ferramentas, "motor", Duble())
        troca.start()
        self.addCleanup(troca.stop)
        self.listas = ferramentas.listas()

    def anotar(self, campos, de=None):
        return ficha.anotar(de or ficha.nova(), campos, self.listas, HOJE)

    def test_as_listas_vem_do_motor(self):
        self.assertEqual(list(self.listas["cidades"]), ["rio_verde", "jatai", "silvania"])
        self.assertEqual(self.listas["cidades"]["jatai"], "Jataí (GO)")
        self.assertEqual(list(self.listas["rotacoes"]), ["soja_milho_pousio", "soja_milho_braquiaria", "soja_sorgo_pousio"])
        self.assertEqual(self.listas["terras"], ("pouca", "media", "muita"))
        self.assertEqual(self.listas["preocupacoes"], ("agua", "calor", "terra"))

    def test_valor_da_lista_entra_e_a_rotacao_fica_como_a_lista_das_culturas(self):
        f, aceitos, recusados = self.anotar(dict(COMPLETA, plantio_da_soja="2026-11-10"))
        self.assertEqual(recusados, {})
        self.assertEqual(f["rotacao_atual"], ["soja", "milho", "pousio"])
        self.assertEqual((f["cidade_id"], f["terra"], f["plantio_da_soja"], f["preocupacao"]),
                         ("jatai", "media", "2026-11-10", "agua"))
        self.assertEqual(set(aceitos), set(COMPLETA) | {"plantio_da_soja"})
        self.assertTrue(ficha.completa(f))
        self.assertFalse(f["confirmada"])
        self.assertEqual(self.anotar({"rotacao_atual": ["Soja", " sorgo", "pousio"]})[0]["rotacao_atual"],
                         ["soja", "sorgo", "pousio"])

    def test_valor_fora_da_lista_nao_entra(self):
        casos = {"cidade_id": ["goiania", "Jataí", 7, ["jatai"]], "terra": ["barro", "média", 2],
                 "rotacao_atual": ["soja_algodao", ["soja", "algodao"], ["soja"], 5],
                 "preocupacao": ["preco", "pragas", True],
                 "plantio_da_soja": ["10/11/2026", "2026-13-40", "2026-02-30", "ontem", "1999-10-10", "2031-10-10", 20261110]}
        for campo, valores in casos.items():
            for valor in valores:
                f, aceitos, recusados = self.anotar({campo: valor})
                self.assertIsNone(f[campo], (campo, valor))
                self.assertEqual(aceitos, {})
                self.assertIn(campo, recusados)
        f, aceitos, recusados = self.anotar({"telefone": "64999990000", "nome": "José", "cidade_id": "jatai"})
        self.assertEqual((aceitos, set(recusados)), ({"cidade_id": "jatai"}, {"telefone", "nome"}))
        self.assertNotIn("telefone", f)
        self.assertEqual(self.anotar("jatai")[1], {})
        self.assertEqual(self.anotar(None)[1], {})

    def test_valor_vazio_nao_muda_nada_e_o_recusado_nao_apaga_o_que_estava(self):
        f = self.anotar(COMPLETA)[0]
        g, aceitos, recusados = self.anotar({"terra": "barro", "cidade_id": None, "preocupacao": ""}, f)
        self.assertEqual((g, aceitos), (f, {}))
        self.assertEqual(list(recusados), ["terra"])

    def test_mudar_um_valor_desfaz_a_confirmacao_e_repetir_o_mesmo_nao(self):
        f = ficha.confirmar(self.anotar(COMPLETA)[0])
        self.assertTrue(f["confirmada"])
        self.assertTrue(self.anotar({"terra": "media"}, f)[0]["confirmada"])
        mudada = self.anotar({"terra": "pouca"}, f)[0]
        self.assertEqual((mudada["terra"], mudada["confirmada"]), ("pouca", False))
        self.assertTrue(f["confirmada"])                                   # a ficha de antes não foi mexida

    def test_so_confirma_ficha_completa(self):
        f = self.anotar({"cidade_id": "jatai"})[0]
        self.assertEqual(ficha.falta(f), ["rotacao_atual", "terra", "preocupacao"])
        with self.assertRaises(ValueError):
            ficha.confirmar(f)

    def test_ficha_que_vem_de_fora_e_limpa(self):
        suja = {"cidade_id": "marte", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media",
                "preocupacao": "agua", "plantio_da_soja": "amanhã", "confirmada": True, "cpf": "000"}
        limpa = ficha.conferir(suja, self.listas, HOJE)
        self.assertEqual(limpa, dict(ficha.nova(), rotacao_atual=["soja", "milho", "pousio"], terra="media",
                                     preocupacao="agua"))
        self.assertFalse(limpa["confirmada"])                              # incompleta não fica confirmada
        inteira = ficha.conferir(dict(suja, cidade_id="jatai", confirmada=True), self.listas, HOJE)
        self.assertTrue(inteira["confirmada"])
        self.assertFalse(ficha.conferir(dict(suja, cidade_id="jatai", confirmada="sim"), self.listas, HOJE)["confirmada"])
        for torta in (None, "ficha", [], 5):
            self.assertEqual(ficha.conferir(torta, self.listas, HOJE), ficha.nova())

    def test_os_textos_prontos_so_tem_o_que_esta_na_ficha(self):
        f = self.anotar(dict(COMPLETA, plantio_da_soja="2026-11-10"))[0]
        resumo = ficha.resumo(f, self.listas)
        for pedaco in ("Jataí (GO)", "soja → milho safrinha → pousio", "média", "10/11/2026", "a falta de água", '"sim"'):
            self.assertIn(pedaco, resumo)
        self.assertEqual(conferencia.conferir_texto(resumo, f), [])
        self.assertIn("pelo calendário da região", ficha.resumo(self.anotar(COMPLETA)[0], self.listas))
        pergunta = ficha.pergunta_do_que_falta(self.anotar({"cidade_id": "jatai"})[0], self.listas)
        self.assertNotIn("Onde fica", pergunta)
        for pedaco in ("O que você planta hoje", "sorgo", "Se não souber, diga média", "o calor forte ou a terra"):
            self.assertIn(pedaco, pergunta)
        self.assertEqual(conferencia.conferir_texto(pergunta, {}), [])     # nenhuma pergunta pronta leva número

    def test_a_ia_so_ve_listas_fechadas_e_nenhum_dado_pessoal(self):
        definicao = ficha.definicao(self.listas)
        campos = definicao["parametros"]["properties"]
        self.assertEqual(definicao["nome"], "anotar_na_ficha")
        self.assertEqual(set(campos), set(ficha.CAMPOS) | set(ficha.DITOS))
        self.assertEqual(campos["cidade_id"]["enum"], ["rio_verde", "jatai", "silvania"])
        self.assertEqual(campos["rotacao_atual"]["enum"], list(self.listas["rotacoes"]))
        self.assertEqual(campos["terra"]["enum"], ["pouca", "media", "muita"])
        self.assertEqual(campos["preocupacao"]["enum"], ["agua", "calor", "terra"])
        self.assertFalse(definicao["parametros"]["additionalProperties"])

    def test_a_ficha_publica_diz_o_que_falta(self):
        publica = ficha.publica(self.anotar({"cidade_id": "jatai"})[0])
        self.assertEqual(list(publica), list(ficha.CAMPOS) + list(ficha.DITOS) + ["confirmada", "falta"])
        self.assertEqual(publica["falta"], ["rotacao_atual", "terra", "preocupacao"])


    def test_a_rotacao_dita_ganha_a_rotacao_da_conta_pela_regra_fixa(self):
        # A regra (2026-11-15), na ordem: tem sorgo, soja → sorgo → pousio; senão, tem capim ou braquiária, soja →
        # milho → braquiária; senão, soja → milho → pousio. Sem maiúscula nem acento. Quem escolhe é o programa.
        sorgo, capim, sempre = ["soja", "sorgo", "pousio"], ["soja", "milho", "braquiaria"], ["soja", "milho", "pousio"]
        for dito, esperada in (("sorgo e milho", sorgo), ("milho com capim e feijão", capim),
                               ("braquiária e girassol", capim), ("feijão e girassol", sempre),
                               ("sorgo com capim", sorgo),             # o sorgo vem primeiro na regra
                               ("SORGO", sorgo), ("Braquiaria", capim), ("CAPIM", capim)):
            self.assertEqual(ficha.rotacao_parecida(dito, self.listas), esperada, dito)
            f, aceitos, recusados = self.anotar({"rotacao_dita": dito})
            self.assertEqual((f["rotacao_atual"], recusados), (esperada, {}), dito)

    def test_a_rotacao_que_a_ia_mandar_junto_com_a_dita_e_trocada_pela_da_regra(self):
        for da_ia in ("soja_milho_pousio", "soja_milho_braquiaria", ["soja", "milho", "pousio"], "trigo"):
            f, aceitos, recusados = self.anotar({"rotacao_dita": "sorgo e milho", "rotacao_atual": da_ia})
            self.assertEqual((f["rotacao_dita"], f["rotacao_atual"]), ("sorgo e milho", ["soja", "sorgo", "pousio"]))
            self.assertEqual(aceitos["rotacao_atual"], ["soja", "sorgo", "pousio"])
            self.assertNotIn("rotacao_atual", recusados)
        # a ficha que vem de fora (o estado que a tela devolve) passa pela mesma regra
        de_fora = dict(ficha.nova(), rotacao_dita="sorgo e milho", rotacao_atual=["soja", "milho", "pousio"])
        self.assertEqual(ficha.conferir(de_fora, self.listas, HOJE)["rotacao_atual"], ["soja", "sorgo", "pousio"])
        # e a rotação da lista, dita depois, apaga o "dito" de antes
        f = self.anotar({"rotacao_atual": "soja_milho_braquiaria"}, de=f)[0]
        self.assertEqual((f["rotacao_dita"], f["rotacao_atual"]), (None, ["soja", "milho", "braquiaria"]))

    def test_o_pedido_a_ia_diz_que_quem_escolhe_a_rotacao_da_conta_e_o_programa(self):
        definicao = ficha.definicao(self.listas)
        for texto in (definicao["descricao"], definicao["parametros"]["properties"]["rotacao_dita"]["description"]):
            self.assertIn("quem escolhe a rotação da conta é o programa", texto)
            self.assertNotIn("mais culturas em comum", texto)


if __name__ == "__main__":
    unittest.main()
