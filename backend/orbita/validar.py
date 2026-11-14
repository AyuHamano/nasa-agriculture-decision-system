# Gerado com IA (Claude)
"""A validação cruzada: confere a conta do motor com outras fontes. De dentro de backend/: python3 -m orbita.validar

Lê data/orbita/validacao/ (ver o LEIA-ME de lá) e mostra:
1. a chuva de 1/fev a 30/jun por safra em cada fonte, e a safra mais seca de cada uma;
2. a chuva de modelo da NASA POWER contra a estação em terra do INMET (dia em branco não vira zero);
3. a ETo do motor (Hargreaves) contra a ETo do FAO que o Open-Meteo entrega;
4. a falta de água simulada do milho, com cada fonte de chuva, contra o rendimento do milho de 2ª safra no IBGE;
5. o NDVI (o verde visto pelo satélite) contra o calendário.
Se um arquivo não estiver lá, diz o que falta e segue.
"""
import datetime
import math
import sys
from pathlib import Path

from orbita import balanco, clima, motor, parametros, rotacoes

PASTA = clima.PASTA_DOS_DADOS / "validacao"
BRANCOS_TOLERADOS = 10
SAFRAS = balanco.SAFRAS_DO_ESTUDO + (motor.SAFRA_A_PARTE,)


def postos(valores):
    """O posto de cada valor (1 = o menor); valores iguais dividem a média dos postos."""
    ordem = sorted(range(len(valores)), key=lambda i: valores[i])
    saida, i = [0.0] * len(valores), 0
    while i < len(ordem):
        j = i
        while j + 1 < len(ordem) and valores[ordem[j + 1]] == valores[ordem[i]]:
            j += 1
        for k in range(i, j + 1):
            saida[ordem[k]] = (i + j) / 2 + 1
        i = j + 1
    return saida


def pearson(x, y):
    if len(x) < 3:
        return None
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sx, sy = sum((a - mx) ** 2 for a in x), sum((b - my) ** 2 for b in y)
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sx * sy)


def spearman(x, y):
    """A correlação de postos: +1 = sobem juntos, -1 = um sobe e o outro desce, 0 = sem relação."""
    return pearson(postos(x), postos(y))


def soma_da_janela(valores, inicio, fim):
    """A soma dos dias com dado entre as duas datas e quantos dias ficaram em branco (ou fora do arquivo)."""
    soma, brancos, dia = 0.0, 0, inicio
    while dia <= fim:
        valor = valores.get(dia)
        if valor is None:
            brancos += 1
        else:
            soma += valor
        dia += datetime.timedelta(days=1)
    return soma, brancos


def _janela(safra):
    ano = int(safra[:4]) + 1
    return datetime.date(ano, 2, 1), datetime.date(ano, 6, 30)


def _n(numero, casas=0):
    return "--" if numero is None else f"{numero:.{casas}f}".replace(".", ",")


def _chuvas(pasta):
    """fonte -> {data: chuva}: a NASA POWER guardada e cada CSV de pasta/chuva."""
    fontes = {"power": {d.data: d.chuva for d in clima.ler_serie()}}
    for arquivo in sorted((Path(pasta) / "chuva").glob("*.csv")):
        fontes[arquivo.stem] = clima.ler_chuva_csv(arquivo)
    return fontes


def _parte_1(pasta, p):
    p("1. A CHUVA DE 1/FEV A 30/JUN POR SAFRA, EM CADA FONTE (mm)")
    fontes = _chuvas(pasta)
    if len(fontes) == 1:
        p(f"FALTA: nenhum arquivo de chuva em {Path(pasta) / 'chuva'} (esperado: open-meteo.csv com data,chuva_mm,"
          "tmax_c,tmin_c,eto_mm; e <fonte>.csv com data,chuva_mm). Só a NASA POWER aparece.")
    nomes = list(fontes)
    p("   safra   | " + " | ".join(f"{nome:>10}" for nome in nomes))
    mais_seca = {}
    for safra in SAFRAS:
        celulas = []
        for nome in nomes:
            soma, brancos = soma_da_janela(fontes[nome], *_janela(safra))
            if brancos > BRANCOS_TOLERADOS:
                celulas.append(f"{'--(' + str(brancos) + ')':>10}")
            else:
                celulas.append(f"{_n(soma) + ('*' + str(brancos) if brancos else ''):>10}")
                if safra in balanco.SAFRAS_DO_ESTUDO and soma < mais_seca.get(nome, (None, 1e9))[1]:
                    mais_seca[nome] = (safra, soma)
        p(f"   {safra} | " + " | ".join(celulas))
    p(f"   (*n = n dias em branco na janela, somados só os dias com dado; --(n) = mais de {BRANCOS_TOLERADOS} dias "
      "em branco, janela não comparada; a safra 2025-26 fica fora das 10)")
    p("   A safra mais seca das 10 em cada fonte: " + "; ".join(
        f"{nome} {safra} ({_n(soma)} mm)" for nome, (safra, soma) in mais_seca.items()) + ".")
    return fontes


