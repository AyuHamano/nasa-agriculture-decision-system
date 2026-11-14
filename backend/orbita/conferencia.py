# Gerado com IA (Claude).
"""A trava do texto: todo número escrito tem de estar na conta do motor.

Uso:
    from orbita.conferencia import conferir_texto
    sobras = conferir_texto(texto, resposta)      # lista vazia = o texto pode ir à tela

`texto` é a explicação em português (escrita por gente ou por IA). `resposta` é o que o
motor devolveu: um dicionário ou uma lista, de qualquer profundidade. A função devolve a
lista dos números do texto que NÃO estão na resposta, como foram escritos, na ordem em
que aparecem e sem repetir.

As regras:
- Da resposta entram todos os números: os valores, as chaves e os que estão dentro dos
  textos dela. Verdadeiro/falso e vazio não são números.
- O texto pode escrever do jeito brasileiro ("1.234,5", "34 dias", "20%", "0,38") ou do
  inglês ("1234.5", "1,234.5"). Um separador só, seguido de 3 algarismos ("1.234"), pode
  ser milhar ou decimal: vale se uma das duas leituras estiver na resposta.
- Um número do texto vale se for igual a um número da resposta arredondado para as mesmas
  casas com que foi escrito: com 87,26 na resposta, valem "87,26", "87,3" e "87"; não
  valem "87,2" nem "87,30".
- Porcentagem: "35%" vale se a resposta tiver 35 ou a fração 0,35.
- Ano ("2020") vale se aparecer na resposta. Rótulo de safra ("2020-21", "2020/21",
  "2020-2021") vale inteiro, se o mesmo rótulo aparecer na resposta; o "21" do rótulo não
  libera "21 dias". O rótulo libera os dois anos dele (2020 e 2021).
- Data ("2026-10-16", "16/10/2026", "16 de outubro de 2026") vale inteira, se a mesma data
  aparecer na resposta; o dia e o mês de uma data não liberam número solto, só o ano.
- `permitidos` são números (ou textos com números, rótulos e datas) liberados à parte.

O que a trava NÃO faz (para ninguém confiar além da conta):
- Não confere a que coisa o número se refere: "34 dias" passa se houver um 34 em qualquer
  lugar da resposta.
- Não confere o sinal: olha o tamanho do número ("24 dias a menos" passa com -24).
- Não vê número escrito por extenso ("três meses").
- Não confere ordinal ("2ª safra", "1º plantio"), hora ("18h04") nem número colado em
  letra, que é nome ("MOD13Q1", "v061").
"""
import math
import re
from datetime import date, datetime
from decimal import Decimal
from fractions import Fraction

_MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}

# A ordem importa: data antes de safra, safra antes de número.
_FICHA = re.compile(
    r"""
      (?P<iso>(?<![\w.,/-])(?P<iso_a>\d{4})-(?P<iso_m>\d{2})-(?P<iso_d>\d{2})(?![\d-])
          (?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?)
    | (?P<br>(?<![\w.,/-])(?P<br_d>\d{1,2})/(?P<br_m>\d{1,2})/(?P<br_a>\d{4})(?![\d/]))
    | (?P<extenso>(?<![\w.,/-])(?P<ex_d>\d{1,2})[ºo°]?\s+de\s+(?P<ex_m>%s)\b
          (?:\s+de\s+(?P<ex_a>\d{4})(?!\d))?)
    | (?P<safra>(?<![\w.,/-])(?P<sa_1>(?:19|20)\d{2})[-/–](?P<sa_2>(?:19|20)\d{2}|\d{2})
          (?![\w/-]|[.,]\d))
    | (?P<hora>(?<![\w.,])\d{1,2}h\d{2}(?!\w))
    | (?P<ordinal>(?<![\w.,])(?:\d+[ªº]|\d{1,2}[ao](?!\w)))
    | (?P<numero>(?<!\w)\d+(?:[.,]\d+)*)(?P<pct>\s*(?:%%|por\s+cento\b))?
    """ % "|".join(_MESES),
    re.VERBOSE | re.IGNORECASE,
)


class _Achado:
    """O que foi juntado da resposta (ou dos permitidos)."""

    def __init__(self):
        self.numeros = set()    # os tamanhos (sem sinal)
        self.rotulos = set()    # safras, no formato "2020-21"
        self.datas = set()      # datas inteiras
        self.dias_do_ano = set()  # (mês, dia) de data escrita sem ano

    def numero(self, valor):
        try:
            valor = abs(float(valor))
        except (OverflowError, ValueError):
            return
        if math.isfinite(valor):
            self.numeros.add(valor)

    def data(self, dia):
        self.datas.add(dia)
        self.dias_do_ano.add((dia.month, dia.day))
        self.numero(dia.year)


def _grupos_de_milhar(grupos):
    return 1 <= len(grupos[0]) <= 3 and all(len(g) == 3 for g in grupos[1:])


def _leituras(escrito):
    """As leituras possíveis de um número escrito: [(valor, casas)]. Vazia = não deu para ler."""
    tem_ponto, tem_virgula = "." in escrito, "," in escrito
    if not tem_ponto and not tem_virgula:
        return [(float(escrito), 0)]
    if tem_ponto and tem_virgula:
        decimal = "," if escrito.rfind(",") > escrito.rfind(".") else "."
        milhar = "." if decimal == "," else ","
        if escrito.count(decimal) != 1:
            return []
        inteiro, fracao = escrito.split(decimal)
        grupos = inteiro.split(milhar)
        if not _grupos_de_milhar(grupos):
            return []
        return [(float("".join(grupos) + "." + fracao), len(fracao))]
    partes = escrito.split("." if tem_ponto else ",")
    if len(partes) == 2:
        inteiro, fracao = partes
        leituras = [(float(inteiro + "." + fracao), len(fracao))]
        if len(fracao) == 3 and len(inteiro) <= 3 and inteiro[0] != "0":
            leituras.append((float(inteiro + fracao), 0))   # o separador era de milhar
        return leituras
    if _grupos_de_milhar(partes):
        return [(float("".join(partes)), 0)]
    return []


