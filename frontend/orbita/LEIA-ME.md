# Órbita Rural · o aplicativo do produtor

É o que o produtor vê do Órbita Rural, o projeto da **Equipe Agronautas** no NASA Space Apps Challenge 2026
(desafio "Field Shift: Adapting Farms with NASA Data"). Ele cadastra a lavoura numa conversa curta com o assistente e
passa a ter três telas: **Hoje** (como a lavoura está), **Ensaiar** (antes de plantar) e **Registrar** (depois de
colher). A tela **não faz conta**: mostra o que o motor e o agente (em `backend/orbita/`) devolvem.

## Como abrir

- **No servidor** (o jeito de uso): a tela acha a API sozinha. Aberta por `http(s)` sem nenhum parâmetro, ela procura
  a API em `/api` do mesmo endereço (`GET /api/saude`): se a resposta é a do motor, usa; se não (404, erro, demora),
  usa os dados guardados, sem aviso de erro. A pergunta é feita uma vez só, e toda tela espera por ela.
- **Com a API em outro endereço:** `index.html?api=http://127.0.0.1:8000` (ou o endereço em `API_BASE`, no
  `js/textos.js`); tem prioridade sobre o `/api`. Para ligar a API, de dentro de `backend/`: `python3 -m orbita.api`
  (a IA do assistente precisa da chave no ambiente; veja o `LEIA-ME-agente.md`).
- **Sem a API:** dois cliques em `index.html`. Não precisa de servidor nem de internet: as letras, o logo e os ícones
  estão nesta pasta, e os números vêm dos dados guardados em `dados/` (aberta como arquivo, a tela não procura a
  API). Uma linha discreta no topo diz isso ("Dados guardados em 15/11.").

## O que tem na tela

- **A tela de boas-vindas.** Quem ainda não tem lavoura guardada vê primeiro o logo, o lema, um texto curto (em
  `js/textos.js`, chave `welcome.text`) e o botão "Iniciar", que abre a conversa abaixo. Quem já tem lavoura guardada não a
  vê: o aplicativo abre direto em "Minha lavoura hoje".
- **A entrada: o assistente monta a ficha.** Ele pergunta onde fica a lavoura (Rio Verde, Jataí ou Silvânia), qual é o
  ciclo de plantio dele hoje (soja e depois milho, milho com capim ou sorgo), quando plantou, ou vai plantar, a soja desta safra (de setembro a dezembro,
  no dia 15, ou "Escolher o dia") e como é a terra (arenosa, média ou argilosa). Cada pergunta tem botões; os toques
  montam a ficha sem IA. Quem prefere escrever, escreve: o texto vai ao assistente (`POST /agente`), e o que ele
  anotar entra na ficha. Quando ele diz um lugar ou uma rotação fora da lista, a resposta traz `lugar_dito` e
  `rotacao_dita`: a ficha mostra a cidade e a rotação da conta e, embaixo, "Você disse: ..."; os dois ficam guardados
  com a lavoura e vão junto nas perguntas ao assistente. Sem a IA, a tela lê as palavras mais simples do texto (o nome da cidade, da cultura, da
  terra, o mês) e pede o toque no que faltar. No fim o produtor confere a ficha e confirma.
- **A lavoura fica guardada no aparelho** (no armazenamento do navegador, chave `orbita.lavoura.v1`). Ao voltar, o
  aplicativo abre direto em "Minha lavoura hoje". O botão com o nome da cidade, no topo, mostra a ficha e tem
  "Trocar de lavoura".
- **Hoje · "Minha lavoura hoje"** (`POST /lavoura-hoje`): o quadro do topo com a situação (tranquilo, atenção ou
  alerta), uma frase que diz o que pede atenção e até que dia vai a chuva do satélite; e seis cartões, cada um com o número grande, a
  situação e uma frase curta: o aviso de sede, a água na terra (com o mesmo dia do ano normal e do ano ruim), a fase
  da cultura, o calor, o verde do satélite e a terra coberta. "Entender" abre a frase inteira do motor.
- **Ensaiar** (`POST /recomendacao`): a dica em uma frase (o caminho que fica na frente em mais das 3 medidas), a linha
  que diz de que ano ruim a tabela fala, os 3 caminhos lado a lado com 3 medidas (a água que
  falta, o calor forte na fase crítica, os dias seguidos de terra sem planta viva; o melhor número de cada linha vem
  marcado; a falta de água do milho com capim, que o motor dá em faixa, aparece com o número do meio, o do cenário
  `meio` em `comparacao.agua.pela_faixa.por_cenario`, e a faixa inteira fica em "Ver a prova"), uma linha de risco
  por caminho (o `risco` curto do motor), o aviso curto do motor (`aviso`), o botão "Ver a prova" (as
  frases de prova do motor, o que falta saber e as fontes, recolhidas) e o botão "Ver um ano ruim".
