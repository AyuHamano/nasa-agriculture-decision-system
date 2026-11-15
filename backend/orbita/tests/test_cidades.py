# Gerado com IA (Claude)
"""Testes das cidades novas (Jataí e Silvânia): os dados guardados, com o endereço e a hora, e a resposta do motor."""
import datetime
import json
import unittest

from orbita import clima, conferencia, explicacao, mensagem, motor

ENTRADA = {"rotacao_atual": ["soja", "milho", "pousio"], "terra": "media"}
RESPOSTAS = {cidade: motor.responder(dict(ENTRADA, cidade_id=cidade)) for cidade in motor.CIDADES}
NOVAS = ("jatai", "silvania")


def erro_de(entrada):
    with unittest.TestCase().assertRaises(ValueError) as erro:
        motor.validar_entrada(entrada)
    return str(erro.exception)


class DadosGuardados(unittest.TestCase):
    def test_cada_cidade_nova_tem_o_endereco_e_a_hora_de_cada_consulta(self):
        for cidade in NOVAS:
            pastas, ponto = clima.pastas_da_cidade(cidade), motor.CIDADES[cidade]
            consulta = (pastas["nasa_power"] / "consulta.txt").read_text(encoding="utf-8").strip()
            self.assertTrue(consulta.startswith("https://power.larc.nasa.gov/api/temporal/daily/point?"), cidade)
            self.assertIn(f"latitude={ponto['latitude']}", consulta)
            self.assertIn(f"longitude={ponto['longitude']}", consulta)
            datetime.datetime.fromisoformat((pastas["nasa_power"] / "baixado-em.txt").read_text().strip())
            fonte = json.loads((pastas["chuva"] / "fonte.json").read_text(encoding="utf-8"))
            for registro in fonte["fontes"]["imerg"]["consultas"]:
                self.assertIn("IMERG_PRECTOT", registro["endereco"])
                datetime.datetime.fromisoformat(registro["baixado_em"])
            self.assertEqual(fonte["ponto"]["latitude"], ponto["latitude"])

    def test_a_serie_de_cada_cidade_e_do_ponto_dela(self):
        for cidade in NOVAS:
            bruto = json.loads((clima.pastas_da_cidade(cidade)["nasa_power"] / "resposta.json").read_text())
            self.assertEqual(bruto["geometry"]["coordinates"][:2],
                             [motor.CIDADES[cidade]["longitude"], motor.CIDADES[cidade]["latitude"]])
            dias, avisos = clima.ler_serie_com_aviso("imerg", cidade_id=cidade, lugar="X")
            self.assertEqual(dias[0].data, clima.INICIO_DA_SIMULACAO)
            self.assertGreater(len(dias), 4000)
            self.assertTrue(any("dia de X" in aviso for aviso in avisos))

    def test_so_ha_as_chuvas_guardadas(self):
        self.assertEqual(set(clima.chuvas_guardadas("jatai")), {"imerg", "power"})
        self.assertEqual(set(clima.chuvas_guardadas("rio_verde")), set(clima.FONTES_DE_CHUVA))
        erro = erro_de(dict(ENTRADA, cidade_id="jatai", chuva="chirps"))
        self.assertTrue(erro.startswith("Entrada fora do formato:"), erro)
        self.assertIn("Jataí", erro)
        self.assertIn("imerg", erro)


class Resposta(unittest.TestCase):
    def test_cada_cidade_responde_com_o_seu_lugar_e_os_seus_numeros(self):
        faltas = set()
        for cidade, r in RESPOSTAS.items():
            self.assertEqual(r["local"]["id"], cidade)
            self.assertEqual(r["local"]["nome"], motor.CIDADES[cidade]["nome"])
            self.assertEqual(len(r["rotacoes"]["atual"]["safras"]), 10)
            self.assertEqual(len(r["comparacao_das_rotacoes"]), 3)
            pior = r["comparacao"]["pior_ano"]
            faltas.add(r["rotacoes"]["atual"]["safras"][pior]["total"]["falta_mm"])
        self.assertEqual(len(faltas), 3)                      # três lugares, três contas diferentes
        for cidade in NOVAS:
            self.assertIn(f"data/orbita/cidades/{cidade}/", RESPOSTAS[cidade]["clima"]["chuva"]["origem"])
            self.assertIn(f"latitude={motor.CIDADES[cidade]['latitude']}",
                          RESPOSTAS[cidade]["clima"]["temperatura"]["consulta"])

    def test_a_regra_do_pior_ano_segue_o_que_esta_guardado(self):
        for cidade in NOVAS:
            tem_colheita = clima.pastas_da_cidade(cidade)["ibge"].exists()
            self.assertEqual(RESPOSTAS[cidade]["entrada"]["regra"], "rendimento" if tem_colheita else "chuva")
            if not tem_colheita:    # sem a colheita do IBGE, pedir a regra do rendimento é erro em português
                erro = erro_de(dict(ENTRADA, cidade_id=cidade, regra="rendimento"))
                self.assertIn("IBGE", erro)
                self.assertIsNone(RESPOSTAS[cidade]["sede_forte"]["nivel_pct"])
        self.assertEqual(RESPOSTAS["rio_verde"]["entrada"]["regra"], "rendimento")
        self.assertEqual(motor.responder(dict(ENTRADA, cidade_id="jatai", regra="chuva"))["regra_dos_anos"]["regra"],
                         "chuva")

    def test_o_verde_do_satelite_so_existe_onde_ha_medida(self):
        self.assertTrue(RESPOSTAS["rio_verde"]["ndvi"]["disponivel"])
        for cidade in NOVAS:
            if not list(clima.pastas_da_cidade(cidade)["ndvi"].glob("*.csv")):
                self.assertFalse(RESPOSTAS[cidade]["ndvi"]["disponivel"])
                self.assertIn("Rio Verde", RESPOSTAS[cidade]["ndvi"]["aviso"])
                self.assertEqual(RESPOSTAS[cidade]["terra_coberta"]["pelo_satelite"]["leitura"], "sem_medida")

    def test_os_textos_das_cidades_novas_so_tem_numero_da_conta(self):
        for cidade in NOVAS:
            r = RESPOSTAS[cidade]
            self.assertEqual(conferencia.conferir_texto(explicacao.texto(r), r), [])
            self.assertEqual(conferencia.conferir_texto(mensagem.texto(r), r), [])
            self.assertIn(motor.CIDADES[cidade]["nome"], explicacao.texto(r))

    def test_cidade_que_nao_existe_diz_quais_existem(self):
        erro = erro_de(dict(ENTRADA, cidade_id="sorriso"))
        for cidade in motor.CIDADES:
            self.assertIn(cidade, erro)


if __name__ == "__main__":
    unittest.main()
