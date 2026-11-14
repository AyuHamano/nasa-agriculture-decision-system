# Gerado com IA (Claude).
"""Testes da trava do texto (orbita/conferencia.py).

A resposta de exemplo é inventada aqui dentro: o que importa é a regra, não os números.

Rodar, de `backend/`: python3 -m unittest discover -s orbita/tests -t .
"""
import unittest
from datetime import date

from orbita.conferencia import conferir_texto

RESPOSTA = {
    "cidade": "Rio Verde (GO)",
    "ponto": {"lat": -17.79, "lon": -50.92},
    "rotacoes": [
        {
            "nome": "soja, milho e pousio",
            "safras": {
                "2019-20": {"falta_mm": 87.26, "dias_de_sede": 34, "falta_relativa": 12.4},
                "2020-21": {"falta_mm": 1234.5, "dias_de_sede": 61, "falta_relativa": 38.04},
            },
            "dias_sem_planta": 112,
        },
    ],
    "regra": {"safra_com_sede": 0.20, "frase": "Safra com sede: falta relativa de 20% ou mais."},
    "ndvi": {"limite": 0.3841, "mediana": 96, "fonte": "MOD13Q1 v061, de 2018-06-26 a 2026-10-16"},
    "ano_mais_seco": "2020-21",
    "anos": (2015, 2024),
    "tem_aviso": True,
    "vazio": None,
}


class NumerosCertos(unittest.TestCase):
    def test_texto_com_todos_os_numeros_certos_passa(self):
        texto = ("Na safra 2020-21, o milho ficou 61 dias com sede e faltaram 1.234,5 mm de água "
                 "(38,04% do que a planta pediu). Em 2019-20 foram 34 dias e 87,26 mm. "
                 "A terra fica 112 dias sem planta.")
        self.assertEqual(conferir_texto(texto, RESPOSTA), [])

    def test_texto_sem_numero_passa(self):
        self.assertEqual(conferir_texto("Valide com o agrônomo antes de trocar a rotação.", RESPOSTA), [])

    def test_resposta_em_lista_e_em_qualquer_profundidade(self):
        resposta = [{"a": [{"b": ({"c": 7.5},)}]}, [[3]]]
        self.assertEqual(conferir_texto("Foram 7,5 mm em 3 dias.", resposta), [])

    def test_numero_que_esta_dentro_de_um_texto_da_resposta_vale(self):
        # O 20 e o 250 só aparecem dentro de frases da resposta.
        self.assertEqual(conferir_texto("O corte é de 20 pontos.", {"frase": "falta de 20% ou mais"}), [])
        self.assertEqual(conferir_texto("São 250 metros.", {"fonte": "MOD13Q1, pixel de 250m"}), [])

    def test_numero_que_e_chave_da_resposta_vale(self):
        self.assertEqual(conferir_texto("Em 2021 foram 48 dias.", {"dias": {2021: 48}}), [])
        self.assertEqual(conferir_texto("Em 2021 foram 48 dias.", {"dias": {"2021": 48}}), [])


class NumerosErrados(unittest.TestCase):
    def test_um_numero_trocado_e_pego(self):
        texto = "Na safra 2020-21, o milho ficou 16 dias com sede e faltaram 1.234,5 mm de água."
        self.assertEqual(conferir_texto(texto, RESPOSTA), ["16"])

    def test_um_numero_inventado_e_pego(self):
        texto = "A troca rende 4.300 reais a mais por hectare e a terra fica 112 dias sem planta."
        self.assertEqual(conferir_texto(texto, RESPOSTA), ["4.300"])

    def test_devolve_como_foi_escrito_na_ordem_e_sem_repetir(self):
        texto = "Faltaram 999,9 mm; em 77 dias, 999,9 mm; e mais 5%."
        self.assertEqual(conferir_texto(texto, RESPOSTA), ["999,9", "77", "5%"])

    def test_verdadeiro_e_falso_nao_sao_numeros(self):
        # True vale 1 no Python; aqui não pode liberar o "1".
        self.assertEqual(conferir_texto("Foi 1 safra.", {"tem_aviso": True, "outro": False}), ["1"])

    def test_sem_resposta_todo_numero_e_pego(self):
        self.assertEqual(conferir_texto("Foram 34 dias.", {}), ["34"])


