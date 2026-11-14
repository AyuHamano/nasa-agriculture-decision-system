<!-- Gerado com IA (Claude) -->
# Órbita Rural · a API do motor (provisória)

**O que é.** A porta para outro programa (o site, um serviço de mensagem) perguntar ao motor: "vale trocar a minha
rotação de hoje por outra? por quê, com que prova e com que risco?". Vale só para Rio Verde (GO). Não é recomendação
agronômica: valide com o agrônomo. Python 3 só com a biblioteca padrão; sem chave, sem login, sem serviço pago.

**Nenhum WhatsApp está ligado.** A API só devolve texto para quem chamou. Ela não manda mensagem a ninguém, não pede
nem guarda nome ou telefone, e não grava o corpo dos pedidos (o registro no terminal tem só o método, a rota e o código).

## Como ligar
De dentro de `backend/`:

    python3 -m orbita.api                      # liga em http://127.0.0.1:8000 (só esta máquina); Ctrl+C desliga
    python3 -m orbita.api --porta 8123         # outra porta (0 = uma porta livre, que ela mostra ao ligar)
    python3 -m orbita.api --endereco 0.0.0.0   # abre para a rede: não há senha nem limite de pedidos
    python3 -m orbita.api --origem https://o-site.exemplo   # só esse site lê as respostas pelo navegador (padrão: *)

Fora do `127.0.0.1` a API fica aberta a quem alcançar a máquina. Para pôr na internet, ela precisa ficar atrás de uma
proteção (um proxy com HTTPS e limite de pedidos); isso não está feito.

## As rotas
| rota | o que entra | o que sai |
|---|---|---|
| `GET /saude` | nada | `{"ok": true, ...}` |
| `POST /recomendacao` | a pergunta (abaixo) | a resposta inteira do motor (uns 32 KB de JSON) |
| `POST /mensagem` | a mesma pergunta | `{"texto": o texto curto, pronto para mensagem}` |
| `POST /conversa` | `{"estado": ..., "texto": ...}` | `{"estado": ..., "resposta": ...}` |

**A pergunta** (o formato do documento do time, mais a terra):

    {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"],
     "prioridades": {"agua": 5, "solo": 4, "renda": 2, "erosao": 3}, "terra": "media"}

`terra`: `pouca`, `media` ou `muita` (quanta água a terra segura); sem ela, vale `media`. As notas (1 a 5) só mudam a
ordem e o destaque; nenhum número muda. A API aceita só esses 4 campos: a fonte da chuva e a regra dos anos, que o
comando `perguntar` deixa trocar, não entram por aqui (vale o padrão do motor).

**As regras de todo pedido:** o corpo é JSON em UTF-8, com o cabeçalho `Content-Type: application/json` e no máximo
16.384 bytes. As respostas levam `Access-Control-Allow-Origin` (o site pode ler pelo navegador).

**Os erros** saem em português, no formato `{"erro": "..."}`:

| código | quando |
|---|---|
| 400 | entrada errada: JSON torto, campo que falta, nota fora de 1 a 5, campo que a API não aceita |
| 404 | rota que não existe |
| 405 | método errado (o cabeçalho `Allow` diz o certo) |
| 411 | faltou o tamanho do corpo (`Content-Length`) |
| 413 | corpo maior que 16.384 bytes |
| 415 | o corpo não veio como `application/json` |
| 500 | defeito do lado de dentro (nada foi guardado; pode tentar de novo) |

## Um exemplo de cada chamada (rodados em 2026-11-14; a porta 8000 é a do padrão)

### GET /saude

    curl -s http://127.0.0.1:8000/saude

    {"ok": true, "servico": "Órbita Rural · a API do motor (provisória)", "aviso": "Vale só para Rio Verde (GO). Não é recomendação agronômica: valide com o agrônomo.", "rotas": ["GET /saude", "POST /recomendacao", "POST /mensagem", "POST /conversa"], "limite_do_corpo_bytes": 16384}

### POST /recomendacao

    curl -s -X POST http://127.0.0.1:8000/recomendacao -H 'Content-Type: application/json' \
      -d '{"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "prioridades": {"agua": 5, "solo": 4, "renda": 2, "erosao": 3}, "terra": "media"}'

