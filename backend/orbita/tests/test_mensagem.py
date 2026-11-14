# Gerado com IA (Claude)
"""Testes do texto curto para mensagem: o que ele traz, o tamanho, a conferência dos números e os campos que faltam."""
import copy
import unittest

from orbita import conferencia, mensagem, motor

BASE = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"]}
VARIAS_NOTAS = ({"agua": 5, "solo": 4, "renda": 2, "erosao": 3}, {"agua": 3, "solo": 3, "renda": 3, "erosao": 3},
                {"agua": 1, "solo": 2, "renda": 5, "erosao": 4}, {"agua": 2, "solo": 5, "renda": 1, "erosao": 5})
RESPOSTAS = [motor.responder(dict(BASE, prioridades=notas, terra=terra))
             for terra in ("pouca", "media", "muita") for notas in VARIAS_NOTAS]
RESPOSTA = RESPOSTAS[4]                    # terra média, água 5, solo 4, renda 2, erosão 3
RENDA_NA_FRENTE = RESPOSTAS[6]             # terra média, renda 5, erosão 4
TROCAS = (None, "x", 7, 2.5, True, [], {}, ["x"], {"x": 1}, float("nan"))


def cada_lugar(coisa):
    """Todo lugar da resposta, de qualquer profundidade: (o dono, a chave ou a posição)."""
    if isinstance(coisa, dict):
        for chave in list(coisa):
            yield coisa, chave
            yield from cada_lugar(coisa[chave])
    elif isinstance(coisa, list):
        for posicao in range(len(coisa)):
            yield coisa, posicao
            yield from cada_lugar(coisa[posicao])


class OTexto(unittest.TestCase):
    def test_traz_a_pergunta_o_resultado_a_prova_o_risco_e_o_agronomo(self):
        texto = mensagem.texto(RESPOSTA)
        pior = RESPOSTA["comparacao"]["pior_ano"]
        self.assertIn("Pergunta:", texto)
        self.assertIn(RESPOSTA["rotacoes"]["atual"]["nome"], texto)
        self.assertIn(RESPOSTA["rotacoes"]["alternativa"]["nome"], texto)
        self.assertIn(RESPOSTA["veredito"]["frase"], texto)
        self.assertIn("A prova:", texto)
        for rotacao in ("atual", "alternativa"):
            falta = RESPOSTA["rotacoes"][rotacao]["safras"][pior]["total"]["falta_mm"]
            self.assertIn(f"{falta:.1f}".replace(".", ",") + " mm", texto)
        self.assertIn(f"safra {pior}", texto)
        self.assertIn("satélite", texto)                       # a fonte dita em palavras
        self.assertIn("NASA", texto)
        self.assertNotIn("http", texto)
        self.assertEqual(texto.count("O risco:"), 1)
        self.assertIn("valide com o agrônomo", texto)

    def test_mostra_as_prioridades_de_maior_nota(self):
        texto = mensagem.texto(RESPOSTA)
        self.assertIn("Água (nota 5): empate", texto)
        self.assertIn("Solo (nota 4): a alternativa se saiu melhor", texto)
        self.assertNotIn("Erosão (nota", texto)
        self.assertNotIn("Renda (nota", texto)
        self.assertLess(texto.index("Água (nota 5)"), texto.index("Solo (nota 4)"))
        self.assertIn(f"{RESPOSTA['comparacao']['solo_e_erosao']['dias_sem_planta_viva_hoje']} dias", texto)

    def test_com_a_renda_na_frente_diz_que_nao_foi_medida_e_prova_a_outra(self):
        texto = mensagem.texto(RENDA_NA_FRENTE)
        self.assertIn("Renda (nota 5): não medido", texto)
        self.assertIn("Erosão (nota 4)", texto)
        self.assertNotIn("Água (nota", texto)
        self.assertIn("dias por ano sem planta viva", texto)
        self.assertNotIn("mm de água", texto)                  # a água não está entre as duas maiores notas

    def test_cabe_numa_mensagem_e_nao_tem_tabela_nem_markdown(self):
        for resposta in RESPOSTAS:
            texto = mensagem.texto(resposta)
            self.assertLessEqual(len(texto), mensagem.LIMITE)
            self.assertLessEqual(mensagem.LIMITE, 900)
            for sinal in ("|", "*", "#", "_", "`", "~", "\t", "\n- ", "\n1. "):
                self.assertNotIn(sinal, texto)
            self.assertFalse(any(linha != linha.strip() for linha in texto.split("\n")))

    def test_todo_numero_do_texto_esta_na_resposta(self):
        for resposta in RESPOSTAS:
            self.assertEqual(conferencia.conferir_texto(mensagem.texto(resposta), resposta), [])

    def test_a_mesma_resposta_da_o_mesmo_texto_e_nada_muda_nela(self):
        copia = copy.deepcopy(RESPOSTA)
        self.assertEqual(mensagem.texto(copia), mensagem.texto(RESPOSTA))
        self.assertEqual(copia, RESPOSTA)


