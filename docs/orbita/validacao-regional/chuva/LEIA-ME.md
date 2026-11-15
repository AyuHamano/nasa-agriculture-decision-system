# A chuva da NASA contra as estações do INMET em Goiás

> Gerado com IA (Claude), em 2026-11-15. O método foi escrito às 07h07, antes de baixar qualquer dado; os números da
> seção "Os resultados" são escritos pelo próprio programa (`calcular`), nenhum à mão.

## O resumo em 6 linhas
1. Goiás tem 26 estações automáticas do INMET nos arquivos de 2016 a 2025; 22 têm 5 janelas de fev a jun comparáveis ou mais e entram na conta (o DF tem 5, todas entram, à parte).
2. O satélite (IMERG) fica mais perto da estação que a chuva de modelo (PRECTOTCORR) em 16 das 22 estações de Goiás; a chuva de modelo, em 6. No DF, o satélite ganha nas 5.
3. A mediana do erro em Goiás: satélite 19,0%, chuva de modelo 23,7%. O satélite ganha, mas por pouco; em Rio Verde a distância era bem maior (12,7% contra 28,8% aqui).
4. A queda de 2021 aparece na região: a chuva de modelo dá, na mediana, 92% da estação até 2020 e 78% de 2021 em diante; caiu em 17 das 22 estações (mediana da queda, 16 pontos). Rio Verde é a queda mais forte (91% para 51%).
5. O satélite, no mesmo teste, fica perto de 100%: 103% até 2020 e 99% depois (caiu em 13 das 22, mediana de 6 pontos). A queda da chuva de modelo é maior que a do satélite.
6. A frase honesta: na região, o satélite acompanha melhor a estação e a chuva de modelo fica abaixo de 2021 em diante, mas "o satélite bate" vale com erro típico de 19%, não de 12%, e há estações em que ele erra muito (Monte Alegre de Goiás, Edéia).

## O método (fixado em 2026-11-15, às 07h07 de Brasília, antes de baixar a chuva da NASA e antes de ler qualquer estação)

1. **As estações.** Todas as estações automáticas do INMET cujo arquivo, nos zips anuais de 2016 a 2025 de
   https://portal.inmet.gov.br/dadoshistoricos (sem login), tem `_GO_` no nome. As do Distrito Federal (`_DF_`)
   entram à parte, com as mesmas contas, fora das medianas de Goiás. Código, nome e coordenadas vêm do cabeçalho do
   arquivo mais recente da estação no período; se o cabeçalho mudou com os anos, todas as versões ficam guardadas.
2. **O dia da estação** (a mesma regra da série da estação de Rio Verde guardada em `data/orbita/validacao/chuva/`): a hora do arquivo é UTC
   e marca o fim da hora medida; o dia é o de Brasília (das 04:00 UTC às 03:00 UTC do dia seguinte); vazio ou -9999 é
   hora sem dado, nunca zero; dia com menos de 20 horas com dado de chuva fica em branco.
3. **A chuva da NASA no ponto da estação**, pela NASA POWER, sem login: `IMERG_PRECTOT` (a chuva medida por satélite,
   GPM IMERG; só existe no horário UTC) e `PRECTOTCORR` (a chuva de modelo; no horário solar local, LST, como o motor
   usa). Um pedido por parâmetro e por estação, de 2016-01-01 a 2025-12-31.
4. **As janelas:** 1/fev a 30/jun de 2016 a 2025 (as safras 2015-16 a 2024-25). A regra do `validar.py` do motor:
   janela com mais de 10 dias em branco na estação não é comparada; na janela, cada fonte é somada só nos dias em que
   a estação tem dado (e a fonte também); a fonte precisa ter dado em todos esses dias menos 10, no máximo; a estação
   precisa ter somado mais de 0 mm. O número é o total da fonte em % do da estação. **Janela comparável** = as duas
   fontes têm o seu %; assim as duas são medidas nas mesmas janelas.
5. **Entra na conta** a estação com pelo menos 5 janelas comparáveis. A que tem menos fica na tabela, com o número de
   janelas, e não entra nas medidas.
