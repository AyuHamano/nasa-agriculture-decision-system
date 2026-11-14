<!-- Gerado com IA (Claude) -->
# Órbita Rural · o motor (provisório, sem site)

**O que é.** Um programa que responde, para um caso só (Rio Verde, GO, ponto -17.79, -50.92): "Com o clima que a NASA
registrou na minha região, vale trocar a minha rotação de hoje por outra? Por quê, com que prova e com que risco?"
A rotação de hoje é soja → milho safrinha → pousio (terra parada). A alternativa, uma só, é soja → milho com
braquiária (capim). A resposta pode ser "fique como está": nada é escrito antes de a conta rodar.

**Uso de IA.** Todo o código, os testes e este texto foram gerados com IA (Claude, da Anthropic), a pedido do time, e
revisados por outra IA (GPT). Cada arquivo leva o cabeçalho "Gerado com IA (Claude)". A explicação que o motor
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
4. Por rotação e por safra (de 1/set a 31/ago): a falta de água em mm (pedido menos bebido), os dias de sede (dias com
   soja ou milho e Ks < 1) e a falta em % do pedido. "Safra com sede" = falta do milho de 20% ou mais (mostra também
   com 10% e 30%). "Dias sem planta viva" saem do calendário.

## As fontes (cada arquivo guardado leva o endereço e a hora da consulta)
| o quê | fonte | onde está |
|---|---|---|
| a temperatura (máxima e mínima) | NASA POWER, API diária | `data/orbita/nasa-power/` |
| a chuva do padrão | o satélite GPM IMERG, da NASA (parâmetro `IMERG_PRECTOT` da API da NASA POWER; o dia é o UTC; vai até 2026-09-14) | `data/orbita/validacao/chuva/imerg.csv` |
| as chuvas de comparação | CHIRPS, ERA5 (Open-Meteo), a chuva de modelo da NASA POWER (`PRECTOTCORR`) e a estação do INMET | `data/orbita/validacao/chuva/` e `data/orbita/nasa-power/` |
| o rendimento do milho de 2ª safra | IBGE, Produção Agrícola Municipal | `data/orbita/validacao/ibge/` |
| o verde visto pelo satélite (NDVI) | MODIS MOD13Q1 v061, 6 pontos escolhidos no mapa | `data/orbita/ndvi/` |
| os parâmetros (Kc, fases, raízes, p, a água da terra, o calendário) | FAO-56 e ZARC, com o link e a etiqueta "publicado" ou "hipótese" | `data/orbita/parametros-com-fonte.json` e `parametros.py` |

## Por que a chuva do satélite e o pior ano pelo IBGE
A validação cruzada (`python3 -m orbita.validar`, 2026-11-14) mostrou que a chuva de modelo da NASA POWER fica bem
abaixo da estação em terra do INMET de 2021 para cá (na janela de fevereiro a junho: em média 51% da estação nas 4
safras comparadas de 2021 em diante, contra 86% nas 4 comparadas até 2020; no ano de 2025, 678 mm contra 1.548 mm).
Com a chuva do IMERG, a falta de água simulada do milho acompanha melhor o rendimento do IBGE (correlação de postos
-0,52; CHIRPS -0,42; ERA5 -0,41; NASA POWER -0,26; são só 10 safras: indício, não prova). O dono do projeto decidiu:
o padrão é a chuva do IMERG e o pior ano é o da pior colheita no IBGE (2015-16: 3.300 kg/ha). As outras opções
continuam, para comparar.

## O que a conta deu em 2026-11-14 (terra média; rode os comandos para ver tudo)
- Padrão (`--chuva imerg --regra rendimento`): ano normal 2019-20, pior ano 2015-16. Água: empate. No pior ano faltaram
  224,2 mm na rotação de hoje e 227,2 mm na alternativa (67 e 73 dias de sede); no ano normal, 152,3 e 152,5 mm (60 e
  60 dias). O milho passou sede (20% ou mais) em 10 das 10 safras nas duas rotações. Dias sem planta viva: 122 (hoje)
  contra 30 (alternativa). Resposta: "vale testar a troca" (ganha em solo e erosão, não perde na água medida).
- A falta de água do milho é igual nas duas rotações em todas as safras; a diferença aparece na soja (soma das 10
  safras: 421,7 mm hoje, 427,2 mm na alternativa), porque a braquiária deixa a terra mais seca no plantio.
- Com 10 de 10 safras "com sede", o critério de 20% não separa os anos: a conta, com a raiz do ZARC (0,5 m no milho)
  e sem enxurrada nem palha, pede conferência de um agrônomo antes de virar número de vitrine.
- NDVI (prova só da rotação de hoje): pelo calendário, 122 dias sem planta; o satélite viu 96 dias seguidos sem planta
  verde (mediana de 36 medidas, de 16 a 160 dias).

## Os limites
- Um caso só, com calendário fixo. Não mede renda, preço, custo nem produtividade: falta de água não é quebra de safra.
- Não mede a palha do capim (menos evaporação, mais chuva entrando na terra) nem a enxurrada: só entra o lado em que a
  braquiária bebe água. Enquanto o milho está na terra, o capim debaixo dele não aumenta o pedido de água (hipótese).
- A ETo de Hargreaves ficou de 7% a 10% acima da ETo do FAO que o Open-Meteo entrega (o `validar` mostra).
- O dia do IMERG é o UTC; a temperatura é do dia local. A safra 2025-26 fica à parte, "a conferir".
- 17 parâmetros ainda são hipótese (o `--json` lista cada um): o dia de plantio e as fases da soja, o Kc, o p, a raiz
  e a data de secar a braquiária, a classe de terra usada para a camada de cima (TEW e REW), o critério de 20% e o
  empate de 5 mm. **Valide com o agrônomo.**

## Os arquivos
`clima.py` (a série e a ETo) · `parametros.py` · `rotacoes.py` (o calendário e o Kc) · `balanco.py` (a água dia a dia)
· `motor.py` (a resposta) · `explicacao.py` (o texto) · `conferencia.py` (a conferência do texto) · `ndvi.py` ·
`perguntar.py` e `validar.py` (os comandos) · `tests/` (143 testes).
