# Gerado com IA (Claude)
"""A leitura do produtor em palavras simples (2026-11-15): sem palavra da conta sem explicação, com a data no jeito
brasileiro, e com a conferência dos números passando do mesmo jeito."""
import datetime
import re
import unittest

from orbita import agente, conferencia, exportar_conversas, explicacao, hoje, motor
from orbita.modelo import chamada

RIO_VERDE = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media"}
PROIBIDAS = ("mediana", "zona das raízes", "faixa da hipótese", "chuva de modelo", "franco-arenosa")
DATA_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
DIA = datetime.date(2026, 11, 15)


def _frases_do_produtor(cidade):
    """Tudo o que o motor escreve pronto para o produtor, de uma cidade: [(de onde, a frase, a conta dela)]."""
    entrada = dict(RIO_VERDE, cidade_id=cidade)
    resposta = motor.responder(entrada)
    frases = [(f"{item['id']}.{chave}", item[chave], resposta) for item in resposta["comparacao_das_rotacoes"]
              for chave in ("evidencia", "beneficio", "risco", "falta_saber")]
    agora = motor.como_esta_hoje(entrada, hoje=DIA)
    frases += [("hoje.frase", agora["frase"], agora), ("hoje.aviso", agora["aviso"], agora)]
    registro = motor.registro_da_safra(entrada, "2015-16")
    frases += [("registro.frase", registro["frase"], registro)]
    replay = motor.replay_da_safra(entrada, "2015-16")
    frases += [(f"marco.{m['tipo']}", m["frase"], replay) for m in replay["marcos"]]
    frases += [("replay.aviso", aviso, replay) for aviso in replay["avisos"]]
    verde = motor.verde_do_satelite(cidade)
    frases += [("verde", frase, verde) for frase in agente._frases_de(verde)]
    return frases


class AsFrasesDoProdutor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frases = {cidade: _frases_do_produtor(cidade) for cidade in motor.CIDADES}

    def test_nenhuma_frase_traz_palavra_da_conta_sem_explicacao(self):
        for cidade, frases in self.frases.items():
            for de_onde, frase, _ in frases:
                for palavra in PROIBIDAS:
                    self.assertNotIn(palavra, frase.lower(), (cidade, de_onde))

    def test_a_fao_e_o_satelite_vem_com_a_explicacao_ao_lado(self):
        for cidade, frases in self.frases.items():
            for de_onde, frase, _ in frases:
                if "FAO" in frase:
                    self.assertIn("ONU", frase, (cidade, de_onde))
                if "IMERG" in frase or "GIBS" in frase:
                    self.assertTrue("medida por satélite da NASA" in frase, (cidade, de_onde))

    def test_a_data_sai_no_jeito_brasileiro(self):
        for cidade, frases in self.frases.items():
            for de_onde, frase, _ in frases:
                self.assertIsNone(DATA_ISO.search(frase), (cidade, de_onde, frase))
        self.assertEqual(explicacao.data_br("2026-11-11"), "11/11/2026")
        self.assertEqual(explicacao.data_br(datetime.date(2016, 4, 4)), "04/04/2016")

    def test_a_conferencia_dos_numeros_continua_passando(self):
        for cidade, frases in self.frases.items():
            for de_onde, frase, conta in frases:
                self.assertEqual(conferencia.conferir_texto(frase, conta), [], (cidade, de_onde, frase))

    def test_o_como_esta_hoje_escreve_as_duas_datas_e_nao_um_hoje_solto(self):
        agora = motor.como_esta_hoje(RIO_VERDE, hoje=DIA)
        ultimo = explicacao.data_br(agora["ultimo_dia_com_dado"])
        self.assertIn(f"o último dia com dado é {ultimo}, {agora['atraso_dias']} dias antes do dia desta consulta "
                      "(15/11/2026).", agora["frase"])
        self.assertNotIn("antes de hoje", agora["frase"])
        self.assertIn("na camada de terra onde ficam as raízes", agora["frase"])
        self.assertIn("a chuva estimada por modelo de computador", agora["frase"])
        self.assertIn("a chuva estimada por modelo de computador", hoje.AVISO)

    def test_o_mesmo_numero_sai_escrito_do_mesmo_jeito(self):
        # A falta de água em mm sai sempre com uma casa ("252,0", nunca "252"), nas 4 frases de cada rotação.
        for cidade in motor.CIDADES:
            resposta = motor.responder(dict(RIO_VERDE, cidade_id=cidade))
            for item in resposta["comparacao_das_rotacoes"]:
                for chave in ("evidencia", "beneficio", "risco"):
                    for escrito in re.findall(r"(\d+(?:,\d+)?) mm", item[chave]):
                        self.assertRegex(escrito, r"^\d+,\d$", (cidade, item["id"], chave))


class AsRegrasDaIA(unittest.TestCase):
    def test_o_pedido_a_ia_manda_falar_simples_e_escrever_o_numero_como_a_conta(self):
        for trecho in ('diga "o valor do meio"', 'diga "a camada de terra onde ficam as raízes"',
                       'diga "a chuva estimada por modelo de computador"', 'diga "a chuva medida por satélite da NASA"',
                       "com a mesma casa depois da vírgula", "a data do dia da consulta e a data do último dia com dado",
                       "ficou perto do fundo sem acabar",
                       'Não diga que uma rotação é "a que mais sofre"', "Escreva só em português"):
            self.assertIn(trecho, " ".join(agente.REGRAS.split()))


