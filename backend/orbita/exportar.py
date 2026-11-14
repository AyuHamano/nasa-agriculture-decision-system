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


def _gravar(arquivo, texto):
    """Grava num arquivo ao lado e troca de uma vez: o site nunca lê um arquivo pela metade."""
    provisorio = arquivo.with_name(arquivo.name + ".gravando")
    provisorio.write_text(texto, encoding="utf-8")
    os.replace(provisorio, arquivo)


def exportar(pasta):
    """Pergunta ao motor uma vez por tipo de terra e grava os dois arquivos. Devolve os caminhos gravados."""
    pasta = Path(pasta)
    respostas = {terra: motor.responder(dict(PERGUNTA, terra=terra)) for terra in TERRAS}
    agora = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    entrada = respostas["media"].get("entrada", {})                   # o que o motor usou de fato
    usados = dict(PERGUNTA, terras=list(TERRAS), chuva=entrada.get("chuva"), regra=entrada.get("regra"))
    pasta.mkdir(parents=True, exist_ok=True)
    objeto = json.dumps(respostas, ensure_ascii=False, separators=(",", ":"))
    objeto = objeto.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")   # quebras que o JavaScript antigo recusa
    _gravar(pasta / "respostas.js",
            "/* Gerado com IA (Claude) */\n"
            f"/* As 3 respostas do motor do Órbita Rural (uma por tipo de terra), gravadas em {agora} por\n"
            f"   {COMANDO}, com: {json.dumps(usados, ensure_ascii=False)}\n"
            "   Não editar à mão: o site só mostra o que está aqui. */\n"
            f"window.ORBITA_RESPOSTAS = {objeto};\n")
    _gravar(pasta / "respostas.json",
            json.dumps({"gerado_em": agora, "gerado_por": COMANDO + " (Gerado com IA (Claude))",
                        "parametros_usados": usados, "respostas": respostas}, ensure_ascii=False, indent=1) + "\n")
    return pasta / "respostas.js", pasta / "respostas.json"


def main(argv=None):
    argumentos = sys.argv[1:] if argv is None else list(argv)
    if len(argumentos) != 1 or argumentos[0].startswith("-"):
        print(f"Diga a pasta onde gravar. Exemplo: {COMANDO.replace('<pasta>', '../frontend/dados')}", file=sys.stderr)
        return 2
    try:
        js, dados = exportar(argumentos[0])
    except (OSError, ValueError) as erro:
        print(f"Não deu para gravar na pasta {argumentos[0]}: {erro}. Confira se o caminho é de uma pasta e se dá "
              "para escrever nela, e rode de novo.", file=sys.stderr)
        return 1
    print(f"Gravado: {js} ({js.stat().st_size} bytes) e {dados} ({dados.stat().st_size} bytes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
