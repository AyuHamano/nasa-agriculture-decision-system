# Gerado com IA (Claude)
"""O comando de perguntar ao motor, sem site.

De dentro de backend/:
    python3 -m orbita.perguntar --agua 5 --solo 4 --renda 2 --erosao 3 --terra media          (em português)
    python3 -m orbita.perguntar --agua 5 --solo 4 --renda 2 --erosao 3 --terra media --json   (a estrutura)
"""
import argparse
import json
import sys

from orbita import explicacao, motor


class _Argumentos(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(f"Comando fora do formato ({message}). Exemplo: python3 -m orbita.perguntar --agua 5 "
                         "--solo 4 --renda 2 --erosao 3 --terra media")


def main(argv=None):
    leitor = _Argumentos(prog="python3 -m orbita.perguntar", description="Pergunta ao motor do Órbita Rural.")
    for nome in ("agua", "solo", "renda", "erosao"):
        leitor.add_argument(f"--{nome}", type=int, help=f"a nota da prioridade {nome}, de 1 a 5")
    leitor.add_argument("--terra", default="media", help="quanta água a terra segura: pouca, media ou muita")
    leitor.add_argument("--cidade", default="rio_verde", help="por enquanto, só rio_verde")
    leitor.add_argument("--json", action="store_true", help="mostra a estrutura inteira em vez do texto")
    try:
        a = leitor.parse_args(argv)
        notas = {nome: getattr(a, nome) for nome in ("agua", "solo", "renda", "erosao") if getattr(a, nome) is not None}
        resposta = motor.responder({"cidade_id": a.cidade, "rotacao_atual": ["soja", "milho", "pousio"],
                                    "prioridades": notas, "terra": a.terra})
    except ValueError as erro:
        print(f"Não deu para responder. {erro}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(resposta, ensure_ascii=False, indent=2))
    else:
        print(explicacao.texto(resposta))
    return 0


if __name__ == "__main__":
    sys.exit(main())
