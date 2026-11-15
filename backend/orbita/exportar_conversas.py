# Gerado com IA (Claude)
"""Grava as conversas de exemplo que a tela lê quando a API não está ligada: uma de cada momento do produtor.

De dentro de backend/:
    python3 -m orbita.exportar_conversas <pasta>            (com a chave no ambiente: a IA de verdade escreve)
    python3 -m orbita.exportar_conversas <pasta> --sem-ia   (sem chave: saem as frases prontas do motor)

Grava na pasta (cria, se não existir):
    conversas.js     window.ORBITA_CONVERSAS = {"gerado_em": ..., "gerado_por": ..., "conversas": [...]};
    conversas.json   o mesmo objeto

Cada conversa: {"id", "momento" (antes, durante ou depois), "titulo", "texto_de" ("ia" ou "frases_prontas"),
"replay" (os dias e os marcos de uma safra, ou null), "passos": [{"de": "produtor", "texto": ...},
{"de": "agente", "saida": a resposta da rota POST /agente}]}. O formato está no mapa do projeto, seção 7.5.

As conversas: antes de plantar (plantei a soja tarde: milho ou sorgo?), durante (o replay da pior safra, dia a
dia, e "como está hoje"), depois (o que a terra mostrou; o registro de uma safra) e uma pergunta sem conta (pragas
e adubo), que sai com o aviso de conhecimento geral.

Os cuidados: cada texto do agente é conferido de novo contra a conta ao gravar (`agente.conferir_saida`); se
sobrar número, nada é gravado. A chave da IA não entra em arquivo nenhum (e é procurada no que vai ser gravado).
Sem chave, o roteiro de cada fala diz que ferramentas consultar, e o agente responde com as frases prontas: o
arquivo sai completo, só que sem o texto da IA. Com a IA, a conversa que não chegar ao seu momento (ou o replay
que não vier) é gravada de novo pelo roteiro, e isso é dito.
"""
import datetime
import json
import os
import sys
from pathlib import Path

from orbita import agente, ferramentas, modelo
from orbita.modelo import chamada, fala

COMANDO = "python3 -m orbita.exportar_conversas <pasta>"
RIO_VERDE = dict(cidade_id="rio_verde", rotacao_atual="soja_milho_pousio", terra="media", preocupacao="agua")
FICHA_DE_RIO_VERDE = ("Minha lavoura é em Rio Verde. Planto soja e depois milho safrinha, e a terra fica parada na "
                      "seca. A terra é de textura média. O que mais me preocupa é a falta de água.")
ENSAIO = chamada("ensaio_da_rotacao")

# Cada fala do produtor e o roteiro dela: as ferramentas que o modelo de mentira consulta quando não há IA.
CONVERSAS = (
    {"id": "antes-plantei-tarde", "momento": "antes", "titulo": "Plantei a soja tarde: ainda vale o milho ou vou de sorgo?",
     "falas": (
         ("Plantei a soja tarde, dia 10 de novembro, em Jataí. Planto soja e milho safrinha, depois a terra fica "
          "parada. A terra é de textura média. Meu medo é faltar água. Ainda vale o milho ou vou de sorgo?",
          [chamada("anotar_na_ficha", cidade_id="jatai", rotacao_atual="soja_milho_pousio", terra="media",
                   plantio_da_soja="{ano}-11-10", preocupacao="agua")]),
         ("sim", [ENSAIO]),
         ("E a braquiária, o que muda para a minha terra?", [ENSAIO]))},
    {"id": "replay-2015-16", "momento": "durante", "titulo": "Como foi a pior safra aqui, dia a dia?",
     "falas": (
         (FICHA_DE_RIO_VERDE, [chamada("anotar_na_ficha", **RIO_VERDE)]),
         ("sim", [ENSAIO]),
         ("Como foi a pior safra aqui, dia a dia?", [chamada("ensaio_da_rotacao", safra="pior_ano")]),
         ("E como está a minha lavoura hoje?", [chamada("clima_do_lugar", hoje=True)]))},
    {"id": "depois-o-que-a-terra-mostrou", "momento": "depois", "titulo": "Depois da colheita: o que a terra mostrou?",
     "falas": (
         (FICHA_DE_RIO_VERDE + " O que a terra mostrou depois da colheita?", [chamada("anotar_na_ficha", **RIO_VERDE)]),
         ("sim", [chamada("verde_do_satelite")]),
         ("E na safra 2015-16, como ficou o registro?", [chamada("verde_do_satelite", safra="2015-16")]))},
    {"id": "sem-conta-pragas-e-adubo", "momento": "antes", "titulo": "E as pragas? E o adubo? (o que a conta não mede)",
     "falas": (
         (FICHA_DE_RIO_VERDE, [chamada("anotar_na_ficha", **RIO_VERDE)]),
         ("sim", [ENSAIO]),
         ("Quais pragas atacam mais o milho safrinha? E quanto de adubo eu ponho?", []))},
)


