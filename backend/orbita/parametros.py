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
FAO10 = "https://www.fao.org/4/X0490E/x0490e0g.htm"  # cap. 10: a palha (surface mulches) e o consórcio (intercropping)
IMPACTO_EMBRAPA = "https://bs.sede.embrapa.br/2019/relatorios/agropecuariaoeste_consorcio.pdf"
DOURADOS_EMBRAPA = "https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/909678/1/211Produtividade.pdf"
ZARC_CONSORCIO = ("https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola"
                  "-de-risco-climatico/portarias/2022-2023/goias-go/port-no-345-cons-milho-braquiaria-2a-safra-go-ret.pdf")
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
            "raiz_m": _p(1.0, FAO8, "FAO-56, Tabela 22, Soybeans: raízes de 0.6 a 1.3 m; 1,0 m é escolha."),
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
            "raiz_m": _p(1.0, FAO8, "FAO-56, Tabela 22, Maize, Field (grain): raízes de 1.0 a 1.7 m; 1,0 m é escolha."),
        },
        "braquiaria_apos_milho": {
            "kc": _p(0.75, FAO6, "FAO-56, Tabela 12, Grazing Pasture, Extensive Grazing: Kc mid 0.75. Usar o Kc de "
                     "pastagem para a braquiária depois do milho é hipótese."),
            "p": _p(0.6, FAO8, "FAO-56, Tabela 22, Grazing Pasture: p 0.60."),
            "raiz_m": _p(1.0, FAO8, "FAO-56, Tabela 22, Grazing Pasture: raízes de 0.5 a 1.5 m; 1,0 m é escolha."),
            "dessecacao_dias_antes_da_soja": _p(20, "", "Escolha desta versão: o capim é seco (dessecado) 20 dias "
                                                "antes de plantar a soja. Sem fonte conferida."),
        },
        "solo_nu": {
            "kc": _p(1.0, FAO7, "Hipótese: o coeficiente da terra sem planta com a camada de cima molhada, perto "
                     "da ETo (FAO-56, cap. 7, eq. 72: o teto, Kc max, é 1,2). O freio vem da camada de cima "
                     "secando (Kr, eq. 74), não de um Kc baixo. O valor de solo seco conferido na fonte (kc_seco, "
                     "0,15 a 0,20) fica guardado e não entra na conta: junto com o Kr, frearia a evaporação duas "
                     "vezes. A palha, que reduz a evaporação, entra à parte (ver 'palha')."),
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
    "palha": {
        "reducao_por_cobertura": _p(0.5, FAO10, "FAO-56, cap. 10, Effects of surface mulches, Organic mulches: 'A "
                                    "general rule when applying Kc from Table 12 is to reduce the amount of soil "
                                    "water evaporation by about 5% for each 10% of soil surface that is effectively "
                                    "covered by an organic mulch.' E: 'In the case of Kc ini, which represents mostly "
                                    "evaporation from soil, one would reduce Kc ini by about 25% in this situation' "
                                    "(com 50% da terra coberta). 0,5 = 5% a cada 10%.", PUBLICADO),
        "cobertura_do_milho_solteiro": _p(0.6, IMPACTO_EMBRAPA, "Hipótese, com a faixa de 0,4 a 0,8: a parte da terra "
                                          "coberta pela palha do milho safrinha solteiro. Não achei a porcentagem "
                                          "de cobertura medida em página aberta. A Embrapa diz só que é baixa: 'Uma "
                                          "das fragilidades do sistema de sucessão soja/milho safrinha consiste nos "
                                          "baixos índices de cobertura do solo, principalmente durante os meses de "
                                          "agosto a outubro, entre a colheita do milho e a semeadura da soja' "
                                          "(Embrapa Agropecuária Oeste, Relatório de avaliação dos impactos: "
                                          "Consórcio milho safrinha com Brachiaria ruziziensis, 2019)."),
        "cobertura_do_milho_com_braquiaria": _p(0.9, IMPACTO_EMBRAPA, "Hipótese, com a faixa de 0,8 a 1,0: a parte "
                                                "da terra coberta pela palha do milho mais a do capim. As fontes dão "
                                                "massa de palha, não a porcentagem de terra coberta: 'É possível "
                                                "produzir até 12 toneladas de palha (milho safrinha + braquiária)' "
                                                "(o mesmo relatório da Embrapa, 2019); em Dourados (MS), em 2010, 'o "
                                                "rendimento de massa seca de braquiária (2.759 kg ha-1)' somou-se à "
                                                "do milho (Fonseca, Ceccon e outros, Embrapa: " + DOURADOS_EMBRAPA
                                                + "). Os dois números de cobertura são escolha desta versão."),
    },
    "disputa_com_o_milho": {
        "sem_disputa": _p(0.0, ZARC_CONSORCIO, "A ponta de baixo da faixa (o que a conta fazia antes): o capim "
                          "debaixo do milho não aumenta o pedido de água. ZARC do milho com braquiária em Goiás "
                          "(Portaria 345, de 2022): 'a braquiária apresenta desenvolvimento lento até a colheita "
                          "do milho'."),
        "meio": _p(0.04, "", "Hipótese: o meio da faixa. Enquanto o milho e o capim crescem juntos, o conjunto pede 4% "
                   "a mais de água que o milho sozinho. Metade da ponta de cima; não há medida."),
        "alta": _p(0.08, FAO10, "Hipótese: a ponta de cima da faixa (8% a mais). Não achei medida do consumo de água "
                   "do consórcio. A Embrapa cita a disputa sem número: 'competição com a braquiária por água e "
                   "nutrientes, que provavelmente ocorre no sistema consorciado' (Dourados, MS: " + DOURADOS_EMBRAPA
                   + ") e 'pode ocorrer influencia no rendimento final de grãos do milho pela competição entre as "
                   "culturas, principalmente após o florescimento' (relatório de 2019: " + IMPACTO_EMBRAPA + "). O "
                   "teto vem do FAO-56: no consórcio, 'the Kc may increase as the density of the combined vegetation "
                   "increases, proportional to the increase in LAI', 'with maximum Kc constrained by either Kc max "
                   "(Equation 72) or by Kcb full' (cap. 10), e 'Kc max ranges from about 1.05 to 1.30 when using the "
                   "grass reference ETo' (cap. 7: " + FAO7 + "). 1,20 (o Kc do milho no meio do ciclo) x 1,08 = 1,30."),
    },
    "ajustar_p_pela_demanda": _p(True, FAO8, "FAO-56, cap. 8: 'p = pTable 22 + 0.04 (5 - ETc)', limitado entre 0.1 e "
                                 "0.8, com a ETc em mm/dia.", PUBLICADO),
    "regras": {
        "sede_da_2a_safra_pct": _p(20, "", "Escolha fixada antes de ver o resultado: 'safra com sede' = falta "
                                   "relativa de água do milho de 20% ou mais. O motor mostra também com 10% e 30%."),
        "quebra_fracao_da_mediana": _p(0.8, "", "Decisão do dono do projeto (2026-11-14): safra de quebra = rendimento "
                                       "do milho de 2ª safra no IBGE abaixo de 80% da mediana das 10 safras. O "
                                       "nível de 'sede forte' é a menor falta do milho entre as safras de quebra "
                                       "(rotação de hoje, terra média, chuva padrão): sai do IBGE e da conta, não "
                                       "está escrito à mão. O limite de 80% é escolha."),
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


def _folha_de(conferido, caminho):
    coisa = conferido
    for chave in caminho:
        if not isinstance(coisa, dict) or chave not in coisa:
            return None
        coisa = coisa[chave]
    return coisa if eh_folha(coisa) else None


def _adotar(par, conferido):
    """Põe em `par` os valores, os links e as etiquetas do arquivo conferido. Devolve os caminhos adotados.

    O arquivo conferido usa outros nomes em três lugares: `kc_med` (aqui `kc_meio`), `plantio_mm_dd` (aqui
    `plantio_mes_dia`) e as fases em quatro chaves (aqui a lista `fases_dias`).
    """
    adotados = []

    def por(destino, folha):
        alvo = par
        for chave in destino[:-1]:
            alvo = alvo[chave]
        etiqueta = folha["etiqueta"] if folha["etiqueta"] in (PUBLICADO, HIPOTESE) else HIPOTESE
        if etiqueta == PUBLICADO and not str(folha.get("fonte") or "").startswith("http"):
            etiqueta = HIPOTESE
        alvo[destino[-1]] = {"valor": folha["valor"], "fonte": folha.get("fonte") or "",
                             "trecho": folha.get("trecho") or "(sem trecho no arquivo conferido)", "etiqueta": etiqueta}
        adotados.append(".".join(destino))

    for cultura in ("soja", "milho_2a_safra"):
        for la, ca in (("kc_ini", "kc_ini"), ("kc_med", "kc_meio"), ("kc_fim", "kc_fim"), ("raiz_m", "raiz_m"),
                       ("p", "p"), ("plantio_mm_dd", "plantio_mes_dia")):
            folha = _folha_de(conferido, ("culturas", cultura, la))
            if folha:
                por(("culturas", cultura, ca), folha)
        fases = [_folha_de(conferido, ("culturas", cultura, chave)) for chave in
                 ("fase_inicial_dias", "fase_crescimento_dias", "fase_media_dias", "fase_final_dias")]
        if all(fases):
            por(("culturas", cultura, "fases_dias"), {
                "valor": [f["valor"] for f in fases], "fonte": fases[0].get("fonte"),
                "trecho": " / ".join(dict.fromkeys(str(f.get("trecho") or "") for f in fases)),
                "etiqueta": PUBLICADO if all(f["etiqueta"] == PUBLICADO for f in fases) else HIPOTESE})
    for chave in ("kc", "raiz_m", "p", "dessecacao_dias_antes_da_soja"):
        folha = _folha_de(conferido, ("culturas", "braquiaria_apos_milho", chave))
        if folha:
            por(("culturas", "braquiaria_apos_milho", chave), folha)
    seco = _folha_de(conferido, ("culturas", "solo_nu", "kc"))
    if seco:   # no arquivo conferido, este é o Kc do solo SECO (Kc min): guardado à parte, fora da conta
        por(("culturas", "solo_nu", "kc_seco"), seco)
    for caminho in [("ndvi", "fracao_da_amplitude")] + [
            ("terra", terra, "agua_mm_por_m") for terra in ("pouca", "media", "muita")]:
        folha = _folha_de(conferido, caminho)
        if folha:
            por(caminho, folha)
    return adotados


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
