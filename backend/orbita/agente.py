# Gerado com IA (Claude)
"""O agente: a IA que conversa com o produtor, colhe a ficha, consulta a conta e explica o resultado.

Uso (o molde é o do `conversa.passo`; nada fica guardado aqui dentro):
    from orbita import agente, modelo
    estado, saida = agente.passo(None, "oi", modelo.do_ambiente())        # o começo: o estado é None
    estado, saida = agente.passo(estado, "planto soja e milho em Jataí", modelo.do_ambiente())
    agente.resposta_da_rota(estado, saida)                                # o que a rota POST /agente devolve

No terminal, de dentro de backend/ (precisa da chave no ambiente; ver LEIA-ME-agente.md):
    python3 -m orbita.agente

O que a IA faz: entende a fala do produtor, propõe os valores da ficha, escolhe qual ferramenta consultar e
escreve a explicação. O que o PROGRAMA garante, sem depender do pedido à IA:
- A ficha é fechada: só entra valor das listas do motor (`ficha.py`), e é o programa que lê o "sim" do produtor.
  A confirmação leva um selo (`estado["selo"]`) feito com um segredo que só existe na memória deste programa: o
  estado volta de quem chama (o navegador), e "confirmada" escrito à mão, sem o selo certo, não vale.
- A conta só roda com a ficha confirmada. Ferramenta da conta pedida antes disso não roda.
- Com a ficha confirmada, toda resposta sai com a comparação de 3 rotações ou mais, contando a de hoje, cada uma
  com a evidência, o benefício, o risco e o que falta saber (`comparacao`), e com o aviso do agrônomo (`aviso`).
- A trava dos números: o texto da IA é conferido por `conferencia.conferir_texto` contra a ficha, a comparação e
  o que as ferramentas devolveram nesta fala; se ela não consultou nada nesta fala, o texto não pode ter número
  nenhum. Sobrou número, a IA tenta uma vez de novo; sobrou outra vez, o texto dela não sai: saem as frases
  prontas, feitas só com as frases do motor (`texto_de` diz qual dos dois foi). Uma troca de sentido também é
  barrada: "a terra fica coberta 30 dias", quando 30 é o número de dias SEM planta viva.
- A marca `apoio` sai das ferramentas que a IA consultou de fato: `conta` (o ensaio, o replay, o registro, o
  painel da lavoura hoje), `dados_do_lugar` (só o clima ou o verde do satélite) ou `conhecimento_geral` (nenhuma; aí o
  programa põe o aviso na frente do texto). Antes de a ficha ser confirmada, `apoio` e `comparacao` são vazios.
- O `momento`: `depois` (o verde do satélite ou o registro), `durante` (o replay de uma safra ou o "como está
  hoje") ou `antes` (o resto).

- A indicação: com a ficha confirmada, a resposta nunca termina em recusa. O que o produtor disse fora das listas
  fica nos campos "ditos" da ficha (`lugar_dito`, `rotacao_dita`); a conta roda com o lugar guardado mais próximo
  e a rotação guardada mais parecida (escolhida pelo programa, pela regra fixa de `ficha.rotacao_parecida`, nunca
  pela IA), e o programa garante que a resposta diz "conhecimento geral" para a parte de
  fora (acrescenta a frase, se a IA não disse). As frases prontas também terminam numa indicação.

O estado é pequeno e vira JSON: a ficha, o selo da confirmação, a pergunta que o produtor fez antes de fechar a
ficha, o momento e as últimas falas (cortadas numa palavra inteira e conferidas de novo). Quem chama guarda e devolve na fala seguinte; cabe no limite do corpo da API.
A IA não escolhe a rotação pelo produtor, e nenhum dado pessoal é pedido.
"""
import datetime
import hashlib
import hmac
import json
import re
import secrets
import sys
import unicodedata

from orbita import conferencia, conversa, ferramentas, ficha

VERSAO = 1
MAX_FALAS = 6                    # as últimas falas que voltam no estado (3 do produtor e 3 do agente)
TAMANHO_DA_FALA = 1300           # o tamanho de cada fala guardada no estado, em bytes, já como JSON
TAMANHO_DO_TEXTO = 1500          # letras da fala do produtor que o agente lê
TAMANHO_DA_PERGUNTA = 500        # o tamanho da pergunta guardada, em bytes, já como JSON
VOLTAS = 4                       # rodadas de ferramenta por fala
PEDIDOS = 7                      # pedidos à IA por fala, no máximo
MOMENTOS = ("antes", "durante", "depois")
APOIOS = ("conta", "dados_do_lugar", "conhecimento_geral")
QUANTOS_MARCOS = 10              # os marcos do replay que entram nas frases prontas (o motor chega a 9 numa safra)
FRASE_MINIMA = 40                # um texto cortado só vale se sobrar pelo menos isto até a última frase inteira
ARGUMENTOS = {"clima_do_lugar": ("hoje",), "ensaio_da_rotacao": ("safra",), "verde_do_satelite": ("safra",),
              "lavoura_hoje": ()}
_SEGREDO = secrets.token_bytes(32)   # sorteado quando o programa liga; fica só na memória (nunca em arquivo)

AVISO = "Converse com o agrônomo antes de decidir."
AVISO_DE_CONHECIMENTO_GERAL = "Isto é conhecimento geral: não saiu da conta com os dados da NASA."
PERGUNTA_PADRAO = "Vale trocar a minha rotação de hoje por outra?"
SAUDACAO = ("Olá! Aqui é o Órbita Rural. Eu ensaio a sua rotação de culturas com o que os satélites da NASA "
            "registraram na sua região: comparo o que você planta hoje com outras rotações, no ano normal e no pior "
            "ano, e cada número vem da conta.\nNão peço nome nem telefone. A decisão é sua, com o seu agrônomo.")
NAO_ENTENDI = "Não entendi."
PODE_PERGUNTAR = ("Pode perguntar sobre a sua rotação. Por exemplo: vale trocar o que eu planto? Como foi a pior "
                  "safra, dia a dia? Quantos dias a terra fica sem planta viva?")
DE_NADA = PODE_PERGUNTAR + " A comparação das rotações continua aqui embaixo."
AGRADECEU = ("obrigad", "brigad", "valeu")
FICHA_MUDOU = "Mudei a sua ficha, e por isso a conta espera você confirmar de novo."
FICHA_NAO_CONFIRMADA = ("A ficha ainda não foi confirmada pelo produtor: a conta só roda depois do sim dele. Não "
                        "diga nenhum número da conta.")
SEM_CONTA = ("Sobre isso eu não tenho conta, e por isso não dou número. O que a conta mostra da sua rotação está na "
             "comparação aqui embaixo. Para esse assunto, converse com o agrônomo.")
SEM_CONTA_COM_A_ROTACAO = ("Para esse assunto eu não tenho conta. O que a conta mostra da sua rotação ({nome}): "
                           "{evidencia} O que a conta indica: {beneficio}")
ROTACAO_PARECIDA = ("Você planta {dito}: a conta que eu tenho é a da rotação guardada mais parecida, {nome}. "
                    "{evidencia}")
LUGAR_PROXIMO = "O clima é o de {lugar}, o lugar guardado mais próximo de {dito}."
NOTA_DA_ROTACAO_DITA = ("O que eu disse de {dito} fora desses números é conhecimento geral: a conta é a da rotação "
                        "guardada mais parecida, {nome}.")
