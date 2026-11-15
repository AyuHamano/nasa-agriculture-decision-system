# Gerado com IA (Claude)
"""As duas rotações e o calendário: o que está na terra em cada dia e quanto pede de água (o Kc do dia).

- A rotação de hoje ("atual"): soja -> milho safrinha -> pousio (terra parada, sem planta viva).
- A alternativa, uma só: soja -> milho com braquiária (capim). O capim nasce junto com o milho, fica vivo depois da
  colheita e é seco (dessecado) alguns dias antes de plantar a soja.
A curva do Kc por fase é a do FAO-56, cap. 6 (eq. 66): https://www.fao.org/4/X0490E/x0490e0b.htm
A palha (FAO-56, cap. 10, "Effects of surface mulches": https://www.fao.org/4/X0490E/x0490e0g.htm): a evaporação da
terra cai uns 5% a cada 10% de terra coberta por palha. Vale nas DUAS rotações (no plantio direto a palha do milho
também fica), com coberturas diferentes, nos dias sem planta viva e na fase inicial da soja (o Kc ini).
A disputa do capim com o milho (hipótese, em faixa): enquanto os dois crescem juntos, o conjunto pede
(1 + fator) x o pedido do milho. Com o fator em zero, o capim não tira nada do milho.
"""
import datetime
import re

from orbita import parametros

SEM_PLANTA = "sem_planta"
BRAQUIARIA = "braquiaria"
CULTURAS = ("soja", "milho")
ROTACOES = {
    "atual": {"nome": "soja → milho safrinha → pousio (terra parada)", "com_braquiaria": False},
    "alternativa": {"nome": "soja → milho com braquiária (capim)", "com_braquiaria": True},
}
DIAS_DO_MES = 365 / 12
JANELA_DA_SOJA = ((9, 1), (12, 31))   # o plantio da soja que o produtor informa: de 1 de setembro a 31 de dezembro


def ler_plantio_da_soja(texto):
    """A data do plantio da soja que o produtor informou (AAAA-MM-DD), como data. Fora do formato: erro.

    Só o mês e o dia entram no ensaio das safras guardadas (o mesmo dia em todos os anos); a janela vai de 1 de
    setembro a 31 de dezembro, que é o começo da safra na conta (a safra vai de 1 de setembro a 31 de agosto).
    """
    if isinstance(texto, datetime.date):
        data = texto
    else:
        try:    # só o formato ano-mês-dia com traços (o fromisoformat do Python também aceita 20261105)
            if not isinstance(texto, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto.strip()):
                raise ValueError(texto)
            data = datetime.date.fromisoformat(texto.strip())
        except ValueError:
            raise ValueError(f'plantio_da_soja "{texto}" fora do formato: use ano-mês-dia, como 2026-11-05 '
                             "(5 de novembro de 2026)") from None
    if not JANELA_DA_SOJA[0] <= (data.month, data.day) <= JANELA_DA_SOJA[1]:
        raise ValueError(f'plantio_da_soja "{data.isoformat()}" fora da janela: o motor aceita o plantio da soja de '
                         "1 de setembro a 31 de dezembro")
    return data


def fator_da_palha(cobertura, reducao):
    """Por quanto se multiplica a evaporação da terra com a fração `cobertura` (0 a 1) coberta de palha.

    FAO-56, cap. 10: "reduce the amount of soil water evaporation by about 5% for each 10% of soil surface that is
    effectively covered by an organic mulch" (reducao = 0,5): com 50% de cobertura, 25% a menos.
    """
    if not 0.0 <= cobertura <= 1.0 or not 0.0 <= reducao <= 1.0:
        raise ValueError("A cobertura de palha e a redução por cobertura são frações entre 0 e 1 "
                         f"(vieram {cobertura} e {reducao}).")
    return 1.0 - reducao * cobertura


def _mes_dia(texto):
    try:
        mes, dia = (int(parte) for parte in str(texto).split("-"))
        datetime.date(2021, mes, dia)
    except ValueError:
        raise ValueError(f"Data de plantio fora do formato: '{texto}'. Use mês-dia, como 10-15 (15 de outubro).") from None
    return mes, dia


