#!/usr/bin/env python3
# Gerado com IA (Claude). Órbita Rural (NASA Space Apps 2026).
"""Acrescenta à temperatura guardada da NASA POWER os dias do fim que ainda estavam sem dado (-999).

A NASA POWER solta a temperatura com uns 3 dias de atraso: o arquivo guardado (`resposta.json`) traz os últimos dias
como -999. Este programa pergunta de novo só os últimos dias, na mesma consulta de sempre (API diária, comunidade AG,
dia local, PRECTOTCORR, T2M_MAX e T2M_MIN), e troca o -999 pelo valor só nos dias em que os três já chegaram. Dia
que já tinha valor não muda; dia que continua sem dado continua -999 (nunca vira zero). O endereço, a hora e os dias
acrescentados ficam em `acrescimos.json`, ao lado do arquivo. Só a biblioteca padrão.

Como rodar, da raiz do repositório:  python3 -I data/orbita/nasa-power/acrescentar_dias.py
"""
import datetime
import json
import pathlib
import re
import sys
import urllib.request

AQUI = pathlib.Path(__file__).resolve().parent
CIDADES = {"rio_verde": (AQUI, -17.79, -50.92),
           "jatai": (AQUI.parent / "cidades" / "jatai" / "nasa-power", -17.88, -51.71),
           "silvania": (AQUI.parent / "cidades" / "silvania" / "nasa-power", -16.66, -48.61)}
PARAMETROS = ("PRECTOTCORR", "T2M_MAX", "T2M_MIN")
SEM_DADO = -999.0
DIAS_PARA_TRAS = 12


def trocar(texto, parametro, dia, valor):
    """Troca, no texto do arquivo, o -999 do dia dentro do bloco do parâmetro. Devolve (o texto novo, se trocou)."""
    comeco = texto.index(f'"{parametro}"', texto.index('"parameter"'))
    achado = re.compile(rf'("{dia}":\s*)-999(?:\.0)?(?![\d.])').search(texto, comeco)
    fim_do_bloco = texto.index("}", comeco)
    if achado is None or achado.start() > fim_do_bloco:
        return texto, False
    return texto[:achado.start()] + achado.group(1) + repr(float(valor)) + texto[achado.end():], True


def main():
    hoje = datetime.date.today()
    for cidade, (pasta, latitude, longitude) in CIDADES.items():
        arquivo = pasta / "resposta.json"
        texto = arquivo.read_text(encoding="utf-8")
        guardado = json.loads(texto)["properties"]["parameter"]
        endereco = ("https://power.larc.nasa.gov/api/temporal/daily/point?parameters=" + ",".join(PARAMETROS)
                    + f"&community=AG&longitude={longitude}&latitude={latitude}"
                    + f"&start={hoje - datetime.timedelta(days=DIAS_PARA_TRAS):%Y%m%d}&end={hoje:%Y%m%d}"
                    + "&format=JSON&time-standard=LST")
        hora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with urllib.request.urlopen(urllib.request.Request(endereco, headers={"User-Agent": "orbita-rural"}),
                                    timeout=60) as resposta:
            novo = json.loads(resposta.read().decode("utf-8"))["properties"]["parameter"]
        acrescentados = []
        for dia in sorted(novo["T2M_MAX"]):
            chegou = all(novo[p].get(dia, SEM_DADO) != SEM_DADO for p in PARAMETROS)
            faltava = all(guardado[p].get(dia) == SEM_DADO for p in PARAMETROS)
            if not (chegou and faltava):
                continue
            for parametro in PARAMETROS:
                texto, trocou = trocar(texto, parametro, dia, novo[parametro][dia])
                if not trocou:
                    raise SystemExit(f"{cidade}: não achei o -999 de {parametro} em {dia}; nada foi gravado.")
            acrescentados.append({"dia": f"{dia[:4]}-{dia[4:6]}-{dia[6:]}",
                                  **{parametro: novo[parametro][dia] for parametro in PARAMETROS}})
        json.loads(texto)                                   # o arquivo continua um JSON válido
        if acrescentados:
            arquivo.write_text(texto, encoding="utf-8")
        registro = pasta / "acrescimos.json"
        ficha = json.loads(registro.read_text(encoding="utf-8")) if registro.exists() else {
            "o_que_e": "Os dias do fim da série que foram acrescentados depois do primeiro download (o -999 trocado "
                       "pelo valor que a NASA POWER soltou depois). O programa é data/orbita/nasa-power/"
                       "acrescentar_dias.py.", "rodadas": []}
        ficha["rodadas"].append({"endereco": endereco, "consultado_em_utc": hora, "dias_acrescentados": acrescentados})
        registro.write_text(json.dumps(ficha, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ultimo = max(d for d in guardado["T2M_MAX"] if guardado["T2M_MAX"][d] != SEM_DADO)
        print(f"{cidade}: a temperatura guardada ia até {ultimo}; acrescentados "
              f"{[a['dia'] for a in acrescentados] or 'nenhum dia (a NASA POWER ainda não soltou mais)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