NOTA_DO_LUGAR_DITO = ("Sobre {dito}, o que não está nesses números é conhecimento geral: o clima da conta é o de "
                      "{lugar}, o lugar guardado mais próximo.")
O_QUE_A_CONTA_INDICA = "O que a conta indica em cada caminho:"
SEM_NUMERO = "Fiz a conta. O resultado de cada rotação está na comparação aqui embaixo."
FALA_LONGA = "(Resposta longa: o resultado de cada rotação está na comparação.)"
TAMBEM_COMPAREI = ("Também comparei {quantas} rotações, contando a sua de hoje: a evidência, o benefício, o risco e o "
                   "que falta saber de cada uma estão na comparação aqui embaixo.")
CONTA_RECUSADA = "Não consegui fazer a conta com essa ficha. {motivo} Diga o que corrigir."
AVISO_DA_TRAVA = ("A conferência barrou o seu texto por causa disto: {sobras}. Cada item é um número que não está "
                  "no que as ferramentas devolveram nesta fala, ou um número dito com o sentido trocado. Escreva a "
                  "resposta inteira de novo sem isso. Se o número é da conta, consulte a ferramenta nesta fala e use "
                  "o número exato dela, com o sentido que ela dá. Não peça desculpa nem fale da correção.")
# A troca de sentido que o programa barra: a conta só tem "dias SEM planta viva"; "coberta 30 dias" diz o contrário.
COBERTA_TANTOS_DIAS = re.compile(r"\bcobert[ao]s?\s+(?:só\s+|somente\s+|apenas\s+|por\s+|durante\s+|em\s+)*"
                                 r"(?:uns\s+|cerca\s+de\s+)?\d+\s+dias\b(?!\s+(?:por\s+ano\s+)?sem\b)", re.IGNORECASE)
SENTIDO_TROCADO = " (a conta só tem os dias SEM planta viva: esse número não é de dias de terra coberta)"
# A outra troca que o programa barra: no replay, o marco "agua_acabou" é o dia em que a sede começa (acabou só a água
# fácil de tirar); a água acaba no marco "agua_no_fundo". "A água acabou em 04/04/2016" diz isso do dia errado.
AGUA_ACABOU = re.compile(r"\bágua\b(?![^.!?\n•]*\bfácil)[^.!?\n•]{0,60}?\bacab(?:ou|a|aram|am)\b", re.IGNORECASE)
DATA_NO_TEXTO = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?:/(\d{4}))?(?![\d/])")
FIM_DE_FRASE = re.compile(r"[.!?\n•]")
A_SEDE_COMECOU = (" (nesse dia a sede começou: acabou só a água fácil de tirar; a conta só diz que a água acabou no "
                  "marco da água no fundo, se houver)")

OUTRO_ALFABETO = " (letra de outro alfabeto: escreva só em português)"

OLA = ("oi", "ola", "oie", "opa", "alo", "bom dia", "boa tarde", "boa noite", "e ai", "eai", "oi tudo bem",
       "ola tudo bem", "oi bom dia", "oi boa tarde", "oi boa noite", "comecar", "inicio")
CORTESIAS = ("obrigado", "obrigada", "muito obrigado", "muito obrigada", "brigado", "brigada", "valeu", "ok",
             "ok obrigado", "ok obrigada", "beleza", "entendi", "certo", "ta bom", "tudo bem", "legal", "tchau",
             "ate mais", "ate logo")
SIM = ("sim", "s", "isso", "isso mesmo", "e isso", "e isso mesmo", "confirmo", "confirmado", "confirma", "certo",
       "esta certo", "ta certo", "tudo certo", "certinho", "correto", "esta correto", "ta correto", "exato", "ok",
       "perfeito", "positivo", "fechado", "pode sim", "pode fazer", "pode seguir", "pode rodar", "pode fazer a conta")
NEGAM = ("mas", "nao", "porem", "errado", "errada", "corrige", "corrigir", "corrija", "menos")