def _roteiro(chamadas, hoje):
    """As chamadas do roteiro, com o ano de hoje onde o roteiro pede."""
    return [dict(c, argumentos={chave: valor.replace("{ano}", str(hoje.year)) if isinstance(valor, str) else valor
                                for chave, valor in c["argumentos"].items()}) for c in chamadas]


def _conversar(conversa, ia, hoje):
    """Roda uma conversa inteira. `ia` None = o modelo de mentira, pelo roteiro (saem as frases prontas)."""
    estado, passos, replay = None, [], None
    for texto, chamadas in conversa["falas"]:
        quem_responde = ia or modelo.ModeloDeMentira([fala("", *_roteiro(chamadas, hoje))] if chamadas else [])
        estado, saida = agente.passo(estado, texto, quem_responde, hoje)
        sobras = agente.conferir_saida(saida, hoje)
        if sobras:
            raise ValueError(f'A conversa "{conversa["id"]}" tem número fora da conta ({", ".join(sobras)}): não '
                             "foi gravada.")
        replay = saida["replay"] or replay
        passos += [{"de": "produtor", "texto": texto}, {"de": "agente", "saida": agente.resposta_da_rota(estado, saida)}]
    saidas = [p["saida"] for p in passos if p["de"] == "agente"]
    return {"id": conversa["id"], "momento": conversa["momento"], "titulo": conversa["titulo"],
            "texto_de": "ia" if any(s["texto_de"] == "ia" for s in saidas) else "frases_prontas",
            "replay": replay, "passos": passos}


def _serve(conversa, gravada):
    """A conversa gravada chegou aonde devia: a comparação saiu, o momento aconteceu e o replay veio (se é o caso)."""
    saidas = [p["saida"] for p in gravada["passos"] if p["de"] == "agente"]
    return (any(s["comparacao"] for s in saidas) and any(s["momento"] == conversa["momento"] and s["comparacao"]
                                                         for s in saidas)
            and (not conversa["id"].startswith("replay-") or bool(gravada["replay"] and gravada["replay"].get("dias"))))


def conversar(ia=None, hoje=None):
    """As conversas de exemplo, prontas para gravar: (a lista das conversas, os avisos do que saiu pelo roteiro)."""
    hoje = hoje or datetime.date.today()
    conversas, avisos = [], []
    for conversa in CONVERSAS:
        gravada = _conversar(conversa, ia, hoje)
        if ia is not None and not _serve(conversa, gravada):
            avisos.append(f'A conversa "{conversa["id"]}" não chegou ao seu momento com a IA: foi gravada pelo '
                          "roteiro, com as frases prontas.")
            gravada = _conversar(conversa, None, hoje)
        if not _serve(conversa, gravada):
            raise ValueError(f'A conversa "{conversa["id"]}" não chegou ao seu momento nem pelo roteiro: confira o '
                             "motor (a comparação, o replay) antes de gravar.")
        conversas.append(gravada)
    return conversas, avisos


def _gravar(arquivo, texto):
    """Grava num arquivo ao lado e troca de uma vez: a tela nunca lê um arquivo pela metade."""
    provisorio = arquivo.with_name(arquivo.name + ".gravando")
    provisorio.write_text(texto, encoding="utf-8")
    os.replace(provisorio, arquivo)


