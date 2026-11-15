<!-- Gerado com IA (Claude) -->
# Órbita Rural · a API do motor (provisória)

**O que é.** A porta para outro programa (o site, um serviço de mensagem) perguntar ao motor: "vale trocar a minha
rotação de hoje por outra? por quê, com que prova e com que risco?". Vale para três cidades de Goiás (Rio Verde, Jataí
e Silvânia) e compara três rotações. Não é recomendação agronômica: valide com o agrônomo. Python 3 só com a biblioteca
padrão. As rotas da conta não usam chave, login nem serviço pago; só a rota `/agente` (a conversa com a IA) precisa de
uma chave, que fica no ambiente de quem liga a API.

**Nenhum WhatsApp está ligado.** A API só devolve texto para quem chamou. Ela não manda mensagem a ninguém, não pede
nem guarda nome ou telefone, e não grava o corpo dos pedidos (o registro no terminal tem só o método, a rota e o código).

## Como ligar
De dentro de `backend/`:

    python3 -m orbita.api                      # liga em http://127.0.0.1:8000 (só esta máquina); Ctrl+C desliga
    python3 -m orbita.api --porta 8123         # outra porta (0 = uma porta livre, que ela mostra ao ligar)
    python3 -m orbita.api --endereco 0.0.0.0   # abre para a rede: não há senha nem limite de pedidos
    python3 -m orbita.api --origem https://o-site.exemplo   # só esse site lê as respostas pelo navegador (padrão: *)

Para a rota `/agente` responder, a chave da IA vai só no ambiente do terminal, nunca em arquivo:

    export OPENROUTER_API_KEY=...                      # a chave do OpenRouter; o .env.example traz só o nome
    export ORBITA_MODELO=anthropic/claude-haiku-5.5    # opcional; este é o padrão
    python3 -m orbita.api

Ao ligar, a API diz se a IA do agente está ligada e com que modelo. Sem a chave ela liga do mesmo jeito: as outras
rotas respondem, e a `/agente` devolve 503.

Fora do `127.0.0.1` a API fica aberta a quem alcançar a máquina (e gastaria a chave de quem ligou). Para pôr na
internet, ela precisa ficar atrás de uma proteção (um proxy com HTTPS e limite de pedidos); isso não está feito. O que
ela já faz sozinha: o corpo tem limite de tamanho e 10 segundos para chegar inteiro, e uma ligação parada cai em 15
segundos. O que ela não faz: não limita quantos pedidos chegam ao mesmo tempo, e os cabeçalhos de um pedido ainda
podem chegar devagar.

## As rotas
| rota | o que entra | o que sai |
|---|---|---|
| `GET /saude` | nada | `{"ok": true, ...}`, com as cidades e se a IA do agente está ligada |
| `POST /recomendacao` | a pergunta (abaixo) | a resposta inteira do motor (uns 100 KB de JSON) |
| `POST /mensagem` | a mesma pergunta | `{"texto": o texto curto, pronto para mensagem}` |
| `POST /conversa` | `{"estado": ..., "texto": ...}` | `{"estado": ..., "resposta": ...}` (a conversa em passos, sem IA) |
| `POST /agente` | `{"estado": ..., "texto": ...}` | `{"estado": ..., "resposta": ..., "comparacao": [...], ...}` (a conversa com a IA) |
| `POST /lavoura-hoje` | `{"cidade_id", "rotacao_atual", "terra", "plantio_da_soja"}` | a lavoura hoje: a situação, a frase do topo e os seis itens (a fase, a água, o calor, o verde, a terra coberta e o aviso de sede) |

O replay de uma safra, o "como está hoje" e o registro da safra **não têm rota própria**. Eles chegam por três
caminhos: pela rota `/agente` (a IA consulta e a resposta traz em `consultas` e em `replay`), pelo comando
`python3 -m orbita.perguntar` e pelo arquivo que o `exportar --tudo` grava para a tela. Os campos estão mais abaixo.

**A pergunta** (o corpo do `/recomendacao` e do `/mensagem`):

    {"cidade_id": "jatai", "rotacao_atual": ["soja", "sorgo"], "terra": "media",
     "plantio_da_soja": "2026-11-20", "preocupacao": "agua"}

| campo | o que é | os valores |
|---|---|---|
| `cidade_id` | a cidade (obrigatório) | `rio_verde`, `jatai` ou `silvania` |
| `rotacao_atual` | o que o produtor planta hoje (obrigatório) | `["soja", "milho", "pousio"]`, `["soja", "milho", "braquiaria"]` ou `["soja", "sorgo"]`; vale com ou sem acento, com ou sem o `"pousio"` no fim, ou o `id` da rotação (`soja_sorgo_pousio`) |
| `terra` | quanta água a terra segura | `pouca`, `media` ou `muita`; sem ela, vale `media`. Arenosa é `pouca`, textura média é `media`, argilosa é `muita` |
| `plantio_da_soja` | a data do plantio da soja (opcional) | ano-mês-dia, de 1 de setembro a 31 de dezembro (`"2026-11-20"`). O calendário inteiro anda junto com essa data |
| `preocupacao` | o que mais preocupa (opcional) | `agua`, `calor` ou `terra`. Só muda a ordem e o destaque; nenhum número muda |
| `prioridades` | as notas de 1 a 5, como antes (opcional) | `{"agua": 5, "solo": 4, "renda": 2, "erosao": 3}`: ou vêm as 4, ou nenhuma. Sem elas, a lista sai com `nota: null` |

A API aceita só esses 6 campos. A fonte da chuva e a regra dos anos, que o comando `perguntar` deixa trocar, não
entram por aqui (vale o padrão do motor). O pedido de antes, só com Rio Verde e as notas, continua valendo igual.

**As regras de todo pedido:** o corpo é JSON em UTF-8, com o cabeçalho `Content-Type: application/json` e no máximo
16.384 bytes. As respostas levam `Access-Control-Allow-Origin` (o site pode ler pelo navegador). Antes de um `POST`, o
navegador manda um `OPTIONS`: a API responde 204, sem corpo, dizendo o método que a rota aceita.

**Os erros** saem em português, no formato `{"erro": "..."}`:

