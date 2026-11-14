# Gerado com IA (Claude)
"""Testes do exportar: o respostas.js que o site lê e o respostas.json igual, numa pasta temporária."""
import contextlib
import datetime
import io
import json
import tempfile
import unittest
from pathlib import Path

from orbita import exportar, motor

COMECO = "window.ORBITA_RESPOSTAS = "


def rodar(argumentos):
    saida, erros = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erros):
        codigo = exportar.main(argumentos)
    return codigo, saida.getvalue(), erros.getvalue()


class Exportar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporaria = tempfile.TemporaryDirectory()
        cls.pasta = Path(cls.temporaria.name) / "site" / "dados"            # ainda não existe: o exportar cria
        cls.codigo, cls.saida, cls.erros = rodar([str(cls.pasta)])
        cls.js = (cls.pasta / "respostas.js").read_text(encoding="utf-8")
        cls.dados = json.loads((cls.pasta / "respostas.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.temporaria.cleanup()

    def do_js(self):
        linha = next(linha for linha in self.js.split("\n") if linha.startswith(COMECO))
        self.assertTrue(linha.endswith(";"))
        return json.loads(linha[len(COMECO):-1])

    def test_grava_os_dois_arquivos_e_diz_onde(self):
        self.assertEqual(self.codigo, 0)
        self.assertEqual(sorted(p.name for p in self.pasta.iterdir()), ["respostas.js", "respostas.json"])
        self.assertIn("respostas.js", self.saida)
        self.assertIn("respostas.json", self.saida)

    def test_o_js_tem_o_cabecalho_e_a_resposta_inteira_de_cada_terra_com_as_notas_iguais_a_3(self):
        self.assertTrue(self.js.startswith("/* Gerado com IA (Claude) */"))
        self.assertEqual(self.js.count(COMECO), 1)
        respostas = self.do_js()
        self.assertEqual(list(respostas), ["pouca", "media", "muita"])
        for terra in respostas:
            entrada = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"],
                       "prioridades": {"agua": 3, "solo": 3, "renda": 3, "erosao": 3}, "terra": terra}
            self.assertEqual(respostas[terra], json.loads(json.dumps(motor.responder(entrada))))

    def test_o_json_e_igual_e_leva_a_hora_e_os_parametros_usados(self):
        self.assertEqual(self.dados["respostas"], self.do_js())
        gerado = datetime.datetime.fromisoformat(self.dados["gerado_em"])
        self.assertIsNotNone(gerado.tzinfo)
        self.assertLess(abs((datetime.datetime.now(datetime.timezone.utc) - gerado).total_seconds()), 600)
        self.assertIn(self.dados["gerado_em"], self.js)                      # a mesma hora nos dois
        usados = self.dados["parametros_usados"]
        self.assertEqual(usados["prioridades"], {"agua": 3, "solo": 3, "renda": 3, "erosao": 3})
        self.assertEqual(usados["terras"], ["pouca", "media", "muita"])
        self.assertEqual((usados["cidade_id"], usados["rotacao_atual"]), ("rio_verde", ["soja", "milho", "pousio"]))
        self.assertEqual((usados["chuva"], usados["regra"]), ("imerg", "rendimento"))   # o que o motor usou de fato

    def test_rodar_de_novo_troca_os_arquivos_e_nao_deixa_sobra(self):
        codigo, _, _ = rodar([str(self.pasta)])
        self.assertEqual(codigo, 0)
        self.assertEqual(sorted(p.name for p in self.pasta.iterdir()), ["respostas.js", "respostas.json"])

    def test_sem_a_pasta_ou_com_um_arquivo_no_lugar_diz_o_que_fazer(self):
        codigo, _, erros = rodar([])
        self.assertEqual(codigo, 2)
        self.assertIn("python3 -m orbita.exportar", erros)
        codigo, _, erros = rodar([str(self.pasta / "respostas.js")])          # é um arquivo, não uma pasta
        self.assertEqual(codigo, 1)
        self.assertIn("pasta", erros)


if __name__ == "__main__":
    unittest.main()