def exportar(pasta, ia=None, hoje=None, agora=None):
    """Grava `conversas.js` e `conversas.json` na pasta. `ia` None = sem IA (as frases prontas). Devolve um resumo."""
    pasta = Path(pasta)
    conversas, avisos = conversar(ia, hoje)
    agora = agora or datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    com_ia = any(c["texto_de"] == "ia" for c in conversas)
    objeto = {"gerado_em": agora, "gerado_por": COMANDO + " (Gerado com IA (Claude))",
              "modelo": getattr(ia, "nome", None) if com_ia else None,
              "uso_de_ia": ("O texto do agente foi escrito por um modelo de linguagem e conferido contra a conta; "
                            "os números vêm do motor." if com_ia else
                            "Sem IA: o texto do agente são frases prontas, feitas só com as frases do motor."),
              "conversas": conversas}
    texto = json.dumps(objeto, ensure_ascii=False, separators=(",", ":"))
    segredo = (os.environ.get(modelo.VARIAVEL_DA_CHAVE) or "").strip()
    if segredo and segredo in texto:
        raise ValueError("A chave da IA apareceu numa conversa: nada foi gravado.")
    texto = texto.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")     # quebras que o JavaScript antigo recusa
    pasta.mkdir(parents=True, exist_ok=True)
    _gravar(pasta / "conversas.js",
            "/* Gerado com IA (Claude) */\n"
            f"/* As conversas de exemplo do agente do Órbita Rural, gravadas em {agora} por\n"
            f"   {COMANDO}. {objeto['uso_de_ia']}\n"
            "   Não editar à mão: cada texto foi conferido contra a conta ao gravar. */\n"
            f"window.ORBITA_CONVERSAS = {texto};\n")
    _gravar(pasta / "conversas.json", json.dumps(objeto, ensure_ascii=False, indent=1) + "\n")
    saidas = [p["saida"] for c in conversas for p in c["passos"] if p["de"] == "agente"]
    return {"arquivos": (pasta / "conversas.js", pasta / "conversas.json"), "conversas": len(conversas),
            "passos_do_agente": len(saidas), "texto_da_ia": sum(1 for s in saidas if s["texto_de"] == "ia"),
            "barrados_pela_conferencia": sum(1 for s in saidas if not s["conferencia"]["passou"]),
            "avisos": avisos}


def main(argv=None):
    argumentos = sys.argv[1:] if argv is None else list(argv)
    sem_ia = "--sem-ia" in argumentos
    argumentos = [a for a in argumentos if a != "--sem-ia"]
    if len(argumentos) != 1 or argumentos[0].startswith("-"):
        print(f"Diga a pasta onde gravar. Exemplo: {COMANDO.replace('<pasta>', '../frontend/orbita/dados')} "
              "(com --sem-ia, saem as frases prontas, sem chave).", file=sys.stderr)
        return 2
    ia = None
    if not sem_ia:
        try:
            ia = modelo.do_ambiente()
        except modelo.SemChave:
            print(f"Sem chave no ambiente ({modelo.VARIAVEL_DA_CHAVE}): as conversas saem com as frases prontas, "
                  "sem o texto da IA.", file=sys.stderr)
    try:
        resumo = exportar(argumentos[0], ia)
    except (OSError, ValueError, modelo.ErroDoModelo, ferramentas.ContaIndisponivel) as erro:
        print(f"Não deu para gravar as conversas em {argumentos[0]}: {erro}", file=sys.stderr)
        return 1
    js, dados = resumo["arquivos"]
    print(f"Gravado: {js} ({js.stat().st_size} bytes) e {dados} ({dados.stat().st_size} bytes).")
    print(f"{resumo['conversas']} conversas, {resumo['passos_do_agente']} falas do agente: {resumo['texto_da_ia']} "
          f"com o texto da IA, {resumo['barrados_pela_conferencia']} barradas pela conferência dos números.")
    for aviso in resumo["avisos"]:
        print("Aviso: " + aviso)
    if ia is not None:
        print(f"Modelo: {ia.nome}. Gasto: {ia.uso['pedidos']} pedidos, {ia.uso['custo_usd']:.4f} dólares.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