6. **As medidas (decididas agora):**
   - (a) o erro médio de cada fonte em cada estação = a média, nas janelas comparáveis, de |% − 100|;
   - (b) em quantas estações o erro do satélite é menor que o da chuva de modelo (empate é contado à parte);
   - (c) a mediana, entre as estações, do erro do satélite e do erro da chuva de modelo;
   - (d) a chuva de modelo em % da estação, a média dos % das janelas de 2016 a 2020 e a das janelas de 2021 a 2025,
     em cada estação e na mediana entre as estações que têm ao menos uma janela no período; e, nas estações que têm os
     dois períodos, em quantas o % de 2021 em diante é menor que o de até 2020, e a mediana da diferença. A mesma conta
     sai para o satélite, como controle (se a queda for da estação, o satélite cai junto).
7. **Nada sai depois de ver o resultado.** A lista à parte é decidida só pelo dado da estação, nunca pela comparação
   com a NASA, e quem está nela **continua nas medidas** (quem decide se a janela vale é a regra dos dias em branco).
   As medidas saem também sem as estações da lista à parte, como segunda leitura. Vai à lista a estação que tiver,
   de 2016 a 2025:
   - um ano com 180 dias ou mais com dado e menos de 100 mm no ano (um ano "de zeros");
   - uma janela que passa na regra dos dias em branco com menos de 100 mm na estação;
   - 40 dias seguidos ou mais com 0,0 mm, com dado, entre 1/fev e 31/mar (o auge das chuvas);
   - um dia com mais de 200 mm;
   - coordenadas do cabeçalho que mudaram mais de 5 km entre os anos.
8. **A estação A025 (Rio Verde)** entra como qualquer outra, no ponto dela (não no ponto do projeto). Os números de
   antes (erro do satélite de 12,1%, chuva de modelo em 86% e 51%) foram feitos no ponto do projeto e com a safra
   2025-26; a diferença fica dita.

## Os resultados

<!-- tabelas: geradas pelo calcular -->
### As estações de Goiás

