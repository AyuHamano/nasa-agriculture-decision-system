<!-- Gerado com IA (Claude) -->
# Órbita Rural · o agente (a IA que conversa com o produtor)

**O que é.** O agente é a IA que conversa com o produtor rural. Ele colhe os dados da lavoura numa ficha fechada,
consulta o motor (o programa que faz a conta com os dados da NASA) por 4 ferramentas e explica o resultado em
português simples. **A IA não cria número:** cada número do texto dela é conferido contra a conta antes de aparecer.
E ela não escolhe a rotação pelo produtor: mostra a comparação e manda conferir com o agrônomo.

O agente liga os três momentos do ano da lavoura: **antes** de plantar ("o que eu planto agora?"), **durante** a safra
("como está a minha lavoura?") e **depois** da colheita ("o que a terra mostrou?").

## O que a IA faz e o que o programa garante

A IA (um modelo de linguagem) faz quatro coisas: entende a fala do produtor, propõe os valores da ficha, escolhe qual
ferramenta consultar e escreve a explicação. O resto é garantido pelo programa, e não pelo pedido feito à IA:

| a garantia | como o programa garante | o teste |
|---|---|---|
| Valor fora da lista não entra na ficha | `ficha.anotar` só aceita valor das listas do motor (as cidades, as rotações, as terras, as preocupações) | `tests/test_ficha.py` |
| A conta não roda antes de o produtor confirmar | quem lê o "sim" é o programa (`agente._disse_sim`), nunca a IA; ferramenta da conta pedida antes disso devolve erro e não roda; a confirmação leva um selo que só este programa sabe fazer (o estado volta do navegador, e "confirmada" escrito à mão não vale) | `tests/test_agente.py` |
| Toda resposta, com a ficha confirmada, traz a comparação de 3 rotações ou mais, contando a de hoje | o programa roda o ensaio em toda fala e recusa comparação com menos de 3, sem a de hoje ou sem as 4 frases (a evidência, o benefício, o risco, o que falta saber) | `tests/test_ferramentas.py`, `tests/test_agente.py` |
| Número inventado pela IA não chega à tela | o texto é conferido por `conferencia.conferir_texto` contra a ficha, a comparação e o que as ferramentas devolveram nesta fala; sem consulta nenhuma, o texto não pode ter número; o que a IA manda como argumento a uma ferramenta não conta como conta; sobrou número, a IA tenta de novo uma vez; sobrou outra vez, saem as frases prontas do motor | `tests/test_agente.py` |
| Uma troca de sentido conhecida também não passa | "a terra fica coberta 30 dias", quando 30 é o número de dias **sem** planta viva, é barrada como um número de fora (vista no uso de verdade, em 2026-11-15) | `tests/test_agente.py` |
| "A água acabou" só no dia em que a conta diz | no replay de uma safra, o marco `agua_acabou` é o dia em que a sede começa (acabou só a água fácil de tirar) e o marco `agua_no_fundo` é o dia em que a água acabou; "a água acabou em 04/04/2016", dito do dia em que a sede começou, é barrado do mesmo jeito (visto nas conversas gravadas, em 2026-11-15) | `tests/test_agente.py` |
| Letra de outro alfabeto não chega à tela | texto da IA com letra que não é do português ("fazer 监测 de campo", visto na gravação de 2026-11-15) é barrado como um número de fora: a IA tenta de novo e, se repetir, saem as frases prontas | `tests/test_fala_simples.py` |
| A fala simples | o pedido à IA manda trocar as palavras da conta ("mediana" vira "o valor do meio"; "zona das raízes", "a camada de terra onde ficam as raízes"; "chuva de modelo", "a chuva estimada por modelo de computador"), escrever cada número como a conta escreve (252,0 mm, não 252 mm) e a data como 11/11/2026; as frases prontas do motor já saem assim. Isto é pedido, não trava: quem confere é a leitura das conversas gravadas | `tests/test_fala_simples.py` |
| O aviso do agrônomo | todo passo sai com `aviso: "Converse com o agrônomo antes de decidir."` | `tests/test_agente.py` |
| A marca do apoio | `apoio` sai das ferramentas que a IA consultou de fato: `conta`, `dados_do_lugar` ou `conhecimento_geral` (aí o programa põe o aviso na frente do texto) | `tests/test_agente.py` |
| A chave da IA não vaza | ela só existe na variável de ambiente; não entra em arquivo, erro, registro nem conversa guardada | `tests/test_modelo.py`, `tests/test_exportar_conversas.py` |

