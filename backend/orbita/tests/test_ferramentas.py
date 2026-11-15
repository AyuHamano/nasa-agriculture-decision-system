# Gerado com IA (Claude)
"""Testes das 3 ferramentas do agente, com o dublê do motor no formato combinado (o mapa, seção 7)."""
import json
import unittest
from unittest import mock

from orbita import ferramentas, motor
from orbita.tests.duble_do_motor import Duble

FICHA = {"cidade_id": "jatai", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media",
         "plantio_da_soja": "2026-11-10", "preocupacao": "agua", "confirmada": True}


def com_o_duble(caso, **opcoes):
    duble = Duble(**opcoes)
    troca = mock.patch.object(ferramentas, "motor", duble)
    troca.start()
    caso.addCleanup(troca.stop)
    return duble


class OEnsaio(unittest.TestCase):
    def test_devolve_a_comparacao_de_3_rotacoes_como_o_motor_mandou(self):
        duble = com_o_duble(self)
        ensaio = ferramentas.ensaio_da_rotacao(FICHA)
        self.assertEqual(list(ensaio), ["lugar", "pior_ano", "ano_normal", "calendario", "rotacoes"])
        self.assertEqual(ensaio["calendario"]["plantio_da_soja_informado"], "2026-11-10")      # repassado do motor
        self.assertEqual(ensaio["calendario"]["milho"], {"plantio": "08/03", "sai_da_terra": "11/07"})
        self.assertEqual((ensaio["lugar"], ensaio["pior_ano"], ensaio["ano_normal"]), ("Jataí (GO)", "2015-16", "2019-20"))
        self.assertEqual(ensaio["rotacoes"], json.loads(json.dumps(duble.responder(ferramentas.entrada_do_motor(FICHA))
                                                                   ["comparacao_das_rotacoes"])))
        self.assertEqual([r["de_hoje"] for r in ensaio["rotacoes"]], [True, False, False])

    def test_a_entrada_do_motor_leva_so_os_campos_combinados(self):
        self.assertEqual(ferramentas.entrada_do_motor(FICHA), {
            "cidade_id": "jatai", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media",
            "plantio_da_soja": "2026-11-10", "preocupacao": "agua"})
        sem_opcionais = dict(FICHA, plantio_da_soja=None, preocupacao=None)
        self.assertEqual(list(ferramentas.entrada_do_motor(sem_opcionais)), ["cidade_id", "rotacao_atual", "terra"])

    def test_menos_de_3_rotacoes_nao_passa(self):
        com_o_duble(self, rotacoes=2)
        with self.assertRaises(ferramentas.ContaIndisponivel) as erro:
            ferramentas.ensaio_da_rotacao(FICHA)
        self.assertIn("2 rotações", str(erro.exception))

    def test_comparacao_torta_nao_passa(self):
        boa = Duble().responder(ferramentas.entrada_do_motor(FICHA))["comparacao_das_rotacoes"]
        self.assertIs(ferramentas.conferir_comparacao(boa), boa)
        sem_risco = json.loads(json.dumps(boa))
        sem_risco[1]["risco"] = "  "
        sem_a_de_hoje = [dict(item, de_hoje=False) for item in boa]
        sem_nome = [dict(boa[0], nome=""), boa[1], boa[2]]
        for torta in (None, {}, boa[:2], sem_risco, sem_a_de_hoje, sem_nome, [1, 2, 3]):
            with self.assertRaises(ferramentas.ContaIndisponivel):
                ferramentas.conferir_comparacao(torta)

    def test_com_a_safra_traz_o_replay_e_a_ia_nao_recebe_os_dias(self):
        com_o_duble(self)
        for pedida in ("2015-16", "pior_ano"):
            replay = ferramentas.ensaio_da_rotacao(FICHA, pedida)["replay"]
            self.assertEqual((replay["safra"], replay["cidade_id"]), ("2015-16", "jatai"))
            self.assertEqual(len(replay["dias"]), 20)
            self.assertEqual([m["tipo"] for m in replay["marcos"]], ["plantio", "agua_acabou", "calor_forte", "colheita"])
        lido = ferramentas.para_a_ia(ferramentas.ensaio_da_rotacao(FICHA, "pior_ano"))
        self.assertNotIn("dias", lido["replay"])
        self.assertEqual(len(lido["replay"]["marcos"]), 4)
        self.assertEqual(len(lido["rotacoes"]), 3)

    def test_safra_torta_volta_como_erro_para_a_ia_ler(self):
        com_o_duble(self)
        for torta in ("2015", "a pior", "15-16", "2015-2016"):
            self.assertIn("erro", ferramentas.chamar("ensaio_da_rotacao", FICHA, {"safra": torta}))
        self.assertIn("erro", ferramentas.chamar("verde_do_satelite", FICHA, {"safra": 2015}))
        self.assertIn("erro", ferramentas.chamar("apagar_tudo", FICHA, {}))

    def test_o_que_o_motor_recusa_na_ficha_vira_ficha_recusada(self):
        com_o_duble(self, recusar="o plantio da soja tem de ficar entre setembro e dezembro.")
        with self.assertRaises(ferramentas.FichaRecusada) as erro:
            ferramentas.chamar("ensaio_da_rotacao", FICHA, {})
        self.assertIn("entre setembro e dezembro", str(erro.exception))