| código | nome | lat | lon | janelas comparáveis | entra? | erro do satélite (%) | erro do modelo (%) | mais perto | modelo em % da estação: até 2020 (n) | de 2021 em diante (n) | satélite: até 2020 | de 2021 em diante | lista à parte? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A002 | GOIANIA | -16,6428 | -49,2203 | 9 | sim | 13,3 | 22,8 | satélite | 86 (5) | 67 (4) | 108 | 93 | não |
| A003 | MORRINHOS | -17,7450 | -49,1017 | 10 | sim | 19,1 | 19,1 | modelo | 107 (5) | 85 (5) | 123 | 98 | não |
| A005 | PORANGATU | -13,3094 | -49,1175 | 6 | sim | 19,4 | 20,3 | satélite | 97 (2) | 104 (4) | 108 | 114 | sim |
| A011 | SAO SIMAO | -18,9692 | -50,6333 | 4 | não | 36,1 | 25,8 | -- | 77 (1) | 87 (3) | 97 | 147 | não |
| A012 | LUZIANIA | -16,2606 | -47,9669 | 6 | sim | 14,6 | 15,4 | satélite | 101 (4) | 99 (2) | 103 | 97 | não |
| A013 | ARAGARCAS | -15,9028 | -52,2453 | 6 | sim | 11,2 | 22,0 | satélite | 78 (4) | 77 (2) | 99 | 86 | não |
| A014 | GOIAS | -15,9397 | -50,1414 | 6 | sim | 19,5 | 20,5 | satélite | 95 (2) | 82 (4) | 99 | 105 | não |
| A015 | ITAPACI | -14,9797 | -49,5394 | 4 | não | 19,3 | 19,6 | -- | 93 (4) | -- (0) | 99 | -- | não |
| A016 | JATAI | -17,9236 | -51,7175 | 8 | sim | 8,7 | 25,4 | satélite | 81 (4) | 80 (4) | 103 | 107 | não |
| A017 | POSSE | -14,0892 | -46,3664 | 6 | sim | 18,9 | 23,6 | satélite | 86 (4) | 57 (2) | 87 | 70 | não |
| A022 | GOIANESIA | -15,2203 | -48,9900 | 1 | não | 9,0 | 29,9 | -- | -- (0) | 70 (1) | -- | 91 | não |
| A023 | CAIAPONIA | -16,9669 | -51,8175 | 6 | sim | 13,0 | 21,1 | satélite | 93 (4) | 75 (2) | 109 | 105 | não |
| A024 | ALTO PARAISO DE GOIAS | -14,1331 | -47,5233 | 4 | não | 24,4 | 34,4 | -- | 75 (2) | 122 (2) | 82 | 109 | não |
| A025 | RIO VERDE | -17,7853 | -50,9650 | 7 | sim | 12,7 | 28,8 | satélite | 91 (4) | 51 (3) | 103 | 83 | não |
| A026 | MINEIROS | -17,4547 | -52,6011 | 5 | sim | 25,5 | 29,9 | satélite | 70 (1) | 72 (4) | 71 | 93 | não |
| A027 | PARAUNA | -16,9625 | -50,4256 | 6 | sim | 18,1 | 16,0 | modelo | 95 (4) | 81 (2) | 110 | 103 | não |
| A028 | IPORA | -16,4231 | -51,1489 | 8 | sim | 19,3 | 26,8 | satélite | 86 (5) | 70 (3) | 102 | 97 | não |
| A029 | EDEIA | -17,3369 | -49,9147 | 5 | sim | 51,4 | 47,3 | modelo | 79 (2) | 130 (3) | 100 | 185 | não |
| A031 | SAO MIGUEL DO ARAGUAIA | -12,8206 | -50,3358 | 5 | sim | 8,4 | 23,9 | satélite | 74 (2) | 78 (3) | 85 | 102 | não |
| A032 | MONTE ALEGRE DE GOIAS | -13,2536 | -46,8903 | 6 | sim | 131,0 | 76,2 | modelo | 113 (3) | 230 (3) | 143 | 304 | sim |
| A033 | PIRES DO RIO | -17,3042 | -48,2842 | 7 | sim | 36,4 | 34,7 | modelo | 149 (2) | 78 (5) | 191 | 107 | não |
| A034 | CATALAO | -18,1547 | -47,9275 | 9 | sim | 20,0 | 31,8 | satélite | 84 (4) | 60 (5) | 94 | 86 | não |
| A035 | ITUMBIARA | -18,4097 | -49,1919 | 8 | sim | 19,9 | 26,6 | satélite | 101 (5) | 65 (3) | 118 | 102 | não |
| A036 | CRISTALINA | -16,7850 | -47,6131 | 8 | sim | 18,1 | 28,8 | satélite | 78 (5) | 59 (3) | 88 | 97 | não |
| A037 | SILVANIA | -16,6797 | -48,6181 | 7 | sim | 26,1 | 19,9 | modelo | 102 (5) | 85 (2) | 120 | 93 | não |
| A056 | CRISTALINA (FAZENDA SANTA MONICA) | -16,3994 | -47,6258 | 8 | sim | 18,1 | 21,5 | satélite | 94 (3) | 72 (5) | 98 | 99 | não |

**Goiás, todas as que entram (22 estações):**
- (b) o satélite fica mais perto da estação em **16 de 22**; a chuva de modelo em 6; empates: 0.
- (c) a mediana do erro: satélite **19,0%**, chuva de modelo **23,7%**.
- (d) a chuva de modelo em % da estação, na mediana: **92%** até 2020 (22 estações) e **78%** de 2021 em diante (22 estações). Nas 22 que têm os dois períodos, caiu em 17; a mediana da diferença é -16 pontos.
- (d, controle) o satélite em % da estação, na mediana: 103% até 2020 e 99% de 2021 em diante; caiu em 13 das 22; mediana da diferença -6 pontos.

**Goiás, sem as da lista à parte (20 estações):**
- (b) o satélite fica mais perto da estação em **15 de 20**; a chuva de modelo em 5; empates: 0.
- (c) a mediana do erro: satélite **18,5%**, chuva de modelo **23,7%**.
- (d) a chuva de modelo em % da estação, na mediana: **89%** até 2020 (20 estações) e **76%** de 2021 em diante (20 estações). Nas 20 que têm os dois períodos, caiu em 17; a mediana da diferença é -17 pontos.
- (d, controle) o satélite em % da estação, na mediana: 102% até 2020 e 98% de 2021 em diante; caiu em 13 das 20; mediana da diferença -7 pontos.

### As estações de Distrito Federal (à parte)

