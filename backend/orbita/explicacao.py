# Gerado com IA (Claude)
"""A explicação em português simples: frases prontas, preenchidas só com os números da resposta do motor.

Não há IA aqui (não há chave ligada). Todo número que aparece no texto vem de `motor.responder`.
"""

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


def _prioridade(p, r):
    hoje, alternativa = r["rotacoes"]["atual"], r["rotacoes"]["alternativa"]
    seco = r["comparacao"]["pior_ano"]
    rotulo = "No pior ano" if r["regra_dos_anos"]["regra"] == "rendimento" else "No ano mais seco"
    linhas = [f"{p['nome']} (nota {p['nota']}): {_quem(p)}."]
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
         f"Na sua maior nota entre o que foi medido ({r['destaque']['nome'].lower()}, nota {r['destaque']['nota']}): "
         f"{_quem(r['destaque'])}.",
         "",
         "SUAS PRIORIDADES, DA MAIOR NOTA PARA A MENOR (elas só mudam a ordem; nenhum número muda)"]
    for i, p in enumerate(r["prioridades"], start=1):
        linhas = _prioridade(p, r)
        t.append(f"{i}. {linhas[0]}")
        t.extend(linhas[1:])
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
    if regra["empate_do_ano_normal"]:
        t.append(f"As safras {' e '.join(regra['empate_do_ano_normal'])} ficam à mesma distância da mediana; "
                 "pelo desempate, vale a mais antiga.")
    rotulo_do_pior = "Pior ano" if regra["regra"] == "rendimento" else "Ano mais seco"
    t += _palha_e_disputa(r)
    t += _ano("Ano normal", normal, r) + _ano(rotulo_do_pior, seco, r)
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
