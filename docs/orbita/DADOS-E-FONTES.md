<!-- Gerado com IA (Claude) -->
# Órbita Rural · os dados e as fontes

Cada dado usado pelo projeto: o que é, de quem é, por onde foi consultado, de que período e onde está guardado no repositório. Todo arquivo baixado tem ao lado o endereço e a hora da consulta. O motor não baixa nada na hora da pergunta: lê o que está guardado.

Os três pontos: Rio Verde (-17.79, -50.92), Jataí (-17.88, -51.71) e Silvânia (-16.66, -48.61), todos em Goiás. São pontos de cidade, não de fazenda.

## 1. Os dados da NASA

| o dado | a missão ou o produto | o endereço da consulta | o período | onde está guardado |
|---|---|---|---|---|
| a temperatura máxima e a mínima de cada dia | NASA POWER, API diária, comunidade AG (`T2M_MAX`, `T2M_MIN`) | `https://power.larc.nasa.gov/api/temporal/daily/point` (o endereço inteiro em `consulta.txt`) | Rio Verde: 1981-01-01 a 2026-11-13; Jataí e Silvânia: 2014-07-01 a 2026-11-13 | `data/orbita/nasa-power/` e `data/orbita/cidades/<cidade>/nasa-power/` |
| a chuva de modelo (só para comparar e para a faixa do "como está hoje") | NASA POWER (`PRECTOTCORR`, do modelo MERRA-2 corrigido) | a mesma consulta | os mesmos | as mesmas pastas |
| a chuva do satélite, o padrão da conta | GPM IMERG, entregue pela NASA POWER (`IMERG_PRECTOT`; o dia é o UTC) | `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=IMERG_PRECTOT...` | 2014-07-01 a 2026-09-14 (chega com cerca de 2 meses de atraso) | `data/orbita/validacao/chuva/imerg.csv` e `data/orbita/cidades/<cidade>/chuva/` |
| a chuva recente do satélite (para o "como está hoje") | GPM IMERG, versão rápida, lida da cor da imagem diária do NASA GIBS (camada `IMERG_Precipitation_Rate`) | `https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/IMERG_Precipitation_Rate/...` | 2026-09-01 a 2026-11-13 | `data/orbita/recente/<cidade>/chuva-recente.csv` (`fonte.json`) |
| a chuva do satélite em mm, de 5 em 5 dias (só conferência) | GPM IMERG Late V07, num espelho: o servidor do Climate Hazards Center, da Universidade da Califórnia em Santa Barbara. Não é servidor da NASA | `https://data.chc.ucsb.edu/products/EWX2/IMERGlatev7/...` | 2026-02-11 a 2026-11-10 | `data/orbita/recente/<cidade>/chuva-5-dias.csv` (`fonte-5-dias.json`) |
| o verde do satélite (NDVI), 6 pontos por cidade | MOD13Q1 v061 (MODIS/Terra, 250 m, uma medida a cada 16 dias), NASA LP DAAC, https://doi.org/10.5067/MODIS/MOD13Q1.061, pelo espelho Microsoft Planetary Computer | `https://planetarycomputer.microsoft.com/api/stac/v1/search` e `.../api/data/v1/item/point/...` | 2018-06-26 a 2026-10-16 (sem 2024 e 2025: faltam imagens no espelho) | `data/orbita/ndvi/` (Rio Verde) e `data/orbita/cidades/<cidade>/ndvi/` |

## 2. Os dados de outros órgãos

| o dado | de quem é | o endereço da consulta | o período | onde está guardado |
|---|---|---|---|---|
| a chuva medida em terra | INMET, estação automática A025 (Rio Verde), a 4,79 km do ponto | `https://portal.inmet.gov.br/dadoshistoricos` (um arquivo por ano) | 2014-01-01 a 2026-10-31, com buracos (o maior: de 2019-11-26 a 2021-06-10) | `data/orbita/validacao/chuva/inmet.csv` (`fonte-inmet.json`) |
| a colheita do milho de 2ª safra e da soja (kg por hectare) | IBGE, Produção Agrícola Municipal, pela API do SIDRA (tabelas 839 e 1612) | `https://apisidra.ibge.gov.br/values/t/839/...` e `.../t/1612/...` | 2015 a 2025 (o ano N do IBGE é a safra N-1/N) | `data/orbita/validacao/ibge/` e `data/orbita/cidades/<cidade>/ibge/` |
| a chuva CHIRPS (satélite ajustado com pluviômetros; só para comparar) | Climate Hazards Center, servida pelo ClimateSERV (do SERVIR) | `https://climateserv.servirglobal.net/api/submitDataRequest/` | 2014-07-01 a 2026-09-30 | `data/orbita/validacao/chuva/chirps.csv` |
| a chuva ERA5 (reanálise europeia) e a série padrão do Open-Meteo (modelos; só para comparar) | Open-Meteo, arquivo histórico | `https://archive-api.open-meteo.com/v1/archive` | 2014-07-01 a 2026-10-31 | `data/orbita/validacao/chuva/era5.csv` e `open-meteo.csv` |
| o mapa de uso da terra, usado só para escolher os pontos do verde em Jataí e Silvânia | `io-lulc-annual-v02` (Impact Observatory, Esri e Microsoft), 10 m, pelo Planetary Computer | no `fonte.json` de cada pasta | os mapas de 2018 e de 2023 | `data/orbita/cidades/<cidade>/ndvi/fonte.json` |

