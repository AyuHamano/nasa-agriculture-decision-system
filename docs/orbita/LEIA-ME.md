<!-- Gerado com IA (Claude) -->
# Órbita Rural · o projeto inteiro, para quem chega agora

English version: [README.en.md](README.en.md)

## 1. O que é, em 5 linhas

- O Órbita Rural é a ferramenta da **Equipe Agronautas** no NASA Space Apps Challenge 2026, no desafio "Field Shift: Adapting Farms with NASA Data".
- O produtor rural conta onde planta e o que planta. O sistema faz a conta com o que os satélites da NASA registraram naquele lugar e põe a rotação dele ao lado de outras duas.
- Olha três coisas: a água que faltou para a planta, os dias de calor forte e os dias em que a terra ficou sem planta viva.
- Uma IA conversa com o produtor em português simples. Ela não cria número: todo número sai da conta e é conferido antes de aparecer.
- A ferramenta apoia a decisão. Não substitui o agrônomo, não promete lucro e não promete colheita maior.

Este projeto usa dados públicos da NASA. Não é um produto da NASA e não tem o apoio dela.

## 2. A história

"O Órbita Rural acompanha a lavoura o ano inteiro com os dados da NASA: ensaia antes de plantar, acompanha durante a safra e registra depois. E cada número tem prova."

| o momento | a pergunta do produtor | o que a ferramenta faz |
|---|---|---|
| antes de plantar | "O que eu planto agora?" | compara 3 rotações (a dele e outras duas) no ano normal e no pior ano da região |
| durante a safra | "Como está a minha lavoura?" | mostra a água na terra no último dia com dado, ao lado do mesmo dia do ano normal e do pior ano |
| depois de colher | "O que a terra mostrou?" | guarda o registro da safra: o que foi plantado, a água, o calor e os dias sem planta viva |

O pior ano (a safra 2015-16 em Rio Verde, Goiás) é a prova de que a conta acerta. Não é o produto.

**A dor de onde partimos.** Planejar a safra com o clima instável, a falta de água na fase crítica da planta, o calor extremo e a terra que perde matéria orgânica aparecem no levantamento "Dores do Agro 2026", do IFAG (dores listadas por técnicos e validadas por 80 produtores de Goiás). A citação pública desse documento ainda espera a confirmação do time.

## 3. O desafio e como o projeto responde

O desafio pede uma ferramenta de apoio à decisão que junte observações da Terra da NASA, dados do solo do lugar, características das culturas e prioridades do agricultor, para ele explorar rotações de culturas. Ela apoia e não substitui o juízo do agricultor nem o conhecimento agrícola local.

| o que o desafio pede | como o Órbita Rural responde |
|---|---|
| dados da NASA | três dos citados pelo nome no desafio: a chuva por satélite (GPM IMERG), a temperatura (NASA POWER) e o verde da lavoura (MODIS) |
| dados do solo do lugar | o tipo de solo do cadastro (arenoso, textura média, argiloso) vira a água que a terra segura, pelos valores do ZARC |
| características das culturas | o calendário, o pedido de água e o limite de calor da soja, do milho, do sorgo e da braquiária, cada valor com a fonte e a etiqueta "publicado" ou "hipótese" |
| prioridades do agricultor | ele diz, na conversa, o que mais preocupa (a água, o calor ou a terra); isso muda a ordem e o destaque, nunca os números |
| comparar pelo menos 3 rotações, contando a de hoje | toda resposta com a ficha confirmada traz 3 rotações: soja, milho e pousio; soja, milho com braquiária; soja e sorgo |
| a evidência, o benefício, o risco e a lacuna de cada uma | as quatro frases de cada rotação, montadas só com números da conta |
| comparar o satélite com medida em terra | a chuva do satélite contra a estação do INMET de Rio Verde (seção 7) |
| marcar terra sem planta e estresse da cultura | os dias sem planta viva (pelo calendário e pelo satélite), os dias de sede e os dias de calor forte |
| comunicar a incerteza | a rotação com capim sai em faixa; a água de hoje sai em faixa; 30 valores da conta são marcados como hipótese |
| explicar os termos técnicos | as respostas usam palavras do campo ("falta de água", "dias de sede", "sem planta verde") e dizem o que cada uma quer dizer; a aba "Agrônomo" da tela mostra como a conta foi feita |
| entendível por quem não é técnico; o juízo humano | conversa em português simples; toda resposta termina com "Converse com o agrônomo antes de decidir." |