def _parte_2(fontes, p):
    p("")
    p("2. A NASA POWER CONTRA A ESTAÇÃO EM TERRA DO INMET (a chuva de modelo PRECTOTCORR contra a chuva medida)")
    if "inmet" not in fontes:
        p("FALTA: chuva/inmet.csv (data,chuva_mm; a estação do INMET de Rio Verde, com o dia sem dado em branco).")
        return
    inmet, power = fontes["inmet"], fontes["power"]

    def comparar(rotulo, inicio, fim):
        _, brancos = soma_da_janela(inmet, inicio, fim)
        if brancos > BRANCOS_TOLERADOS:
            p(f"   {rotulo}: não comparado ({brancos} dias em branco na estação)")
            return None
        dias = [d for d in inmet if inicio <= d <= fim and inmet[d] is not None and power.get(d) is not None]
        medido, modelo = sum(inmet[d] for d in dias), sum(power[d] for d in dias)
        razao = 100 * modelo / medido if medido else None
        p(f"   {rotulo}: estação {_n(medido)} mm, NASA POWER {_n(modelo)} mm nos mesmos dias "
          f"({_n(razao)}% da estação; {brancos} dias em branco)")
        return razao

    p("   De 1/fev a 30/jun, por safra:")
    razoes = {safra: comparar(f"safra {safra}", *_janela(safra)) for safra in SAFRAS}
    p("   No ano inteiro:")
    for ano in range(2015, 2026):
        comparar(f"ano {ano}", datetime.date(ano, 1, 1), datetime.date(ano, 12, 31))
    antes = [r for s, r in razoes.items() if r is not None and int(s[:4]) + 1 <= 2020]
    depois = [r for s, r in razoes.items() if r is not None and int(s[:4]) + 1 >= 2021]
    if antes and depois:
        p(f"   Na janela da 2ª safra, a NASA POWER deu em média {_n(sum(antes) / len(antes))}% da estação até 2020 "
          f"({len(antes)} safras comparadas) e {_n(sum(depois) / len(depois))}% de 2021 em diante ({len(depois)} "
          "safras comparadas).")


def _parte_3(pasta, p):
    import csv
    p("")
    p("3. A ETo DO MOTOR (Hargreaves, com a temperatura da NASA POWER) CONTRA A ETo DO FAO NO OPEN-METEO")
    motor_eto = {d.data: d.eto for d in clima.ler_serie()}
    achou = False
    for nome in ("open-meteo", "era5"):
        arquivo = Path(pasta) / "chuva" / f"{nome}.csv"
        if not arquivo.exists():
            continue
        pares = []
        with open(arquivo, encoding="utf-8", newline="") as f:
            for linha in csv.DictReader(f):
                texto = (linha.get("eto_mm") or "").strip()
                dia = datetime.date.fromisoformat(linha["data"].strip())
                if texto and dia in motor_eto:
                    pares.append((motor_eto[dia], float(texto)))
        if not pares:
            continue
        achou = True
        do_motor, de_fora = [a for a, _ in pares], [b for _, b in pares]
        media_motor, media_fora = sum(do_motor) / len(pares), sum(de_fora) / len(pares)
        p(f"   {nome}: em {len(pares)} dias, o motor dá em média {_n(media_motor, 2)} mm/dia e o Open-Meteo "
          f"{_n(media_fora, 2)} mm/dia (o motor fica {_n(100 * (media_motor / media_fora - 1), 1)}% "
          f"{'acima' if media_motor > media_fora else 'abaixo'}); correlação dia a dia {_n(pearson(do_motor, de_fora), 2)}.")
    if not achou:
        p("FALTA: chuva/open-meteo.csv com a coluna eto_mm (data,chuva_mm,tmax_c,tmin_c,eto_mm).")