| código | nome | lat | lon | janelas comparáveis | entra? | erro do satélite (%) | erro do modelo (%) | mais perto | modelo em % da estação: até 2020 (n) | de 2021 em diante (n) | satélite: até 2020 | de 2021 em diante | lista à parte? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A001 | BRASILIA | -15,7894 | -47,9258 | 10 | sim | 17,1 | 24,4 | satélite | 90 (5) | 75 (5) | 94 | 95 | não |
| A042 | BRAZLANDIA | -15,5997 | -48,1311 | 7 | sim | 26,3 | 38,9 | satélite | 64 (3) | 59 (4) | 71 | 76 | não |
| A045 | AGUAS EMENDADAS | -15,5964 | -47,6258 | 10 | sim | 17,5 | 26,6 | satélite | 107 (5) | 79 (5) | 119 | 111 | não |
| A046 | GAMA (PONTE ALTA) | -15,9353 | -48,1375 | 9 | sim | 16,3 | 27,7 | satélite | 82 (4) | 64 (5) | 96 | 88 | não |
| A047 | PARANOA (COOPA-DF) | -16,0122 | -47,5575 | 9 | sim | 18,6 | 30,4 | satélite | 80 (4) | 61 (5) | 86 | 90 | não |

**Distrito Federal (à parte), todas as que entram (5 estações):**
- (b) o satélite fica mais perto da estação em **5 de 5**; a chuva de modelo em 0; empates: 0.
- (c) a mediana do erro: satélite **17,5%**, chuva de modelo **27,7%**.
- (d) a chuva de modelo em % da estação, na mediana: **82%** até 2020 (5 estações) e **64%** de 2021 em diante (5 estações). Nas 5 que têm os dois períodos, caiu em 5; a mediana da diferença é -18 pontos.
- (d, controle) o satélite em % da estação, na mediana: 94% até 2020 e 90% de 2021 em diante; caiu em 2 das 5; mediana da diferença 1 pontos.

**Distrito Federal (à parte), sem as da lista à parte (5 estações):**
- (b) o satélite fica mais perto da estação em **5 de 5**; a chuva de modelo em 0; empates: 0.
- (c) a mediana do erro: satélite **17,5%**, chuva de modelo **27,7%**.
- (d) a chuva de modelo em % da estação, na mediana: **82%** até 2020 (5 estações) e **64%** de 2021 em diante (5 estações). Nas 5 que têm os dois períodos, caiu em 5; a mediana da diferença é -18 pontos.
- (d, controle) o satélite em % da estação, na mediana: 94% até 2020 e 90% de 2021 em diante; caiu em 2 das 5; mediana da diferença 1 pontos.

### A lista à parte (dado estranho na estação; quem está aqui continua nas medidas)

| código | nome | UF | motivo | detalhe |
|---|---|---|---|---|
| A005 | PORANGATU | GO | mudou_de_lugar | o cabeçalho mudou 24.4 km entre os anos |
| A032 | MONTE ALEGRE DE GOIAS | GO | janela_baixa | fev-jun de 2016: 98.8 mm na estação (0 dias em branco) |
| A032 | MONTE ALEGRE DE GOIAS | GO | janela_baixa | fev-jun de 2023: 61.8 mm na estação (0 dias em branco) |

**Conferência:** a série diária de Rio Verde (A025) feita aqui e a de `data/orbita/validacao/chuva/inmet.csv` foram comparadas em 3653 dias de 2016 a 2025: 0 dias diferentes.
<!-- fim das tabelas -->

