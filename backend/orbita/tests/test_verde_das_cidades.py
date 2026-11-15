# Gerado com IA (Claude)
"""O verde do satélite (NDVI) de Jataí e de Silvânia: os pontos baixados em 2026-11-15, o aviso e a fonte de cada cidade."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orbita import clima, conferencia, motor, ndvi

NOVAS = ("jatai", "silvania")


class VerdeDasCidades(unittest.TestCase):
    def test_cada_cidade_nova_tem_6_pontos_com_a_fonte_ao_lado(self):
        for cidade in NOVAS:
            pasta = clima.pastas_da_cidade(cidade)["ndvi"]
            fonte = json.loads((pasta / "fonte.json").read_text(encoding="utf-8"))
            self.assertEqual(len(list(pasta.glob("*.csv"))), 6, cidade)
            self.assertEqual(sorted(p["arquivo"] for p in fonte["pontos"]), sorted(a.name for a in pasta.glob("*.csv")))
            self.assertIn("não se sabe de quem são", fonte["regra_da_escolha"]["aviso"])
            for ponto in fonte["pontos"]:                    # o endereço e a hora de cada consulta ficam guardados
                self.assertTrue(ponto["busca_no_catalogo"][0]["endereco"].startswith("https://planetarycomputer."))
                with (pasta / ponto["arquivo"]).open(encoding="utf-8", newline="") as f:
                    linhas = list(csv.DictReader(f))
                self.assertTrue(all(linha["consultado_em_utc"] and linha["item"].startswith("MOD13Q1.") for linha in linhas))
                self.assertEqual((float(linhas[0]["lat"]), float(linhas[0]["lon"])), (ponto["lat"], ponto["lon"]))

    def test_os_pontos_escolhidos_passaram_no_mapa_de_uso_da_terra(self):
        for cidade in NOVAS:
            fonte = json.loads((clima.pastas_da_cidade(cidade)["ndvi"] / "fonte.json").read_text(encoding="utf-8"))
            passaram = [c for c in fonte["candidatos"] if c["passou"]]
            self.assertEqual([c["nome"] + ".csv" for c in passaram[:6]], [p["arquivo"] for p in fonte["pontos"]])
            for candidato in passaram[:6]:
                self.assertEqual({leitura["classe"] for leitura in candidato["leituras"]}, {5})
                self.assertEqual(len(candidato["leituras"]), 10)

    def test_o_motor_le_o_verde_das_cidades_novas(self):
        for cidade in NOVAS:
            verde = motor.verde_do_satelite(cidade)
            nome = motor.CIDADES[cidade]["nome"]
            self.assertIn(verde["leitura"], ("bate", "dentro_da_faixa", "fora_da_faixa"), cidade)
            self.assertEqual(verde["dias_pelo_satelite"],
                             ndvi.resumo(pasta=clima.pastas_da_cidade(cidade)["ndvi"])["mediana"])
            self.assertEqual(conferencia.conferir_texto(verde["frase"], verde), [])
            self.assertIn(f"perto de {nome}", verde["aviso"])
            self.assertNotIn("Rio Verde", verde["aviso"])
            self.assertIn("não foram conferidos em campo", verde["aviso"])
            self.assertEqual(verde["fonte"]["onde_esta"][:len(f"data/orbita/cidades/{cidade}/ndvi/")],
                             f"data/orbita/cidades/{cidade}/ndvi/")
            self.assertEqual(verde["fonte"]["baixado_em"], "2026-11-15")
            self.assertIn("io-lulc-annual-v02", verde["fonte"]["escolha_dos_pontos"])

    def test_a_resposta_da_cidade_nova_traz_o_satelite_na_terra_coberta(self):
        for cidade in NOVAS:
            resposta = motor.responder({"cidade_id": cidade, "rotacao_atual": ["soja", "milho", "pousio"]})
            self.assertTrue(resposta["ndvi"]["disponivel"], cidade)
            self.assertIn(f"perto de {motor.CIDADES[cidade]['nome']}", resposta["ndvi"]["frases"][-1])
            itens = {item["id"]: item for item in resposta["comparacao_das_rotacoes"]}
            self.assertEqual(itens["soja_milho_pousio"]["terra_coberta"]["pelo_satelite"],
                             resposta["ndvi"]["comparacao"]["dias_pelo_satelite"])
            self.assertIsNone(itens["soja_sorgo_pousio"]["terra_coberta"]["pelo_satelite"])

    def test_rio_verde_continua_como_era(self):
        self.assertIn("perto de Rio Verde (GO)", ndvi.AVISO_DOS_PONTOS)
        self.assertEqual(ndvi.aviso_dos_pontos(), ndvi.AVISO_DOS_PONTOS)
        self.assertEqual(ndvi.fonte(), ndvi.FONTE)
        verde = motor.verde_do_satelite("rio_verde")
        self.assertEqual(verde["fonte"], ndvi.FONTE)
        self.assertIn("perto de Rio Verde (GO)", verde["aviso"])

    def test_cidade_sem_arquivo_continua_dizendo_sem_medida(self):
        with tempfile.TemporaryDirectory() as vazia, mock.patch.object(clima, "PASTA_DAS_CIDADES", Path(vazia)):
            sem = motor.verde_do_satelite("silvania")
        self.assertEqual(sem["leitura"], "sem_medida")
        self.assertIsNone(sem["dias_pelo_satelite"])
        self.assertIn("122", sem["frase"])


if __name__ == "__main__":
    unittest.main()