class LetraDeOutroAlfabeto(unittest.TestCase):
    def test_o_texto_com_letra_de_outro_alfabeto_e_barrado(self):
        # Visto na gravação de 2026-11-15: "Vale fazer 监测 de campo toda semana", numa resposta de conhecimento geral.
        sobras = agente._sentido_trocado("Vale fazer 监测 de campo toda semana e conversar com o agrônomo.")
        self.assertEqual(sobras, ["监测 (letra de outro alfabeto: escreva só em português)"])
        saida = {"resposta": "Vale fazer 监测 de campo.", "ficha": {}, "comparacao": None, "consultas": []}
        self.assertEqual(len(agente.conferir_saida(saida, DIA)), 1)

    def test_o_portugues_com_acento_ordinal_grau_e_seta_passa(self):
        texto = "soja → milho de 2ª safra: máxima de 33,2 °C; a 1º de março • não é à toa. Órbita, ação, pé, vovô."
        self.assertEqual(agente._sentido_trocado(texto), [])


class AsFrasesProntasDoRegistro(unittest.TestCase):
    def test_a_pergunta_de_uma_safra_nao_comeca_igual_a_pergunta_geral(self):
        geral = {"ferramenta": "verde_do_satelite", "argumentos": {},
                 "resultado": {"frase": "Pelo calendário, a terra fica 122 dias sem planta.", "aviso": "O aviso geral."}}
        da_safra = {"ferramenta": "verde_do_satelite", "argumentos": {"safra": "2015-16"},
                    "resultado": dict(geral["resultado"], registro={"frase": "Safra 2015-16 em Rio Verde.",
                                                                   "aviso": "O aviso do registro."})}
        comparacao = [{}, {}, {}]
        primeira = agente._frases_prontas([geral], comparacao, "Rio Verde")
        segunda = agente._frases_prontas([da_safra], comparacao, "Rio Verde")
        self.assertTrue(primeira.startswith("Pelo calendário, a terra fica 122 dias sem planta."))
        self.assertTrue(segunda.startswith("Safra 2015-16 em Rio Verde."))
        self.assertNotIn("Pelo calendário", segunda)
        self.assertNotEqual(primeira[:40], segunda[:40])


class ORoteiroDasConversas(unittest.TestCase):
    def test_a_conversa_que_abre_a_tela_e_a_do_replay_sao_de_rio_verde(self):
        for ident in ("antes-plantei-tarde", "replay-2015-16"):
            conversa = next(c for c in exportar_conversas.CONVERSAS if c["id"] == ident)
            fala, chamadas = conversa["falas"][0]
            self.assertIn("Rio Verde", fala)
            self.assertEqual(chamadas[0]["argumentos"]["cidade_id"], "rio_verde")
        self.assertEqual(exportar_conversas.CONVERSAS[0]["id"], "antes-plantei-tarde")

    def test_no_durante_o_como_esta_hoje_vem_logo_depois_da_ficha(self):
        conversa = next(c for c in exportar_conversas.CONVERSAS if c["momento"] == "durante")
        (ficha, _), (sim, depois_do_sim), (terceira, da_terceira) = conversa["falas"][:3]
        self.assertTrue(ficha.endswith("Como está a minha lavoura hoje?"))
        self.assertEqual((sim, depois_do_sim), ("sim", [chamada("clima_do_lugar", hoje=True)]))
        self.assertEqual(da_terceira, [chamada("ensaio_da_rotacao", safra="pior_ano")])

    def test_as_travas_da_gravacao(self):
        def gravada(*respostas):
            return {"passos": [{"de": "agente", "saida": {"resposta": r}} for r in respostas]}
        igual = "Depois da colheita, a terra de Rio Verde ficou sem planta verde por bastante tempo."
        self.assertEqual(exportar_conversas.comecos_repetidos(gravada(igual + " Um.", igual + " Dois.")), 1)
        self.assertEqual(exportar_conversas.comecos_repetidos(gravada(igual, "Na safra 2015-16 foi diferente.")), 0)
        self.assertEqual(exportar_conversas.comecos_repetidos(gravada("Confira a sua ficha: a", "Confira a sua ficha: a")), 0)
        self.assertEqual(exportar_conversas.hoje_sem_data(gravada("O último dia com dado foi 4 dias antes de hoje.")), 1)
        self.assertEqual(exportar_conversas.hoje_sem_data(gravada("Até 11/11/2026, 4 dias antes de hoje (15/11/2026).")), 0)
        solta = {"passos": [{"de": "agente", "saida": {"resposta": "Hoje é 15/11/2026. A decisão é sua.",
                                                       "consultas": [{"resultado": {"comparacao": []}}]}}]}
        do_hoje = {"passos": [{"de": "agente", "saida": {"resposta": "Hoje é 15/11/2026, e o último dado é de 11/11/2026.",
                                                         "consultas": [{"resultado": {"hoje": {"disponivel": True}}}]}}]}
        self.assertEqual(exportar_conversas.hoje_fora_de_hora(solta), 1)
        self.assertEqual(exportar_conversas.hoje_fora_de_hora(do_hoje), 0)
        self.assertEqual(exportar_conversas.palavras_da_conta(gravada("A mediana delas é 38,0%.")), 1)
        self.assertEqual(exportar_conversas.palavras_da_conta(gravada("O valor do meio delas é 38,0%.")), 0)


if __name__ == "__main__":
    unittest.main()
