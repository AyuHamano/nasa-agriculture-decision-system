# Gerado com IA (Claude)
"""A explicação em português simples: frases prontas, preenchidas só com os números da resposta do motor.

Não há IA aqui (não há chave ligada). Todo número que aparece no texto vem de `motor.responder`.
"""

import datetime

QUEM = {"atual": "a rotação de hoje se saiu melhor", "alternativa": "a alternativa se saiu melhor",
        "empate": "empate", "não medido": "não medido"}
PELA_FAIXA = {"alternativa_melhor": "a alternativa se saiu melhor", "alternativa_pior": "a alternativa se saiu pior",
              "empate": "empate", "depende_da_hipotese": "depende da hipótese"}


def _quem(item):
    """Quem se saiu melhor, em palavras; na água vale o veredito pela faixa."""
    return PELA_FAIXA.get(item.get("veredito_pela_faixa"), QUEM[item["melhor"]])


def _lista(safras):
    return ", ".join(safras) or "nenhuma"


def _sede_forte(r):
    """As linhas da sede forte: o nível, de onde saiu, quantas safras em cada rotação e o aviso."""
    sede = r["sede_forte"]
    hoje = r["rotacoes"]["atual"]["safras_com_sede_forte"]
    alternativa = r["rotacoes"]["alternativa"]["safras_com_sede_forte"]
    if sede["nivel_pct"] is None:
        return [f"   Sede forte: {sede['aviso']}"]
    total = len(r["rotacoes"]["atual"]["safras"])
    faixa = alternativa["faixa"]
    quantas = (f"{faixa['menor']}" if faixa["menor"] == faixa["maior"]
               else f"de {faixa['menor']} a {faixa['maior']} (conforme a disputa)")
    linhas = [f"   Sede forte (falta do milho de {n(sede['nivel_pct'])}% ou mais do que ele pediu): {hoje['quantas']} "
              f"de {total} safras na rotação de hoje ({_lista(hoje['quais'])}) e {quantas} na alternativa "
              f"({_lista(alternativa['quais'])} na hipótese do meio).",
              f"   De onde sai o nível: é a menor falta do milho entre as safras de quebra, as de "
              f"{sede['safra_de_quebra']}: {_lista(sede['safras_de_quebra'])} (abaixo de {n(sede['limite_kg_ha'])} "
              f"kg/ha), na conta da rotação de hoje com a terra média e a chuva padrão."]
    for nome, forte in (("rotação de hoje", hoje), ("alternativa (hipótese do meio)", alternativa)):
        if forte["alarmes_falsos"] or forte["quebras_abaixo_do_nivel"]:
            linhas.append(f"   Na {nome}: alarme falso (sede forte na conta, sem quebra no IBGE): "
                          f"{_lista(forte['alarmes_falsos'])}; quebra no IBGE que ficou abaixo do nível: "
                          f"{_lista(forte['quebras_abaixo_do_nivel'])}.")
    aviso = sede["aviso"]
    perto = sede.get("maior_falta_sem_quebra")
    if perto:
        aviso += (f" Por exemplo: a safra {perto['safra']} teve falta de {n(perto['falta_do_milho_pct'])}% na conta "
                  f"de referência, perto do nível, e colheu {perto['rendimento_kg_ha']} kg/ha, sem quebra.")
    return linhas + [f"   {aviso}"]


def n(numero):
    """Número em português: inteiro sem casa, o resto com uma casa e vírgula."""
    if isinstance(numero, int):
        return str(numero)
    return f"{numero:.1f}".replace(".", ",")


def data_br(dia):
    """A data no jeito brasileiro, para as frases que o produtor lê: "2026-11-11" (ou a data) vira "11/11/2026"."""
    if isinstance(dia, str):
        dia = datetime.date.fromisoformat(dia[:10])
    return f"{dia.day:02d}/{dia.month:02d}/{dia.year}"