def kc_da_fase(n, fases, kc_ini, kc_meio, kc_fim):
    """O Kc no dia n do ciclo (0 = dia do plantio). FAO-56: constante no início e no meio, reta entre eles (eq. 66)."""
    inicio, crescimento, meio, final = fases
    dia = n + 1  # no FAO-56 o dia do plantio é o dia 1 (Exemplo 28: dia 40 -> 0,77; dia 95 -> 0,56)
    if n < inicio:
        return kc_ini
    if n < inicio + crescimento:
        return kc_ini + (dia - inicio) / crescimento * (kc_meio - kc_ini)
    if n < inicio + crescimento + meio:
        return kc_meio
    return kc_meio + (dia - inicio - crescimento - meio) / final * (kc_fim - kc_meio)


class Calendario:
    """As datas e os coeficientes das culturas, lidos dos parâmetros e conferidos uma vez."""

    def __init__(self, par, plantio_da_soja=None):
        def v(*caminho):
            return parametros.valor(par, *caminho)
        # A data do produtor (opcional): a soja entra no mês e dia dele, e o calendário inteiro anda o mesmo número
        # de dias (a 2ª safra entra depois de a soja sair, com o mesmo intervalo do calendário de costume).
        self.soja_md_de_costume = _mes_dia(v("culturas", "soja", "plantio_mes_dia"))
        self.soja_md = self.soja_md_de_costume
        if plantio_da_soja is not None:
            informado = ler_plantio_da_soja(plantio_da_soja)
            self.soja_md = (informado.month, informado.day)
        self.deslocamento_dias = (datetime.date(2021, *self.soja_md)
                                  - datetime.date(2021, *self.soja_md_de_costume)).days
        self.soja_fases = list(v("culturas", "soja", "fases_dias"))
        self.soja_kc = tuple(v("culturas", "soja", k) for k in ("kc_ini", "kc_meio", "kc_fim"))
        self.soja_p = v("culturas", "soja", "p")
        self.milho_md = _mes_dia(v("culturas", "milho_2a_safra", "plantio_mes_dia"))
        self.milho_fases = list(v("culturas", "milho_2a_safra", "fases_dias"))
        self.milho_kc = tuple(v("culturas", "milho_2a_safra", k) for k in ("kc_ini", "kc_meio", "kc_fim"))
        self.milho_p = v("culturas", "milho_2a_safra", "p")
        self.braquiaria_kc = v("culturas", "braquiaria_apos_milho", "kc")
        self.braquiaria_p = v("culturas", "braquiaria_apos_milho", "p")
        self.dessecacao_dias = int(v("culturas", "braquiaria_apos_milho", "dessecacao_dias_antes_da_soja"))
        self.solo_nu_kc = v("culturas", "solo_nu", "kc")
        # A palha: a cobertura de cada rotação (False = a de hoje, True = a alternativa) e o fator na evaporação.
        self.palha_reducao = v("palha", "reducao_por_cobertura")
        self.cobertura_de_palha = {False: v("palha", "cobertura_do_milho_solteiro"),
                                   True: v("palha", "cobertura_do_milho_com_braquiaria")}
        self.fator_da_palha = {com: fator_da_palha(cobertura, self.palha_reducao)
                               for com, cobertura in self.cobertura_de_palha.items()}
        # A profundidade das raízes de cada cobertura; a terra sem planta vale com a mais funda delas (o perfil).
        self.raizes = {"soja": v("culturas", "soja", "raiz_m"), "milho": v("culturas", "milho_2a_safra", "raiz_m"),
                       BRAQUIARIA: v("culturas", "braquiaria_apos_milho", "raiz_m")}
        self.raizes[SEM_PLANTA] = max(self.raizes.values())
        for nome, fases in (("soja", self.soja_fases), ("milho", self.milho_fases)):
            if len(fases) != 4 or any(f <= 0 for f in fases):
                raise ValueError(f"As fases da cultura ({nome}) têm de ser 4 números de dias, todos acima de zero.")
        self.soja_ciclo, self.milho_ciclo = sum(self.soja_fases), sum(self.milho_fases)
        if self.fim_da_soja(2021) > self.plantio_do_milho(2022):
            raise ValueError("Calendário impossível: o milho está sendo plantado antes de a soja sair da terra ("
                             f"a soja sai em {self.fim_da_soja(2021):%d/%m}, o milho entra em "
                             f"{self.plantio_do_milho(2022):%d/%m}).")
        if not self.fim_do_milho(2022) <= self.dessecacao(2022) <= self.plantio_da_soja(2022):
            raise ValueError("Calendário impossível: o milho tem de sair antes de secar a braquiária, e a braquiária "
                             "tem de ser seca antes de plantar a soja.")

    def plantio_da_soja(self, ano):
        return datetime.date(ano, *self.soja_md)

    def fim_da_soja(self, ano_do_plantio):
        """O primeiro dia sem soja na terra."""
        return self.plantio_da_soja(ano_do_plantio) + datetime.timedelta(days=self.soja_ciclo)

    def plantio_do_milho(self, ano):
        """O plantio da 2ª safra "do ano": a data de costume mais os dias que o calendário andou."""
        return datetime.date(ano, *self.milho_md) + datetime.timedelta(days=self.deslocamento_dias)

    def fim_do_milho(self, ano):
        """O primeiro dia sem milho vivo na terra (o fim do ciclo; a colheitadeira pode passar depois)."""
        return self.plantio_do_milho(ano) + datetime.timedelta(days=self.milho_ciclo)

    def dessecacao(self, ano):
        return self.plantio_da_soja(ano) - datetime.timedelta(days=self.dessecacao_dias)