class OClimaEOVerde(unittest.TestCase):
    def test_o_clima_do_lugar_e_o_como_esta_hoje(self):
        duble = com_o_duble(self)
        clima = ferramentas.clima_do_lugar(FICHA)
        self.assertEqual(clima["regra_dos_anos"], {"pior_ano": "2015-16", "ano_normal": "2019-20"})
        self.assertNotIn("hoje", clima)
        self.assertEqual(ferramentas.chamar("clima_do_lugar", FICHA, {"hoje": True})["hoje"]["agua_na_terra_mm"], 71.5)
        self.assertEqual(duble.chamadas, ["clima_do_lugar", "clima_do_lugar", "como_esta_hoje"])

    def test_sem_o_como_esta_hoje_no_motor_sai_o_aviso(self):
        com_o_duble(self, com_hoje=False)
        hoje = ferramentas.clima_do_lugar(FICHA, hoje=True)["hoje"]
        self.assertEqual(hoje, {"disponivel": False, "aviso": ferramentas.AVISO_SEM_HOJE})

    def test_o_verde_do_satelite_e_o_registro_da_safra(self):
        com_o_duble(self)
        verde = ferramentas.verde_do_satelite(FICHA)
        self.assertEqual((verde["dias_pelo_calendario"], verde["dias_pelo_satelite"]), (122, 96))
        self.assertNotIn("registro", verde)
        registro = ferramentas.chamar("verde_do_satelite", FICHA, {"safra": "pior_ano"})["registro"]
        self.assertEqual((registro["safra"], registro["falta_de_agua_mm"]), ("2015-16", 232.9))

    def test_sem_o_registro_no_motor_sai_o_aviso(self):
        com_o_duble(self, com_registro=False)
        registro = ferramentas.verde_do_satelite(FICHA, "2015-16")["registro"]
        self.assertEqual(registro, {"disponivel": False, "safra": "2015-16", "aviso": ferramentas.AVISO_SEM_REGISTRO})


class OQueAIaLe(unittest.TestCase):
    def test_as_3_ferramentas_tem_nome_descricao_e_parametros(self):
        definicoes = ferramentas.definicoes()
        self.assertEqual(tuple(d["nome"] for d in definicoes), ferramentas.NOMES)
        for definicao in definicoes:
            self.assertGreater(len(definicao["descricao"]), 60)
            self.assertEqual(definicao["parametros"]["type"], "object")
            self.assertFalse(definicao["parametros"]["additionalProperties"])

    def test_o_que_passa_do_teto_e_cortado_e_dito(self):
        grande = {"pequeno": 1, "enorme": ["x" * 100] * 400, "medio": "y" * 50, "dias": [1, 2, 3]}
        lido = ferramentas.para_a_ia(grande)
        self.assertEqual(lido, {"pequeno": 1, "medio": "y" * 50, "cortado_por_tamanho": ["enorme"]})
        com_a_comparacao = {"rotacoes": ["x" * 100] * 400, "outro": "y" * 50}        # a comparação nunca é cortada
        self.assertEqual(ferramentas.para_a_ia(com_a_comparacao)["rotacoes"], com_a_comparacao["rotacoes"])
        self.assertEqual(ferramentas.para_a_ia({"a": [{"dias": [1], "b": 2}]}), {"a": [{"b": 2}]})


