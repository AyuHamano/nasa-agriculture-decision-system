# Os parâmetros da conta de água, cada um com a fonte (frente C · 2026-11-14)

> Gerado com IA (Claude), por pesquisa na web em 2026-11-14. O mesmo conteúdo, para o programa ler, está em `parametros-com-fonte.json`.
> **Etiquetas:** "publicado" = a página foi aberta e o valor lido nela; "hipótese" = não li o valor numa página aberta, ou o número é de outra coisa e foi aplicado aqui por escolha nossa.
> **Placar:** 26 valores "publicado" e 9 "hipótese".

## De onde veio

- **FAO-56** (o manual da FAO para a água das lavouras): os capítulos 3, 4, 6, 7, 8 e 11, abertos em https://www.fao.org/4/X0490E/x0490e00.htm. Kc é o quanto a planta pede em relação à evaporação de referência; p é a fração da água da terra que a planta tira sem passar sede.
- **ZARC** (o zoneamento de risco do Ministério da Agricultura com a Embrapa): a portaria da soja em Goiás, safra 2025/2026 (nº 368, de 24/06/2025), e a do milho consorciado com braquiária, 2ª safra, em Goiás, safra 2022/2023 (nº 345, de 26/09/2022), que traz a linha de Rio Verde.
- **NDVI:** Klisch e Atzberger (2014), que descrevem o limite de 20% da amplitude usado com o TIMESAT.

## As escolhas que são nossas (e não da fonte)

- As fases da soja: a linha dos trópicos do FAO-56 tem 85 dias; foi esticada para os 115 dias do ZARC (20/20/55/20).
- A data de plantio da soja (15/out): não li a janela de Rio Verde; o milho (10/fev) sai da portaria.
- A raiz: fiquei com a do ZARC (60 cm na soja, 50 cm no milho), bem mais rasa que a do FAO-56 (até 1,3 m e 1,7 m). Com a raiz do FAO-56 a terra guarda mais água e a falta diminui: vale rodar as duas.
- A braquiária: os números são de pasto (FAO-56), não de braquiária medida. A dessecação 30 dias antes da soja é costume de campo, sem página lida.
- A terra sem planta: Kc de 0,20 é o de solo nu e seco; em dia de chuva a evaporação é maior.

### Soja