| código | quando |
|---|---|
| 400 | entrada errada: JSON torto, campo que falta, cidade ou rotação que o motor não tem, data fora do formato, campo que a API não aceita |
| 404 | rota que não existe |
| 405 | método errado (o cabeçalho `Allow` diz o certo) |
| 408 | o corpo demorou mais de 10 segundos para chegar |
| 411 | faltou o tamanho do corpo (`Content-Length`) |
| 413 | corpo maior que 16.384 bytes |
| 415 | o corpo não veio como `application/json` |
| 500 | defeito do lado de dentro (nada foi guardado; pode tentar de novo) |
| 503 | só na rota `/agente`: não há chave da IA no servidor, a IA não respondeu, ou o motor não tem a conta pedida |

Pedido que nem chega a ser HTTP direito (endereço ou cabeçalhos grandes demais, método que não existe, versão que a
API não aceita) também sai nesse formato, com o código do próprio HTTP (414, 431, 501, 505).

## Um exemplo de cada chamada (rodados em 2026-11-15, numa porta livre do 127.0.0.1; a porta 8000 é a do padrão)
Nos exemplos, os textos longos estão cortados com "...".

### GET /saude

    curl -s http://127.0.0.1:8000/saude

    {"ok": true, "servico": "Órbita Rural · a API do motor (provisória)", "aviso": "Vale para Rio Verde (GO), Jataí (GO) e Silvânia (GO). Não é recomendação agronômica: valide com o agrônomo.", "rotas": ["GET /saude", "POST /recomendacao", "POST /mensagem", "POST /conversa", "POST /agente"], "limite_do_corpo_bytes": 16384, "ia_do_agente": {"ligada": true, "modelo": "anthropic/claude-haiku-5.5"}}

Sem a chave no ambiente, `ia_do_agente` sai `{"ligada": false, "modelo": null}`. A chave nunca aparece.

### POST /recomendacao

    curl -s -X POST http://127.0.0.1:8000/recomendacao -H 'Content-Type: application/json' \
      -d '{"cidade_id": "jatai", "rotacao_atual": ["soja", "sorgo"], "terra": "media", "plantio_da_soja": "2026-11-20", "preocupacao": "agua"}'

A resposta é a mesma do `python3 -m orbita.perguntar ... --json` (103.261 bytes neste pedido). As chaves de cima e
alguns pedaços:

    {"aviso": "...", "pergunta": "...",
     "entrada": {"cidade_id": "jatai", "rotacao_atual": ["soja", "sorgo", "pousio"], "rotacao_id": "soja_sorgo_pousio",
                 "prioridades": null, "terra": "media", "chuva": "imerg", "regra": "rendimento",
                 "plantio_da_soja": "2026-11-20", "preocupacao": "agua"},
     "local": {...}, "clima": {...}, "terra": {...}, "calendario": {...},
     "rotacao_de_hoje": {"id": "soja_sorgo_pousio", "nome": "soja → sorgo safrinha → pousio (terra parada)",
                         "chave": "com_sorgo", "nota": "..."},
     "regra_dos_anos": {...}, "rotacoes": {"atual": {...}, "alternativa": {...}, "com_sorgo": {...}},
     "comparacao": {...}, "prioridades": [...], "preocupacao": ..., "ordem_das_pernas": ..., "sede_forte": {...},
     "destaque": {"prioridade": "agua", "nome": "Água", "nota": null, "melhor": "atual",
                  "veredito_pela_faixa": "depende_da_hipotese"},
     "veredito": {"codigo": "depende", "frase": "...", "a_favor_da_troca": ["solo", "erosao"], "contra_a_troca": []},
     "safra_2025_26": {...}, "ndvi": {...}, "parametros": [...], "hipoteses": 30, "limites": [...],
     "calor": {...}, "terra_coberta": {...}, "comparacao_das_rotacoes": [...]}

O motor pode ganhar campos novos; os nomes de hoje não mudam. Os campos que entraram em 2026-11-15 estão descritos
na seção "A resposta do motor: os campos novos".

**Atenção às chaves de sempre.** `rotacoes.atual`, `rotacoes.alternativa`, `comparacao`, `veredito`, `prioridades`,
`destaque` e `sede_forte` continuam comparando soja-milho-pousio com soja-milho-braquiária, agora no lugar, na terra e
na data do produtor. A rotação que o produtor faz hoje (qualquer uma das três) está em `rotacao_de_hoje` e vem marcada
em `comparacao_das_rotacoes`. Quem mostra as três rotações deve ler `comparacao_das_rotacoes`.

### POST /mensagem

    curl -s -X POST http://127.0.0.1:8000/mensagem -H 'Content-Type: application/json' \
      -d '{"cidade_id": "jatai", "rotacao_atual": ["soja", "sorgo"], "terra": "media", "plantio_da_soja": "2026-11-20", "preocupacao": "agua"}'

    {"texto": "Órbita Rural · Jataí (GO)\nPergunta: vale trocar ... por ...?\n\nResposta: ...\n\n..."}

O texto não tem tabela nem markdown e cabe em uns 900 caracteres (948 bytes neste pedido). Traz a pergunta, a
resposta, o resultado no que mais pesa para o produtor, um número de prova de cada medida
mostrada (com a fonte em palavras), o risco em uma frase e "valide com o agrônomo". Não usa IA: são frases prontas, e
todo número dele está na resposta do motor (um teste confere com `conferencia.conferir_texto`). Se a resposta do motor
vier sem um campo, o texto sai sem aquele trecho. O texto segue as chaves de sempre: a pergunta dele é sempre a troca
de soja-milho-pousio por soja-milho-braquiária, na cidade pedida, mesmo quando a rotação de hoje é a do sorgo.

### POST /conversa (a conversa em passos, sem IA)

    curl -s -X POST http://127.0.0.1:8000/conversa -H 'Content-Type: application/json' -d '{"estado": null, "texto": "oi"}'

    {"estado": {"etapa": "terra"}, "resposta": "Olá! Aqui é o Órbita Rural. ..."}

    curl -s -X POST http://127.0.0.1:8000/conversa -H 'Content-Type: application/json' -d '{"estado": {"etapa": "terra"}, "texto": "2"}'

    {"estado": {"etapa": "agua", "terra": "media", "notas": {}}, "resposta": "De 1 a 5, quanto pesa para você a água ...?"}

    curl -s -X POST http://127.0.0.1:8000/conversa -H 'Content-Type: application/json' \
      -d '{"estado": {"etapa": "erosao", "terra": "media", "notas": {"agua": 5, "solo": 4, "renda": 2}}, "texto": "3"}'

    {"estado": {"etapa": "fim"}, "resposta": "Órbita Rural · Rio Verde (GO)\nPergunta: ... (o mesmo texto do /mensagem) ...\n\n..."}