def _prioridade(p, r):
    hoje, alternativa = r["rotacoes"]["atual"], r["rotacoes"]["alternativa"]
    seco = r["comparacao"]["pior_ano"]
    rotulo = "No pior ano" if r["regra_dos_anos"]["regra"] == "rendimento" else "No ano mais seco"
    normal = r["comparacao"]["ano_normal"]
    if rotulo == "No pior ano" and pior_contra_normal(hoje["safras"][seco]["total"]["falta_mm"],
                                                      hoje["safras"][normal]["total"]["falta_mm"]) != "maior":
        rotulo = "No ano da pior colheita da região"    # a conta não deu nele mais falta de água que no ano normal
    linhas = [f"{p['nome']}: {_quem(p)}."]      # as notas de 1 a 5 saíram (decisão do dono, 2026-11-15)
    if p["id"] == "agua":
        a, faixa = hoje["safras"][seco]["total"], alternativa["faixa"][seco]["falta_total_mm"]
        meio = alternativa["safras"][seco]["total"]
        linhas.append(f"   {r['comparacao']['agua']['pela_faixa']['frase']}")
        linhas.append(f"   {rotulo} (safra {seco}), faltaram {n(a['falta_mm'])} mm de água para a soja e o milho "
                      f"na rotação de hoje; na alternativa, de {n(faixa['menor'])} a {n(faixa['maior'])} mm, com "
                      f"{n(meio['falta_mm'])} mm na hipótese do meio (falta de água = o que a planta pediu menos o "
                      "que conseguiu beber). A alternativa vai em faixa porque não se sabe quanto o capim disputa "
                      "água com o milho.")
        linhas += _sede_forte(r)
    elif p["id"] in ("solo", "erosao"):
        a, b = hoje["sem_planta_viva"], alternativa["sem_planta_viva"]
        outro = "da erosão" if p["id"] == "solo" else "do solo"
        linhas.append(f"   Pelo calendário, a terra fica {a['dias_sem_planta_viva']} dias por ano sem planta viva "
                      f"({n(a['meses_sem_planta_viva'])} meses) na rotação de hoje e {b['dias_sem_planta_viva']} dias "
                      f"({n(b['meses_sem_planta_viva'])} meses) na alternativa. É o mesmo número {outro}: o motor "
                      "não mede a terra perdida, só o tempo sem planta viva.")
    else:
        linhas.append("   O motor não tem preço, custo nem produtividade: a renda fica para o agrônomo e para a "
                      "conta do produtor.")
    return linhas


def _linha_da_safra(safra, r):
    partes = [f"  {safra} | chuva {n(r['regra_dos_anos']['chuva_por_safra_mm'][safra])} mm"]
    for rotulo, chave in (("hoje", "atual"), ("alternativa", "alternativa")):
        s = r["rotacoes"][chave]["safras"][safra]
        partes.append(f"{rotulo}: soja {n(s['soja']['falta_mm'])} mm, milho {n(s['milho']['falta_mm'])} mm "
                      f"({n(s['milho']['falta_relativa_pct'])}%), {s['total']['dias_de_sede']} dias de sede")
    faixa = r["rotacoes"]["alternativa"]["faixa"][safra]
    partes.append(f"faixa do milho na alternativa: de {n(faixa['falta_do_milho_mm']['menor'])} a "
                  f"{n(faixa['falta_do_milho_mm']['maior'])} mm ({n(faixa['falta_do_milho_pct']['menor'])}% a "
                  f"{n(faixa['falta_do_milho_pct']['maior'])}%)")
    return " | ".join(partes)


def _ano(rotulo, safra, r):
    linhas = [f"{rotulo} (safra {safra}, {n(r['regra_dos_anos']['chuva_por_safra_mm'][safra])} mm de chuva na janela):"]
    for nome, chave in (("rotação de hoje", "atual"), ("alternativa", "alternativa")):
        s = r["rotacoes"][chave]["safras"][safra]
        linha = (f"  - {nome}: falta de água de {n(s['total']['falta_mm'])} mm (soja {n(s['soja']['falta_mm'])}, milho "
                 f"{n(s['milho']['falta_mm'])}, que é {n(s['milho']['falta_relativa_pct'])}% do que o milho pediu) e "
                 f"{s['total']['dias_de_sede']} dias de sede (soja {s['soja']['dias_de_sede']}, milho "
                 f"{s['milho']['dias_de_sede']}); a terra tinha "
                 f"{n(s['agua_na_terra_no_plantio_da_soja_mm'])} mm de água no plantio da soja")
        if "braquiaria" in s:
            linha += (f"; a braquiária bebeu {n(s['braquiaria']['bebido_junto_com_o_milho_mm'])} mm junto com o "
                      f"milho e {n(s['braquiaria']['bebido_mm'])} mm depois dele (números da hipótese do meio)")
        linhas.append(linha + ".")
    faixa = r["rotacoes"]["alternativa"]["faixa"][safra]
    linhas.append(f"  - a alternativa em faixa (de sem disputa a disputa alta): falta de água de "
                  f"{n(faixa['falta_total_mm']['menor'])} a {n(faixa['falta_total_mm']['maior'])} mm; a do milho, de "
                  f"{n(faixa['falta_do_milho_mm']['menor'])} a {n(faixa['falta_do_milho_mm']['maior'])} mm "
                  f"({n(faixa['falta_do_milho_pct']['menor'])}% a {n(faixa['falta_do_milho_pct']['maior'])}%).")
    return linhas


