# Gerado com IA (Claude)
"""Testes das notas opcionais e da preocupação do produtor (`preocupacao`: agua, calor ou terra)."""
import contextlib
import io
import unittest

from orbita import conferencia, explicacao, mensagem, motor, perguntar

SEM_NOTAS = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media"}
COM_NOTAS = dict(SEM_NOTAS, prioridades={"agua": 5, "solo": 4, "renda": 2, "erosao": 3})
RESPOSTA = motor.responder(SEM_NOTAS)
TERRA = motor.responder(dict(SEM_NOTAS, preocupacao="terra"))
ANTIGA = motor.responder(COM_NOTAS)


def erro_de(entrada):
    with unittest.TestCase().assertRaises(ValueError) as erro:
        motor.validar_entrada(entrada)
    return str(erro.exception)


class SemAsNotas(unittest.TestCase):
    def test_a_entrada_sem_notas_vale_e_sai_na_ordem_de_costume(self):
        self.assertEqual([p["id"] for p in RESPOSTA["pontos_medidos"]], ["agua", "solo", "erosao", "renda"])
        self.assertEqual([p for p in RESPOSTA["pontos_medidos"] if "nota" in p], [])     # a chave `nota` saiu
        self.assertEqual(RESPOSTA["destaque"]["ponto"], "agua")
        self.assertNotIn("nota", RESPOSTA["destaque"])
        self.assertNotIn("prioridades", RESPOSTA["entrada"])
        self.assertIsNone(RESPOSTA["preocupacao"])
        self.assertEqual(RESPOSTA["ordem_das_pernas"], ["agua", "calor", "terra"])

    def test_nenhum_numero_muda_sem_as_notas(self):
        for chave in ("rotacoes", "comparacao", "veredito", "regra_dos_anos", "safra_2025_26", "sede_forte"):
            self.assertEqual(RESPOSTA[chave], ANTIGA[chave], chave)
        self.assertEqual({p["id"]: p["melhor"] for p in RESPOSTA["pontos_medidos"]},
                         {p["id"]: p["melhor"] for p in ANTIGA["pontos_medidos"]})

    def test_notas_pela_metade_ou_fora_do_formato_sao_ignoradas(self):
        # Mudou em 2026-11-15 (decisão do dono: as notas de 1 a 5 saem): o motor não confere mais o campo.
        for notas in ({"agua": 5, "solo": 4, "renda": 2}, {"agua": 9, "solo": 4, "renda": 2, "erosao": 1}, [5, 4, 2, 3]):
            self.assertNotIn("prioridades", motor.validar_entrada(dict(SEM_NOTAS, prioridades=notas)))
        self.assertEqual(ANTIGA, RESPOSTA)      # a resposta com notas é a mesma da resposta sem notas

    def test_os_textos_nao_falam_de_nota_e_todo_numero_esta_na_conta(self):
        for resposta in (RESPOSTA, TERRA):
            texto = explicacao.texto(resposta)
            self.assertNotIn("None", texto)
            self.assertNotIn("nota", texto.lower())
            self.assertEqual(conferencia.conferir_texto(texto, resposta), [])
            curto = mensagem.texto(resposta)
            self.assertNotIn("None", curto)
            self.assertEqual(conferencia.conferir_texto(curto, resposta), [])

    def test_perguntar_sem_notas(self):
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            self.assertEqual(perguntar.main(["--terra", "media", "--preocupacao", "terra"]), 0)
        self.assertIn("No que mais preocupa (solo)", saida.getvalue())


class Preocupacao(unittest.TestCase):
    def test_a_preocupacao_so_muda_a_ordem_e_o_destaque(self):
        self.assertEqual([p["id"] for p in TERRA["pontos_medidos"]], ["solo", "erosao", "agua", "renda"])
        self.assertEqual(TERRA["destaque"]["ponto"], "solo")
        self.assertEqual(TERRA["preocupacao"], "terra")
        self.assertEqual(TERRA["ordem_das_pernas"], ["terra", "agua", "calor"])
        for chave in ("rotacoes", "comparacao", "veredito", "regra_dos_anos", "safra_2025_26", "sede_forte"):
            self.assertEqual(TERRA[chave], RESPOSTA[chave], chave)

    def test_com_notas_na_entrada_vale_so_a_preocupacao(self):
        # Mudou em 2026-11-15 (decisão do dono: as notas saem): antes a nota mandava e a preocupação desempatava.
        iguais = motor.responder(dict(SEM_NOTAS, prioridades={"agua": 3, "solo": 3, "renda": 3, "erosao": 3},
                                      preocupacao="terra"))
        self.assertEqual([p["id"] for p in iguais["pontos_medidos"]], ["solo", "erosao", "agua", "renda"])
        com_notas = motor.responder(dict(COM_NOTAS, preocupacao="terra"))
        self.assertEqual([p["id"] for p in com_notas["pontos_medidos"]], [p["id"] for p in TERRA["pontos_medidos"]])
        self.assertEqual(com_notas, TERRA)

    def test_preocupacao_que_nao_existe_e_erro_em_portugues(self):
        erro = erro_de(dict(SEM_NOTAS, preocupacao="preco"))
        self.assertTrue(erro.startswith("Entrada fora do formato:"), erro)
        self.assertIn("agua, calor ou terra", erro)


if __name__ == "__main__":
    unittest.main()
