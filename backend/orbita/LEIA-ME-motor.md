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
| As notas de 1 a 5 saíram | entrada `prioridades` | virou opcional; sem ela, a lista sai com `nota: null` |
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
- Cada marco: `data`, `tipo` (`plantio`, `agua_acabou`, `calor_forte` ou `colheita`), `cultura`, `frase` e `principal`
  (um só marco é o principal: o começo da maior sequência de dias de sede). As datas dos marcos saem da conta.

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
python3 -m unittest                                   # 314 testes (os 227 de antes e os novos)
python3 -m orbita.perguntar --cidade jatai --rotacao soja,sorgo --plantio 2026-11-20   # 3 rotações comparadas
python3 -m orbita.perguntar --cidade jatai --rotacao soja,sorgo --plantio 20/11        # entrada errada: a frase, saída 2
python3 -m orbita.perguntar --cidade silvania --lugar          # os fatos do clima do lugar
python3 -m orbita.perguntar --verde                            # o que o satélite viu da terra
python3 -m orbita.perguntar --replay 2015-16                   # a safra dia a dia: os marcos
python3 -m orbita.perguntar --hoje                             # como está a água hoje
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
| Os valores do sorgo | FAO-56, Tabelas 11, 12 e 22; Embrapa Milho e Sorgo | `data/orbita/parametros-com-fonte.json`, `culturas.sorgo_2a_safra` |
| Os limites de calor | Embrapa Soja, Embrapa Milho e Sorgo, FAO | `data/orbita/parametros-com-fonte.json`, `calor` |

O programa de baixar uma cidade nova é `data/orbita/cidades/baixar_cidade.py`; o da chuva recente,
`data/orbita/recente/baixar_chuva_recente.py`. O motor não baixa nada na hora da pergunta: lê o que está guardado.

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

## 4. Os limites (o que a conta não faz)
- O verde do satélite e a estação em terra só foram conferidos em Rio Verde. Em Jataí e Silvânia, a terra coberta sai
  só do calendário, e `terra_coberta.pelo_satelite.leitura` diz `sem_medida`.
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
- Baixar o verde do satélite (NDVI) de Jataí e de Silvânia, para a prova da terra coberta existir nas três cidades.
- A chuva recente exata, em mm, pelo GES DISC da NASA (pede uma conta Earthdata, grátis), no lugar da leitura da cor.
- Abrir a portaria do ZARC do sorgo em vigor e a Tabela 30 do Cultivo do Sorgo da Embrapa, para a janela de plantio
  por município.
- Fases e ciclo do sorgo de 2ª safra medidos em Goiás, e a raiz do sorgo com número próprio.
- Levar a rotação de hoje do produtor também para as chaves de sempre (hoje elas comparam sempre as duas de antes).
- O `api.py` (a porta de internet) não foi tocado aqui: ligar os campos novos é da parte do agente.

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
