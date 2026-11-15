# Gerado com IA (Claude).
"""O verde visto pelo satélite (NDVI): prova só da rotação de hoje.

O NDVI é um índice de 0 a 1 que o satélite mede: perto de 1, muita planta verde; perto de
0,2, quase nenhuma. Aqui ele responde uma pergunta só: de junho em diante, por quantos
dias seguidos cada ponto ficou "sem planta verde"?

A conta, por ponto (cada CSV de data/orbita/ndvi/ é um ponto):
1. A série boa: as medidas com `pixel_reliability` 0 (boa) ou 1 (aceitável) e `ndvi_bruto`
   diferente de -3000 ("sem dado"). O NDVI é o `ndvi_bruto` dividido por 10.000.
2. O limite de "sem planta verde": mínimo + fração x (máximo - mínimo) da série boa do
   ponto. A fração padrão é 0,20 e pode ser trocada.
3. Por ano completo, a maior sequência de medidas boas seguidas abaixo do limite, de 1 de
   junho a 31 de dezembro. Cada medida vale 16 dias. Medida ruim no meio não quebra a
   sequência nem soma dias (a conta fica para menos, nunca para mais).
4. Ano completo: de 1 de junho a 31 de dezembro, nenhum buraco de mais de 32 dias sem
   medida boa (falta de uma medida passa; de duas seguidas, não). O ano em que a série
   ainda não chegou a dezembro fica à parte, como "ano em andamento", fora da mediana.

Leitura: "sem planta verde" não é "terra descoberta". O satélite não vê a palha.

Uso, de `backend/`:
    python3 -m orbita.ndvi            # mostra o resumo em JSON
    from orbita import ndvi; ndvi.resumo(); ndvi.comparar_com_calendario(120)
"""
import csv
import json
import statistics
from datetime import date
from pathlib import Path

PASTA_DOS_DADOS = Path(__file__).resolve().parents[2] / "data" / "orbita" / "ndvi"

FRACAO_PADRAO = 0.20          # 20% da amplitude da série do ponto
# "hipótese" até a fonte do valor ser conferida (o método do limiar pela amplitude é o de
# programas como o TIMESAT, de Jönsson e Eklundh; lá a amplitude é a de cada safra, aqui é
# a da série inteira do ponto). Quem conferir a fonte troca esta etiqueta.
ETIQUETA_DA_FRACAO = "hipótese"
DIAS_POR_MEDIDA = 16          # o MOD13Q1 junta 16 dias em cada medida
BURACO_MAXIMO_DIAS = 32       # mais que isso sem medida boa, o ano não conta
MES_INICIAL = 6               # de junho em diante
ESCALA = 10000                # o ndvi_bruto vem multiplicado por 10.000
SEM_DADO = -3000              # o valor de "sem dado" do produto
QUALIDADE_QUE_VALE = (0, 1)   # pixel_reliability: 0 boa, 1 aceitável (2 neve, 3 nuvem)

FONTE = {
    "produto": "MOD13Q1 v061 (MODIS/Terra, índice de vegetação NDVI, uma medida a cada 16 dias, pixel de 250 m)",
    "de_quem": "NASA (LP DAAC)",
    "link": "https://doi.org/10.5067/MODIS/MOD13Q1.061",
    "espelho": "Microsoft Planetary Computer, coleção modis-13Q1-061",
    "link_do_espelho": "https://planetarycomputer.microsoft.com/dataset/modis-13Q1-061",
    "baixado_em": "2026-11-14",
    "onde_esta": "data/orbita/ndvi/ (um CSV por ponto; o LEIA-ME.md de lá conta a origem)",
}
AVISO = ('"Sem planta verde" não é "terra descoberta": o satélite mede o verde das folhas e não vê a palha. '
         "Um ponto sem planta verde pode estar coberto de palha.")
LUGAR_PADRAO = "Rio Verde (GO)"


def aviso_dos_pontos(lugar=LUGAR_PADRAO):
    """O aviso dos pontos de uma cidade. O de Rio Verde é o de sempre; o das outras diz também que ninguém foi ao campo."""
    aviso = ("Os pontos foram escolhidos no mapa, perto de %s: não se sabe de quem são "
             "nem o que foi plantado em cada um. É prova só da rotação de hoje." % lugar)
    if lugar != LUGAR_PADRAO:
        aviso += " Os pontos não foram conferidos em campo."
    return aviso