Esta rota é a de antes e não mudou: vale só para Rio Verde, com as duas rotações de antes e as notas. A ordem da
conversa: a saudação (o que a ferramenta faz e o aviso de que vale só para Rio Verde) → a terra (1 pouca, 2 média,
3 muita) → as notas de 1 a 5 para água, solo, renda e erosão (uma pergunta por vez) → o resultado. Resposta fora do
esperado: a pergunta volta, com um exemplo, e o estado não anda. "de novo", em qualquer ponto, recomeça. Também vale
escrever por extenso ("média", "nota 4", "cinco"). As três cidades e as três rotações estão na rota `/agente`.

### POST /agente (a conversa com a IA)
O molde é o do `/conversa`: a API não guarda nada; quem chama guarda o `estado` e devolve na fala seguinte. O manual
inteiro do agente (as garantias, as 3 ferramentas, as conversas guardadas) é o `LEIA-ME-agente.md`.

**O pedido:** `{"estado": null no começo (ou o que a chamada anterior devolveu, sem mexer), "texto": "a fala do
produtor"}`. Só esses dois campos. O corpo tem o limite de sempre (16.384 bytes); o estado nunca passa de uns 9.500
bytes.

**A resposta, campo a campo:**

| campo | o que traz |
|---|---|
| `estado` | o que guardar e devolver na fala seguinte: `v` (a versão), `ficha`, `selo` (o selo da confirmação), `pergunta` (a pergunta feita antes de a ficha fechar), `momento` e `falas` (as últimas 6 falas, cortadas numa palavra inteira) |
| `resposta` | o texto do agente, já conferido |
| `momento` | `antes` (o que plantar), `durante` (como está a lavoura) ou `depois` (o que a terra mostrou) |
| `ficha` | `cidade_id`, `rotacao_atual` (a lista das culturas), `terra`, `plantio_da_soja`, `preocupacao`, `confirmada` e `falta` (os campos que ainda não foram ditos) |
| `comparacao` | a lista de 3 rotações ou mais, como o motor mandou (`comparacao_das_rotacoes`); `null` enquanto a ficha não foi confirmada |
| `apoio` | de onde o texto se apoia: `conta`, `dados_do_lugar` ou `conhecimento_geral` (aí o texto sai com o aviso na frente); `null` enquanto a ficha não foi confirmada |
| `conferencia` | `{"passou": ..., "sobras": [...], "tentativas": ...}`: o resultado da conferência dos números do texto da IA. `passou: false` quer dizer que o texto dela foi barrado e a `resposta` são as frases prontas; `sobras` lista os números barrados |
| `aviso` | o aviso do agrônomo, em todo passo |
| `texto_de` | `ia` (o texto é do modelo de linguagem, conferido) ou `frases_prontas` (frases do programa e do motor, sem IA) |
| `consultas` | o que a IA leu das ferramentas nesta fala: `[{"ferramenta", "argumentos", "resultado"}]`. Serve para qualquer um conferir os números de novo |
| `replay` | os dias e os marcos de uma safra, quando o replay foi pedido (para a tela desenhar); senão `null` |

**Os erros da rota:** **503** quando não há chave no servidor, quando a IA não responde ou quando o motor não tem a
conta (quem chama mantém o estado que tinha e usa as conversas guardadas); **400** para corpo errado (falta o texto,
estado que não é objeto nem `null`, campo a mais). Dois exemplos, rodados com a API ligada sem chave:

    {"erro": "A IA do agente não está ligada neste servidor: falta a chave no ambiente (OPENROUTER_API_KEY). Use as conversas guardadas."}   (código 503)

    {"erro": "Campo que a API não aceita: nome. Ela aceita só: estado, texto."}   (código 400)

**Como a conversa anda.** "oi" devolve a saudação pronta, sem chamar a IA. O produtor conta da lavoura; a IA anota na
ficha (só entra valor das listas do motor). Com a ficha completa, o programa mostra a ficha e pede o "sim". Depois do
"sim", a conta roda e a IA responde à pergunta que ele fez. Mudou a ficha depois de confirmada, ela é mostrada de novo
e a conta espera outro "sim". "de novo" recomeça.

**O selo da confirmação.** O estado volta de quem chama, e quem chama pode ser qualquer programa. Por isso a
confirmação da ficha vai junto com um selo (`estado.selo`), feito com um segredo sorteado quando a API liga e guardado
só na memória dela. Estado com `confirmada: true` e sem o selo certo volta a "não confirmada", e a ficha é mostrada de
novo. A consequência: se a API for desligada e ligada de novo, o produtor confirma a ficha outra vez (um "sim").

**Um exemplo real: o começo** (2026-11-15, com a chave só no ambiente do processo; o "oi" não gasta a IA):

    curl -s -X POST http://127.0.0.1:8000/agente -H 'Content-Type: application/json' -d '{"estado": null, "texto": "oi"}'

    {"estado": {"v": 1, "ficha": {"cidade_id": null, "rotacao_atual": null, "terra": null, "plantio_da_soja": null,
                                  "preocupacao": null, "confirmada": false},
                "selo": null, "pergunta": null, "momento": "antes",
                "falas": [{"de": "produtor", "texto": "oi"}, {"de": "agente", "texto": "Olá! Aqui é o Órbita Rural. ..."}]},
     "resposta": "Olá! Aqui é o Órbita Rural. ...",
     "momento": "antes",
     "ficha": {"cidade_id": null, "rotacao_atual": null, "terra": null, "plantio_da_soja": null, "preocupacao": null,
               "confirmada": false, "falta": ["cidade_id", "rotacao_atual", "terra", "preocupacao"]},
     "comparacao": null, "apoio": null,
     "conferencia": {"passou": true, "sobras": [], "tentativas": 0},
     "aviso": "Converse com o agrônomo antes de decidir.",
     "texto_de": "frases_prontas", "consultas": [], "replay": null}

A resposta inteira teve 2.465 bytes. A saudação diz o que o agente faz e pergunta o que falta na ficha: a cidade, a
rotação de hoje, a terra e a preocupação (a data do plantio é opcional e não entra em `falta`).

