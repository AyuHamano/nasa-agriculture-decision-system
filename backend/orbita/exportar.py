# Gerado com IA (Claude)
"""Grava o arquivo de respostas que o site lê: a resposta inteira do motor para cada tipo de terra.

De dentro de backend/:
    python3 -m orbita.exportar <pasta>

Grava na pasta (cria, se não existir):
    respostas.js     window.ORBITA_RESPOSTAS = {"pouca": {...}, "media": {...}, "muita": {...}};
    respostas.json   {"gerado_em": a hora, "gerado_por": o comando, "parametros_usados": {...}, "respostas": o mesmo
                     objeto do respostas.js}

Todas as notas vão iguais a 3: as notas não mudam nenhum número, só a ordem da explicação, e essa ordem o site refaz
com as notas da tela. O site não faz conta: só mostra o que está nestes arquivos. Rodar de novo quando o motor mudar.

Desde 2026-11-15 cada resposta traz também `comparacao_das_rotacoes` (as 3 rotações), `calor` e `terra_coberta`. As
opções, todas opcionais (sem elas, sai como sempre):
    --cidade jatai            a cidade (rio_verde, jatai ou silvania)
    --rotacao soja,sorgo      a rotação de hoje do produtor (uma do cardápio)
    --plantio 2026-11-20      a data do plantio da soja
    --preocupacao calor       o que mais preocupa (agua, calor ou terra)
    --sem-notas               pergunta sem as notas de 1 a 5 (as notas saíram da tela nova)
    --tudo                    grava também motor.js e motor.json: window.ORBITA_MOTOR = {"lugares": o clima de cada
                              cidade, "respostas": a resposta de cada cidade (terra média, sem notas), "replay": a
                              safra 2015-16 dia a dia, "hoje": o retrato do último dia com dado, "registro": o
                              registro da safra 2015-16}, tudo na rotação pedida. É o que o motor oferece, guardado,
                              para a tela mostrar sem servidor.
"""
import datetime
import json
import os
import sys
from pathlib import Path

from orbita import motor

TERRAS = ("pouca", "media", "muita")
PERGUNTA = {"cidade_id": "rio_verde", "rotacao_atual": ["soja", "milho", "pousio"],
            "prioridades": {"agua": 3, "solo": 3, "renda": 3, "erosao": 3}}
COMANDO = "python3 -m orbita.exportar <pasta>"
SAFRA_DO_REPLAY = "2015-16"         # a safra da pior colheita em Rio Verde: a prova de que a conta acerta


def _gravar(arquivo, texto):
    """Grava num arquivo ao lado e troca de uma vez: o site nunca lê um arquivo pela metade."""
    provisorio = arquivo.with_name(arquivo.name + ".gravando")
    provisorio.write_text(texto, encoding="utf-8")
    os.replace(provisorio, arquivo)


def _js(coisa):
    texto = json.dumps(coisa, ensure_ascii=False, separators=(",", ":"))
    return texto.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")    # quebras que o JavaScript antigo recusa


def exportar_tudo(pasta, pergunta, agora):
    """Grava motor.js e motor.json: o que o motor oferece, guardado, na rotação e na data da pergunta."""
    base = {k: v for k, v in pergunta.items() if k != "prioridades"}
    tudo = {"lugares": {c: motor.clima_do_lugar(c) for c in motor.CIDADES},
            "respostas": {c: motor.responder(dict(base, cidade_id=c, terra="media")) for c in motor.CIDADES},
            "replay": {c: motor.replay_da_safra(dict(base, cidade_id=c, terra="media"), SAFRA_DO_REPLAY)
                       for c in motor.CIDADES},
            "hoje": {c: motor.como_esta_hoje(dict(base, cidade_id=c, terra="media")) for c in motor.CIDADES},
            "registro": {c: motor.registro_da_safra(dict(base, cidade_id=c, terra="media"), SAFRA_DO_REPLAY)
                         for c in motor.CIDADES}}
    _gravar(pasta / "motor.js",
            "/* Gerado com IA (Claude) */\n"
            f"/* O que o motor do Órbita Rural oferece, guardado em {agora} por {COMANDO} --tudo, com:\n"
            f"   {json.dumps(base, ensure_ascii=False)} (terra média; a safra do replay e do registro: "
            f"{SAFRA_DO_REPLAY}). Não editar à mão. */\n"
            f"window.ORBITA_MOTOR = {_js(tudo)};\n")
    _gravar(pasta / "motor.json",
            json.dumps({"gerado_em": agora, "gerado_por": COMANDO + " --tudo (Gerado com IA (Claude))",
                        "parametros_usados": dict(base, terra="media", safra=SAFRA_DO_REPLAY), "motor": tudo},
                       ensure_ascii=False, indent=1) + "\n")
    return pasta / "motor.js", pasta / "motor.json"


