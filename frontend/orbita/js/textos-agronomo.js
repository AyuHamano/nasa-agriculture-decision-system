/* Gerado com IA (Claude). Os textos da leitura do agrônomo (vieram do painel de 2026-11-14). */
TEXTOS.pt.locais = {
  "hoje": "Hoje",
  "alternativa": "Alternativa"
};
TEXTOS.pt.resultado = {
  "ano": {
    "dias": "dias do ano sem planta viva",
    "coberturas": {
      "soja": "Soja",
      "milho": "Milho",
      "milho_com_capim": "Milho com capim",
      "capim": "Capim cobrindo a terra",
      "sem_planta": "Terra sem planta viva"
    },
    "trecho": "{o_que}: de {de} a {ate} ({dias} dias)"
  },
  "safras": {
    "deAte": "de {a} a {b}"
  }
};
TEXTOS.pt.agro = {
  "intro": "Esta leitura mostra como a conta foi feita, com que valores e de onde eles vêm, para o agrônomo conferir. Os números são os mesmos da leitura do produtor, agora em milímetros.",
  "baixar": "Baixar a resposta completa (JSON)",
  "baixado": "Arquivo baixado.",
  "metodo": {
    "titulo": "O método em 5 passos",
    "sub": "A conta é a do manual 56 da FAO (Crop evapotranspiration, 1998), rodada dia a dia de {de} a {ate}.",
    "passos": [
      {
        "nome": "A evaporação de referência",
        "texto": "Quanta água uma grama bem regada perderia em cada dia (a ETo). Sai da fórmula de Hargreaves-Samani, que usa só a temperatura máxima e a mínima do dia e a radiação do sol para a latitude.",
        "ref": "FAO-56, equação 52"
      },
      {
        "nome": "O coeficiente da cultura",
        "texto": "Cada cultura pede uma fração dessa evaporação, que muda com a fase (o Kc). O pedido da planta no dia é Kc × ETo.",
        "ref": "FAO-56, tabelas 11 e 12"
      },
      {
        "nome": "O balanço diário",
        "texto": "A terra é uma caixa de água na profundidade das raízes. Todo dia entra a chuva e sai o que a planta bebeu; a chuva que passa de encher a caixa se perde.",
        "ref": "FAO-56, capítulo 8"
      },
      {
        "nome": "O freio da sede",
        "texto": "Enquanto a água fácil de tirar não acaba, a planta bebe tudo o que pede. Depois disso entra um freio (o Ks, de 1 a 0), e ela bebe Ks × o pedido.",
        "ref": "FAO-56, equação 84"
      },
      {
        "nome": "A falta de água",
        "texto": "É o que a planta pediu menos o que conseguiu beber, somado na safra (de 1/set a 31/ago), em milímetros e em % do pedido. Dia de sede é dia com soja ou milho e freio ligado.",
        "ref": "FAO-56, capítulo 8"
      }
    ],
    "kc": "Kc início · meio · fim: soja {soja}; milho {milho}",
    "caixa": "caixa nesta terra: soja {soja} mm; milho {milho} mm",
    "p": "fração fácil (p): soja {soja}; milho {milho}",
    "forte": "sede forte: falta de {nivel}% ou mais no milho"
  },
  "terra": {
    "classe": "Classe de terra usada",
    "porMetro": "Água que segura por metro",
    "raizSoja": "Caixa na raiz da soja",
    "raizMilho": "Caixa na raiz do milho",
    "m": "m de raiz"
  },
  "faixa": {
    "titulo": "A alternativa em faixa e a palha",
    "sub": "Duas hipóteses pesam no resultado da água: quanto o capim disputa água com o milho e quanto a palha cobre a terra.",
    "cenarios": {
      "sem_disputa": "Sem disputa",
      "meio": "Meio",
      "alta": "Disputa alta"
    },
    "classes": {
      "empate": "empate",
      "pior": "alternativa pior",
      "melhor": "alternativa melhor"
    },
    "colunas": [
      "Cenário da alternativa",
      "Pedido a mais",
      "Falta total (mm)",
      "Diferença para hoje (mm)",
      "Leitura"
    ],
    "pior": "Pior ano · safra {safra}",
    "normal": "Ano normal · safra {safra}",
    "hoje": "Falta total na rotação de hoje no pior ano: {mm} mm. Diferença abaixo de {empate} mm conta como empate.",
    "palha": "{deQue} cobre {cobertura}% da terra e corta {menos}% da evaporação, {onde}."
  },
  "parametros": {
    "titulo": "Os parâmetros da conta",
    "sub": "{total} valores, cada um com a fonte. {hip} ainda são hipótese: escolha do time, a conferir.",
    "todos": "Todos",
    "soHipoteses": "Só as hipóteses",
    "colunas": [
      "Parâmetro",
      "Valor",
      "Situação",
      "Fonte e trecho"
    ],
    "hipotese": "hipótese",
    "semFonte": "escolha do time, sem fonte publicada",
    "abrir": "abrir a fonte"
  },
  "calendario": {
    "titulo": "O calendário usado",
    "sub": "As mesmas datas em todos os anos.",
    "colunas": [
      "Cultura",
      "Plantio",
      "Sai da terra",
      "Dias"
    ],
    "soja": "Soja",
    "milho": "Milho de 2ª safra",
    "capim": "Braquiária (na alternativa)",
    "capimTexto": "seca em {data}, {dias} dias antes da soja",
    "entre": "Entre a soja e o milho: {dias} dias sem planta.",
    "semPlanta": "Sem planta viva: {hoje} dias na rotação de hoje (de {hojeDe} a {hojeAte}) e {alt} na alternativa (de {altDe} a {altAte})."
  },
  "safras": {
    "titulo": "Safra por safra",
    "sub": "A falta de água em mm (o que a planta pediu menos o que bebeu); entre parênteses, em % do pedido. Chuva: de 1/fev a 30/jun. A alternativa está na hipótese do meio; a coluna da faixa dá as duas pontas.",
    "colunas": {
      "safra": "Safra",
      "chuva": "Chuva fev–jun (mm)",
      "ibge": "Milho IBGE (kg/ha)",
      "soja": "Soja: falta mm (%)",
      "milho": "Milho: falta mm (%)",
      "faixa": "Milho: faixa (%)",
      "sede": "Dias de sede",
      "plantio": "Água no plantio (mm)",
      "capim": "Capim bebeu (mm)"
    },
    "hoje": "Rotação de hoje",
    "alt": "Alternativa",
    "normal": "ano normal",
    "pior": "pior ano",
    "aParte": "à parte",
    "soma": "Soma das {total} safras: falta da soja de {sojaHoje} mm hoje e {sojaAlt} mm na alternativa; do milho, {milhoHoje} mm e {milhoAlt} mm; dias de sede, {sedeHoje} e {sedeAlt}.",
    "somaFaixa": "Na faixa, a falta do milho da alternativa vai de {a} a {b} mm.",
    "forteTitulo": "Sede forte",
    "forte": "Nível: {nivel}% de falta. Safra de quebra: {quebra}; são elas: {quebras}. Passaram do nível: {hoje} na rotação de hoje ({hojeQuais}) e {alt} na alternativa ({altQuais}).",
    "alarmes": "Alarme falso (sede forte com colheita boa): {safras}.",
    "quebrasAbaixo": "Quebra que a conta não viu: {safras}.",
    "regra": "Como os anos foram escolhidos: {criterio}. Mediana das {total} safras: {mediana} kg/ha.",
    "pelaChuva": "Pela regra da chuva, o pior ano seria a safra {pior} e o normal, a {normal}."
  },
  "validacao": {
    "titulo": "A validação cruzada",
    "sub": "Duas conferências contra dados medidos em terra, feitas fora da conta.",
    "chuvaTitulo": "A chuva de cada fonte contra a estação em terra",
    "chuvaTexto": "Total {janela} em cada fonte, em % do que a {estacao} mediu. Só entram as safras em que a estação tem dado.",
    "safra": "Safra",
    "estacao": "Estação (mm)",
    "naoComparada": "não comparada: {dias} dias em branco na estação",
    "erro": "Erro médio",
    "maisPerto": "mais perto",
    "erroTexto": "Erro médio = a distância média até a estação, em % dela, nas {n} safras comparadas (a 2025-26 entra aqui). Por isso a chuva da conta é a do {fonte}.",
    "colheitaTitulo": "A falta de água simulada contra a colheita do IBGE",
    "colheitaTexto": "A falta do milho (% do pedido, rotação de hoje, terra média) com cada fonte de chuva, ao lado do rendimento do milho de 2ª safra em Rio Verde.",
    "ibge": "IBGE (kg/ha)",
    "correlacao": "Correlação de postos",
    "correlacaoTexto": "Quanto mais perto de −1, mais a conta acompanha a colheita. São só 10 safras: é indício, não prova. O rendimento também depende de praga, adubo, semente e data de plantio.",
    "etoTitulo": "A evaporação de referência",
    "etoTexto": "Em {dias} dias, a ETo da conta deu em média {motor} mm por dia e a do FAO no {fonte}, {outra} mm por dia: a conta fica {pct}% acima (correlação diária de {r}).",
    "ndviTitulo": "O verde visto pelo satélite (prova só da rotação de hoje)",
    "nomes": {
      "imerg": "IMERG (satélite)",
      "chirps": "CHIRPS",
      "era5": "ERA5",
      "power": "NASA POWER (modelo)",
      "open-meteo": "Open-Meteo"
    },
    "semDados": "Os dados da validação não vieram neste site."
  },
  "limites": {
    "titulo": "Os limites da conta",
    "sub": "O que a conta não vê e o que ainda é escolha do time. Não é recomendação agronômica.",
    "aParte": "Safra {safra}: {aviso}. Falta do milho: {hoje}% na rotação de hoje e {alt}% na alternativa."
  },
  "fontes": {
    "titulo": "As fontes",
    "chuva": "Chuva",
    "temperatura": "Temperatura",
    "conta": "Conta",
    "rendimento": "Rendimento",
    "periodo": "Período",
    "de": "de {de} a {ate}",
    "consulta": "a consulta"
  }
};