**Um exemplo real: a ficha confirmada.** É a resposta ao "sim" da conversa `antes-plantei-tarde`, guardada em
`conversas-guardadas/conversas.json` (gravada em 2026-11-15 com o Claude Haiku 5.5; os campos grandes estão cortados):

    {"estado": {"v": 1, "ficha": {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media",
                                  "plantio_da_soja": "2026-11-10", "preocupacao": "agua", "confirmada": true},
                "selo": "5f665e66...", "pergunta": null, "momento": "antes", "falas": [...]},
     "resposta": "Com a data que você deu (10/11), a soj...",
     "momento": "antes",
     "ficha": {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media",
               "plantio_da_soja": "2026-11-10", "preocupacao": "agua", "confirmada": true, "falta": []},
     "comparacao": [
       {"id": "soja_milho_pousio", "nome": "soja → milho safrinha → pousio (terra parada)",
        "apelido": "soja, milho e pousio", "de_hoje": true,
        "agua": {"falta_no_ano_normal_mm": 230.2, "falta_no_pior_ano_mm": 252.7, "dias_de_sede_no_pior_ano": 92, "em_faixa": false, "pior_ano_contra_o_normal": "maior"},
        "calor": {"dias_de_calor_forte_no_pior_ano": 9, "dias_de_calor_forte_no_ano_normal": 0, "limite_c": 33.0, "cultura_do_limite": "milho", "etiqueta": "publicado", "por_cultura": {...}},
        "terra_coberta": {"dias_sem_planta_viva": 122, "dias_sem_planta_viva_no_ano": 125, "pelo_satelite": 96},
        "contra_as_outras": {"soja_milho_braquiaria": {"agua": "depende", "calor": "empate", "terra_coberta": "pior"}, "soja_sorgo_pousio": {"agua": "pior", "calor": "pior", "terra_coberta": "empate"}},
        "evidencia": "...", "beneficio": "...", "risco": "...", "falta_saber": "..."},
       {"id": "soja_milho_braquiaria", ...}, {"id": "soja_sorgo_pousio", ...}],
     "apoio": "conta",
     "conferencia": {"passou": true, "sobras": [], "tentativas": 2},
     "aviso": "Converse com o agrônomo antes de decidir.",
     "texto_de": "ia",
     "consultas": [{"ferramenta": "ensaio_da_rotacao", "argumentos": {},
                    "resultado": {"lugar": "Rio Verde (GO)", "pior_ano": "2015-16", "ano_normal": "2019-20", "calendario": ..., "rotacoes": ...}}, ...],
     "replay": null}

Nesse passo o estado inteiro tem 1.753 bytes. Na conversa `replay-2015-16`, guardada no mesmo arquivo, o passo do
replay traz `replay` com 366 dias e 8 marcos (Rio Verde, safra 2015-16), pedido pela IA com
`{"ferramenta": "ensaio_da_rotacao", "argumentos": {"safra": "pior_ano"}}`.

### POST /lavoura-hoje (a lavoura hoje: o acompanhamento durante a safra)
O pedido (só estes campos; `cidade_id` e `rotacao_atual` são obrigatórios, `terra` vale `media` se faltar, e sem
`plantio_da_soja` vale o calendário de costume, com a soja em 15 de outubro):

    curl -s -X POST http://127.0.0.1:8000/lavoura-hoje -H 'Content-Type: application/json' \
      -d '{"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"], "terra": "media", "plantio_da_soja": "2026-10-15"}'

A resposta (`motor.lavoura_hoje`; os números mudam com o dado guardado, e aqui vão só os campos principais):

    {"disponivel": true, "local": {"nome": "Rio Verde (GO)", "id": "rio_verde", ...},
     "rotacao": {"id": "soja_milho_pousio", "nome": "..."}, "terra": "media", "plantio_da_soja_informado": "2026-10-15",
     "hoje": "2026-11-15", "ultimo_dia_com_dado": "2026-11-11", "ultimo_dia_com_dado_de": "...", "atraso_dias": 4,
     "safra": "2026-27", "situacao": "atencao", "situacao_nome": "atenção",
     "frase": "Em Rio Verde (GO), em 11/11/2026 (o último dia com dado), a soja tinha 27 dias e estava em crescimento, sem sede, com ... mm de água ao alcance da planta. Pedem atenção: ...",
     "itens": [
       {"id": "fase", "titulo": "A fase da cultura", "situacao": "tranquilo", "situacao_nome": "tranquilo",
        "frase": "Na terra está a soja, plantada em 15/10/2026. Em 11/11/2026, o último dia com dado, fazia 27 dias do plantio e a lavoura estava em crescimento, no dia 8 dos 20 dessa fase. ...",
        "ultimo_dado": {"data": "2026-11-11", "de": "o calendário da rotação e as fases da tabela da FAO ..."},
        "regra_da_situacao": "Atenção: a cultura está na fase crítica ...",
        "o_que_esta_na_terra": "soja", "cultura": "soja", "plantio": "2026-10-15", "dias_desde_o_plantio": 27,
        "fase": "crescimento", "dia_da_fase": 8, "dias_da_fase": 20, "fase_critica": false,
        "fase_critica_de": "2026-11-24", "fase_critica_ate": "2027-01-17", "dias_para_a_fase_critica": 13,
        "no_dia_da_consulta": {"data": "2026-11-15", "dias_desde_o_plantio": 31, "fase": "crescimento", "fase_critica": false}},
       {"id": "agua", ...}, {"id": "calor", ...}, {"id": "verde", ...}, {"id": "terra_coberta", ...},
       {"id": "aviso_de_sede", ...}],
     "regras": {"fase": "...", "agua": "...", "calor": "...", "verde": "...", "terra_coberta": "...", "aviso_de_sede": "..."},
     "janela_do_consumo_dias": 7, "horizonte_sem_chuva_dias": 30, "aviso": "..."}

- Todo item traz `id`, `titulo`, `situacao` (`tranquilo`, `atencao`, `alerta` ou `sem_dado`), `situacao_nome`, `frase`
  (pronta para o produtor, só com números da conta), `ultimo_dado` (`data`, em ano-mês-dia, e `de`, que diz de qual
  dado é) e `regra_da_situacao`. A `situacao` do topo é a pior dos itens; "sem dado" não conta.
