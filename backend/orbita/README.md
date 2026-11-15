<!-- Gerado com IA (Claude) -->
# Órbita Rural · o motor (provisório, sem site)

**O que é.** Um programa que responde: "Com o clima que a NASA registrou na minha região, vale trocar a minha rotação
de hoje por outra? Por quê, com que prova e com que risco?" Ele vale para três cidades de Goiás: Rio Verde (ponto
-17.79, -50.92), Jataí (-17.88, -51.71) e Silvânia (-16.66, -48.61). Compara três rotações: soja → milho safrinha →
pousio (terra parada), soja → milho com braquiária (capim) e soja → sorgo safrinha → pousio. O produtor diz qual das
três faz hoje, a terra, a data do plantio da soja e o que mais preocupa. A resposta pode ser "fique como está": nada
é escrito antes de a conta rodar.

**O que mudou em 2026-11-15.** Até 2026-11-14 o motor respondia um caso só (Rio Verde, duas rotações). Entraram as
duas cidades, a rotação com sorgo, a data do plantio, o calor, a terra coberta com o verde do satélite nas três
cidades, a safra dia a dia (o replay), o "como está hoje", o registro da safra e o agente (a IA que conversa com o
produtor). Nenhum nome de antes mudou de lugar nem de sentido: quem lia a resposta de antes continua lendo igual. O
resumo está na seção "O que entrou em 2026-11-15"; o detalhe, no `LEIA-ME-motor.md` (o motor), no
`LEIA-ME-agente.md` (o agente) e no `API.md` (as rotas e os campos).

**Uso de IA.** Todo o código, os testes e este texto foram gerados com IA (Claude, da Anthropic), a pedido do time, e
revisados por outra IA (GPT, uma volta: 5 achados, os 5 consertados com teste). Cada arquivo leva o cabeçalho "Gerado com IA (Claude)". A explicação que o motor
escreve **não** usa IA: são frases prontas, preenchidas só com os números da conta, e uma conferência
(`conferencia.py`) lista todo número do texto que não esteja na conta. Só o agente (a rota `POST /agente`) usa um
modelo de linguagem para escrever; os números não são dele: saem do motor, e o texto é conferido contra a conta.

## Como rodar (Python 3, só a biblioteca padrão; a conta roda sem chave e sem login)
De dentro de `backend/`:

    python3 -m orbita.perguntar --terra media                                                 # a resposta em português
    python3 -m orbita.perguntar --terra media --plantio 2026-11-20 --preocupacao agua --json  # a estrutura
    python3 -m orbita.perguntar --cidade jatai --rotacao soja,sorgo --plantio 2026-11-20      # outra cidade, a rotação de hoje
    python3 -m orbita.perguntar --agua 5 --solo 4 --renda 2 --erosao 3 --terra media          # com as notas, como antes
    python3 -m orbita.perguntar --cidade silvania --lugar      # os fatos do clima do lugar
    python3 -m orbita.perguntar --verde                        # o que o satélite viu da terra
    python3 -m orbita.perguntar --replay 2015-16               # a safra dia a dia: os marcos
    python3 -m orbita.perguntar --hoje                         # como está a água hoje
    python3 -m orbita.perguntar --registro 2015-16             # o registro da safra
    python3 -m orbita.validar                                  # a validação cruzada (Rio Verde)
    python3 -m orbita.api                                      # liga a API em http://127.0.0.1:8000
    python3 -m unittest                                        # os testes

- `--cidade rio_verde|jatai|silvania` (o padrão é `rio_verde`). `--rotacao` é a rotação de hoje, com vírgulas:
  `soja,milho,pousio` (o padrão), `soja,milho,braquiaria` ou `soja,sorgo`.
- `--terra`: `pouca`, `media` ou `muita` (quanta água a terra segura; o padrão é `media`).
- `--plantio`: a data do plantio da soja, ano-mês-dia, de 1 de setembro a 31 de dezembro. O calendário inteiro anda
  junto. `--preocupacao agua|calor|terra`: o que mais preocupa; só muda a ordem e o destaque.
- As notas (1 a 5) são opcionais: ou vêm as 4, ou nenhuma. Só mudam a ordem e o destaque; nenhum número muda.
- `--lugar`, `--verde`, `--replay`, `--hoje` e `--registro` são as outras portas do motor, uma de cada vez. Saem em
  frases prontas, ou na estrutura inteira com `--json`.
