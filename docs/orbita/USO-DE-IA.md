<!-- Gerado com IA (Claude) -->
# Órbita Rural · declaração do uso de IA

English version: [AI-USE.en.md](AI-USE.en.md)

O NASA Space Apps Challenge pede que o uso de inteligência artificial seja declarado. Esta é a declaração da Equipe Agronautas para o Órbita Rural. Este arquivo também foi escrito com IA.

## 1. No desenvolvimento

| o que | como a IA entrou |
|---|---|
| o código do motor, do agente e da tela (`backend/orbita/`, `frontend/orbita/`) e os testes | gerado com IA (Claude, da Anthropic), a pedido do time, com as decisões e a conferência do time. Cada arquivo de código leva o cabeçalho "Gerado com IA (Claude)" |
| os programas que baixam os dados (`data/orbita/`) | gerados com IA (Claude). Os dados em si não são de IA: são cópias do que cada fonte devolveu, com o endereço e a hora da consulta |
| os textos (os LEIA-ME, estes documentos, o questionário, o texto da submissão) | escritos com IA (Claude) e conferidos pelo time |
| os slides do pitch | feitos com apoio de IA |
| a voz do vídeo | gerada por IA |
| a revisão do código | outro modelo (GPT) revisou o código do motor e do agente em pontos marcados; os defeitos achados foram consertados, cada um com um teste (o registro está no `README.md`, no `LEIA-ME-motor.md` e no `LEIA-ME-agente.md` de `backend/orbita/`) |

**Os modelos do desenvolvimento:** Claude, da Anthropic, para programar e escrever; revisões pontuais por outro modelo (GPT).

O que não é de IA: os dados (NASA, INMET, IBGE), os valores publicados das culturas (FAO, Embrapa, ZARC) e as decisões do projeto.

## 2. No produto

O agente (a IA que conversa com o produtor) usa um modelo de linguagem chamado pelo OpenRouter:

- o padrão: `anthropic/claude-haiku-5.5` (Claude Haiku 5.5, da Anthropic);
- a reserva testada: `deepseek/deepseek-v4.1-flash` (DeepSeek V4.1 Flash).

A chave fica só no ambiente do terminal (`OPENROUTER_API_KEY`); nenhum arquivo do repositório tem chave. Sem chave, o produto funciona com as conversas guardadas e com as frases prontas do motor.

O motor (a conta) não usa IA. A explicação que ele escreve é feita de frases prontas, preenchidas com os números da conta.

## 3. As travas do produto

A IA faz quatro coisas: entende a fala do produtor, propõe os valores da ficha, escolhe que ferramenta consultar e escreve a explicação. O resto é garantido pelo programa, com teste:

- **A IA não cria número.** Cada número do texto dela é conferido contra a conta (a ficha, a comparação e o que as ferramentas devolveram naquela fala). Sobrou número fora da conta, a IA tenta de novo uma vez; sobrou outra vez, o texto dela não vai à tela e saem as frases prontas do motor.
- **O que não tem conta é dito como conhecimento geral.** Nutrientes, pragas e mercado não são medidos. A resposta sai marcada como conhecimento geral, com aviso na frente, e sem nenhum número.
- **A resposta manda conferir com o agrônomo.** Toda resposta sai com o aviso "Converse com o agrônomo antes de decidir." A IA não escolhe a rotação pelo produtor.
- **A conta só roda depois do "sim" do produtor** à ficha, e quem lê o "sim" é o programa, não a IA.
- **Toda resposta com a ficha confirmada traz 3 rotações ou mais**, contando a de hoje, cada uma com a evidência, o benefício, o risco e o que falta saber.
- **Cada resposta diz de onde veio:** `texto_de` (IA ou frases prontas) e `apoio` (a conta, os dados do lugar ou conhecimento geral).
- **Nenhum dado pessoal é pedido** (nome, telefone, CPF, endereço), e a API não guarda nada.

Onde está escrito e testado: `backend/orbita/LEIA-ME-agente.md` (a tabela "O que a IA faz e o que o programa garante") e os testes `backend/orbita/tests/test_agente.py`, `test_ficha.py`, `test_ferramentas.py` e `test_modelo.py`.

## 4. O que as travas não pegam

A conferência olha se cada número do texto existe na conta. Ela não confere a que coisa o número se refere, nem o sinal, nem número escrito por extenso. Uma frase que compare errado dois números certos pode passar. Duas trocas de sentido conhecidas são barradas pelo programa (os dias de terra coberta e "a água acabou" dito do dia em que a sede só começou). Por isso as 4 conversas guardadas (13 falas do agente, 9 com o texto da IA) foram lidas uma a uma contra a conta antes de serem guardadas.

## 5. As regras do concurso que seguimos

- Não usamos o logo da NASA e não dizemos que a NASA apoia o projeto. Usamos dados públicos da NASA.
- Nenhum nome, imagem ou voz de menor de 18 anos aparece no projeto.
- O material da submissão está em inglês; os documentos principais têm versão em português e em inglês.
