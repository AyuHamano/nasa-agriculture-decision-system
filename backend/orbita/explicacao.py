# Gerado com IA (Claude)
"""A explicação em português simples: frases prontas, preenchidas só com os números da resposta do motor.

Não há IA aqui (não há chave ligada). Todo número que aparece no texto vem de `motor.responder`.
"""

QUEM = {"atual": "a rotação de hoje se saiu melhor", "alternativa": "a alternativa se saiu melhor",
        "empate": "empate", "não medido": "não medido"}


def n(numero):
    """Número em português: inteiro sem casa, o resto com uma casa e vírgula."""
    if isinstance(numero, int):
        return str(numero)
    return f"{numero:.1f}".replace(".", ",")


def _prioridade(p, r):
    hoje, alternativa = r["rotacoes"]["atual"], r["rotacoes"]["alternativa"]
    seco = r["comparacao"]["pior_ano"]
    rotulo = "No pior ano" if r["regra_dos_anos"]["regra"] == "rendimento" else "No ano mais seco"
    linhas = [f"{p['nome']} (nota {p['nota']}): {QUEM[p['melhor']]}."]
    if p["id"] == "agua":
        a, b = hoje["safras"][seco]["total"], alternativa["safras"][seco]["total"]
        linhas.append(f"   {rotulo} (safra {seco}), faltaram {n(a['falta_mm'])} mm de água para a soja e o milho "
                      f"na rotação de hoje e {n(b['falta_mm'])} mm na alternativa (falta de água = o que a planta "
                      "pediu menos o que conseguiu beber).")
        linhas.append(f"   Das {len(hoje['safras'])} safras, o milho passou sede (falta de "
                      f"{hoje['safras_com_sede']['criterio_pct']}% ou mais do que pediu) em "
                      f"{hoje['safras_com_sede']['quantas']} na rotação de hoje e em "
                      f"{alternativa['safras_com_sede']['quantas']} na alternativa.")
        if r["comparacao"]["agua"]["as_medidas_discordam"]:
            linhas.append("   As duas medidas apontam para lados diferentes; por isso, empate.")
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
            linha += f"; a braquiária bebeu {n(s['braquiaria']['bebido_mm'])} mm depois do milho"
        linhas.append(linha + ".")
    return linhas


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
         f"{QUEM[r['destaque']['melhor']]}.",
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
    t += _ano("Ano normal", normal, r) + _ano(rotulo_do_pior, seco, r)
    if "aviso_do_ano_mais_seco" in regra:
        t.append(f"Atenção ao ano mais seco: {regra['aviso_do_ano_mais_seco']}. Em 2025 a NASA POWER soma "
                 f"{n(regra['chuva_de_2025_mm'])} mm no ano. Por isso, a segunda safra mais seca vai ao lado:")
        t += _ano("Segunda safra mais seca", regra["segunda_mais_seca"], r)
    t += ["Safra por safra (a falta de água em mm; entre parênteses, a falta do milho em % do que ele pediu):"]
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
          "- A braquiária também bebe água depois do milho: a terra pode chegar mais seca ao plantio da soja "
          "(os números de água na terra no plantio, acima, mostram quanto). Na soma das "
          f"{len(hoje['safras'])} safras, a falta de água da soja foi de "
          f"{n(hoje['soma_das_10_safras']['falta_da_soja_mm'])} mm na rotação de hoje e de "
          f"{n(alternativa['soma_das_10_safras']['falta_da_soja_mm'])} mm na alternativa.",
          f"- A safra 2025-26 ficou à parte ({extra['aviso']}): chuva de {n(extra['chuva_da_janela_mm'])} mm na "
          f"janela; falta do milho de {n(extra['atual']['milho']['falta_relativa_pct'])}% na rotação de hoje e de "
          f"{n(extra['alternativa']['milho']['falta_relativa_pct'])}% na alternativa.",
          f"- {r['hipoteses']} parâmetros da conta ainda são hipótese (o comando com --json lista cada um, com a "
          "fonte e a etiqueta)."]
    t += [f"- {aviso}" for aviso in r["clima"]["avisos"]]
    t += [f"- {limite}" for limite in r["limites"]]
    t += [""] + _ndvi(r)
    t += ["", "Valide com o agrônomo antes de decidir: isto é uma conta com o clima da região, não uma recomendação."]
    return "\n".join(t)