- `--chuva imerg|chirps|era5|power`: a fonte da chuva. O padrão é `imerg` (o satélite de chuva da NASA). Em Jataí e
  Silvânia só há `imerg` e `power`.
- `--regra rendimento|chuva`: como se escolhe o pior ano. O padrão é `rendimento` (a pior colheita de milho no IBGE).
- Entrada errada: sai uma frase em português dizendo o que usar, e o comando termina com o código 2.
- A entrada em JSON: `{"cidade_id": "jatai", "rotacao_atual": ["soja", "sorgo"], "terra": "media",
  "plantio_da_soja": "2026-11-20", "preocupacao": "agua"}`. Só `cidade_id` e `rotacao_atual` são obrigatórios;
  `prioridades` (as notas), `chuva` e `regra` são opcionais. Em Python: `from orbita import motor;
  motor.responder(entrada)`.
- **A conversa com a IA** (o agente) precisa de uma chave do OpenRouter, só no ambiente do terminal, nunca em
  arquivo: `export OPENROUTER_API_KEY=...` e depois `python3 -m orbita.api` (a rota `POST /agente`) ou
  `python3 -m orbita.agente` (a conversa no terminal). Sem a chave, todo o resto roda igual; só a rota `/agente`
  responde 503, e a tela usa as conversas guardadas em `conversas-guardadas/`.

## O que entrou em 2026-11-15 (o resumo)
- **As cidades.** `cidade_id`: `rio_verde`, `jatai` ou `silvania`. Cada uma com o clima, a chuva do satélite e a
  colheita do IBGE do seu ponto. A estação em terra, e por isso a validação cruzada, só existe em Rio Verde.
- **A data do plantio, a terra e a preocupação.** `plantio_da_soja` (opcional), `terra` (arenosa é `pouca`, textura
  média é `media`, argilosa é `muita`) e `preocupacao` (`agua`, `calor` ou `terra`).
- **As três rotações.** A resposta traz `comparacao_das_rotacoes`: uma lista com as três, a de hoje primeiro
  (`de_hoje`). Cada uma com a água (a falta no ano normal e no pior ano, os dias de sede), o calor, a terra coberta,
  a posição contra as outras duas (`contra_as_outras`) e 4 frases prontas: a evidência, o benefício, o risco e o que
  falta saber. As chaves de sempre (`rotacoes.atual`, `rotacoes.alternativa`, `comparacao`, `veredito`) continuam
  comparando soja-milho-pousio com soja-milho-braquiária; a rotação com sorgo está em `rotacoes.com_sorgo`.
- **O calor** (`calor`). Os dias de calor forte: os dias da fase crítica da cultura com a máxima acima do limite
  (40 °C na soja, 33 °C no milho, 35 °C no sorgo). É uma contagem à parte: não mexe na conta da água.
- **A terra coberta** (`terra_coberta`). Os dias seguidos sem planta viva pelo calendário, o total do ano e o que o
  satélite viu (o NDVI). Agora há NDVI guardado das três cidades, 6 pontos por cidade. **Os pontos foram escolhidos
  no mapa e ninguém conferiu em campo.**
- **O replay** (`motor.replay_da_safra`). A safra dia a dia (`dias`) e os marcos: `plantio`, `agua_acabou` (o começo
  da sede: acabou a água fácil de tirar), `agua_no_fundo` (o dia em que a água acabou; a `situacao` dele diz se acabou, se ficou perto do fundo ou se a terra já
  chegou seca ao plantio), `calor_forte` e `colheita`.
  Um só marco é o `principal`: o começo da maior sequência de dias de sede.
- **O "como está hoje"** (`motor.como_esta_hoje`). A água da lavoura no último dia com dado, com a chuva rápida do
  satélite e com a chuva de modelo, a faixa entre as duas, e o mesmo dia do ano normal e do pior ano.
  `chuva_recente.conferencia_em_mm` põe ao lado o valor do satélite em mm, somado de 5 em 5 dias (só conferência).
- **O registro** (`motor.registro_da_safra`). A safra contada depois da colheita: a água, o calor, a terra coberta,
  os marcos e a posição dela entre as 10 safras do estudo.
