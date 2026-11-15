<!-- Gerado com IA (Claude) -->
# Órbita Rural · a validação

A conta do Órbita Rural foi conferida contra o que foi medido no chão: a colheita registrada pelo IBGE e a chuva das estações do INMET. Primeiro em Goiás inteiro (seções 1 e 2), depois, com mais detalhe, em Rio Verde (seções 3 a 7). Cada número diz de onde sai.

## 1. A prova de Goiás: a conta contra a colheita, em 20 municípios

**A pergunta.** Onde a conta aponta mais falta de água para o milho safrinha, a colheita foi menor?

**O método, em 4 linhas** (fixado antes de ver os resultados):

1. As cidades: os 20 municípios de Goiás com a maior área colhida de milho de 2ª safra no IBGE (média de 2016 a 2025), escolhidos pela regra, não à mão. Rio Verde, Jataí e Silvânia estão entre eles.
2. Os dados: a chuva do satélite GPM IMERG e a temperatura da NASA POWER no ponto da sede de cada município, pelas mesmas consultas do motor; a colheita, da Produção Agrícola Municipal do IBGE (SIDRA, tabela 839).
3. A conta: a do motor, sem mudar nada (soja, milho safrinha e pousio; terra média; o calendário de costume), nas 10 safras de 2015-16 a 2024-25. O número de cada safra é a falta de água do milho, em % do que ele pediu.
4. A medida: a correlação de postos (Spearman) entre a falta de água e o rendimento, em cada cidade, em todas juntas e ano a ano. Negativa quer dizer: mais falta de água, menos colheita.

**Os números.**

| a medida | o resultado |
|---|---|
| cidades em que a conta foi no sentido da colheita (correlação negativa) | **20 de 20** |
| a correlação do meio das 20 cidades | −0,50 (de −0,84, em Paraúna, a −0,05, em Santa Helena de Goiás) |
| cidades em que a pior colheita (a de 2015-16, nas 20) está entre as 3 safras de maior falta de água | 16 de 20 |
| todas as cidades juntas (200 cidade-safras, o rendimento em % da mediana de cada cidade) | −0,44 (valor-p de 0,017, um lado, embaralhando os anos juntos em todas as cidades) |
| ano a ano, na média da região (10 safras) | **−0,72** (valor-p de 0,011, um lado) |

A região, safra por safra:

| safra | falta de água média do milho (%) | rendimento médio (% da mediana de cada cidade) |
|---|---|---|
| 2015-16 | 53,3 | 54,7 |
| 2016-17 | 30,9 | 93,7 |
| 2017-18 | 35,6 | 95,8 |
| 2018-19 | 24,8 | 119,6 |
| 2019-20 | 35,2 | 111,9 |
| 2020-21 | 50,3 | 83,0 |
| 2021-22 | 54,8 | 90,1 |
| 2022-23 | 42,1 | 109,9 |
| 2023-24 | 42,9 | 93,9 |
| 2024-25 | 36,4 | 112,1 |

A safra de menor falta de água na conta (2018-19) é a de melhor colheita, e a pior colheita da região (2015-16) é a 2ª de maior falta. Duas conferências a mais, feitas com o mesmo programa: sem a safra 2015-16, a conta vai no sentido da colheita em 17 de 20 cidades (−0,65 ano a ano); com a soja plantada 15 dias mais tarde, em 19 de 20 (−0,68 ano a ano).

De onde sai: [validacao-regional/colheita/LEIA-ME.md](validacao-regional/colheita/LEIA-ME.md) (a tabela das 20 cidades, as escolhas do método e os arquivos de resultado).

## 2. A prova de Goiás: a chuva do satélite contra 27 estações

**A pergunta.** A chuva que a conta usa (a do satélite) fica perto da chuva medida no chão?

**O método, em 4 linhas** (fixado antes de baixar os dados):

1. As estações: todas as estações automáticas do INMET de Goiás (26) e do Distrito Federal (5) nos arquivos de 2016 a 2025. Entram na conta as que têm 5 ou mais janelas comparáveis: 22 em Goiás e 5 no Distrito Federal.
2. A janela: de 1 de fevereiro a 30 de junho (a 2ª safra) de cada ano.
3. As duas chuvas da NASA no ponto de cada estação: a do satélite (GPM IMERG) e a de modelo (`PRECTOTCORR`, da NASA POWER).
4. A medida: o erro médio de cada chuva contra a estação (a distância entre o total da fonte e o da estação na janela, em % da estação).

