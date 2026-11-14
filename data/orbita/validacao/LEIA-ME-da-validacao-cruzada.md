# Validação cruzada da chuva de Rio Verde (GO) · frente B do motor do Órbita Rural

> Gerado com IA (Claude) em 2026-11-14. Ponto: latitude -17.79, longitude -50.92. Período: de 2014-07-01 a 2026-10-31, por dia.
> Todo número das tabelas sai do programa `comparar.py`, que lê os arquivos baixados. Nenhum foi digitado à mão.
> Os valores de chuva estão em milímetros (mm), arredondados para o inteiro.

**O resumo, em 5 linhas**

- As outras fontes **não confirmam** a NASA POWER. A ordem das safras, da mais seca à mais chuvosa, muda de fonte para fonte.
- A safra mais seca (fevereiro a junho) é uma em cada fonte: 2024-25 na NASA POWER, 2017-18 no IMERG, 2015-16 no CHIRPS, 2021-22 no ERA5.
- 2025 só é um ano muito seco na NASA POWER (678 mm). Os dois satélites dão 1.505 mm (IMERG) e 1.481 mm (CHIRPS): um ano comum.
- O pior rendimento do milho 2ª safra em Rio Verde, no IBGE, é o de 2016 (safra 2015-16): 3.300 kg/ha. Só o CHIRPS dá essa safra como a mais seca.
- A série padrão do Open-Meteo troca de modelo em 2017-01-01 e passa a dar bem menos chuva. Para comparar anos, use `open-meteo-era5.csv`.

## 1. As fontes

Os endereços completos e a hora de cada consulta estão em `chuva/fonte.json` e `ibge/fonte.json`. A resposta crua de cada uma está em `chuva/bruto/` e `ibge/bruto/`.

| arquivo | o que é | baixado em (horário de Brasília) | o que veio | dias sem dado |
|---|---|---|---|---|
| `chuva/open-meteo.csv` | Open-Meteo, a consulta padrão ("best match": a mistura de modelos que o serviço escolhe). É reanálise: clima recalculado por modelo, não é pluviômetro | 2026-11-14 19:20:51 | 2014-07-01 a 2026-10-31, 4.506 dias | 0 |
| `chuva/open-meteo-era5.csv` | Open-Meteo, só o modelo ERA5 (reanálise europeia, grade de 0,25 grau, uns 25 km) | 2026-11-14 19:20:51 | 2014-07-01 a 2026-10-31, 4.506 dias | 0 |
| `chuva/imerg.csv` | GPM IMERG: chuva estimada por satélites da NASA, servida pela NASA POWER no parâmetro `IMERG_PRECTOT` | 2026-11-14 19:20:54 | 2014-07-01 a 2026-09-14 | 47 (de 2026-09-15 a 2026-10-31) |
| `chuva/chirps.csv` | CHIRPS: satélite (infravermelho) ajustado com pluviômetros, servido pelo ClimateSERV (do SERVIR, ligado à NASA) | 2026-11-14, de 19:21:47 a 19:23:20 | 2014-07-01 a 2026-09-30 | 31 (outubro de 2026) |
| `ibge/rendimento_rio_verde.csv` | IBGE, Produção Agrícola Municipal (PAM), pela API do SIDRA | 2026-11-14 19:22:08 | 2015 a 2025, 22 linhas (11 anos × 2 produtos) | 0 |
| `../verificacao/nasa-power/resposta.json` | NASA POWER, `PRECTOTCORR` (a chuva do modelo MERRA-2 corrigida). Baixado antes, por outra frente | 2026-11-14 13:42:12 | 1981-01-01 a 2026-11-13 | 2 (2026-11-12 e 13) |

Os endereços:

