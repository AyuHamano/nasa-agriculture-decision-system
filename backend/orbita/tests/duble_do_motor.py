# Gerado com IA (Claude)
"""O dublê do motor: uma peça de mentira, no formato combinado no mapa do projeto (seções 7.2, 7.3 e 7.5).

Serve aos testes do agente enquanto as funções novas do motor não chegam (e depois, para os testes não dependerem dos
números de verdade). Os números daqui são de mentira: só servem para conferir que o agente repassa o que recebeu.
Uso: `unittest.mock.patch.object(ferramentas, "motor", Duble())`.
"""
import copy

ROTACOES = {
    "atual": {"nome": "soja → milho safrinha → pousio (terra parada)", "id": "soja_milho_pousio",
              "culturas": ["soja", "milho", "pousio"]},
    "alternativa": {"nome": "soja → milho com braquiária (capim)", "id": "soja_milho_braquiaria",
                    "culturas": ["soja", "milho", "braquiaria"]},
    "com_sorgo": {"nome": "soja → sorgo safrinha → pousio (terra parada)", "id": "soja_sorgo_pousio",
                  "culturas": ["soja", "sorgo", "pousio"]},
}
COMPARACAO = [
    {"id": "soja_milho_pousio", "nome": "soja → milho safrinha → pousio (terra parada)", "de_hoje": True,
     "agua": {"falta_no_ano_normal_mm": 61.2, "falta_no_pior_ano_mm": 232.9, "dias_de_sede_no_pior_ano": 58},
     "calor": {"dias_de_calor_forte_no_pior_ano": 17, "limite_c": 35.0, "etiqueta": "publicado"},
     "terra_coberta": {"dias_sem_planta_viva": 122, "pelo_satelite": 96},
     "evidencia": "No pior ano (safra 2015-16) faltaram 232,9 mm de água, e a terra fica 122 dias sem planta viva.",
     "beneficio": "É a rotação que você já faz: não muda o manejo.",
     "risco": "A terra fica 122 dias por ano sem planta viva, exposta ao sol e à chuva.",
     "falta_saber": "A conta não mede preço nem produtividade."},
    {"id": "soja_milho_braquiaria", "nome": "soja → milho com braquiária (capim)", "de_hoje": False,
     "agua": {"falta_no_ano_normal_mm": {"de": 60.1, "ate": 66.4}, "falta_no_pior_ano_mm": {"de": 229.4, "ate": 251.6},
              "dias_de_sede_no_pior_ano": {"de": 57, "ate": 63}},
     "calor": {"dias_de_calor_forte_no_pior_ano": 17, "limite_c": 35.0, "etiqueta": "publicado"},
     "terra_coberta": {"dias_sem_planta_viva": 30, "pelo_satelite": None},
     "evidencia": "No pior ano faltaram de 229,4 a 251,6 mm de água, e a terra fica 30 dias sem planta viva.",
     "beneficio": "A terra fica coberta quase o ano inteiro.",
     "risco": "O capim também bebe água: a terra pode chegar mais seca ao plantio da soja.",
     "falta_saber": "Quanto o capim disputa água com o milho não foi medido."},
    {"id": "soja_sorgo_pousio", "nome": "soja → sorgo safrinha → pousio (terra parada)", "de_hoje": False,
     "agua": {"falta_no_ano_normal_mm": 44.8, "falta_no_pior_ano_mm": 187.5, "dias_de_sede_no_pior_ano": 41},
     "calor": {"dias_de_calor_forte_no_pior_ano": 9, "limite_c": 38.0, "etiqueta": "hipótese"},
     "terra_coberta": {"dias_sem_planta_viva": 131, "pelo_satelite": None},
     "evidencia": "No pior ano faltaram 187,5 mm de água, menos que com o milho.",
     "beneficio": "O sorgo aguenta melhor a falta de água na segunda safra.",
     "risco": "A terra fica 131 dias por ano sem planta viva.",
     "falta_saber": "O limite de calor do sorgo ainda é hipótese."},
]
MARCOS = [
    {"data": "2015-10-20", "tipo": "plantio", "frase": "A soja foi plantada."},
    {"data": "2016-03-14", "tipo": "agua_acabou", "frase": "Neste dia a água da terra acabou para o milho."},
    {"data": "2016-04-02", "tipo": "calor_forte", "frase": "Calor forte: a máxima passou de 35 °C."},
    {"data": "2016-06-18", "tipo": "colheita", "frase": "O milho saiu da terra."},
]