AVISO_DOS_PONTOS = aviso_dos_pontos()


def fonte(pasta=None):
    """A ficha da fonte dos pontos de uma pasta. Sem pasta (ou na de Rio Verde), a de sempre.

    Nas outras cidades, o dia em que foi baixado, onde está e a regra da escolha dos pontos saem do `fonte.json`
    que o programa de baixar (data/orbita/ndvi/baixar_ndvi.py) grava ao lado dos CSV.
    """
    ficha = dict(FONTE)
    if pasta is None or Path(pasta).resolve() == PASTA_DOS_DADOS.resolve():
        return ficha
    pasta = Path(pasta).resolve()
    try:
        ficha["onde_esta"] = pasta.relative_to(PASTA_DOS_DADOS.parents[2]).as_posix() + "/"
    except ValueError:
        ficha["onde_esta"] = str(pasta)
    ficha["onde_esta"] += " (um CSV por ponto; o fonte.json de lá guarda o endereço e a hora de cada consulta)"
    ficha["baixado_em"] = None
    arquivo = pasta / "fonte.json"
    if arquivo.exists():
        guardado = json.loads(arquivo.read_text(encoding="utf-8"))
        ficha["baixado_em"] = (guardado.get("terminou_em_utc") or "")[:10] or None
        regra = guardado.get("regra_da_escolha") or {}
        ficha["escolha_dos_pontos"] = "Candidatos %s. Mapa: %s. Passa se %s. Ficam %s." % (
            regra.get("candidatos"), regra.get("mapa"), regra.get("passa_se"), regra.get("ficam"))
    return ficha