class CampoQueFalta(unittest.TestCase):
    def test_sem_cada_campo_o_texto_sai_sem_quebrar_e_sem_numero_de_fora(self):
        resposta, vistos = copy.deepcopy(RESPOSTA), {mensagem.texto(RESPOSTA)}
        for dono, lugar in cada_lugar(resposta):
            guardado = dono[lugar]
            del dono[lugar]
            texto = mensagem.texto(resposta)
            dono.insert(lugar, guardado) if isinstance(dono, list) else dono.__setitem__(lugar, guardado)
            self.assertIn("valide com o agrônomo", texto)
            if texto not in vistos:                            # tirar um campo nunca põe número novo no texto
                vistos.add(texto)
                self.assertEqual(conferencia.conferir_texto(texto, RESPOSTA), [])
        self.assertGreater(len(vistos), 10)                    # vários trechos saíram, um de cada vez
        self.assertEqual(mensagem.texto(resposta), mensagem.texto(RESPOSTA))

    def test_campo_com_o_tipo_errado_nao_quebra(self):
        resposta = copy.deepcopy(RESPOSTA)
        for dono, lugar in cada_lugar(resposta):
            guardado = dono[lugar]
            for troca in TROCAS:
                dono[lugar] = troca
                texto = mensagem.texto(resposta)
                self.assertIsInstance(texto, str)
                self.assertIn("valide com o agrônomo", texto)
                self.assertNotIn("nan", texto)
                self.assertNotIn("None", texto)
            dono[lugar] = guardado

    def test_cada_trecho_some_com_o_campo_dele(self):
        sem = lambda *campos: mensagem.texto({k: v for k, v in RESPOSTA.items() if k not in campos})  # noqa: E731
        self.assertNotIn("Resposta:", sem("veredito"))
        self.assertNotIn("(nota", sem("prioridades"))
        self.assertIn("A prova:", sem("prioridades"))          # sem as notas, a prova ainda vai
        self.assertNotIn("A prova:", sem("rotacoes", "comparacao"))
        self.assertNotIn("O risco:", sem("rotacoes"))
        self.assertIn("Pergunta: " + RESPOSTA["pergunta"], sem("rotacoes"))
        self.assertNotIn("satélite", sem("clima"))
        self.assertIn(" mm de água", sem("clima"))

    def test_resposta_vazia_ou_que_nao_e_dicionario_da_so_o_aviso(self):
        for coisa in ({}, None, "soja", 3, []):
            texto = mensagem.texto(coisa)
            self.assertIn("valide com o agrônomo", texto)
            self.assertNotIn("Pergunta:", texto)

    def test_campo_novo_na_resposta_nao_muda_o_texto(self):
        resposta = copy.deepcopy(RESPOSTA)
        resposta["campo_novo"] = {"numero": 123456}
        resposta["veredito"]["outro"] = "texto novo 987"
        resposta["prioridades"][0]["peso"] = 0.77
        resposta["rotacoes"]["atual"]["safras"][RESPOSTA["comparacao"]["pior_ano"]]["total"]["novo_mm"] = 55.5
        self.assertEqual(mensagem.texto(resposta), mensagem.texto(RESPOSTA))


if __name__ == "__main__":
    unittest.main()
