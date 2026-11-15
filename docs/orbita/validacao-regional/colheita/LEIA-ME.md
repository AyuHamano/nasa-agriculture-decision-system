# O teste regional: a conta do motor acompanha a colheita do milho safrinha em Goiás?

> Gerado com IA (Claude) em 2026-11-15. Todo número das tabelas sai do programa `regional.py`, que lê os dados
> baixados e escreve as tabelas entre as marcas `TABELA` e `FIM` deste arquivo. Nenhum número foi digitado à mão.

**O resumo, em 6 linhas**

- **Vale para a região, no sentido certo.** Nas 20 cidades de maior área de milho safrinha de Goiás (escolhidas pela regra, não à mão), a correlação entre a falta de água da conta e a colheita do IBGE deu negativa em **todas as 20** (a do meio: −0,50; de −0,84 em Paraúna a −0,05 em Santa Helena de Goiás).
- Pelo teste do sinal, 20 de 20 só pelo acaso teria chance de 1 em 1.048.576 (p < 0,001).
- Todas as cidades juntas (200 cidade-safras, o rendimento em % da mediana de cada cidade): −0,44, valor-p de 0,017 (um lado) com o embaralhar que respeita que as cidades dividem o tempo de cada ano.
- Ano a ano, na média da região: −0,72 nas 10 safras (valor-p 0,011, um lado). A pior safra da região, 2015-16, é a 2ª de maior falta de água média.
- **A ressalva grande:** a pior safra é a mesma (2015-16) nas 20 cidades, e as cidades são vizinhas: a prova forte é de 10 anos da região, não de 200 casos soltos. Sem 2015-16 (conta feita depois de ver os números), ainda dão negativas 17 de 20, e o ano a ano dá −0,65.
- Com a soja 15 dias mais tarde (só checagem), o resultado da região quase não muda (19 de 20 negativas; −0,40 juntas; −0,68 ano a ano), mas no sudoeste ele some em Jataí, Chapadão do Céu e Serranópolis (de −0,30, −0,62 e −0,48 para perto de zero).

## 1. A pergunta e o método (fixado antes de ver os resultados)

Até aqui, a conta do motor (a falta de água do milho safrinha, dia a dia, com a chuva do satélite GPM IMERG e a
temperatura da NASA POWER) tinha sido comparada com a colheita do IBGE em 3 cidades escolhidas à mão. Este teste
pergunta se isso vale para a região. O método foi fixado antes da conta e não mudou depois de ver os números:

1. **As cidades:** os 20 municípios de Goiás com a maior área colhida de milho 2ª safra no IBGE (média de 2016 a
   2025, SIDRA, tabela 839, categoria 114254 = "Milho (em grão) - 2ª safra"), entre os que têm rendimento nos 10
   anos. Rio Verde, Jataí e Silvânia estão na lista que a regra deu; não houve cidade à parte.