Nenhum dado pessoal é pedido (nome, telefone, CPF, endereço), e a API continua sem guardar nada.

## Os arquivos (todos em `backend/orbita/`)

| arquivo | o que é |
|---|---|
| `ficha.py` | a ficha fechada: o lugar, o que planta hoje, o tipo de terra, a data do plantio da soja (opcional) e o que mais preocupa |
| `modelo.py` | o encaixe da IA: o modelo de mentira (para os testes) e o de verdade (OpenRouter), no mesmo formato |
| `ferramentas.py` | as 4 ferramentas: `clima_do_lugar`, `ensaio_da_rotacao`, `verde_do_satelite` e `lavoura_hoje`; cada uma chama uma função do motor |
| `agente.py` | o passo da conversa: `agente.passo(estado, texto, modelo)`; é aqui que moram as garantias |
| `api.py` | a rota nova `POST /agente` (as rotas de antes continuam iguais) |
| `exportar_conversas.py` | grava as conversas de exemplo que a tela lê quando a API não está ligada |
| `conversas-guardadas/` | as conversas de exemplo já gravadas (`conversas.js` e `conversas.json`) |
| `.env.example` | só os nomes das variáveis de ambiente (nunca a chave) |
| `tests/duble_do_motor.py` | um motor de mentira, no formato combinado, para os testes do agente |

Só a biblioteca padrão do Python 3: nenhum pacote de fora.

## Como rodar sem chave (sem IA e sem internet)

De dentro de `backend/`:

    python3 -m unittest                                         # todos os testes; os do agente usam o modelo de mentira
    python3 -m orbita.exportar_conversas /tmp/conversas --sem-ia    # grava as conversas com as frases prontas do motor

Sem chave, a API liga do mesmo jeito (`python3 -m orbita.api`); só a rota `/agente` responde 503, e a tela usa as
conversas guardadas.

## Como ligar com a IA de verdade