def exportar(pasta, pergunta=None, tudo=False):
    """Pergunta ao motor uma vez por tipo de terra e grava os dois arquivos. Devolve os caminhos gravados.

    `pergunta`: a pergunta sem a terra (sem ela, a de sempre: Rio Verde, soja-milho-pousio, notas iguais a 3).
    `tudo`: grava também motor.js e motor.json (ver o cabeçalho).
    """
    pasta = Path(pasta)
    pergunta = dict(PERGUNTA if pergunta is None else pergunta)
    respostas = {terra: motor.responder(dict(pergunta, terra=terra)) for terra in TERRAS}
    agora = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    entrada = respostas["media"].get("entrada", {})                   # o que o motor usou de fato
    usados = dict(pergunta, terras=list(TERRAS), chuva=entrada.get("chuva"), regra=entrada.get("regra"))
    pasta.mkdir(parents=True, exist_ok=True)
    objeto = _js(respostas)
    _gravar(pasta / "respostas.js",
            "/* Gerado com IA (Claude) */\n"
            f"/* As 3 respostas do motor do Órbita Rural (uma por tipo de terra), gravadas em {agora} por\n"
            f"   {COMANDO}, com: {json.dumps(usados, ensure_ascii=False)}\n"
            "   Não editar à mão: o site só mostra o que está aqui. */\n"
            f"window.ORBITA_RESPOSTAS = {objeto};\n")
    _gravar(pasta / "respostas.json",
            json.dumps({"gerado_em": agora, "gerado_por": COMANDO + " (Gerado com IA (Claude))",
                        "parametros_usados": usados, "respostas": respostas}, ensure_ascii=False, indent=1) + "\n")
    gravados = [pasta / "respostas.js", pasta / "respostas.json"]
    if tudo:
        gravados += exportar_tudo(pasta, pergunta, agora)
    return tuple(gravados)


OPCOES = {"--cidade": "cidade_id", "--plantio": "plantio_da_soja", "--preocupacao": "preocupacao"}


def ler_argumentos(argumentos):
    """Dos argumentos do comando para (a pasta, a pergunta, se grava tudo). Fora do formato: ValueError."""
    pasta, pergunta, tudo, i = None, dict(PERGUNTA), False, 0
    while i < len(argumentos):
        argumento = argumentos[i]
        if argumento in OPCOES or argumento == "--rotacao":
            if i + 1 >= len(argumentos):
                raise ValueError(f"faltou o valor de {argumento}")
            valor = argumentos[i + 1]
            if argumento == "--rotacao":
                pergunta["rotacao_atual"] = [parte.strip() for parte in valor.split(",") if parte.strip()]
            else:
                pergunta[OPCOES[argumento]] = valor
            i += 2
        elif argumento == "--sem-notas":
            pergunta.pop("prioridades", None)
            i += 1
        elif argumento == "--tudo":
            tudo, i = True, i + 1
        elif argumento.startswith("-") or pasta is not None:
            raise ValueError(f"não conheço o argumento {argumento}")
        else:
            pasta, i = argumento, i + 1
    if pasta is None:
        raise ValueError("faltou a pasta")
    return pasta, pergunta, tudo


def main(argv=None):
    argumentos = sys.argv[1:] if argv is None else list(argv)
    try:
        pasta, pergunta, tudo = ler_argumentos(argumentos)
    except ValueError as erro:
        print(f"Diga a pasta onde gravar ({erro}). Exemplo: {COMANDO.replace('<pasta>', '../frontend/dados')}; as "
              "opções: --cidade, --rotacao, --plantio, --preocupacao, --sem-notas e --tudo.", file=sys.stderr)
        return 2
    try:
        gravados = exportar(pasta, pergunta, tudo)
    except (OSError, ValueError) as erro:
        print(f"Não deu para gravar na pasta {pasta}: {erro}. Confira se o caminho é de uma pasta e se dá "
              "para escrever nela, e rode de novo.", file=sys.stderr)
        return 1
    print("Gravado: " + " e ".join(f"{arquivo} ({arquivo.stat().st_size} bytes)" for arquivo in gravados) + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