## 3. Os valores das culturas e da conta

| o que | a fonte | onde está |
|---|---|---|
| a conta da água (a evaporação, o pedido da planta, a água na zona das raízes, a palha) | FAO-56 (FAO Irrigation and Drainage Paper 56), https://www.fao.org/4/X0490E/x0490e00.htm | `backend/orbita/README.md`, seção "A conta" |
| o pedido de água, as fases e a raiz de cada cultura | FAO-56, Tabelas 11, 12 e 22; Embrapa Milho e Sorgo | `data/orbita/parametros-com-fonte.json` e `parametros-com-fonte.md` |
| a água que cada tipo de terra segura | ZARC, Portaria 345/2022 (solos Tipo 1, 2 e 3) | o mesmo arquivo |
| o limite de calor de cada cultura (soja 40 °C, milho 33 °C, sorgo 35 °C) | Embrapa Soja (Sistemas de Produção 9), Embrapa Milho e Sorgo (Cultivo do Milho), FAO (Crop Information: Sorghum) | o mesmo arquivo, em `calor` |
| a palha e a disputa do capim com o milho | FAO-56, capítulos 7 e 10; Embrapa Agropecuária Oeste | `backend/orbita/parametros.py` |

Cada valor leva a etiqueta "publicado" ou "hipótese". São 30 hipóteses, listadas na resposta do motor (`--json`).

## 4. O que foi comparado com o quê

| a comparação | para quê | onde ver |
|---|---|---|
| 4 fontes de chuva (IMERG, CHIRPS, ERA5, NASA POWER) contra a estação do INMET, de fevereiro a junho, em 8 safras | escolher a fonte de chuva da conta | `python3 -m orbita.validar`, seção 2 |
| a falta de água do milho na conta contra a colheita do milho de 2ª safra no IBGE, em 10 safras | saber se a conta acompanha a colheita | `python3 -m orbita.validar`, seção 4 |
| a evaporação da conta (Hargreaves) contra a evaporação do FAO entregue pelo Open-Meteo | conferir a conta | `python3 -m orbita.validar`, seção 3 |
| os dias sem planta viva do calendário contra os dias sem planta verde do satélite | provar a rotação de hoje da região | `python3 -m orbita.perguntar --cidade <cidade> --verde` |
| a chuva recente lida da cor contra a mesma chuva em mm e contra a estação do INMET | saber quanto confiar no "como está hoje" | `data/orbita/recente/LEIA-ME.md` |

Os números de cada comparação estão em [VALIDACAO.md](VALIDACAO.md).

## 5. Licenças e termos dos dados

Os registros das consultas guardam o endereço e a hora, mas **não trazem a licença nem os termos de uso de nenhuma fonte**. Fica a conferir pelo time, na página de cada fonte, antes de uma publicação fora do concurso. As únicas licenças que constam no repositório são as das letras da tela (Anton e Montserrat, SIL Open Font License 1.1, em `frontend/orbita/fontes/`).

## 6. Como baixar de novo

| o dado | o programa |
|---|---|
| o clima, a chuva do satélite e a colheita de uma cidade nova | `data/orbita/cidades/baixar_cidade.py` |
| a chuva recente | `data/orbita/recente/baixar_chuva_recente.py` |
| a chuva em mm de 5 em 5 dias | `data/orbita/recente/baixar_imerg_5_dias.py` (o único que usa biblioteca de fora: Pillow e numpy) |
| o verde do satélite | `data/orbita/ndvi/baixar_ndvi.py` |

Os comandos exatos estão no LEIA-ME de cada pasta. Esses programas não foram rodados de novo na conferência deste documento.
