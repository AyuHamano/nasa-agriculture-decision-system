# Gerado com IA (Claude)
"""Testes do comando perguntar com as portas novas do motor (a cidade, a rotação, o lugar, o replay, o hoje, o registro)."""
import contextlib
import io
import json
import unittest

from orbita import perguntar


def rodar(argumentos):
    saida, erros = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erros):
        codigo = perguntar.main(argumentos)
    return codigo, saida.getvalue(), erros.getvalue()


class Perguntar(unittest.TestCase):
    def test_a_pergunta_de_jatai_com_plantio_atrasado_e_sorgo_compara_tres_rotacoes(self):
        codigo, saida, erros = rodar(["--cidade", "jatai", "--rotacao", "soja,sorgo", "--plantio", "2026-11-20",
                                      "--json"])
        self.assertEqual(codigo, 0, erros)
        resposta = json.loads(saida)
        self.assertEqual(resposta["local"]["nome"], "Jataí (GO)")
        self.assertEqual(len(resposta["comparacao_das_rotacoes"]), 3)
        self.assertEqual([i["id"] for i in resposta["comparacao_das_rotacoes"] if i["de_hoje"]], ["soja_sorgo_pousio"])
        codigo, texto, erros = rodar(["--cidade", "jatai", "--rotacao", "soja,sorgo", "--plantio", "2026-11-20"])
        self.assertEqual((codigo, erros), (0, ""))                # sem sobra de número na conferência do texto
        self.assertIn("AS ROTAÇÕES LADO A LADO", texto)
        self.assertIn("(a rotação de hoje)", texto)

    def test_cada_porta_nova_responde_em_texto_e_em_json(self):
        for argumentos, chave in ((["--cidade", "silvania", "--lugar"], "regra_dos_anos"), (["--verde"], "leitura"),
                                  (["--replay", "2015-16"], "marcos"), (["--hoje"], "ultimo_dia_com_dado"),
                                  (["--registro", "2015-16"], "o_que_foi_plantado")):
            codigo, texto, erros = rodar(argumentos)
            self.assertEqual((codigo, erros), (0, ""), argumentos)
            self.assertGreater(len(texto), 50, argumentos)
            codigo, saida, _ = rodar(argumentos + ["--json"])
            self.assertEqual(codigo, 0)
            self.assertIn(chave, json.loads(saida), argumentos)

    def test_as_notas_de_1_a_5_sairam_do_comando(self):
        # decisão do dono, 2026-11-15: --agua, --solo, --renda e --erosao deixaram de existir
        for opcao in ("--agua", "--solo", "--renda", "--erosao"):
            codigo, saida, erros = rodar([opcao, "5"])
            self.assertEqual((codigo, saida), (2, ""), opcao)
            self.assertIn("Comando fora do formato", erros)
            self.assertNotIn("--agua 5", erros.split("Exemplo:")[-1])      # o exemplo do erro já não traz as notas
        codigo, saida, erros = rodar(["--terra", "media", "--json"])
        self.assertEqual(codigo, 0, erros)
        self.assertIsNone(json.loads(saida)["entrada"].get("prioridades"))

    def test_entrada_errada_devolve_a_frase_em_portugues_sem_erro_cru(self):
        for argumentos in (["--cidade", "sorriso"], ["--rotacao", "soja,algodao"], ["--plantio", "20/11/2026"],
                           ["--preocupacao", "preco"], ["--replay", "1990-91"], ["--terra", "barro", "--hoje"],
                           ["--registro", "2015"]):
            codigo, saida, erros = rodar(argumentos)
            self.assertEqual(codigo, 2, argumentos)
            self.assertIn("Entrada fora do formato:", erros, argumentos)
            self.assertNotIn("Traceback", erros)
            self.assertEqual(saida, "")


if __name__ == "__main__":
    unittest.main()