- `agua`: os campos do "como está hoje" (`agua_na_terra_mm`, `agua_na_terra_pct`, `com_sede`,
  `faixa_da_agua_na_terra_mm`, `no_ano_normal`, `no_pior_ano`, `com_a_chuva_de_modelo`), mais `dias_seguidos_de_sede`.
- `calor`: `limite_c` e `fonte_do_limite`, `dias_de_calor_forte_desde_o_plantio`, `dias_de_calor_forte_na_fase_atual`,
  `dias_de_calor_forte_na_fase_critica`, `maxima_desde_o_plantio_c`, `dia_da_maxima` e `nas_safras_guardadas`
  (`safras`, `desde_o_plantio` e `na_fase_atual`, cada um com `valor_do_meio`, `menor` e `maior`, e `por_safra`).
- `verde`: `imagem` e `imagem_ate` (os 16 dias da imagem), `verde` (de 0 a 1), `pontos_com_medida`, `pontos`, `leitura`
  (`acima`, `dentro`, `abaixo` ou `sem_comparacao`) e `outros_anos` (`anos`, `quantos`, `valor_do_meio`, `menor`,
  `maior`, `por_ano`).
- `terra_coberta`: `com_planta_viva`, `desde`, `dias_seguidos`, `antes` (a sequência anterior) e `na_safra`.
- `aviso_de_sede`: `ja_com_sede`, `dias_seguidos_de_sede`, `dias_ate_a_sede`, `data_da_sede`, `sem_chuva_a_partir_de`,
  `consumo_medio_mm_por_dia`, `janela_dias` (7), `horizonte_dias` (30) e `chuva_depois_do_ultimo_dia` (a chuva que
  o satélite já marcou depois do último dia da conta, se houver).
- Desde 2026-11-15 a chuva dos dias recentes é a chuva do satélite em mm de cada dia (`data/orbita/chuva-do-dia/`), e
  não mais a lida da cor da imagem: a água sai como um número só (`faixa_da_agua_na_terra_mm` fica com as duas pontas
  iguais, `com_a_chuva_de_modelo` fica só para comparar), no painel e no "como está hoje". O exemplo acima foi escrito
  antes dessa troca. Hoje a conta segue até o último dia com chuva do satélite (`ultimo_dia_com_dado`: `2026-11-14`
  na consulta de 2026-11-15); onde a temperatura ainda não chegou, o consumo é o do tempo dos 7 dias anteriores
  (`ultimo_dia_com_temperatura`, `dias_com_o_consumo_estimado`, `consumo_estimado_desde`), e o calor conta só até o
  último dia com temperatura medida. A regra está no `LEIA-ME-motor.md`, seção 12.
- Sem a chuva recente guardada: `{"disponivel": false, "aviso": ...}`. Entrada errada: 400, com a frase do motor.
- As regras de cada situação, a janela de 7 dias e os 30 dias estão no `LEIA-ME-motor.md`, seção 10. Na linha de
  comando: `python3 -m orbita.perguntar --lavoura-hoje --cidade jatai --plantio 2026-10-20` (com `--json`, a estrutura).

### Um erro, como exemplo

    curl -s -X POST http://127.0.0.1:8000/recomendacao -H 'Content-Type: application/json' \
      -d '{"cidade_id": "jatai", "rotacao_atual": ["soja", "sorgo"], "terra": "media", "chuva": "power"}'

    {"erro": "Campo que a API não aceita: chuva. Ela aceita só: cidade_id, rotacao_atual, prioridades, terra, plantio_da_soja, preocupacao."}   (código 400)

Erro de entrada do motor (cidade que não existe, rotação fora do cardápio, data como `"20/11"`, terra como `"barro"`)
também sai com 400, numa frase que começa por "Entrada fora do formato:" e diz o que usar no lugar.

## A resposta do motor: os campos novos
O que entrou em 2026-11-15, campo a campo. O porquê de cada um, as fontes e os limites estão no `LEIA-ME-motor.md`.
Os números dos exemplos saíram da conta rodada em 2026-11-15, com a terra média.

### As cidades
`cidade_id` aceita `rio_verde`, `jatai` e `silvania`. Cada cidade tem o clima, a chuva do satélite e a colheita do
IBGE do seu ponto. Em Jataí e Silvânia só há a chuva `imerg` (o satélite) e `power` (o modelo); a estação em terra só
existe em Rio Verde. O pior ano e o ano normal saem da colheita de cada cidade (`regra_dos_anos`).

### As três rotações (`rotacoes` e `comparacao_das_rotacoes`)
| `id` | a rotação | onde está em `rotacoes` |
|---|---|---|
| `soja_milho_pousio` | soja → milho safrinha → pousio (terra parada) | `rotacoes.atual` |
| `soja_milho_braquiaria` | soja → milho com braquiária (capim) | `rotacoes.alternativa` |
| `soja_sorgo_pousio` | soja → sorgo safrinha → pousio (terra parada) | `rotacoes.com_sorgo` |

`comparacao_das_rotacoes` é uma lista com as três. A rotação de hoje do produtor vem primeiro, com `de_hoje: true`.
Cada rotação da lista:

| campo | o que traz |
|---|---|
| `id`, `nome`, `apelido`, `de_hoje` | quem é a rotação, e se é a que o produtor faz hoje |
| `agua.falta_no_ano_normal_mm`, `agua.falta_no_pior_ano_mm` | a água que faltou, em mm, no ano normal e no pior ano |
| `agua.dias_de_sede_no_pior_ano` | os dias de sede no pior ano |
| `agua.em_faixa` | `true` na rotação com capim: aí os três números acima saem como `{"de": ..., "ate": ...}`, porque não se sabe quanto o capim disputa água com o milho |
| `agua.pior_ano_contra_o_normal` | `maior`, `menor`, `igual` ou, nas faixas, `cruza`. O pior ano é o da pior colheita da região (IBGE), não o de maior falta de água na conta; `menor` avisa que nele a conta deu menos falta que no ano normal |
| `calor.dias_de_calor_forte_no_pior_ano`, `calor.dias_de_calor_forte_no_ano_normal` | os dias de calor forte na fase crítica das culturas da rotação |
| `calor.limite_c`, `calor.cultura_do_limite`, `calor.etiqueta` | o limite da cultura da 2ª safra (a que muda entre as rotações) e se ele é publicado ou hipótese |
| `calor.por_cultura` | o detalhe de cada cultura da rotação |
| `terra_coberta.dias_sem_planta_viva` | os dias seguidos sem planta viva antes do plantio da soja, pelo calendário (122 com pousio, 30 com capim) |
| `terra_coberta.dias_sem_planta_viva_no_ano` | o ano inteiro, contado dia a dia: soma os 3 dias entre a soja e a 2ª safra (125 e 33) |
| `terra_coberta.pelo_satelite` | os dias seguidos sem planta verde que o satélite viu, só na rotação soja-milho-pousio (a que a região faz hoje); nas outras, `null` |
| `contra_as_outras` | para cada outra rotação: `agua`, `calor` e `terra_coberta`, cada um com `melhor`, `pior`, `empate` ou `depende`. A conta usa os números sem arredondar |
| `evidencia`, `beneficio`, `risco`, `falta_saber` | as 4 frases prontas da rotação. Só têm números da conta: cada uma passa pela conferência. O benefício e o risco saem de `contra_as_outras`, não de opinião |

