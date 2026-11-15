<!-- Gerado com IA (Claude) -->
# Órbita Rural · a validação

O projeto se apresenta validado por duas vias: **os dados** (a conta foi conferida contra medida em terra e contra a colheita registrada) e **o uso** (um questionário para produtores). A primeira via está feita e descrita aqui, com os números e de onde cada um sai. A segunda está pronta para ir a campo e **ainda não tem respostas**.

Como conferir de novo: de dentro de `backend/`, `python3 -m orbita.validar` (rodado em 2026-11-15 numa cópia do ramo `jose`, commit `fe578c6`; os números abaixo são os da saída).

## 1. A chuva do satélite contra a estação em terra

**O que foi comparado.** A soma da chuva de 1 de fevereiro a 30 de junho (a janela da 2ª safra), em cada safra, em quatro fontes, contra a chuva medida pela estação automática A025 do INMET em Rio Verde, que fica a 4,79 km do ponto do projeto. Das 10 safras de 2015-16 a 2024-25, 8 servem para comparar: a estação ficou fora do ar de 2019-11-26 a 2021-06-10.

| fonte da chuva | o que é | erro médio contra a estação (8 safras) |
|---|---|---|
| GPM IMERG | a chuva estimada por satélites da NASA | 12,1% |
| CHIRPS | satélite ajustado com pluviômetros | 17,6% |
| ERA5 | modelo (reanálise europeia) | 26,7% |
| NASA POWER, `PRECTOTCORR` | a chuva de modelo da NASA POWER | 33,2% |

De onde sai: `orbita.validar`, seção 2. O erro médio é a média, nas safras comparadas, da distância entre o total da fonte e o da estação na janela, em % da estação.

**O que mais apareceu.** A chuva de modelo da NASA POWER deu, na janela, em média 86% da chuva da estação nas 4 safras comparadas até 2020, e 51% nas 4 de 2021 em diante. No ano de 2025, 678,4 mm no modelo contra 1.548,0 mm na estação (44%). De onde sai: `orbita.validar`, seção 2, e `data/orbita/validacao/LEIA-ME-da-validacao-cruzada.md`.

**A decisão.** A conta usa a chuva do satélite GPM IMERG. A temperatura continua sendo a da NASA POWER.

**Os limites.** Uma estação só, que mede um ponto, enquanto o satélite mede um quadrado do mapa. Os 12,1% valem para a soma de cinco meses nessa série longa. Não valem para um dia, nem para a chuva recente (seção 4), nem para Jataí e Silvânia, onde não há estação conferida.

## 2. A conta contra a colheita do IBGE

**O que foi comparado.** A falta de água do milho de 2ª safra na conta (em % do que o milho pediu; rotação de hoje, terra média, chuva do IMERG) contra o rendimento do milho de 2ª safra em Rio Verde na Produção Agrícola Municipal do IBGE, nas 10 safras de 2015-16 a 2024-25.

| safra | colheita no IBGE (kg/ha) | falta de água do milho na conta |
|---|---|---|
| 2015-16 | 3.300 | 49,6% |
| 2016-17 | 6.000 | 25,8% |
| 2017-18 | 5.400 | 35,1% |
| 2018-19 | 8.000 | 29,4% |
| 2019-20 | 6.750 | 34,7% |
| 2020-21 | 7.200 | 45,9% |
| 2021-22 | 5.100 | 54,8% |
| 2022-23 | 7.000 | 41,0% |
| 2023-24 | 6.700 | 41,8% |
| 2024-25 | 7.560 | 32,7% |

De onde sai: `orbita.validar`, seção 4, e `data/orbita/validacao/ibge/rendimento_rio_verde.csv`.

- **As 2 safras de maior falta de água na conta (2021-22 e 2015-16) são as 2 piores colheitas no IBGE.** A ordem dentro do par é invertida: a maior falta na conta é a de 2021-22, e a pior colheita é a de 2015-16.
- A régua de colheita ruim usada pelo motor: rendimento abaixo de 80% da mediana das 10 safras (mediana de 6.725 kg/ha; 80% são 5.380 kg/ha). Só essas duas safras ficam abaixo. Essa régua é escolha do projeto, não do IBGE.
- A safra de maior falta sem colheita ruim é a de 2020-21 (45,9%, 7.200 kg/ha).
- A correlação de postos entre a falta de água e o rendimento: -0,52 com a chuva do IMERG (CHIRPS -0,42; ERA5 -0,41; NASA POWER -0,26). **São só 10 safras: é indício, não prova.**

**Os limites.** O resultado vale para Rio Verde com a terra média. Na terra que segura pouca água aparece um alarme falso (2020-21); na que segura muita, a colheita ruim de 2015-16 fica abaixo do nível (`backend/orbita/README.md`). Em Jataí, o nível de sede forte marca as 10 safras e só uma foi colheita ruim; em Silvânia nenhuma safra ficou abaixo do corte. O rendimento também depende de praga, adubo, semente e data de plantio. Falta de água na conta não é previsão de colheita.

