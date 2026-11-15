<!-- Gerado com IA (Claude) -->
# O motor do Órbita Rural · o que mudou em 2026-11-15

O motor é o programa que faz a conta: pega o clima que a NASA registrou, o calendário das culturas e a terra, e diz
quanta água faltou, quantos dias de calor forte houve e quantos dias a terra ficou sem planta viva, em cada rotação.
Até 2026-11-14 ele respondia um caso só (Rio Verde, soja com milho e pousio contra soja com milho e braquiária). Este
arquivo conta o que entrou depois. O que já existia continua descrito no `README.md` e no `API.md` desta pasta.

**A regra que não mudou:** nenhum nome de antes mudou de lugar nem de sentido. O motor só ganhou campos. Quem lia a
resposta de antes continua lendo igual.

## 1. O que entrou

| o que | onde aparece | em uma linha |
|---|---|---|
| A data do plantio da soja | entrada `plantio_da_soja` ("2026-11-20") | opcional; o calendário inteiro anda junto com a data do produtor |
| As notas de 1 a 5 saíram | entrada `prioridades` | o campo é aceito e ignorado (seção 13); a resposta sai sem `entrada.prioridades` e sem a chave `nota` |
| O que mais preocupa | entrada `preocupacao` (`agua`, `calor` ou `terra`) | só muda a ordem e o destaque; nenhum número muda |
| Mais duas cidades | entrada `cidade_id`: `rio_verde`, `jatai`, `silvania` | cada uma com o clima, a chuva e a colheita do IBGE do seu ponto |
| O cardápio das rotações | entrada `rotacao_atual` | `["soja","milho","pousio"]`, `["soja","milho","braquiaria"]` ou `["soja","sorgo"]` |
| A terceira rotação, com sorgo | `rotacoes.com_sorgo` | soja e depois sorgo de 2ª safra, no lugar do milho |
| A comparação das três | `comparacao_das_rotacoes` | uma lista; a rotação de hoje vem primeiro, marcada com `de_hoje` |
| O calor | `calor` | os dias de calor forte na fase crítica de cada cultura |
| A terra coberta | `terra_coberta` | os dias seguidos sem planta viva pelo calendário (e o total do ano) e, onde há medida, pelo satélite |
| As portas para o agente | `motor.clima_do_lugar`, `motor.verde_do_satelite`, `motor.replay_da_safra` | o clima do lugar, o que o satélite viu, a safra dia a dia |
| O "durante" | `motor.como_esta_hoje` | como está a água da lavoura no último dia com dado |
| O "depois" | `motor.registro_da_safra` | o registro de uma safra, depois da colheita |

### A entrada, campo por campo
```json
{"cidade_id": "jatai", "rotacao_atual": ["soja", "sorgo"], "terra": "media",
 "plantio_da_soja": "2026-11-20", "preocupacao": "agua"}
```
- `cidade_id` e `rotacao_atual` são obrigatórios. `rotacao_atual` aceita a lista das culturas (com ou sem acento, com
  ou sem o "pousio" no fim) ou o `id` da rotação (`soja_sorgo_pousio`).
- `terra`: `pouca`, `media` ou `muita` (a água que a terra segura). O tipo de solo do cadastro vira a terra assim:
  arenoso, `pouca`; textura média, `media`; argiloso, `muita`. A fonte é o ZARC (Portaria 345/2022, já citada em
  `data/orbita/parametros-com-fonte.json`): solos Tipo 1, 2 e 3, com 0,7, 1,1 e 1,5 mm de água por cm de terra.
- `plantio_da_soja`: ano-mês-dia, de 1 de setembro a 31 de dezembro. Só o mês e o dia entram no ensaio das safras
  guardadas; a 2ª safra entra depois de a soja sair, com o mesmo intervalo do calendário de costume.
- `chuva` e `regra` continuam como eram. Em Jataí e Silvânia só há a chuva `imerg` (o satélite) e `power` (o modelo).
- Erro de entrada: `ValueError` com a frase em português que começa por "Entrada fora do formato:".

### As chaves de sempre e a rotação de hoje
As chaves `rotacoes.atual`, `rotacoes.alternativa`, `comparacao`, `veredito`, `prioridades`, `destaque` e `sede_forte`
continuam comparando soja-milho-pousio com soja-milho-braquiária, agora no lugar, na terra e na data do produtor. A
rotação que o produtor faz hoje (qualquer uma do cardápio) aparece em `rotacao_de_hoje` e vem marcada em
`comparacao_das_rotacoes`. O replay, o "como está hoje" e o registro seguem a rotação de hoje dele.

### Cada rotação na comparação
```json
{"id": "soja_sorgo_pousio", "nome": "soja → sorgo safrinha → pousio (terra parada)", "de_hoje": true,
 "agua": {"falta_no_ano_normal_mm": 0, "falta_no_pior_ano_mm": 0, "dias_de_sede_no_pior_ano": 0, "em_faixa": false,
          "pior_ano_contra_o_normal": "maior"},
 "calor": {"dias_de_calor_forte_no_pior_ano": 0, "limite_c": 35.0, "etiqueta": "publicado", "por_cultura": {}},
 "terra_coberta": {"dias_sem_planta_viva": 122, "dias_sem_planta_viva_no_ano": 125, "pelo_satelite": null},
 "contra_as_outras": {"soja_milho_pousio": {"agua": "melhor", "calor": "empate", "terra_coberta": "empate"}},
 "evidencia": "...", "beneficio": "...", "risco": "...", "falta_saber": "..."}
```
- Na rotação com capim, os números da água saem em faixa (`{"de": ..., "ate": ...}`), porque não se sabe quanto o capim
  disputa água com o milho. `em_faixa` diz qual é o caso.