REGRAS = """Você é o agente do Órbita Rural. Você conversa com um produtor rural de Goiás sobre a rotação de \
culturas dele (o que ele planta, em que ordem, ao longo do ano). Fale em português simples, com frases curtas. Se \
usar um termo técnico, explique na mesma frase.

Como a conversa anda:
1. Primeiro a ficha: o lugar da lavoura, o que ele planta hoje, o tipo de terra, o que mais preocupa e, se ele \
disser, o dia do plantio da soja. Tudo o que ele disser sobre isso você anota com a ferramenta anotar_na_ficha. Só \
existem os valores das listas da ferramenta. Se ele disser um lugar ou uma rotação que não está nas listas, não \
recuse nem liste as opções: anote lugar_dito (o lugar que ele disse) junto com cidade_id (o lugar guardado mais \
próximo, pela latitude e longitude) e, para a rotação, só rotacao_dita (o que ele disse que planta): quem escolhe \
a rotação da conta é o programa, por regra fixa, não você. Não anote o que ele não disse.
2. O programa mostra a ficha e o produtor confirma. Quem lê o "sim" é o programa, não você.
3. Com a ficha confirmada, você responde às perguntas dele consultando as ferramentas da conta: lavoura_hoje, \
ensaio_da_rotacao, clima_do_lugar e verde_do_satelite.

Qual ferramenta para qual pergunta:
- Antes de plantar ("o que eu planto agora?", "vale trocar?", "milho ou sorgo?"): ensaio_da_rotacao. Se o \
produtor disse o dia em que plantou a soja, comece pelo calendário que a conta usou, numa frase só: quando a soja \
sai e quando a segunda safra entra na terra.
- Durante a safra, "como está a lavoura?" ou "como está hoje?": lavoura_hoje. A resposta traz, curta e em \
palavras de produtor, os seis indicadores: a fase da cultura, a água, o calor, o verde do satélite, a terra \
coberta e o aviso de sede. Os seis aparecem sempre, também os que estão tranquilos: uma frase curta para cada \
um, com um número só, começando pelos que pedem atenção. Nessa resposta, a indicação é sobre a lavoura de \
agora: o que acompanhar nos próximos dias (o que pede atenção), sem falar de trocar de rotação.
- "Como foi tal safra, dia a dia?": ensaio_da_rotacao com a safra (vale "pior_ano"). No replay de uma safra, conte \
os marcos na ordem, cada um com a data; o dia a dia inteiro a tela mostra.
- Depois da colheita ("o que a terra mostrou?", "quantos dias ficou sem planta?"): verde_do_satelite, com a safra \
se ele falar de uma.
- O argumento safra só entra quando o produtor pergunta por uma safra ("como foi a pior safra?", "e na safra \
2015-16?"). Para "vale trocar?", "milho ou sorgo?" ou "e a braquiária?", chame ensaio_da_rotacao sem safra. Uma \
consulta por pergunta costuma bastar: não repita a mesma consulta.

As regras que nunca mudam:
- Você não cria número. Todo número que você escrever tem de estar, igual, no que uma ferramenta devolveu nesta \
fala. Não some, não subtraia, não tire média, não faça porcentagem, não conte itens. Precisa de um número? Chame a \
ferramenta. Não tem o número? Diga sem número.
- Diga cada rotação como ela é. No milho com braquiária, o capim é plantado junto com o milho e fica cobrindo a \
terra depois da colheita dele: a braquiária não entra no lugar do milho. No sorgo, é o sorgo que entra no lugar do \
milho, na segunda safra.
- Nos marcos de uma safra há dois dias diferentes. Um é o dia em que a sede começa: acabou só a água fácil de \
tirar da terra, e ainda há água na terra. O outro, quando existe, é o dia em que a água que a planta alcança acabou. \
Nunca escreva que "a água acabou" no dia em que a sede começou.
- O número de "dias sem planta viva" é o tempo em que a terra fica descoberta: quanto menos dias, mais coberta \
ela fica. Nunca escreva que a terra fica "coberta" esse número de dias.
- Toda resposta com a ficha confirmada termina numa indicação: o que a conta mostra de melhor em cada caminho \
para o que mais preocupa o produtor, com os números lado a lado (as frases de benefício da comparação já dizem \
quem ficou na frente). Comece a última frase por "A indicação:". A decisão continua dele, com o agrônomo.
- Você nunca termina em recusa nem só em "não tenho". Se o produtor fala de uma cultura ou sequência que a conta \
não tem (feijão, algodão, "sorgo e milho", "e se eu puser feijão?"), consulte ensaio_da_rotacao e responda com os \
números da rotação guardada mais parecida, dizendo qual é; depois diga o que você sabe da cultura de fora numa \
frase curta, sem número, começando por "Sobre o feijão, por conhecimento geral:" (com o nome da cultura). Não \
estenda a conta para a sequência nova: os números são só os da rotação guardada.
- Se o lugar dele não está guardado, a conta usa o clima do lugar guardado mais próximo: consulte clima_do_lugar \
junto com ensaio_da_rotacao e diga uma vez de que lugar é o clima.
- Avisos: no máximo uma linha de risco e uma de "o que falta saber" por rotação. Não repita aviso, não explique \
limite da conta por extenso e não trate a data do dado como defeito.
- Pergunta sobre o que a conta não mede (adubo e nutrientes, pragas e doenças, preço e mercado, máquinas, \
crédito): não chame ferramenta; responda em poucas frases como conhecimento geral, sem número nenhum. O programa \
já escreve, na frente da sua resposta, o aviso de que é conhecimento geral e não saiu da conta: comece direto pelo \
assunto, sem repetir esse aviso.
- Não fale de ferramenta, de programa nem de conferência ao produtor: fale do que a conta mostrou e do que o \
satélite viu.
- Ao comparar, ponha os dois números lado a lado. Não diga a diferença entre eles, nem "o dobro", nem "metade", nem \
de qual dos dois um terceiro número está mais perto.
- Escreva as datas no jeito brasileiro, dia/mês/ano, como 14/03/2016. Não diga que dia é hoje: não escreva \
"hoje é" nem a data do dia da consulta.
- No "como está a lavoura", diga a data do dado uma vez só, discreta, no começo ("em 14/11/2026"), com o verbo no \
passado ("a soja estava em crescimento"). Não escreva "atraso", "aproximada", "ainda não chegou" nem "último dia \
com dado": a data basta. Os prazos contam a partir da data do dado: escreva como a conta escreve ("em 7 dias, em \
21/11/2026"), nunca "daqui a".
- Diga "o pior ano" e "o ano normal", como a conta diz. Não escreva "a safra mais seca" nem "o ano mais seco": o \
pior ano é o da pior colheita da região.
- Em resposta de conhecimento geral, não escreva data nenhuma, nem a de hoje.
- Escreva cada número igual ao da conta, com a mesma casa depois da vírgula: se a conta diz 252,0 mm, escreva \
252,0 mm (não 252 mm); se diz 96 dias, escreva 96 dias.
- O produtor não conhece as palavras da conta. Não escreva "mediana": diga "o valor do meio". Não escreva "zona das \
raízes": diga "a camada de terra onde ficam as raízes". Não escreva "faixa da hipótese": diga "do menor ao maior \
valor, porque isso não foi medido". Não escreva "chuva de modelo": diga "a chuva estimada por modelo de \
computador". Não escreva "GPM IMERG" nem "NASA GIBS" sozinhos: diga "a chuva medida por satélite da NASA". Não \
escreva "FAO" sozinho: diga "a FAO, o órgão da ONU para a agricultura". Não escreva "franco-arenosa": diga "terra \
de textura média".
- A falta de água de cada rotação, na comparação, é das culturas do ano inteiro (a soja mais a segunda safra), \
não só do milho ou do sorgo: diga "na rotação com milho faltaram", não "o milho deixou faltando". O que o satélite \
viu da terra vale para a rotação de hoje da região, não para uma cultura.
- Não diga que uma rotação é "a melhor" ou "a pior" de todas: diga em quê cada uma ficou na frente, como as \
frases de benefício dizem, com os números de cada uma lado a lado.
- Escreva só em português, com as letras do português.
- No marco da água no fundo, a frase da conta diz o que aconteceu: a água acabou, ficou perto do fundo sem acabar, \
ou a terra já estava seca no dia do plantio. Conte como a frase conta; não diga que a água acabou nos outros dois \
casos.
- Não peça nome, telefone, CPF nem endereço. Não prometa lucro nem produtividade.
- Embaixo da sua resposta o programa mostra a comparação das rotações lado a lado e o aviso de conversar com o \
agrônomo. Não repita a tabela inteira: explique o que ela mostra para a pergunta dele.
- Se a fala traz um fato da lavoura diferente do que está na ficha (outro dia de plantio da soja, outra coisa \
plantada, outra terra, outro lugar), anote primeiro com anotar_na_ficha. Se o fato já está na ficha, não anote de \
novo: a conta já usa esse fato. Consulte a conta e responda à pergunta de uma vez, sem repetir a ficha.
- Não explique o calendário, nem o ano das datas, nem como a conta foi feita: escreva as datas como a conta traz \
e siga para a resposta.
- Escreva texto corrido, sem markdown (sem asterisco, sem cerquilha, sem tabela). A resposta inteira, contando a \
indicação, cabe numa tela de celular: no máximo 600 caracteres. Passou disso, corte: fica o que responde à \
pergunta dele e a indicação, que é uma frase só, com os números lado a lado. Não escreva "Converse com o \
agrônomo antes de decidir": o programa já mostra essa frase embaixo."""