- **O ano ruim, dia a dia** (`POST /replay`; só atrás do botão do ensaio): a safra do pior ano da cidade, com a
  chuva, a água na terra descendo, os dias de sede e de calor forte e os marcos. Tem tocar, pausar, voltar,
  velocidade e tela cheia. O ponto alto é o dia em que a água acaba (o marco `agua_no_fundo` com `situacao:
  "acabou"`); o dia em que a sede começa (`agua_acabou`) vem antes, como o aviso. É o `js/replay.js`, sem mudança.
- **Registrar** (`POST /registro`): a safra que terminou (a mais recente, ou outra da lista): o que foi plantado, a
  água que faltou, os dias de calor forte e de terra sem planta, e onde a safra ficou entre as guardadas. O produtor
  pode escrever quanto colheu (sacas por hectare) e guardar: fica só no aparelho (`orbita.safras.v1`).
- **O assistente à mão:** o botão "Perguntar", em qualquer tela, abre a conversa (`POST /agente`). Ele já recebe a
  ficha da lavoura; a resposta diz de onde saiu (da conta, dos dados da NASA do lugar ou de conhecimento geral).
- **Para o agrônomo:** o link do rodapé abre a leitura técnica (como a conta foi feita, os valores, as fontes, as
  hipóteses e os limites), com a resposta completa do motor para baixar.

## De onde vêm os números

Com a API, cada tela pede a rota dela. Se a rota não responde (sem servidor, sem internet, ou API antiga, sem as
rotas `/replay` e `/registro`), a tela usa o dado guardado e diz isso em uma linha. O assistente, sem a API ou sem a
chave da IA, avisa que está sem conexão; o resto funciona.

| arquivo | quem grava | o que traz |
|---|---|---|
| `dados/guardados.js` | `gerar-dados.py` | o painel (a resposta do `/lavoura-hoje`) e o ensaio (os campos do `/recomendacao` que a tela lê) das 3 cidades, 3 rotações e 3 terras; o registro (a safra mais recente e o pior ano) das 3 cidades e 3 rotações, em terra média |
| `dados/guardados-replay.js` | `gerar-dados.py` | a safra dia a dia do pior ano de cada cidade e rotação, em terra média |
| `dados/respostas.js` e `respostas.json` | o motor (`orbita.exportar`), chamado pelo `gerar-dados.py` | a resposta inteira do motor para os três tipos de terra (a leitura do agrônomo) |
| `dados/complementos.js` e `validacao.js` | `gerar-dados.py` | o calendário do ano e a validação cruzada (a leitura do agrônomo) |

Os guardados valem para a soja no dia de costume (15/10) e são do dia em que o programa rodou: a linha discreta
diz a data e, se o plantio do produtor for outro, que o guardado é o de 15/10. Os arquivos guardados só são
baixados quando fazem falta. Nenhum número é escrito à mão nesta pasta.

**Como gerar tudo de novo** (depois de mudar o motor), da raiz do repositório:

    python3 -B frontend/orbita/dados/gerar-dados.py

As fontes: a chuva é do GPM IMERG (a chuva medida por satélite da NASA); a temperatura, do NASA POWER; o verde da
lavoura, do satélite MODIS, da NASA; a conta da água segue o manual FAO-56; a colheita é do IBGE e a chuva medida em
terra é da estação do INMET. O caminho de cada dado está em `data/orbita/`.

## Como a tela escreve

- **Números:** os milímetros com uma casa ("66,0 mm"); os dias, inteiros; o verde do satélite, com duas casas.
- **Datas:** dia e mês nos cartões (21/11) e a data inteira na linha do topo do Hoje e no "Dado de" do "Entender" (14/11/2026); na ficha, por extenso.
- **Frases curtas:** a frase do topo do painel, a de cada cartão e a dica do ensaio são montadas pela tela com os
  campos da resposta (a situação de cada item, os números, e quem ficou `melhor` em `contra_as_outras`: a dica conta em quantas das 3
  medidas cada caminho tem o número em destaque na tabela): nenhuma
  conta, nenhum número novo. A frase inteira do motor está em "Entender" e em "Ver a prova". A linha de risco é a
  primeira frase do `risco` do motor.
- **A data do dado** aparece na linha pequena do topo do Hoje ("Chuva do satélite até ontem, DD/MM/AAAA."; "ontem",
  "hoje" e "há N dias" saem de `atraso_dias`, e só quando o `hoje` da resposta é o dia do aparelho), no cartão do
  calor ("até DD/MM") e, dentro do "Entender" de cada cartão, como "Dado de DD/MM/AAAA". O aviso é o curto do motor (`aviso`); o texto
  técnico (`aviso_tecnico`, `detalhe_tecnico`, `risco_detalhe`, `falta_saber_detalhe`) não aparece para o produtor.
