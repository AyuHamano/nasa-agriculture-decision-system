# Gerado com IA (Claude)
"""O comando de perguntar ao motor, sem site.

De dentro de backend/:
    python3 -m orbita.perguntar --terra media                                      (em português)
    python3 -m orbita.perguntar --terra media --plantio 2026-11-20 --preocupacao agua --json   (a estrutura)
    python3 -m orbita.perguntar --agua 5 --solo 4 --renda 2 --erosao 3 --terra media          (com as notas, como antes)
As notas de 1 a 5 são opcionais (ou vêm as 4, ou nenhuma). --plantio é a data do plantio da soja (ano-mês-dia) e
--preocupacao é o que mais preocupa (agua, calor ou terra): só muda a ordem e o destaque.
Para comparar: --chuva imerg|chirps|era5|power (a fonte da chuva; o padrão é imerg, o satélite da NASA) e
--regra rendimento|chuva (como se escolhe o pior ano; o padrão é rendimento, a pior colheita no IBGE).
"""
import argparse
import json
import sys

from orbita import conferencia, explicacao, motor


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
    leitor.add_argument("--chuva", default=None, help="a fonte da chuva: imerg (padrão), chirps, era5 ou power")
    leitor.add_argument("--regra", default=None, help="o pior ano: rendimento (padrão, o IBGE) ou chuva")
    leitor.add_argument("--plantio", default=None, help="a data do plantio da soja, ano-mês-dia (2026-11-05)")
    leitor.add_argument("--preocupacao", default=None, help="o que mais preocupa: agua, calor ou terra")
    leitor.add_argument("--json", action="store_true", help="mostra a estrutura inteira em vez do texto")
    try:
        a = leitor.parse_args(argv)
        notas = {nome: getattr(a, nome) for nome in ("agua", "solo", "renda", "erosao") if getattr(a, nome) is not None}
        resposta = motor.responder({"cidade_id": a.cidade, "rotacao_atual": ["soja", "milho", "pousio"],
                                    "prioridades": notas or None, "terra": a.terra, "chuva": a.chuva,
                                    "regra": a.regra, "plantio_da_soja": a.plantio, "preocupacao": a.preocupacao})
    except ValueError as erro:
        print(f"Não deu para responder. {erro}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(resposta, ensure_ascii=False, indent=2))
    else:
        texto = explicacao.texto(resposta)
        print(texto)
        sobras = conferencia.conferir_texto(texto, resposta)
        if sobras:
            print("Conferência do texto: estes números do texto não estão na conta: " + ", ".join(sobras),
                  file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