class Duble:
    """O motor de mentira. `chamadas` guarda o nome de cada função chamada, na ordem (para os testes olharem)."""

    CIDADES = {"rio_verde": {"nome": "Rio Verde (GO)"}, "jatai": {"nome": "Jataí (GO)"},
               "silvania": {"nome": "Silvânia (GO)"}}
    TERRAS = ("pouca", "media", "muita")
    PREOCUPACOES = ("agua", "calor", "terra")
    ROTACOES = ROTACOES
    ROTACAO_DE_HOJE = ["soja", "milho", "pousio"]

    def __init__(self, rotacoes=3, com_hoje=True, com_registro=True, recusar=None):
        self.chamadas, self.quantas, self.recusar = [], rotacoes, recusar
        if not com_hoje:
            self.como_esta_hoje = None
        if not com_registro:
            self.registro_da_safra = None

    def __getattribute__(self, nome):                       # função desligada no dublê = o motor não tem a função
        valor = object.__getattribute__(self, nome)
        if valor is None and nome in ("como_esta_hoje", "registro_da_safra"):
            raise AttributeError(nome)
        return valor

    def _conferir(self, entrada):
        if entrada.get("cidade_id") not in self.CIDADES:
            raise ValueError(f'Entrada fora do formato: cidade_id "{entrada.get("cidade_id")}" ainda não existe.')
        if self.recusar:
            raise ValueError("Entrada fora do formato: " + self.recusar)

    def responder(self, entrada):
        self.chamadas.append("responder")
        self._conferir(entrada)
        comparacao = copy.deepcopy(COMPARACAO[:self.quantas])
        for item in comparacao:
            culturas = next(r["culturas"] for r in ROTACOES.values() if r["id"] == item["id"])
            item["de_hoje"] = culturas == list(entrada["rotacao_atual"])
        return {"entrada": dict(entrada), "local": dict(self.CIDADES[entrada["cidade_id"]], id=entrada["cidade_id"]),
                "regra_dos_anos": {"pior_ano": "2015-16", "ano_normal": "2019-20"},
                "calendario": {"soja": {"plantio": "10/11", "sai_da_terra": "05/03"},
                               "milho": {"plantio": "08/03", "sai_da_terra": "11/07"},
                               "plantio_da_soja_informado": entrada.get("plantio_da_soja"), "deslocamento_dias": 26},
                "comparacao_das_rotacoes": comparacao, "parametros": [{"valor": 777}], "limites": ["um limite, 555"]}

    def clima_do_lugar(self, cidade_id):
        self.chamadas.append("clima_do_lugar")
        return {"local": dict(self.CIDADES[cidade_id], id=cidade_id),
                "clima": {"chuva": "o satélite de chuva GPM IMERG, da NASA", "temperatura": "NASA POWER",
                          "primeiro_dia": "2015-07-01", "ultimo_dia": "2026-09-14", "avisos": []},
                "regra_dos_anos": {"pior_ano": "2015-16", "ano_normal": "2019-20"},
                "calor": {"dias_de_calor_forte_no_pior_ano": 17, "limite_c": 35.0}}

    def verde_do_satelite(self, cidade_id):
        self.chamadas.append("verde_do_satelite")
        return {"dias_pelo_calendario": 122, "dias_pelo_satelite": 96, "leitura": "dentro_da_faixa",
                "frase": "Pelo calendário, a terra fica 122 dias sem planta. O satélite viu 96 dias seguidos sem "
                         "planta verde.",
                "aviso": "O satélite mede o verde das folhas e não vê a palha."}

    def replay_da_safra(self, entrada, safra):
        self.chamadas.append("replay_da_safra")
        self._conferir(entrada)
        dias = [{"data": f"2016-03-{dia:02d}", "cultura": "milho", "chuva_mm": 0.0, "agua_na_terra_mm": 40.0 - dia,
                 "pedido_mm": 5.1, "bebido_mm": 3.3, "falta_mm": 1.8, "com_sede": dia > 13, "tmax_c": 33.3,
                 "calor_forte": False} for dia in range(1, 21)]
        return {"dias": dias, "marcos": copy.deepcopy(MARCOS)}

    def como_esta_hoje(self, entrada):
        self.chamadas.append("como_esta_hoje")
        return {"ultimo_dia_com_dado": "2026-11-12", "atraso_dias": 3, "agua_na_terra_mm": 71.5,
                "no_ano_normal_mm": 88.0, "no_pior_ano_mm": 52.4, "aviso": "O dado chega com 3 dias de atraso."}

    def registro_da_safra(self, entrada, safra):
        self.chamadas.append("registro_da_safra")
        return {"plantado": ["soja", "milho"], "falta_de_agua_mm": 232.9, "dias_de_calor_forte": 17,
                "dias_sem_planta_viva": 122, "frase": f"Na safra {safra} faltaram 232,9 mm de água."}