class Arredondamento(unittest.TestCase):
    def test_um_numero_arredondado_passa(self):
        # 87,26 -> "87,3" (1 casa) e "87" (0 casas); 38,04 -> "38"; 0,3841 -> "0,38".
        texto = "Faltaram 87,3 mm (uns 87), 38% do pedido, e o limite do verde foi 0,38."
        self.assertEqual(conferir_texto(texto, RESPOSTA), [])

    def test_arredondado_errado_e_pego(self):
        # 87,26 com 1 casa é 87,3, não 87,2; 0,3841 com 2 casas é 0,38, não 0,39.
        self.assertEqual(conferir_texto("Faltaram 87,2 mm.", RESPOSTA), ["87,2"])
        self.assertEqual(conferir_texto("O limite foi 0,39.", RESPOSTA), ["0,39"])

    def test_casas_a_mais_que_a_resposta_nao_passam(self):
        # A resposta tem 34; "34,7" não é 34 arredondado para 1 casa.
        self.assertEqual(conferir_texto("Foram 34,7 dias.", RESPOSTA), ["34,7"])
        self.assertEqual(conferir_texto("Foram 34,0 dias.", RESPOSTA), [])

    def test_o_sinal_fica_por_conta_das_palavras(self):
        # A conferência olha o tamanho do número: -24 na resposta, "24 dias a menos" no texto.
        self.assertEqual(conferir_texto("São 24 dias a menos.", {"diferenca": -24}), [])
        self.assertEqual(conferir_texto("O ponto fica em -17,79 e -50,92.", RESPOSTA), [])


class FormatosBrasileiros(unittest.TestCase):
    def test_milhar_com_ponto_e_decimal_com_virgula(self):
        self.assertEqual(conferir_texto("Faltaram 1.234,5 mm.", RESPOSTA), [])
        self.assertEqual(conferir_texto("Faltaram 1.234,6 mm.", RESPOSTA), ["1.234,6"])
        self.assertEqual(conferir_texto("São 1.234.567 litros.", {"litros": 1234567}), [])

    def test_decimal_com_virgula(self):
        self.assertEqual(conferir_texto("O limite foi 0,38.", RESPOSTA), [])
        self.assertEqual(conferir_texto("O limite foi 0,3841.", RESPOSTA), [])

    def test_numero_com_unidade(self):
        self.assertEqual(conferir_texto("Foram 34 dias.", RESPOSTA), [])
        self.assertEqual(conferir_texto("Foram 34dias e 87,26mm.", RESPOSTA), [])

    def test_porcentagem(self):
        self.assertEqual(conferir_texto("Faltou 12,4% da água.", RESPOSTA), [])
        self.assertEqual(conferir_texto("Faltou 12,4 % da água, ou 12 por cento.", RESPOSTA), [])
        self.assertEqual(conferir_texto("Faltou 13% da água.", RESPOSTA), ["13%"])

    def test_porcentagem_vale_pela_fracao_da_resposta(self):
        # A resposta guarda 0,35 (uma fração); "35%" no texto é o mesmo número.
        self.assertEqual(conferir_texto("O corte é de 35%.", {"corte": 0.35}), [])
        self.assertEqual(conferir_texto("O corte é de 35.", {"corte": 0.35}), ["35"])

    def test_jeito_ingles(self):
        self.assertEqual(conferir_texto("A shortfall of 1234.5 mm.", RESPOSTA), [])
        self.assertEqual(conferir_texto("A shortfall of 1,234.5 mm.", RESPOSTA), [])
        self.assertEqual(conferir_texto("The threshold was 0.38.", RESPOSTA), [])
        self.assertEqual(conferir_texto("A shortfall of 1234.9 mm.", RESPOSTA), ["1234.9"])

    def test_um_separador_e_tres_casas_vale_dos_dois_jeitos(self):
        # "1.234" pode ser mil duzentos e trinta e quatro (Brasil) ou 1 vírgula 234 (inglês).
        self.assertEqual(conferir_texto("Faltaram 1.234 mm.", {"falta": 1234.4}), [])
        self.assertEqual(conferir_texto("O índice foi 1.234.", {"indice": 1.2341}), [])
        self.assertEqual(conferir_texto("Faltaram 1.234 mm.", {"falta": 12.34}), ["1.234"])

    def test_numero_no_fim_da_frase_e_em_lista(self):
        self.assertEqual(conferir_texto("Foram 34, 61 e 112.", RESPOSTA), [])


