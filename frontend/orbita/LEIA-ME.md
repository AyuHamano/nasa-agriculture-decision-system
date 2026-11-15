# Órbita Rural · a tela do produtor

A tela é o que o produtor vê do Órbita Rural, o projeto da **Equipe Agronautas** no NASA Space Apps Challenge 2026
(desafio "Field Shift: Adapting Farms with NASA Data"). Nela o produtor conversa com o agente, confere a ficha dele e
vê a rotação que planta hoje ao lado de outras, com a água, o calor e a terra coberta de cada uma. A tela **não faz
conta**: mostra o que o motor e o agente (em `backend/orbita/`) devolvem.

## Como abrir

Dois cliques em `index.html`. Não precisa de servidor nem de internet: as letras, o logo e os ícones estão nesta
pasta, e os dados estão em `dados/`.

## O que tem na tela

- **Os três momentos da lavoura**, cada um com a pergunta do produtor: antes de plantar ("O que eu planto agora?"),
  durante a safra ("Como está a minha lavoura?") e depois de colher ("O que a terra mostrou?").
- **A conversa:** a fala do produtor e a resposta do agente. Cada resposta diz de onde saiu (da conta, dos dados da
  NASA do lugar, ou de conhecimento geral, quando a conta não mede o assunto). Resposta comprida mostra o começo e o
  fecho, e o miolo abre em "Ler a resposta inteira".
- **A ficha:** o município, o tipo de solo, a rotação de hoje, a data do plantio e o que mais preocupa. O produtor
  confirma ou corrige antes de a conta rodar.
- **As rotações lado a lado:** três ou mais, com a de hoje marcada. Cada uma com a água que falta (num ano normal e no
  pior ano), os dias de calor forte, os dias do ano sem planta viva, a prova, o que ganha, o risco e o que falta
  saber. Onde a conta dá faixa, a tela mostra a faixa. No fim, "Converse com o agrônomo antes de decidir".
- **A prova:** o replay da safra 2015-16, dia a dia: a chuva, a água na terra descendo, os dias de sede e de calor
  forte, e os marcos com a frase de cada um. Tem tocar, pausar, voltar, velocidade e tela cheia (para gravar o vídeo).
  Na velocidade normal, a safra inteira passa em cerca de 30 segundos, com uma parada no dia em que a água acaba.
- **A leitura do agrônomo** (a aba "Agrônomo"): como a conta foi feita, com que valores, de onde eles vêm, as
  hipóteses e os limites. Dá para baixar a resposta completa do motor.

## Os dois modos

1. **Conversas guardadas** (o padrão): a tela lê `dados/conversas.js` e toca as conversas gravadas pelo agente. A
   próxima fala do produtor aparece como um botão. Serve para a demonstração sem servidor.
2. **Agente ao vivo:** abra a tela com o endereço da API no fim, por exemplo
   `index.html?api=http://127.0.0.1:8000`. O produtor escreve o que quiser, e a tela chama `POST /agente`, guarda o
   `estado` que volta e devolve na fala seguinte. Para ligar a API, de dentro de `backend/`:
   `python3 -m orbita.api` (a IA do agente precisa da chave no ambiente; veja o `LEIA-ME-agente.md`).

Se a API não responder, responder com erro ou estiver sem a chave da IA, a tela avisa e passa para as conversas
guardadas. Pedido recusado pelo agente (a frase vem em `{"erro": ...}`) aparece na conversa, e ela continua ao vivo.

## De onde vêm os dados

| arquivo | quem grava | o que traz |
|---|---|---|
| `dados/conversas.js` | o agente: `python3 -m orbita.exportar_conversas <esta pasta>/dados` (de dentro de `backend/`) | as conversas guardadas e o replay da safra (os dias e os marcos) |
| `dados/respostas.js` e `respostas.json` | o motor, por `python3 -B frontend/orbita/dados/gerar-dados.py` | a resposta inteira do motor para os três tipos de solo (a leitura do agrônomo) |
| `dados/complementos.js` e `validacao.js` | o mesmo `gerar-dados.py` | o calendário do ano e a validação cruzada (o satélite contra a estação em terra e a colheita do IBGE) |

Sem o `dados/conversas.js`, a tela abre, avisa que as conversas ainda não foram gravadas e mostra só a leitura do
agrônomo. Nenhum número é escrito à mão nesta pasta. Depois de mudar o motor ou o agente, grave os dois de novo (os
dois comandos da tabela), para a tela mostrar a conta de agora.

As fontes dos dados: a chuva é do satélite GPM IMERG, da NASA; a temperatura, da NASA POWER; o verde da lavoura, do
satélite MODIS, da NASA; a conta da água segue o manual FAO-56; a colheita é do IBGE e a chuva medida em terra é da
estação do INMET. O caminho de cada dado está em `data/orbita/`.

## Os arquivos

    index.html              a página
    styles.css              o estilo, na marca do time
    app.js                  liga as peças: as duas leituras, os três momentos, a mesa, os dois modos
    js/textos.js            todos os textos da tela do produtor (e o endereço da API, em API_BASE)
    js/conversa.js          a conversa: guardadas e ao vivo, com a queda para as guardadas
    js/comparacao.js        a ficha e as rotações lado a lado
    js/replay.js            o replay da safra, dia a dia
    js/icones.js            os ícones, desenhados aqui mesmo
    js/adaptar.js           lê a resposta do motor para a leitura do agrônomo
    js/resultado.js         a leitura do agrônomo
    js/textos-agronomo.js   os textos da leitura do agrônomo
    dados/                  os dados gravados pelo motor e pelo agente (tabela acima)
    marca/                  o logo do time
    fontes/                 as letras (Anton e Montserrat), com a licença de cada uma

## A marca

A marca é a da Equipe Agronautas, tirada do pitch do time: o logo (um satélite sobre faixas de lavoura), o
verde-escuro sobre o fundo quase branco, os títulos em Anton e o texto em Montserrat, e o lema "Inteligência do
espaço. Decisões para a terra.". As cores da água, do calor e da terra coberta foram acrescentadas pela tela. Não há
logo da NASA.

## Uso de IA

- Esta tela foi programada com apoio de IA (Claude, da Anthropic), com as decisões e a conferência do time.
- Na conversa, o texto do agente é escrito por IA ou montado com frases prontas; cada conversa diz qual dos dois. Todo
  número do texto é conferido com a conta antes de aparecer; se a conferência achar número fora da conta, o texto da IA
  não vai à tela.
- A IA não escolhe a rotação pelo produtor: a ferramenta apoia a decisão e manda conversar com o agrônomo.

## Créditos e licenças

- O logo e a identidade visual são do time (o arquivo do logo veio do pitch).
- A primeira versão desta tela partiu do painel do ramo `nat` do time (de nathancabrall); a leitura do agrônomo e o
  `js/adaptar.js` vêm dela.
- As letras Anton e Montserrat são distribuídas sob a SIL Open Font License 1.1 (`fontes/OFL-Anton.txt` e
  `fontes/OFL-Montserrat.txt`).

## O que ainda não tem

- A tela é só em português.
- A leitura do agrônomo mostra a conta guardada de Rio Verde (GO), com a rotação de hoje e a rotação com capim; a
  rotação com sorgo aparece só na comparação do produtor.
- O painel da cooperativa (acompanhar vários produtores) é o próximo passo; aqui ele aparece só como um aviso no fim.