def _palha_e_disputa(r):
    hoje, alternativa = r["rotacoes"]["atual"]["palha"], r["rotacoes"]["alternativa"]["palha"]
    cenarios = r["rotacoes"]["alternativa"]["disputa_com_o_milho"]["cenarios"]
    return [f"A palha entra nas duas rotações ({hoje['regra']}): {hoje['de_que']} cobre {n(hoje['cobertura_pct'])}% da "
            f"terra na rotação de hoje e tira {n(hoje['evaporacao_a_menos_pct'])}% da evaporação; "
            f"{alternativa['de_que']} cobre {n(alternativa['cobertura_pct'])}% na alternativa e tira "
            f"{n(alternativa['evaporacao_a_menos_pct'])}%. Vale {hoje['onde_vale']}. As duas coberturas são "
            f"{hoje['etiqueta_da_cobertura']}.",
            "A disputa do capim com o milho é hipótese, e por isso a alternativa sai em faixa: sem disputa (o capim "
            f"não tira água do milho), meio (o conjunto pede {n(cenarios['meio']['pedido_a_mais_pct'])}% a mais de "
            f"água que o milho sozinho) e alta ({n(cenarios['alta']['pedido_a_mais_pct'])}% a mais). Os números da "
            "alternativa fora da faixa são os da hipótese do meio."]


def _ndvi(r):
    ndvi = r["ndvi"]
    if not ndvi.get("disponivel"):
        return ["O NDVI (O VERDE VISTO PELO SATÉLITE)", ndvi.get("aviso", "Não disponível.")]
    return ["O NDVI (O VERDE VISTO PELO SATÉLITE): PROVA SÓ DA ROTAÇÃO DE HOJE"] + list(ndvi.get("frases", []))


def _mm(valor):
    """Um número ou uma faixa {"de", "ate"}, em português: "183,9" ou "de 318,0 a 336,3"."""
    if isinstance(valor, dict):
        return n(valor["de"]) if valor["de"] == valor["ate"] else f"de {n(valor['de'])} a {n(valor['ate'])}"
    return n(valor)


def _dias(valor):
    """Dias, um número ou uma faixa: "73" ou "76 a 77"."""
    if isinstance(valor, dict):
        return n(valor["de"]) if valor["de"] == valor["ate"] else f"{n(valor['de'])} a {n(valor['ate'])}"
    return n(valor)


def _grau(valor):
    """A temperatura do limite: "40" se for número redondo, "33,5" se não for."""
    return str(int(valor)) if float(valor) == int(valor) else n(valor)


def _e(partes):
    """Junta com vírgulas e "e": "a, b e c"."""
    partes = list(partes)
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " e " + partes[-1]


def _pontas(valor):
    return (valor["de"], valor["ate"]) if isinstance(valor, dict) else (valor, valor)


def pior_contra_normal(pior, normal):
    """A falta de água do pior ano contra a do ano normal, pelo que a conta mostra (números ou faixas {"de", "ate"}).

    O pior ano é escolhido pela colheita da região (ou pela chuva), não pela falta de água da conta: a falta dele
    pode sair "maior", "menor" ou "igual" à do ano normal; nas faixas, "cruza" quando uma ponta fica acima e a outra
    abaixo.
    """
    (p1, p2), (n1, n2) = _pontas(pior), _pontas(normal)
    if (p1, p2) == (n1, n2):
        return "igual"
    if p1 >= n1 and p2 >= n2:
        return "maior"
    if p1 <= n1 and p2 <= n2:
        return "menor"
    return "cruza"


def _criterio_do_pior_ano(r):
    """Como o pior ano foi escolhido, em palavras: (o que ele é, o nome dele para o começo das frases)."""
    if (r.get("regra_dos_anos") or {}).get("regra") == "chuva":
        return "o de menor chuva de fevereiro a junho", "do ano de menor chuva"
    return "o da pior colheita da região", "do ano da pior colheita da região"