- **O agente** (a rota `POST /agente`). A IA conversa com o produtor, preenche uma ficha fechada (a cidade, a rotação
  de hoje, a terra, a data do plantio, a preocupação) e consulta o motor por 3 ferramentas. A conta só roda depois do
  "sim" do produtor, e essa confirmação leva um selo que só a API sabe fazer. Toda resposta com a ficha confirmada
  traz a comparação das 3 rotações, e cada número do texto da IA é conferido contra a conta antes de aparecer.
- **As rotas de antes** (`POST /mensagem` e `POST /conversa`) continuam valendo, com o alcance de antes. A
  `/conversa` (a conversa de frases prontas, sem IA) vale só para Rio Verde e só para as duas rotações de antes: soja,
  milho e pousio contra soja e milho com braquiária. A `/mensagem` (o texto curto) aceita as três cidades, mas o texto
  fala sempre dessas duas rotações de antes, mesmo que a entrada diga outra rotação de hoje. As 3 rotações, o sorgo,
  o replay, o "como está hoje" e o registro saem pela `/recomendacao` e pela `/agente`.

O campo a campo, com exemplos, está no `API.md`.

## A conta (FAO-56: https://www.fao.org/4/X0490E/x0490e00.htm)
1. A evaporação de referência de cada dia (ETo) por Hargreaves-Samani (eq. 52), com a radiação no topo da atmosfera
   (Ra) pela latitude e o dia do ano (eq. 21 a 25). Testes: os Exemplos 8 e 20 do FAO-56.
2. O que a planta pede = Kc × ETo, com o Kc por fase (Tabelas 11 e 12).
3. A água na zona das raízes, dia a dia (cap. 8, eq. 82 a 88): a água que a terra segura (TAW), a parte fácil de tirar
   (RAW = p × TAW), o freio da sede (Ks) e o que a planta bebeu (Ks × pedido). A chuva que passa de encher se perde.
   A simulação é contínua, de 2014-07-01 ao último dia com dado. Terra sem planta evapora só a camada de cima (cap. 7,
   eq. 74). A braquiária continua bebendo água depois do milho, até ser seca antes da soja.
   **A palha** (cap. 10, "Effects of surface mulches": a evaporação da terra cai uns 5% a cada 10% de terra coberta)
   entra nas DUAS rotações, nos dias sem planta viva e na fase inicial da soja: 60% de cobertura com a palha do
   milho (hoje) e 90% com a do milho mais a do capim (alternativa); as duas coberturas são hipótese.
   **A disputa do capim com o milho** é hipótese e sai em faixa: enquanto os dois crescem juntos, o conjunto pede
   (1 + fator) × o pedido do milho, com o fator em 0 (sem disputa), 0,04 (meio) e 0,08 (alta: o teto do Kc no
   FAO-56, 1,30). O pedido do milho não muda; a terra é que seca mais depressa. Os campos antigos da alternativa
   na resposta são os da hipótese do meio (`rotacoes.alternativa.disputa_com_o_milho` traz os três cenários).
4. Por rotação e por safra (de 1/set a 31/ago): a falta de água em mm (pedido menos bebido), os dias de sede (dias com
   soja ou milho e Ks < 1) e a falta em % do pedido. "Safra com sede" = falta do milho de 20% ou mais (mostra também
   com 10% e 30%). "Dias sem planta viva" saem do calendário.
5. **"Sede forte"**: safra de quebra = rendimento do milho de 2ª safra no IBGE abaixo de 80% da mediana das 10
   safras; o nível é a menor falta do milho entre as safras de quebra, na conta da rotação de hoje com a terra
   média e a chuva padrão. Sai do arquivo do IBGE, não está escrito à mão. O motor conta, em cada rotação, as safras
   no nível ou acima, diz quais são, quais são alarme falso (sem quebra no IBGE) e que quebra ficou abaixo do nível.
6. **O veredito da água** sai das duas pontas da faixa, pela falta de água da soja e do milho no pior ano: "a
   alternativa se saiu melhor", "pior", "empate" (menos de 5 mm nas duas pontas) ou "depende da hipótese" (muda
   dentro da faixa). Nenhuma vencedora está escrita no código. Está em `comparacao.agua.pela_faixa` e em
   `prioridades[].veredito_pela_faixa`, e é ele que entra no `veredito` geral. Os campos antigos (`comparacao.agua.melhor`
   e o `melhor` de cada prioridade) continuam com o sentido de antes: comparam a rotação de hoje com a alternativa
   num cenário só, que agora é o da hipótese do meio. Quem mostra a água deve ler o campo novo.

