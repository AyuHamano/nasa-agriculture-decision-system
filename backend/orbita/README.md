<!-- Gerado com IA (Claude) -->
# Órbita Rural · o motor (provisório, sem site)

**O que é.** Um programa que responde, para um caso só (Rio Verde, GO, ponto -17.79, -50.92): "Com o clima que a NASA
registrou na minha região, vale trocar a minha rotação de hoje por outra? Por quê, com que prova e com que risco?"
A rotação de hoje é soja → milho safrinha → pousio (terra parada). A alternativa, uma só, é soja → milho com
braquiária (capim). A resposta pode ser "fique como está": nada é escrito antes de a conta rodar.

**Uso de IA.** Todo o código, os testes e este texto foram gerados com IA (Claude, da Anthropic), a pedido do time, e
revisados por outra IA (GPT, uma volta: 5 achados, os 5 consertados com teste). Cada arquivo leva o cabeçalho "Gerado com IA (Claude)". A explicação que o motor
escreve **não** usa IA: são frases prontas, preenchidas só com os números da conta, e uma conferência
(`conferencia.py`) lista todo número do texto que não esteja na conta.

## Como rodar (Python 3, só a biblioteca padrão; sem chave, sem login)
De dentro de `backend/`:

    python3 -m orbita.perguntar --agua 5 --solo 4 --renda 2 --erosao 3 --terra media          # a resposta em português
    python3 -m orbita.perguntar --agua 5 --solo 4 --renda 2 --erosao 3 --terra media --json   # a estrutura
    python3 -m orbita.validar                                                                # a validação cruzada
    python3 -m unittest                                                                      # os testes

- As notas (1 a 5) só mudam a ordem e o destaque da explicação; nenhum número muda. `--terra`: `pouca`, `media` ou `muita`.
- `--chuva imerg|chirps|era5|power`: a fonte da chuva. O padrão é `imerg` (o satélite de chuva da NASA).
- `--regra rendimento|chuva`: como se escolhe o pior ano. O padrão é `rendimento` (a pior colheita de milho no IBGE).
- A entrada em JSON (a mesma do documento do time, mais a terra): `{"cidade_id": "rio_verde", "rotacao_atual":
  ["soja", "milho", "pousio"], "prioridades": {"agua": 5, "solo": 4, "renda": 2, "erosao": 3}, "terra": "media"}`;
  `chuva` e `regra` são opcionais. Em Python: `from orbita import motor; motor.responder(entrada)`.

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
   dentro da faixa). Nenhuma vencedora está escrita no código.

## As fontes (cada arquivo guardado leva o endereço e a hora da consulta)
| o quê | fonte | onde está |
|---|---|---|
| a temperatura (máxima e mínima) | NASA POWER, API diária | `data/orbita/nasa-power/` |
| a chuva do padrão | o satélite GPM IMERG, da NASA (parâmetro `IMERG_PRECTOT` da API da NASA POWER; o dia é o UTC; vai até 2026-09-14) | `data/orbita/validacao/chuva/imerg.csv` |
| as chuvas de comparação | CHIRPS, ERA5 (Open-Meteo), a chuva de modelo da NASA POWER (`PRECTOTCORR`) e a estação do INMET | `data/orbita/validacao/chuva/` e `data/orbita/nasa-power/` |
| o rendimento do milho de 2ª safra | IBGE, Produção Agrícola Municipal | `data/orbita/validacao/ibge/` |
| o verde visto pelo satélite (NDVI) | MODIS MOD13Q1 v061, 6 pontos escolhidos no mapa | `data/orbita/ndvi/` |
| a palha e a disputa do capim com o milho | FAO-56, cap. 10 (a regra da palha: publicado) e cap. 7 (o teto do Kc); Embrapa Agropecuária Oeste (o relatório de impacto do consórcio, 2019, e o ensaio de Dourados, MS): dão a massa de palha e citam a disputa, sem número de cobertura nem de água; por isso as coberturas e a faixa são hipótese | `parametros.py` (`palha` e `disputa_com_o_milho`) |
| os parâmetros (Kc, fases, raízes, p, a água da terra, o calendário) | FAO-56 e ZARC, com o link e a etiqueta "publicado" ou "hipótese" | `data/orbita/parametros-com-fonte.json` e `parametros.py` |

## Por que a chuva do satélite e o pior ano pelo IBGE
A validação cruzada (`python3 -m orbita.validar`, 2026-11-14) mostrou que a chuva de modelo da NASA POWER fica bem
abaixo da estação em terra do INMET de 2021 para cá (na janela de fevereiro a junho: em média 51% da estação nas 4
safras comparadas de 2021 em diante, contra 86% nas 4 comparadas até 2020; no ano de 2025, 678 mm contra 1.548 mm).
O IMERG é a fonte mais perto da estação (erro médio do total da janela: 12,1% nas 8 safras comparadas; CHIRPS
17,6%; ERA5 26,7%; NASA POWER 33,2%). Com a chuva do IMERG, a falta de água simulada do milho também acompanha
melhor o rendimento do IBGE (correlação de postos
-0,52; CHIRPS -0,42; ERA5 -0,41; NASA POWER -0,26; são só 10 safras: indício, não prova). O dono do projeto decidiu:
o padrão é a chuva do IMERG e o pior ano é o da pior colheita no IBGE (2015-16: 3.300 kg/ha). As outras opções
continuam, para comparar.

## O que a conta deu em 2026-11-14 (terra média; rode os comandos para ver tudo)
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

## Os limites
- Um caso só, com calendário fixo. Não mede renda, preço, custo nem produtividade: falta de água não é quebra de safra.
- A palha entra só pelo lado da evaporação, com uma cobertura fixa em cada rotação (não se desfaz com o tempo) e só
  nos dias sem planta viva e na fase inicial da soja; não entra a chuva a mais que a palha deixa entrar na terra, nem
  a enxurrada. As coberturas (60% e 90%) são hipótese: a Embrapa dá a massa de palha, não a terra coberta.
- O quanto o capim disputa água com o milho não foi medido: a faixa (0, 4% e 8% a mais de pedido) é hipótese, e o
  veredito da água pode mudar com ela.
- O nível de sede forte sai de poucas safras (2 de quebra em 10) e de uma conta só: pode haver alarme falso e quebra
  que a conta não vê. É régua de comparação, não previsão de quebra.
- A ETo de Hargreaves ficou de 7% a 10% acima da ETo do FAO que o Open-Meteo entrega (o `validar` mostra).
- O dia do IMERG é o UTC; a temperatura é do dia local. A safra 2025-26 fica à parte, "a conferir".
- 24 parâmetros ainda são hipótese (o `--json` lista cada um): o dia de plantio e as fases da soja, o coeficiente da
  terra sem planta com a camada de cima molhada, o Kc, o p, a raiz
  e a data de secar a braquiária, a classe de terra usada para a camada de cima (TEW e REW), as duas coberturas de palha, os
  três fatores da disputa, o limite de 80% da mediana para a quebra, o critério de 20% e o empate de 5 mm. **Valide com o agrônomo.**

## Os arquivos
`clima.py` (a série e a ETo) · `parametros.py` · `rotacoes.py` (o calendário e o Kc) · `balanco.py` (a água dia a dia)
· `motor.py` (a resposta) · `explicacao.py` (o texto) · `conferencia.py` (a conferência do texto) · `ndvi.py` ·
`perguntar.py` e `validar.py` (os comandos) · `tests/` (172 testes).