- **Letras e dedos:** nenhuma letra abaixo de 13 px; botões com 44 px ou mais; nenhuma rolagem de lado.

## A rodada do alinhamento (2026-11-15)

A tela deixou de ser uma demonstração com conversas gravadas e virou o aplicativo descrito acima: a entrada no
assistente, a lavoura guardada, "Minha lavoura hoje" como tela inicial, o ensaio enxuto, a safra de 2016 só atrás do
botão "Ver um ano ruim", o registro, o assistente à mão e a leitura do agrônomo no rodapé. Conferido num navegador,
em 390 px e em 1280 px, com a API ligada (as três cidades, a ficha pelos botões e por texto, uma pergunta livre) e
sem ela (aberta como arquivo).

## Os arquivos

    index.html              a página: a barra, as três telas, o assistente, o ano ruim
    app.css                 o estilo do aplicativo (a casca, os cartões, a conversa, o ensaio, o registro)
    styles.css              as cores e as letras da marca, a safra dia a dia e a leitura do agrônomo
    app.js                  liga as peças: a entrada, a lavoura guardada, as telas, o assistente, o agrônomo
    js/dados.js             acha a API (o "?api=", ou "/api" do mesmo endereço), busca nela e, se ela não responde, nos dados guardados
    js/telas.js             desenha "Minha lavoura hoje", "Ensaiar" e "Registrar"
    js/replay.js            a safra dia a dia
    js/comparacao.js        funções de escrita (números, datas) que a safra dia a dia usa
    js/textos.js            os textos da safra dia a dia e da leitura do agrônomo (e o endereço da API, em API_BASE)
    js/icones.js            os ícones, desenhados aqui mesmo
    js/adaptar.js, js/resultado.js, js/textos-agronomo.js   a leitura do agrônomo (só carregam quando ela abre)
    dados/                  os dados guardados (tabela acima) e o gerar-dados.py
    marca/                  o logo do time
    fontes/                 as letras (Anton e Montserrat), com a licença de cada uma

## A marca

A marca é a da Equipe Agronautas, tirada do pitch do time: o logo (um satélite sobre faixas de lavoura), o
verde-escuro sobre o fundo quase branco, os títulos em Anton e o texto em Montserrat, e o lema "Inteligência do
espaço. Decisões para a terra.". As cores da água, do calor e da terra coberta foram acrescentadas pela tela. Não há
logo da NASA.

## Uso de IA

- Esta tela foi programada com apoio de IA (Claude, da Anthropic), com as decisões e a conferência do time.
- O assistente escreve com IA; todo número do texto dele é conferido com a conta antes de aparecer (isso é feito no
  agente, em `backend/orbita/`). A IA não escolhe a rotação pelo produtor: a ferramenta apoia a decisão e manda
  conversar com o agrônomo.

## Créditos e licenças

- O logo e a identidade visual são do time (o arquivo do logo veio do pitch).
- A primeira versão desta tela partiu do painel do ramo `nat` do time (de nathancabrall); a leitura do agrônomo e o
  `js/adaptar.js` vêm dela.
- As letras Anton e Montserrat são distribuídas sob a SIL Open Font License 1.1 (`fontes/OFL-Anton.txt` e
  `fontes/OFL-Montserrat.txt`).

## O que ainda não tem, e o que saber

- A tela é só em português, e vale para três cidades de Goiás e três rotações, todas começando com soja.
- O mês do plantio escolhido no botão vira o dia 15 daquele mês; para outro dia, "Escolher o dia".
- A ficha tem 4 perguntas; o agente pede também "o que mais preocupa". Quando o produtor não disse, a tela manda
  "água" ao agente (isso só muda a ordem e o destaque do texto dele; nenhum número muda).
- Na primeira pergunta ao assistente, a tela manda a ficha já confirmada pelo produtor junto com o "sim", para ele
  não ter de confirmar duas vezes; o selo da confirmação continua sendo posto pelo servidor.
- A colheita que o produtor escreve no Registrar fica só no aparelho: não vai ao servidor nem entra em conta.
- A leitura do agrônomo mostra a conta guardada de Rio Verde (GO), com a rotação de hoje e a rotação com capim.
- Saíram em 2026-11-15, por não ter mais quem os lesse: `js/conversa.js`, `dados/conversas.js` (as conversas gravadas
  continuam em `backend/orbita/conversas-guardadas/`) e 46 regras do `styles.css` cujas classes nenhum `.js` nem o
  `index.html` usa. O `styles.css` ainda pode ter regra da tela de antes: na dúvida, a regra ficou.
- A linha de risco do milho com capim é a frase do motor e ainda cita a faixa da água.
- O painel da cooperativa (acompanhar vários produtores) é um próximo passo e não aparece na tela.