# Gerado com IA (Claude)
"""Os parâmetros da conta, cada um com o valor, a fonte (o link), o trecho e a etiqueta "publicado" ou "hipótese".

"publicado" = o valor (ou a fórmula) está escrito na fonte do link. "hipótese" = escolha desta versão, ou valor de
tabela usado fora do lugar para o qual foi medido: precisa do olho de um agrônomo. Todo valor é trocável: quem chama
pode copiar o dicionário de `carregar()` e mudar o que quiser.

Se existir `data/orbita/parametros-com-fonte.json` (os parâmetros conferidos na fonte por outra frente do time), os
valores, os links e as etiquetas de lá entram no lugar dos daqui (ver `_adotar`).
"""
import copy
import json
from pathlib import Path

ARQUIVO_CONFERIDO = Path(__file__).resolve().parents[2] / "data" / "orbita" / "parametros-com-fonte.json"
FAO6 = "https://www.fao.org/4/X0490E/x0490e0b.htm"  # cap. 6: Tabelas 11 (fases) e 12 (Kc)
FAO7 = "https://www.fao.org/4/X0490E/x0490e0c.htm"  # cap. 7: Tabela 19 (a terra) e a evaporação do solo (eq. 73, 74)
FAO8 = "https://www.fao.org/4/X0490E/x0490e0e.htm"  # cap. 8: Tabela 22 (raízes e p) e o balanço (eq. 82 a 88)
PUBLICADO, HIPOTESE = "publicado", "hipótese"


def _p(valor, fonte, trecho, etiqueta=HIPOTESE):
    return {"valor": valor, "fonte": fonte, "trecho": trecho, "etiqueta": etiqueta}


PADRAO = {
    "culturas": {
        "soja": {
            "plantio_mes_dia": _p("10-15", "", "Escolha desta versão (15 de outubro), sem fonte conferida: falta a "
                                  "janela oficial de plantio em Goiás (Conab, ZARC)."),
            "fases_dias": _p([15, 25, 50, 20], FAO6, "FAO-56, Tabela 11, soja: 15/15/40/15 (85 dias, trópicos) e "
                             "20/30-35/60/25 (140 dias, centro dos EUA). Os 110 dias em 15/25/50/20 são escolha desta "
                             "versão, entre as duas linhas."),
            "kc_ini": _p(0.4, FAO6, "FAO-56, Tabela 12, leguminosas: Kc ini 0.4."),
            "kc_meio": _p(1.15, FAO6, "FAO-56, Tabela 12, Soybeans: Kc mid 1.15."),
            "kc_fim": _p(0.5, FAO6, "FAO-56, Tabela 12, Soybeans: Kc end 0.50."),
            "p": _p(0.5, FAO8, "FAO-56, Tabela 22, Soybeans: p 0.50 (a parte da água que a planta tira sem sede)."),
        },
        "milho_2a_safra": {
            "plantio_mes_dia": _p("02-10", "", "Escolha desta versão (10 de fevereiro, logo depois de colher a soja), "
                                  "sem fonte conferida."),
            "fases_dias": _p([20, 35, 40, 30], FAO6, "FAO-56, Tabela 11, Maize (grain): 20/35/40/30 (125 dias, Nigéria "
                             "úmida e Índia). Usar essa linha em Goiás é escolha desta versão."),
            "kc_ini": _p(0.3, FAO6, "FAO-56, Tabela 12, cereais: Kc ini 0.3."),
            "kc_meio": _p(1.2, FAO6, "FAO-56, Tabela 12, Maize, Field (grain): Kc mid 1.20."),
            "kc_fim": _p(0.35, FAO6, "FAO-56, Tabela 12, Maize, Field (grain): Kc end 0.60-0.35; 0.35 é o do grão "
                         "que seca no campo (nota 11 da tabela)."),
            "p": _p(0.55, FAO8, "FAO-56, Tabela 22, Maize, Field (grain): p 0.55."),
        },
        "braquiaria_apos_milho": {
            "kc": _p(0.75, FAO6, "FAO-56, Tabela 12, Grazing Pasture, Extensive Grazing: Kc mid 0.75. Usar o Kc de "
                     "pastagem para a braquiária depois do milho é hipótese."),
            "p": _p(0.6, FAO8, "FAO-56, Tabela 22, Grazing Pasture: p 0.60."),
            "dessecacao_dias_antes_da_soja": _p(20, "", "Escolha desta versão: o capim é seco (dessecado) 20 dias "
                                                "antes de plantar a soja. Sem fonte conferida."),
        },
        "solo_nu": {
            "kc": _p(1.0, FAO7, "Hipótese: com a camada de cima molhada, a terra sem planta evapora perto da ETo "
                     "(FAO-56, cap. 7: o Kc do solo molhado chega a 1,0-1,2). O freio vem da camada de cima "
                     "secando (eq. 74), não de um Kc baixo. A palha do milho, que reduz isso, não entra."),
        },
    },
    "terra": {
        "pouca": {
            "classe": _p("areia franca (loamy sand)", FAO7, "FAO-56, Tabela 19. Ligar 'pouca' a esta classe é escolha."),
            "agua_mm_por_m": _p(90.0, FAO7, "FAO-56, Tabela 19, Loamy sand: 0.06-0.12 m³/m³ (60 a 120 mm por metro "
                                "de terra); 90 é o meio da faixa."),
            "tew_mm": _p(11.5, FAO7, "FAO-56, Tabela 19, Loamy sand: TEW 9-14 mm (o meio da faixa)."),
            "rew_mm": _p(6.0, FAO7, "FAO-56, Tabela 19, Loamy sand: REW 4-8 mm (o meio da faixa)."),
        },
        "media": {
            "classe": _p("franco-arenosa (sandy loam)", FAO7, "FAO-56, Tabela 19. Ligar 'media' a esta classe é escolha."),
            "agua_mm_por_m": _p(130.0, FAO7, "FAO-56, Tabela 19, Sandy loam: 0.11-0.15 m³/m³ (110 a 150 mm por "
                                "metro de terra); 130 é o meio da faixa."),
            "tew_mm": _p(17.5, FAO7, "FAO-56, Tabela 19, Sandy loam: TEW 15-20 mm (o meio da faixa)."),
            "rew_mm": _p(8.0, FAO7, "FAO-56, Tabela 19, Sandy loam: REW 6-10 mm (o meio da faixa)."),
        },
        "muita": {
            "classe": _p("argila (clay)", FAO7, "FAO-56, Tabela 19. Ligar 'muita' a esta classe é escolha."),
            "agua_mm_por_m": _p(160.0, FAO7, "FAO-56, Tabela 19, Clay: 0.12-0.20 m³/m³ (120 a 200 mm por metro de "
                                "terra); 160 é o meio da faixa."),
            "tew_mm": _p(25.5, FAO7, "FAO-56, Tabela 19, Clay: TEW 22-29 mm (o meio da faixa)."),
            "rew_mm": _p(10.0, FAO7, "FAO-56, Tabela 19, Clay: REW 8-12 mm (o meio da faixa)."),
        },
    },
    "raizes_m": _p(1.0, FAO8, "FAO-56, Tabela 22: soja 0.6-1.3 m, milho 1.0-1.7 m, pastagem 0.5-1.5 m. Usar 1,0 m "
                   "para todas, desde o plantio, é escolha desta versão (cabe nas três faixas)."),
    "ajustar_p_pela_demanda": _p(True, FAO8, "FAO-56, cap. 8: 'p = pTable 22 + 0.04 (5 - ETc)', limitado entre 0.1 e "
                                 "0.8, com a ETc em mm/dia.", PUBLICADO),
    "regras": {
        "sede_da_2a_safra_pct": _p(20, "", "Escolha fixada antes de ver o resultado: 'safra com sede' = falta "
                                   "relativa de água do milho de 20% ou mais. O motor mostra também com 10% e 30%."),
        "empate_mm": _p(5.0, "", "Escolha fixada antes de ver o resultado: diferença de falta de água menor que 5 mm "
                        "entre as rotações conta como empate."),
    },
    "ndvi": {
        "fracao_da_amplitude": _p(0.2, "", "'Sem planta verde' = NDVI abaixo de mínimo + 20% x (máximo - mínimo). O "
                                  "limite de 20% da amplitude é usado com o TIMESAT (Jönsson e Eklundh); não "
                                  "confirmado na fonte por esta frente."),
    },
}