| parâmetro | valor | etiqueta | trecho da fonte | observação |
|---|---|---|---|---|
| kc_ini | 0.4 | publicado | Tabela 12: "e. Legumes (Leguminosae) / 0.4 / 1.15 / 0.55"; a linha "Soybeans" deixa o Kc ini em branco e vale o do grupo ([link](https://www.fao.org/4/X0490E/x0490e0b.htm)) |  |
| kc_med | 1.15 | publicado | Tabela 12: "Soybeans / / 1.15 / 0.50 / 0.5-1.0" ([link](https://www.fao.org/4/X0490E/x0490e0b.htm)) |  |
| kc_fim | 0.5 | publicado | Tabela 12: "Soybeans / / 1.15 / 0.50 / 0.5-1.0" ([link](https://www.fao.org/4/X0490E/x0490e0b.htm)) |  |
| fase_inicial_dias | 20 | hipótese | FAO-56, Tabela 11, Soybeans: "15 / 15 / 40 / 15 / 85 / Dec / Tropics"; "20 / 30/35 / 60 / 25 / 140 / May / Central USA"; "20 / 25 / 75 / 30 / 150 / June / Japan" ([link](https://www.fao.org/4/X0490E/x0490e0b.htm)) | A linha dos trópicos (85 dias) esticada na mesma proporção para o ciclo de 115 dias do ZARC de Goiás: 20/20/55/20. A proporção é escolha nossa; o FAO-56 manda usar observação local. |
| fase_crescimento_dias | 20 | hipótese | FAO-56, Tabela 11, Soybeans: "15 / 15 / 40 / 15 / 85 / Dec / Tropics"; "20 / 30/35 / 60 / 25 / 140 / May / Central USA"; "20 / 25 / 75 / 30 / 150 / June / Japan" ([link](https://www.fao.org/4/X0490E/x0490e0b.htm)) | A linha dos trópicos (85 dias) esticada na mesma proporção para o ciclo de 115 dias do ZARC de Goiás: 20/20/55/20. A proporção é escolha nossa; o FAO-56 manda usar observação local. |
| fase_media_dias | 55 | hipótese | FAO-56, Tabela 11, Soybeans: "15 / 15 / 40 / 15 / 85 / Dec / Tropics"; "20 / 30/35 / 60 / 25 / 140 / May / Central USA"; "20 / 25 / 75 / 30 / 150 / June / Japan" ([link](https://www.fao.org/4/X0490E/x0490e0b.htm)) | A linha dos trópicos (85 dias) esticada na mesma proporção para o ciclo de 115 dias do ZARC de Goiás: 20/20/55/20. A proporção é escolha nossa; o FAO-56 manda usar observação local. |
| fase_final_dias | 20 | hipótese | FAO-56, Tabela 11, Soybeans: "15 / 15 / 40 / 15 / 85 / Dec / Tropics"; "20 / 30/35 / 60 / 25 / 140 / May / Central USA"; "20 / 25 / 75 / 30 / 150 / June / Japan" ([link](https://www.fao.org/4/X0490E/x0490e0b.htm)) | A linha dos trópicos (85 dias) esticada na mesma proporção para o ciclo de 115 dias do ZARC de Goiás: 20/20/55/20. A proporção é escolha nossa; o FAO-56 manda usar observação local. |
| raiz_m | 0.6 | publicado | "uma profundidade efetiva média do sistema radicular (Ze) de 60 cm" ([link](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/portarias/2025-2026/goias-go/PORTN368SOJAGO.ret2.pdf)) | FAO-56, Tabela 22: "Soybeans / 0.6-1.3 / 0.50" (o 0,6 é também o piso do FAO-56). |
| p | 0.5 | publicado | Tabela 22: "Soybeans / 0.6-1.3 / 0.50" ([link](https://www.fao.org/4/X0490E/x0490e0e.htm)) | Vale para ETc perto de 5 mm/dia; ajuste opcional do FAO-56: "p = p table 22 + 0.04 (5 - ETc)", entre 0,1 e 0,8. |
| plantio_mm_dd | 10-15 | hipótese | "Art. 2º ... devem ser observadas as determinações relativas ao vazio sanitário e ao calendário de plantio"; os períodos por município "estão disponibilizados no Painel de Indicação de Riscos" ([link](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/portarias/2025-2026/goias-go/PORTN368SOJAGO.ret2.pdf)) | A janela de Rio Verde não está no PDF (fica no painel do ministério, que não abri). 15/out é a data de costume do início firme das chuvas no sudoeste goiano e fecha com o milho em 10/fev (15/out + 115 dias = 7/fev). A conferir no painel do ZARC ou no calendário da Conab. |
| ciclo_dias | 115 | publicado | "foram analisados os comportamentos das cultivares dos ciclos de 100, 115 e 130 dias; os quais foram divididos em 4 fases fenológicas" ([link](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/portarias/2025-2026/goias-go/PORTN368SOJAGO.ret2.pdf)) | O ciclo do meio dos três que o ZARC simula; a escolha do meio é nossa. |

### Milho de segunda safra

| parâmetro | valor | etiqueta | trecho da fonte | observação |
|---|---|---|---|---|
| kc_ini | 0.3 | publicado | Tabela 12: "i. Cereals / 0.3 / 1.15 / 0.4"; a linha do milho deixa o Kc ini em branco e vale o do grupo ([link](https://www.fao.org/4/X0490E/x0490e0b.htm)) |  |
| kc_med | 1.2 | publicado | Tabela 12: "Maize, Field (grain) (field corn) / / 1.20 / 0.60-0.35 / 2" ([link](https://www.fao.org/4/X0490E/x0490e0b.htm)) |  |
| kc_fim | 0.35 | publicado | Tabela 12, nota 11: "The second Kc end value is for harvest after complete field drying of the grain (to about 18% moisture, wet mass basis)" ([link](https://www.fao.org/4/X0490E/x0490e0b.htm)) | A faixa é 0,60 a 0,35; o 0,35 é o de grão colhido seco no campo, como na 2ª safra. |
| fase_inicial_dias | 20 | publicado | FAO-56, Tabela 11, Maize (grain): "20 / 35 / 40 / 30 / 125 / June / Nigeria (humid)" ([link](https://www.fao.org/4/X0490E/x0490e0b.htm)) | Linha de clima úmido com 125 dias, que cabe no Grupo II do ZARC de Goiás (116 a 135 dias). Outras linhas da tabela: 25/40/45/30 = 140 (clima árido, dez/jan); 30/50/60/40 = 180 (África do Leste). |
| fase_crescimento_dias | 35 | publicado | FAO-56, Tabela 11, Maize (grain): "20 / 35 / 40 / 30 / 125 / June / Nigeria (humid)" ([link](https://www.fao.org/4/X0490E/x0490e0b.htm)) | Linha de clima úmido com 125 dias, que cabe no Grupo II do ZARC de Goiás (116 a 135 dias). Outras linhas da tabela: 25/40/45/30 = 140 (clima árido, dez/jan); 30/50/60/40 = 180 (África do Leste). |
| fase_media_dias | 40 | publicado | FAO-56, Tabela 11, Maize (grain): "20 / 35 / 40 / 30 / 125 / June / Nigeria (humid)" ([link](https://www.fao.org/4/X0490E/x0490e0b.htm)) | Linha de clima úmido com 125 dias, que cabe no Grupo II do ZARC de Goiás (116 a 135 dias). Outras linhas da tabela: 25/40/45/30 = 140 (clima árido, dez/jan); 30/50/60/40 = 180 (África do Leste). |
| fase_final_dias | 30 | publicado | FAO-56, Tabela 11, Maize (grain): "20 / 35 / 40 / 30 / 125 / June / Nigeria (humid)" ([link](https://www.fao.org/4/X0490E/x0490e0b.htm)) | Linha de clima úmido com 125 dias, que cabe no Grupo II do ZARC de Goiás (116 a 135 dias). Outras linhas da tabela: 25/40/45/30 = 140 (clima árido, dez/jan); 30/50/60/40 = 180 (África do Leste). |
| raiz_m | 0.5 | publicado | "e uma profundidade efetiva média do sistema radicular de 50 cm" ([link](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/portarias/2022-2023/goias-go/port-no-345-cons-milho-braquiaria-2a-safra-go-ret.pdf)) | É a raiz que o ZARC usa para o milho com braquiária em Goiás. FAO-56, Tabela 22: "Maize, Field (grain) (field corn) / 1.0-1.7 / 0.55" (bem mais fundo; serve para o teste de sensibilidade). |
| p | 0.55 | publicado | Tabela 22: "Maize, Field (grain) (field corn) / 1.0-1.7 / 0.55" ([link](https://www.fao.org/4/X0490E/x0490e0e.htm)) |  |
| plantio_mm_dd | 02-10 | publicado | Períodos de semeadura, Grupo I, risco de 20%: "Rio Verde 1a3 4 1a4 5 1a5 6" (solo 1: períodos 1 a 3; solo 2: 1 a 4; solo 3: 1 a 5); o período 4 vai de 1º a 10 de fevereiro ([link](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/portarias/2022-2023/goias-go/port-no-345-cons-milho-braquiaria-2a-safra-go-ret.pdf)) | 10/fev é o último dia da janela de risco 20% no solo médio (Grupo I); no solo argiloso vai até 20/fev; no arenoso, até 31/jan. No Grupo II: solo 1, períodos 1 a 2; solos 2 e 3, 1 a 3. É a portaria do milho consorciado com braquiária, safra 2022/2023. |
| ciclo_dias | 125 | publicado | "Grupo I (n ≤ 115 dias); Grupo II (116 dias ≤ n ≤ 135 dias)" ([link](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/portarias/2022-2023/goias-go/port-no-345-cons-milho-braquiaria-2a-safra-go-ret.pdf)) | 125 fica dentro do Grupo II e é o total da linha do FAO-56 usada nas fases (20+35+40+30). A colheita de fato vem depois, com o grão seco. |

### Braquiária depois do milho (capim que cobre a terra)

| parâmetro | valor | etiqueta | trecho da fonte | observação |
|---|---|---|---|---|
| kc | 0.75 | hipótese | Tabela 12: "Grazing Pasture ... - Extensive Grazing / 0.30 / 0.75 / 0.75 / 0.10"; "- Rotated Grazing / 0.40 / 0.85-1.05 / 0.85 / 0.15-0.30" ([link](https://www.fao.org/4/X0490E/x0490e0b.htm)) | O número é do FAO-56 para pasto; usar o de pasto extensivo na braquiária de cobertura é escolha nossa. Não achei Kc medido de braquiária em consórcio. Na seca o freio da sede (Ks) é que manda. |
| raiz_m | 1.0 | hipótese | Tabela 22: "Grazing Pasture ... - Extensive Grazing / 0.5-1.5 / 0.60" ([link](https://www.fao.org/4/X0490E/x0490e0e.htm)) | Meio da faixa do FAO-56 para pasto; o ZARC do consórcio usa 50 cm para o conjunto. |
| p | 0.6 | hipótese | Tabela 22: "Grazing Pasture ... - Extensive Grazing / 0.5-1.5 / 0.60" ([link](https://www.fao.org/4/X0490E/x0490e0e.htm)) | Valor de pasto aplicado à braquiária. |
| dessecacao_dias_antes_da_soja | 30 | hipótese | "proporcionando cobertura permanente do solo até a semeadura da safra de verão subsequente" ([link](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/portarias/2022-2023/goias-go/port-no-345-cons-milho-braquiaria-2a-safra-go-ret.pdf)) | Nenhuma página aberta dá o número de dias. 30 dias é o costume de campo (20 a 30). A Embrapa trata do tema em publicações que a busca listou e eu não abri (ex.: https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/982634/1/Cap4.pdf). |
| semeadura | no mesmo dia do milho | publicado | "No consórcio, deve ser feito plantio profundo da braquiária no mesmo dia da semeadura do milho" ([link](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/portarias/2022-2023/goias-go/port-no-345-cons-milho-braquiaria-2a-safra-go-ret.pdf)) |  |
| disputa_com_o_milho | cresce devagar até a colheita do milho; em alguns casos pede herbicida em subdose | publicado | "a braquiária apresenta desenvolvimento lento até a colheita do milho"; "em alguns casos, houve necessidade da aplicação de herbicida em subdoses para reduzir o crescimento da forrageira" ([link](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/portarias/2022-2023/goias-go/port-no-345-cons-milho-braquiaria-2a-safra-go-ret.pdf)) | A portaria não dá número de água disputada. Na conta: durante o milho, só o Kc do milho; depois da colheita, o Kc da braquiária. |

### Terra sem planta

| parâmetro | valor | etiqueta | trecho da fonte | observação |
|---|---|---|---|---|
| kc | 0.2 | publicado | "Kc min is the minimum crop coefficient for dry bare soil ... Kc min » 0.15 - 0.20 is recommended" ([link](https://www.fao.org/4/X0490E/x0490e0c.htm)) | Vale para solo nu e seco (a seca de Rio Verde). Cap. 6, Tabela 12, nota 18: "Kc end » 0.20 for bare, dry soil or dead ground cover". Cap. 11: "Kc for bare soil can be calculated as Kc = Kc ini" e, com chuva frequente, sobe: "Kc ini can vary between 0.1 and 1.15" (Figura 29, que é imagem; não li número nela). Usar 0,20 fixo subestima a evaporação nos dias de chuva: é limite a declarar. |

### A água que a terra segura (mm de água por metro de terra)

| parâmetro | valor | etiqueta | trecho da fonte | observação |
|---|---|---|---|---|
| pouca | 70 | publicado | "solos Tipo 1 (textura arenosa), Tipo 2 (textura média) e Tipo 3 (textura argilosa), com capacidade de armazenamento de 0,7mm/cm, 1,1mm/cm e 1,5mm/cm, respectivamente" ([link](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/portarias/2022-2023/goias-go/port-no-345-cons-milho-braquiaria-2a-safra-go-ret.pdf)) | 0,7 mm/cm = 70 mm por metro. |
| media | 110 | publicado | "capacidade de armazenamento de 0,7mm/cm, 1,1mm/cm e 1,5mm/cm, respectivamente" ([link](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/portarias/2022-2023/goias-go/port-no-345-cons-milho-braquiaria-2a-safra-go-ret.pdf)) | 1,1 mm/cm = 110 mm por metro. |
| muita | 150 | publicado | "capacidade de armazenamento de 0,7mm/cm, 1,1mm/cm e 1,5mm/cm, respectivamente" ([link](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/portarias/2022-2023/goias-go/port-no-345-cons-milho-braquiaria-2a-safra-go-ret.pdf)) | 1,5 mm/cm = 150 mm por metro. |

### A água da terra: as outras tabelas (faixas em mm por metro)

| parâmetro | valor | etiqueta | trecho da fonte | observação |
|---|---|---|---|---|
| zarc_6_classes_de_hoje | {"AD1": [34, 46], "AD2": [46, 61], "AD3": [61, 80], "AD4": [80, 106], "AD5": [106, 140], "AD6": [140, 184]} | publicado | "0,34 AD1 0,46 / 0,46 AD2 0,61 / 0,61 AD3 0,80 / 0,80 AD4 1,06 / 1,06 AD5 1,40 / 1,40 AD6 1,84" (mm cm-1); "capacidade de armazenamento de 24 mm, 32 mm, 42 mm, 55 mm, 72 mm e 95mm, respectivamente; e ... (Ze) de 60 cm" ([link](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/portarias/2025-2026/goias-go/PORTN368SOJAGO.ret2.pdf)) | Faixas em mm por metro (mm/cm x 100). É o que o ZARC da soja usa hoje (Instrução Normativa SPA/MAPA nº 1, de 21/06/2022). 70, 110 e 150 caem em AD3, AD5 e AD6. |
| fao56_tabela_19 | {"loamy_sand": [60, 120], "sandy_loam": [110, 150], "loam": [130, 180], "silt_loam": [130, 190], "silty_clay": [130, 190], "clay": [120, 200]} | publicado | Tabela 19, coluna (θFC - θWP), m3/m3: "Loamy sand ... 0.06 - 0.12"; "Sandy loam ... 0.11 - 0.15"; "Loam ... 0.13 - 0.18"; "Clay ... 0.12 - 0.20" ([link](https://www.fao.org/4/X0490E/x0490e0c.htm)) | Faixas em mm por metro (m3/m3 x 1000). Os três valores do ZARC caem dentro delas. |

### O limite do NDVI (o verde visto pelo satélite)

| parâmetro | valor | etiqueta | trecho da fonte | observação |
|---|---|---|---|---|
| fracao_da_amplitude | 0.2 | publicado | "when the NDVI increases 20% of the seasonal amplitude from the seasonal minimum" ([link](https://www.dgpf.de/pfg/2014/pfg2014_5_klisch.pdf)) | Lido em Klisch e Atzberger (2014), que descrevem o limite relativo usado com o TIMESAT e citam Jönsson e Eklundh. O artigo original do TIMESAT (Jönsson e Eklundh, 2004, Computers & Geosciences) não foi aberto; nele a fração é ajuste de quem usa, e 20% é o costume, não regra. |

### Exemplos resolvidos do FAO-56 (valores esperados para os testes)

| o que | entrada | esperado | trecho |
|---|---|---|---|
| Radiação no topo da atmosfera (Ra), Exemplo 8 (eq. 21 a 25) | {"latitude_graus": -20, "dia_do_ano": 246} | {"ra_mj_m2_dia": 32.2, "ra_mm_dia": 13.1, "dr": 0.985, "declinacao_rad": 0.12, "ws_rad": 1.527} | "Determine the extraterrestrial radiation (Ra) for 3 September at 20°S." ... "32.2 / MJ m-2 d-1" ... "0.408 (32.2) = / 13.1 / mm/day" ([link](https://www.fao.org/4/X0490E/x0490e07.htm)) |
| Ra em Lyon, 15 de julho (dentro do Exemplo 20) | {"latitude_graus": 45.72, "dia_do_ano": 196} | {"ra_mj_m2_dia": 40.55} | "For Day 15, Month = July, J = / 196" ... "Latitude = 45°43'N = / 45.72" ... "Ra = / 40.55 / MJ m-2 day-1" ([link](https://www.fao.org/4/X0490E/x0490e08.htm)) |
| ETo por Hargreaves (eq. 52), fim do Exemplo 20 | {"tmax_c": 26.6, "tmin_c": 14.8, "ra_mj_m2_dia": 40.55} | {"eto_mm_dia": 5.0} | "In comparison, the Hargreaves equation (Equation 52) predicts ETo = 5.0 mm/day" ([link](https://www.fao.org/4/X0490E/x0490e08.htm)) |
| A fórmula de Hargreaves (eq. 52) | {"formula": "ETo = 0.0023 (Tmean + 17.8) (Tmax - Tmin)^0.5 Ra, com Ra em mm/dia (MJ m-2 dia-1 x 0.408)"} | "ETo em mm/dia" | "ETo = 0.0023(Tmean + 17.8)(Tmax - Tmin)0.5 Ra (52)" ... "Units for both ETo and Ra in Equation 52 are mm day-1." ([link](https://www.fao.org/4/X0490E/x0490e07.htm)) |
| O balanço da água (cap. 8) | {"formulas": ["TAW = 1000(θFC - θWP) Zr (82)", "RAW = p TAW (83)", "Ks = (TAW - Dr) / ((1 - p) TAW), para Dr > RAW (84; na página é imagem)", "Dr,i = Dr,i-1 - (P - RO)i - Ii - CRi + ETc,i + DPi (85)", "0 ≤ Dr,i ≤ TAW (86)"]} | "Ks = 1 quando Dr ≤ RAW" | "When the root zone depletion is smaller than RAW, Ks = 1." ([link](https://www.fao.org/4/X0490E/x0490e0e.htm)) |

### O que não achei

- Conab, calendário de plantio e colheita: o endereço antigo.conab.gov.br recusou a conexão (certificado); nada lido.
- A janela de plantio da soja em Rio Verde: está no painel do ZARC, não no PDF da portaria.
- Embrapa, Kc e fases da soja e do milho medidos no Cerrado: não abri nenhuma página.
- Embrapa, dias de dessecação da braquiária antes da soja e água disputada com o milho: não abri nenhuma página.
- TIMESAT: o artigo original de Jönsson e Eklundh não foi aberto; a citação veio de fonte que o cita.