class AnosESafras(unittest.TestCase):
    def test_rotulo_de_safra_que_esta_na_resposta_vale(self):
        self.assertEqual(conferir_texto("A safra 2020-21 foi a mais seca.", RESPOSTA), [])
        self.assertEqual(conferir_texto("A safra 2020/21 foi a mais seca.", RESPOSTA), [])
        self.assertEqual(conferir_texto("A safra 2020-2021 foi a mais seca.", RESPOSTA), [])

    def test_rotulo_de_safra_que_nao_esta_e_pego(self):
        self.assertEqual(conferir_texto("A safra 2021-22 foi a mais seca.", RESPOSTA), ["2021-22"])

    def test_o_final_do_rotulo_nao_libera_numero_solto(self):
        # O "21" de "2020-21" é o ano de 2021 abreviado, não 21 dias.
        self.assertEqual(conferir_texto("Foram 21 dias.", {"safra": "2020-21"}), ["21"])

    def test_ano_que_esta_na_resposta_vale(self):
        self.assertEqual(conferir_texto("De 2015 a 2024.", RESPOSTA), [])
        self.assertEqual(conferir_texto("A colheita de 2021 quebrou.", RESPOSTA), [])   # o fim da safra 2020-21

    def test_ano_que_nao_esta_e_pego(self):
        self.assertEqual(conferir_texto("Em 2012 choveu menos.", RESPOSTA), ["2012"])

    def test_data_que_esta_na_resposta_vale(self):
        self.assertEqual(conferir_texto("A série vai até 2026-10-16.", RESPOSTA), [])
        self.assertEqual(conferir_texto("A série vai até 16/10/2026.", RESPOSTA), [])
        self.assertEqual(conferir_texto("A série vai até 16 de outubro de 2026.", RESPOSTA), [])
        self.assertEqual(conferir_texto("Começa em 2018-06-26.", {"inicio": date(2018, 6, 26)}), [])

    def test_data_que_nao_esta_e_pega_inteira(self):
        self.assertEqual(conferir_texto("A série vai até 2026-10-17.", RESPOSTA), ["2026-10-17"])
        self.assertEqual(conferir_texto("A série vai até 17/10/2026.", RESPOSTA), ["17/10/2026"])


class OQueNaoENumero(unittest.TestCase):
    def test_ordinal_nao_e_conferido(self):
        self.assertEqual(conferir_texto("Na 2ª safra, o 1º plantio atrasou.", {}), [])

    def test_numero_colado_em_letra_e_nome_nao_numero(self):
        self.assertEqual(conferir_texto("O produto MOD13Q1 v061 mede o verde.", {}), [])

    def test_numero_depois_de_hifen_e_numero(self):
        self.assertEqual(conferir_texto("A conta segue o FAO-56.", {}), ["56"])
        self.assertEqual(conferir_texto("A conta segue o FAO-56.", {"fonte": "FAO-56, capítulo 8"}), [])


class Permitidos(unittest.TestCase):
    def test_numero_liberado_a_parte(self):
        texto = "Cada medida do satélite vale 16 dias; foram 34 dias de sede."
        self.assertEqual(conferir_texto(texto, RESPOSTA), ["16"])
        self.assertEqual(conferir_texto(texto, RESPOSTA, permitidos=[16]), [])
        self.assertEqual(conferir_texto(texto, RESPOSTA, permitidos=(16.0,)), [])

    def test_liberado_como_texto_e_rotulo_de_safra(self):
        texto = "Na safra 2021-22 faltaram 3,5 mm."
        self.assertEqual(conferir_texto(texto, RESPOSTA, permitidos=["2021-22", "3,5"]), [])

    def test_um_numero_so_tambem_serve(self):
        self.assertEqual(conferir_texto("Foram 16 dias.", {}, permitidos=16), [])

    def test_liberar_um_nao_libera_os_outros(self):
        self.assertEqual(conferir_texto("Foram 16 dias e 17 noites.", {}, permitidos=[16]), ["17"])


if __name__ == "__main__":
    unittest.main()
