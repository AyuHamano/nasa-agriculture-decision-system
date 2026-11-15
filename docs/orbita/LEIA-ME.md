<!-- Gerado com IA (Claude) -->
# Órbita Rural · o controle de missão da lavoura

English version: [README.en.md](README.en.md)

## 1. O que é

O Órbita Rural é o aplicativo da **Equipe Agronautas** no NASA Space Apps Challenge 2026, no desafio "Field Shift: Adapting Farms with NASA Data". Ele acompanha a lavoura o ano inteiro com os dados abertos da NASA:

- **Antes de plantar, o produtor ensaia.** "Plantei a soja tarde: ainda vale o milho ou vou de sorgo?" O aplicativo põe a rotação dele ao lado de outras duas e mostra como cada uma atravessou dez safras de clima de verdade: a água que faltou, o calor forte e os dias de terra sem planta viva.
- **Durante a safra, ele acompanha.** A tela "Minha lavoura hoje" mostra a fase da cultura, a água na terra, o calor, o verde visto do satélite, a terra coberta e um aviso: se não chover, em quantos dias a lavoura começa a passar sede.
- **Depois de colher, ele registra.** A safra fica guardada: o que foi plantado e o que a terra mostrou.

Um assistente de IA conversa com o produtor em português simples. Ele não cria número: todo número sai da conta e é conferido antes de aparecer. A decisão continua com o produtor e com o agrônomo dele.

Este projeto usa dados públicos da NASA. Não é um produto da NASA e não tem o apoio dela.

## 2. A história: o controle de missão da lavoura

A NASA não voa sem ensaio, sem controle de missão e sem relatório da missão. O produtor planta sem nenhum dos três. O Órbita Rural dá os três à lavoura.

| o momento | na missão | na lavoura | no aplicativo |
|---|---|---|---|
| antes de plantar | o ensaio | a rotação dele e outras duas, contra dez safras de clima de verdade | a aba **Ensaiar** |
| durante a safra | o controle de missão | a lavoura dele, hoje, na tela, com o aviso de sede | a aba **Hoje** ("Minha lavoura hoje") |
| depois de colher | o relatório da missão | o registro da safra, que vira histórico de um ano para o outro | a aba **Registrar** |

O controle de missão é o coração do projeto. Em Rio Verde, na safra de 2016, a conta mostra a sede do milho começando em 4 de abril e a água acabando em 24 de abril. Entre um dia e o outro foram 20 dias: é o tempo que o aviso de sede põe na mão do produtor.

**A dor de onde partimos.** Planejar a safra com o clima mudando, a água que falta na fase crítica da planta, o calor extremo e a terra que perde matéria orgânica estão no levantamento "Dores do Agro 2026", do IFAG: dores listadas por técnicos e validadas por 80 produtores de Goiás.

## 3. Como o produtor usa, em 5 passos

1. **Conta da lavoura.** Ao abrir, o assistente pergunta onde fica a lavoura, o que ele planta, quando planta a soja e como é a terra. Cada pergunta tem botões; quem prefere, escreve. No fim ele confere a ficha e confirma.
2. **A lavoura fica guardada no aparelho.** Na volta, o aplicativo abre direto em "Minha lavoura hoje".
3. **Hoje.** Ele vê como a lavoura está: a situação (tranquilo, atenção ou alerta), o aviso de sede e os outros cinco indicadores, cada um com a data do dado. "Entender" abre a explicação inteira.
4. **Ensaiar.** Antes de plantar, ele vê a resposta em uma frase, os 3 caminhos lado a lado com 3 medidas (a água que falta, o calor forte na fase crítica, os dias seguidos de terra sem planta viva) e uma linha de risco por caminho. "Ver a prova" abre as fontes; "Ver um ano ruim" mostra a safra ruim da cidade, dia a dia.
5. **Registrar e perguntar.** Depois de colher, ele vê o registro da safra e pode anotar quanto colheu. O botão "Perguntar", em qualquer tela, abre o assistente, que já conhece a ficha da lavoura e diz de onde saiu cada resposta: da conta, dos dados da NASA do lugar ou de conhecimento geral.