Um exemplo dos números (Rio Verde, sem data de plantio): faltaram no pior ano 225,9 mm com soja-milho-pousio, de
229,8 a 241,2 mm com o capim e 191,3 mm com o sorgo.

### O calor (`calor`)
"Dia de calor forte" é o dia da fase crítica da cultura com a temperatura máxima acima do limite da cultura: 40 °C
na soja, 33 °C no milho e 35 °C no sorgo.

| campo | o que traz |
|---|---|
| `o_que_e`, `fonte_da_temperatura`, `aviso` | a regra em palavras, de onde vem a temperatura (NASA POWER) e o limite da medida |
| `pior_ano`, `ano_normal` | as duas safras que a comparação usa |
| `limites.<cultura>` | `limite_c`, `etiqueta`, `fonte`, `trecho`, `outro_limite_publicado` (35 °C no milho e 38 °C no sorgo; a soja não tem) e `fase_critica` |
| `por_cultura.<cultura>` | `limite_c`, `outro_limite_c`, `por_safra` (cada safra guardada), `soma_das_safras` e `safras_com_calor_forte` |
| `por_rotacao.<id>` | `culturas`, `dias_no_pior_ano`, `dias_no_ano_normal` e `soma_das_safras` |
| `hipoteses` | as duas hipóteses da contagem: o uso da temperatura máxima do dia e a fase crítica ser a fase do meio da tabela da FAO |

O calor é uma contagem à parte: não mexe na conta da água, e dia de calor forte não é perda de safra. Em Rio Verde,
no pior ano (2015-16), a conta deu 19 dias de calor forte nas rotações com milho e nenhum na rotação com sorgo.

### A terra coberta (`terra_coberta`) e o verde do satélite
| campo | o que traz |
|---|---|
| `o_que_e`, `aviso` | o que cada número conta, e o que o satélite prova |
| `por_rotacao.<id>` | `dias_sem_planta_viva`, `meses_sem_planta_viva`, `de` e `ate` (o dia e o mês em que o período começa e acaba) e `dias_sem_planta_viva_no_ano` |
| `pelo_satelite` | `dias_pelo_calendario`, `dias_pelo_satelite` (a mediana), `menor`, `maior`, `quantos` (as medidas), `diferenca`, `leitura`, `prova_de`, `frase`, `aviso` e `fonte` |

O verde do satélite (NDVI, do produto MOD13Q1 da NASA) existe nas três cidades: 6 pontos por cidade. **Os pontos
foram escolhidos no mapa e ninguém conferiu em campo: não se sabe de quem são nem o que foi plantado.** O satélite
prova só a rotação que a região faz hoje (soja, milho e pousio); nas outras, os dias sem planta viva vêm do
calendário. O que a conta deu:

| cidade | dias seguidos sem planta verde (a mediana) | de quanto a quanto | medidas | pelo calendário | `leitura` |
|---|---|---|---|---|---|
| Rio Verde | 96 | 16 a 160 | 36 | 122 | `dentro_da_faixa` |
| Jataí | 80 | 0 a 128 | 30 | 122 | `dentro_da_faixa` |
| Silvânia | 96 | 16 a 192 | 35 | 122 | `dentro_da_faixa` |

A mesma comparação está em `ndvi` (a chave de antes, agora nas três cidades) e na porta `motor.verde_do_satelite`.
Cidade sem arquivo guardado continua saindo com `sem_medida`.

## As outras portas do motor (sem rota própria)
Em Python: `from orbita import motor`. Pelo terminal: `python3 -m orbita.perguntar` (os comandos estão no
`README.md`). Pela rota `/agente`: as 3 ferramentas da IA chamam estas mesmas funções. A `entrada` é a pergunta de cima.

| a função | o que devolve | o comando |
|---|---|---|
| `motor.clima_do_lugar(cidade_id)` | os fatos do clima guardado do lugar: `local`, `clima`, `regra_dos_anos`, `chuva_da_safra_mm`, `calor`, `frase`, `aviso` | `--cidade silvania --lugar` |
| `motor.verde_do_satelite(cidade_id)` | o que o satélite viu da terra (os campos de `terra_coberta.pelo_satelite`) | `--verde` |
| `motor.replay_da_safra(entrada, safra)` | a safra dia a dia | `--replay 2015-16` |
| `motor.como_esta_hoje(entrada)` | a água da lavoura no último dia com dado | `--hoje` |
| `motor.registro_da_safra(entrada, safra)` | o registro de uma safra, depois da colheita | `--registro 2015-16` |

### O replay (`motor.replay_da_safra`)
As chaves: `safra`, `cidade_id`, `local`, `rotacao`, `terra`, `plantio_da_soja_informado`, `primeiro_dia`,
`ultimo_dia`, `completa`, `dias`, `marcos`, `resumo`, `limites_de_calor_c` e `avisos`. O replay segue a rotação de
hoje do produtor.

- **`dias`**: um por dia, de 1 de setembro a 31 de agosto. Cada dia: `data`, `cultura` (ou `sem_planta`), `chuva_mm`,
  `agua_na_terra_mm`, `pedido_mm`, `bebido_mm`, `falta_mm`, `com_sede`, `tmax_c` e `calor_forte`.