def _rotulo_de_safra(m):
    """"2020-21", se os dois anos forem seguidos; senão, None."""
    primeiro, segundo = int(m.group("sa_1")), m.group("sa_2")
    seguinte = primeiro + 1
    if int(segundo) == (seguinte if len(segundo) == 4 else seguinte % 100):
        return "%d-%02d" % (primeiro, seguinte % 100)
    return None


def _data(m):
    """(data inteira, (mês, dia)) da ficha. Data que não existe devolve (None, None)."""
    try:
        if m.group("iso"):
            dia = date(int(m.group("iso_a")), int(m.group("iso_m")), int(m.group("iso_d")))
        elif m.group("br"):
            dia = date(int(m.group("br_a")), int(m.group("br_m")), int(m.group("br_d")))
        else:
            mes = _MESES[m.group("ex_m").lower()]
            if m.group("ex_a") is None:
                date(2000, mes, int(m.group("ex_d")))   # 2000 é bissexto: aceita 29 de fevereiro
                return None, (mes, int(m.group("ex_d")))
            dia = date(int(m.group("ex_a")), mes, int(m.group("ex_d")))
    except ValueError:
        return None, None
    return dia, (dia.month, dia.day)


def _fichas(texto):
    """Quebra um texto em fichas: (tipo, como foi escrito, dado).

    tipo "data": dado = (data ou None, (mês, dia) ou None)
    tipo "safra": dado = o rótulo "2020-21"
    tipo "numero": dado = (leituras, é porcentagem)
    """
    for m in _FICHA.finditer(texto):
        if m.group("ordinal") or m.group("hora"):
            continue
        if m.group("iso") or m.group("br") or m.group("extenso"):
            yield "data", " ".join(m.group(0).split()), _data(m)
        elif m.group("safra"):
            rotulo = _rotulo_de_safra(m)
            if rotulo:
                yield "safra", m.group("safra"), rotulo
            else:   # dois anos que não são seguidos: são dois números
                for pedaco in (m.group("sa_1"), m.group("sa_2")):
                    yield "numero", pedaco, ([(float(pedaco), 0)], False)
        else:
            escrito, pct = m.group("numero"), bool(m.group("pct"))
            leituras = _leituras(escrito)
            if leituras:
                yield "numero", escrito + ("%" if pct else ""), (leituras, pct)
            else:   # separadores sem sentido ("1.2.3"): cada pedaço é um número
                for pedaco in re.findall(r"\d+", escrito):
                    yield "numero", pedaco, ([(float(pedaco), 0)], False)


def _juntar_texto(texto, achado):
    for tipo, _, dado in _fichas(texto):
        if tipo == "data":
            dia, dia_do_ano = dado
            if dia:
                achado.data(dia)
            elif dia_do_ano:
                achado.dias_do_ano.add(dia_do_ano)
        elif tipo == "safra":
            achado.rotulos.add(dado)
            achado.numero(int(dado[:4]))
            achado.numero(int(dado[:4]) + 1)
        else:
            for valor, _ in dado[0]:
                achado.numero(valor)


def _juntar(coisa, achado):
    """Percorre a resposta inteira (dicionário, lista, texto, número) e junta o que achar."""
    if coisa is None or isinstance(coisa, bool):
        return
    if isinstance(coisa, (int, float, Decimal, Fraction)):
        achado.numero(coisa)
    elif isinstance(coisa, datetime):
        achado.data(coisa.date())
    elif isinstance(coisa, date):
        achado.data(coisa)
    elif isinstance(coisa, str):
        _juntar_texto(coisa, achado)
    elif isinstance(coisa, dict):
        for chave, valor in coisa.items():
            _juntar(chave, achado)
            _juntar(valor, achado)
    elif isinstance(coisa, (list, tuple, set, frozenset)):
        for item in coisa:
            _juntar(item, achado)


def _vale(valor, casas, numeros):
    """O número escrito é algum número da resposta arredondado para as mesmas casas?"""
    folga = 0.5 * 10 ** -casas + 1e-9 * max(1.0, valor)
    return any(abs(n - valor) <= folga for n in numeros)


def conferir_texto(texto, resposta, permitidos=()):
    """Devolve os números do texto que não estão na resposta. Lista vazia = pode ir à tela."""
    if not isinstance(texto, str):
        raise TypeError("conferir_texto: o texto tem de ser uma frase (str), e veio %s."
                        % type(texto).__name__)
    achado = _Achado()
    _juntar(resposta, achado)
    _juntar(permitidos, achado)

    sobras = []
    for tipo, escrito, dado in _fichas(texto):
        if tipo == "data":
            dia, dia_do_ano = dado
            certo = dia in achado.datas if dia else dia_do_ano in achado.dias_do_ano
        elif tipo == "safra":
            certo = dado in achado.rotulos
        else:
            leituras, pct = dado
            certo = any(_vale(valor, casas, achado.numeros) for valor, casas in leituras)
            if not certo and pct:
                certo = any(_vale(valor / 100, casas + 2, achado.numeros) for valor, casas in leituras)
        if not certo and escrito not in sobras:
            sobras.append(escrito)
    return sobras