## 4. "Minha lavoura hoje": um exemplo de verdade

Rio Verde (GO), soja plantada em 15/10/2026, terra média. A consulta foi feita em 2026-11-15 (`python3 -m orbita.perguntar --lavoura-hoje`); cada linha traz a data do dado.

| o indicador | o que a tela mostrou | data do dado |
|---|---|---|
| a lavoura hoje | **atenção**: a soja tinha 30 dias, em crescimento, sem sede; pedem atenção o calor e o aviso de sede | 14/11/2026 |
| o aviso de sede | se não chover, a soja começa a passar sede em 7 dias, em 21/11/2026 (nos últimos 7 dias a lavoura bebeu em média 4,1 mm por dia) | 14/11/2026 |
| a água | 66,0 mm ao alcance da planta, 100% do que a terra segura; no mesmo dia do ano normal (safra 2019-20) havia 58,4 mm, e no do pior ano (safra 2015-16), 63,4 mm | 14/11/2026 |
| a fase da cultura | 30 dias do plantio, em crescimento; a fase crítica (a floração e o enchimento do grão) começa em 24/11/2026 | 14/11/2026 |
| o calor | 2 dias de calor forte desde o plantio (máxima acima de 40 °C, o limite da soja); nas 10 safras guardadas, até o mesmo dia do ciclo, o valor do meio foi 0 (de 0 a 6); a máxima mais alta foi 40,7 °C, em 07/11/2026 | 12/11/2026 |
| o verde do satélite | 0,41, numa medida que vai de 0 a 1, dentro do normal para a época (valor do meio dos outros anos: 0,38; de 0,26 a 0,46) | imagem de 16/10/2026 (junta 16 dias) |
| a terra coberta | planta viva há 31 dias seguidos; antes disso, 122 dias seguidos sem planta viva | 14/11/2026 |

A resposta termina com "Converse com o agrônomo antes de decidir." O aviso de sede não é previsão do tempo: é a conta da água seguida para a frente sem chuva nenhuma; a chuva que cair muda a conta.

**E o ensaio, no mesmo lugar.** Um produtor de Rio Verde plantou a soja em 10 de novembro e pergunta: milho ou sorgo? (`python3 -m orbita.perguntar --cidade rio_verde --rotacao soja,milho --plantio 2026-11-10`)

| no pior ano (safra 2015-16) | soja e milho | soja e milho com capim | soja e sorgo |
|---|---|---|---|
| a água que faltou (mm) | 252,7 | 252,7 a 263,5 | **220,3** |
| os dias de calor forte na fase crítica | 9 | 9 | **0** |
| os dias seguidos de terra sem planta viva | 122 | **30** | 122 |

## 5. Como o projeto responde ao desafio

O desafio pede uma ferramenta de apoio à decisão que junte observações da Terra da NASA, dados do solo do lugar, características das culturas e prioridades do agricultor, para ele explorar rotações de culturas, sem substituir o juízo dele nem o conhecimento agrícola local.

| o que o desafio pede | como o Órbita Rural responde |
|---|---|
| dados da NASA | a chuva por satélite (GPM IMERG), a temperatura (NASA POWER) e o verde da lavoura (MODIS), três dos citados pelo nome no desafio |
| dados do solo do lugar | o tipo de terra da ficha (arenosa, média, argilosa) vira a água que a terra segura, pelos valores do ZARC |
| características das culturas | o calendário, o pedido de água e o limite de calor da soja, do milho, do sorgo e da braquiária, cada valor com a fonte e a etiqueta "publicado" ou "hipótese" |
| prioridades do agricultor | a conta roda com a lavoura dele (o lugar, a rotação, a data do plantio, a terra); o que mais preocupa (a água, o calor ou a terra) muda a ordem e o destaque, nunca os números |
| comparar pelo menos 3 rotações, contando a de hoje | todo ensaio traz 3 caminhos: soja, milho e pousio; soja e milho com braquiária; soja e sorgo |
| a evidência, o benefício, o risco e a lacuna de cada uma | as quatro frases de cada rotação, montadas só com números da conta; na tela, uma linha de risco por caminho e o resto em "Ver a prova" |
| comparar o satélite com medida em terra | a chuva do satélite contra 27 estações do INMET em Goiás e no Distrito Federal (seção 7) |
| marcar terra sem planta e estresse da cultura | os dias sem planta viva (pelo calendário e pelo satélite), os dias de sede, os dias de calor forte e o aviso de sede |
| comunicar a incerteza | a rotação com capim sai em faixa; cada indicador do painel traz a data do dado; os valores que são hipótese vêm marcados |
| entendível por quem não é técnico; o juízo humano | palavras do campo ("falta de água", "dias de sede", "terra sem planta viva"), botões em vez de formulário, "Entender" em cada cartão e a leitura do agrônomo no rodapé; toda resposta termina com "Converse com o agrônomo antes de decidir." |