## As fontes (cada arquivo guardado leva o endereço e a hora da consulta)
| o quê | fonte | onde está |
|---|---|---|
| a temperatura (máxima e mínima) | NASA POWER, API diária | `data/orbita/nasa-power/` |
| a chuva do padrão | o satélite GPM IMERG, da NASA (parâmetro `IMERG_PRECTOT` da API da NASA POWER; o dia é o UTC; vai até 2026-09-14) | `data/orbita/validacao/chuva/imerg.csv` |
| as chuvas de comparação | CHIRPS, ERA5 (Open-Meteo), a chuva de modelo da NASA POWER (`PRECTOTCORR`) e a estação do INMET | `data/orbita/validacao/chuva/` e `data/orbita/nasa-power/` |
| o rendimento do milho de 2ª safra | IBGE, Produção Agrícola Municipal | `data/orbita/validacao/ibge/` |
| o verde visto pelo satélite (NDVI) | MODIS MOD13Q1 v061, 6 pontos por cidade, escolhidos no mapa e não conferidos em campo | `data/orbita/ndvi/` (Rio Verde) e `data/orbita/cidades/<id>/ndvi/` (Jataí e Silvânia) |
| o clima, a chuva e a colheita de Jataí e Silvânia | NASA POWER, GPM IMERG e IBGE, como em Rio Verde | `data/orbita/cidades/<id>/` |
| a chuva dos dias recentes (o "como está hoje") | NASA GIBS, a imagem diária do IMERG (aproximada); a conferência em mm, de 5 em 5 dias, vem do IMERG Late V07 | `data/orbita/recente/<id>/` |
| o sorgo e os limites de calor | FAO-56, FAO, Embrapa Soja e Embrapa Milho e Sorgo, com a etiqueta "publicado" ou "hipótese" | `data/orbita/parametros-com-fonte.json` |
| a palha e a disputa do capim com o milho | FAO-56, cap. 10 (a regra da palha: publicado) e cap. 7 (o teto do Kc); Embrapa Agropecuária Oeste (o relatório de impacto do consórcio, 2019, e o ensaio de Dourados, MS): dão a massa de palha e citam a disputa, sem número de cobertura nem de água; por isso as coberturas e a faixa são hipótese | `parametros.py` (`palha` e `disputa_com_o_milho`) |
| os parâmetros (Kc, fases, raízes, p, a água da terra, o calendário) | FAO-56 e ZARC, com o link e a etiqueta "publicado" ou "hipótese" | `data/orbita/parametros-com-fonte.json` e `parametros.py` |

As linhas de cima são as de Rio Verde, a não ser onde dizem outra cidade. O detalhe das fontes novas (o endereço e a
hora de cada consulta) está na seção 3 do `LEIA-ME-motor.md`.

## Por que a chuva do satélite e o pior ano pelo IBGE
Esta comparação foi feita em Rio Verde, a única das três cidades com estação em terra. A validação cruzada (`python3 -m orbita.validar`, 2026-11-14) mostrou que a chuva de modelo da NASA POWER fica bem
abaixo da estação em terra do INMET de 2021 para cá (na janela de fevereiro a junho: em média 51% da estação nas 4
safras comparadas de 2021 em diante, contra 86% nas 4 comparadas até 2020; no ano de 2025, 678 mm contra 1.548 mm).
O IMERG é a fonte mais perto da estação (erro médio do total da janela: 12,1% nas 8 safras comparadas; CHIRPS
17,6%; ERA5 26,7%; NASA POWER 33,2%). Com a chuva do IMERG, a falta de água simulada do milho também acompanha
melhor o rendimento do IBGE (correlação de postos
-0,52; CHIRPS -0,42; ERA5 -0,41; NASA POWER -0,26; são só 10 safras: indício, não prova). O dono do projeto decidiu:
o padrão é a chuva do IMERG e o pior ano é o da pior colheita no IBGE (2015-16: 3.300 kg/ha). As outras opções
continuam, para comparar.