def _cortar(texto, teto):
    """O texto cortado para caber em `teto` bytes depois de virar JSON (a conta mais larga: \\uXXXX por letra
    acentuada). Assim o estado cabe no corpo da API, escreva quem chama o JSON como escrever.

    O corte cai sempre no fim de uma palavra inteira: um número ("232,9") ou uma data nunca fica pela metade.
    """
    texto = texto.strip()
    if len(json.dumps(texto)) <= teto:
        return texto
    while texto and len(json.dumps(texto + "…")) > teto:
        texto = texto[:max(len(texto) * 9 // 10, len(texto) - 40)]
    espaco = max(texto.rfind(" "), texto.rfind("\n"))
    if espaco > 0:
        texto = texto[:espaco]                           # sai a última palavra, que pode ter ficado pela metade
    else:
        texto = re.sub(r"[\d.,/:%+-]+$", "", texto)       # uma palavra só: sai o resto de número do fim
    return texto.rstrip() + "…"


def _guardar(resposta, conta, permitidos):
    """A fala do agente como fica no estado: cortada e conferida de novo. Se o corte deixou número fora da conta
    (uma data escrita em palavras, partida no meio), recua até o fim da frase anterior; sem frase, fica um aviso."""
    guardada = _cortar(resposta, TAMANHO_DA_FALA)
    while guardada != resposta and conferencia.conferir_texto(guardada, conta, permitidos):
        corpo = guardada[:-1]
        fim = max(corpo.rfind(ponto) for ponto in (". ", "! ", "? ", "\n"))
        if fim < FRASE_MINIMA:
            return FALA_LONGA
        guardada = corpo[:fim + 1].rstrip() + "…"
    return guardada


def _selo(fch):
    """O selo da ficha confirmada: a prova de que foi este programa que leu o "sim" do produtor para esta ficha.

    É um HMAC-SHA256 dos 5 campos da ficha e dos 2 "ditos" com o segredo da memória. Quem chama guarda e devolve o selo junto com o
    estado; sem o segredo, não dá para fazer o selo de outra ficha. Se o programa reiniciar, o segredo muda e o
    produtor confirma a ficha de novo.
    """
    marca = json.dumps([fch.get(campo) for campo in ficha.CAMPOS + ficha.DITOS], ensure_ascii=False, separators=(",", ":"))
    return hmac.new(_SEGREDO, marca.encode("utf-8"), hashlib.sha256).hexdigest()


def _selo_confere(selo, fch):
    return isinstance(selo, str) and hmac.compare_digest(selo.encode("utf-8"), _selo(fch).encode("utf-8"))


def _sem_marcas(texto):
    """O texto da IA sem as marcas de markdown, que a tela não desenha."""
    texto = re.sub(r"[*`]", "", texto or "")
    texto = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", texto)
    texto = re.sub(r"(?m)^\s*[-–]\s+", "• ", texto)
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


def _texto_da_ia(resposta):
    """O texto que a IA escreveu, limpo. Se ele parou no meio por falta de espaço, vale só até a última frase
    inteira; sem uma frase inteira, não vale nada (e saem as frases prontas)."""
    texto = _sem_marcas(resposta.get("texto") or "")
    if resposta.get("cortado") is True:
        fim = max(texto.rfind(ponto) for ponto in (".", "!", "?"))
        texto = texto[:fim + 1].strip() if fim >= FRASE_MINIMA else ""
    return texto


def _disse_sim(fala):
    """O "sim" do produtor, lido pelo programa: a fala começa por uma confirmação e não traz ressalva."""
    palavras = re.findall(r"[a-z0-9]+", fala)
    junto = " ".join(palavras)
    if not palavras or any(palavra in NEGAM for palavra in palavras):
        return False
    return any(junto == sim or junto.startswith(sim + " ") for sim in SIM)


def _novo():
    return {"v": VERSAO, "ficha": ficha.nova(), "selo": None, "pergunta": None, "momento": "antes", "falas": []}


def _conferir_estado(estado, listas, hoje):
    """O estado limpo (só o que o agente conhece), ou None se veio vazio ou estragado: aí a conversa recomeça."""
    if not isinstance(estado, dict) or estado.get("v") != VERSAO:
        return None
    falas = []
    for item in estado["falas"][-MAX_FALAS:] if isinstance(estado.get("falas"), list) else []:
        if (isinstance(item, dict) and item.get("de") in ("produtor", "agente")
                and isinstance(item.get("texto"), str) and item["texto"].strip()):
            falas.append({"de": item["de"], "texto": _cortar(item["texto"], TAMANHO_DA_FALA)})
    while falas and falas[0]["de"] != "produtor":
        falas.pop(0)
    pergunta = estado.get("pergunta")
    fch = ficha.conferir(estado.get("ficha"), listas, hoje)
    if fch["confirmada"] and not _selo_confere(estado.get("selo"), fch):
        fch = dict(fch, confirmada=False)            # "confirmada" sem o selo deste programa não vale: confirma de novo
    return {"v": VERSAO, "ficha": fch, "selo": None,
            "pergunta": _cortar(pergunta, TAMANHO_DA_PERGUNTA) if isinstance(pergunta, str) and pergunta.strip()
            else None,
            "momento": estado.get("momento") if estado.get("momento") in MOMENTOS else "antes", "falas": falas}


def _instrucoes(fch, hoje):
    """As regras do agente, com a ficha de agora e o ponto em que a conversa está."""
    if fch["confirmada"]:
        ponto = ("A ficha está confirmada. Para cada pergunta, consulte a ferramenta que responde a ela antes de "
                 "escrever. Se o produtor quiser mudar a ficha (outro lugar, outra terra, outra data), anote com "
                 "anotar_na_ficha: o programa pede a confirmação de novo.")
    elif ficha.completa(fch):
        ponto = ("A ficha está completa e espera o sim do produtor. Se ele corrigir algo, anote. As ferramentas da "
                 "conta só funcionam depois do sim; até lá, não diga nenhum número da conta.")
    else:
        ponto = ("A ficha ainda não está completa. Anote o que o produtor disser e peça o que falta, numa frase só. "
                 "As ferramentas da conta só funcionam depois que ele confirmar a ficha; até lá, não diga nenhum "
                 "número da conta.")
    if fch.get("rotacao_dita") and fch.get("rotacao_atual"):
        ponto += (f" O produtor planta «{fch['rotacao_dita']}», que a conta não tem. A conta compara com a rotação "
                  "guardada mais parecida (a que está marcada como a de hoje na comparação). Na resposta, diga que "
                  "rotação parecida é essa, dê a indicação com os números dela e, numa frase curta e sem número, o "
                  "que você sabe da cultura de fora, começando por \"Sobre ..., por conhecimento geral:\".")
    if fch.get("lugar_dito") and fch.get("cidade_id"):
        ponto += (f" A lavoura fica em «{fch['lugar_dito']}», que não está guardado. O clima da conta é o do lugar "
                  "guardado mais próximo (o cidade_id da ficha): consulte clima_do_lugar e ensaio_da_rotacao nesta fala "
                  "e diga uma vez de que lugar é o clima.")
    return (f"{REGRAS}\n\nHoje é {hoje.isoformat()}.\nA ficha agora: "
            f"{json.dumps(ficha.publica(fch), ensure_ascii=False)}\n{ponto}")


def _conversa(estado, fch, hoje, fala_do_produtor):
    return ([{"de": "sistema", "texto": _instrucoes(fch, hoje)}]
            + [{"de": item["de"], "texto": item["texto"]} for item in estado["falas"]]
            + [{"de": "produtor", "texto": fala_do_produtor}])


def _datas_dos_marcos(coisa, tipo):
    """As datas (dia, mês, ano) dos marcos de um tipo, em tudo o que as ferramentas devolveram nesta fala."""
    datas = set()
    if isinstance(coisa, dict):
        for chave, valor in coisa.items():
            if chave == "marcos" and isinstance(valor, list):
                for marco in valor:
                    if isinstance(marco, dict) and marco.get("tipo") == tipo:
                        try:
                            dia = datetime.date.fromisoformat(str(marco.get("data"))[:10])
                        except ValueError:
                            continue
                        datas.add((dia.day, dia.month, dia.year))
            else:
                datas |= _datas_dos_marcos(valor, tipo)
    elif isinstance(coisa, (list, tuple)):
        for item in coisa:
            datas |= _datas_dos_marcos(item, tipo)
    return datas


def _agua_acabou_no_dia_errado(texto, consultas):
    """Os trechos que dizem "a água acabou" colados à data de um marco em que a sede só começou."""
    resultados = [c.get("resultado") for c in consultas or () if isinstance(c, dict)]
    comeco = _datas_dos_marcos(resultados, "agua_acabou") - _datas_dos_marcos(resultados, "agua_no_fundo")
    achados = []
    for achado in AGUA_ACABOU.finditer(texto) if comeco else ():
        antes = [m.end() for m in FIM_DE_FRASE.finditer(texto, 0, achado.start())]
        depois = FIM_DE_FRASE.search(texto, achado.end())
        inicio, fim = (antes[-1] if antes else 0), (depois.start() if depois else len(texto))
        datas = list(DATA_NO_TEXTO.finditer(texto, inicio, fim))
        perto = [d for d in datas if d.end() <= achado.start()][-1:] or [d for d in datas if d.start() >= achado.end()][:1]
        for data in perto:                               # a data mais perto: a última antes, ou a primeira depois
            dia, mes, ano = int(data.group(1)), int(data.group(2)), data.group(3)
            if any((dia, mes) == (d, m) and (ano is None or int(ano) == a) for d, m, a in comeco):
                achados.append(f"{achado.group(0)} em {data.group(0)}" + A_SEDE_COMECOU)
    return achados


def _outro_alfabeto(texto):
    """Os trechos escritos com letra de outro alfabeto (visto na gravação de 2026-11-15: "fazer 监测 de campo")."""
    trechos, atual = [], ""
    for letra in texto + " ":
        de_fora = letra.isalpha() and letra not in "ªºµ" and "LATIN" not in unicodedata.name(letra, "")
        if de_fora:
            atual += letra
        elif atual:
            trechos.append(atual + OUTRO_ALFABETO)
            atual = ""
    return list(dict.fromkeys(trechos))


def _sentido_trocado(texto, consultas=()):
    """Os trechos com o sentido trocado: um número de "dias sem planta viva" dito como dias de terra coberta (o
    contrário), e "a água acabou" dito do dia em que a sede só começou (com os replays consultados nesta fala)."""
    texto = texto or ""
    return ([achado.group(0) + SENTIDO_TROCADO for achado in COBERTA_TANTOS_DIAS.finditer(texto)]
            + _agua_acabou_no_dia_errado(texto, consultas) + _outro_alfabeto(texto))


def _conta(fch, comparacao, consultas):
    """A conta contra a qual o texto é conferido: a ficha, a comparação e o que as ferramentas devolveram.

    Dos `consultas` entra só o `resultado` (o que veio do motor). Os `argumentos` são o que a IA pediu: não são conta.
    """
    return {"ficha": fch, "comparacao": comparacao,
            "resultados": [c.get("resultado") for c in consultas if isinstance(c, dict)]}


def _permitidos(hoje, comparacao=None):
    """Os números que valem além da conta: a data de hoje e quantas rotações a comparação tem."""
    return [hoje.isoformat()] + ([len(comparacao)] if comparacao else [])


def conferir_saida(saida, hoje):
    """Confere de novo o texto de uma saída guardada, só com o que está nela. Lista vazia = o texto está na conta.

    `hoje` é o dia em que a saída foi feita. Serve a quem guarda conversas (`exportar_conversas`) e a quem duvidar.
    """
    return conferencia.conferir_texto(saida["resposta"],
                                      _conta(saida["ficha"], saida["comparacao"], saida["consultas"]),
                                      _permitidos(hoje, saida["comparacao"])) + _sentido_trocado(saida["resposta"],
                                                                                                saida["consultas"])


def _sair(estado, texto, resposta, hoje, *, comparacao=None, apoio=None, momento=None,
          texto_de="frases_prontas", passou=True, sobras=(), tentativas=0, consultas=(), replay=None):
    """Monta o estado novo e a saída. O texto que sai, de quem for, passa pela conferência mais uma vez."""
    confirmada = estado["ficha"]["confirmada"] is True
    if confirmada and not comparacao:
        raise RuntimeError("Erro de dentro do agente: com a ficha confirmada, toda resposta leva a comparação das "
                           "rotações.")
    conta, permitidos = _conta(ficha.publica(estado["ficha"]), comparacao, consultas), _permitidos(hoje, comparacao)
    if conferencia.conferir_texto(resposta, conta, permitidos) or _sentido_trocado(resposta, consultas):
        resposta, texto_de, passou = (SEM_NUMERO if comparacao else NAO_ENTENDI), "frases_prontas", False
    momento = momento or estado["momento"]
    falas = estado["falas"] + [{"de": "produtor", "texto": _cortar(texto, TAMANHO_DA_FALA) or "…"},
                               {"de": "agente", "texto": _guardar(resposta, conta, permitidos)}]
    estado = dict(estado, momento=momento, falas=falas[-MAX_FALAS:],
                  selo=_selo(estado["ficha"]) if confirmada else None)
    saida = {"resposta": resposta, "momento": momento, "ficha": ficha.publica(estado["ficha"]),
             "comparacao": comparacao, "apoio": apoio,
             "conferencia": {"passou": passou, "sobras": list(sobras), "tentativas": tentativas},
             "aviso": AVISO, "texto_de": texto_de, "consultas": list(consultas), "replay": replay}
    return estado, saida


def resposta_da_rota(estado, saida):
    """O que a rota POST /agente devolve: o estado (para quem chama guardar) e a saída do passo."""
    return dict({"estado": estado}, **saida)


# ---------------------------------------------------------------------------------------------- a ficha

def _resultado_da_ficha(fch, aceitos, recusados, listas):
    if ficha.completa(fch):
        dizer = ("A ficha está completa. O programa mostra a ficha ao produtor e pede o sim dele: não escreva a "
                 "ficha de novo.")
    else:
        dizer = "Peça ao produtor o que falta, numa frase só e sem número. " + ficha.pergunta_do_que_falta(fch, listas)
    return {"anotado": aceitos, "recusado": recusados, "ficha": ficha.publica(fch), "o_que_dizer": dizer}


def _colher(estado, texto, modelo, listas, hoje):
    """A ficha ainda não foi confirmada: a IA anota o que o produtor disse e pede o que falta."""
    antes = fch = estado["ficha"]
    definicoes = [ficha.definicao(listas)]
    mensagens = _conversa(estado, fch, hoje, texto)
    texto_da_ia, pedidos = "", 0
    while pedidos < 3:
        resposta = modelo.responder(mensagens, definicoes)
        pedidos += 1
        if not resposta["chamadas"]:
            texto_da_ia = _texto_da_ia(resposta)
            break
        mensagens.append({"de": "agente", "texto": resposta["texto"], "chamadas": resposta["chamadas"]})
        for pedido in resposta["chamadas"]:
            if pedido["nome"] == "anotar_na_ficha":
                fch, aceitos, recusados = ficha.anotar(fch, pedido["argumentos"], listas, hoje)
                resultado = _resultado_da_ficha(fch, aceitos, recusados, listas)
            elif pedido["nome"] in ferramentas.NOMES:            # a conta não roda antes do sim do produtor
                resultado = {"erro": FICHA_NAO_CONFIRMADA}
            else:
                resultado = {"erro": f"A ferramenta {pedido['nome']} não existe."}
            mensagens.append({"de": "ferramenta", "id": pedido["id"], "nome": pedido["nome"],
                              "resultado": resultado})
        if ficha.completa(fch) and fch != antes:                 # o programa mostra a ficha: não precisa de mais
            break
    estado = dict(estado, ficha=fch)
    if "?" in texto:
        estado["pergunta"] = _cortar(texto, TAMANHO_DA_PERGUNTA)
    sobras = (conferencia.conferir_texto(texto_da_ia, _conta(ficha.publica(fch), None, ()), _permitidos(hoje))
              if texto_da_ia else [])
    vale = bool(texto_da_ia) and not sobras
    if ficha.completa(fch):
        pronto = ficha.resumo(fch, listas)
        vale = vale and fch == antes                             # mudou a ficha: sai só a ficha, para conferir
    else:
        pronto = ficha.pergunta_do_que_falta(fch, listas)
    if not vale:
        resposta_final = pronto
    elif ficha.completa(fch) or "?" not in texto_da_ia:
        resposta_final = texto_da_ia + "\n\n" + pronto
    else:
        resposta_final = texto_da_ia
    return _sair(estado, texto, resposta_final, hoje, texto_de="ia" if vale else "frases_prontas",
                 passou=not sobras, sobras=sobras, tentativas=1 if texto_da_ia else 0)


# ---------------------------------------------------------------------------------------------- a conta

class _Consultas:
    """As consultas de uma fala: roda cada ferramenta, guarda o que a IA leu e não repete o ensaio."""

    def __init__(self, fch):
        self.ficha, self.feitas, self.replay, self._ensaio = fch, [], None, None

    def ensaio(self):
        if self._ensaio is None:
            self._ensaio = ferramentas.ensaio_da_rotacao(self.ficha)
        return self._ensaio

    def chamar(self, nome, argumentos):
        pedido, argumentos = (argumentos if isinstance(argumentos, dict) else {}), {}
        aceita = ARGUMENTOS.get(nome, ())             # cada ferramenta só aceita o argumento dela, e no formato dele
        if "safra" in aceita and isinstance(pedido.get("safra"), str) and pedido["safra"].strip():
            argumentos["safra"] = pedido["safra"].strip()[:20]
        if "hoje" in aceita and pedido.get("hoje") is True:
            argumentos["hoje"] = True
        if nome == "ensaio_da_rotacao" and not argumentos.get("safra"):
            resultado = self.ensaio()
        else:
            resultado = ferramentas.chamar(nome, self.ficha, argumentos)
        if "erro" in resultado:
            return resultado
        if isinstance(resultado.get("replay"), dict):
            self.replay = resultado["replay"]
        self.feitas.append({"ferramenta": nome, "argumentos": argumentos,
                            "resultado": ferramentas.para_a_ia(resultado)})
        return self.feitas[-1]["resultado"]


def _tem(consulta, chave):
    bloco = consulta["resultado"].get(chave)
    return isinstance(bloco, dict) and bloco.get("disponivel") is not False


def _painel(consulta):
    """A consulta trouxe o painel da lavoura hoje (a ferramenta lavoura_hoje, com o motor respondendo)."""
    return consulta["ferramenta"] == "lavoura_hoje" and consulta["resultado"].get("disponivel") is not False


def _primeira_frase(texto):
    """A primeira frase de um texto do motor (a linha curta de cada item do painel)."""
    return re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý])", texto.strip(), maxsplit=1)[0]