def _parte_4(pasta, p):
    p("")
    p("4. A FALTA DE ÁGUA SIMULADA DO MILHO (rotação de hoje, terra média) CONTRA O RENDIMENTO DO MILHO NO IBGE")
    arquivo = Path(pasta) / "ibge" / "rendimento_rio_verde.csv"
    if not arquivo.exists():
        p(f"FALTA: ibge/rendimento_rio_verde.csv (ano,produto,rendimento_kg_ha,area_colhida_ha,producao_t) em {pasta}.")
        return
    rendimento = motor.ler_rendimento_do_milho(arquivo)
    par = parametros.carregar()
    faltas = {}
    for fonte in clima.FONTES_DE_CHUVA:
        try:
            dias, _ = clima.ler_serie_com_aviso(fonte, Path(pasta) / "chuva")
        except ValueError as erro:
            p(f"FALTA: a chuva '{fonte}' não entrou ({erro})")
            continue
        numeros = balanco.numeros_por_safra(balanco.simular(dias, False, par, "media"))
        faltas[fonte] = {s: numeros[s]["milho"]["falta_relativa_pct"] for s in balanco.SAFRAS_DO_ESTUDO}
    safras = [s for s in balanco.SAFRAS_DO_ESTUDO if s in rendimento]
    p("   (a falta é em % do que o milho pediu; o ano N do IBGE é a safra (N-1)/N)")
    p("   safra   | IBGE kg/ha | " + " | ".join(f"{fonte:>7}" for fonte in faltas))
    for s in safras:
        p(f"   {s} | {_n(rendimento[s]):>10} | " + " | ".join(f"{_n(faltas[f][s], 1):>6}%" for f in faltas))
    correlacoes = {f: spearman([faltas[f][s] for s in safras], [rendimento[s] for s in safras]) for f in faltas}
    p("   A correlação de postos entre a falta de água e o rendimento (quanto mais perto de -1, mais a conta "
      "acompanha a colheita): " + "; ".join(f"{f} {_n(c, 2)}" for f, c in correlacoes.items()) + ".")
    for f in faltas:
        pior = max(safras, key=lambda s: faltas[f][s])
        p(f"   Com a chuva {f}, a safra de maior falta de água do milho é {pior} ({_n(faltas[f][pior], 1)}%).")
    pior_ibge = min(safras, key=lambda s: rendimento[s])
    p(f"   No IBGE, o pior rendimento das {len(safras)} safras é o da {pior_ibge} ({_n(rendimento[pior_ibge])} kg/ha).")
    validas = {f: c for f, c in correlacoes.items() if c is not None}
    if validas:
        melhor = min(validas, key=validas.get)
        p(f"   A fonte de chuva que faz a conta acompanhar melhor a colheita: {melhor} ({_n(validas[melhor], 2)}). "
          f"São só {len(safras)} safras: é indício, não prova. O rendimento também depende de praga, adubo, "
          "semente e data de plantio.")


def _parte_5(p):
    p("")
    p("5. O NDVI (O VERDE VISTO PELO SATÉLITE) CONTRA O CALENDÁRIO (prova só da rotação de hoje)")
    par = parametros.carregar()
    dias = rotacoes.resumo_do_calendario(par)["atual"]["dias_sem_planta_viva"]
    ndvi = motor._ndvi(par, dias)
    if not ndvi["disponivel"]:
        p(f"FALTA: {ndvi['aviso']} (esperado: os CSV dos pontos em data/orbita/ndvi/)")
        return
    for frase in ndvi["frases"]:
        p("   " + frase)


def main(argv=None, pasta=PASTA, saida=None):
    saida = saida or sys.stdout

    def p(linha):
        print(linha, file=saida)

    p("ÓRBITA RURAL · a validação cruzada (os dados para cruzar estão em " + str(pasta) + ")")
    p("")
    fontes = _parte_1(pasta, p)
    _parte_2(fontes, p)
    _parte_3(pasta, p)
    _parte_4(pasta, p)
    _parte_5(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