class ComOMotorDeVerdade(unittest.TestCase):
    """O encaixe com o motor de verdade. O que depende das funções novas só roda quando elas existem."""

    def test_as_listas_saem_do_motor_de_verdade(self):
        listas = ferramentas.listas()
        self.assertIn("rio_verde", listas["cidades"])
        self.assertEqual(listas["terras"], tuple(motor.TERRAS))
        self.assertIn(["soja", "milho", "pousio"], [r["culturas"] for r in listas["rotacoes"].values()])

    def test_funcao_que_o_motor_ainda_nao_tem_vira_conta_que_nao_esta_ligada(self):
        for nome in ("clima_do_lugar", "verde_do_satelite"):
            if not hasattr(motor, nome):                         # depois da junção das partes, o motor tem as duas
                with self.assertRaises(ferramentas.ContaIndisponivel) as erro:
                    ferramentas.chamar(nome, dict(FICHA, cidade_id="rio_verde"), {})
                self.assertIn(nome, str(erro.exception))

    @unittest.skipUnless(hasattr(motor, "clima_do_lugar") and hasattr(motor, "verde_do_satelite"),
                         "o motor ainda não tem as funções novas (chegam na junção das partes)")
    def test_com_as_funcoes_novas_cada_cidade_e_cada_rotacao_do_cardapio_da_3_rotacoes(self):
        listas = ferramentas.listas()
        self.assertGreaterEqual(len(listas["rotacoes"]), 3)
        for cidade in listas["cidades"]:
            for rotacao in listas["rotacoes"].values():
                ficha_do_lugar = dict(FICHA, cidade_id=cidade, rotacao_atual=rotacao["culturas"], plantio_da_soja=None)
                ensaio = ferramentas.ensaio_da_rotacao(ficha_do_lugar)
                self.assertGreaterEqual(len(ensaio["rotacoes"]), 3, (cidade, rotacao))
                self.assertEqual([r["de_hoje"] for r in ensaio["rotacoes"]].count(True), 1, (cidade, rotacao))
                self.assertTrue(ensaio["pior_ano"] and ensaio["ano_normal"])
            self.assertIn("regra_dos_anos", ferramentas.clima_do_lugar(dict(FICHA, cidade_id=cidade)))
            self.assertIsInstance(ferramentas.verde_do_satelite(dict(FICHA, cidade_id=cidade)), dict)
        replay = ferramentas.ensaio_da_rotacao(dict(FICHA, cidade_id="rio_verde", plantio_da_soja=None), "pior_ano")["replay"]
        self.assertTrue(replay["dias"] and replay["marcos"])


class OPainelQueVaiAIa(unittest.TestCase):
    """O painel da lavoura hoje, como a IA o lê: sem a leitura do agrônomo (o atraso do dado, o que não chegou)."""
    PROIBIDO = ("atras", "último dia com dado", "aproximad", "ainda não chegou")

    def frases(self, coisa):
        if isinstance(coisa, dict):
            for chave, valor in coisa.items():
                yield str(chave)
                yield from self.frases(valor)
        elif isinstance(coisa, list):
            for item in coisa:
                yield from self.frases(item)
        elif isinstance(coisa, str):
            yield coisa

    @unittest.skipUnless(hasattr(motor, "lavoura_hoje"), "o motor ainda não tem o painel da lavoura hoje")
    def test_nenhuma_frase_do_painel_que_vai_a_ia_fala_de_atraso_nas_3_cidades(self):
        cidades, cardapio = ferramentas.listas()["cidades"], ferramentas.listas()["rotacoes"]
        self.assertEqual(len(cidades), 3)
        for cidade in cidades:
            for rotacao in cardapio.values():
                ficha_da_cidade = dict(FICHA, cidade_id=cidade, rotacao_atual=rotacao["culturas"], plantio_da_soja=None)
                painel = ferramentas.para_a_ia(ferramentas.chamar("lavoura_hoje", ficha_da_cidade, {}))
                self.assertTrue(painel["disponivel"] and len(painel["itens"]) == 6, cidade)
                for frase in self.frases(painel):
                    for proibido in self.PROIBIDO:
                        self.assertNotIn(proibido, frase.lower(), (cidade, rotacao["culturas"]))
                for item in painel["itens"]:                     # nenhum campo técnico chega, nem curto
                    self.assertEqual([c for c in item if c in ferramentas.FORA_DO_PAINEL and c != "situacao"], [])
                self.assertEqual([c for c in painel if c in ferramentas.FORA_DO_PAINEL and c != "situacao"], [])

    def test_o_campo_tecnico_curto_de_um_item_nao_passa(self):
        item = {"id": "fase", "situacao_nome": "tranquilo", "frase": "Na terra está a soja.", "dias": 12,
                "detalhe_tecnico": "14/11/2026 é o último dia com dado.", "regra_da_situacao": "curta",
                "ultimo_dado": {"data": "2026-11-14", "de": "da chuva"}, "ultimo_dia_com_dado_de": "da conta"}
        self.assertEqual(ferramentas._item_do_painel(item),
                         {"id": "fase", "situacao": "tranquilo", "frase": "Na terra está a soja.", "dias": 12})


if __name__ == "__main__":
    unittest.main()