def _de_hoje(comparacao):
    return next((item for item in comparacao or () if item.get("de_hoje") is True), None)


def _frases_dos_ditos(fch, comparacao, listas):
    """A indicação pronta dos campos "ditos": qual rotação parecida (com a evidência dela) e de que lugar é o clima."""
    partes, de_hoje = [], _de_hoje(comparacao)
    if fch.get("rotacao_dita") and de_hoje and isinstance(de_hoje.get("evidencia"), str):
        partes.append(ROTACAO_PARECIDA.format(dito=fch["rotacao_dita"], nome=de_hoje["nome"],
                                              evidencia=de_hoje["evidencia"]))
    if fch.get("lugar_dito"):
        partes.append(LUGAR_PROXIMO.format(lugar=ficha.nome_do_lugar(fch, listas), dito=fch["lugar_dito"]))
    return partes


def _notas_dos_ditos(fch, comparacao, listas):
    """A frase curta que o programa acrescenta quando há campo "dito" e o texto não diz "conhecimento geral"."""
    de_hoje = _de_hoje(comparacao)
    if fch.get("rotacao_dita") and de_hoje:
        return NOTA_DA_ROTACAO_DITA.format(dito=fch["rotacao_dita"], nome=de_hoje["nome"])
    if fch.get("lugar_dito"):
        return NOTA_DO_LUGAR_DITO.format(dito=fch["lugar_dito"], lugar=ficha.nome_do_lugar(fch, listas))
    return None