def eh_folha(coisa):
    return isinstance(coisa, dict) and "valor" in coisa and "etiqueta" in coisa


def folhas(par, prefixo=""):
    """A lista (caminho, parâmetro) de todos os parâmetros, em ordem."""
    saida = []
    for chave, coisa in par.items():
        caminho = f"{prefixo}.{chave}" if prefixo else chave
        if eh_folha(coisa):
            saida.append((caminho, coisa))
        elif isinstance(coisa, dict):
            saida.extend(folhas(coisa, caminho))
    return saida


def _adotar(base, conferido):
    """Troca, na base, cada parâmetro que o arquivo conferido traz no mesmo caminho. Devolve os caminhos trocados."""
    trocados = []
    for chave, coisa in conferido.items():
        if chave not in base or not isinstance(coisa, dict):
            continue
        if eh_folha(base[chave]) and eh_folha(coisa):
            if type(coisa["valor"]) is type(base[chave]["valor"]) or (
                    isinstance(coisa["valor"], (int, float)) and not isinstance(coisa["valor"], bool)
                    and isinstance(base[chave]["valor"], (int, float)) and not isinstance(base[chave]["valor"], bool)):
                base[chave] = {"valor": coisa["valor"], "fonte": coisa.get("fonte") or "",
                               "trecho": coisa.get("trecho") or "", "etiqueta": coisa["etiqueta"]}
                trocados.append(chave)
        elif isinstance(base[chave], dict) and not eh_folha(base[chave]) and not eh_folha(coisa):
            trocados.extend(f"{chave}.{c}" for c in _adotar(base[chave], coisa))
    return trocados


def carregar(arquivo_conferido=ARQUIVO_CONFERIDO):
    """Os parâmetros em uso: os desta pasta, com os do arquivo conferido por cima quando ele existe."""
    par = copy.deepcopy(PADRAO)
    arquivo = Path(arquivo_conferido)
    if arquivo.exists():
        with open(arquivo, encoding="utf-8") as f:
            _adotar(par, json.load(f))
    return par


def valor(par, *caminho):
    coisa = par
    for chave in caminho:
        coisa = coisa[chave]
    return coisa["valor"]


def hipoteses(par):
    """Os parâmetros que ainda são hipótese: (caminho, valor, trecho)."""
    return [(c, p["valor"], p["trecho"]) for c, p in folhas(par) if p["etiqueta"] != PUBLICADO]
