# Gerado com IA (Claude)
"""As duas rotações e o calendário: o que está na terra em cada dia e quanto pede de água (o Kc do dia).

- A rotação de hoje ("atual"): soja -> milho safrinha -> pousio (terra parada, sem planta viva).
- A alternativa, uma só: soja -> milho com braquiária (capim). O capim nasce junto com o milho, fica vivo depois da
  colheita e é seco (dessecado) alguns dias antes de plantar a soja.
A curva do Kc por fase é a do FAO-56, cap. 6 (eq. 66): https://www.fao.org/4/X0490E/x0490e0b.htm
Hipótese declarada: enquanto o milho está na terra, a braquiária debaixo dele não aumenta o pedido de água.
"""
import datetime

from orbita import parametros

SEM_PLANTA = "sem_planta"
BRAQUIARIA = "braquiaria"
CULTURAS = ("soja", "milho")
ROTACOES = {
    "atual": {"nome": "soja → milho safrinha → pousio (terra parada)", "com_braquiaria": False},
    "alternativa": {"nome": "soja → milho com braquiária (capim)", "com_braquiaria": True},
}
DIAS_DO_MES = 365 / 12


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
    if n < inicio:
        return kc_ini
    if n < inicio + crescimento:
        return kc_ini + (n - inicio) / crescimento * (kc_meio - kc_ini)
    if n < inicio + crescimento + meio:
        return kc_meio
    return kc_meio + (n - inicio - crescimento - meio) / final * (kc_fim - kc_meio)


class Calendario:
    """As datas e os coeficientes das culturas, lidos dos parâmetros e conferidos uma vez."""

    def __init__(self, par):
        def v(*caminho):
            return parametros.valor(par, *caminho)
        self.soja_md = _mes_dia(v("culturas", "soja", "plantio_mes_dia"))
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
        return datetime.date(ano, *self.milho_md)

    def fim_do_milho(self, ano):
        """O primeiro dia sem milho vivo na terra (o fim do ciclo; a colheitadeira pode passar depois)."""
        return self.plantio_do_milho(ano) + datetime.timedelta(days=self.milho_ciclo)

    def dessecacao(self, ano):
        return self.plantio_da_soja(ano) - datetime.timedelta(days=self.dessecacao_dias)


def calendario(par):
    return Calendario(par)


def cobertura_do_dia(data, com_braquiaria, cal):
    """O que está na terra no dia: (tipo, Kc do dia, p). Tipos: soja, milho, braquiaria, sem_planta."""
    for ano in (data.year, data.year - 1):
        n = (data - cal.plantio_da_soja(ano)).days
        if 0 <= n < cal.soja_ciclo:
            return ("soja", kc_da_fase(n, cal.soja_fases, *cal.soja_kc), cal.soja_p)
    n = (data - cal.plantio_do_milho(data.year)).days
    if 0 <= n < cal.milho_ciclo:
        return ("milho", kc_da_fase(n, cal.milho_fases, *cal.milho_kc), cal.milho_p)
    if com_braquiaria and cal.fim_do_milho(data.year) <= data < cal.dessecacao(data.year):
        return (BRAQUIARIA, cal.braquiaria_kc, cal.braquiaria_p)
    return (SEM_PLANTA, cal.solo_nu_kc, None)


def resumo_do_calendario(par):
    """As datas do calendário e os dias sem planta viva de cada rotação (num ano comum, de 365 dias)."""
    cal = Calendario(par)
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