NOMES_DAS_CULTURAS = {"soja": "soja", "milho": "milho", "sorgo": "sorgo"}
RISCOS_PROPRIOS = {
    "soja_milho_braquiaria": "A braquiária bebe água junto com o milho e depois dele: a terra pode chegar mais seca "
                             "ao plantio da soja.",
}
# O que falta saber de cada rotação, frase por frase (a primeira é a principal; juntas, dão o texto de sempre).
FALTA_SABER = {
    "soja_milho_pousio": ("A conta não mede renda, preço, custo nem produtividade, e a palha entra só pelo lado da "
                          "evaporação.", "O quanto de terra a palha do milho cobre é hipótese."),
    "soja_milho_braquiaria": ("Quanto o capim disputa água com o milho não foi medido: por isso os números desta "
                              "rotação saem em faixa.", "O satélite não prova esta rotação, e a conta não mede renda "
                              "nem o custo da semente do capim."),
    "soja_sorgo_pousio": ("As fases e o ciclo do sorgo vêm da tabela geral da FAO (o órgão da ONU para a "
                          "agricultura), que não tem linha de 2ª safra em "
                          "Goiás, e a raiz do sorgo vale igual à do milho.", "A conta não mede renda nem o preço do "
                          "sorgo contra o do milho, e o satélite não prova esta rotação."),
}
FALTA_SABER_DE_COSTUME = ("A conta não mede renda, preço nem produtividade.",)
SEM_RISCO_NA_CONTA = ("Na conta, esta rotação não ficou atrás das outras em água, calor nem terra coberta.",
                      "O risco que a conta não vê (praga, preço, data de plantio) continua valendo.")
PERNA_DA_PREOCUPACAO = {"agua": "agua", "calor": "calor", "terra": "terra_coberta"}


def frase_principal(frases, preocupacao=None):
    """A UMA frase que o produtor lê, tirada da lista de sempre (a regra do alinhamento, 2026-11-15).

    `frases`: a lista na ordem de sempre, cada uma como (a perna dela ou None, o texto). Vale a frase da perna que
    preocupa o produtor (água, calor ou terra), se ele disse qual e a rotação tem frase nessa perna; senão, a
    primeira da ordem de sempre. O texto inteiro (todas as frases) continua no campo `_detalhe`.
    """
    perna = PERNA_DA_PREOCUPACAO.get(preocupacao)
    return next((texto for de, texto in frases if perna and de == perna), frases[0][1])
PERNAS = (("agua", "Na água do pior ano", "mm de falta", "mm"),
          ("calor", "No calor do pior ano", "dias de calor forte", "dias"),
          ("terra_coberta", "Na terra coberta", "dias seguidos sem planta viva", "dias"))


def _valor_da_perna(item, perna):
    return {"agua": item["agua"]["falta_no_pior_ano_mm"], "calor": item["calor"]["dias_de_calor_forte_no_pior_ano"],
            "terra_coberta": item["terra_coberta"]["dias_sem_planta_viva"]}[perna]


# A frase de risco que a tela do produtor mostra (`risco_curto`): o nome de cada caminho em palavras simples.
NOMES_SIMPLES = {"soja_milho_pousio": "milho", "soja_milho_braquiaria": "capim", "soja_sorgo_pousio": "sorgo"}
RISCOS_PROPRIOS_CURTOS = {
    "soja_milho_braquiaria": "O capim também bebe água: a terra pode chegar mais seca ao plantio da soja.",
}
SEM_RISCO_CURTO = "Na conta, este caminho não ficou atrás dos outros em água, calor nem terra coberta."


def _um_numero(item, perna, r):
    """O número só que a tabela da tela mostra. Na água em faixa (o milho com capim), é o do meio da disputa do
    capim com o milho, que a conta também dá; sem ele, fica a faixa."""
    valor = _valor_da_perna(item, perna)
    if perna == "agua" and isinstance(valor, dict):
        cenarios = ((r.get("comparacao") or {}).get("agua") or {}).get("pela_faixa") or {}
        meio = ((cenarios.get("por_cenario") or {}).get("meio") or {}).get("falta_mm")
        if isinstance(meio, (int, float)) and not isinstance(meio, bool) and valor["de"] <= meio <= valor["ate"]:
            return meio
    return valor