- `agua.pior_ano_contra_o_normal` (`maior`, `menor`, `igual` ou, nas faixas, `cruza`): o pior ano é o da pior colheita
  da região (IBGE), não o de maior falta de água na conta. Quando a conta dá nele menos falta que no ano normal
  (Jataí; Rio Verde com o plantio em 20 de novembro), as frases dizem isso: "o pior ano é o da pior colheita da região
  (safra 2015-16), não o de maior falta de água na conta: nele faltaram ..., menos que no ano normal ...". O texto
  inteiro (`explicacao.texto`) e o curto (`mensagem.texto`) acompanham.
- `calor.limite_c` é o limite da cultura da 2ª safra (a que muda entre as rotações); o detalhe está em `por_cultura`.
- `terra_coberta.dias_sem_planta_viva` é o número de sempre: os dias seguidos sem planta viva antes do plantio da soja
  (122 com pousio, 30 com capim), o que se compara com o satélite. `dias_sem_planta_viva_no_ano` é o ano inteiro,
  contado dia a dia: soma os 3 dias entre a soja e a 2ª safra (125 e 33).
- `contra_as_outras` compara os números sem arredondar: uma diferença de 4,99 mm não vira 5.
- As quatro frases são prontas e só têm números da conta: cada uma passa pelo `conferencia.conferir_texto`. O
  benefício e o risco saem da posição da rotação contra as outras (`contra_as_outras`), não de opinião.

### O replay: os dias e os marcos
`motor.replay_da_safra(entrada, "2015-16")` devolve `dias` (um por dia, de 1 de setembro a 31 de agosto) e `marcos`.
- Cada dia: `data`, `cultura`, `chuva_mm`, `agua_na_terra_mm`, `pedido_mm`, `bebido_mm`, `falta_mm`, `com_sede`,
  `tmax_c`, `calor_forte`.
- Cada marco: `data`, `tipo` (`plantio`, `agua_acabou`, `agua_no_fundo`, `calor_forte` ou `colheita`), `cultura`,
  `frase` e `principal` (um só marco é o principal: o começo da maior sequência de dias de sede). As datas dos marcos
  saem da conta.