A resposta é a mesma do `python3 -m orbita.perguntar ... --json` (uns 32 KB). As chaves de cima e dois pedaços:

    {"aviso": "...", "pergunta": "...", "entrada": {...}, "local": {...}, "clima": {...}, "terra": {...},
     "calendario": {...}, "regra_dos_anos": {...}, "rotacoes": {"atual": {...}, "alternativa": {...}},
     "comparacao": {...}, "prioridades": [...],
     "destaque": {"prioridade": "agua", "nome": "Água", "nota": 5, "melhor": "empate"},
     "veredito": {"codigo": "vale_testar_a_troca", "frase": "Pelo que foi medido, vale testar a troca: a alternativa se saiu melhor em solo e erosão e não ficou pior em nada do que foi medido.", "a_favor_da_troca": ["solo", "erosao"], "contra_a_troca": []},
     "safra_2025_26": {...}, "ndvi": {...}, "parametros": [...], "hipoteses": 17, "limites": [...]}

O motor pode ganhar campos novos; os nomes de hoje não mudam.

### POST /mensagem

    curl -s -X POST http://127.0.0.1:8000/mensagem -H 'Content-Type: application/json' \
      -d '{"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "prioridades": {"agua": 5, "solo": 4, "renda": 2, "erosao": 3}, "terra": "media"}'

    {"texto": "Órbita Rural · Rio Verde (GO)\nPergunta: vale trocar \"soja → milho safrinha → pousio (terra parada)\" por \"soja → milho com braquiária (capim)\"?\n\nResposta: Pelo que foi medido, vale testar a troca: a alternativa se saiu melhor em solo e erosão e não ficou pior em nada do que foi medido.\n\nNas suas maiores notas:\nÁgua (nota 5): empate.\nSolo (nota 4): a alternativa se saiu melhor.\n\nA prova: no pior ano (safra 2015-16), faltaram 224,2 mm de água na rotação de hoje e 227,2 mm na alternativa. Fontes: o satélite de chuva GPM IMERG, da NASA (a chuva) e a FAO (a conta de água). Pelo calendário das culturas, a terra fica 122 dias por ano sem planta viva hoje e 30 na alternativa.\n\nO risco: a braquiária também bebe água depois do milho, e a terra pode chegar mais seca ao plantio da soja.\n\nIsto é uma conta, não uma recomendação: valide com o agrônomo antes de decidir."}

O texto não tem tabela nem markdown e cabe em uns 900 caracteres. Traz a pergunta, a resposta, o resultado nas duas
prioridades de maior nota, um número de prova de cada medida mostrada (com a fonte em palavras), o risco em uma frase
e "valide com o agrônomo". Não usa IA: são frases prontas, e todo número dele está na resposta do motor (um teste
confere com `conferencia.conferir_texto`). Se a resposta do motor vier sem um campo, o texto sai sem aquele trecho.

### POST /conversa

    curl -s -X POST http://127.0.0.1:8000/conversa -H 'Content-Type: application/json' -d '{"estado": null, "texto": "oi"}'

    {"estado": {"etapa": "terra"}, "resposta": "Olá! Aqui é o Órbita Rural. Eu comparo a rotação soja → milho safrinha → pousio (terra parada) com soja → milho com braquiária (capim) e digo se vale testar a troca: por quê, com que prova e com que risco. Uso o clima que a NASA registrou e a conta de água da FAO.\nAviso: por enquanto a conta vale só para Rio Verde (GO), e não é recomendação: valide com o agrônomo. Não peço nem guardo nome ou telefone.\n\nSão 5 perguntas rápidas.\n\nQuanta água a sua terra segura? Responda 1 (pouca), 2 (média) ou 3 (muita). Se não souber, responda 2."}

    curl -s -X POST http://127.0.0.1:8000/conversa -H 'Content-Type: application/json' -d '{"estado": {"etapa": "terra"}, "texto": "2"}'

    {"estado": {"etapa": "agua", "terra": "media", "notas": {}}, "resposta": "De 1 a 5, quanto pesa para você a água (a lavoura não passar sede)? 1 é pouco, 5 é muito."}

    curl -s -X POST http://127.0.0.1:8000/conversa -H 'Content-Type: application/json' \
      -d '{"estado": {"etapa": "erosao", "terra": "media", "notas": {"agua": 5, "solo": 4, "renda": 2}}, "texto": "3"}'

    {"estado": {"etapa": "fim"}, "resposta": "Órbita Rural · Rio Verde (GO)\nPergunta: ... (o mesmo texto do /mensagem) ...\n\nMande 'de novo' para recomeçar."}