2. **O ponto de cada cidade:** a sede do município na Base de Localidades do IBGE de 2022 (a categoria "Sede
   Municipal", com latitude e longitude). Por isso o ponto das três cidades de antes mudou um pouco (seção 5).
3. **Os dados:** a NASA POWER diária, sem login, pelas mesmas consultas do `data/orbita/cidades/baixar_cidade.py`
   do motor: `PRECTOTCORR,T2M_MAX,T2M_MIN` no dia local (a chuva de modelo vem junto, mas não entra na conta) e
   `IMERG_PRECTOT` no dia UTC, de 2014-07-01 a 2025-12-31. A colheita: uma consulta ao SIDRA com todos os
   municípios de Goiás. Uma consulta por vez, com 2 segundos de pausa.
4. **A conta:** a do motor, sem mudar nada: a rotação de hoje (soja, milho safrinha, pousio), terra média, o
   calendário de costume (soja em 15/10, milho em 10/02) e os parâmetros de hoje, a chuva IMERG, as 10 safras de
   2015-16 a 2024-25. O número de cada safra é a falta de água do milho em % do que ele pediu (o
   `falta_relativa_pct`). O programa chama as funções do próprio motor (`clima.serie_do_json`, `balanco.simular`,
   `balanco.numeros_por_safra`, `validar.spearman`); a única parte copiada é a troca da chuva pela do IMERG (cortar
   os dias sem dado do fim e parar se houver buraco no meio), e a conferência da seção 5 mostra que dá igual.
5. **As medidas:** (a) por cidade, a correlação de postos (Spearman) entre a falta e o rendimento, e se a safra de
   pior rendimento está entre as 3 de maior falta; (b) quantas cidades têm correlação negativa, com o teste do
   sinal; (c) todas as cidades juntas: o rendimento de cada safra em % da mediana da própria cidade contra a falta,
   a correlação de postos sobre as 200 cidade-safras e o valor-p por permutação; (d) ano a ano: a média da falta
   das cidades em cada safra contra a média do rendimento relativo.
6. **A checagem de sensibilidade** (seção 4): a mesma conta com a soja plantada 15 dias mais tarde (30/10). O
   calendário inteiro anda junto, como o motor faz com a data do produtor: o milho passa a 25/02.

**As escolhas de detalhe, fixadas antes de rodar a conta** (estão no código desde a primeira
versão):
- Correlação negativa = a conta no sentido certo (mais falta, menos colheita). Na pior safra, empate no rendimento
  fica com a mais antiga, como no motor; o posto na falta é 1 para a safra de maior falta.
- O teste do sinal: sob o acaso, cada cidade tem metade de chance de dar negativa. O valor-p principal é o de um
  lado (a chance de dar tantas ou mais negativas), porque a pergunta tem sentido; o de dois lados vai ao lado.
- O valor-p da medida (c): **o principal embaralha a ordem das safras da falta de água do mesmo jeito em todas as
  cidades**, 10.000 vezes. As cidades vizinhas dividem o tempo de cada ano: se a seca de um ano pega todas, as 200
  cidade-safras não são 200 casos soltos, e embaralhar cada cidade por si daria um valor-p pequeno demais. O
  embaralhar de cada cidade por si vai ao lado, só para mostrar a diferença. A semente é 20261115.
- O valor-p da medida (d): a ordem das 10 safras embaralhada 10.000 vezes.
- O valor-p conta o resultado observado como uma das permutações ((quantas + 1) / (10.000 + 1)).

## 2. As cidades e a medida (a)

<!-- TABELA:cidades -->
| # | município | área colhida média 2016-2025 (ha) | correlação (falta × rendimento) | pior safra no IBGE (kg/ha) | posto dela na falta (1 = maior falta) | entre as 3 de maior falta? |
|---|---|---|---|---|---|---|
| 1 | Rio Verde | 303.150 | −0,52 | 2015-16 (3.300) | 2º | sim |
| 2 | Jataí | 236.700 | −0,30 | 2015-16 (4.200) | 6º | não |
| 3 | Montividiu | 111.320 | −0,77 | 2015-16 (3.600) | 2º | sim |
| 4 | Mineiros | 88.200 | −0,19 | 2015-16 (4.000) | 5º | não |
| 5 | Cristalina | 76.041 | −0,48 | 2015-16 (3.517) | 1º | sim |
| 6 | Chapadão do Céu | 60.950 | −0,62 | 2015-16 (4.200) | 3º | sim |
| 7 | Paraúna | 51.250 | −0,84 | 2015-16 (2.400) | 1º | sim |
| 8 | Caiapônia | 44.450 | −0,25 | 2015-16 (4.020) | 2º | sim |
| 9 | Santa Helena de Goiás | 40.790 | −0,05 | 2015-16 (1.800) | 2º | sim |
| 10 | Perolândia | 34.000 | −0,18 | 2015-16 (4.000) | 5º | não |
| 11 | Bom Jesus de Goiás | 33.993 | −0,61 | 2015-16 (1.600) | 1º | sim |
| 12 | Silvânia | 31.700 | −0,81 | 2015-16 (5.000) | 2º | sim |
| 13 | Goiatuba | 27.990 | −0,65 | 2015-16 (1.500) | 1º | sim |
| 14 | Acreúna | 23.640 | −0,11 | 2015-16 (2.400) | 2º | sim |
| 15 | Serranópolis | 22.700 | −0,48 | 2015-16 (4.000) | 5º | não |
| 16 | Água Fria de Goiás | 19.205 | −0,23 | 2015-16 (3.000) | 1º | sim |
| 17 | Doverlândia | 17.220 | −0,38 | 2015-16 (3.900) | 2º | sim |
| 18 | Luziânia | 15.992 | −0,60 | 2015-16 (4.800) | 2º | sim |
| 19 | Ipameri | 14.906 | −0,66 | 2015-16 (2.213) | 1º | sim |
| 20 | Itumbiara | 14.765 | −0,65 | 2015-16 (1.922) | 1º | sim |
<!-- FIM:cidades -->

As coordenadas de cada sede e de onde vieram: `dados/cidades.csv`. A falta e o rendimento de cada safra:
`resultados/cidade-safra-principal.csv`.

Como ler:
- Das 246 cidades de Goiás que aparecem na tabela, 84 têm rendimento do milho 2ª safra nos 10 anos; as 20 escolhidas
  vão de 303.150 ha (Rio Verde) a 14.765 ha de área colhida média. Rio Verde, Jataí e Silvânia estão na lista (1ª,
  2ª e 12ª): não houve cidade à parte.
- **A correlação deu negativa nas 20.** Em 9 delas fica entre −0,60 e −0,84; em 4 fica entre 0 e −0,20 (Santa
  Helena de Goiás, Acreúna, Perolândia e Mineiros): ali a conta quase não acompanha a colheita.
- **A pior safra do IBGE é 2015-16 em todas as 20 cidades.** Ela está entre as 3 de maior falta de água em 16; nas
  outras 4 (Jataí, Mineiros, Perolândia e Serranópolis, no sudoeste) ela fica em 5º ou 6º lugar: a conta dá a ela
  falta de água média, e a colheita caiu muito.

## 3. As medidas (b), (c) e (d)

<!-- TABELA:medidas -->
| medida | o número |
|---|---|
| (a) a correlação do meio das 20 cidades (a mediana) | −0,50 |
| (a) cidades em que a pior safra está entre as 3 de maior falta | 16 de 20 |
| (b) cidades com correlação negativa (a conta no sentido certo) | 20 de 20 |
| (b) teste do sinal: a chance de 20 ou mais de 20 só pelo acaso | menor que 0,001 (dos dois lados: menor que 0,001) |
| (c) a correlação de postos sobre as 200 cidade-safras (rendimento em % da mediana da cidade) | −0,44 |
| (c) valor-p, a mesma ordem embaralhada em todas as cidades (o principal), 10.000 vezes | um lado 0,017; dois lados 0,037 |
| (c) valor-p, cada cidade embaralhada por si (mostrado ao lado) | um lado menor que 0,001; dois lados menor que 0,001 |
| (d) a correlação de postos ano a ano (a média das cidades, 10 safras) | −0,72 |
| (d) valor-p por permutação (10.000 vezes) | um lado 0,011; dois lados 0,024 |
| (d) a pior safra da região (o menor rendimento relativo médio) e o posto dela na falta média | 2015-16, 2º de 10 |
<!-- FIM:medidas -->

A visão regional, safra por safra (a medida d):

<!-- TABELA:regional -->
| safra | falta de água média do milho (%) | rendimento relativo médio (% da mediana da cidade) |
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
<!-- FIM:regional -->

Como ler:
- **(b)** 20 de 20 no sentido certo. Se a conta não tivesse nada a ver com a colheita, cada cidade teria metade de
  chance de dar negativa; 20 de 20 só pelo acaso tem chance de 1 em 1.048.576. Mas as cidades não são
  independentes (dividem o tempo de cada ano), e por isso este número exagera a certeza; as medidas (c) e (d) cuidam
  disso.
- **(c)** −0,44 sobre as 200 cidade-safras. Com o embaralhar principal (a mesma ordem das safras em todas as
  cidades, que respeita o ano em comum), a chance de dar −0,44 ou menos pelo acaso é de 1,7% (3,7% contando os dois
  lados). Embaralhando cada cidade por si o valor-p cai para menos de 0,001 (1 em 10.001, o menor que dá para ver
  com 10.000 vezes): é a conta que faz de conta que são 200 casos soltos, e por isso não é a principal.
- **(d)** −0,72 ano a ano. Os anos de falta alta e colheita baixa: 2015-16 (53,3% de falta, 54,7% da colheita
  normal). Os que não batem tão bem: 2021-22 tem a maior falta média (54,8%) e a colheita ficou em 90,1%; 2020-21,
  50,3% de falta e 83,0% de colheita. O ano de menor falta (2018-19, 24,8%) é o de melhor colheita (119,6%).

**Uma conferência feita depois de ver os números (não é do método fixado):** como a pior safra é a mesma nas 20
cidades, a conta foi refeita sem 2015-16, para ver quanto do resultado vem só dela.

<!-- TABELA:sem-2015-16 -->
| sem a safra 2015-16 (9 safras) | o número |
|---|---|
| cidades com correlação negativa | 17 de 20 (teste do sinal, um lado: 0,001) |
| a correlação do meio das cidades (a mediana) | −0,44 |
| (d) ano a ano, 9 safras | −0,65 (valor-p de um lado: 0,034) |
<!-- FIM:sem-2015-16 -->

Sem 2015-16 o resultado enfraquece, mas fica no mesmo sentido. Ela não troca o resultado principal.

## 4. A checagem de sensibilidade: a soja 15 dias mais tarde (só para conferir, não troca o resultado)

<!-- TABELA:medidas-sensibilidade -->
| medida | o número |
|---|---|
| (a) a correlação do meio das 20 cidades (a mediana) | −0,38 |
| (a) cidades em que a pior safra está entre as 3 de maior falta | 15 de 20 |
| (b) cidades com correlação negativa (a conta no sentido certo) | 19 de 20 |
| (b) teste do sinal: a chance de 19 ou mais de 20 só pelo acaso | menor que 0,001 (dos dois lados: menor que 0,001) |
| (c) a correlação de postos sobre as 200 cidade-safras (rendimento em % da mediana da cidade) | −0,40 |
| (c) valor-p, a mesma ordem embaralhada em todas as cidades (o principal), 10.000 vezes | um lado 0,018; dois lados 0,045 |
| (c) valor-p, cada cidade embaralhada por si (mostrado ao lado) | um lado menor que 0,001; dois lados menor que 0,001 |
| (d) a correlação de postos ano a ano (a média das cidades, 10 safras) | −0,68 |
| (d) valor-p por permutação (10.000 vezes) | um lado 0,018; dois lados 0,036 |
| (d) a pior safra da região (o menor rendimento relativo médio) e o posto dela na falta média | 2015-16, 3º de 10 |
<!-- FIM:medidas-sensibilidade -->

<!-- TABELA:cidades-sensibilidade -->
| # | município | área colhida média 2016-2025 (ha) | correlação (falta × rendimento) | pior safra no IBGE (kg/ha) | posto dela na falta (1 = maior falta) | entre as 3 de maior falta? |
|---|---|---|---|---|---|---|
| 1 | Rio Verde | 303.150 | −0,50 | 2015-16 (3.300) | 3º | sim |
| 2 | Jataí | 236.700 | −0,01 | 2015-16 (4.200) | 9º | não |
| 3 | Montividiu | 111.320 | −0,74 | 2015-16 (3.600) | 3º | sim |
| 4 | Mineiros | 88.200 | −0,06 | 2015-16 (4.000) | 7º | não |
| 5 | Cristalina | 76.041 | −0,43 | 2015-16 (3.517) | 1º | sim |
| 6 | Chapadão do Céu | 60.950 | −0,01 | 2015-16 (4.200) | 7º | não |
| 7 | Paraúna | 51.250 | −0,85 | 2015-16 (2.400) | 1º | sim |
| 8 | Caiapônia | 44.450 | −0,32 | 2015-16 (4.020) | 2º | sim |
| 9 | Santa Helena de Goiás | 40.790 | −0,12 | 2015-16 (1.800) | 3º | sim |
| 10 | Perolândia | 34.000 | +0,03 | 2015-16 (4.000) | 8º | não |
| 11 | Bom Jesus de Goiás | 33.993 | −0,74 | 2015-16 (1.600) | 2º | sim |
| 12 | Silvânia | 31.700 | −0,78 | 2015-16 (5.000) | 2º | sim |
| 13 | Goiatuba | 27.990 | −0,73 | 2015-16 (1.500) | 1º | sim |
| 14 | Acreúna | 23.640 | −0,33 | 2015-16 (2.400) | 1º | sim |
| 15 | Serranópolis | 22.700 | −0,07 | 2015-16 (4.000) | 9º | não |
| 16 | Água Fria de Goiás | 19.205 | −0,16 | 2015-16 (3.000) | 1º | sim |
| 17 | Doverlândia | 17.220 | −0,30 | 2015-16 (3.900) | 2º | sim |
| 18 | Luziânia | 15.992 | −0,60 | 2015-16 (4.800) | 1º | sim |
| 19 | Ipameri | 14.906 | −0,79 | 2015-16 (2.213) | 1º | sim |
| 20 | Itumbiara | 14.765 | −0,73 | 2015-16 (1.922) | 3º | sim |
<!-- FIM:cidades-sensibilidade -->

<!-- TABELA:regional-sensibilidade -->
| safra | falta de água média do milho (%) | rendimento relativo médio (% da mediana da cidade) |
|---|---|---|
| 2015-16 | 58,4 | 54,7 |
| 2016-17 | 41,6 | 93,7 |
| 2017-18 | 50,1 | 95,8 |
| 2018-19 | 40,9 | 119,6 |
| 2019-20 | 47,5 | 111,9 |
| 2020-21 | 56,5 | 83,0 |
| 2021-22 | 62,7 | 90,1 |
| 2022-23 | 50,3 | 109,9 |
| 2023-24 | 59,3 | 93,9 |
| 2024-25 | 44,4 | 112,1 |
<!-- FIM:regional-sensibilidade -->

Como ler (é checagem, não resultado): com a soja em 30/10 e o milho em 25/02, a região quase não muda: 19 de 20
negativas (só Perolândia vira +0,03), −0,40 com todas juntas (valor-p 0,019, um lado) e −0,68 ano a ano (0,019).
A pior safra entre as 3 de maior falta: 15 de 20. **O que muda é o sudoeste:** Jataí (−0,30 para −0,01), Chapadão do
Céu (−0,62 para −0,01), Serranópolis (−0,48 para −0,07) e Mineiros (−0,19 para −0,06); nelas 2015-16 cai para o 7º
a 9º lugar na falta. Ou seja: nessas cidades a resposta depende da data de plantio, que a conta não sabe (ela usa
as mesmas datas em todos os anos e em todas as cidades). Nas outras 16, a correlação muda no máximo 0,22 (Acreúna, que fica mais forte: de −0,11 para −0,33).

## 5. As três cidades de antes

<!-- TABELA:as-tres -->
| cidade | antes deste teste | nos dados guardados do motor, a conta de hoje | neste teste (a sede do IBGE) | com a soja 15 dias depois | a conta deste programa = a do motor? |
|---|---|---|---|---|---|
| Rio Verde | −0,52 | −0,52 | −0,52 | −0,50 | sim, nas 10 safras |
| Jataí | −0,28 | −0,30 | −0,30 | −0,01 | sim, nas 10 safras |
| Silvânia | −0,81 | −0,81 | −0,81 | −0,78 | sim, nas 10 safras |
<!-- FIM:as-tres -->

- Este programa, rodado nos dados que o motor já guarda, dá o mesmo número que a resposta do motor nas 10 safras
  das três cidades (o `falta_relativa_pct`, com uma casa).
- O ponto da sede do IBGE fica a poucos quilômetros do ponto que o motor usa (Rio Verde: −17,7853, −50,9081 contra
  −17,79, −50,92; Jataí: −17,8858, −51,7240 contra −17,88, −51,71; Silvânia: −16,6592, −48,6074 contra −16,66,
  −48,61), e as correlações saíram iguais às dos dados guardados.
- **Jataí dá −0,30 na conta de hoje, e não −0,28, o número anotado antes deste teste.** O −0,30 sai tanto dos dados guardados do
  motor quanto dos baixados agora; com a falta arredondada a uma casa, dá −0,29. De onde veio o −0,28 (talvez de uma
  versão anterior do motor) não foi investigado.

## 6. O que este teste não diz

- **Não são 200 provas independentes.** As cidades são vizinhas e a pior safra é a mesma em todas: a evidência
  forte é a de 10 anos da região. Por isso o valor-p principal da medida (c) é o que embaralha os anos juntos.
- **Uma safra pesa muito.** 2015-16 é a pior em todas as cidades; sem ela o resultado fica mais fraco (17 de 20
  negativas; −0,65 ano a ano).
- **Correlação não é previsão.** A conta põe as safras na ordem certa com frequência, mas erra anos (2021-22 e
  2020-21 com falta alta e colheita só um pouco abaixo do normal). O rendimento do IBGE também depende de praga,
  geada, semente, adubo e da data de plantio de verdade, e sobe com o tempo pela tecnologia; nada disso foi tirado
  (não estava no método).
- **O ponto é a sede, não as lavouras.** A chuva é de um quadrado de uns 10 km (IMERG) e a temperatura de um de uns
  50 km (NASA POWER); o rendimento é do município inteiro.
- **Só as cidades grandes.** A regra pega as 20 de maior área entre as 84 com os 10 anos de dado; não diz nada das
  cidades pequenas nem de fora de Goiás.
- **Uma conta só:** terra média, a chuva IMERG, o calendário de costume. Outras terras e outras chuvas não foram
  testadas aqui. A checagem de sensibilidade mostra que, no sudoeste, a data de plantio muda o resultado.

## 7. As fontes e como rodar de novo

O endereço e a hora de cada consulta estão em `dados/consultas.json`; as respostas cruas, em `dados/bruto/`
(comprimidas). As sedes de Goiás, na `dados/sedes-goias-ibge-2022.csv` (o arquivo do IBGE tem o Brasil inteiro;
fica só Goiás, com o sha256 do arquivo baixado no `consultas.json`). Neste repositório ficam o `consultas.json`, o
`cidades.csv` e os resultados; as respostas cruas e a lista das sedes voltam com o `baixar`.

- SIDRA, tabela 839, milho 2ª safra, Goiás: `https://apisidra.ibge.gov.br/values/t/839/n6/in%20n3%2052/v/216,112/p/2016,2017,2018,2019,2020,2021,2022,2023,2024,2025/c81/114254`
- IBGE, Base de Localidades 2022: `https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/localidades/Localidades_do_Brasil/2022/Localidades_Brasil_shp.zip`
- NASA POWER, por cidade, duas consultas: `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR,T2M_MAX,T2M_MIN&community=AG&longitude=<lon>&latitude=<lat>&start=20140701&end=20251231&format=JSON&time-standard=LST`
  e o mesmo com `parameters=IMERG_PRECTOT` e `time-standard=UTC`.

Como rodar (Python 3, só a biblioteca padrão; o motor é o deste repositório, em `backend/`, ou o do
caminho na variável `ORBITA_REPO`):

```bash
cd docs/orbita/validacao-regional/colheita
python3 -I regional.py baixar     # baixa tudo de novo (uns 3 minutos)
python3 -I regional.py calcular   # a conta, as medidas, os CSV de resultados/ e as tabelas deste arquivo
python3 -I regional.py tudo       # as duas coisas
```

Os arquivos:
- `regional.py`: o programa.
- `dados/cidades.csv`: as 20 cidades, a área, o ponto e a fonte do ponto.
- `resultados/cidade-safra-principal.csv` e `resultados/cidade-safra-sensibilidade_soja_15_dias_depois.csv`: a
  falta, o rendimento e o rendimento relativo de cada cidade em cada safra.
- `resultados/por-cidade-*.csv`: a medida (a). `resultados/regional-por-safra-*.csv`: a medida (d).
- `resultados/resultado.json`: tudo, sem arredondar.