def calendario(par, plantio_da_soja=None):
    return Calendario(par, plantio_da_soja)


def cobertura_do_dia(data, com_braquiaria, cal, disputa=0.0):
    """O que está na terra no dia: (tipo, Kc do dia, p). Tipos: soja, milho, braquiaria, sem_planta.

    A palha da rotação baixa o Kc nos dias sem planta e na fase inicial da soja. Com `disputa` acima de zero (só na
    alternativa), o dia de milho devolve um 4º valor: o fator a mais que o capim põe no pedido de água do conjunto.
    """
    palha = cal.fator_da_palha[bool(com_braquiaria)]
    for ano in (data.year, data.year - 1):
        n = (data - cal.plantio_da_soja(ano)).days
        if 0 <= n < cal.soja_ciclo:
            kc = kc_da_fase(n, cal.soja_fases, *cal.soja_kc)
            return ("soja", kc * palha if n < cal.soja_fases[0] else kc, cal.soja_p)
    # Com a soja plantada cedo, a 2ª safra "do ano seguinte" pode entrar ainda em dezembro: olha os dois anos.
    for ano in (data.year, data.year + 1):
        n = (data - cal.plantio_do_milho(ano)).days
        if 0 <= n < cal.milho_ciclo:
            milho = ("milho", kc_da_fase(n, cal.milho_fases, *cal.milho_kc), cal.milho_p)
            return milho + (disputa,) if com_braquiaria and disputa else milho
    if com_braquiaria:
        for ano in (data.year, data.year + 1):
            if cal.fim_do_milho(ano) <= data < cal.dessecacao(ano):
                return (BRAQUIARIA, cal.braquiaria_kc, cal.braquiaria_p)
    return (SEM_PLANTA, cal.solo_nu_kc * palha, None)


def resumo_do_calendario(par, plantio_da_soja=None):
    """As datas do calendário e os dias sem planta viva de cada rotação (num ano comum, de 365 dias)."""
    cal = Calendario(par, plantio_da_soja)
    plantio, fim_soja = cal.plantio_da_soja(2021), cal.fim_da_soja(2021)
    plantio_milho, fim_milho = cal.plantio_do_milho(2022), cal.fim_do_milho(2022)
    proxima_soja, dessecacao = cal.plantio_da_soja(2022), cal.dessecacao(2022)
    dias = {"atual": (proxima_soja - fim_milho).days, "alternativa": (proxima_soja - dessecacao).days}
    inicio = {"atual": fim_milho, "alternativa": dessecacao}
    resumo = {
        "soja": {"plantio": f"{plantio:%d/%m}", "sai_da_terra": f"{fim_soja:%d/%m}", "ciclo_dias": cal.soja_ciclo},
        "milho": {"plantio": f"{plantio_milho:%d/%m}", "sai_da_terra": f"{fim_milho:%d/%m}",
                  "ciclo_dias": cal.milho_ciclo},
        "braquiaria": {"seca_em": f"{dessecacao:%d/%m}", "dias_antes_da_soja": cal.dessecacao_dias},
        "entre_a_soja_e_o_milho_dias": (plantio_milho - fim_soja).days,
    }
    for rotacao in ROTACOES:
        resumo[rotacao] = {"dias_sem_planta_viva": dias[rotacao],
                           "meses_sem_planta_viva": round(dias[rotacao] / DIAS_DO_MES, 1),
                           "de": f"{inicio[rotacao]:%d/%m}", "ate": f"{proxima_soja:%d/%m}"}
    return resumo