## O que a conta deu em 2026-11-14 (Rio Verde, terra média; rode os comandos para ver tudo)
- Padrão (`--chuva imerg --regra rendimento`): ano normal 2019-20, pior ano 2015-16. **Água: depende da hipótese.**
  No pior ano faltaram 225,9 mm de água na rotação de hoje (73 dias de sede); na alternativa, de 229,8 mm (sem
  disputa: 3,9 mm a mais, dentro do empate de 5 mm) a 241,2 mm (disputa alta: 15,3 mm a mais), com 76 a 77 dias de
  sede. No ano normal, 152,8 mm hoje e de 149,9 a 163,2 mm na alternativa. Dias sem planta viva: 122 (hoje) contra
  30 (alternativa). **Resposta: "depende": a alternativa ganha em solo e erosão, e na água o resultado muda com a
  hipótese da disputa.**
- A falta de água do milho no pior ano: 220,6 mm (49,6% do pedido) na rotação de hoje e de 220,6 a 232,0 mm (49,6% a
  52,1%) na alternativa; no ano normal, 142,8 mm (34,7%) e de 142,8 a 156,1 mm (34,7% a 38,0%). Na soma das 10
  safras: milho 1.696,6 mm hoje e de 1.696,6 a 1.811,6 mm na alternativa; soja 452,0 mm hoje e 427,1 mm na
  alternativa (a palha a mais ajuda a soja na soma; no pior ano a terra ainda chega mais seca ao plantio: 31,5 mm
  hoje e 18,2 mm na alternativa).
- Sede forte: o nível saiu em 49,6% (as safras de quebra no IBGE são 2015-16 e 2021-22, abaixo de 5.380 kg/ha). Na
  terra média, 2 de 10 safras nas duas rotações (2015-16 e 2021-22). Na terra que segura pouca água, 3 hoje e de 3 a 4
  na alternativa, com 2020-21 como alarme falso (falta alta, colheita de 7.200 kg/ha); na que segura muita, 1 nas
  duas, e a quebra de 2015-16 fica abaixo do nível. O critério antigo de 20% continua na resposta (10 de 10 safras).
- A resposta muda com as opções, e isso é parte do resultado: com `--terra pouca`, depende da hipótese (de 0,9 mm a
  menos a 8,7 mm a mais); com `--terra muita`, a alternativa se saiu pior nas duas pontas (de 8,8 a 21,4 mm a mais);
  com `--regra chuva` (pior ano 2017-18), o sinal muda dentro da faixa (de 6,1 mm a menos a 6,2 mm a mais); com a
  chuva `era5`, empate nas duas pontas.
- NDVI (prova só da rotação de hoje): pelo calendário, 122 dias sem planta; o satélite viu 96 dias seguidos sem planta
  verde (mediana de 36 medidas, de 16 a 160 dias).

## O que as partes novas deram em 2026-11-15 (terra média)
- **A rotação com sorgo, em Rio Verde:** no pior ano (2015-16) faltaram 191,3 mm de água (75 dias de sede), contra
  225,9 mm com soja-milho-pousio; no ano normal, 126,5 mm contra 152,8 mm. Os dias sem planta viva são os mesmos do
  pousio: 122 seguidos (125 no ano, contando os 3 dias entre a soja e a 2ª safra); com o capim, 30 (33 no ano).
- **O calor, em Rio Verde:** no pior ano, 19 dias de calor forte nas duas rotações com milho (limite de 33 °C) e
  nenhum na rotação com sorgo (limite de 35 °C).
- **Jataí, com a soja plantada em 2026-11-20:** o pior ano é 2015-16 e o ano normal, 2021-22. No pior ano faltaram
  147,8 mm com o sorgo (83 dias de sede), 171,7 mm com soja-milho-pousio (88 dias) e de 171,7 a 185,6 mm com o capim.
  Aqui a conta deu menos falta no pior ano que no ano normal (234,5 mm com o sorgo e 262,1 mm com soja-milho-pousio):
  o pior ano é o da pior colheita da região, não o de maior falta de água na conta, e a resposta diz isso
  (`pior_ano_contra_o_normal: "menor"`).
- **O verde do satélite nas três cidades** (os dias seguidos sem planta verde, a mediana; pelo calendário são 122):
  Rio Verde 96 (de 16 a 160, 36 medidas), Jataí 80 (de 0 a 128, 30 medidas), Silvânia 96 (de 16 a 192, 35 medidas).
  As três leituras ficaram dentro da faixa.
- **O replay de Rio Verde, safra 2015-16:** 366 dias e 8 marcos. A sede mais longa do milho começou em 2016-04-04
  (60 dias seguidos; é o marco principal) e a água acabou em 2016-04-24 (0,1 mm na terra).