def _nome_simples(item, outro):
    """O outro caminho em uma palavra: "sorgo", "capim", "milho" (para quem planta com capim, "milho sem capim")."""
    nome = NOMES_SIMPLES.get(outro["id"], outro["apelido"])
    return "milho sem capim" if (item["id"], outro["id"]) == ("soja_milho_braquiaria", "soja_milho_pousio") else nome


def frase_curta_do_risco(perna, meu, com_quem, do_outro):
    """O risco de um caminho em duas frases curtas, para o produtor: o número dele e o do outro caminho.

    `meu` e `do_outro` são números da conta (ou a faixa, se a conta não deu o do meio); `com_quem` é o outro caminho
    em uma palavra. A água e o calor são os do ano ruim; os dias de terra sem planta vêm do calendário.
    """
    if perna == "agua":
        return f"Num ano ruim, faltam {_mm(meu)} mm de água. Com {com_quem} faltariam {_mm(do_outro)} mm."
    seria = "não teria nenhum" if do_outro == 0 else ("seria 1" if do_outro == 1 else f"seriam {_dias(do_outro)}")
    if perna == "calor":
        tem = "é 1 dia" if meu == 1 else f"são {_dias(meu)} dias"
        return f"Num ano ruim, {tem} de calor forte na fase crítica. Com {com_quem} {seria}."
    fica = "1 dia" if meu == 1 else f"{_dias(meu)} dias seguidos"
    return f"A terra fica {fica} sem planta viva. Com {com_quem} {seria}."


def _frase_do_calor(item):
    """Os dias de calor forte da rotação no pior ano, cultura por cultura, cada uma com o seu limite."""
    partes = [f"{NOMES_DAS_CULTURAS[c]}, {d['dias']} dias acima de {_grau(d['limite_c'])} °C"
              for c, d in item["calor"]["por_cultura"].items()]
    if not partes:
        return "Sem temperatura guardada para contar o calor."
    return (f"Na fase crítica das culturas, {item['calor']['dias_de_calor_forte_no_pior_ano']} dias de calor forte "
            f"no pior ano ({'; '.join(partes)}).")