## 3. O verde do satélite contra o calendário

**O que foi comparado.** Os dias seguidos sem planta viva que o calendário da rotação de hoje dá (122, com pousio) contra os dias seguidos sem planta verde que o satélite MODIS viu em 6 pontos de lavoura perto de cada cidade.

| cidade | mediana do satélite (dias) | de quanto a quanto | medidas | o calendário | leitura |
|---|---|---|---|---|---|
| Rio Verde | 96 | 16 a 160 | 36 | 122 | dentro da faixa |
| Jataí | 80 | 0 a 128 | 30 | 122 | dentro da faixa |
| Silvânia | 96 | 16 a 192 | 35 | 122 | dentro da faixa |

De onde sai: `python3 -m orbita.perguntar --cidade <cidade> --verde`, `backend/orbita/LEIA-ME-motor.md` (seção 8) e `data/orbita/ndvi/LEIA-ME.md`.

**Os limites.** Os pontos foram escolhidos no mapa: não se sabe de quem são nem o que foi plantado, e ninguém conferiu em campo. Os anos de 2024 e 2025 ficaram de fora (faltam imagens no serviço consultado). "Sem planta verde" não é "terra descoberta": o satélite não vê a palha. É prova só da rotação de hoje da região; nas outras rotações os dias vêm do calendário. O limite que separa "com verde" de "sem verde" é hipótese.

## 4. A chuva recente (o "como está hoje")

**O que foi comparado.** A chuva rápida do satélite, lida da cor da imagem diária do NASA GIBS (2 dias de atraso), contra a mesma chuva em mm somada de 5 em 5 dias e contra a estação do INMET de Rio Verde.

- A leitura da cor contra o valor em mm, de 2026-09-01 a 2026-11-10 (13 períodos de 5 dias): 9,0% a menos em Rio Verde, 5,0% a mais em Jataí, 12,6% a mais em Silvânia.
- Contra a estação de Rio Verde, em 10 períodos de 2026-09-01 a 2026-10-25 (50 dias): a estação mediu 202,0 mm; o satélite em mm, 278,7 mm (38,0% a mais); o satélite lido da cor, 266,2 mm (31,8% a mais); a chuva de modelo, 111,6 mm (44,8% a menos).

De onde sai: `data/orbita/recente/LEIA-ME.md`.

**A consequência.** O "como está hoje" não dá um número só. Mostra a água na terra com a chuva do satélite e com a chuva de modelo, e a faixa entre as duas. Em Rio Verde, no último dia com dado em 2026-11-15 (o dia 2026-11-11), a faixa ia de 34,8 a 63,0 mm (`python3 -m orbita.perguntar --hoje`). **A faixa é larga, o período comparado é curto (50 dias) e a estação é uma só.**

## 5. A safra ruim, dia a dia

O replay da safra 2015-16 em Rio Verde (`python3 -m orbita.perguntar --replay 2015-16`) mostra a conta de cada dia: o milho entra em 2016-02-10; a sede começa em 2016-04-04 e dura 60 dias seguidos; em 2016-04-24 a água que a planta alcança chega a 0,1 mm; foram 19 dias de calor forte na fase crítica do milho (máxima acima de 33 °C); faltaram 220,6 mm, 49,6% do pedido. São valores da conta. Ninguém mediu a terra.

## 6. A conferência do próprio programa

- 440 testes automáticos passam no ramo `jose` (`python3 -m unittest`, de dentro de `backend/`; rodado em 2026-11-15).
- A conta da evaporação foi testada com os Exemplos 8 e 20 do manual FAO-56 e ficou 6,6% acima da evaporação do FAO que o Open-Meteo entrega (`orbita.validar`, seção 3).
- O código do motor e do agente foi revisado por outro modelo de IA; os defeitos achados foram consertados, cada um com teste (`backend/orbita/LEIA-ME-motor.md`, seção 6, e `LEIA-ME-agente.md`).
- As 4 conversas guardadas (13 falas do agente) foram lidas uma a uma contra a conta.

## 7. A validação pelo uso: o questionário

O texto está em [questionario-produtores.md](questionario-produtores.md): 12 perguntas, só para o produtor rural, anônimo, só para maiores de 18 anos. O fim do arquivo diz o que cada pergunta serve para provar.

**Estado em 2026-11-15: o questionário ainda não foi enviado e não há respostas.** Nenhum número de questionário aparece no projeto. Quando as respostas chegarem, entram aqui com a contagem ("7 de 10", e não porcentagem, se forem poucas), a data e de onde vieram.

## 8. O que não foi validado

- Nenhum teste em lavoura de verdade, e nenhum produtor ou agrônomo usou a ferramenta numa safra.
- A comparação com a estação e com a colheita só fecha em Rio Verde.
- O calor não foi comparado com nenhuma medida de perda: é uma contagem de dias.
- Os pontos do verde do satélite não foram conferidos em campo.
- A diferença entre a versão rápida e a versão final da chuva do satélite não foi medida.