- **O "como está hoje" de Rio Verde, rodado em 2026-11-15:** o último dia com dado era 2026-11-11, com soja na terra
  e de 34,8 a 63,0 mm de água (a terra segura 66,0 mm). A faixa é larga porque as duas chuvas recentes discordam:
  411,0 mm pelo satélite rápido e 146,5 mm pelo modelo, de 2026-09-15 a 2026-11-11.

## Os limites
- Três cidades e três rotações, com um calendário de costume que só anda com a data do plantio da soja. Não mede
  renda, preço, custo nem produtividade: falta de água não é quebra de safra.
- As chaves de sempre (`veredito`, `comparacao`, `prioridades`) e o texto curto comparam sempre soja-milho-pousio com
  soja-milho-braquiária. A rotação de hoje do produtor, quando é outra, está em `comparacao_das_rotacoes`.
- Os pontos do verde do satélite foram escolhidos no mapa, nas três cidades: ninguém conferiu em campo, e o satélite
  prova só a rotação soja-milho-pousio. O calor não mexe na conta da água, e a temperatura é a de um quadrado de uns
  50 km, não a da lavoura. A chuva dos dias recentes é aproximada. O sorgo entra no mesmo dia do milho, com o mesmo
  ciclo e a mesma raiz. O resto dos limites das partes novas está na seção 4 do `LEIA-ME-motor.md`.
- A palha entra só pelo lado da evaporação, com uma cobertura fixa em cada rotação (não se desfaz com o tempo) e só
  nos dias sem planta viva e na fase inicial da soja; não entra a chuva a mais que a palha deixa entrar na terra, nem
  a enxurrada. As coberturas (60% e 90%) são hipótese: a Embrapa dá a massa de palha, não a terra coberta.
- O quanto o capim disputa água com o milho não foi medido: a faixa (0, 4% e 8% a mais de pedido) é hipótese, e o
  veredito da água pode mudar com ela.
- O nível de sede forte sai de poucas safras (2 de quebra em 10) e de uma conta só: pode haver alarme falso e quebra
  que a conta não vê. É régua de comparação, não previsão de quebra.
- A ETo de Hargreaves ficou de 7% a 10% acima da ETo do FAO que o Open-Meteo entrega (o `validar` mostra).
- O dia do IMERG é o UTC; a temperatura é do dia local. A safra 2025-26 fica à parte, "a conferir".
- 30 parâmetros ainda são hipótese (o `--json` lista cada um): o dia de plantio e as fases da soja, o coeficiente da
  terra sem planta com a camada de cima molhada, o Kc, o p, a raiz
  e a data de secar a braquiária, a classe de terra usada para a camada de cima (TEW e REW), as duas coberturas de palha, os
  três fatores da disputa, o limite de 80% da mediana para a quebra, o critério de 20% e o empate de 5 mm; e, desde
  2026-11-15, o pedido de água do sorgo no meio do ciclo, a raiz do sorgo, a fase crítica de cada uma das 3 culturas
  e o uso da temperatura máxima do dia na contagem do calor. **Valide com o agrônomo.**

## Os arquivos
`clima.py` (a série e a ETo) · `parametros.py` · `rotacoes.py` (o calendário e o Kc) · `balanco.py` (a água dia a dia)
· `calor.py` (os dias de calor forte) · `motor.py` (a resposta) · `hoje.py` (o "como está hoje") · `registro.py` (o
registro da safra) · `explicacao.py` (o texto) · `mensagem.py` (o texto curto) · `conferencia.py` (a conferência do
texto) · `ndvi.py` · `perguntar.py` e `validar.py` (os comandos) · `api.py` (as rotas) · `conversa.py` (a conversa em
passos, sem IA) · `agente.py`, `ficha.py`, `ferramentas.py` e `modelo.py` (o agente) · `exportar.py` e
`exportar_conversas.py` (os arquivos que a tela lê) · `conversas-guardadas/` (as conversas de exemplo) · `tests/`
(489 testes, com os da API e os do agente; a rota `POST /lavoura-hoje` e o comando `--lavoura-hoje`, a lavoura hoje em seis itens, estão no `API.md` e no `LEIA-ME-motor.md`, seção 10).

Os outros manuais desta pasta: `API.md` (as rotas e os campos, um a um), `LEIA-ME-motor.md` (o que o motor ganhou em
2026-11-15, as fontes novas e os limites) e `LEIA-ME-agente.md` (o agente e as garantias).