A ordem da conversa: a saudação (o que a ferramenta faz e o aviso de que vale só para Rio Verde) → a terra (1 pouca,
2 média, 3 muita) → as notas de 1 a 5 para água, solo, renda e erosão (uma pergunta por vez) → o resultado. Resposta
fora do esperado: a pergunta volta, com um exemplo, e o estado não anda. "de novo", em qualquer ponto, recomeça.
Também vale escrever por extenso ("média", "nota 4", "cinco").

### Um erro, como exemplo

    curl -s -X POST http://127.0.0.1:8000/recomendacao -H 'Content-Type: application/json' -d '{"cidade_id": "rio_verde", "terra": "barro"}'

    {"erro": "Entrada fora do formato: falta rotacao_atual (por enquanto, só [\"soja\", \"milho\", \"pousio\"]); faltam as prioridades (agua, solo, renda e erosao, cada uma com nota de 1 a 5); terra \"barro\" não existe: use pouca, media ou muita (quanta água a terra segura)."}   (código 400)

## Como um serviço de WhatsApp usaria o /conversa
A API não guarda nada entre um pedido e outro. Quem guarda a conversa é o serviço de fora:

1. Chegou a primeira mensagem de uma pessoa: o serviço chama `POST /conversa` com `{"estado": null, "texto": "<o que ela
   escreveu>"}`.
2. Ele manda a `resposta` de volta para a pessoa e **guarda o `estado`** daquela conversa, do jeito que veio.
3. Na mensagem seguinte da mesma pessoa, ele chama de novo com o `estado` guardado e o texto novo. E assim até o fim.
4. Quando o `estado` volta `{"etapa": "fim"}`, a conta foi entregue; se a pessoa mandar "de novo", a conversa recomeça.

O `estado` é pequeno (menos de 120 caracteres) e só tem a etapa, a terra e as notas já dadas; no fim, só a etapa. O
que a pessoa escreveu não volta no estado nem na resposta. Se o estado guardado se perder ou chegar estragado, a
conversa recomeça pela saudação. Se a API responder com erro (qualquer código que não seja 200), o serviço mantém o
estado que tinha e pede para a pessoa tentar de novo.

**O que falta para ser um WhatsApp de verdade, e o cuidado.** Nada disto está ligado ao WhatsApp. Para ligar, o serviço
de fora teria de ficar entre o WhatsApp (pelo caminho oficial da Meta) e esta API. O telefone de quem escreve é dado
pessoal (LGPD): o serviço de fora é que o veria e guardaria, junto do estado. Por isso a ligação de verdade pede o
consentimento da pessoa, dizer para que o número é usado, guardar pelo menor tempo possível e apagar quando ela pedir.
Esta API continua sem receber o telefone: quem chama manda só o texto e o estado.

## O arquivo de respostas que o site lê
O site não faz conta nem chama a API: lê um arquivo com as respostas guardadas. Para gravar:

    python3 -m orbita.exportar <pasta>         # por exemplo: python3 -m orbita.exportar ../frontend/dados

Grava `<pasta>/respostas.js`, com `window.ORBITA_RESPOSTAS = {"pouca": {...}, "media": {...}, "muita": {...}};` (a
resposta inteira do motor para cada tipo de terra, com todas as notas iguais a 3; o site reordena pelas notas da tela),
e `<pasta>/respostas.json`, com `gerado_em` (a hora), `gerado_por`, `parametros_usados` e `respostas` (o mesmo objeto
do `respostas.js`). Rodar de novo sempre que o motor mudar.

## Os arquivos e os testes
`api.py` (as rotas) · `mensagem.py` (o texto curto) · `conversa.py` (a conversa em passos) · `exportar.py` (o arquivo
do site) · os testes em `tests/test_api.py` (as funções direto e uma ida e volta de verdade por HTTP numa porta livre do
`127.0.0.1`), `test_mensagem.py`, `test_conversa.py` e `test_exportar.py`. De `backend/`: `python3 -m unittest`.

**Uso de IA.** Estes arquivos foram gerados com IA (Claude, da Anthropic) e revisados por outra IA (GPT). O texto da
mensagem e a conversa **não** usam IA: são frases prontas, preenchidas só com os números da conta.