O que o desafio cita e a conta não mede: nutrientes, pragas e mercado. Sobre isso o agente responde como conhecimento geral, com aviso, e sem número.

## 4. As três pernas

| a perna | o que mede | que dado alimenta |
|---|---|---|
| a água | a falta de água dia a dia, por safra (o que a planta pediu menos o que conseguiu beber) | a chuva do satélite GPM IMERG, da NASA; a temperatura da NASA POWER; a conta do manual FAO-56 |
| o calor | os dias de calor forte na fase crítica de cada cultura | a temperatura máxima da NASA POWER; o limite de cada cultura, de fonte publicada (Embrapa e FAO) |
| a terra coberta | os dias seguidos sem planta viva | o calendário das culturas e o verde do satélite MODIS (o NDVI, um índice do verde das folhas) |

Os endereços, os períodos e onde cada dado está guardado: [DADOS-E-FONTES.md](DADOS-E-FONTES.md).

## 5. As peças e onde mora cada uma

| a peça | o que é | onde está |
|---|---|---|
| o motor | o programa que faz a conta (sem IA, sem chave, sem internet na hora da pergunta) | `backend/orbita/` (comece por `README.md` e `LEIA-ME-motor.md`) |
| o agente | a IA que conversa com o produtor, com as travas que conferem os números | `backend/orbita/` (`LEIA-ME-agente.md`; a porta de internet está descrita no `API.md`) |
| a tela | o que o produtor vê: a conversa, a ficha, as rotações lado a lado e o replay da safra ruim | `frontend/orbita/` (`LEIA-ME.md`) |
| os dados | tudo o que foi baixado, com o endereço e a hora de cada consulta | `data/orbita/` |
| os documentos | este arquivo, o uso de IA, os dados e as fontes, a validação e o questionário | `docs/orbita/` |

O trabalho do Órbita Rural mora só nessas quatro pastas. O resto do repositório é dos outros integrantes do time e não foi alterado.

## 6. Como rodar

Precisa só do Python 3 (biblioteca padrão). Os comandos abaixo foram rodados em 2026-11-15 numa cópia do ramo `jose` (commit `fe578c6`), e todos funcionaram, salvo onde está dito.

**Os testes** (programas que conferem o programa), de dentro de `backend/`:

    python3 -m unittest

Resultado nessa cópia: 440 testes, nenhuma falha, em cerca de 40 segundos.

**Uma pergunta ao motor**, de dentro de `backend/`:

    python3 -m orbita.perguntar --cidade jatai --rotacao soja,sorgo --plantio 2026-11-20   # as 3 rotações comparadas
    python3 -m orbita.perguntar --cidade jatai --verde                                     # o que o satélite viu da terra
    python3 -m orbita.perguntar --hoje                                                     # como está a água hoje (Rio Verde)
    python3 -m orbita.perguntar --replay 2015-16                                           # a safra ruim, dia a dia
    python3 -m orbita.perguntar --registro 2015-16                                         # o registro da safra
    python3 -m orbita.validar                                                              # as provas da seção 7

As cidades: `rio_verde`, `jatai`, `silvania`. Com `--json`, cada comando devolve a estrutura inteira.

**A API** (a porta por onde outro programa pergunta), de dentro de `backend/`:

    python3 -m orbita.api                              # liga em http://127.0.0.1:8000 (só esta máquina)
    curl -s http://127.0.0.1:8000/saude                # diz as rotas e se a IA está ligada

