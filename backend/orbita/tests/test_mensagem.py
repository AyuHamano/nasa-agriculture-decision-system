# Gerado com IA (Claude)
"""Testes do texto curto para mensagem: o que ele traz, o tamanho, a conferência dos números e os campos que faltam."""
import copy
import unittest

from orbita import conferencia, mensagem, motor

BASE = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"]}
# As notas de 1 a 5 saíram (decisão do dono, 2026-11-15): as respostas do teste vêm sem `prioridades`, e o que muda
# de uma para outra é o que mais preocupa o produtor (ou nada).
PREOCUPACOES = (None, "agua", "calor", "terra")
RESPOSTAS = [motor.responder(dict(BASE, terra=terra, **({"preocupacao": p} if p else {})))
             for terra in ("pouca", "media", "muita") for p in PREOCUPACOES]
RESPOSTA = RESPOSTAS[4]                    # terra média, sem dizer o que mais preocupa
COM_PREOCUPACAO = RESPOSTAS[7]             # terra média, o que mais preocupa é a terra
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
        hoje = RESPOSTA["rotacoes"]["atual"]["safras"][pior]["total"]["falta_mm"]
        self.assertIn(f"{hoje:.1f}".replace(".", ",") + " mm", texto)
        faixa = RESPOSTA["rotacoes"]["alternativa"]["faixa"][pior]["falta_total_mm"]   # a alternativa vai em faixa
        for ponta in ("menor", "maior"):
            self.assertIn(f"{faixa[ponta]:.1f}".replace(".", ","), texto)
        self.assertIn(f"safra {pior}", texto)
        self.assertIn("satélite", texto)                       # a fonte dita em palavras
        self.assertIn("NASA", texto)
        self.assertNotIn("http", texto)
        self.assertEqual(texto.count("O risco:"), 1)           # uma linha de risco, sem aviso repetido
        self.assertTrue(texto.endswith("Converse com o agrônomo antes de decidir."))
        self.assertEqual(texto.count("agrônomo antes de decidir"), 1)

    def test_nao_trata_a_data_do_dado_como_defeito(self):
        for resposta in RESPOSTAS:
            texto = mensagem.texto(resposta).lower()
            for pedaco in ("aproximada", "com atraso", "ainda não entrou"):
                self.assertNotIn(pedaco, texto)

    def test_mostra_as_duas_primeiras_medidas_sem_nota(self):
        # mudou em 2026-11-15 (decisão do dono: as notas de 1 a 5 saíram): antes era "Água (nota 5): ...", sob o
        # título "Nas suas maiores notas"; agora vale a ordem do motor, sem nota
        for resposta, titulo in ((RESPOSTA, "No que foi medido:"), (COM_PREOCUPACAO, "No que mais preocupa:")):
            texto = mensagem.texto(resposta)
            self.assertIn(titulo, texto)
            self.assertNotIn("nota", texto.lower())
            for p in resposta["pontos_medidos"][:2]:              # o resultado vem da conta, não do teste
                quem = mensagem.PELA_FAIXA.get(p.get("veredito_pela_faixa")) or mensagem.QUEM[p["melhor"]]
                self.assertIn(f"{p['nome']}: {quem}.", texto)
            for p in resposta["pontos_medidos"][2:]:
                self.assertNotIn(f"{p['nome']}:", texto)
            ids = [p["id"] for p in resposta["pontos_medidos"][:2]]
            self.assertEqual("mm de água" in texto, "agua" in ids)
            self.assertEqual("dias por ano sem planta viva" in texto, "solo" in ids or "erosao" in ids)

    def test_resposta_antiga_que_ainda_traz_nota_da_o_mesmo_texto_sem_nota_e_na_mesma_ordem(self):
        antiga = copy.deepcopy(RESPOSTA)
        for nota, p in enumerate(antiga["pontos_medidos"], start=1):
            p["nota"] = nota                                   # a última teria a maior nota: a ordem não muda
        self.assertEqual(mensagem.texto(antiga), mensagem.texto(RESPOSTA))

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
            self.assertIn("Converse com o agrônomo", texto)
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
                self.assertIn("Converse com o agrônomo", texto)
                self.assertNotIn("nan", texto)
                self.assertNotIn("None", texto)
            dono[lugar] = guardado

    def test_cada_trecho_some_com_o_campo_dele(self):
        sem = lambda *campos: mensagem.texto({k: v for k, v in RESPOSTA.items() if k not in campos})  # noqa: E731
        self.assertNotIn("Resposta:", sem("veredito"))
        self.assertNotIn("No que foi medido:", sem("pontos_medidos"))
        self.assertIn("A prova:", sem("pontos_medidos"))          # sem as prioridades, a prova ainda vai
        self.assertNotIn("A prova:", sem("rotacoes", "comparacao"))
        self.assertNotIn("O risco:", sem("rotacoes"))
        self.assertIn("Pergunta: " + RESPOSTA["pergunta"], sem("rotacoes"))
        self.assertNotIn("satélite", sem("clima"))
        self.assertIn(" mm de água", sem("clima"))

    def test_resposta_vazia_ou_que_nao_e_dicionario_da_so_o_aviso(self):
        for coisa in ({}, None, "soja", 3, []):
            texto = mensagem.texto(coisa)
            self.assertIn("Converse com o agrônomo", texto)
            self.assertNotIn("Pergunta:", texto)

    def test_campo_novo_na_resposta_nao_muda_o_texto(self):
        resposta = copy.deepcopy(RESPOSTA)
        resposta["campo_novo"] = {"numero": 123456}
        resposta["veredito"]["outro"] = "texto novo 987"
        resposta["pontos_medidos"][0]["peso"] = 0.77
        resposta["rotacoes"]["atual"]["safras"][RESPOSTA["comparacao"]["pior_ano"]]["total"]["novo_mm"] = 55.5
        self.assertEqual(mensagem.texto(resposta), mensagem.texto(RESPOSTA))


if __name__ == "__main__":
    unittest.main()