## 6. Os dados da NASA em cada indicador

| o indicador | o dado da NASA | o que mais entra |
|---|---|---|
| a água na terra e o aviso de sede | a chuva do satélite GPM IMERG (a série de 10 safras e a chuva de cada dia até a véspera) e a temperatura da NASA POWER, que dá o pedido de água da planta | a conta da água do manual FAO-56 |
| o calor | a temperatura máxima de cada dia, da NASA POWER | o limite de cada cultura, de fonte publicada (Embrapa e FAO) |
| o verde do satélite | o NDVI do MODIS (produto MOD13Q1, 250 m, uma imagem a cada 16 dias) | 6 pontos de lavoura por cidade |
| a terra coberta | o verde do MODIS confere o calendário | o calendário da rotação |
| a fase da cultura | (vem do calendário) | o calendário da rotação e as fases da tabela da FAO |
| a falta de água do ensaio e do registro | a chuva do GPM IMERG e a temperatura da NASA POWER, dia a dia, em 10 safras | a conta da água do manual FAO-56 |

O endereço de cada consulta, o período, a licença e onde cada dado está guardado: [DADOS-E-FONTES.md](DADOS-E-FONTES.md).

## 7. A prova: testamos em Goiás

- **20 de 20 municípios.** Nos 20 municípios de Goiás que mais plantam milho safrinha, em dez safras, onde a conta apontou mais falta de água a colheita registrada pelo IBGE foi menor. Nos 20. Na média da região, ano a ano, a relação entre as duas é de −0,72 (numa medida em que 0 é não ter relação e −1 é a colheita cair sempre que a falta de água sobe).
- **21 de 27 estações.** A chuva do satélite ficou mais perto da chuva medida no chão do que a chuva de modelo em 21 de 27 estações do INMET: 16 de 22 em Goiás e 5 de 5 no Distrito Federal.

O método, os números de cada município e de cada estação e como refazer os dois testes: [VALIDACAO.md](VALIDACAO.md) e a pasta [validacao-regional/](validacao-regional/).

## 8. Como rodar

Precisa só do Python 3 (biblioteca padrão). Os comandos abaixo foram rodados em 2026-11-15 e funcionaram.

**Os testes**, de dentro de `backend/`:

    python3 -m unittest

Mais de 500 testes automáticos, nenhuma falha, em cerca de um minuto.

**O painel, o ensaio, o ano ruim e o registro**, de dentro de `backend/`:

    python3 -m orbita.perguntar --lavoura-hoje                                               # "Minha lavoura hoje" (Rio Verde)
    python3 -m orbita.perguntar --cidade rio_verde --rotacao soja,milho --plantio 2026-11-10 # o ensaio das 3 rotações
    python3 -m orbita.perguntar --replay 2015-16                                             # o ano ruim, dia a dia
    python3 -m orbita.perguntar --registro 2015-16                                           # o registro da safra
    python3 -m orbita.validar                                                                # as conferências de Rio Verde

As cidades: `rio_verde`, `jatai`, `silvania`. Com `--json`, cada comando devolve a estrutura inteira.