- `agua_acabou` é o começo da sede: o dia em que a água fácil de tirar acabou (em Rio Verde, 2015-16, o milho em
  2016-04-04, com 17,2 mm na terra). Não é o dia em que a água acabou de fato, e por isso a frase dele começa pela
  sede ("Neste dia começou a sede mais longa do milho de 2ª safra: a água fácil de tirar da terra acabou, e foram 60
  dias seguidos de sede."); a frase do `agua_no_fundo` é a que diz "a água que a planta alcança acabou".
- `agua_no_fundo` (acerto de 2026-11-15) é esse dia: o primeiro em que a água na terra chega ao menor valor do ciclo
  da cultura, só quando nesse dia a planta pediu água e não conseguiu beber nada (no mesmo caso, 2016-04-24, com
  0,1 mm). Campos: `data`, `tipo`, `cultura`, `agua_na_terra_mm`, `situacao`, `frase` e `principal` (sempre `false`).
  `situacao` (2026-11-15) diz o que aconteceu, e a frase acompanha: `acabou` (sobrou até 0,1 mm, a última casa que a
  conta mostra), `perto_do_fundo` (sobrou mais que isso: em Rio Verde, 2018-19, o milho com 0,5 mm a 2 dias do fim do
  ciclo) ou `seca_no_plantio` (o dia é o do plantio: a terra já chegou seca, como a soja em Silvânia 2015-16 e em Rio
  Verde 2020-21). Só a frase do `acabou` diz "a água que a planta alcança acabou". Se a água
  não acabou de fato, ou se o ciclo não fechou nos dados guardados, não há esse marco. Os números são os de `dias`.

### O registro: as mesmas regras da comparação (acerto de 2026-11-15)
`motor.registro_da_safra(entrada, "2015-16")` conta a safra depois da colheita. Dois números dele discordavam da
comparação das rotações, e agora cada um diz de onde vem:
- `terra_coberta.dias_sem_planta_viva` são os dias sem planta viva contados nos dias da própria safra
  (`dias_da_safra`); `dias_sem_planta_viva_no_ano` é o número da comparação, contado pelo calendário num ano comum.
  Em safra de ano bissexto (2015-16, 2019-20 e 2023-24) a safra dá um dia a mais (126 contra 125, com pousio), e a
  frase diz por quê.
- `entre_as_safras_guardadas` compara com as 10 safras do estudo, as mesmas da conta (`de: 10`). A safra mais recente
  (2025-26) fica à parte, como na conta: sai com `a_parte: true`, fora da lista e da mediana, e a `posicao` dela diz
  onde ficaria ao lado das 10. Antes ela entrava na lista, e a frase falava em "11 safras".

## 2. Como rodar
De dentro de `backend/`:
```bash
python3 -m unittest                                   # 522 testes (os 227 de antes e os novos)
python3 -m orbita.perguntar --cidade jatai --rotacao soja,sorgo --plantio 2026-11-20   # 3 rotações comparadas
python3 -m orbita.perguntar --cidade jatai --rotacao soja,sorgo --plantio 20/11        # entrada errada: a frase, saída 2
python3 -m orbita.perguntar --cidade silvania --lugar          # os fatos do clima do lugar
python3 -m orbita.perguntar --verde                            # o que o satélite viu da terra
python3 -m orbita.perguntar --replay 2015-16                   # a safra dia a dia: os marcos
python3 -m orbita.perguntar --hoje                             # como está a água hoje
python3 -m orbita.perguntar --lavoura-hoje --cidade jatai      # a lavoura hoje: os 6 itens (seção 10)
python3 -m orbita.perguntar --registro 2015-16                 # o registro da safra
python3 -m orbita.exportar <pasta> --sem-notas --tudo          # grava também motor.js e motor.json
```
Com `--json`, cada comando devolve a estrutura inteira. O `exportar` sem opções grava o que sempre gravou, com os
campos novos dentro de cada resposta. Com `--tudo`, grava também `window.ORBITA_MOTOR = {lugares, respostas, replay,
hoje, registro}` das três cidades, para a tela mostrar sem servidor.

## 3. As fontes novas
Tudo o que foi baixado tem o endereço e a hora da consulta ao lado.

| o que | de onde | onde está guardado |
|---|---|---|
| A temperatura e a chuva de modelo de Jataí e Silvânia | NASA POWER, API diária | `data/orbita/cidades/<id>/nasa-power/` (`consulta.txt`, `baixado-em.txt`) |
| A chuva do satélite de Jataí e Silvânia | GPM IMERG, pela NASA POWER (`IMERG_PRECTOT`) | `data/orbita/cidades/<id>/chuva/` (`fonte.json`) |
| A colheita de Jataí e Silvânia | IBGE, Produção Agrícola Municipal (SIDRA) | `data/orbita/cidades/<id>/ibge/` (`fonte.json`) |
| A chuva recente das três cidades | NASA GIBS, camada diária `IMERG_Precipitation_Rate` | `data/orbita/recente/<id>/` (`fonte.json`, `LEIA-ME.md`) |
| O verde do satélite de Jataí e Silvânia (6 pontos cada) | MOD13Q1 v061 (NASA LP DAAC), pelo espelho do Planetary Computer | `data/orbita/cidades/<id>/ndvi/` (`fonte.json`; a hora de cada medida no CSV) |
| A chuva do satélite em mm, de 5 em 5 dias (conferência) | GPM IMERG Late V07, no arquivo do Climate Hazards Center (UC Santa Barbara) | `data/orbita/recente/<id>/chuva-5-dias.csv` (`fonte-5-dias.json`) |
| Os valores do sorgo | FAO-56, Tabelas 11, 12 e 22; Embrapa Milho e Sorgo | `data/orbita/parametros-com-fonte.json`, `culturas.sorgo_2a_safra` |
| Os limites de calor | Embrapa Soja, Embrapa Milho e Sorgo, FAO | `data/orbita/parametros-com-fonte.json`, `calor` |

O programa de baixar uma cidade nova é `data/orbita/cidades/baixar_cidade.py`; o da chuva recente,
`data/orbita/recente/baixar_chuva_recente.py`; o do verde do satélite, `data/orbita/ndvi/baixar_ndvi.py`; o da chuva
em mm de 5 em 5 dias, `data/orbita/recente/baixar_imerg_5_dias.py` (o único que usa biblioteca de fora, Pillow e
numpy; o motor não depende dele). O motor não baixa nada na hora da pergunta: lê o que está guardado.

### O sorgo: o que é publicado e o que é hipótese
- Publicado (FAO-56): o pedido de água no começo e no fim do ciclo (Kc 0,3 e 0,55), as quatro fases (20, 35, 40 e 30
  dias) e a fração de água fácil de tirar (0,55). Publicado (Embrapa, Documentos 198): a época de plantio em Goiás.
- Hipótese, dita na resposta: o pedido de água no meio do ciclo (a fonte dá a faixa de 1,00 a 1,10; a conta usa 1,05)
  e a profundidade da raiz (vale a do milho de 2ª safra, 50 cm, para comparar os dois na mesma medida).
- A tabela da FAO não tem linha de 2ª safra em Goiás: usar as fases dela aqui é escolha desta versão.

### O calor: o critério, escrito antes de ver os números
"Dia de calor forte" é o dia da fase crítica da cultura com a temperatura máxima acima do limite da cultura. De cada
cultura vale o limite publicado mais ligado à fase crítica (a floração e o enchimento dos grãos):

| cultura | limite | fonte | o outro limite publicado (vai ao lado) |
|---|---|---|---|
| soja | 40 °C | Embrapa Soja, Sistemas de Produção 9 | não há |
| milho | 33 °C | Embrapa Milho e Sorgo, Cultivo do Milho, Clima e solo | 35 °C, na mesma página |
| sorgo | 35 °C | FAO, Crop Information: Sorghum | 38 °C, Embrapa, Cultivo do Sorgo |

Duas hipóteses, ditas na resposta: as fontes não dizem se o limite é da máxima ou da média do dia (a conta usa a
máxima); e a fase crítica, no calendário, é a fase do meio da tabela da FAO. As páginas de cultura da FAO foram lidas
na cópia do Internet Archive, porque a página viva deu erro em 2026-11-15.

### O "como está hoje": o teste do caminho rápido
A chuva do satélite que o motor usa chega pela NASA POWER com cerca de 2 meses de atraso. O teste de 30 minutos achou
um caminho sem login, com 2 dias de atraso: a imagem diária do IMERG no NASA GIBS, com o valor lido da cor do ponto.
Deu certo com ressalvas, que estão em `data/orbita/recente/LEIA-ME.md` (o que foi tentado: `tentativas.md`, ao lado):
- a chuva recente é aproximada (vem em faixas de cor; dia com menos de 2,4 mm sai como zero);
- nos dias recentes ela discorda bastante da chuva de modelo (em Rio Verde, de 2026-09-15 a 2026-11-11: 411,0 mm
  contra 146,5 mm). Por isso `como_esta_hoje` devolve a conta com as duas e a faixa entre elas
  (`faixa_da_agua_na_terra_mm`), ao lado do mesmo dia do ano normal e do pior ano.
- na resposta há duas datas com o nome `ultimo_dia_com_dado`, de dados diferentes, e cada uma leva ao lado o campo
  `ultimo_dia_com_dado_de`, que diz de qual dado é. A de cima é a da conta: o último dia em que há a temperatura (NASA
  POWER) e a chuva rápida do satélite, as duas (é o dia do retrato). A de `chuva_recente.fonte` é só da chuva rápida
  do satélite, e pode ir além. Em Rio Verde, na consulta de 2026-11-15: 11/11/2026 (a temperatura guardada acaba
  nesse dia) e 13/11/2026 (a chuva rápida). O teste é `tests/test_hoje.py`.

## 4. Os limites (o que a conta não faz)
- A estação em terra só existe em Rio Verde. O verde do satélite existe nas três cidades (ver a seção 8), em pontos
  escolhidos no mapa, que ninguém conferiu em campo. Cidade sem arquivo continua saindo com `sem_medida`.
- O satélite prova só a rotação de hoje da região (soja, milho e pousio). Nas outras, os dias sem planta viva vêm do
  calendário.
- O calor é uma contagem à parte: não mexe na conta da água, e dia de calor forte não é perda de safra. A temperatura
  é a de um quadrado de uns 50 km, não a da lavoura.
- O sorgo entra no mesmo dia do milho, com o mesmo ciclo e a mesma raiz: a diferença entre os dois, na conta, vem só
  do quanto cada um pede de água. A conta não mede renda nem o preço do sorgo contra o do milho.
- O nível de sede forte sai da colheita do milho no IBGE: não vale para o sorgo. Em Silvânia nenhuma safra ficou
  abaixo do corte de quebra, e o nível sai vazio (`nivel_pct: null`), como o motor já fazia nesse caso.
- Em Silvânia duas safras empatam no pior rendimento (2015-16 e 2021-22): vale a mais antiga, dito em
  `regra_dos_anos.empate_do_pior_ano`.
- Com o sorgo e o calor, o número de hipóteses da resposta (`hipoteses`) subiu de 24 para 30: as 6 novas são o pedido
  de água do sorgo no meio do ciclo, a raiz do sorgo, a fase crítica de cada uma das 3 culturas e o uso da temperatura
  máxima do dia. Os textos que citam esse número acompanham.
- Continua valendo o aviso de sempre: não é recomendação agronômica; converse com o agrônomo.

## 5. O que ficou como próximo passo
- A chuva recente exata **de cada dia**, em mm, pelo GES DISC da NASA (pede uma conta Earthdata, grátis). Sem login só
  se achou o valor em mm somado de 5 em 5 dias (seção 8), que serve de conferência e não de entrada da conta.
- Tapar os buracos do verde do satélite (2024 e 2025 não entram: o espelho não tem as imagens). O serviço do ORNL
  DAAC, que poderia tapar, estava fora do ar (503) em 2026-11-14 e em 2026-11-15.
- Conferir em campo, ou com quem planta, os pontos do verde do satélite das três cidades.
- Comparar a chuva recente com a estação por mais tempo e em mais de uma estação (hoje são 50 dias e uma estação).
- Abrir a portaria do ZARC do sorgo em vigor e a Tabela 30 do Cultivo do Sorgo da Embrapa, para a janela de plantio
  por município.
- Fases e ciclo do sorgo de 2ª safra medidos em Goiás, e a raiz do sorgo com número próprio.
- Levar a rotação de hoje do produtor também para as chaves de sempre (hoje elas comparam sempre as duas de antes).
- O `api.py` (a porta de internet) já foi ligado pela parte do agente: tem as rotas `GET /saude`, `POST /recomendacao`,
  `POST /mensagem`, `POST /conversa` e `POST /agente` (a conversa com a IA, que consulta o motor pelas ferramentas e é
  a única rota que traz a comparação das 3 rotações, o replay, o "como está hoje" e o registro). O que falta: as rotas
  de antes (`/mensagem` e `/conversa`) ainda falam só das duas rotações de antes, e a `/conversa` só de Rio Verde.

## 6. A revisão da outra IA (uma volta, 2026-11-15, 01h25)
O GPT revisou o código novo e apontou 7 defeitos; os 7 foram consertados, cada um com o teste que falhava antes
(`tests/test_revisao_do_motor.py`):
1. o registro quebrava se a safra mais recente ainda não tivesse chegado à 2ª safra: agora só entram na comparação as
   safras em que a 2ª safra fechou o ciclo, e a safra parcial sai com `posicao: null`;
2. o replay anunciava "colheita" no último dia com dado, com a cultura ainda crescendo: agora só há marco de colheita
   com o ciclo completo (`resumo.<cultura>.ciclo_completo`), e um aviso diz até onde vão os dados;
3. com o servidor ligado, o clima baixado de novo não era lido: a hora da última mudança do arquivo entra na chave do
   que fica na memória (`clima.marca_dos_arquivos`);
4. o número da terra coberta era chamado de "dias por ano", mas não contava os 3 dias entre a soja e a 2ª safra: as
   frases passaram a dizer "dias seguidos", e entrou `dias_sem_planta_viva_no_ano`;
5. a posição da safra no registro saía de números arredondados: agora sai dos números sem arredondar;
6. a margem do empate na comparação das rotações valia sobre números arredondados: agora vale sobre os exatos;
7. uma safra de 365 dias num ano de 366 saía como completa: agora confere de 1 de setembro a 31 de agosto, sem buraco.
Não houve segunda volta (a coordenação pediu uma só).

## 7. Os arquivos desta parte
- Novos: `calor.py`, `hoje.py`, `registro.py`, este `LEIA-ME-motor.md`, e os testes `test_plantio.py`,
  `test_preocupacao.py`, `test_cidades.py`, `test_sorgo.py`, `test_comparacao.py`, `test_replay.py`, `test_hoje.py`,
  `test_registro.py`, `test_perguntar.py`, `test_revisao_do_motor.py`.
- Mudados: `motor.py`, `rotacoes.py`, `balanco.py`, `clima.py`, `parametros.py`, `explicacao.py`, `mensagem.py`,
  `perguntar.py`, `exportar.py`, `tests/test_motor.py` (um teste mudou de sentido, com o motivo escrito nele) e
  `tests/test_exportar.py`.
- Dados: `data/orbita/cidades/`, `data/orbita/recente/` e `data/orbita/parametros-com-fonte.json`.

## 8. Os dois dados que faltavam (2026-11-15, trabalho começado às 02h00)
**1. O verde do satélite de Jataí e de Silvânia entrou.** São 6 pontos por cidade, do mesmo produto e pelo mesmo
caminho de Rio Verde, de 2018-06-26 a 2026-10-16. Os pontos foram escolhidos no mapa por uma regra escrita antes de
ver os números (a 15, 20 ou 25 km da cidade, onde o mapa de uso da terra de 10 m diz "lavoura" em 2018 e em 2023):
**não se sabe de quem são nem o que foi plantado, e ninguém conferiu em campo.** As coordenadas, a regra e os buracos
estão em `data/orbita/ndvi/LEIA-ME.md`.

| cidade | dias seguidos sem planta verde (a mediana) | de quanto a quanto | medidas | pelo calendário | leitura |
|---|---|---|---|---|---|
| Rio Verde (como era) | 96 | 16 a 160 | 36 | 122 | dentro da faixa |
| Jataí | 80 | 0 a 128 | 30 | 122 | dentro da faixa |
| Silvânia | 96 | 16 a 192 | 35 | 122 | dentro da faixa |

No código: `motor.verde_do_satelite`, `resposta["ndvi"]`, `terra_coberta.pelo_satelite` e o registro da safra passam
a responder nas três cidades; o aviso dos pontos cita a cidade certa (`ndvi.aviso_dos_pontos`) e a ficha da fonte sai
do `fonte.json` da pasta (`ndvi.fonte`). Nenhum nome de antes mudou; Rio Verde responde igual.

**2. A chuva recente: achado o valor em mm, mas só de 5 em 5 dias; a fonte do `como_esta_hoje` não foi trocada.**
- De onde vem a chuva rápida de hoje: da cor da imagem diária do IMERG no NASA GIBS (2 dias de atraso).
- O que se achou sem login: o IMERG Late V07 em mm, somado de 5 em 5 dias, no arquivo do Climate Hazards Center da
  UC Santa Barbara (um espelho, não um servidor da NASA), com 5 a 9 dias de atraso. Por dia, em mm e sem login, nada.
- O que a comparação mostrou (os números e a tabela estão em `data/orbita/recente/LEIA-ME.md`): a leitura da cor
  bate com o valor em mm (diferença de 5% a 13% nas três cidades, em 13 períodos). Contra a estação do INMET de Rio
  Verde, em 50 dias de setembro e outubro de 2026, o satélite deu de 32% a 38% a mais e a chuva de modelo, 45% a
  menos: a estação caiu entre os dois. A faixa larga do `como_esta_hoje` é a distância entre o satélite e o modelo,
  não erro de leitura.
- O que entrou: `chuva_recente.conferencia_em_mm` na resposta do `como_esta_hoje` (as duas somas lado a lado; a conta
  não usa). Testes: `tests/test_verde_das_cidades.py` e `tests/test_chuva_de_5_dias.py`; dois testes antigos que
  esperavam "sem medida" em Silvânia mudaram, com o motivo escrito neles.
- O que foi tentado e não deu (o Planetary Computer, o ClimateSERV, o ORNL, o portal do EGIS): `tentativas.md`, seção 7.

## 9. A leitura do produtor em palavras simples (2026-11-15, 03h10)
As frases que o motor escreve para o produtor (as 4 frases de cada rotação, o "como está hoje", o registro, o verde
do satélite, os marcos e os avisos do replay) deixaram as palavras da conta: "mediana" virou "o valor do meio"; "zona
das raízes", "a camada de terra onde ficam as raízes"; "chuva de modelo", "a chuva estimada por modelo de
computador"; "faixa da hipótese", "o menor e o maior valor, porque isso não foi medido". O GPM IMERG, o NASA GIBS e a
FAO vêm com a explicação ao lado ("a chuva medida por satélite da NASA", "o órgão da ONU para a agricultura"). A data
sai como 11/11/2026 (`explicacao.data_br`), e o "como está hoje" escreve as duas datas, a do último dado e a da
consulta, no lugar de "4 dias antes de hoje". Os campos (`data`, `ultimo_dia_com_dado`, `hoje`) continuam em
ano-mês-dia, e o texto inteiro do agrônomo (`explicacao.texto`) mantém os termos técnicos. A falta de água em mm sai
sempre com uma casa ("252,0 mm"). O teste é `tests/test_fala_simples.py`; a conferência dos números passa em todas.

## 10. A lavoura hoje: o acompanhamento com todos os indicadores (2026-11-15, 08h00)
O dono do projeto aprovou o painel "a lavoura hoje" como o centro do produto: o acompanhamento durante a safra não
pode usar só a chuva. `motor.lavoura_hoje(entrada, hoje=None)` (a peça é o `lavoura.py`) devolve seis itens, no
último dia com dado, na rotação e na data de plantio do produtor. O `como_esta_hoje` continua com os campos de sempre.

| item | o que diz | de onde sai (nada novo) |
|---|---|---|
| a fase da cultura | o que está na terra, os dias desde o plantio, a fase e se é a fase crítica | o calendário e as 4 fases da tabela da FAO, as mesmas do consumo de água; a crítica é a do meio, como no calor |
| a água | a água na terra, a sede, o ano normal e o pior ano, e os dias seguidos de sede | o `como_esta_hoje` e os registros da mesma conta |
| o calor | os dias com a máxima acima do limite da cultura desde o plantio, na fase atual e na fase crítica, ao lado do valor do meio das 10 safras guardadas no mesmo dia do ciclo | a temperatura da NASA POWER e os limites publicados (seção 3) |
| o verde do satélite | o valor da imagem mais recente, com a data, contra a mesma época dos outros anos guardados | os CSV do verde (MOD13Q1), com a mesma regra de medida boa do `ndvi.py` |
| a terra coberta | há quantos dias seguidos a terra está com planta viva (ou sem), a sequência de antes e os dias da safra | o calendário da rotação |
| o aviso de sede | sem chuva, em quantos dias a água chega ao nível de sede; se já há sede, há quantos dias | a mesma conta da água, seguida para a frente com chuva zero |

Cada item leva `situacao`, `frase`, `ultimo_dado` (a data e de qual dado é) e `regra_da_situacao`. No topo, a `frase`
que resume e a `situacao`, que é a pior dos itens.

### As regras (escolhas desta peça, escritas antes de ver os números; estão em `lavoura.REGRAS`)
- **A fase.** Atenção: a cultura está na fase crítica (a floração e o enchimento do grão). Tranquilo: nas outras fases
  ou sem cultura na terra. Os nomes das fases para o produtor: no começo do ciclo, em crescimento, na fase crítica, no
  fim do ciclo (a maturação).
- **A água.** Alerta: com sede no último dia com dado. Tranquilo: sem sede, ou sem cultura na terra. A água não tem
  "atenção" (quem avisa antes é o aviso de sede); até a troca da seção 11, "atenção" era ter sede só na conta com a
  chuva de modelo. A comparação com o ano normal e o pior ano vai na frase, mas não muda a situação (em Jataí o pior
  ano tinha a terra quase cheia nessa data).
- **O calor.** "Dia de calor forte", aqui, é o dia com a máxima acima do limite da cultura em qualquer fase (na
  comparação das rotações o motor conta só os da fase crítica; esse número vai ao lado, em
  `dias_de_calor_forte_na_fase_critica`). Alerta: já houve dia de calor forte dentro da fase crítica desta safra.
  Atenção: sem isso, mas os dias desde o plantio passam do valor do meio das safras guardadas no mesmo dia do ciclo.
  Tranquilo: o resto.
- **O verde.** O valor de cada imagem é o valor do meio dos pontos com medida boa. A mesma época é a mesma medida do
  satélite nos outros anos (o mesmo dia do ano em que os 16 dias começam). Abaixo do normal: abaixo do menor valor
  dos outros anos; acima: acima do maior; dentro: entre os dois. Com menos de 3 outros anos, não compara (sem dado).
  Atenção: abaixo do normal com cultura na terra no fim da imagem. O verde nunca dá alerta sozinho: os pontos são da
  região, escolhidos no mapa, não da lavoura.
- **A terra coberta.** Tranquilo: com planta viva (a cultura ou o capim) pelo calendário. Atenção: sem planta viva.
- **O aviso de sede.** A conta segue para a frente por 30 dias, sem chuva, com o tempo dos últimos 7 dias com dado (a
  média da temperatura e da evaporação de referência); o pedido da cultura em cada dia segue o calendário e as fases.
  O nível de sede é o dos dias de sede do motor (a água fácil de tirar acabou). Alerta: já com sede. Atenção: a sede
  chega em até 7 dias. Tranquilo: o resto. A frase diz também quanta chuva o satélite já marcou depois do último dia
  da conta (`chuva_depois_do_ultimo_dia`), que ainda não entrou por faltar a temperatura desses dias. Os 7 e os 30
  dias são escolha desta versão, não número de fonte. Não há previsão do tempo.

### Como rodar e o que ficou de fora
- `python3 -m orbita.perguntar --lavoura-hoje --cidade rio_verde|jatai|silvania [--plantio 2026-10-20] [--rotacao
  soja,sorgo] [--terra media] [--json]`; na API, `POST /lavoura-hoje` (o `API.md` tem o pedido e a resposta).
- O teste é `tests/test_lavoura_hoje.py`, com o "hoje" fixo em 2026-11-15 e só com os dados guardados.
- O verde não foi atualizado: em 2026-11-15, 08h10, o espelho (Planetary Computer) ainda só tinha a imagem de
  16/10/2026 (a de 01/11/2026 não tinha saído). O painel diz a data da imagem.
- Ficou de fora: o arquivo da tela (`exportar --tudo`) ainda não leva o painel (a ferramenta do agente passou a
  levar em 2026-11-15: a `lavoura_hoje`, no `ferramentas.py`); a fase vem do calendário, não de visita à lavoura; o verde é da região, não do talhão do produtor.

## 11. A chuva do dia no lugar da chuva lida da cor, e a temperatura um dia mais perto (2026-11-15, 08h20)
A pedido da coordenação, num commit à parte do painel:
- **A chuva recente mudou de fonte.** O `como_esta_hoje` e o painel passam a ler `data/orbita/chuva-do-dia/<cidade>/
  chuva-do-dia.csv`: o GPM IMERG V07 em mm, por dia de Brasília, na versão Late e, onde ela ainda não chegou, na
  Early (`hoje.ler_chuva_recente`). Vem da cópia dos arquivos da NASA que a dynamical.org mantém (não é servidor da
  NASA; licença CC BY 4.0, citação "NASA IMERG from dynamical.org"); o programa, a regra do dia e a conferência estão
  no `LEIA-ME.md` daquela pasta. A leitura da cor da imagem do NASA GIBS (`data/orbita/recente/`) não entra mais na
  conta: fica em `hoje.ler_chuva_da_cor` e no registro `chuva_recente.conferencia_em_mm`.
- **A água sai como um número só.** A frase do `como_esta_hoje` dá a água da conta com essa chuva e diz até que dia a
  chuva vai; `faixa_da_agua_na_terra_mm` continua existindo, com as duas pontas iguais, e `com_a_chuva_de_modelo`
  continua ao lado, só para comparar (nenhum nome de antes saiu). No painel, a chuva de modelo saiu das frases e das
  regras.
- **A temperatura guardada ganhou um dia.** `data/orbita/nasa-power/acrescentar_dias.py` (novo, só a biblioteca
  padrão) pergunta de novo os últimos dias à NASA POWER e troca o -999 pelo valor só onde os três parâmetros já
  chegaram; dia que já tinha valor não muda. Em 2026-11-15, 08h18, entrou o dia 12/11/2026 nas três cidades (o
  endereço e a hora estão em `acrescimos.json`, em cada pasta); 13/11 em diante a NASA POWER ainda não tinha.
- **A data de cada dado, na consulta de 2026-11-15** (já com a regra da seção 12): a conta da água, a fase, a terra
  coberta e o aviso de sede, até 14/11/2026 (o último dia com chuva do satélite: Late até 13/11, Early no dia 14); o
  calor, até 12/11/2026 (o último dia com temperatura medida); o verde do satélite, a imagem de 16/10/2026.
- **O que saber:** o dia da chuva nova é o de Brasília e o da temperatura e da chuva guardada é o da NASA POWER (na
  emenda de 14 para 15/09/2026 ficam 3 horas sem entrar em nenhuma das duas); em Rio Verde, de 15/09 a 12/11/2026, a
  chuva nova soma 431,8 mm (a lida da cor dava 411,0 mm até 11/11).
- **O que não acompanhou** (fora das pastas desta parte, ou sem tempo): os números gravados da tela (`motor.js`,
  `respostas.js`) ainda trazem a água com a chuva lida da cor e a faixa (as conversas guardadas e o pedido à IA do
  agente foram acertados na rodada do alinhamento, em 2026-11-15: seção 13); os documentos de `docs/orbita/` e a seção 3 deste
  arquivo ainda descrevem a leitura da cor como a fonte da conta. Nenhuma rotina agendada baixa a chuva ou a
  temperatura: é rodar os dois programas à mão.

## 12. A conta segue até o último dia com chuva do satélite (2026-11-15, 08h30)
A temperatura da NASA POWER chega uns 3 dias depois; a chuva do satélite, no dia seguinte. Antes a conta parava no
último dia com as duas (12/11/2026) e deixava de fora a chuva que já tinha chegado (em Rio Verde, 23,7 mm em 13 e
14/11). **A regra, escolha desta versão:**
- A conta da água segue até o último dia com chuva do satélite guardada, sem dia faltando no meio e nunca depois do
  dia da consulta (`hoje.seguir_com_a_chuva`). Nos dias em que a temperatura ainda não chegou, entra a chuva de
  verdade do satélite e, para o consumo da cultura, o tempo médio dos últimos 7 dias com temperatura (a média da
  máxima, da mínima e da evaporação de referência): a mesma regra que o aviso de sede usa para a frente. O que a
  cultura pede nesses dias segue o calendário e as fases, como no resto da conta.
- A fase, a terra coberta e o aviso de sede acompanham esse dia. O aviso de sede parte dele, e o tempo dos dias para a
  frente continua sendo o dos últimos 7 dias com temperatura medida (não os estimados).
- **O calor não usa dia estimado:** conta só até o último dia com temperatura medida, e a frase e o `ultimo_dado`
  dele dizem essa data.
- A conta com a chuva de modelo (`com_a_chuva_de_modelo`, só para comparar) para no último dia com temperatura, que é
  até onde a chuva de modelo vai; o campo `data` dela diz o dia.
- Na resposta do `como_esta_hoje` e do painel entraram `ultimo_dia_com_temperatura`, `dias_com_o_consumo_estimado`,
  `consumo_estimado_desde` e `janela_do_consumo_dias` (7); `ultimo_dia_com_dado` passa a ser o último dia com chuva.
  A frase da água diz, em poucas palavras, de que dia em diante o consumo é o dos 7 dias anteriores.
- Na consulta de 2026-11-15: a conta vai até 14/11/2026, com 2 dias de consumo estimado (13 e 14/11); em Rio Verde a
  água passou de 58,6 mm (em 12/11) para 66,0 mm (em 14/11, a terra cheia), e a sede, sem chuva, chega em 7 dias
  (21/11/2026).
- O limite: nos dias estimados a temperatura de verdade pode ter sido outra; quando ela chega (rodando
  `data/orbita/nasa-power/acrescentar_dias.py`), a conta desses dias é refeita com o dado medido.

## 13. A rodada do alinhamento (2026-11-15, 08h54)

O dono do projeto decidiu no dia: as limitações não precisam ficar explícitas para o produtor, a data do dado não é
defeito e as notas de 1 a 5 saem. O que a conta dá não mudou: nenhum número e nenhuma situação (tranquilo, atenção,
alerta) mudou, e nenhum campo de antes saiu. Cada resposta passa a ter duas leituras:

- **A leitura do produtor** (frases curtas, só com a data do dado): `frase`, `aviso`, e, na comparação, `risco` e
  `falta_saber`.
- **A leitura do agrônomo** (o texto de antes, inteiro): os campos novos `risco_detalhe`, `falta_saber_detalhe`,
  `detalhe_tecnico` e `aviso_tecnico`, mais os de sempre (`aviso` de cada item, `o_que_e`, `ultimo_dado`,
  `regra_da_situacao`, `limites`, `hipoteses`).

| onde | o que mudou | campo novo |
|---|---|---|
| `comparacao_das_rotacoes[*]` | `risco` e `falta_saber` saem em UMA frase só | `risco_detalhe` e `falta_saber_detalhe`: o texto de antes, igual |
| `motor.lavoura_hoje`, o topo | a `frase` sem "(o último dia com dado)"; o `aviso` é a linha curta | `aviso_tecnico` (o aviso longo de antes) e `detalhe_tecnico` (de qual dado é a data) |
| `motor.lavoura_hoje`, cada item | a `frase` leva só a data do dado | `detalhe_tecnico`: o que saiu da frase (até onde vai cada dado, o dia da consulta, os pontos da região) |
| `motor.como_esta_hoje` | a `frase` leva só a data do dado; o `aviso` é a linha curta | `aviso_tecnico` e `detalhe_tecnico` |
| `motor.responder`, o topo | o `aviso` é a linha curta (saiu "Motor provisório, sem site...") | nenhum: `limites` e `hipoteses` continuam |

A linha curta é uma só, em todo lugar: "Converse com o agrônomo antes de decidir." (`motor.AVISO_DO_PRODUTOR`).

**A regra de qual frase fica** (`explicacao.frase_principal`), a mesma para o `risco` e para o `falta_saber`: as
frases continuam sendo montadas na ordem de sempre (água, calor, terra coberta e, no fim, a frase própria da
rotação). Se o produtor disse o que mais o preocupa (`preocupacao`: agua, calor ou terra) e a rotação tem frase
nessa perna (no risco: ela perde nessa perna para outra rotação), fica essa frase. Senão, fica a primeira da ordem
de sempre. As duas nunca saem vazias: sem perda nenhuma, o risco é "Na conta, esta rotação não ficou atrás das
outras em água, calor nem terra coberta."

**As notas de 1 a 5 saíram do motor.** `motor.responder` ainda aceita a entrada que traz `prioridades` (as rotas
antigas não quebram), mas ignora o campo: não confere as notas e não ordena por elas. A resposta é sempre a de sem
notas, na ordem de costume, com a preocupação na frente; e as chaves que ficavam vazias saíram da resposta:
`entrada.prioridades`, `prioridades[*].nota` e `destaque.nota` (a lista `prioridades` continua, com `id`, `nome`,
`melhor` e `medida`). Do texto (`explicacao.py`) saíram "(nota N)" e "DA MAIOR NOTA PARA A MENOR". Os 4 campos
`entrada.prioridades.*`, o `prioridades.[].nota` e o `destaque.nota` de `tests/campos_de_antes.json` são os únicos
de antes que já não aparecem (o teste diz por quê).

Ficou na frase do aviso de sede "Não é previsão do tempo: a chuva que cair muda a conta.": é o sentido do "se não
chover", não um limite do dado. Os testes novos: a classe `ALeituraDoProdutor` em `tests/test_comparacao.py`,
`tests/test_lavoura_hoje.py` e `tests/test_hoje.py`, e os de notas em `tests/test_motor.py` e
`tests/test_preocupacao.py`.