- Open-Meteo padrão: `https://archive-api.open-meteo.com/v1/archive?latitude=-17.79&longitude=-50.92&start_date=2014-07-01&end_date=2026-10-31&daily=precipitation_sum,temperature_2m_max,temperature_2m_min,et0_fao_evapotranspiration&timezone=America%2FSao_Paulo`
- Open-Meteo só ERA5: o mesmo endereço, com `&models=era5` no fim.
- IMERG: `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=IMERG_PRECTOT&community=AG&longitude=-50.92&latitude=-17.79&start=20140701&end=20261031&format=JSON&time-standard=UTC`
- CHIRPS: 13 pedidos, um por ano, em `https://climateserv.servirglobal.net/api/submitDataRequest/` (conjunto 0, operação 5 = média, geometria = o ponto). Os 13 endereços estão no `chuva/fonte.json`.
- IBGE, milho 2ª safra: `https://apisidra.ibge.gov.br/values/t/839/n6/5218805/v/216,214,112/p/all/c81/114254`
- IBGE, soja: `https://apisidra.ibge.gov.br/values/t/1612/n6/5218805/v/216,214,112/p/all/c81/2713`

**Que modelo o Open-Meteo usa.** A documentação (https://open-meteo.com/en/docs/historical-weather-api) diz: "The default Best Match combines IFS HRES, ERA5 and ERA5-Land seamlessly." E dá as datas: ERA5 (0,25 grau) desde 1940, ERA5-Land (0,1 grau) desde 1950, ECMWF IFS (9 km) "2017 to present". Ela não diz o dia da troca. Por isso conferi: repeti a consulta só com o ERA5 e só com o IFS e comparei dia a dia (a conta está no `chuva/fonte.json`, em `conferencia_do_modelo`).

- Até 2016-12-31, a chuva da série padrão é igual à do ERA5 em todos os dias comparados (86 de 86 em 2014, 216 de 216 em 2015, 194 de 194 em 2016).
- De 2017-01-01 em diante, é igual à do IFS em todos os dias comparados (199 de 199 em 2017 até 164 de 164 em 2026). A evaporação (`eto_mm`) também passa a ser a do IFS em 2017.
- Neste ponto o IFS dá bem menos chuva que o ERA5. Em 2017: 946 mm na série padrão e 1.345 mm no ERA5.
- **Consequência:** a série padrão tem um degrau em 2017. Queda de chuva nela, de 2016 para 2017, é troca de modelo e não clima. O `open-meteo-era5.csv` tem as mesmas colunas e um modelo só.
- A grade devolvida: -17.75044, -50.930237 (padrão) e -17.75, -51.0 (ERA5). Altitude 763 m.

**O dia do IMERG é o dia UTC.** A NASA POWER só entrega o IMERG no horário universal (com a hora local ela devolve o aviso "The IMERG Source Data is not available at the Local Solar Time (LST) standard."). O dia vai das 21h da véspera às 21h, em Brasília. Isso mexe pouco na soma de meses.

**A que safra corresponde o "ano" do IBGE.** A PAM é por ano civil (de janeiro a dezembro), o ano da colheita. Então o ano N do IBGE é a safra (N-1)/N: a soja plantada no fim de N-1 e colhida no começo de N; o milho 2ª safra plantado no começo de N e colhido no meio de N. Exemplo: 2016 no IBGE = safra 2015-16.

- A regra do ano civil vem das notas técnicas da PAM (https://ftp.ibge.gov.br/Producao_Agricola/Producao_Agricola_Municipal_%5banual%5d/2013/pam2013_Nota_Tecnica.pdf). O trecho, como apareceu no resumo da busca: "considera-se o total, no ano civil em que for registrada a maior parte da quantidade produzida". **Não abri o PDF** (a página do IBGE devolveu erro 403): fica "a conferir".
- O calendário do milho 2ª safra no Sul Goiano vem do boletim da Conab citado na seção 6 (quadro do milho segunda safra, safra 2020/21): semeadura em fevereiro, floração em abril e maio, colheita em agosto e setembro.

**Os códigos do IBGE** vieram da própria API, que devolve o nome de cada código: tabela 839, categoria 114254 = "Milho (em grão) - 2ª safra"; tabela 1612, categoria 2713 = "Soja (em grão)"; variável 112 = "Rendimento médio da produção" (quilogramas por hectare), 216 = "Área colhida" (hectares), 214 = "Quantidade produzida" (toneladas). O programa confere esses nomes e para se algum não bater.

## 2. A chuva por safra, em cada fonte

**De 1/fev a 30/jun (a janela da 2ª safra):**

<!-- TABELA:fev-jun -->
| safra | janela | NASA POWER | IMERG | CHIRPS | ERA5 | Open-Meteo padrão |
|---|---|---|---|---|---|---|
| 2015-16 | fev a jun de 2016 | 350 | 553 | 468 | 402 | 402 |
| 2016-17 | fev a jun de 2017 | 518 | 625 | 676 | 529 | 302 |
| 2017-18 | fev a jun de 2018 | 408 | 431 | 522 | 428 | 285 |
| 2018-19 | fev a jun de 2019 | 541 | 582 | 603 | 503 | 401 |
| 2019-20 | fev a jun de 2020 | 436 | 483 | 574 | 531 | 428 |
| 2020-21 | fev a jun de 2021 | 326 | 506 | 502 | 412 | 247 |
| 2021-22 | fev a jun de 2022 | 341 | 529 | 469 | 343 | 283 |
| 2022-23 | fev a jun de 2023 | 379 | 710 | 686 | 481 | 283 |
| 2023-24 | fev a jun de 2024 | 358 | 734 | 759 | 567 | 415 |
| 2024-25 | fev a jun de 2025 | 298 | 491 | 584 | 350 | 296 |
| 2025-26 | fev a jun de 2026 | 273 | 542 | 637 | 402 | 432 |
<!-- FIM:fev-jun -->

**De 1/out a 31/jan (a janela da soja):**

<!-- TABELA:out-jan -->
| safra | janela | NASA POWER | IMERG | CHIRPS | ERA5 | Open-Meteo padrão |
|---|---|---|---|---|---|---|
| 2015-16 | out de 2015 a jan de 2016 | 616 | 803 | 1089 | 866 | 866 |
| 2016-17 | out de 2016 a jan de 2017 | 706 | 812 | 841 | 824 | 802 |
| 2017-18 | out de 2017 a jan de 2018 | 798 | 834 | 970 | 804 | 669 |
| 2018-19 | out de 2018 a jan de 2019 | 767 | 792 | 840 | 757 | 609 |
| 2019-20 | out de 2019 a jan de 2020 | 793 | 860 | 1044 | 762 | 599 |
| 2020-21 | out de 2020 a jan de 2021 | 391 | 737 | 727 | 525 | 381 |
| 2021-22 | out de 2021 a jan de 2022 | 877 | 991 | 970 | 684 | 605 |
| 2022-23 | out de 2022 a jan de 2023 | 556 | 729 | 785 | 743 | 484 |
| 2023-24 | out de 2023 a jan de 2024 | 441 | 643 | 737 | 486 | 341 |
| 2024-25 | out de 2024 a jan de 2025 | 665 | 906 | 1041 | 972 | 643 |
| 2025-26 | out de 2025 a jan de 2026 | 394 | 932 | 848 | 613 | 438 |
<!-- FIM:out-jan -->

Como ler: a NASA POWER fica abaixo dos dois satélites em todas as 11 safras, nas duas janelas. Na janela de fevereiro a junho, a diferença para o IMERG vai de 23 mm (2017-18) a 376 mm (2023-24). "Open-Meteo padrão" é igual ao ERA5 só em 2015-16, antes da troca de modelo.

## 3. A safra mais seca em cada fonte, e se a ordem é parecida

Só as 10 safras da regra dos anos (2015-16 a 2024-25), na janela de fevereiro a junho.

<!-- TABELA:mais-seca -->
| fonte | a safra mais seca (fev a jun) | a 2ª mais seca | mediana das 10 (mm) | a mais perto da mediana | soma de d² contra a NASA POWER | correlação de postos com a NASA POWER |
|---|---|---|---|---|---|---|
| NASA POWER | 2024-25 (298 mm) | 2020-21 (326 mm) | 369 | 2022-23 | — | — |
| IMERG | 2017-18 (431 mm) | 2019-20 (483 mm) | 541 | 2015-16 | 132 | 0,20 |
| CHIRPS | 2015-16 (468 mm) | 2021-22 (469 mm) | 579 | 2019-20 | 98 | 0,41 |
| ERA5 | 2021-22 (343 mm) | 2024-25 (350 mm) | 454 | 2017-18 | 50 | 0,70 |
| Open-Meteo padrão | 2020-21 (247 mm) | 2022-23 (283 mm) | 299 | 2024-25 | 96 | 0,42 |
<!-- FIM:mais-seca -->

**A conta da correlação de postos (Spearman).** Em cada fonte, as 10 safras recebem um posto: 1 para a mais seca, 10 para a mais chuvosa. Para cada safra, d é a diferença entre o posto na fonte e o posto na NASA POWER. A correlação é 1 − 6 × (soma de d²) ÷ (10 × 99). Vale 1 se a ordem for igual, 0 se não houver relação. Exemplo, o IMERG: soma de d² = 132, então 1 − 792 ÷ 990 = 0,20. Os postos:

<!-- TABELA:postos -->
| safra | NASA POWER | IMERG | CHIRPS | ERA5 | Open-Meteo padrão |
|---|---|---|---|---|---|
| 2015-16 | 4 | 6 | 1 | 3 | 8 |
| 2016-17 | 9 | 8 | 8 | 8 | 6 |
| 2017-18 | 7 | 1 | 4 | 5 | 4 |
| 2018-19 | 10 | 7 | 7 | 7 | 7 |
| 2019-20 | 8 | 2 | 5 | 9 | 10 |
| 2020-21 | 2 | 4 | 3 | 4 | 1 |
| 2021-22 | 3 | 5 | 2 | 1 | 3 |
| 2022-23 | 6 | 9 | 9 | 6 | 2 |
| 2023-24 | 5 | 10 | 10 | 10 | 9 |
| 2024-25 | 1 | 3 | 6 | 2 | 5 |
<!-- FIM:postos -->

E as outras fontes entre si:

<!-- TABELA:pares -->
| par | soma de d² | correlação de postos |
|---|---|---|
| IMERG × CHIRPS | 62 | 0,62 |
| IMERG × ERA5 | 100 | 0,39 |
| CHIRPS × ERA5 | 48 | 0,71 |
<!-- FIM:pares -->

O que isso diz, sem forçar:

- **Nenhuma fonte dá a mesma safra mais seca que a NASA POWER** (2024-25). Na NASA POWER ela cai em 2025, o ano suspeito (seção 4).
- A ordem das safras é parecida só com o ERA5 (0,70), que é da mesma família (modelo). Com os satélites é fraca: 0,20 (IMERG) e 0,41 (CHIRPS). Com 10 safras, a correlação precisa passar de uns 0,65 para se distinguir do acaso (valor de tabela estatística, citado de memória: a conferir).
- Os dois satélites também não concordam muito entre si (0,62). O CHIRPS e o ERA5 concordam mais (0,71).
- **Onde há acordo:** 2020-21 e 2021-22 estão entre as 5 mais secas em todas as fontes; 2018-19 está entre as 4 mais chuvosas em todas; 2016-17 também, menos no Open-Meteo padrão (que tem o degrau de 2017).
- **Onde não há:** 2023-24 é a mais chuvosa nos satélites e no ERA5 e a 5ª mais seca na NASA POWER. 2022-23 é a 2ª mais chuvosa nos satélites e a 6ª mais seca na NASA POWER.
- **A safra "normal"** (a mais perto da mediana) também muda: 2022-23 na NASA POWER, 2015-16 no IMERG, 2019-20 no CHIRPS, 2017-18 no ERA5.

## 4. A dúvida de 2025

O total de cada ano civil, em cada fonte:

<!-- TABELA:anos -->
| ano | NASA POWER | IMERG | CHIRPS | ERA5 | Open-Meteo padrão |
|---|---|---|---|---|---|
| 2015 | 1176 | 1486 | 1715 | 1320 | 1320 |
| 2016 | 1075 | 1465 | 1522 | 1403 | 1403 |
| 2017 | 1373 | 1493 | 1677 | 1345 | 946 |
| 2018 | 1299 | 1437 | 1576 | 1378 | 1068 |
| 2019 | 1265 | 1341 | 1542 | 1186 | 931 |
| 2020 | 981 | 1246 | 1382 | 1149 | 918 |
| 2021 | 1100 | 1554 | 1496 | 1054 | 825 |
| 2022 | 977 | 1298 | 1293 | 1024 | 807 |
| 2023 | 973 | 1553 | 1610 | 1149 | 704 |
| 2024 | 1012 | 1589 | 1702 | 1400 | 963 |
| 2025 | 678 | 1505 | 1481 | 1064 | 793 |
| 2026 (até 31/out) | 572 | 858 (faltam 47 dias) | 1096 (faltam 31 dias) | 828 | 786 |
<!-- FIM:anos -->

2025 contra os dez anos anteriores:

<!-- TABELA:duvida-2025 -->
| fonte | 2025 (mm) | média de 2015 a 2024 (mm) | 2025 contra essa média | posto de 2025 (1º = o mais seco) | o ano mais seco de 2015 a 2025 |
|---|---|---|---|---|---|
| NASA POWER | 678 | 1123 | -40% | 1º de 11 | 2025 (678 mm) |
| IMERG | 1505 | 1446 | +4% | 8º de 11 | 2020 (1246 mm) |
| CHIRPS | 1481 | 1551 | -5% | 3º de 11 | 2022 (1293 mm) |
| ERA5 | 1064 | 1241 | -14% | 3º de 11 | 2022 (1024 mm) |
| Open-Meteo padrão | 793 | 988 | -20% | 2º de 11 | 2023 (704 mm) |
<!-- FIM:duvida-2025 -->

A chuva da NASA POWER dividida pela de cada fonte, ano a ano (1,00 = igual):

<!-- TABELA:razao-power -->
| ano | IMERG | CHIRPS | ERA5 | Open-Meteo padrão |
|---|---|---|---|---|
| 2015 | 0,79 | 0,69 | 0,89 | 0,89 |
| 2016 | 0,73 | 0,71 | 0,77 | 0,77 |
| 2017 | 0,92 | 0,82 | 1,02 | 1,45 |
| 2018 | 0,90 | 0,82 | 0,94 | 1,22 |
| 2019 | 0,94 | 0,82 | 1,07 | 1,36 |
| 2020 | 0,79 | 0,71 | 0,85 | 1,07 |
| 2021 | 0,71 | 0,74 | 1,04 | 1,33 |
| 2022 | 0,75 | 0,76 | 0,95 | 1,21 |
| 2023 | 0,63 | 0,60 | 0,85 | 1,38 |
| 2024 | 0,64 | 0,59 | 0,72 | 1,05 |
| 2025 | 0,45 | 0,46 | 0,64 | 0,86 |
<!-- FIM:razao-power -->

**A resposta: não, as outras fontes não mostram um ano tão seco.** Na NASA POWER, 2025 fica 40% abaixo da média de 2015 a 2024 e é o mais seco dos 11. No IMERG fica 4% acima; no CHIRPS, 5% abaixo; no ERA5, 14% abaixo (o 3º mais seco). A NASA POWER dava de 0,6 a 0,9 da chuva dos satélites até 2024 e cai para 0,45 (IMERG) e 0,46 (CHIRPS) em 2025. Ou seja: a NASA POWER já era a fonte mais seca, e em 2025 ela se afasta ainda mais das outras. Isso combina com um problema da série (por exemplo, troca de fonte dentro da NASA POWER, que lista "MERRA2" e "GEOSIT" no cabeçalho), mas **este trabalho não prova a causa**. Também há uma queda desde 2023: a razão para os satélites já estava em 0,6 em 2023 e 2024. 2026 segue baixo na NASA POWER (572 mm até 31/out, contra 1.096 mm no CHIRPS até 30/set).

## 5. O rendimento do milho 2ª safra e da soja, e a safra mais seca

<!-- TABELA:ibge -->
| ano do IBGE | safra | milho 2ª safra (kg/ha) | área colhida (ha) | produção (t) | soja (kg/ha) | área colhida (ha) | produção (t) |
|---|---|---|---|---|---|---|---|
| 2015 | 2014-15 | 6900 | 216000 | 1490400 | 2400 | 310000 | 744000 |
| 2016 | 2015-16 | 3300 | 200000 | 660000 | 3120 | 315000 | 982800 |
| 2017 | 2016-17 | 6000 | 245000 | 1470000 | 3500 | 315000 | 1102500 |
| 2018 | 2017-18 | 5400 | 245000 | 1323000 | 3600 | 325000 | 1170000 |
| 2019 | 2018-19 | 8000 | 285000 | 2280000 | 3180 | 340000 | 1081200 |
| 2020 | 2019-20 | 6750 | 320000 | 2160000 | 3600 | 390000 | 1404000 |
| 2021 | 2020-21 | 7200 | 340000 | 2448000 | 3600 | 410000 | 1476000 |
| 2022 | 2021-22 | 5100 | 357000 | 1820700 | 3900 | 420000 | 1638000 |
| 2023 | 2022-23 | 7000 | 357500 | 2502500 | 4200 | 421500 | 1770300 |
| 2024 | 2023-24 | 6700 | 332000 | 2224400 | 3700 | 425000 | 1572500 |
| 2025 | 2024-25 | 7560 | 350000 | 2646000 | 3900 | 428500 | 1671150 |
<!-- FIM:ibge -->

- **O pior rendimento do milho 2ª safra é o de 2016 (safra 2015-16): 3.300 kg/ha**, perto da metade dos anos vizinhos (6.900 em 2015 e 6.000 em 2017). O segundo pior é o de 2022 (safra 2021-22): 5.100 kg/ha.
- A soja não tem quebra parecida nesses anos. O pior ano da soja é 2015 (safra 2014-15): 2.400 kg/ha.
- O ano de 2021 (safra 2020-21, a da quebra em Goiás na Conab) **não aparece como quebra em Rio Verde no IBGE**: 7.200 kg/ha, o 3º melhor dos 11.

A chuva de fevereiro a junho contra o rendimento do milho, nas 10 safras (mesma conta de postos da seção 3):

<!-- TABELA:chuva-x-milho -->
| fonte da chuva | a safra mais seca (fev a jun) | posto da chuva de 2015-16 (1º = a mais seca) | soma de d² (chuva × rendimento) | correlação de postos (chuva × rendimento do milho 2ª safra) |
|---|---|---|---|---|
| NASA POWER | 2024-25 | 4º de 10 | 156 | 0,05 |
| IMERG | 2017-18 | 6º de 10 | 160 | 0,03 |
| CHIRPS | 2015-16 | 1º de 10 | 90 | 0,45 |
| ERA5 | 2021-22 | 3º de 10 | 134 | 0,19 |
| Open-Meteo padrão | 2020-21 | 8º de 10 | 186 | -0,13 |
<!-- FIM:chuva-x-milho -->

- **Bate com a safra mais seca? Só no CHIRPS.** Ele dá 2015-16 como a mais seca e 2021-22 como a 2ª mais seca (468 e 469 mm: 1 mm de diferença entre as duas), os dois piores anos do milho no IBGE. Na NASA POWER, 2015-16 é a 4ª mais seca e 2021-22 a 3ª; a mais seca dela (2024-25) teve o 2º melhor rendimento (7.560 kg/ha).
- A soma da chuva da janela explica pouco do rendimento em qualquer fonte (a maior correlação é 0,45, no CHIRPS). O total de 5 meses não vê quando a chuva faltou; a conta dia a dia do motor (a falta de água) é o teste melhor.
- O rendimento do IBGE também sobe com o tempo (tecnologia, área), o que atrapalha a comparação entre anos distantes.

## 6. A Conab e a quebra da 2ª safra de milho de 2020-21

**A fonte:** Conab, *Acompanhamento da safra brasileira de grãos*, v. 8, safra 2020/21, nº 12, décimo segundo levantamento, setembro de 2021. O link (aberto em 2026-11-14, 19:22): https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/safras/safra-de-graos/boletim-da-safra-de-graos/12o-levantamento-safra-2020-21/e-book_boletimzdezsafrasz-z12ozlevantamentoz1z2020z21.pdf

Os trechos exatos:

- Sobre o país (seção "Milho segunda safra – 2020/21", páginas 56 e 57 pelo rodapé): "A segunda safra de milho contempla os danos causados pelo clima nos principais estados produtores. Além da seca ocorrida em momentos cruciais das lavouras, houve a ocorrência de massas de ar frio que trouxeram geadas nos principais estados produtores da Região Centro-Sul." E: "Mesmo com o aumento de 8,6% na área plantada, estimada em 14.935,5 mil hectares, as condições climáticas adversas derrubaram os níveis de produtividade, para 3.982 kg/ha, redução de 27% em relação à temporada passada. A produção estimada atingiu 59.471,5 mil toneladas, representando queda de 20,8%, comparada à safra passada."
- Sobre Goiás (página 60 pelo rodapé): "Em Goiás, cerca de 85% da área de milho já foi colhida. Na parte leste do estado, em virtude da baixa disponibilidade de secadores e rede armazenadora, o ritmo segue lento (em média 60% colhido). A qualidade colhida deixa a desejar, tanto no tamanho quanto no peso dos grãos."
- Na tabela de todos os grãos por estado, a linha de Goiás traz a produtividade de 4.535 para 3.845 kg/ha (−15,2%) e a produção de 27.547,2 para 23.735,2 mil toneladas (−13,8%), de 2019/20 para 2020/21. É a soma de todos os grãos, não só o milho (li a linha no texto extraído do PDF; o cabeçalho das colunas não conferi um a um).

**O que não achei:** o número só do milho 2ª safra de Goiás (área, produtividade e produção). Ele não está no texto do boletim; a tabela por estado fica em planilha à parte, que não abri no limite de 10 minutos. O boletim fala em seca e geada no país e em grão pequeno e leve em Goiás, mas não dá, no texto, o tamanho da quebra goiana.

## 7. O que não deu para baixar ou conferir

- **Pluviômetro (estação do INMET):** não foi baixado por esta frente e não entra nas tabelas daqui. Outra frente (a E do guia) está pondo a estação de Rio Verde na pasta `inmet/`; não li esse material. Sem a chuva medida em terra, não dá para dizer qual fonte está certa; só que elas discordam.
- **A versão do IMERG** que a NASA POWER serve (a final ou a rápida) e **a versão do CHIRPS** no ClimateSERV: não conferi.
- **O IMERG acaba em 2026-09-14 e o CHIRPS em 2026-09-30.** Nenhuma janela das tabelas de safra é afetada; só o total de 2026.
- **O título das tabelas 839 e 1612 do IBGE:** a página de descrição (`desctabapi.aspx`) devolveu erro 403 (barreira contra robô) e o outro serviço de metadados (`servicodados.ibge.gov.br`) não respondeu em 50 segundos, duas vezes. Os nomes dos códigos vieram da própria resposta dos dados.
- **O texto do IBGE sobre o ano civil:** só o resumo da busca, sem abrir o PDF (seção 1).
- **O número da Conab só para o milho 2ª safra de Goiás** (seção 6).
- **A causa da chuva baixa da NASA POWER em 2025:** não investigada aqui.
- **O modelo da temperatura do Open-Meteo padrão depois de 2017:** não identificado. Num teste à parte, não guardado, a máxima não bateu com o ERA5 nem com o ERA5-Land na maioria dos dias, e o IFS veio vazio na temperatura até 2025-09-28. Até 2016 ela bateu com o ERA5-Land.
- A API do ClimateSERV também oferece o IMERG (conjunto 26). Não usei, porque a NASA POWER já entregou.

## Os programas (Python 3, só a biblioteca padrão)

Rodar de dentro desta pasta, com `python3 -I`:

- `timeout 300 python3 -I baixar_open_meteo.py` → `chuva/open-meteo.csv` e `chuva/open-meteo-era5.csv`
- `timeout 300 python3 -I baixar_imerg_power.py` → `chuva/imerg.csv`
- `timeout 900 python3 -I baixar_chirps_climateserv.py` → `chuva/chirps.csv` (levou menos de 3 minutos)
- `timeout 180 python3 -I baixar_ibge.py` → `ibge/rendimento_rio_verde.csv`
- `python3 -I comparar.py` → `tabelas.md` e as tabelas deste arquivo (entre as marcas `TABELA` e `FIM`)

Formatos: `chuva/open-meteo.csv` e `chuva/open-meteo-era5.csv` têm `data,chuva_mm,tmax_c,tmin_c,eto_mm`; `chuva/imerg.csv` e `chuva/chirps.csv` têm `data,chuva_mm`; dia sem dado fica com o campo em branco. `ibge/rendimento_rio_verde.csv` tem `ano,produto,rendimento_kg_ha,area_colhida_ha,producao_t`, com `milho_2a_safra` e `soja`.
