<!-- Gerado com IA (Claude) -->
# Órbita Rural · declaração do uso de IA

English version: [AI-USE.en.md](AI-USE.en.md)

O NASA Space Apps Challenge pede que o uso de inteligência artificial seja declarado. Esta é a declaração da Equipe Agronautas para o Órbita Rural. Este arquivo também foi escrito com IA.

## 1. No desenvolvimento

| o que | como a IA entrou |
|---|---|
| o código do motor, do assistente e da tela (`backend/orbita/`, `frontend/orbita/`) e os testes | gerado com IA (Claude, da Anthropic), a pedido do time, com as decisões e a conferência do time. Os arquivos de código levam o cabeçalho "Gerado com IA (Claude)" |
| os programas que baixam os dados (`data/orbita/`) e os dos testes de Goiás (`docs/orbita/validacao-regional/`) | gerados com IA (Claude). Os dados em si não são de IA: são cópias do que cada fonte devolveu, com o endereço e a hora da consulta |
| os textos (os LEIA-ME, estes documentos, o questionário, o roteiro falado, o texto da submissão) | escritos com IA (Claude) e conferidos pelo time |
| os slides do pitch (`docs/orbita/pitch/`) | feitos com apoio de IA. Não há imagem gerada por IA: a foto de satélite dos slides é uma imagem de verdade da NASA |
| a voz do vídeo | gerada por IA |
| a revisão do código | outro modelo (GPT) revisou o código do motor e do assistente em pontos marcados; os defeitos achados foram consertados, cada um com um teste (o registro está no `README.md`, no `LEIA-ME-motor.md` e no `LEIA-ME-agente.md` de `backend/orbita/`) |

**Os modelos do desenvolvimento:** Claude, da Anthropic, para programar e escrever; revisões pontuais por outro modelo (GPT).

O que não é de IA: os dados (NASA, INMET, IBGE), os valores publicados das culturas (FAO, Embrapa, ZARC) e as decisões do projeto.

## 2. No produto

O assistente (a IA que conversa com o produtor) usa um modelo de linguagem chamado pelo OpenRouter:

- o padrão: `anthropic/claude-haiku-5.5` (Claude Haiku 5.5, da Anthropic);
- a reserva testada: `deepseek/deepseek-v4.1-flash` (DeepSeek V4.1 Flash).

A chave fica só no ambiente do terminal (`OPENROUTER_API_KEY`); nenhum arquivo do repositório tem chave.

**A IA fica só na conversa.** O painel "Minha lavoura hoje", o ensaio das rotações, o ano ruim dia a dia e o registro da safra são contas do motor: não usam IA e funcionam sem chave. A explicação que o motor escreve é feita de frases prontas, preenchidas com os números da conta. Na entrada, os botões montam a ficha da lavoura sem IA; a IA entra quando o produtor escreve e quando ele toca em "Perguntar".

## 3. As travas do produto

A IA faz quatro coisas: entende a fala do produtor, propõe os valores da ficha, escolhe que ferramenta consultar (o ensaio das rotações, o painel da lavoura hoje, o clima do lugar, o verde do satélite) e escreve a explicação. O resto é garantido pelo programa, com teste:

- **A IA não cria número.** Cada número do texto dela é conferido contra a conta (a ficha, a comparação e o que as ferramentas devolveram naquela fala). Sobrou número fora da conta, a IA tenta de novo uma vez; sobrou outra vez, o texto dela não vai à tela e saem as frases prontas do motor.
- **O assistente sempre dá uma indicação, e diz o que é conta e o que é conhecimento geral.** Toda resposta com a conta termina em "A indicação:". Quando o produtor fala de um lugar ou de uma rotação que não estão guardados, a conta roda com a cidade guardada mais próxima e com a rotação guardada mais parecida, a ficha mostra as duas escolhas para ele confirmar, e a resposta diz de que lugar é o clima e qual rotação foi usada. O que fica de fora da conta sai marcado como conhecimento geral; se a IA não disser, o programa acrescenta a frase.
- **O que não tem conta é dito como conhecimento geral.** Nutrientes, pragas e mercado não são medidos. A resposta sai com o aviso na frente e sem nenhum número.
- **A resposta manda conferir com o agrônomo.** Toda resposta sai com o aviso "Converse com o agrônomo antes de decidir." A IA não escolhe a rotação pelo produtor.
- **A conta só roda depois do "sim" do produtor** à ficha, e quem lê o "sim" é o programa, não a IA.
- **Toda resposta com a ficha confirmada traz 3 rotações ou mais**, contando a de hoje, cada uma com a evidência, o benefício, o risco e o que falta saber.
- **Cada resposta diz de onde veio:** `texto_de` (IA ou frases prontas) e `apoio` (a conta, os dados do lugar ou conhecimento geral).
- **Duas trocas de sentido conhecidas são barradas:** os dias de terra coberta ditos no lugar dos dias sem planta viva, e "a água acabou" dito do dia em que a sede só começou. Texto com letra de outro alfabeto também não vai à tela.
- **Nenhum dado pessoal é pedido** (nome, telefone, CPF, endereço), e a API não guarda nada. A lavoura fica guardada só no aparelho do produtor.

Onde está escrito e testado: `backend/orbita/LEIA-ME-agente.md` (a tabela "O que a IA faz e o que o programa garante") e os testes `backend/orbita/tests/test_agente.py`, `test_ficha.py`, `test_ferramentas.py`, `test_fala_simples.py` e `test_modelo.py`.

## 4. A conferência das conversas

A conferência automática olha se cada número do texto existe na conta. O sentido de cada frase é conferido por leitura: as 6 conversas guardadas de exemplo (gravadas em 2026-11-15, com 16 falas do assistente, 10 com o texto da IA e 6 com frases prontas, nenhuma barrada pela conferência dos números) foram lidas uma a uma contra a conta antes de serem guardadas. A escolha da cidade mais próxima e da rotação mais parecida é da IA (se ela não escolher a rotação, o programa escolhe a de mais culturas em comum), e por isso a ficha mostra as duas ao produtor antes da conta.

## 5. As regras do concurso que seguimos

- Não usamos o logo da NASA e não dizemos que a NASA apoia o projeto. Usamos dados públicos da NASA.
- Nenhum nome, imagem ou voz de menor de 18 anos aparece no projeto.
- O material da submissão está em inglês; os documentos principais têm versão em português e em inglês.