**Os números.**

| | o satélite mais perto da estação | erro do meio: satélite | erro do meio: chuva de modelo |
|---|---|---|---|
| Goiás (22 estações) | **16 de 22** | 19,0% | 23,7% |
| Distrito Federal (5 estações) | **5 de 5** | 17,5% | 27,7% |
| as duas juntas | **21 de 27** | | |

Nas três cidades do aplicativo: em Rio Verde (estação A025), o erro do satélite foi de 12,7% e o da chuva de modelo, 28,8%; em Jataí (A016), 8,7% e 25,4%; em Silvânia (A037), 26,1% e 19,9%. O teste também mostra por que a conta usa o satélite: de 2021 em diante a chuva de modelo passou a dar, na mediana de Goiás, 78% da chuva da estação (eram 92% até 2020), enquanto o satélite ficou em 99% (eram 103%).

De onde sai: [validacao-regional/chuva/LEIA-ME.md](validacao-regional/chuva/LEIA-ME.md) (a tabela das estações, as regras e os arquivos de resultado).

**Como refazer os dois testes:** [validacao-regional/LEIA-ME.md](validacao-regional/LEIA-ME.md).

## 3. Rio Verde: a chuva do satélite contra a estação

Como conferir de novo as seções 3 e 4: de dentro de `backend/`, `python3 -m orbita.validar` (rodado em 2026-11-15; os números abaixo são os da saída).

**O que foi comparado.** A soma da chuva de 1 de fevereiro a 30 de junho, em cada safra, em quatro fontes, contra a chuva medida pela estação automática A025 do INMET em Rio Verde, que fica a 4,79 km do ponto do projeto. Das 10 safras de 2015-16 a 2024-25, 8 servem para comparar (a estação ficou fora do ar de 2019-11-26 a 2021-06-10).

| fonte da chuva | o que é | erro médio contra a estação (8 safras) |
|---|---|---|
| GPM IMERG | a chuva estimada por satélites da NASA | 12,1% |
| CHIRPS | satélite ajustado com pluviômetros | 17,6% |
| ERA5 | modelo (reanálise europeia) | 26,7% |
| NASA POWER, `PRECTOTCORR` | a chuva de modelo da NASA POWER | 33,2% |

A chuva de modelo da NASA POWER deu, na janela, em média 86% da chuva da estação nas 4 safras comparadas até 2020, e 51% nas 4 de 2021 em diante. No ano de 2025, 678,4 mm no modelo contra 1.548,0 mm na estação. **A decisão:** a conta usa a chuva do satélite GPM IMERG; a temperatura é a da NASA POWER.

De onde sai: `orbita.validar`, seção 2, e `data/orbita/validacao/LEIA-ME-da-validacao-cruzada.md`. O erro médio é a média, nas safras comparadas, da distância entre o total da fonte e o da estação na janela, em % da estação.

## 4. Rio Verde: a conta contra a colheita do IBGE

**O que foi comparado.** A falta de água do milho de 2ª safra na conta (em % do que o milho pediu; soja, milho e pousio; terra média; chuva do IMERG) contra o rendimento do milho de 2ª safra em Rio Verde na Produção Agrícola Municipal do IBGE, nas 10 safras.

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

- **As 2 safras de maior falta de água na conta (2021-22 e 2015-16) são as 2 piores colheitas no IBGE.**
- A régua de colheita ruim usada pelo motor: rendimento abaixo de 80% da mediana das 10 safras (mediana de 6.725 kg/ha; 80% são 5.380 kg/ha). É uma escolha do projeto, não do IBGE.
- A correlação de postos entre a falta de água e o rendimento: −0,52 com a chuva do IMERG (CHIRPS −0,42; ERA5 −0,41; NASA POWER −0,26). É o mesmo −0,52 que Rio Verde tem no teste dos 20 municípios (seção 1).