## O que cada número quer dizer, e os limites
- **Erro médio** de uma fonte numa estação: em cada janela de 1/fev a 30/jun, o total da fonte em % do total da estação (nos mesmos dias); a distância até 100%; a média dessas distâncias. 0% seria bater sempre.
- **Monte Alegre de Goiás (A032)** está na lista à parte (duas janelas com menos de 100 mm na estação, o que pede desconfiança do pluviômetro) e continua nas medidas, como o método mandou. Sem ela e sem Porangatu (A005, cujo cabeçalho mudou 24,4 km), as medidas quase não mudam (ver acima).
- **Edéia (A029)** tem o satélite em 185% da estação de 2021 em diante. Nenhuma regra fixada a pegou; ela fica nas medidas. Não se sabe se é a estação ou o satélite.
- **Morrinhos (A003)** é quase empate (19,1% e 19,1% arredondados); pela conta sem arredondar, a chuva de modelo fica à frente.
- As 4 estações de Goiás que não entram (menos de 5 janelas): São Simão (A011, 4), Itapaci (A015, 4), Goianésia (A022, 1) e Alto Paraíso de Goiás (A024, 4). Os números delas estão na tabela, fora das medidas.
- O dia do satélite é o dia UTC (a NASA POWER só entrega o IMERG assim); o da estação é o de Brasília; o da chuva de modelo, o da hora solar. São 3 horas de diferença no começo e no fim de cada janela de 150 dias, como na conta de antes.
- Uma estação é um ponto; o satélite é um quadrado de 0,1 grau (uns 11 km) e a chuva de modelo, um quadrado de 0,5 por 0,625 grau (uns 55 por 65 km). Pluviômetro também erra, quase sempre para menos.
- **Rio Verde, antes e aqui.** Antes: satélite com erro de 12,1% e chuva de modelo em 86% e 51% (no ponto do projeto, a 4,8 km da estação, com a safra 2025-26). Aqui, no ponto da estação e só de 2015-16 a 2024-25: 12,7%, e 91% e 51%. A série diária da estação feita aqui é igual à de antes nos 3.653 dias de 2016 a 2025.

## De onde veio cada dado
- **A chuva no chão:** INMET, dados históricos das estações automáticas, https://portal.inmet.gov.br/dadoshistoricos, um zip por ano em `https://portal.inmet.gov.br/uploads/dadoshistoricos/<ano>.zip`, sem login. Baixados em 2026-11-15, de 07h08 a 07h11 de Brasília (10h08 a 10h11 UTC), os 10 anos de 2016 a 2025; nenhum faltou. Dos zips saíram só os arquivos com `_GO_` e `_DF_` no nome (de 25 a 31 por ano).
- **A chuva do satélite:** NASA POWER, `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=IMERG_PRECTOT&community=AG&longitude=<lon>&latitude=<lat>&start=20160101&end=20251231&format=JSON&time-standard=UTC`, um pedido por estação, no ponto do cabeçalho mais recente dela.
- **A chuva de modelo:** o mesmo endereço com `parameters=PRECTOTCORR` e `time-standard=LST`. A resposta diz que a fonte é o MERRA-2.
- Os 62 pedidos à NASA POWER foram feitos em 2026-11-15, das 07h11min30s às 07h11min42s de Brasília.
- `fonte.json` guarda, para cada zip e cada resposta, o endereço exato, a hora, o tamanho e a assinatura (sha256). O `calcular` confere a assinatura de cada resposta antes de usar.

## O que tem nesta pasta
- `chuva_regional.py`: o programa (Python 3, só a biblioteca padrão).
- `estacoes.csv`: as 31 estações (26 de Goiás, 5 do DF), com código, nome, coordenadas, janelas comparáveis, se entra, os erros e os % por período.
- `janelas.csv`: cada estação em cada janela (dias em branco, totais das três fontes, os %).
- `diario-fev-jun.csv`: dia a dia, de 1/fev a 30/jun de 2016 a 2025, a chuva da estação, a do satélite e a de modelo.
- `lista-a-parte.csv`: as estações com dado estranho e o motivo.
- `resultado.json`: as medidas e a tabela, em formato de máquina.
- `fonte.json`: de onde veio cada dado.
- Fora do repositório, na pasta de cache que o programa cria (`~/.cache/orbita-rural/dados-regionais/`): `zips/` (os 10 zips, 976 MB), `inmet/` (os arquivos de GO e DF, 221 MB) e `power/` (as 62 respostas da NASA POWER).

## Como rodar de novo
De dentro desta pasta:
```
python3 -I chuva_regional.py testar     # as regras, com casos feitos à mão
python3 -I chuva_regional.py baixar     # o que já está no cache não baixa de novo (para baixar do zero, apague a pasta do cache e o fonte.json)
python3 -I chuva_regional.py calcular   # refaz os CSV, o resultado.json e a seção "Os resultados" deste arquivo
```
Conferido em 2026-11-15: os CSV foram apagados e refeitos pelo `calcular`, e saíram iguais, byte a byte.
