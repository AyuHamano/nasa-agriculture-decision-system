# Gerado com IA (Claude)
"""Testes das conversas de exemplo guardadas: o formato que a tela lê, a conferência de cada texto e a chave fora."""
import datetime
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orbita import agente, exportar_conversas, ferramentas
from orbita.modelo import ErroDoModelo, fala
from orbita.tests.duble_do_motor import Duble

HOJE = datetime.date(2026, 11, 15)
CHAVE = "sk-or-chave-de-mentira-0123456789"


class IaDeRoteiro:
    """Uma IA de mentira que conversa de verdade: consulta o que o roteiro da fala manda e depois escreve `texto`."""

    nome = "ia-de-roteiro"

    def __init__(self, texto="Veja a comparação das rotações aqui embaixo.", muda=False):
        self.texto, self.muda, self.uso = texto, muda, {"pedidos": 0, "custo_usd": 0.0}
        self.roteiros = {t: exportar_conversas._roteiro(chamadas, HOJE)
                         for conversa in exportar_conversas.CONVERSAS for t, chamadas in conversa["falas"]}

    def responder(self, mensagens, definicoes):
        self.uso["pedidos"] += 1
        if self.muda:
            return fala("Certo.")
        ultima = mensagens[-1]
        if ultima["de"] != "produtor":
            return fala(self.texto)
        dito = ultima["texto"].split("\n\n[Aviso do programa")[0]
        pedidos = self.roteiros.get(dito) or []
        if dito == "sim":                                    # o roteiro do "sim" depende da pergunta de antes
            pedidos = [exportar_conversas.chamada("verde_do_satelite" if "depois da colheita" in ultima["texto"]
                                                  else "ensaio_da_rotacao")]
        return fala("", *pedidos) if pedidos else fala("A rotação de culturas ajuda a quebrar o ciclo das pragas.")