def ler_csv(caminho):
    """Lê um ponto. Devolve lat, lon, as medidas boas [(data, ndvi)], o total e a última data."""
    boas, total, ultima, lat, lon = [], 0, None, None, None
    with Path(caminho).open(newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            dia = date.fromisoformat(linha["Date"].strip())
            bruto, qualidade = int(linha["ndvi_bruto"]), int(linha["pixel_reliability"])
            total += 1
            ultima = dia if ultima is None or dia > ultima else ultima
            if lat is None:
                lat, lon = float(linha["lat"]), float(linha["lon"])
            if qualidade in QUALIDADE_QUE_VALE and bruto != SEM_DADO:
                boas.append((dia, bruto / ESCALA))
    boas.sort()
    return {"lat": lat, "lon": lon, "boas": boas, "medidas": total, "ultima_data": ultima}


def ler_pontos(pasta=None):
    """Lê todos os CSV da pasta: {nome do ponto: o que ler_csv devolve}."""
    pasta = Path(pasta) if pasta else PASTA_DOS_DADOS
    arquivos = sorted(pasta.glob("*.csv"))
    if not arquivos:
        raise FileNotFoundError("Não achei nenhum CSV do NDVI em %s. Copie para lá os arquivos dos pontos "
                                "(Date, ndvi_bruto, pixel_reliability, lat, lon)." % pasta)
    return {a.stem: ler_csv(a) for a in arquivos}


def limite_sem_planta_verde(valores, fracao=FRACAO_PADRAO):
    """mínimo + fração x (máximo - mínimo), com 4 casas (as mesmas do dado)."""
    valores = list(valores)
    if not valores:
        raise ValueError("Sem medida boa não dá para calcular o limite de 'sem planta verde'.")
    if isinstance(fracao, bool) or not isinstance(fracao, (int, float)) or not 0 <= fracao <= 1:
        raise ValueError("A fração do limite tem de ser um número de 0 a 1 (o padrão é 0,20), e veio %r." % (fracao,))
    return round(min(valores) + fracao * (max(valores) - min(valores)), 4)


def _janela(serie_boa, ano):
    inicio, fim = date(ano, MES_INICIAL, 1), date(ano, 12, 31)
    return [(d, v) for d, v in serie_boa if inicio <= d <= fim]


def _sequencias(serie_boa, ano, limite):
    """Os tamanhos das sequências de medidas abaixo do limite, e se a última medida está abaixo."""
    tamanhos, atual = [], 0
    for _, valor in _janela(serie_boa, ano):
        if valor < limite:
            atual += 1
        else:
            tamanhos.append(atual)
            atual = 0
    tamanhos.append(atual)
    return tamanhos, atual > 0


def dias_sem_planta_verde(serie_boa, ano, limite):
    """Os dias seguidos abaixo do limite, de junho a dezembro do ano: a maior sequência x 16."""
    return max(_sequencias(serie_boa, ano, limite)[0]) * DIAS_POR_MEDIDA


def situacao_do_ano(datas_boas, ano, fim_da_serie):
    """Diz se o ano conta: ("completo", ""), ("em_andamento", motivo) ou ("de_fora", motivo).

    datas_boas: as datas das medidas boas do ponto. fim_da_serie: a última data do arquivo.
    """
    inicio, fim = date(ano, MES_INICIAL, 1), date(ano, 12, 31)
    boas = sorted(d for d in datas_boas if inicio <= d <= fim)
    if not boas:
        return "de_fora", "nenhuma medida boa de junho a dezembro"
    em_andamento = fim_da_serie.year == ano and (fim - fim_da_serie).days > BURACO_MAXIMO_DIAS
    marcos = [inicio] + boas + [fim_da_serie if em_andamento else fim]
    for antes, depois in zip(marcos, marcos[1:]):
        dias = (depois - antes).days
        if dias > BURACO_MAXIMO_DIAS:
            return "de_fora", "buraco de %d dias sem medida boa, de %s a %s" % (dias, antes, depois)
    if em_andamento:
        return "em_andamento", ("a série termina em %s: faltam %d dias até 31 de dezembro"
                                % (fim_da_serie, (fim - fim_da_serie).days))
    return "completo", ""


def _inteiro_se_der(numero):
    return int(numero) if float(numero).is_integer() else numero


def resumo(fracao=FRACAO_PADRAO, pasta=None, lugar=LUGAR_PADRAO):
    """O resumo do verde: os dias por ponto e ano, os limites, a mediana, o menor e o maior."""
    pontos = ler_pontos(pasta)
    limites, fichas, dias, de_fora, parciais, abertos = {}, {}, {}, {}, {}, []
    ano_parcial, ultima_parcial, motivo_parcial = None, None, ""
    for nome, ponto in pontos.items():
        valores = [v for _, v in ponto["boas"]]
        limite = limites[nome] = limite_sem_planta_verde(valores, fracao)
        fichas[nome] = {"lat": ponto["lat"], "lon": ponto["lon"], "medidas": ponto["medidas"],
                        "medidas_boas": len(valores), "minimo": min(valores), "maximo": max(valores),
                        "limite": limite}
        dias[nome] = {}
        datas = [d for d, _ in ponto["boas"]]
        for ano in range(datas[0].year, ponto["ultima_data"].year + 1):
            situacao, motivo = situacao_do_ano(datas, ano, ponto["ultima_data"])
            if situacao == "completo":
                dias[nome][str(ano)] = dias_sem_planta_verde(ponto["boas"], ano, limite)
            elif situacao == "em_andamento":
                tamanhos, aberta = _sequencias(ponto["boas"], ano, limite)
                parciais[nome] = max(tamanhos) * DIAS_POR_MEDIDA
                if aberta:
                    abertos.append(nome)
                ano_parcial, ultima_parcial, motivo_parcial = ano, ponto["ultima_data"], motivo
            else:
                de_fora.setdefault((ano, motivo), []).append(nome)
    todos = [d for anos in dias.values() for d in anos.values()]
    andamento = None
    if parciais:
        andamento = {
            "ano": ano_parcial, "ultima_medida": ultima_parcial.isoformat(), "motivo": motivo_parcial,
            "dias_ate_a_ultima_medida": parciais,
            "ainda_sem_planta_verde_na_ultima_medida": abertos,
            "aviso": "Conta parcial, fora da mediana. Onde a última medida ainda está sem planta verde, "
                     "o número é 'pelo menos': a sequência não fechou.",
        }
    return {
        "o_que_e": "Dias seguidos sem planta verde, de junho em diante, vistos pelo satélite em cada ponto.",
        "fonte": fonte(pasta),
        "aviso": AVISO,
        "aviso_dos_pontos": aviso_dos_pontos(lugar),
        "regra": {
            "fracao": fracao,
            "etiqueta_da_fracao": ETIQUETA_DA_FRACAO,
            "limite": "mínimo + fração x (máximo - mínimo) da série boa de cada ponto",
            "dias_por_medida": DIAS_POR_MEDIDA,
            "mes_inicial": MES_INICIAL,
            "buraco_maximo_dias": BURACO_MAXIMO_DIAS,
            "ano_completo": "de 1 de junho a 31 de dezembro, sem buraco de mais de %d dias sem medida boa"
                            % BURACO_MAXIMO_DIAS,
        },
        "limites": limites,
        "pontos": fichas,
        "dias_sem_planta_verde": dias,
        "quantos": len(todos),
        "mediana": _inteiro_se_der(statistics.median(todos)) if todos else None,
        "menor": min(todos) if todos else None,
        "maior": max(todos) if todos else None,
        "anos_de_fora": [{"ano": ano, "pontos": nomes, "motivo": motivo}
                         for (ano, motivo), nomes in sorted(de_fora.items())],
        "ano_em_andamento": andamento,
    }


def _br(numero):
    """Número do jeito brasileiro: 97.5 -> "97,5"; 96 -> "96"."""
    return str(_inteiro_se_der(numero)).replace(".", ",")


def comparar_com_calendario(dias_pelo_calendario, resumo_ndvi=None):
    """Compara os "dias sem planta pelo calendário" com os dias sem planta verde do satélite.

    A diferença é calendário menos satélite (a mediana): positiva, o calendário diz mais dias.
    Até 16 dias (uma medida do satélite) de diferença, os dois números batem.
    """
    n = dias_pelo_calendario
    if isinstance(n, bool) or not isinstance(n, (int, float)) or n < 0:
        raise ValueError("Os dias sem planta pelo calendário têm de ser um número de zero para cima, e veio %r." % (n,))
    r = resumo_ndvi if resumo_ndvi is not None else resumo()
    saida = {"dias_pelo_calendario": n, "dias_pelo_satelite": r["mediana"], "menor": r["menor"],
             "maior": r["maior"], "quantos": r["quantos"], "dias_por_medida": DIAS_POR_MEDIDA,
             "diferenca": None, "leitura": "sem_medida", "aviso": AVISO,
             "nota": "O satélite mede o verde; o calendário, a planta no chão. Milho já seco antes da colheita "
                     "e soja recém-nascida aparecem como 'sem planta verde': o satélite pode contar mais dias."}
    if not r["quantos"]:
        saida["frase"] = ("Pelo calendário, a terra fica %s dias sem planta. O satélite não tem nenhum ano "
                          "completo para comparar." % _br(n))
        return saida
    diferenca = saida["diferenca"] = _inteiro_se_der(round(n - r["mediana"], 1))
    if abs(diferenca) <= DIAS_POR_MEDIDA:
        saida["leitura"] = "bate"
        fecho = "Os dois números batem: a diferença cabe em uma medida do satélite (%d dias)." % DIAS_POR_MEDIDA
    elif r["menor"] <= n <= r["maior"]:
        saida["leitura"] = "dentro_da_faixa"
        fecho = "O número do calendário é diferente da mediana, mas cabe na faixa que o satélite viu."
    else:
        saida["leitura"] = "fora_da_faixa"
        fecho = "O número do calendário fica fora da faixa que o satélite viu: vale conferir o calendário."
    lado = "a mais" if diferenca > 0 else "a menos"
    quanto = ("não há diferença" if diferenca == 0
              else "a diferença é de %s dias %s no calendário" % (_br(abs(diferenca)), lado))
    saida["frase"] = (
        "Pelo calendário, a terra fica %s dias sem planta. O satélite viu %s dias seguidos sem planta verde "
        "(a mediana de %s medidas, que vão de %s a %s dias): %s. %s"
        % (_br(n), _br(r["mediana"]), _br(r["quantos"]), _br(r["menor"]), _br(r["maior"]), quanto, fecho))
    return saida


if __name__ == "__main__":
    print(json.dumps(resumo(), ensure_ascii=False, indent=2))