A chave é do OpenRouter (https://openrouter.ai). Ela vai **só no ambiente do terminal**, nunca em arquivo:

    export OPENROUTER_API_KEY=...                  # a chave; o arquivo .env.example traz só o nome
    export ORBITA_MODELO=anthropic/claude-haiku-5.5    # opcional; este é o padrão
    python3 -m orbita.api                          # liga em http://127.0.0.1:8000 (só esta máquina)
    python3 -m orbita.agente                       # ou: a conversa no próprio terminal

A API não tem senha: fora do `127.0.0.1` ela fica aberta a quem alcançar a máquina (e gastaria a chave de quem ligou).
Para pôr na internet, precisa ficar atrás de uma proteção; isso não está feito.

## A rota `POST /agente`

O molde é o do `/conversa`: a API não guarda nada; quem chama guarda o `estado` e devolve na fala seguinte.

    curl -s -X POST http://127.0.0.1:8000/agente -H 'Content-Type: application/json' -d '{"estado": null, "texto": "oi"}'

O pedido: `{"estado": null no começo (ou o que a chamada anterior devolveu), "texto": "a fala do produtor"}`. O corpo
tem o limite de sempre (16.384 bytes); o estado nunca passa de uns 9.500 bytes.

A resposta:

| campo | o que traz |
|---|---|
| `estado` | o que guardar e devolver na fala seguinte, sem mexer: a ficha, o selo da confirmação, as últimas 6 falas (cortadas numa palavra inteira), a pergunta feita antes da ficha e o momento |
| `resposta` | o texto do agente, já conferido |
| `momento` | `antes`, `durante` ou `depois` |
| `ficha` | `cidade_id`, `rotacao_atual` (a lista das culturas), `terra`, `plantio_da_soja`, `preocupacao`, `confirmada` e `falta` (os campos que ainda não foram ditos) |
| `comparacao` | a lista de 3 rotações ou mais, como o motor mandou (`comparacao_das_rotacoes`); `null` enquanto a ficha não foi confirmada |
| `apoio` | `conta`, `dados_do_lugar` ou `conhecimento_geral`; `null` enquanto a ficha não foi confirmada |
| `conferencia` | `{"passou": ..., "sobras": [...], "tentativas": ...}`: o resultado da conferência do texto da IA; `passou: false` quer dizer que o texto dela foi barrado e a `resposta` são as frases prontas; `sobras` lista os números barrados |
| `aviso` | "Converse com o agrônomo antes de decidir." |
| `texto_de` | `ia` (o texto é do modelo de linguagem, conferido) ou `frases_prontas` (frases do programa e do motor, sem IA) |
| `consultas` | o que a IA leu das ferramentas nesta fala: `[{"ferramenta", "argumentos", "resultado"}]`; serve para qualquer um conferir os números de novo (`agente.conferir_saida`) |
| `replay` | os dias e os marcos de uma safra, quando o replay foi pedido (para a tela desenhar); senão `null` |

Os erros seguem o `API.md` (`{"erro": "..."}`, em português). Os da rota nova: **503** quando não há chave no
servidor, quando a IA não responde ou quando o motor não tem a conta (quem chama mantém o estado e usa as conversas
guardadas); **400** para corpo errado (falta o texto, estado que não é objeto, campo a mais). O `GET /saude` diz se a
IA está ligada e com que modelo (`ia_do_agente`), sem mostrar a chave.

**Como a conversa anda.** "oi" devolve a saudação pronta (sem gastar a IA). O produtor conta da lavoura; a IA anota
na ficha. Com a ficha completa, o programa mostra a ficha e pede o "sim". Depois do "sim", a conta roda e a IA
responde à pergunta que ele fez (se não fez nenhuma: "vale trocar a minha rotação de hoje por outra?"). Mudou a
ficha depois de confirmada, ela é mostrada de novo e a conta espera outro "sim". "de novo" recomeça.

**O selo da confirmação.** O estado volta de quem chama, e quem chama pode ser qualquer programa. Por isso a
confirmação da ficha vai junto com um selo (`estado.selo`), feito com um segredo sorteado quando a API liga e guardado
só na memória dela. Estado com "confirmada" e sem o selo certo volta a "não confirmada", e a ficha é mostrada de novo.
A consequência: se a API for desligada e ligada de novo, o produtor confirma a ficha outra vez (um "sim").

## As 4 ferramentas

| a ferramenta | o que a IA pode pedir | a função do motor |
|---|---|---|
| `lavoura_hoje` | o painel da lavoura agora ("como está a minha lavoura?"): o resumo e os seis indicadores (a fase da cultura, a água, o calor, o verde do satélite, a terra coberta e o aviso de sede), cada um com a frase, a situação e os números; sem argumento | `motor.lavoura_hoje` |
| `clima_do_lugar` | o que os satélites registraram no lugar (serve também quando o lugar do produtor não está guardado: é o clima do lugar guardado mais próximo) | `motor.clima_do_lugar` |
| `ensaio_da_rotacao` | a comparação das rotações no ano normal e no pior ano, e o calendário que a conta usou (com a data de plantio do produtor, se ele disse); com `safra`, o replay daquela safra, dia a dia | `motor.responder`, `motor.replay_da_safra` |
| `verde_do_satelite` | os dias sem planta viva pelo calendário e pelo satélite (NDVI); com `safra`, o registro daquela safra | `motor.verde_do_satelite`, `motor.registro_da_safra` |

`safra` aceita `"2015-16"`, `"pior_ano"` ou `"ano_normal"`; qualquer outro argumento que a IA mandar é jogado fora.
A ficha é a quinta coisa que a IA pode chamar (`anotar_na_ficha`), e não é da conta. O painel vai à IA enxuto (até 6
mil caracteres): sem as regras de cada situação, as fontes, os detalhes técnicos, a data da consulta e o atraso do
dado; fica a data do dado, que a IA diz uma vez ("em 14/11/2026"). Os números do painel entram na conferência como os
das outras ferramentas: número que não está nele é barrado. Se o motor não tiver o painel ou o registro, a ferramenta
devolve `{"disponivel": false, "aviso": ...}`. Nas frases prontas, o painel sai com o resumo e uma linha por item.

## O que o produtor disse fora das listas, e a indicação (2026-11-15)

A conta continua fechada (3 lugares, 3 rotações), mas a conversa não termina mais em recusa. A ficha ganhou dois
campos livres e opcionais, `lugar_dito` e `rotacao_dita`: o texto curto do que o produtor disse fora das listas
("Cristalina", "sorgo e milho"; só letra, espaço, vírgula e hífen, até 60 letras, sem algarismo). Junto com eles vão
`cidade_id` = o lugar guardado mais próximo (a IA escolhe pela latitude e longitude que a ferramenta mostra; se ela
não mandar, o programa pergunta "Qual destes fica mais perto da sua lavoura?") e `rotacao_atual` = a rotação guardada
mais parecida, que é escolha do programa, sempre, por regra fixa (`ficha.rotacao_parecida`; a IA só anota o
`rotacao_dita`, e a `rotacao_atual` que ela mandar junto é trocada): **tem sorgo no que foi dito: soja → sorgo →
pousio; senão, tem capim ou braquiária: soja → milho → braquiária; senão: soja → milho → pousio** (sem maiúscula nem
acento). O resumo da ficha mostra os dois ("Cristalina (uso o clima de Silvânia (GO), o lugar guardado mais
próximo)"), os dois entram no selo, e mudar um deles pede o "sim" de novo. A conta do motor não é estendida para a
sequência nova: os números são os da rotação guardada, e a resposta diz qual é.

Com a ficha confirmada, toda resposta termina numa indicação ("A indicação: ..."): o que a conta mostra de melhor em
cada caminho para o que mais preocupa o produtor, com os números lado a lado; a decisão continua dele, com o
agrônomo. O que a IA sabe da cultura de fora entra numa frase curta, sem número, marcada como conhecimento geral. O
programa garante: se há campo "dito" e o texto não diz "conhecimento geral", ele acrescenta a frase; e as frases
prontas também trazem a rotação parecida, a evidência dela, o lugar do clima e o benefício de cada caminho.

## As conversas guardadas

    python3 -m orbita.exportar_conversas <pasta>            # com a chave no ambiente: a IA de verdade escreve
    python3 -m orbita.exportar_conversas <pasta> --sem-ia   # sem chave: as frases prontas

Grava `conversas.js` (`window.ORBITA_CONVERSAS = {...};`, o que a tela lê) e `conversas.json` (o mesmo objeto). São 6
conversas, na ordem: `antes-plantei-tarde` (Rio Verde, soja plantada em 10 de novembro: milho ou sorgo? e a
braquiária?), `replay-2015-16` (o momento "durante": primeiro "como está a minha lavoura?", com o painel dos seis
indicadores, e depois a pior safra, dia a dia, com os dias e os marcos em `replay`), `depois-o-que-a-terra-mostrou`
(o que o satélite viu e o registro da safra 2015-16), `sem-conta-pragas-e-adubo` (sai com o aviso de conhecimento
geral), `fora-da-lista-sorgo-e-milho` ("planto sorgo e milho em Jataí, o que você indica?") e
`fora-da-lista-cristalina-feijao` ("sou de Cristalina e planto feijão depois da soja"). Cada conversa diz em
`texto_de` se o texto é da IA ou de frases prontas. Cada texto é conferido de novo contra a conta ao gravar; se sobrar
número, nada é gravado. Com a IA, cada conversa é tentada até 3 vezes e fica a melhor: sem fala barrada, sem replay
que o produtor não pediu, sem duas respostas com o mesmo começo, sem "hoje é tal dia", sem palavra da conta sem
explicação, terminando numa indicação e sem fala de mais de 900 caracteres. Rodar de novo sempre que o motor mudar.

**As que estão guardadas** (`conversas-guardadas/`): gravadas de novo em 2026-11-15, 09h07 a 09h10, com o Claude
Haiku 5.5 e o motor da rodada do alinhamento (o painel da lavoura, as frases curtas, a indicação). São 6 conversas e
16 falas do agente: 10 com o texto da IA e 6 com frases prontas (a ficha para conferir); nenhuma barrada pela
conferência dos números; todas as respostas com a conta terminam em "A indicação:", e as falas da IA têm de 565 a 770
caracteres. Foram 2 gravações seguidas, lidas uma a uma contra a conta. Ficaram as conversas da segunda (feita depois
de três acertos no pedido à IA: os prazos contam da data do dado, sem "daqui a"; "o pior ano", não "a safra mais
seca"; lugar que não está guardado pede a consulta do clima do lugar mais próximo) e a `sem-conta-pragas-e-adubo` da
primeira, trocada inteira pelo `id` nos dois arquivos, sem mexer em texto nenhum: na segunda a IA consultou a conta
também nessa resposta, e ela saiu com o apoio `conta` no lugar de `conhecimento_geral`, que o teste das guardadas
exige em pelo menos uma fala. O que a leitura achou e ficou: na conversa do painel a IA escreveu "a soja não está com
sede agora" (o dado é de 14/11/2026, dito no começo da resposta); na `fora-da-lista-sorgo-e-milho` a rotação parecida
foi a soja → milho safrinha → pousio, escolhida pelo programa no empate (na primeira gravação a IA tinha escolhido a
do sorgo); e na `fora-da-lista-cristalina-feijao` a ficha guardou o dito como "soja e feijão depois da soja". A cópia
que a tela lê (`frontend/`) não foi trocada aqui: é da parte da tela.

## O uso de verdade (2026-11-15)

- **Pela rota, de ponta a ponta:** a API ligada em `127.0.0.1`, com a chave só no ambiente do processo, o motor de
  verdade e o Claude Haiku 5.5. Uma conversa inteira por HTTP: "oi", a ficha, "sim", a comparação de 3 rotações, o
  replay da safra 2015-16 (366 dias), uma pergunta de pragas (saiu com o aviso de conhecimento geral) e "obrigado".
  Nenhum número barrado ficou no texto. O registro do terminal só tem o método, a rota e o código da resposta.
- **Os dois modelos, com as mesmas perguntas:** o Claude Haiku 5.5 e o DeepSeek V4.1 Flash responderam às 4 conversas
  sem nenhuma fala barrada no fim (13 falas cada, 9 com o texto da IA). Empate na conferência dos números: ficou o
  padrão, o Haiku 5.5; o DeepSeek é a reserva (`ORBITA_MODELO=deepseek/deepseek-v4.1-flash`).
- **O que o uso de verdade mostrou, e foi consertado:** o texto da IA saía cortado no meio (ela gastava o espaço
  pensando: agora pensa pouco, tem mais espaço e um texto cortado só vale até a última frase inteira); um "30%" de
  conhecimento geral passava por haver um 30 na conta (agora, sem consulta, o texto não pode ter número); a IA
  escreveu "coberta só 30 dias" (agora barrado); a resposta pronta saía longa demais (agora é curta).
- **O gasto:** 0,27 dólar da chave do hackathon, somando todos os ensaios e as gravações (o teto era 5). Uma conversa de 4 falas
  custa perto de meio centavo de dólar.
  As 3 gravações de 2026-11-15, 03h14 a 03h18, custaram mais 0,05 dólar (61 pedidos).
  As 3 gravações de 2026-11-15, 03h33 a 03h36, custaram mais 0,05 dólar (60 pedidos; o uso da chave, medido no
  OpenRouter, foi de 0,3207 para 0,3735 dólar, de um limite de 5).
  A rodada do alinhamento, em 2026-11-15, 08h48 a 09h10: 5 gravações (3 ensaios para afinar o pedido e 2 de prova),
  0,19 dólar pela soma do que o programa mediu em cada uma (0,0455 + 0,0371 + 0,0282 + 0,0335 + 0,0420).

## O uso de IA, declarado

- **No produto:** o texto do agente é escrito por um modelo de linguagem, chamado pelo OpenRouter. O padrão é o Claude
  Haiku 5.5, da Anthropic (`anthropic/claude-haiku-5.5`); a reserva testada é o DeepSeek V4.1 Flash
  (`deepseek/deepseek-v4.1-flash`). Os números não são da IA: saem do motor, e o texto é conferido contra eles.
- **No código:** estes arquivos foram gerados com IA (Claude, da Anthropic) e revisados por outra IA (GPT), em duas
  voltas: a primeira achou 4 defeitos (a confirmação que quem chama podia forjar, um argumento da IA que liberava um
  número, uma resposta sem a comparação e um número partido no histórico); os 4 foram consertados, cada um com o teste
  que falhava antes, e a segunda volta aprovou.
- **O que é marcado:** cada resposta diz `texto_de` (IA ou frases prontas) e `apoio` (a conta, os dados do lugar ou
  conhecimento geral). O que a conta não mede (nutrientes, pragas, mercado) sai como conhecimento geral, com o aviso.

## Os limites

- A conferência olha se cada número do texto existe na conta; ela não confere a que coisa o número se refere, nem o
  sinal, nem número por extenso (o começo do `conferencia.py` lista tudo). Uma frase que compara errado dois números
  certos ("mais perto de") pode passar: por isso o pedido à IA proíbe conta de cabeça, e a comparação lado a lado
  sai sempre do motor, não da IA. As únicas trocas de sentido que o programa barra sozinho são a dos dias de terra coberta e a
  de "a água acabou" dito do dia em que a sede começou; as outras dependem de alguém ler (as conversas guardadas foram lidas uma a uma).
- O selo da confirmação vale enquanto a API está ligada: desligou e ligou, o produtor confirma a ficha de novo.
- O texto de conhecimento geral (pragas, adubo, mercado) não é conferido por conta nenhuma: só não pode ter número, e
  sai marcado.
- A IA entende português livre, mas a ficha só tem as cidades e as rotações que o motor tem.
- A rota precisa de internet e de uma chave paga; sem elas, valem as conversas guardadas.
- Não há WhatsApp ligado, nem senha na API, nem limite de pedidos.