def frases_da_rotacao(item, itens, r):
    """As quatro frases prontas de uma rotação da comparação: evidência, benefício, risco e o que falta saber.

    Só entram números da conta (os do próprio item e os das outras rotações, para comparar). O benefício e o risco
    saem da posição da rotação contra as outras em cada perna (água, calor e terra coberta), não de opinião.
    """
    pior, normal = r["comparacao"]["pior_ano"], r["comparacao"]["ano_normal"]
    agua, terra = item["agua"], item["terra_coberta"]
    # O pior ano é o da pior colheita, não o de maior falta de água: quando a conta dá nele menos falta (ou a mesma)
    # que no ano normal, a frase diz isso com todas as letras, em vez de soar ao contrário.
    contra = pior_contra_normal(agua["falta_no_pior_ano_mm"], agua["falta_no_ano_normal_mm"])
    criterio, do_pior_ano = _criterio_do_pior_ano(r)
    if contra == "maior":
        do_pior_ano = "do pior ano"
        comeco = (f"Em {r['local']['nome']}, no pior ano (safra {pior}) faltaram {_mm(agua['falta_no_pior_ano_mm'])} "
                  f"mm de água para as culturas, com {_dias(agua['dias_de_sede_no_pior_ano'])} dias de sede; no ano "
                  f"normal (safra {normal}), {_mm(agua['falta_no_ano_normal_mm'])} mm.")
    else:
        (p1, p2), (n1, n2) = _pontas(agua["falta_no_pior_ano_mm"]), _pontas(agua["falta_no_ano_normal_mm"])
        teve = f"no ano normal (safra {normal}), que teve {_mm(agua['falta_no_ano_normal_mm'])} mm"
        ao_lado = {"menor": ("menos que " if p1 < n1 and p2 < n2 else "não mais que ") + teve,
                   "igual": f"a mesma falta do ano normal (safra {normal})",
                   "cruza": "numa faixa que cruza a do ano normal: " + teve}[contra]
        comeco = (f"Em {r['local']['nome']}, o pior ano é {criterio} (safra {pior}), não o de maior falta de água na "
                  f"conta: nele faltaram {_mm(agua['falta_no_pior_ano_mm'])} mm de água para as culturas, com "
                  f"{_dias(agua['dias_de_sede_no_pior_ano'])} dias de sede, {ao_lado}.")
    evidencia = (f"{comeco} {_frase_do_calor(item)} Pelo "
                 f"calendário, a terra fica {terra['dias_sem_planta_viva']} dias seguidos sem planta viva antes do "
                 f"plantio da soja ({terra['dias_sem_planta_viva_no_ano']} dias no ano, contando o intervalo entre "
                 "a soja e a 2ª safra).")
    if terra["pelo_satelite"] is not None:
        evidencia += (f" O satélite viu {n(terra['pelo_satelite'])} dias seguidos sem planta verde (o valor do meio "
                      "entre os pontos medidos).")
    outras = {o["id"]: o for o in itens if o["id"] != item["id"]}
    frente, atras, depende = [], [], []       # atras e depende guardam (a perna, a frase)
    curtas = []                               # o mesmo de atras, na frase curta do produtor
    for perna, rotulo, unidade, curta in PERNAS:
        rotulo = rotulo.replace("do pior ano", do_pior_ano)
        ganhou = [o for i, o in outras.items() if item["contra_as_outras"][i][perna] == "melhor"]
        perdeu = [o for i, o in outras.items() if item["contra_as_outras"][i][perna] == "pior"]
        aberto = [o for i, o in outras.items() if item["contra_as_outras"][i][perna] == "depende"]
        meu = _mm(_valor_da_perna(item, perna))
        if ganhou:
            frente.append(f"{rotulo}, ficou na frente de " + _e(
                f"{o['apelido']} ({_mm(_valor_da_perna(o, perna))} {curta})" for o in ganhou) + f": {meu} {unidade}.")
        if perdeu:
            atras.append((perna, f"{rotulo}, ficou atrás de " + _e(
                f"{o['apelido']} ({_mm(_valor_da_perna(o, perna))} {curta})" for o in perdeu) + f": {meu} {unidade}."))
            # na frase curta, um número só de cada lado, e a comparação com o melhor dos que ficaram na frente
            melhor = min(perdeu, key=lambda o: _pontas(_um_numero(o, perna, r)))
            curtas.append((perna, frase_curta_do_risco(perna, _um_numero(item, perna, r), _nome_simples(item, melhor),
                                                       _um_numero(melhor, perna, r))))
        if aberto:
            depende.append((perna, f"{rotulo}, a comparação com " + _e(o["apelido"] for o in aberto)
                            + " depende de quanto o capim disputa água com o milho: isso não foi medido, e "
                              "por isso a conta dá o menor e o maior valor."))
    beneficio = " ".join(frente) or ("Na conta, esta rotação não ficou na frente das outras em água, calor nem "
                                     "terra coberta.")
    # A leitura do produtor (decisão do dono, 2026-11-15): o risco e o que falta saber em UMA frase só, escolhida
    # por `frase_principal`; o texto de sempre, inteiro, vai a `risco_detalhe` e `falta_saber_detalhe` (a leitura
    # do agrônomo).
    riscos = atras + ([(None, RISCOS_PROPRIOS[item["id"]])] if item["id"] in RISCOS_PROPRIOS else [])
    riscos = riscos or [(None, frase) for frase in SEM_RISCO_NA_CONTA]
    faltas = depende + [(None, frase) for frase in FALTA_SABER.get(item["id"], FALTA_SABER_DE_COSTUME)]
    # A frase que a tela mostra em "O risco de cada caminho": a mesma escolha de `risco` (a perna que preocupa ou
    # a primeira), dita curto, com um número só de cada lado e sem o nome comprido das rotações.
    curtas = curtas or [(None, RISCOS_PROPRIOS_CURTOS.get(item["id"], SEM_RISCO_CURTO))]
    preocupacao = r.get("preocupacao")
    return {"evidencia": evidencia, "beneficio": beneficio,
            "risco": frase_principal(riscos, preocupacao), "falta_saber": frase_principal(faltas, preocupacao),
            "risco_curto": frase_principal(curtas, preocupacao),
            "risco_detalhe": " ".join(texto for _, texto in riscos),
            "falta_saber_detalhe": " ".join(texto for _, texto in faltas)}


def texto_da_comparacao(r):
    """As linhas da comparação das rotações do cardápio (três ou mais, contando a de hoje), em frases prontas."""
    linhas = ["AS ROTAÇÕES LADO A LADO (a de hoje e as outras do cardápio; frases só com números da conta)"]
    for item in r.get("comparacao_das_rotacoes", []):
        linhas.append(f"- {item['nome']}{' (a rotação de hoje)' if item['de_hoje'] else ''}")
        linhas += [f"   A evidência: {item['evidencia']}", f"   O benefício: {item['beneficio']}",
                   f"   O risco: {item['risco']}", f"   O que falta saber: {item['falta_saber']}"]
    return linhas