- **`marcos`**: os dias que contam a história da safra. Todo marco tem `data`, `tipo`, `cultura`, `frase` e
  `principal`. As datas saem da conta.

| `tipo` | o que marca | os campos a mais |
|---|---|---|
| `plantio` | o dia em que a cultura entra | nenhum |
| `agua_acabou` | **o começo da sede**: o dia em que a água fácil de tirar acabou e começou a maior sequência de dias de sede da cultura. Não é o dia em que a água acabou de fato | `dias_seguidos`, `agua_na_terra_mm` |
| `agua_no_fundo` | **o dia da água no fundo**: o primeiro em que a água na terra chega ao menor valor do ciclo, só quando nesse dia a planta pediu água e não conseguiu beber nada. Se isso não aconteceu, não há esse marco. `situacao` diz o que aconteceu, e a frase acompanha: `acabou` (sobrou até 0,1 mm: é o dia em que a água acabou), `perto_do_fundo` (sobrou mais que 0,1 mm) ou `seca_no_plantio` (o dia é o do plantio: a terra já chegou seca) | `agua_na_terra_mm`, `situacao` |
| `calor_forte` | o primeiro dia de calor forte na fase crítica | `tmax_c`, `limite_c`, `dias_na_safra` |
| `colheita` | o fim do ciclo, só com o ciclo completo nos dados | `falta_mm`, `dias_de_sede` |

- **`principal`**: um só marco é o principal (`true`): o começo da maior sequência de dias de sede. O `agua_no_fundo`
  nunca é o principal.
- **`resumo`**: por cultura (`falta_mm`, `pedido_mm`, `falta_relativa_pct`, `dias`, `dias_de_sede`,
  `dias_de_calor_forte`, `ciclo_completo`, `maior_sequencia_de_sede_dias`) e o `total` da safra.

Os marcos de Rio Verde, safra 2015-16, soja-milho-pousio, terra média (366 dias, 8 marcos; as frases estão de fora):

| `data` | `tipo` | `cultura` | os números | `principal` |
|---|---|---|---|---|
| 2015-10-15 | `plantio` | soja | | `false` |
| 2015-10-18 | `agua_acabou` | soja | 6 dias seguidos; 23,3 mm na terra | `false` |
| 2016-02-06 | `colheita` | soja | faltaram 5,3 mm; 13 dias de sede | `false` |
| 2016-02-10 | `plantio` | milho | | `false` |
| 2016-04-04 | `agua_acabou` | milho | 60 dias seguidos; 17,2 mm na terra | `true` |
| 2016-04-08 | `calor_forte` | milho | máxima de 33,2 °C, limite de 33,0 °C; 19 dias na safra | `false` |
| 2016-04-24 | `agua_no_fundo` | milho | 0,1 mm na terra | `false` |
| 2016-06-13 | `colheita` | milho | faltaram 220,6 mm; 60 dias de sede | `false` |

### O "como está hoje" (`motor.como_esta_hoje`)
Como está a água da lavoura no último dia com dado, ao lado do mesmo dia do ano normal e do pior ano.

| campo | o que traz |
|---|---|
| `disponivel`, `local`, `rotacao`, `terra`, `plantio_da_soja_informado` | de quem é a conta |
| `hoje`, `ultimo_dia_com_dado`, `atraso_dias`, `safra` | o dia da pergunta, o último dia com dado e a distância entre os dois |
| `ultimo_dia_com_dado_de` | de qual dado é a data de cima: da conta (o último dia com a temperatura da NASA POWER e a chuva rápida do satélite, as duas; é o dia do retrato). Em `chuva_recente.fonte` há outro `ultimo_dia_com_dado`, só da chuva rápida do satélite, que pode ir além (em 2026-11-15, em Rio Verde: 13/11/2026 contra 11/11/2026); ele também leva o seu `ultimo_dia_com_dado_de` |
| `o_que_esta_na_terra`, `agua_na_terra_mm`, `agua_que_a_terra_segura_mm`, `agua_na_terra_pct`, `com_sede`, `chuva_desde_1_de_setembro_mm` | a conta com a chuva rápida do satélite |
| `com_a_chuva_de_modelo` | os mesmos campos, com a chuva de modelo da NASA POWER |
| `faixa_da_agua_na_terra_mm` | `{"de": ..., "ate": ...}`: a água na terra entre as duas chuvas |
| `no_ano_normal`, `no_pior_ano` | o mesmo dia nessas safras, com `safra`, `diferenca_mm` e `leitura` |
| `chuva_recente` | `de`, `ate`, `dias`, `satelite_rapido_mm`, `modelo_da_nasa_power_mm`, `fonte`, `origem`, `chuva_guardada_ate` e `conferencia_em_mm` |
| `chuva_recente.conferencia_em_mm` | a conferência com o valor do satélite em mm, somado de 5 em 5 dias: `periodos_de_5_dias`, `de`, `ate`, `satelite_em_mm`, `satelite_lido_da_cor_mm`, `diferenca_pct`, `o_que_e`, `origem`. É só conferência: a conta não usa |
| `frase`, `aviso` | o resumo em palavras e o aviso de que a chuva recente é aproximada |

A chuva dos dias recentes vem da cor da imagem diária do satélite (NASA GIBS) e é aproximada; por isso a conta sai
com as duas chuvas e a faixa. Em Rio Verde, rodado em 2026-11-15: o último dia com dado era 2026-11-11 (4 dias de
atraso), com soja na terra e de 34,8 a 63,0 mm de água (a terra segura 66,0 mm). A chuva recente, de 2026-09-15 a
2026-11-11 (58 dias): 411,0 mm pelo satélite rápido e 146,5 mm pelo modelo. A conferência, em 13 períodos de 5 dias
(de 2026-09-01 a 2026-11-10): 437,2 mm no valor em mm e 397,8 mm na leitura da cor (`diferenca_pct`: -9,0).

### O registro da safra (`motor.registro_da_safra`)
A safra contada depois da colheita, com as mesmas regras da comparação.