De onde sai: `orbita.validar`, seção 4, e `data/orbita/validacao/ibge/rendimento_rio_verde.csv`. A conta mede a falta de água, não a colheita em sacas: o rendimento também depende de praga, adubo, semente e data de plantio.

## 5. O verde do satélite contra o calendário

**O que foi comparado.** Os dias seguidos sem planta viva que o calendário da rotação com pousio dá (122) contra os dias seguidos sem planta verde que o satélite MODIS viu em 6 pontos de lavoura perto de cada cidade.

| cidade | mediana do satélite (dias) | de quanto a quanto | medidas | o calendário | leitura |
|---|---|---|---|---|---|
| Rio Verde | 96 | 16 a 160 | 36 | 122 | dentro da faixa |
| Jataí | 80 | 0 a 128 | 30 | 122 | dentro da faixa |
| Silvânia | 96 | 16 a 192 | 35 | 122 | dentro da faixa |

De onde sai: `python3 -m orbita.perguntar --cidade <cidade> --verde`, `backend/orbita/LEIA-ME-motor.md` e `data/orbita/ndvi/LEIA-ME.md`. Os pontos foram escolhidos no mapa, em área de lavoura; o satélite mede o verde das folhas (não vê a palha).

## 6. A chuva dos últimos dias (o painel "Minha lavoura hoje")

O painel usa a chuva do satélite GPM IMERG de cada dia, em mm, até a véspera (`data/orbita/chuva-do-dia/`). A regra que soma o dia foi conferida em Rio Verde: de 01/09 a 30/10/2026 (60 dias, todos com dado), a soma deu 353,0 mm numa versão do dado (Early) e 347,4 mm na outra (Late), os mesmos totais de uma leitura independente do mesmo satélite, e os dias saíram iguais, um a um. Nesses 60 dias o satélite somou 26% a mais que a estação do INMET de Rio Verde. O painel mostra, ao lado da água de hoje, o mesmo dia do ano normal e do pior ano, e cada indicador traz a data do dado.

Na consulta de 2026-11-15, o painel de Rio Verde dava 66,0 mm de água ao alcance da planta em 14/11/2026 e o aviso de sede para 7 dias (`python3 -m orbita.perguntar --lavoura-hoje`).

De onde sai: `data/orbita/chuva-do-dia/LEIA-ME.md` e `backend/orbita/LEIA-ME-motor.md`.

## 7. A safra ruim, dia a dia

O replay da safra 2015-16 em Rio Verde (`python3 -m orbita.perguntar --replay 2015-16`) mostra a conta de cada dia: o milho entra em 2016-02-10; a sede começa em 2016-04-04 e dura 60 dias seguidos; em 2016-04-24 a água que a planta alcança chega a 0,1 mm; foram 19 dias de calor forte na fase crítica do milho (máxima acima de 33 °C); faltaram 220,6 mm, 49,6% do pedido. São valores da conta, alimentada pela chuva do satélite. No IBGE, essa foi a pior colheita de milho de 2ª safra de Rio Verde nas 10 safras (3.300 kg/ha, contra a mediana de 6.725).

## 8. A conferência do próprio programa

- Mais de 500 testes automáticos passam (`python3 -m unittest`, de dentro de `backend/`; rodado em 2026-11-15).
- A conta da evaporação foi testada com os Exemplos 8 e 20 do manual FAO-56 e ficou 6,6% acima da evaporação do FAO que o Open-Meteo entrega (`orbita.validar`, seção 3).
- O código do motor e do assistente foi revisado por outro modelo de IA em pontos marcados; os defeitos achados foram consertados, cada um com teste (`backend/orbita/LEIA-ME-motor.md` e `LEIA-ME-agente.md`).
- As 6 conversas guardadas do assistente (16 falas, 10 com o texto da IA e 6 com frases prontas), gravadas em 2026-11-15, foram lidas uma a uma contra a conta (`backend/orbita/LEIA-ME-agente.md`).

## 9. A validação pelo uso: o questionário

O texto está em [questionario-produtores.md](questionario-produtores.md): 12 perguntas, só para o produtor rural, anônimo, só para maiores de 18 anos. O fim do arquivo diz o que cada pergunta serve para provar. As respostas entram aqui com a contagem, a data e de onde vieram.