def _indicacao_pronta(comparacao):
    """A indicação sem IA: o benefício que a conta escreveu de cada caminho (as frases do motor, sem mexer)."""
    linhas = [f"• {item['nome']}: {item['beneficio']}" for item in comparacao
              if isinstance(item.get("nome"), str) and isinstance(item.get("beneficio"), str)]
    return "\n".join([O_QUE_A_CONTA_INDICA] + linhas) if linhas else TAMBEM_COMPAREI.format(quantas=len(comparacao))


def _apoio(consultas):
    """Em que a resposta se apoia, pelo que a IA consultou de fato."""
    if any(c["ferramenta"] == "ensaio_da_rotacao" or _tem(c, "registro") or _tem(c, "hoje") or _painel(c)
           for c in consultas):
        return "conta"
    return "dados_do_lugar" if consultas else "conhecimento_geral"


def _momento(consultas):
    if any(_tem(c, "registro") for c in consultas):
        return "depois"
    if any(_tem(c, "replay") or _tem(c, "hoje") or _painel(c) for c in consultas):
        return "durante"
    return "depois" if any(c["ferramenta"] == "verde_do_satelite" for c in consultas) else "antes"


def _frases_de(bloco):
    """As frases prontas que o motor pôs num bloco: `frase` e `frases`."""
    if not isinstance(bloco, dict):
        return []
    frases = [bloco.get("frase")] + (bloco["frases"] if isinstance(bloco.get("frases"), list) else [])
    return [f.strip() for f in frases if isinstance(f, str) and f.strip()]


def _data_do_marco(iso):
    try:
        dia = datetime.date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso)
    return f"{dia.day:02d}/{dia.month:02d}/{dia.year}"


def _frases_da_comparacao(comparacao, lugar):
    linhas = [f"Fiz a conta para {lugar} e comparei {len(comparacao)} rotações, contando a sua de hoje:"]
    linhas += [f"• {item['nome']}{' (a de hoje)' if item.get('de_hoje') is True else ''}: {item['evidencia']}"
               for item in comparacao]
    return "\n".join(linhas)