| campo | o que traz |
|---|---|
| `safra`, `local`, `rotacao`, `terra`, `plantio_da_soja_informado`, `periodo` | de que safra e de quem é o registro; `periodo.completa` diz se a safra fechou nos dados |
| `o_que_foi_plantado` | cada cultura, com `entra`, `sai` e `dias` |
| `agua` | `falta_mm`, `dias_de_sede`, `chuva_da_safra_mm` e `por_cultura` |
| `calor` | `dias_de_calor_forte` e `por_cultura` |
| `terra_coberta` | `dias_sem_planta_viva` (contados nos dias da própria safra), `dias_da_safra`, `dias_sem_planta_viva_no_ano` (o número da comparação, num ano comum), `pelo_satelite` e `nota` |
| `entre_as_safras_guardadas` | onde a safra ficou entre as 10 do estudo: `medida`, `posicao`, `de`, `mediana_pct`, `falta_da_2a_safra_pct`, `por_safra_pct`, `empatadas`, `a_parte` e `nota`. A safra mais recente (2025-26) sai com `a_parte: true`, fora da lista e da mediana |
| `marcos` | os mesmos marcos do replay |
| `registrado_em`, `frase`, `aviso` | a hora do registro, o resumo em palavras e o aviso |

Em Rio Verde, safra 2015-16 (soja-milho-pousio, terra média): faltaram 225,9 mm, com 73 dias de sede e 19 dias de
calor forte; 126 dias sem planta viva nos 366 dias da safra (125 num ano comum); a 2ª posição de 10 na falta de água
do milho (49,6% do pedido, contra a mediana de 38,0%).

## Como um serviço de WhatsApp usaria o /conversa ou o /agente
A API não guarda nada entre um pedido e outro. Quem guarda a conversa é o serviço de fora. As duas rotas têm o mesmo
molde:

1. Chegou a primeira mensagem de uma pessoa: o serviço chama a rota com `{"estado": null, "texto": "<o que ela
   escreveu>"}`.
2. Ele manda a `resposta` de volta para a pessoa e **guarda o `estado`** daquela conversa, do jeito que veio.
3. Na mensagem seguinte da mesma pessoa, ele chama de novo com o `estado` guardado e o texto novo. E assim até o fim.
4. No `/conversa`, quando o `estado` volta `{"etapa": "fim"}`, a conta foi entregue. No `/agente` a conversa não tem
   fim marcado: o produtor pode seguir perguntando. Nas duas, "de novo" recomeça.

No `/conversa` o `estado` é pequeno (menos de 120 caracteres) e só tem a etapa, a terra e as notas já dadas; o que a
pessoa escreveu não volta no estado nem na resposta. No `/agente` o `estado` leva a ficha, o selo e as últimas 6
falas (cortadas), e por isso é maior. Se o estado guardado se perder ou chegar estragado, a conversa recomeça do
começo. Se a API responder com erro (qualquer código que não seja 200), o serviço mantém o estado que tinha e pede
para a pessoa tentar de novo.

**O que falta para ser um WhatsApp de verdade, e o cuidado.** Nada disto está ligado ao WhatsApp. Para ligar, o serviço
de fora teria de ficar entre o WhatsApp (pelo caminho oficial da Meta) e esta API. O telefone de quem escreve é dado
pessoal (LGPD): o serviço de fora é que o veria e guardaria, junto do estado. Por isso a ligação de verdade pede o
consentimento da pessoa, dizer para que o número é usado, guardar pelo menor tempo possível e apagar quando ela pedir.
Esta API continua sem receber o telefone: quem chama manda só o texto e o estado.

## Os arquivos que o site lê
O site não faz conta: lê arquivos com as respostas guardadas. Para gravar:

    python3 -m orbita.exportar <pasta>                      # por exemplo: python3 -m orbita.exportar ../frontend/dados
    python3 -m orbita.exportar <pasta> --sem-notas --tudo   # grava também motor.js e motor.json
    python3 -m orbita.exportar_conversas <pasta>            # as conversas do agente (com a chave: a IA escreve)
    python3 -m orbita.exportar_conversas <pasta> --sem-ia   # as mesmas conversas, com as frases prontas

O `exportar` grava `<pasta>/respostas.js`, com `window.ORBITA_RESPOSTAS = {"pouca": {...}, "media": {...}, "muita":
{...}};` (a resposta inteira do motor para cada tipo de terra, já com os campos novos; sem opções, com todas as notas
iguais a 3, e o site reordena pelas notas da tela), e `<pasta>/respostas.json`, com `gerado_em` (a hora),
`gerado_por`, `parametros_usados` e `respostas`. As opções: `--cidade`, `--rotacao`, `--plantio`, `--preocupacao`,
`--sem-notas` (a pergunta sem as notas de 1 a 5) e `--tudo`. Com `--tudo`, grava também `motor.js` e `motor.json`:
`window.ORBITA_MOTOR = {lugares, respostas, replay, hoje, registro}` (o clima e a resposta de cada cidade, e o replay,
o "como está hoje" e o registro guardados), para a tela mostrar sem servidor. O `exportar_conversas` grava `conversas.js` (`window.ORBITA_CONVERSAS = {...};`) e `conversas.json`: são 4
conversas, que a tela usa quando a rota `/agente` não está ligada. Rodar de novo sempre que o motor mudar.

## Os arquivos e os testes
`api.py` (as rotas) · `mensagem.py` (o texto curto) · `conversa.py` (a conversa em passos) · `agente.py`, `ficha.py`,
`ferramentas.py` e `modelo.py` (a conversa com a IA) · `exportar.py` e `exportar_conversas.py` (os arquivos do site) ·
os testes em `tests/test_api.py` (as funções direto e uma ida e volta de verdade por HTTP numa porta livre do
`127.0.0.1`), `test_mensagem.py`, `test_conversa.py`, `test_exportar.py`, `test_agente.py`, `test_ficha.py`,
`test_ferramentas.py`, `test_modelo.py` e `test_exportar_conversas.py`. Os testes do agente usam um modelo de mentira:
não gastam chave nem internet. De `backend/`: `python3 -m unittest` (456 testes, com os do motor).

**Uso de IA.** Estes arquivos foram gerados com IA (Claude, da Anthropic) e revisados por outra IA (GPT). O texto da
mensagem e a conversa em passos (`/conversa`) **não** usam IA: são frases prontas, preenchidas só com os números da
conta. Na rota `/agente` o texto é escrito por um modelo de linguagem (o padrão é o Claude Haiku 5.5, pelo
OpenRouter), e cada número dele é conferido contra a conta antes de aparecer; cada resposta diz em `texto_de` se o
texto é da IA ou de frases prontas.