def _linha_do_destaque(r):
    """A linha do destaque: o que mais preocupa o produtor (as notas de 1 a 5 saíram, 2026-11-15)."""
    destaque = r["destaque"]
    de_onde = "No que mais preocupa" if r.get("preocupacao") else "No primeiro ponto medido"
    return f"{de_onde} ({destaque['nome'].lower()}): {_quem(destaque)}."


def texto(r):
    """O texto inteiro da resposta, a partir da resposta do motor."""
    hoje, alternativa = r["rotacoes"]["atual"], r["rotacoes"]["alternativa"]
    regra, local, terra = r["regra_dos_anos"], r["local"], r["terra"]
    normal, seco = regra["ano_normal"], regra["pior_ano"]
    agua_por_tipo = terra["agua_que_segura_mm"]
    t = ["ÓRBITA RURAL · motor provisório, sem site",
         f"{local['nome']}, ponto {local['latitude']}, {local['longitude']} · terra que segura "
         f"{'pouca' if terra['opcao'] == 'pouca' else ('muita' if terra['opcao'] == 'muita' else 'uma quantidade média de')}"
         f" água ({n(terra['agua_por_metro_mm'])} mm por metro de terra; na zona das raízes, "
         f"{n(agua_por_tipo['soja'])} mm para a soja e {n(agua_por_tipo['milho'])} mm para o milho)",
         f"Pergunta: vale trocar \"{hoje['nome']}\" por \"{alternativa['nome']}\"?",
         "",
         "RESPOSTA",
         r["veredito"]["frase"],
         _linha_do_destaque(r),
         "",
         "O QUE FOI MEDIDO, COM O QUE MAIS PREOCUPA NA FRENTE (a ordem não muda nenhum número)"]
    for i, p in enumerate(r["prioridades"], start=1):
        linhas = _prioridade(p, r)
        t.append(f"{i}. {linhas[0]}")
        t.extend(linhas[1:])
    if r.get("comparacao_das_rotacoes"):
        t += [""] + texto_da_comparacao(r)
    chuva, temperatura = r["clima"]["chuva"], r["clima"]["temperatura"]
    t += ["",
          "A PROVA (a chuva e a temperatura da NASA, e a conta de água do FAO-56)",
          f"De onde vem cada número: a chuva é de {chuva['fonte']}; a temperatura é de {temperatura['fonte']}; a "
          f"conta é a do {r['clima']['conta']}.",
          f"Os anos foram escolhidos por uma regra fixada antes de rodar a conta: {regra['criterio']}."]
    if regra["regra"] == "rendimento":
        t.append(f"No IBGE, o milho de 2ª safra rendeu {regra['rendimento_por_safra_kg_ha'][seco]} kg/ha na safra "
                 f"{seco} (o pior) e {regra['rendimento_por_safra_kg_ha'][normal]} kg/ha na safra {normal}; a mediana "
                 f"das {len(regra['rendimento_por_safra_kg_ha'])} safras é {n(regra['mediana_kg_ha'])} kg/ha. "
                 f"Fonte: {regra['fonte_do_rendimento']}.")
        t.append(f"Se a regra fosse a da chuva (a menor chuva na janela), o pior ano seria a safra "
                 f"{regra['pela_chuva_seria']['pior_ano']} e o normal, a safra {regra['pela_chuva_seria']['ano_normal']}.")
    else:
        t.append(f"A mediana da chuva das {len(regra['chuva_por_safra_mm'])} safras é {n(regra['mediana_mm'])} mm.")
    if regra.get("empate_do_pior_ano"):
        t.append(f"As safras {' e '.join(regra['empate_do_pior_ano'])} empatam no pior rendimento; vale a mais "
                 "antiga.")
    if regra["empate_do_ano_normal"]:
        t.append(f"As safras {' e '.join(regra['empate_do_ano_normal'])} ficam à mesma distância da mediana; "
                 "pelo desempate, vale a mais antiga.")
    rotulo_do_pior = "Pior ano" if regra["regra"] == "rendimento" else "Ano mais seco"
    t += _palha_e_disputa(r)
    t += _ano("Ano normal", normal, r) + _ano(rotulo_do_pior, seco, r)
    contra = pior_contra_normal(hoje["safras"][seco]["total"]["falta_mm"], hoje["safras"][normal]["total"]["falta_mm"])
    if contra != "maior":
        t.append(f"Atenção: o pior ano é {_criterio_do_pior_ano(r)[0]}, não o de maior falta de água na conta: na "
                 f"rotação de hoje, a falta de água da safra {seco} foi "
                 f"{'menor que a' if contra == 'menor' else 'igual à'} da safra {normal}.")
    if "aviso_do_ano_mais_seco" in regra:
        t.append(f"Atenção ao ano mais seco: {regra['aviso_do_ano_mais_seco']}. Em 2025 a NASA POWER soma "
                 f"{n(regra['chuva_de_2025_mm'])} mm no ano. Por isso, a segunda safra mais seca vai ao lado:")
        t += _ano("Segunda safra mais seca", regra["segunda_mais_seca"], r)
    t += ["Safra por safra (a falta de água em mm; entre parênteses, a falta do milho em % do que ele pediu; a "
          "alternativa na hipótese do meio e, no fim da linha, a faixa do milho):"]
    t += [_linha_da_safra(s, r) for s in regra["chuva_por_safra_mm"]]
    for nome, rot in (("rotação de hoje", hoje), ("alternativa", alternativa)):
        sede = rot["safras_com_sede"]
        t.append(f"Safras com sede na {nome}: {sede['quantas']} de {len(rot['safras'])} com o critério de "
                 f"{sede['criterio_pct']}% ({', '.join(sede['quais']) or 'nenhuma'}); com 10%, {sede['com_10_pct']}; "
                 f"com 30%, {sede['com_30_pct']}. Nas {len(rot['safras'])} safras somadas: "
                 f"{n(rot['soma_das_10_safras']['falta_da_soja_mm'])} mm de falta na soja, "
                 f"{n(rot['soma_das_10_safras']['falta_do_milho_mm'])} mm no milho e "
                 f"{rot['soma_das_10_safras']['dias_de_sede']} dias de sede.")
    t.append(f"O clima usado vai de {r['clima']['primeiro_dia']} a {r['clima']['ultimo_dia']}; a temperatura foi "
             f"baixada em {temperatura['baixado_em']}; a origem da chuva: {chuva['origem']}.")
    extra = r["safra_2025_26"]
    t += ["",
          "O RISCO",
          "- A braquiária bebe água junto com o milho (quanto, é hipótese: por isso a faixa) e depois dele: a "
          "terra pode chegar mais seca ao plantio da soja (os números de água na terra no plantio, acima, mostram "
          "quanto). Na soma das "
          f"{len(hoje['safras'])} safras, a falta de água da soja foi de "
          f"{n(hoje['soma_das_10_safras']['falta_da_soja_mm'])} mm na rotação de hoje e de "
          f"{n(alternativa['soma_das_10_safras']['falta_da_soja_mm'])} mm na alternativa (hipótese do meio); a do milho, "
          f"de {n(hoje['soma_das_10_safras']['falta_do_milho_mm'])} mm na rotação de hoje e de "
          f"{n(alternativa['faixa_da_soma_das_10_safras']['falta_do_milho_mm']['menor'])} a "
          f"{n(alternativa['faixa_da_soma_das_10_safras']['falta_do_milho_mm']['maior'])} mm na alternativa.",
          f"- A safra 2025-26 ficou à parte ({extra['aviso']}): chuva de {n(extra['chuva_da_janela_mm'])} mm na "
          f"janela; falta do milho de {n(extra['atual']['milho']['falta_relativa_pct'])}% na rotação de hoje e de "
          f"{n(extra['faixa_da_alternativa']['falta_do_milho_pct']['menor'])}% a "
          f"{n(extra['faixa_da_alternativa']['falta_do_milho_pct']['maior'])}% na alternativa.",
          f"- {r['hipoteses']} parâmetros da conta ainda são hipótese (o comando com --json lista cada um, com a "
          "fonte e a etiqueta)."]
    t += [f"- {aviso}" for aviso in r["clima"]["avisos"]]
    t += [f"- {limite}" for limite in r["limites"]]
    t += [""] + _ndvi(r)
    t += ["", "Valide com o agrônomo antes de decidir: isto é uma conta com o clima da região, não uma recomendação."]
    return "\n".join(t)