def _frases_prontas(consultas, comparacao, lugar, ditos=()):
    """A resposta sem IA: só as frases que o motor escreveu, na ordem do que foi consultado. Termina sempre numa
    indicação: o benefício de cada caminho, como a conta escreveu. `ditos`: as frases dos campos "ditos" da ficha."""
    if not consultas:
        de_hoje = _de_hoje(comparacao)
        sem_conta = (SEM_CONTA_COM_A_ROTACAO.format(nome=de_hoje["nome"], evidencia=de_hoje["evidencia"],
                                                    beneficio=de_hoje["beneficio"])
                     if de_hoje and all(isinstance(de_hoje.get(c), str) for c in ("nome", "evidencia", "beneficio"))
                     else SEM_CONTA)
        return "\n\n".join(dict.fromkeys(list(ditos) + [sem_conta]))
    partes = list(ditos)
    for consulta in consultas:
        resultado = consulta["resultado"]
        if _painel(consulta):
            itens = [i for i in resultado.get("itens") or [] if isinstance(i, dict) and isinstance(i.get("frase"), str)]
            partes.append("\n".join(_frases_de(resultado)[:1] + [f"• {_primeira_frase(i['frase'])}" for i in itens]))
        elif consulta["ferramenta"] == "lavoura_hoje":
            partes += [resultado["aviso"]] if isinstance(resultado.get("aviso"), str) else []
        elif consulta["ferramenta"] == "clima_do_lugar":
            anos = resultado.get("regra_dos_anos") if isinstance(resultado.get("regra_dos_anos"), dict) else {}
            if anos.get("pior_ano") and anos.get("ano_normal"):
                partes.append(f"Em {lugar}, pelo que os satélites registraram, a pior safra foi a de "
                              f"{anos['pior_ano']} e a safra normal, a de {anos['ano_normal']}.")
            partes += _frases_de(resultado) + _frases_de(resultado.get("calor"))
            hoje = resultado.get("hoje") if isinstance(resultado.get("hoje"), dict) else {}
            partes += _frases_de(hoje) + ([hoje["aviso"]] if isinstance(hoje.get("aviso"), str) else [])
        elif consulta["ferramenta"] == "verde_do_satelite":
            # Pergunta de uma safra: a resposta começa pelo registro dela (o retrato geral do satélite já foi a
            # resposta da pergunta sem safra, e duas respostas seguidas não podem começar igual).
            registro = resultado.get("registro") if isinstance(resultado.get("registro"), dict) else {}
            do_registro = _frases_de(registro) + ([registro["aviso"]] if isinstance(registro.get("aviso"), str) else [])
            geral = _frases_de(resultado) + ([resultado["aviso"]] if isinstance(resultado.get("aviso"), str) else [])
            partes += do_registro or geral
        elif isinstance(resultado.get("replay"), dict):
            replay = resultado["replay"]
            marcos = [m for m in replay.get("marcos") or [] if isinstance(m, dict) and isinstance(m.get("frase"), str)]
            if marcos:
                partes.append(f"A safra {replay.get('safra')} em {lugar}, dia a dia:\n" + "\n".join(
                    f"• {_data_do_marco(m.get('data'))}: {m['frase']}" for m in marcos[:QUANTOS_MARCOS]))
    if partes == list(ditos):                         # a fala foi só sobre a comparação: a evidência de cada uma
        partes.append(_frases_da_comparacao(comparacao, lugar))
    return "\n\n".join(dict.fromkeys(partes + [_indicacao_pronta(comparacao)]))


def _conta_recusada(estado, texto, erro, hoje):
    """O motor recusou a ficha: ela deixa de estar confirmada, e o produtor lê o motivo em português."""
    motivo = str(erro).replace("Entrada fora do formato:", "").strip().rstrip(".") + "."
    estado = dict(estado, ficha=dict(estado["ficha"], confirmada=False))
    return _sair(estado, texto, CONTA_RECUSADA.format(motivo=motivo[0].upper() + motivo[1:]), hoje,
                 consultas=[{"ferramenta": "ensaio_da_rotacao", "argumentos": {}, "resultado": {"erro": motivo}}])


def _responder(estado, texto, pergunta, modelo, listas, hoje, pronto=None):
    """A ficha está confirmada: a IA consulta as ferramentas e explica; o programa confere e completa.

    Sem `pergunta` (uma cortesia, uma fala vazia), a IA não é chamada: sai o texto `pronto`, com a comparação.
    """
    fch = estado["ficha"]
    consultas = _Consultas(fch)
    try:
        base = consultas.ensaio()                    # a comparação sai sempre, pergunte a IA ou não
    except ferramentas.FichaRecusada as erro:
        return _conta_recusada(estado, texto, erro, hoje)
    comparacao, lugar = base["rotacoes"], base["lugar"]
    permitidos = _permitidos(hoje, comparacao)

    def conta():
        return _conta(ficha.publica(fch), comparacao, consultas.feitas)

    if pergunta is None:                              # uma cortesia ("obrigado", "ok"): não precisa da IA
        comeco = "Por nada! " if any(pedaco in conversa._limpar(texto) for pedaco in AGRADECEU) else "Combinado. "
        return _sair(estado, texto, pronto or comeco + DE_NADA, hoje, comparacao=comparacao, apoio="conta")
    definicoes = ferramentas.definicoes() + [ficha.definicao(listas)]
    mensagens = _conversa(estado, fch, hoje, pergunta)
    texto_da_ia, sobras_da_ia, pedidos, voltas, tentativas, nova_ficha = "", [], 0, 0, 0, None
    while pedidos < PEDIDOS:
        resposta = modelo.responder(mensagens, definicoes)
        pedidos += 1
        if resposta["chamadas"]:
            if voltas >= VOLTAS:
                break
            voltas += 1
            mensagens.append({"de": "agente", "texto": resposta["texto"], "chamadas": resposta["chamadas"]})
            for pedido in resposta["chamadas"]:
                if pedido["nome"] == "anotar_na_ficha":
                    mudada, aceitos, recusados = ficha.anotar(nova_ficha or fch, pedido["argumentos"], listas, hoje)
                    if mudada != (nova_ficha or fch):
                        nova_ficha = mudada
                    resultado = _resultado_da_ficha(mudada, aceitos, recusados, listas)
                elif pedido["nome"] in ferramentas.NOMES and nova_ficha is None:
                    try:
                        resultado = consultas.chamar(pedido["nome"], pedido["argumentos"])
                    except ferramentas.FichaRecusada as erro:
                        return _conta_recusada(estado, texto, erro, hoje)
                elif pedido["nome"] in ferramentas.NOMES:
                    resultado = {"erro": FICHA_NAO_CONFIRMADA}
                else:
                    resultado = {"erro": f"A ferramenta {pedido['nome']} não existe."}
                mensagens.append({"de": "ferramenta", "id": pedido["id"], "nome": pedido["nome"],
                                  "resultado": resultado})
            if nova_ficha is not None:
                break
            continue
        tentativas += 1
        texto_da_ia = _texto_da_ia(resposta)
        if not texto_da_ia:
            break
        if consultas.feitas:
            sobras = conferencia.conferir_texto(texto_da_ia, conta(), permitidos)
        else:                                         # sem consulta nesta fala, o texto não pode ter número nenhum
            sobras = conferencia.conferir_texto(texto_da_ia, {})
        sobras = sobras + _sentido_trocado(texto_da_ia, consultas.feitas)
        if not sobras:
            break
        sobras_da_ia, falhou, texto_da_ia = sobras, texto_da_ia, ""
        if tentativas >= 2:
            break
        mensagens.append({"de": "agente", "texto": falhou})
        mensagens.append({"de": "programa", "texto": AVISO_DA_TRAVA.format(sobras=", ".join(sobras))})

    if nova_ficha is not None:                        # a ficha mudou: a conta espera o sim de novo
        estado = dict(estado, ficha=nova_ficha, pergunta=_cortar(texto, TAMANHO_DA_PERGUNTA) if "?" in texto else None)
        return _sair(estado, texto, FICHA_MUDOU + "\n\n" + ficha.resumo(nova_ficha, listas), hoje)
    apoio = _apoio(consultas.feitas)
    if texto_da_ia:
        final = texto_da_ia if apoio != "conhecimento_geral" else AVISO_DE_CONHECIMENTO_GERAL + "\n\n" + texto_da_ia
        nota = _notas_dos_ditos(fch, comparacao, listas)
        if nota and "conhecimento geral" not in final.lower():     # a garantia do programa: a parte de fora da conta
            final += "\n\n" + nota                                # é dita como conhecimento geral
        sobras_da_ia = []
    else:
        final = _frases_prontas(consultas.feitas, comparacao, lugar, _frases_dos_ditos(fch, comparacao, listas))
    return _sair(dict(estado, pergunta=None), texto, final, hoje, comparacao=comparacao, apoio=apoio,
                 momento=_momento(consultas.feitas), texto_de="ia" if texto_da_ia else "frases_prontas",
                 passou=not sobras_da_ia, sobras=sobras_da_ia, tentativas=tentativas, consultas=consultas.feitas,
                 replay=consultas.replay)