Sem chave de IA a API liga do mesmo jeito; só a rota `POST /agente` responde 503 (conferido). Para o agente ao vivo, a chave do OpenRouter vai só no ambiente do terminal, nunca em arquivo: `export OPENROUTER_API_KEY=...` antes de ligar a API. **Não conferido aqui:** a conversa ao vivo com a IA, porque esta conferência foi feita sem chave. O `LEIA-ME-agente.md` registra o uso de verdade feito em 2026-11-15.

**A tela com as respostas guardadas:** abrir `frontend/orbita/index.html` com dois cliques. Não precisa de servidor nem de internet.

**A tela ao vivo:** ligar a API (acima, com a chave) e abrir `frontend/orbita/index.html?api=http://127.0.0.1:8000`. Se a API não responder, a tela avisa e volta para as conversas guardadas. **Não conferido aqui:** a abertura da tela no navegador; os dois modos estão descritos e conferidos no `LEIA-ME.md` da tela.

**Gravar de novo o que a tela lê** (depois de mudar o motor ou o agente):

    python3 -m orbita.exportar_conversas ../frontend/orbita/dados --sem-ia    # de dentro de backend/; sem chave, frases prontas
    python3 -B frontend/orbita/dados/gerar-dados.py                           # da raiz do repositório

Os dois foram rodados numa pasta de teste e funcionaram (4 conversas, 13 falas do agente). O primeiro troca as conversas guardadas com o texto da IA por frases prontas: use sem `--sem-ia`, com a chave, para manter o texto da IA.

## 7. As provas

Os números abaixo saem de `python3 -m orbita.validar` e dos arquivos de `data/orbita/validacao/`. O detalhe está em [VALIDACAO.md](VALIDACAO.md).

**O satélite contra a estação em terra** (a estação A025 do INMET, a 4,79 km do ponto de Rio Verde; janela de fevereiro a junho; 8 safras comparadas):

| fonte da chuva | erro médio contra a estação |
|---|---|
| GPM IMERG (o satélite da NASA, o padrão do motor) | 12,1% |
| CHIRPS | 17,6% |
| ERA5 | 26,7% |
| NASA POWER (a chuva de modelo) | 33,2% |

A chuva de modelo da NASA POWER deu, em média, 86% da chuva da estação nas 4 safras comparadas até 2020 e 51% nas 4 de 2021 em diante. No ano de 2025: 678,4 mm no modelo contra 1.548,0 mm no pluviômetro. Por isso o motor usa a chuva do satélite.

**A conta contra a colheita do IBGE** (milho de 2ª safra em Rio Verde, Produção Agrícola Municipal, 10 safras, terra média):

- As 2 safras de maior falta de água do milho na conta (2021-22, com 54,8% do pedido, e 2015-16, com 49,6%) são as 2 piores colheitas no IBGE (5.100 e 3.300 kg/ha). A mediana das 10 safras é 6.725 kg/ha.
- A terceira maior falta é a de 2020-21 (45,9%), que não foi colheita ruim em Rio Verde (7.200 kg/ha).
- A correlação de postos entre a falta de água e o rendimento é de -0,52. São só 10 safras: é indício, não prova.

**O verde do satélite contra o calendário.** O calendário diz 122 dias seguidos sem planta viva na rotação com pousio. O satélite viu, na mediana, 96 dias seguidos sem planta verde em Rio Verde (36 medidas, de 16 a 160 dias), 80 em Jataí (30 medidas, de 0 a 128) e 96 em Silvânia (35 medidas, de 16 a 192). O número do calendário cabe na faixa do satélite nas três cidades.

**A safra ruim, dia a dia** (Rio Verde, 2015-16, pela conta): o milho entra em 10 de fevereiro de 2016; a sede começa em 4 de abril e dura 60 dias seguidos; em 24 de abril a água que a planta alcança chega a 0,1 mm; faltaram 220,6 mm, 49,6% do que o milho pediu. O valor de 0,1 mm é da conta, alimentada pela chuva do satélite. Ninguém mediu a terra.

## 8. Os limites, ditos com franqueza

