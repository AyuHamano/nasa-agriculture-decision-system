/* Gerado com IA (Claude). */
/* A ficha do produtor e a comparação das rotações (o formato 7.3 do mapa do projeto).
   Nada é calculado aqui: os números aparecem como vêm; onde vem faixa ({de, ate}), aparece a faixa.
   A única conta é de desenho: o comprimento de cada barra, na escala do maior valor da mesma medida. */
(function () {
  "use strict";

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function ic(nome) { return window.ORBITA_ICONE ? window.ORBITA_ICONE(nome) : ""; }
  function fmt(x) { return typeof x !== "number" || !isFinite(x) ? "" : x.toLocaleString("pt-BR", { maximumFractionDigits: 1 }); }
  function obj(x) { return x && typeof x === "object" && !Array.isArray(x) ? x : {}; }
  function lista(x) { return Array.isArray(x) ? x : []; }

  // Um valor da comparação: número, faixa {de, ate} ou nada.
  function valor(x) {
    if (typeof x === "number" && isFinite(x)) return { tem: true, de: x, ate: x, faixa: false, texto: fmt(x) };
    var o = obj(x);
    if (typeof o.de === "number" && typeof o.ate === "number") {
      if (fmt(o.de) === fmt(o.ate)) return { tem: true, de: o.de, ate: o.ate, faixa: false, texto: fmt(o.de) };
      return { tem: true, de: Math.min(o.de, o.ate), ate: Math.max(o.de, o.ate), faixa: true, texto: t("comparacao.faixa", { de: fmt(o.de), ate: fmt(o.ate) }) };
    }
    return { tem: false, de: null, ate: null, faixa: false, texto: t("comparacao.semMedida") };
  }

  // "soja → milho safrinha → pousio" vira uma sequência desenhada; o nome inteiro fica para o leitor de tela.
  function sequencia(nome, classe) {
    var partes = String(nome || "").split(/\s*(?:→|->)\s*/).filter(Boolean);
    if (partes.length < 2) return '<span class="seq ' + (classe || "") + '">' + esc(nome) + "</span>";
    return '<span class="seq ' + (classe || "") + '"><span class="so-leitor">' + esc(partes.join(", depois ")) + "</span>" +
      partes.map(function (p, i) { return '<span class="parte" aria-hidden="true">' + (i ? "<i></i>" : "") + esc(p) + "</span>"; }).join(" ") + "</span>";
  }

  var MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
  function dataPorExtenso(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
    return m ? Number(m[3]) + " de " + MESES[Number(m[2]) - 1] + " de " + m[1] : "";
  }

  /* ---------- a ficha ---------- */
  function classeDaTerra(terra) {
    var o = obj(window.ORBITA_RESPOSTAS), r = obj(o.respostas && typeof o.respostas === "object" ? o.respostas : o)[terra];
    return r && r.terra && r.terra.classe ? String(r.terra.classe).replace(/\s*\(.*\)\s*$/, "") : "";
  }
  function nomeDaCultura(c) { var n = t("ficha.culturas." + c); return n === "ficha.culturas." + c ? String(c) : n; }
  function campoDaFicha(f, campo) {
    var v = f[campo], falta = '<em class="falta">' + esc(t("ficha.falta")) + "</em>";
    if (campo === "cidade_id") { if (!v) return falta; var n = t("ficha.cidades." + v); return esc(n === "ficha.cidades." + v ? v : n); }
    if (campo === "terra") { if (!v) return falta; var c = classeDaTerra(v), nome = t("ficha.terras." + v); return esc(nome === "ficha.terras." + v ? v : nome) + (c ? "<small>" + esc(c) + "</small>" : ""); }
    if (campo === "rotacao_atual") { return lista(v).length ? sequencia(lista(v).map(nomeDaCultura).join(" → ")) : falta; }
    if (campo === "plantio_da_soja") { return v ? esc(dataPorExtenso(v) || v) : '<span class="leve">' + esc(t("ficha.semData")) + "</span>"; }
    if (campo === "preocupacao") { if (!v) return falta; var p = t("ficha.preocupacoes." + v); return esc(p === "ficha.preocupacoes." + v ? v : p); }
    return esc(v);
  }
  var CAMPOS = ["cidade_id", "terra", "rotacao_atual", "plantio_da_soja", "preocupacao"];

  function fichaVazia() {
    return '<article class="ficha vazia"><h2>' + esc(t("ficha.vaziaTitulo")) + "</h2><p>" + esc(t("ficha.vaziaTexto")) + "</p><dl>" +
      ["cidade_id", "terra", "rotacao_atual"].map(function (c) { return "<div><dt>" + esc(t("ficha.campos." + c)) + '</dt><dd><span class="traco"></span></dd></div>'; }).join("") + "</dl></article>";
  }

  // opcoes: { podeAgir: a ficha é a da última resposta, aoVivo: há agente ligado, corrigindo: o formulário está aberto }
  function ficha(f, opcoes) {
    f = obj(f); opcoes = opcoes || {};
    if (!Object.keys(f).length) return fichaVazia();
    // O agente diz o que ainda falta (ficha.falta); sem essa lista, valem os três campos da conta.
    var completa = Array.isArray(f.falta) ? !f.falta.length : !!(f.cidade_id && f.terra && lista(f.rotacao_atual).length);
    var linhas = CAMPOS.map(function (c) { return '<div class="campo-' + c + '"><dt>' + esc(t("ficha.campos." + c)) + "</dt><dd>" + campoDaFicha(f, c) + "</dd></div>"; }).join("");
    var pe = "";
    if (f.confirmada) pe = '<p class="selo">' + ic("certo") + esc(t("ficha.confirmada")) + "</p>";
    else if (opcoes.corrigindo) pe = formularioDeCorrecao(f, opcoes);
    else if (opcoes.podeAgir && completa) {
      pe = '<div class="acoes"><button class="botao cheio" data-acao="confirmar-ficha">' + ic("certo") + esc(t("ficha.confirmar")) + '</button><button class="botao" data-acao="corrigir-ficha">' + ic("lapis") + esc(t("ficha.corrigir")) + "</button></div>";
    }
    return '<article class="ficha' + (f.confirmada ? " conferida" : "") + '" id="ficha"><header><h2>' + esc(t("ficha.titulo")) + "</h2>" + (f.confirmada ? "" : "<p>" + esc(t("ficha.sub")) + "</p>") + "</header><dl>" + linhas + "</dl>" + pe + "</article>";
  }

  function opcoesDe(chave, atual) {
    var o = obj(t(chave));
    return Object.keys(o).map(function (k) { return '<option value="' + esc(k) + '"' + (k === atual ? " selected" : "") + ">" + esc(o[k]) + "</option>"; }).join("");
  }
  function formularioDeCorrecao(f, opcoes) {
    if (!opcoes.aoVivo) return '<p class="nota">' + esc(t("ficha.corrigirGuardada")) + '</p><div class="acoes"><button class="botao" data-acao="cancelar-correcao">' + esc(t("ficha.cancelar")) + "</button></div>";
    return '<form class="correcao" id="correcao"><h3>' + esc(t("ficha.corrigirTitulo")) + "</h3>" +
      "<label><span>" + esc(t("ficha.campos.cidade_id")) + '</span><select name="cidade_id">' + opcoesDe("ficha.cidades", f.cidade_id) + "</select></label>" +
      "<label><span>" + esc(t("ficha.campos.terra")) + '</span><select name="terra">' + opcoesDe("ficha.terras", f.terra) + "</select></label>" +
      "<label><span>" + esc(t("ficha.campos.rotacao_atual")) + '</span><input name="rotacao" autocomplete="off" value="' + esc(lista(f.rotacao_atual).map(nomeDaCultura).join(", depois ")) + '"></label>' +
      "<label><span>" + esc(t("ficha.campos.preocupacao")) + '</span><select name="preocupacao">' + opcoesDe("ficha.preocupacoes", f.preocupacao) + "</select></label>" +
      '<div class="acoes"><button class="botao cheio" type="submit">' + esc(t("ficha.corrigirEnviar")) + '</button><button class="botao" type="button" data-acao="cancelar-correcao">' + esc(t("ficha.cancelar")) + "</button></div></form>";
  }
  // A correção vira uma fala para o agente (a rota recebe texto): quem muda a ficha é ele.
  function falaDaCorrecao(form) {
    function rotulo(sel) { return sel.options[sel.selectedIndex].text.replace(/\s*\(.*\)\s*$/, ""); }
    var itens = ["o município é " + rotulo(form.cidade_id), "o solo é " + rotulo(form.terra).toLowerCase(), "planto " + String(form.rotacao.value || "").trim(),
                 "o que mais me preocupa é " + rotulo(form.preocupacao).toLowerCase()];
    return t("ficha.correcaoFala", { itens: itens.join("; ") });
  }

  /* ---------- a comparação ---------- */
  var MEDIDAS = [
    { grupo: "agua", de: "agua", chave: "falta_no_pior_ano_mm", un: "mm", escala: "mm" },
    { grupo: "agua", de: "agua", chave: "falta_no_ano_normal_mm", un: "mm", escala: "mm" },
    { grupo: "agua", de: "agua", chave: "dias_de_sede_no_pior_ano", un: "dias", escala: "sede" },
    { grupo: "calor", de: "calor", chave: "dias_de_calor_forte_no_pior_ano", un: "dias", escala: "calor" },
    { grupo: "terra", de: "terra_coberta", chave: "dias_sem_planta_viva", un: "dias", escala: "terra" }
  ];
  var ICONES = { agua: "gota", calor: "sol", terra: "broto" };
  var FRASES = ["evidencia", "beneficio", "risco", "falta_saber"];

  function medidasNaOrdem(preocupacao) {
    var ordem = ["agua", "calor", "terra"];
    if (ordem.indexOf(preocupacao) > 0) ordem = [preocupacao].concat(ordem.filter(function (g) { return g !== preocupacao; }));
    return MEDIDAS.slice().sort(function (a, b) { return ordem.indexOf(a.grupo) - ordem.indexOf(b.grupo); });
  }
  function escalas(rotacoes) {
    var maior = {};
    rotacoes.forEach(function (r) {
      MEDIDAS.forEach(function (m) { var v = valor(obj(r[m.de])[m.chave]); if (v.tem) maior[m.escala] = Math.max(maior[m.escala] || 0, v.ate); });
    });
    return maior;
  }
  function barra(v, maior) {
    if (!v.tem || !maior) return '<span class="barra vazia"></span>';
    var a = Math.max(0, Math.min(100, 100 * v.de / maior)), b = Math.max(0, Math.min(100, 100 * v.ate / maior));
    return '<span class="barra" aria-hidden="true"><i style="width:' + a.toFixed(1) + '%"></i>' + (v.faixa ? '<b style="left:' + a.toFixed(1) + "%;width:" + (b - a).toFixed(1) + '%"></b>' : "") + "</span>";
  }
  function medida(r, m, maior, preocupacao, primeiraDoGrupo) {
    var grupo = obj(r[m.de]), v = valor(grupo[m.chave]), extra = "";
    if (m.grupo === "calor" && typeof grupo.limite_c === "number") extra = "<small>" + esc(t("comparacao.limite", { c: fmt(grupo.limite_c) })) + "</small>";
    if (m.grupo === "terra" && typeof grupo.pelo_satelite === "number") extra = '<small class="sat">' + ic("satelite") + esc(t("comparacao.satelite", { n: fmt(grupo.pelo_satelite) })) + "</small>";
    return '<div class="medida g-' + m.grupo + (m.grupo === preocupacao ? " preocupa" : "") + (primeiraDoGrupo ? " primeira" : "") + '">' +
      '<span class="rotulo">' + (primeiraDoGrupo ? ic(ICONES[m.grupo]) : "") + esc(t("comparacao.medidas." + m.chave)) + "</span>" +
      '<strong class="numero' + (v.tem ? "" : " sem") + (v.faixa ? " faixa" : "") + '">' + esc(v.texto) + (v.tem ? " <small>" + esc(t("comparacao.unidades." + m.un)) + "</small>" : "") + "</strong>" +
      barra(v, maior[m.escala]) + extra + "</div>";
  }
  function cartao(r, medidas, maior, preocupacao) {
    var visto = {};
    var corpo = medidas.map(function (m) { var primeira = !visto[m.grupo]; visto[m.grupo] = true; return medida(r, m, maior, preocupacao, primeira); }).join("");
    var frases = FRASES.map(function (f) {
      return '<div class="frase f-' + f + '"><h4>' + esc(t("comparacao.frases." + f)) + "</h4><p>" + (r[f] ? esc(r[f]) : '<span class="leve">' + esc(t("comparacao.semMedida")) + "</span>") + "</p></div>";
    }).join("");
    return '<article class="rotacao' + (r.de_hoje ? " de-hoje" : "") + '"><header><span class="etiqueta">' + esc(t(r.de_hoje ? "comparacao.deHoje" : "comparacao.outra")) + "</span><h3>" + sequencia(r.nome) + "</h3></header>" + corpo + frases + "</article>";
  }
  function resumo(rotacoes) {
    var chaves = ["falta_no_pior_ano_mm", "dias_de_calor_forte_no_pior_ano", "dias_sem_planta_viva"];
    // No celular: o nome da rotação numa linha e, embaixo, os três números; as colunas ficam alinhadas entre as rotações.
    var cab = "<tr>" + chaves.map(function (c) { return '<th scope="col">' + esc(t("comparacao.curtas." + c)) + "</th>"; }).join("") + "</tr>";
    var grupos = rotacoes.map(function (r) {
      return "<tbody" + (r.de_hoje ? ' class="de-hoje"' : "") + '><tr class="nome"><th colspan="' + chaves.length + '" scope="rowgroup">' + (r.de_hoje ? '<span class="etiqueta">' + esc(t("comparacao.deHoje")) + "</span>" : "") + sequencia(r.nome, "curta") + "</th></tr><tr>" +
        chaves.map(function (c) {
          var m = MEDIDAS.filter(function (x) { return x.chave === c; })[0], v = valor(obj(r[m.de])[c]);
          var texto = v.faixa ? t("comparacao.faixaCurta", { de: fmt(v.de), ate: fmt(v.ate) }) : v.texto;
          return "<td" + (v.tem ? "" : ' class="sem"') + ">" + esc(texto) + (v.tem ? " <small>" + esc(t("comparacao.unidades." + m.un)) + "</small>" : "") + "</td>";
        }).join("") + "</tr></tbody>";
    }).join("");
    return '<div class="resumo"><table><caption>' + esc(t("comparacao.resumo")) + "</caption><thead>" + cab + "</thead>" + grupos + "</table></div>";
  }
  function glossario() {
    return '<details class="como-ler"><summary>' + esc(t("comparacao.comoLer")) + "</summary><dl>" +
      lista(t("comparacao.glossario")).map(function (g) { return "<div><dt>" + esc(g[0]) + "</dt><dd>" + esc(g[1]) + "</dd></div>"; }).join("") + "</dl></details>";
  }

  function comparacao(rotacoes, preocupacao, aviso) {
    rotacoes = lista(rotacoes).filter(function (r) { return r && typeof r === "object"; });
    if (!rotacoes.length) return "";
    rotacoes = rotacoes.slice().sort(function (a, b) { return (b.de_hoje ? 1 : 0) - (a.de_hoje ? 1 : 0); });   // a de hoje primeiro; o resto na ordem em que veio
    var medidas = medidasNaOrdem(preocupacao), maior = escalas(rotacoes), oQue = t("ficha.preocupacoes." + preocupacao);
    var linha = ICONES[preocupacao] && oQue !== "ficha.preocupacoes." + preocupacao
      ? '<p class="preocupa-linha g-' + preocupacao + '">' + ic(ICONES[preocupacao]) + esc(t("comparacao.preocupaLinha", { o_que: oQue.toLowerCase() })) + "</p>" : "";
    return '<section class="comparacao" id="comparacao" aria-labelledby="tituloDaComparacao"><header><h2 id="tituloDaComparacao">' + esc(t("comparacao.titulo")) + "</h2><p>" + esc(t("comparacao.sub")) + "</p>" + linha + "</header>" +
      resumo(rotacoes) +
      '<div class="rotacoes" style="--n:' + rotacoes.length + '">' + rotacoes.map(function (r) { return cartao(r, medidas, maior, preocupacao); }).join("") + "</div>" +
      glossario() +
      '<aside class="agronomo-aviso">' + ic("pessoa") + "<div><h3>" + esc(aviso || t("comparacao.agronomo")) + "</h3><p>" + esc(t("comparacao.agronomoTexto")) + '</p><button class="botao" data-acao="abrir-agronomo">' + esc(t("comparacao.agronomoBotao")) + "</button></div></aside></section>";
  }

  window.ORBITA_COMPARACAO = { ficha: ficha, comparacao: comparacao, sequencia: sequencia, falaDaCorrecao: falaDaCorrecao, esc: esc, fmt: fmt, dataPorExtenso: dataPorExtenso };
})();