# ---------------------------------------------------------------------------------------------- o passo

def passo(estado, texto, modelo, hoje=None):
    """Um passo da conversa: o estado anterior (None no começo), a fala do produtor e o modelo (a IA).

    Devolve (o estado novo, a saída). A saída tem os campos do mapa (seção 7.4): `resposta`, `momento`, `ficha`,
    `comparacao`, `apoio`, `conferencia` e `aviso`; e mais `texto_de` ("ia" ou "frases_prontas"), `consultas` (o que a
    IA leu das ferramentas nesta fala, para qualquer um conferir os números de novo) e `replay` (os dias de uma
    safra, quando o replay foi pedido). `hoje` é a data de hoje (serve aos testes).
    Erros: `ferramentas.ContaIndisponivel` (o motor não tem a conta) e `modelo.ErroDoModelo` (a IA não respondeu).
    """
    if estado is not None and not isinstance(estado, dict):
        raise ValueError("Conversa fora do formato: o estado tem de ser o que a chamada anterior devolveu (um objeto) "
                         "ou vazio (null), no começo.")
    if not isinstance(texto, str):
        raise ValueError("Conversa fora do formato: o texto tem de ser a frase que a pessoa escreveu.")
    hoje = hoje or datetime.date.today()
    listas = ferramentas.listas()
    texto = " ".join(texto.split())[:TAMANHO_DO_TEXTO]
    fala = conversa._limpar(texto)
    estado = _conferir_estado(estado, listas, hoje) or _novo()
    if fala in conversa.DE_NOVO:
        estado = _novo()
    fch = estado["ficha"]
    vazia = not any(fch.get(campo) for campo in ficha.CAMPOS + ficha.DITOS)
    if vazia and (not fala or fala in OLA or fala in conversa.DE_NOVO):
        return _sair(estado, texto, SAUDACAO + "\n\n" + ficha.pergunta_do_que_falta(fch, listas), hoje)
    if not fala and fch["confirmada"]:                # nem a fala vazia sai sem a comparação
        return _responder(estado, texto, None, modelo, listas, hoje, pronto=NAO_ENTENDI + " " + PODE_PERGUNTAR)
    if not fala:
        pronto = ficha.resumo(fch, listas) if ficha.completa(fch) else ficha.pergunta_do_que_falta(fch, listas)
        return _sair(estado, texto, NAO_ENTENDI + " " + pronto, hoje)
    if ficha.completa(fch) and not fch["confirmada"] and _disse_sim(fala):
        pergunta = texto if "?" in texto else (estado["pergunta"] or PERGUNTA_PADRAO)
        estado = dict(estado, ficha=ficha.confirmar(fch))
        aviso = f"O produtor confirmou a ficha. Responda agora à pergunta dele: «{pergunta}»"
        if fch.get("plantio_da_soja"):
            aviso += (" Ele disse o dia em que plantou a soja: se a pergunta é sobre o que plantar ou trocar, comece "
                      "pelo que o calendário da conta mostra com essa data, numa frase só (quando a soja sai da terra "
                      "e quando a segunda safra entra).")
        return _responder(estado, texto, f"{texto}\n\n[Aviso do programa; o produtor não vê] {aviso}", modelo, listas,
                          hoje)
    if not fch["confirmada"]:
        return _colher(estado, texto, modelo, listas, hoje)
    return _responder(estado, texto, None if fala in CORTESIAS else texto, modelo, listas, hoje)


def texto_inteiro(saida):
    """A saída em texto corrido, para um canal sem tela: a resposta, a comparação (as frases do motor) e o aviso."""
    blocos = [saida["resposta"]]
    for item in saida.get("comparacao") or []:
        blocos.append("\n".join([f"{item['nome']}{' (a de hoje)' if item.get('de_hoje') is True else ''}",
                                 f"A evidência: {item['evidencia']}", f"O benefício: {item['beneficio']}",
                                 f"O risco: {item['risco']}", f"O que falta saber: {item['falta_saber']}"]))
    return "\n\n".join(blocos + [saida["aviso"]])


def main():
    """Uma conversa no terminal, com a IA de verdade (a chave vem do ambiente)."""
    from orbita import modelo as pecas
    try:
        ia = pecas.do_ambiente()
    except pecas.SemChave as erro:
        print(f"{erro} Sem chave, rode os testes (python3 -m unittest) ou grave as conversas de exemplo "
              "(python3 -m orbita.exportar_conversas <pasta>).", file=sys.stderr)
        return 1
    print(f"Órbita Rural · o agente (modelo: {ia.nome}). Linha vazia ou Ctrl+C encerra.\n")
    estado = None
    try:
        estado, saida = passo(estado, "oi", ia)
        while True:
            print(texto_inteiro(saida) + f"\n[apoio: {saida['apoio']} · texto de: {saida['texto_de']} · "
                  f"conferência: {saida['conferencia']}]\n")
            fala_do_produtor = input("> ").strip()
            if not fala_do_produtor:
                break
            estado, saida = passo(estado, fala_do_produtor, ia)
    except (KeyboardInterrupt, EOFError):
        pass
    except (pecas.ErroDoModelo, ferramentas.ContaIndisponivel) as erro:
        print(str(erro), file=sys.stderr)
        return 1
    print(f"\nGasto desta conversa: {ia.uso['pedidos']} pedidos à IA, {ia.uso['custo_usd']:.4f} dólares.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