- **Nenhum teste em lavoura de verdade.** A conta usa o clima do ponto da cidade, não o da fazenda. Nenhum produtor usou a ferramenta numa safra, e o questionário de validação ainda não tem respostas.
- **O que só vale para Rio Verde:** a comparação com a estação em terra (só há estação conferida lá) e o acerto das 2 piores colheitas. Em Jataí, o nível de "sede forte" marca as 10 safras e só uma foi colheita ruim no IBGE; em Silvânia, nenhuma safra ficou abaixo do corte, e o nível sai vazio. O pior ano de Jataí pela colheita teve menos falta de água na conta do que o ano normal, e a resposta diz isso.
- **Os "12%" de erro do satélite valem para a série longa** (8 safras, de fevereiro a junho). Não valem para a chuva recente.
- **A chuva recente sai em faixa larga.** O caminho rápido (2 dias de atraso) lê a chuva da cor de uma imagem da NASA. Em 50 dias de setembro e outubro de 2026, contra a estação de Rio Verde, o satélite deu de 32% a 38% a mais e a chuva de modelo, 45% a menos. Por isso o "como está hoje" mostra a conta com as duas chuvas e a faixa entre elas.
- **Os pontos do verde do satélite foram escolhidos no mapa.** Não se sabe de quem são nem o que foi plantado, e ninguém conferiu em campo. Os anos de 2024 e 2025 ficaram de fora (faltam imagens no serviço consultado). O satélite mede o verde das folhas e não vê a palha.
- **O que é hipótese:** 30 valores da conta, listados na resposta do motor. Entre eles: o quanto o capim disputa água com o milho (por isso a faixa), a cobertura de palha, o pedido de água do sorgo no meio do ciclo, a raiz do sorgo, a fase crítica de cada cultura e o uso da temperatura máxima do dia no calor.
- **Dia de calor forte não é perda de safra, e falta de água não é quebra.** A conta não mede renda, preço, custo nem produtividade. A temperatura é a de um quadrado de uns 50 km.
- **A IA.** A conferência olha se cada número do texto existe na conta. Ela não confere a que coisa o número se refere. As conversas guardadas foram lidas uma a uma por isso.
- A tela é só em português. A API não tem senha e só deve rodar na própria máquina.

## 9. Os próximos passos

- Levar o questionário a produtores e publicar a contagem das respostas.
- Testar com produtores e agrônomos numa safra de verdade, e conferir em campo os pontos do verde do satélite.
- A chuva recente exata de cada dia, em mm, pelo GES DISC da NASA (pede uma conta Earthdata, grátis).
- Comparar com mais estações em terra, também em Jataí e Silvânia.
- Fases, ciclo e raiz do sorgo de 2ª safra medidos em Goiás.
- A tela em inglês, o painel da cooperativa (acompanhar vários produtores) e a conversa pelo WhatsApp.

## 10. Uso de IA

Declarado em [USO-DE-IA.md](USO-DE-IA.md) (em inglês: [AI-USE.en.md](AI-USE.en.md)).

## 11. Créditos

- **O time:** Equipe Agronautas, NASA Space Apps Challenge 2026.
- **Integrantes:** a preencher.
- **A base visual da tela:** a primeira versão partiu do painel do ramo `nat` do time, como registra o `frontend/orbita/LEIA-ME.md`. O logo e a identidade visual são do time.
- **As letras:** Anton e Montserrat, sob a SIL Open Font License 1.1 (`frontend/orbita/fontes/OFL-Anton.txt` e `OFL-Montserrat.txt`).
- **Os dados:** NASA (GPM IMERG, NASA POWER, MODIS), INMET, IBGE, FAO, Embrapa, ZARC, CHIRPS e ERA5. A lista completa está em [DADOS-E-FONTES.md](DADOS-E-FONTES.md).
- Não há logo da NASA neste projeto.

## 12. Licença

A definir pelo time. Em 2026-11-15 não havia arquivo de licença em nenhum ramo do repositório.