class AsConversasGuardadas(unittest.TestCase):
    def setUp(self):
        troca = mock.patch.object(ferramentas, "motor", Duble())
        troca.start()
        self.addCleanup(troca.stop)
        ambiente = mock.patch.dict(os.environ)
        ambiente.start()
        self.addCleanup(ambiente.stop)
        os.environ.pop("OPENROUTER_API_KEY", None)
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.pasta = Path(pasta.name) / "dados"

    def gravar(self, ia=None):
        resumo = exportar_conversas.exportar(self.pasta, ia, HOJE)
        return resumo, json.loads((self.pasta / "conversas.json").read_text(encoding="utf-8"))

    def conferir_o_formato(self, objeto):
        self.assertEqual(list(objeto)[:2], ["gerado_em", "gerado_por"])
        conversas = objeto["conversas"]
        self.assertEqual([c["id"] for c in conversas], ["antes-plantei-tarde", "replay-2015-16",
                                                        "depois-o-que-a-terra-mostrou", "sem-conta-pragas-e-adubo"])
        self.assertEqual({c["momento"] for c in conversas}, {"antes", "durante", "depois"})
        for conversa in conversas:
            self.assertEqual(list(conversa), ["id", "momento", "titulo", "texto_de", "replay", "passos"])
            self.assertIn(conversa["texto_de"], ("ia", "frases_prontas"))
            self.assertEqual([p["de"] for p in conversa["passos"]], ["produtor", "agente"] * (len(conversa["passos"]) // 2))
            saidas = [p["saida"] for p in conversa["passos"] if p["de"] == "agente"]
            self.assertIn(conversa["momento"], [s["momento"] for s in saidas])
            for saida in saidas:                                  # cada texto, conferido de novo, um a um
                self.assertEqual(agente.conferir_saida(saida, HOJE), [], saida["resposta"])
                self.assertEqual(saida["aviso"], "Converse com o agrônomo antes de decidir.")
                self.assertIn("estado", saida)
                if saida["ficha"]["confirmada"]:
                    self.assertGreaterEqual(len(saida["comparacao"]), 3)
                else:
                    self.assertIsNone(saida["comparacao"])
            self.assertTrue(saidas[-1]["ficha"]["confirmada"])
        replay = conversas[1]["replay"]
        self.assertEqual((replay["safra"], replay["cidade_id"]), ("2015-16", "rio_verde"))
        self.assertEqual(set(replay["dias"][0]), {"data", "cultura", "chuva_mm", "agua_na_terra_mm", "pedido_mm",
                                                   "bebido_mm", "falta_mm", "com_sede", "tmax_c", "calor_forte"})
        self.assertEqual(set(replay["marcos"][0]), {"data", "tipo", "frase"})
        self.assertIsNone(conversas[0]["replay"])
        sem_conta = conversas[3]["passos"][-1]["saida"]
        self.assertEqual(sem_conta["apoio"], "conhecimento_geral")
        return conversas

    def test_sem_ia_grava_as_4_conversas_com_as_frases_prontas(self):
        resumo, objeto = self.gravar()
        conversas = self.conferir_o_formato(objeto)
        self.assertEqual({c["texto_de"] for c in conversas}, {"frases_prontas"})
        self.assertEqual((objeto["modelo"], resumo["texto_da_ia"], resumo["barrados_pela_conferencia"]), (None, 0, 0))
        self.assertIn("Sem IA", objeto["uso_de_ia"])
        self.assertEqual(conversas[0]["passos"][1]["saida"]["ficha"]["plantio_da_soja"], "2026-11-10")
        self.assertEqual(conversas[3]["passos"][-1]["saida"]["resposta"], agente.SEM_CONTA)

    def test_o_arquivo_da_tela_e_o_mesmo_objeto_e_nao_fica_resto(self):
        _, objeto = self.gravar()
        js = (self.pasta / "conversas.js").read_text(encoding="utf-8")
        self.assertTrue(js.startswith("/* Gerado com IA (Claude) */"))
        inicio = js.index("window.ORBITA_CONVERSAS = ") + len("window.ORBITA_CONVERSAS = ")
        self.assertEqual(json.loads(js[inicio:].rstrip().rstrip(";")), objeto)
        self.assertEqual(sorted(p.name for p in self.pasta.iterdir()), ["conversas.js", "conversas.json"])

    def test_com_a_ia_o_texto_e_dela_e_o_arquivo_diz(self):
        resumo, objeto = self.gravar(IaDeRoteiro())
        conversas = self.conferir_o_formato(objeto)
        self.assertEqual({c["texto_de"] for c in conversas}, {"ia"})
        self.assertEqual(objeto["modelo"], "ia-de-roteiro")
        self.assertIn("conferido contra a conta", objeto["uso_de_ia"])
        self.assertEqual(resumo["avisos"], [])
        self.assertGreater(resumo["texto_da_ia"], 6)
        self.assertTrue(conversas[3]["passos"][-1]["saida"]["resposta"].startswith(agente.AVISO_DE_CONHECIMENTO_GERAL))

    def test_numero_inventado_pela_ia_nao_entra_no_arquivo(self):
        resumo, objeto = self.gravar(IaDeRoteiro("O sorgo rende 999 sacas."))
        conversas = self.conferir_o_formato(objeto)
        saidas = [p["saida"] for c in conversas for p in c["passos"] if p["de"] == "agente"]
        for saida in saidas:                                     # o número não sai no texto nem volta no estado;
            self.assertNotIn("999", saida["resposta"])           # fica só em `sobras`, que diz o que foi barrado
            self.assertNotIn("999", json.dumps(saida["estado"], ensure_ascii=False))
        self.assertIn(["999"], [s["conferencia"]["sobras"] for s in saidas])
        self.assertGreater(resumo["barrados_pela_conferencia"], 0)

    def test_a_ia_que_nao_chega_ao_momento_e_trocada_pelo_roteiro_e_isso_e_dito(self):
        resumo, objeto = self.gravar(IaDeRoteiro(muda=True))
        conversas = self.conferir_o_formato(objeto)
        self.assertEqual(len(resumo["avisos"]), 4)
        self.assertIn("pelo roteiro", resumo["avisos"][0])
        self.assertEqual({c["texto_de"] for c in conversas}, {"frases_prontas"})

    def test_a_chave_nao_entra_em_arquivo_nenhum(self):
        os.environ["OPENROUTER_API_KEY"] = CHAVE
        self.gravar(IaDeRoteiro())
        for arquivo in self.pasta.iterdir():
            self.assertNotIn(CHAVE, arquivo.read_text(encoding="utf-8"))
        self.gravar(IaDeRoteiro("A chave é " + CHAVE))             # com algarismo, a chave já cai na trava dos números
        for arquivo in self.pasta.iterdir():
            self.assertNotIn(CHAVE, arquivo.read_text(encoding="utf-8"))
        so_letras = "sk-or-chave-de-mentira-sem-algarismo"         # sem algarismo, passa pela trava: o gravador barra
        os.environ["OPENROUTER_API_KEY"] = so_letras
        with self.assertRaises(ValueError) as erro:
            exportar_conversas.exportar(self.pasta / "outra", IaDeRoteiro("A chave é " + so_letras), HOJE)
        self.assertNotIn(so_letras, str(erro.exception))
        self.assertFalse((self.pasta / "outra").exists())

    def test_o_comando_diz_o_que_falta_e_fala_como_gente(self):
        with mock.patch("sys.stderr"), mock.patch("sys.stdout"):
            self.assertEqual(exportar_conversas.main([]), 2)
            self.assertEqual(exportar_conversas.main(["--sem-ia"]), 2)
            self.assertEqual(exportar_conversas.main([str(self.pasta), "--sem-ia"]), 0)
            arquivo = self.pasta / "conversas.json"
            self.assertEqual(exportar_conversas.main([str(arquivo), "--sem-ia"]), 1)      # um arquivo não é pasta
            self.assertEqual(exportar_conversas.main([str(self.pasta)]), 0)               # sem chave: frases prontas
            with mock.patch.object(exportar_conversas.modelo, "do_ambiente",
                                   return_value=mock.Mock(responder=mock.Mock(side_effect=ErroDoModelo("caiu")))):
                self.assertEqual(exportar_conversas.main([str(self.pasta)]), 1)

    def test_motor_sem_a_comparacao_nao_grava_nada(self):
        ferramentas.motor.quantas = 2
        with self.assertRaises(ferramentas.ContaIndisponivel):
            exportar_conversas.exportar(self.pasta, None, HOJE)
        self.assertFalse(self.pasta.exists())


if __name__ == "__main__":
    unittest.main()