**A API** (a porta por onde a tela pergunta), de dentro de `backend/`:

    python3 -m orbita.api                              # liga em http://127.0.0.1:8000 (só esta máquina)
    curl -s http://127.0.0.1:8000/saude                # diz as rotas e se a IA está ligada
    curl -s -X POST http://127.0.0.1:8000/lavoura-hoje -H 'Content-Type: application/json' \
      -d '{"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media", "plantio_da_soja": "2026-10-15"}'

A tela usa quatro rotas de conta, que respondem sem chave nenhuma: `POST /lavoura-hoje` (o painel), `POST /recomendacao` (o ensaio), `POST /replay` (o ano ruim) e `POST /registro` (o registro da safra). A pergunta livre vai ao assistente, na `POST /agente`, que precisa da chave do OpenRouter no ambiente do terminal, nunca em arquivo: `export OPENROUTER_API_KEY=...` antes de ligar a API. Todas as rotas, com exemplo: `backend/orbita/API.md`.

**A tela** (como descreve o `frontend/orbita/LEIA-ME.md`): com a API ligada, abrir `frontend/orbita/index.html?api=http://127.0.0.1:8000`. Sem a API, dois cliques em `frontend/orbita/index.html`: o aplicativo abre com os números guardados e diz de que dia eles são.

**A chuva de cada dia** é baixada por `data/orbita/chuva-do-dia/baixar_chuva_do_dia.py` (os comandos estão no LEIA-ME daquela pasta).

## 9. As peças e onde mora cada uma

| a peça | o que é | onde está |
|---|---|---|
| o motor | o programa que faz a conta (sem IA, sem chave, sem internet na hora da pergunta) | `backend/orbita/` (`README.md`, `LEIA-ME-motor.md`, `API.md`) |
| o assistente | a IA que conversa com o produtor, com as travas que conferem os números | `backend/orbita/` (`LEIA-ME-agente.md`) |
| a tela | o aplicativo do produtor: a entrada pelo assistente e as abas Hoje, Ensaiar e Registrar | `frontend/orbita/` (`LEIA-ME.md`) |
| os dados | tudo o que foi baixado, com o endereço e a hora de cada consulta | `data/orbita/` |
| os documentos | este arquivo, o uso de IA, os dados e as fontes, a validação, os testes de Goiás e o questionário para produtores | `docs/orbita/` |
| o pitch | os 7 slides em português e em inglês, o roteiro falado, o texto da submissão e o vídeo de 30 segundos | `docs/orbita/pitch/` (`LEIA-ME.md`) |

O trabalho do Órbita Rural mora nessas quatro pastas. O resto do repositório é dos outros integrantes do time.

## 10. Uso de IA

Declarado em [USO-DE-IA.md](USO-DE-IA.md) (em inglês: [AI-USE.en.md](AI-USE.en.md)).

## 11. Créditos

- **O time:** Equipe Agronautas, NASA Space Apps Challenge 2026.
- **Integrantes:** a preencher.
- **A base visual da tela:** a primeira versão partiu do painel do ramo `nat` do time, como registra o `frontend/orbita/LEIA-ME.md`. O logo e a identidade visual são do time.
- **As letras:** Anton e Montserrat, sob a SIL Open Font License 1.1 (`frontend/orbita/fontes/OFL-Anton.txt` e `OFL-Montserrat.txt`).
- **Os dados:** NASA (GPM IMERG, NASA POWER, MODIS), INMET, IBGE, FAO, Embrapa, ZARC, CHIRPS e ERA5. A chuva de cada dia vem da cópia aberta do IMERG mantida pela dynamical.org ("NASA IMERG from dynamical.org", CC BY 4.0). A lista completa está em [DADOS-E-FONTES.md](DADOS-E-FONTES.md).
- Não há logo da NASA neste projeto.

## 12. Licença

A definir pelo time. Em 2026-11-15 não havia arquivo de licença no repositório.

## 13. O alcance desta versão

- O aplicativo tem os dados guardados de três cidades de Goiás (Rio Verde, Jataí e Silvânia) e três rotações, todas começando com soja.
- Os dados são da região (o ponto da cidade), não do talhão.
- A ferramenta apoia a decisão e não substitui o agrônomo.
- O que o assistente responde por conhecimento geral (pragas, adubo, mercado), ele diz que é conhecimento geral.
