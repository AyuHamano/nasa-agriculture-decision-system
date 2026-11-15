/* Base: o painel do ramo nat do time (nathancabrall). Ligação com o motor e telas de resultado geradas com IA (Claude) */
/* A tela do resultado: as duas leituras (produtor e agrônomo). Recebe o que o adaptar() leu e devolve HTML.
   Nenhuma conta de dado aqui: só ordenar, comparar para escolher a frase, formatar o número e pôr o desenho na escala. */
(function () {
  "use strict";

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function num(x, casas) { return typeof x !== "number" ? "—" : x.toLocaleString("pt-BR", { minimumFractionDigits: casas || 0, maximumFractionDigits: casas || 0 }); }
  function int(x) { return num(x, 0); }
  function um(x) { return num(x, 1); }
  function icone(nome) { return '<span data-lucide="' + nome + '"></span>'; }
  function e(lista) { lista = lista.slice(); return lista.length < 2 ? lista.join("") : lista.slice(0, -1).join(", ") + " e " + lista[lista.length - 1]; }
  function iguais(a, b) { return int(a) === int(b); }
  var ICONES = { agua: "droplets", solo: "sprout", erosao: "mountain", renda: "wallet" };
  var ORDEM = ["agua", "solo", "erosao", "renda"];

  function prioridadesNaOrdem(v, notas) {
    return v.prioridades.map(function (p) { return { id: p.id, nome: p.nome, veredito: p.veredito, nota: notas && notas[p.id] != null ? notas[p.id] : p.nota }; })
      .sort(function (a, b) { return (b.nota - a.nota) || (ORDEM.indexOf(a.id) - ORDEM.indexOf(b.id)); });
  }

  // "50%" ou "entre 48% e 50%": o que a cultura recebeu (ou, sem o complemento, o que faltou), como o motor deu.
  function quanto(c, f) {
    if (c.recebeuPct != null) {
      if (c.recebeuFaixa && !iguais(c.recebeuFaixa.menor, c.recebeuFaixa.maior)) return { recebeu: true, faixa: c.recebeuFaixa, texto: t("resultado.agua.entre", { a: int(c.recebeuFaixa.menor), b: int(c.recebeuFaixa.maior) }) };
      return { recebeu: true, faixa: null, valor: c.recebeuPct, texto: int(c.recebeuPct) + "%" };
    }
    if (f && !iguais(f.menor, f.maior)) return { recebeu: false, faixa: f, texto: t("resultado.agua.entre", { a: int(f.menor), b: int(f.maior) }) };
    return { recebeu: false, faixa: null, valor: c.faltaPct, texto: int(c.faltaPct) + "%" };
  }
  function quantoDoMilho(l) { return quanto(l.milho, l.faixa ? l.faixa.milhoPct : null); }

  /* ---------- peças de desenho ---------- */
  function faixaDoAno(trechos, classe) {
    return '<div class="year-strip ' + (classe || "") + '">' + trechos.map(function (s) {
      var nome = t("resultado.ano.coberturas." + s.cobertura);
      return '<i class="seg seg-' + esc(s.cobertura) + '" style="flex:' + Number(s.dias) + ' 1 0" title="' + esc(t("resultado.ano.trecho", { o_que: nome, de: s.de, ate: s.ate, dias: s.dias })) + '">' +
             (classe ? "" : "<span>" + (s.dias >= 60 ? esc(nome) : "") + "</span>") + "</i>";
    }).join("") + "</div>";
  }
  function meses(a, classe) {
    return '<div class="' + classe + '">' + a.meses.map(function (m, i) { return '<span style="flex:' + Number(a.diasPorMes[i] || 30) + ' 1 0">' + esc(m) + "</span>"; }).join("") + "</div>";
  }
  function legendaDoAno(a) {
    var vistos = [];
    a.atual.concat(a.alternativa).forEach(function (s) { if (vistos.indexOf(s.cobertura) < 0) vistos.push(s.cobertura); });
    var ordem = ["soja", "milho", "milho_com_capim", "capim", "sem_planta"];
    vistos.sort(function (x, y) { return ordem.indexOf(x) - ordem.indexOf(y); });
    return '<div class="legend">' + vistos.map(function (c) { return '<span><i class="seg-' + esc(c) + '"></i>' + esc(t("resultado.ano.coberturas." + c)) + "</span>"; }).join("") + "</div>";
  }
  function linhasDoAno(v, curto) {
    var a = v.anoDaTerra;
    function linha(rot, classe, rotulo) {
      return '<div class="year-label ' + classe + '"><b>' + esc(rotulo) + "</b>" + (curto ? "" : "<small>" + esc(v.nomes[rot]) + "</small>") + "</div>" + faixaDoAno(a[rot]) +
             '<div class="year-count"><strong>' + int(v.semPlanta[rot].dias) + "</strong><span>" + esc(t("resultado.ano.dias")) + "</span></div>";
    }
    return '<div class="year"><span class="gap"></span>' + meses(a, "year-months") + '<span class="gap"></span>' +
           linha("atual", "hoje", t("locais.hoje")) + linha("alternativa", "alt", t("locais.alternativa")) + "</div>";
  }
  function medidor(frase, q) {
    var barra;
    if (q.recebeu) barra = q.faixa ? '<b class="g-max" style="width:' + q.faixa.maior + '%"></b><i class="g-min" style="width:' + q.faixa.menor + '%"></i><em style="left:' + q.faixa.menor + '%"></em><em style="left:' + q.faixa.maior + '%"></em>'
                                   : '<i class="g-min" style="width:' + q.valor + '%"></i>';
    else barra = q.faixa ? '<b class="f-max" style="width:' + q.faixa.maior + '%"></b><u class="f-min" style="width:' + q.faixa.menor + '%"></u>' : '<u class="f-min" style="width:' + q.valor + '%"></u>';
    return '<div class="gauge"><p>' + frase + '</p><div class="gauge-bar' + (q.recebeu ? "" : " falta") + '">' + barra + "</div></div>";
  }
  function bloco(n, titulo, sub, corpo, extra, classe) {
    return '<article class="panel block ' + (classe || "") + '"><header class="block-head"><span class="block-num">' + n + "</span><div><h2>" + esc(titulo) + "</h2><p>" + esc(sub) + "</p></div>" + (extra || "") + "</header>" + corpo + "</article>";
  }
  function leitura(html) { return '<p class="meaning">' + icone("lightbulb") + "<span>" + html + "</span></p>"; }

  /* ---------- a leitura do produtor ---------- */
  function fraseDaAgua(v) {
    var s = v.porSafra[v.anos.pior]; if (!s) return "";
    var h = quantoDoMilho(s.atual), a = quantoDoMilho(s.alternativa);
    return t(h.recebeu ? "resultado.troca.agua" : "resultado.troca.aguaFalta", { alt: a.texto, hoje: h.texto });
  }
  function fraseDaPrioridade(v, id) {
    if (id === "agua") return fraseDaAgua(v);
    return t("resultado.troca." + id, { alt: int(v.semPlanta.alternativa.dias), hoje: int(v.semPlanta.atual.dias) });
  }
  function resposta(v, notas) {
    var grupos = { alternativa: [], atual: [], depende: [], empate: [], nm: [] };
    prioridadesNaOrdem(v, notas).forEach(function (p) { (grupos[p.veredito] || grupos.nm).push(p); });
    var titulos = { alternativa: ["trending-up", "resultado.ganha"], atual: ["trending-down", "resultado.perde"], depende: ["scale", "resultado.depende"], empate: ["equal", "resultado.igual"], nm: ["circle-help", "resultado.naoMedido"] };
    var colunas = Object.keys(grupos).filter(function (g) { return grupos[g].length; }).map(function (g) {
      return '<div class="trade-col ' + g + '"><h3>' + icone(titulos[g][0]) + esc(t(titulos[g][1])) + "</h3>" +
             grupos[g].map(function (p) { return "<p><b>" + esc(p.nome) + ":</b> " + fraseDaPrioridade(v, p.id) + "</p>"; }).join("") + "</div>";
    }).join("");
    return '<article class="answer"><span class="eyebrow">' + esc(t("resultado.resposta")) + "</span><h2>" + esc(v.veredito.frase) + '</h2><p class="ask">' +
           esc(t("resultado.pergunta", { atual: v.nomes.atual, alternativa: v.nomes.alternativa })) + '</p><div class="trade">' + colunas + "</div></article>" +
           '<div class="rot-legend"><div class="rot-line hoje"><b>' + esc(t("locais.hoje")) + "</b><span>" + esc(v.nomes.atual) + '</span></div><div class="rot-line alt"><b>' +
           esc(t("locais.alternativa")) + "</b><span>" + esc(v.nomes.alternativa) + "</span></div></div>";
  }
  function anoDaTerra(v) {
    if (!v.anoDaTerra) return bloco(2, t("resultado.ano.titulo"), t("resultado.ano.sub"), '<p class="note">' + esc(t("resultado.ano.semFaixa")) + "</p>");
    var h = v.semPlanta.atual, a = v.semPlanta.alternativa;
    return bloco(2, t("resultado.ano.titulo"), t("resultado.ano.sub"), linhasDoAno(v) + legendaDoAno(v.anoDaTerra) +
      leitura(t("resultado.ano.leitura", { hoje: int(h.dias), hojeDe: h.de, hojeAte: h.ate, alt: int(a.dias), altDe: a.de, altAte: a.ate })));
  }
  function chuva(v, safra) {
    var c = v.chuvaPorMes, a = v.anoDaTerra, dados = c && c.safras[safra];
    if (!dados || !a || !c.maior) return '<p class="note">' + esc(t("resultado.agua.semChuva")) + "</p>";
    var barras = dados.mm.map(function (mm, i) {
      return '<div class="rain-col" style="flex:' + Number(a.diasPorMes[i] || 30) + ' 1 0"><b>' + int(mm) + '</b><i style="height:' + (100 * mm / c.maior) + '%"></i></div>';
    }).join("");
    return "<h3>" + esc(t("resultado.agua.chuva")) + '</h3><div class="rain-bars">' + barras + "</div>" + meses(a, "rain-months") + faixaDoAno(a.atual, "mini") +
           '<p class="rain-foot">' + esc(t("resultado.agua.chuvaPe")) + "</p>";
  }
  function desenharAgua(v, qual) {
    var safra = v.anos[qual], outro = qual === "pior" ? "normal" : "pior", s = v.porSafra[safra], o = v.porSafra[v.anos[outro]];
    if (!s) return "";
    function grupo(rot, classe, rotulo) {
      var m = quantoDoMilho(s[rot]), j = quanto(s[rot].soja);
      return '<div class="gauge-group ' + classe + '"><h4><i></i>' + esc(rotulo) + "</h4>" +
             medidor(t(m.recebeu ? "resultado.agua.milho" : "resultado.agua.milhoFalta", { pct: m.texto }), m) +
             medidor(t(j.recebeu ? "resultado.agua.soja" : "resultado.agua.sojaFalta", { pct: j.texto }), j) + "</div>";
    }
    var mh = quantoDoMilho(s.atual), ma = quantoDoMilho(s.alternativa), sh = quanto(s.atual.soja), sa = quanto(s.alternativa.soja), porque = [];
    if (ma.faixa) porque.push(t("resultado.agua.porqueFaixa"));
    else if (ma.texto === mh.texto) porque.push(t("resultado.agua.milhoIgual"));
    if (sh.texto === sa.texto) porque.push(t("resultado.agua.sojaIgual"));
    else if (sh.recebeu) porque.push(t(sa.valor < sh.valor ? "resultado.agua.sojaMenos" : "resultado.agua.sojaMais"));
    var comparar = o && mh.recebeu ? '<p class="why">' + esc(t("resultado.agua.comparar", { rotulo: t(outro === "normal" ? "resultado.agua.noNormal" : "resultado.agua.noPior"), safra: o.safra, pct: quantoDoMilho(o.atual).texto })) + "</p>" : "";
    return '<p class="year-context">' + t(qual === "pior" ? "resultado.agua.contextoPior" : "resultado.agua.contextoNormal", { safra: esc(safra), kg: int(s.rendimento), total: v.safras.length }) + "</p>" +
           '<div class="water-grid"><div class="rain">' + chuva(v, safra) + '</div><div class="gauges"><h3>' + esc(t("resultado.agua.recebeu")) + "</h3>" +
           grupo("atual", "hoje", t("locais.hoje")) + grupo("alternativa", "alt", t("locais.alternativa")) +
           '<div class="gauge-key">' + (mh.recebeu ? '<span><i class="k-agua"></i>' + esc(t("resultado.agua.chaveRecebeu")) + "</span>" : "") + (ma.faixa ? '<span><i class="k-faixa"></i>' + esc(t("resultado.agua.chaveFaixa")) + "</span>" : "") +
           '<span><i class="k-falta"></i>' + esc(t("resultado.agua.chaveFaltou")) + "</span></div>" + comparar + "</div></div>" +
           leitura(porque.join(" "));
  }
  function dezSafras(v) {
    var forte = v.sedeForte, total = v.safras.length;
    function nivel(falta) { return falta < 20 ? 0 : falta < 30 ? 1 : falta < 40 ? 2 : falta < 50 ? 3 : 4; }
    function linha(rot, classe, rotulo) {
      var quais = forte && forte[rot] ? forte[rot].quais : [];
      return '<span class="row-label ' + classe + '"><b>' + esc(rotulo) + "</b></span>" + v.safras.map(function (s) {
        var l = v.porSafra[s][rot], q = quantoDoMilho(l), eForte = quais.indexOf(s) >= 0;
        var texto = q.faixa ? int(q.faixa.menor) + "–" + int(q.faixa.maior) + "%" : q.texto;
        return '<span class="mark lvl-' + nivel(l.milho.faltaPct) + (eForte ? " forte" : "") + '" title="' + esc(s) + '">' + esc(texto) + (eForte ? "<small>" + esc(t("resultado.safras.forte")) + "</small>" : "") + "</span>";
      }).join("");
    }
    var cabeca = '<span class="head-gap"></span>' + v.safras.map(function (s) {
      var marca = s === v.anos.pior ? '<em class="pior">' + esc(t("resultado.safras.pior")) + "</em>" : s === v.anos.normal ? "<em>" + esc(t("resultado.safras.normal")) + "</em>" : "";
      return '<span class="season-name">' + marca + esc(s) + "</span>";
    }).join("");
    var colheita = '<span class="row-label harvest-label">' + esc(t("resultado.safras.colheita")) + "</span>" + v.safras.map(function (s) { return '<span class="harvest">' + int(v.porSafra[s].rendimento) + "</span>"; }).join("");
    var recebeu = v.temRecebida, escala = t(recebeu ? "resultado.safras.escalaRecebeu" : "resultado.safras.escalaFaltou");
    var rampa = '<div class="ramp"><b>' + esc(t("resultado.safras.escalaTitulo")) + "</b>" + escala.map(function (x, i) { return '<span><i class="lvl-' + i + '"></i>' + esc(x) + "</span>"; }).join("") + "</div>";
    var texto = "";
    if (forte && forte.atual) {
      var a = forte.alternativa || { quantas: null, alarmes: [], quebrasAbaixo: [] };
      var quantasAlt = a.faixa && a.faixa.menor !== a.faixa.maior ? t("resultado.safras.deAte", { a: a.faixa.menor, b: a.faixa.maior }) : String(a.quantas);
      texto = t(forte.recebeuNivel != null ? "resultado.safras.leitura" : "resultado.safras.leituraFalta", { nivel: um(forte.recebeuNivel != null ? forte.recebeuNivel : forte.nivel), quebras: esc(e(forte.safrasDeQuebra)), hoje: forte.atual.quantas, alt: quantasAlt, total: total });
      if (forte.atual.alarmes.length) texto += " " + t("resultado.safras.alarme", { safras: esc(e(forte.atual.alarmes)) });
      if (forte.atual.quebrasAbaixo.length) texto += " " + t("resultado.safras.quebraSemSede", { safras: esc(e(forte.atual.quebrasAbaixo)) });
    }
    texto += (texto ? " " : "") + t("resultado.safras.colheitaNota");
    return bloco(4, t("resultado.safras.titulo", { total: total }), t(recebeu ? "resultado.safras.sub" : "resultado.safras.subFalta", { primeira: v.safras[0], ultima: v.safras[total - 1] }),
      '<div class="seasons">' + cabeca + linha("atual", "hoje", t("locais.hoje")) + linha("alternativa", "alt", t("locais.alternativa")) + colheita + "</div>" + rampa + leitura(texto));
  }
  function oQuePesa(v, notas) {
    var s = v.porSafra[v.anos.pior], h = v.semPlanta.atual.dias, a = v.semPlanta.alternativa.dias;
    var cartoes = prioridadesNaOrdem(v, notas).map(function (p) {
      var grande, texto;
      if (p.id === "agua" && s) {
        var mh = quantoDoMilho(s.atual), ma = quantoDoMilho(s.alternativa);
        grande = t("resultado.pesa.aguaGrande", { alt: ma.faixa ? int(ma.faixa.menor) + " a " + int(ma.faixa.maior) + "%" : ma.texto, hoje: mh.texto }) + "<small>" + esc(t(mh.recebeu ? "resultado.pesa.aguaPequeno" : "resultado.pesa.aguaPequenoFalta")) + "</small>";
        texto = t(p.veredito === "depende" ? "resultado.pesa.aguaDepende" : "resultado.pesa.aguaTexto");
      } else if (p.id === "renda" || p.veredito === "nm") { grande = esc(t("resultado.pesa.rendaGrande")); texto = t("resultado.pesa.rendaTexto"); }
      else { grande = t("resultado.pesa.diasGrande", { alt: int(a), hoje: int(h) }) + "<small>" + esc(t("resultado.pesa.diasPequeno")) + "</small>"; texto = t("resultado.pesa." + (p.id === "erosao" ? "erosaoTexto" : "soloTexto")); }
      return '<div class="prio-card"><header>' + icone(ICONES[p.id] || "circle") + "<strong>" + esc(p.nome) + "</strong><span>" + esc(t("resultado.pesa.nota", { nota: p.nota })) + '</span></header><span class="who ' + p.veredito + '">' +
             esc(t("resultado.quem." + p.veredito)) + '</span><div class="big">' + grande + "</div><p>" + esc(texto) + "</p></div>";
    }).join("");
    return bloco(5, t("resultado.pesa.titulo"), t("resultado.pesa.sub"), '<div class="prio-grid">' + cartoes + "</div>");
  }
  function riscoEAgronomo(v) {
    var itens = [t("resultado.risco.capim"), t("resultado.risco.renda"), t("resultado.risco.palha"), t("resultado.risco.hipoteses", { n: int(v.hipoteses) })];
    return '<div class="duo">' + bloco(6, t("resultado.risco.titulo"), t("resultado.risco.sub"), '<ul class="plain-list">' + itens.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul>", "", "risk-card") +
      bloco(icone("user-check"), t("resultado.agronomo.titulo"), t("resultado.agronomo.sub"), '<ul class="plain-list">' + t("resultado.agronomo.perguntas").map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") +
      '</ul><button class="text-button" data-acao="aba-agronomo" style="margin-top:12px">' + esc(t("resultado.agronomo.ver")) + " →</button>", "", "agro-card") + "</div>";
  }
  function resumo(v, estado) {
    var m = v.mensagemDoMotor, notas = estado.notas || {};
    if (m && ORDEM.every(function (k) { return m.notas[k] === notas[k]; })) return m.texto;   // o texto curto do próprio motor (orbita.mensagem)
    var s = v.porSafra[v.anos.pior], linhas = [
      t("resultado.resumo.cabeca", { produto: NOME_DO_PRODUTO, propriedade: estado.propriedade ? estado.propriedade.nome : "", cidade: v.cidade }),
      t("resultado.resumo.pergunta", { atual: v.nomes.atual, alternativa: v.nomes.alternativa }), "", t("resultado.resumo.resposta", { frase: v.veredito.frase }), "", t("resultado.resumo.prioridades")];
    prioridadesNaOrdem(v, notas).forEach(function (p) { linhas.push(t("resultado.resumo.linha", { nome: p.nome, nota: p.nota, quem: t("resultado.quem." + p.veredito).toLowerCase() })); });
    linhas.push("", t("resultado.resumo.dias", { hoje: int(v.semPlanta.atual.dias), alt: int(v.semPlanta.alternativa.dias) }));
    if (s) { var mh = quantoDoMilho(s.atual), ma = quantoDoMilho(s.alternativa); linhas.push(t(mh.recebeu ? "resultado.resumo.agua" : "resultado.resumo.aguaFalta", { safra: s.safra, hoje: mh.texto, alt: ma.texto })); }
    linhas.push("", t("resultado.resumo.fim"));
    return linhas.join("\n");
  }
  function mensagem(v, estado) {
    return bloco(7, t("resultado.mensagem.titulo"), t("resultado.mensagem.sub"), '<div class="message-card"><div class="bubble" id="resumoTexto">' + esc(estado.mensagem || resumo(v, estado)) +
      '</div><button class="primary-action" data-acao="copiar">' + icone("copy") + esc(t("resultado.mensagem.copiar")) + "</button></div>");
  }
  function desenharProdutor(v, estado) {
    var seletor = '<div class="segmented" role="group" aria-label="' + esc(t("resultado.agua.titulo")) + '"><button data-ano="normal" class="' + (estado.ano === "normal" ? "active" : "") + '">' + esc(t("resultado.agua.normal")) +
                  '</button><button data-ano="pior" class="' + (estado.ano === "pior" ? "active" : "") + '">' + esc(t("resultado.agua.pior")) + "</button></div>";
    return resposta(v, estado.notas) + anoDaTerra(v) + bloco(3, t("resultado.agua.titulo"), t("resultado.agua.sub"), '<div id="waterBody">' + desenharAgua(v, estado.ano) + "</div>", seletor) +
           dezSafras(v) + oQuePesa(v, estado.notas) + riscoEAgronomo(v) + mensagem(v, estado);
  }

  /* ---------- a leitura do agrônomo ---------- */
  function etiqueta(x) { return '<span class="tag ' + (x === "publicado" ? "pub" : "hip") + '">' + esc(x || t("agro.parametros.hipotese")) + "</span>"; }
  function tabela(cabeca, linhas, classe) { return '<div class="table-wrap"><table class="data-table ' + (classe || "") + '"><thead>' + cabeca + "</thead><tbody>" + linhas + "</tbody></table></div>"; }
  function painel(titulo, sub, corpo, extra) {
    return '<article class="panel block"><header class="block-head"><div><h2>' + esc(titulo) + "</h2>" + (sub ? "<p>" + esc(sub) + "</p>" : "") + "</div>" + (extra || "") + "</header>" + corpo + "</article>";
  }
  function metodo(v) {
    var m = TEXTOS.pt.agro.metodo, extras = [
      "", t("agro.metodo.kc", { soja: [v.valorDe("culturas.soja.kc_ini"), v.valorDe("culturas.soja.kc_meio"), v.valorDe("culturas.soja.kc_fim")].map(function (x) { return num(x, 2); }).join(" · "),
                               milho: [v.valorDe("culturas.milho_2a_safra.kc_ini"), v.valorDe("culturas.milho_2a_safra.kc_meio"), v.valorDe("culturas.milho_2a_safra.kc_fim")].map(function (x) { return num(x, 2); }).join(" · ") }),
      t("agro.metodo.caixa", { soja: um(v.terra.soja), milho: um(v.terra.milho) }), t("agro.metodo.p", { soja: num(v.valorDe("culturas.soja.p"), 2), milho: num(v.valorDe("culturas.milho_2a_safra.p"), 2) }),
      v.sedeForte ? t("agro.metodo.forte", { nivel: um(v.sedeForte.nivel) }) : ""];
    var passos = m.passos.map(function (p, i) {
      return '<div class="method-step"><b class="n">' + (i + 1) + "</b><h3>" + esc(p.nome) + "</h3><p>" + esc(p.texto) + "</p>" + (extras[i] ? '<span class="ref"><code>' + esc(extras[i]) + "</code></span>" : "") + '<span class="ref">' + esc(p.ref) + "</span></div>";
    }).join("");
    var terra = '<div class="kv" style="margin-top:14px"><div><small>' + esc(t("agro.terra.classe")) + "</small><strong>" + esc(v.terra.classe) + "</strong></div><div><small>" + esc(t("agro.terra.porMetro")) + "</small><strong>" + um(v.terra.porMetro) +
                " mm</strong></div><div><small>" + esc(t("agro.terra.raizSoja")) + "</small><strong>" + um(v.terra.soja) + " mm</strong><span>" + num(v.terra.raizSoja, 1) + " " + esc(t("agro.terra.m")) + "</span></div><div><small>" +
                esc(t("agro.terra.raizMilho")) + "</small><strong>" + um(v.terra.milho) + " mm</strong><span>" + num(v.terra.raizMilho, 1) + " " + esc(t("agro.terra.m")) + "</span></div></div>";
    return painel(m.titulo, t("agro.metodo.sub", { de: v.clima.primeiroDia, ate: v.clima.ultimoDia }), '<div class="method">' + passos + "</div>" + terra);
  }
  function faixaEPalha(v) {
    var pf = v.agua.pelaFaixa, d = v.disputa, corpo = "";
    if (!pf && !d && !v.palha.atual) return "";
    if (d) corpo += '<p class="note">' + esc(d.oQueE.charAt(0).toUpperCase() + d.oQueE.slice(1)) + ". " + etiqueta(d.etiqueta) + "</p>";
    if (pf) {
      var normal = pf.normal ? pf.normal.cenarios : [];
      var linhas = pf.cenarios.map(function (c, i) {
        var info = d ? d.cenarios.filter(function (x) { return x.id === c.id; })[0] : null, n = normal[i] || {};
        return "<tr><td><strong>" + esc(t("agro.faixa.cenarios." + c.id)) + '</strong></td><td class="num">' + (info ? "+" + um(info.pedidoAMais) + "%" : "—") + '</td><td class="num sep">' + um(c.falta) + '</td><td class="num">' + (c.diferenca > 0 ? "+" : "") + um(c.diferenca) +
               "</td><td>" + esc(t("agro.faixa.classes." + c.classe)) + '</td><td class="num sep">' + um(n.falta) + '</td><td class="num">' + (n.diferenca > 0 ? "+" : "") + um(n.diferenca) + "</td><td>" + esc(n.classe ? t("agro.faixa.classes." + n.classe) : "—") + "</td></tr>";
      }).join("");
      var c = TEXTOS.pt.agro.faixa.colunas;
      corpo += tabela("<tr><th></th><th></th><th class='grp sep' colspan='3'>" + esc(t("agro.faixa.pior", { safra: pf.safra })) + "</th><th class='grp sep' colspan='3'>" + esc(t("agro.faixa.normal", { safra: pf.normal ? pf.normal.safra : "" })) +
                      "</th></tr><tr><th>" + esc(c[0]) + '</th><th class="num">' + esc(c[1]) + '</th><th class="num sep">' + esc(c[2]) + '</th><th class="num">' + esc(c[3]) + "</th><th>" + esc(c[4]) + '</th><th class="num sep">' + esc(c[2]) + '</th><th class="num">' + esc(c[3]) + "</th><th>" + esc(c[4]) + "</th></tr>", linhas) +
               '<p class="note">' + esc(t("agro.faixa.hoje", { mm: um(pf.faltaHoje), empate: um(pf.empate) })) + " <b>" + esc(pf.frase) + "</b></p>";
    }
    ["atual", "alternativa"].forEach(function (rot) {
      var p = v.palha[rot]; if (!p) return;
      corpo += '<p class="note"><b>' + esc(t(rot === "atual" ? "agro.safras.hoje" : "agro.safras.alt")) + ":</b> " + esc(t("agro.faixa.palha", { deQue: p.deQue, cobertura: int(p.cobertura), menos: int(p.evaporacaoAMenos), onde: p.ondeVale })) + " " + etiqueta(p.etiqueta) + "<br><small>" + esc(p.regra) + "</small></p>";
    });
    return painel(t("agro.faixa.titulo"), t("agro.faixa.sub"), corpo);
  }
  function parametros(v) {
    var c = TEXTOS.pt.agro.parametros.colunas;
    var linhas = v.parametros.map(function (p) {
      var valor = typeof p.valor === "number" ? num(p.valor, String(p.valor).indexOf(".") >= 0 ? String(p.valor).split(".")[1].length : 0) : Array.isArray(p.valor) ? p.valor.join(" · ") : p.valor === true ? "sim" : p.valor === false ? "não" : String(p.valor);
      return '<tr data-etiqueta="' + esc(p.etiqueta) + '"><td><code>' + esc(p.parametro) + '</code></td><td class="num">' + esc(valor) + "</td><td>" + etiqueta(p.etiqueta) + "</td><td>" +
             (p.fonte ? '<a href="' + esc(p.fonte) + '" target="_blank" rel="noopener">' + esc(t("agro.parametros.abrir")) + "</a> · " : "<em>" + esc(t("agro.parametros.semFonte")) + "</em> · ") + esc(p.trecho) + "</td></tr>";
    }).join("");
    var filtro = '<div class="filter"><button class="active" data-filtro="todos">' + esc(t("agro.parametros.todos")) + '</button><button data-filtro="hipotese">' + esc(t("agro.parametros.soHipoteses")) + "</button></div>";
    return painel(t("agro.parametros.titulo"), t("agro.parametros.sub", { total: v.parametros.length, hip: int(v.hipoteses) }),
      '<div class="scroll-box" id="parametrosBox">' + tabela("<tr><th>" + esc(c[0]) + '</th><th class="num">' + esc(c[1]) + "</th><th>" + esc(c[2]) + "</th><th>" + esc(c[3]) + "</th></tr>", linhas, "params") + "</div>", filtro);
  }
  function calendario(v) {
    var c = TEXTOS.pt.agro.calendario.colunas, k = v.calendario, h = v.semPlanta.atual, a = v.semPlanta.alternativa;
    var linhas = [["soja", k.soja], ["milho", k.milho]].map(function (x) { return "<tr><td><strong>" + esc(t("agro.calendario." + x[0])) + "</strong></td><td>" + esc(x[1].plantio) + "</td><td>" + esc(x[1].sai) + '</td><td class="num">' + int(x[1].ciclo) + "</td></tr>"; }).join("") +
      "<tr><td><strong>" + esc(t("agro.calendario.capim")) + '</strong></td><td colspan="3">' + esc(t("agro.calendario.capimTexto", { data: k.capim.secaEm, dias: int(k.capim.diasAntes) })) + "</td></tr>";
    return painel(t("agro.calendario.titulo"), t("agro.calendario.sub"), '<div class="val-grid"><div>' + tabela("<tr>" + c.map(function (x, i) { return "<th" + (i === 3 ? ' class="num"' : "") + ">" + esc(x) + "</th>"; }).join("") + "</tr>", linhas) +
      '<p class="note">' + esc(t("agro.calendario.entre", { dias: int(k.entre) })) + " " + esc(t("agro.calendario.semPlanta", { hoje: int(h.dias), hojeDe: h.de, hojeAte: h.ate, alt: int(a.dias), altDe: a.de, altAte: a.ate })) + '</p></div><div class="mini-years">' +
      (v.anoDaTerra ? linhasDoAno(v, true) + legendaDoAno(v.anoDaTerra) : "") + "</div></div>");
  }
  function safraPorSafra(v) {
    var c = TEXTOS.pt.agro.safras.colunas, forte = v.sedeForte;
    function mmPct(x) { return um(x.falta) + " (" + um(x.faltaPct) + "%)"; }
    function linha(s, classe, marca) {
      var h = s.atual, a = s.alternativa, fh = forte && forte.atual && forte.atual.quais.indexOf(s.safra) >= 0, fa = forte && forte.alternativa && forte.alternativa.quais.indexOf(s.safra) >= 0;
      var fx = a.faixa && a.faixa.milhoPct ? um(a.faixa.milhoPct.menor) + " a " + um(a.faixa.milhoPct.maior) + "%" : "—";
      return '<tr class="' + classe + '"><td><strong>' + esc(s.safra) + "</strong>" + (marca ? " <small>" + esc(marca) + "</small>" : "") + '</td><td class="num">' + um(s.chuvaJanela) + '</td><td class="num">' + int(s.rendimento) +
        '</td><td class="num sep">' + mmPct(h.soja) + '</td><td class="num">' + mmPct(h.milho) + (fh ? " ●" : "") + '</td><td class="num">' + int(h.total.diasDeSede) + '</td><td class="num">' + um(h.aguaNoPlantio) +
        '</td><td class="num sep">' + mmPct(a.soja) + '</td><td class="num">' + mmPct(a.milho) + (fa ? " ●" : "") + '</td><td class="num">' + fx + '</td><td class="num">' + int(a.total.diasDeSede) + '</td><td class="num">' + um(a.aguaNoPlantio) + '</td><td class="num">' + um(a.capimBebeu) + "</td></tr>";
    }
    var linhas = v.safras.map(function (n) { var s = v.porSafra[n]; return linha(s, n === v.anos.pior ? "hl-pior" : n === v.anos.normal ? "hl-normal" : "", n === v.anos.pior ? t("agro.safras.pior") : n === v.anos.normal ? t("agro.safras.normal") : ""); }).join("");
    if (v.aParte) linhas += linha({ safra: v.aParte.safra, chuvaJanela: v.aParte.chuvaJanela, rendimento: null, atual: v.aParte.atual, alternativa: v.aParte.alternativa }, "apart", t("agro.safras.aParte"));
    var cabeca = '<tr><th colspan="3"></th><th class="grp hoje sep" colspan="4">' + esc(t("agro.safras.hoje")) + '</th><th class="grp alt sep" colspan="6">' + esc(t("agro.safras.alt")) + "</th></tr><tr><th>" + esc(c.safra) + '</th><th class="num">' + esc(c.chuva) + '</th><th class="num">' + esc(c.ibge) +
      '</th><th class="num sep">' + esc(c.soja) + '</th><th class="num">' + esc(c.milho) + '</th><th class="num">' + esc(c.sede) + '</th><th class="num">' + esc(c.plantio) + '</th><th class="num sep">' + esc(c.soja) + '</th><th class="num">' + esc(c.milho) + '</th><th class="num">' + esc(c.faixa) +
      '</th><th class="num">' + esc(c.sede) + '</th><th class="num">' + esc(c.plantio) + '</th><th class="num">' + esc(c.capim) + "</th></tr>";
    var so = v.soma, notas = '<p class="note">' + esc(t("agro.safras.soma", { total: v.safras.length, sojaHoje: um(so.atual.soja), sojaAlt: um(so.alternativa.soja), milhoHoje: um(so.atual.milho), milhoAlt: um(so.alternativa.milho), sedeHoje: int(so.atual.diasDeSede), sedeAlt: int(so.alternativa.diasDeSede) })) +
      (so.faixaDaAlternativa.milho ? " " + esc(t("agro.safras.somaFaixa", { a: um(so.faixaDaAlternativa.milho.menor), b: um(so.faixaDaAlternativa.milho.maior) })) : "") + "</p>";
    if (forte && forte.atual) {
      var fa2 = forte.alternativa || {};
      notas += '<p class="note"><b>● ' + esc(t("agro.safras.forteTitulo")) + ":</b> " + esc(forte.oQueE) + ". " + esc(t("agro.safras.forte", { nivel: um(forte.nivel), quebra: forte.quebra, quebras: e(forte.safrasDeQuebra), hoje: forte.atual.quantas, hojeQuais: e(forte.atual.quais) || "—",
        alt: fa2.faixa && fa2.faixa.menor !== fa2.faixa.maior ? t("resultado.safras.deAte", { a: fa2.faixa.menor, b: fa2.faixa.maior }) : fa2.quantas, altQuais: e(fa2.quais || []) || "—" })) +
        (forte.atual.alarmes.length ? " " + esc(t("agro.safras.alarmes", { safras: e(forte.atual.alarmes) })) : "") + (forte.atual.quebrasAbaixo.length ? " " + esc(t("agro.safras.quebrasAbaixo", { safras: e(forte.atual.quebrasAbaixo) })) : "") + " " + esc(forte.aviso) + "</p>";
    }
    notas += '<p class="note">' + esc(t("agro.safras.regra", { criterio: v.regra.criterio, total: v.safras.length, mediana: um(v.regra.mediana) })) + " " + esc(v.regra.desempate ? v.regra.desempate.charAt(0).toUpperCase() + v.regra.desempate.slice(1) + "." : "") + " " +
      (v.regra.pelaChuva.pior ? esc(t("agro.safras.pelaChuva", { pior: v.regra.pelaChuva.pior, normal: v.regra.pelaChuva.normal })) : "") + "</p>";
    return painel(t("agro.safras.titulo"), t("agro.safras.sub"), tabela(cabeca, linhas, "wide") + notas);
  }
  function validacao(v, val) {
    if (!val || !val.chuva_contra_a_estacao) return painel(t("agro.validacao.titulo"), "", '<p class="note">' + esc(t("agro.validacao.semDados")) + "</p>");
    var ch = val.chuva_contra_a_estacao, co = val.falta_contra_a_colheita || { fontes: [], safras: [] }, nomes = TEXTOS.pt.agro.validacao.nomes;
    function nome(f) { return esc(nomes[f] || f); }
    var cab1 = "<tr><th>" + esc(t("agro.validacao.safra")) + '</th><th class="num">' + esc(t("agro.validacao.estacao")) + "</th>" + ch.fontes.map(function (f) { return '<th class="num">' + nome(f) + "</th>"; }).join("") + "</tr>";
    var lin1 = ch.safras.map(function (s) {
      if (!s.comparada) return "<tr><td><strong>" + esc(s.safra) + '</strong></td><td colspan="' + (ch.fontes.length + 1) + '"><em>' + esc(t("agro.validacao.naoComparada", { dias: s.dias_em_branco })) + "</em></td></tr>";
      return '<tr class="' + (s.a_parte ? "apart" : "") + '"><td><strong>' + esc(s.safra) + '</strong></td><td class="num">' + int(s.estacao_mm) + "</td>" + ch.fontes.map(function (f) { return '<td class="num">' + int((s.pct_da_estacao || {})[f]) + "%</td>"; }).join("") + "</tr>";
    }).join("") + '<tr><td colspan="2"><strong>' + esc(t("agro.validacao.erro")) + "</strong></td>" + ch.fontes.map(function (f) { return '<td class="num"><strong>' + um((ch.erro_medio_pct || {})[f]) + "%</strong>" + (f === ch.mais_perto ? '<span class="tag best">' + esc(t("agro.validacao.maisPerto")) + "</span>" : "") + "</td>"; }).join("") + "</tr>";
    var cab2 = "<tr><th>" + esc(t("agro.validacao.safra")) + '</th><th class="num">' + esc(t("agro.validacao.ibge")) + "</th>" + co.fontes.map(function (f) { return '<th class="num">' + nome(f) + "</th>"; }).join("") + "</tr>";
    var lin2 = co.safras.map(function (s) {
      return '<tr class="' + (co.pior_colheita && s.safra === co.pior_colheita.safra ? "hl-pior" : "") + '"><td><strong>' + esc(s.safra) + '</strong></td><td class="num">' + int(s.ibge_kg_ha) + "</td>" + co.fontes.map(function (f) { return '<td class="num">' + um((s.falta_do_milho_pct || {})[f]) + "%</td>"; }).join("") + "</tr>";
    }).join("") + '<tr><td colspan="2"><strong>' + esc(t("agro.validacao.correlacao")) + "</strong></td>" + co.fontes.map(function (f) { return '<td class="num"><strong>' + num((co.correlacao_de_postos || {})[f], 2) + "</strong>" + (f === co.que_mais_acompanha ? '<span class="tag best">' + esc(t("agro.validacao.maisPerto")) + "</span>" : "") + "</td>"; }).join("") + "</tr>";
    var eto = (val.eto || []).map(function (x) { return "<p class='note'>" + esc(t("agro.validacao.etoTexto", { dias: int(x.dias), motor: num(x.motor_mm_dia, 2), fonte: nomes[x.fonte] || x.fonte, outra: num(x.outra_mm_dia, 2), pct: um(x.motor_acima_pct), r: num(x.correlacao, 2) })) + "</p>"; }).join("");
    var ndvi = v.ndvi.disponivel ? "<h3 class='sub' style='margin-top:14px'>" + esc(t("agro.validacao.ndviTitulo")) + "</h3>" + v.ndvi.frases.map(function (f) { return "<p class='note'>" + esc(f) + "</p>"; }).join("") +
      (v.ndvi.fonteLink ? '<p class="note"><a href="' + esc(v.ndvi.fonteLink) + '" target="_blank" rel="noopener">' + esc(v.ndvi.fonteNome) + "</a></p>" : "") : "";
    return painel(t("agro.validacao.titulo"), t("agro.validacao.sub"), '<div class="val-grid"><div><h3>' + esc(t("agro.validacao.chuvaTitulo")) + "</h3><p>" + esc(t("agro.validacao.chuvaTexto", { janela: ch.janela, estacao: ch.estacao })) + "</p>" + tabela(cab1, lin1) +
      '<p class="note">' + esc(t("agro.validacao.erroTexto", { n: ch.safras_comparadas, fonte: nomes[ch.mais_perto] || ch.mais_perto })) + "</p></div><div><h3>" + esc(t("agro.validacao.colheitaTitulo")) + "</h3><p>" + esc(t("agro.validacao.colheitaTexto")) + "</p>" + tabela(cab2, lin2) +
      '<p class="note">' + esc(t("agro.validacao.correlacaoTexto")) + "</p></div></div><h3 class='sub' style='margin-top:6px'>" + esc(t("agro.validacao.etoTitulo")) + "</h3>" + eto + ndvi);
  }
  function limites(v) {
    var itens = v.limites.concat(v.clima.avisos);
    if (v.aParte) itens.push(t("agro.limites.aParte", { safra: v.aParte.safra, aviso: v.aParte.aviso, hoje: um(v.aParte.atual.milho.faltaPct), alt: um(v.aParte.alternativa.milho.faltaPct) }));
    var f = v.clima, fontes = '<p class="note"><b>' + esc(t("agro.fontes.chuva")) + ":</b> " + esc(f.chuvaFonte) + ". <b>" + esc(t("agro.fontes.temperatura")) + ":</b> " + esc(f.temperaturaFonte) +
      (f.temperaturaLink ? ' (<a href="' + esc(f.temperaturaLink) + '" target="_blank" rel="noopener">' + esc(t("agro.fontes.consulta")) + "</a>)" : "") + ". <b>" + esc(t("agro.fontes.conta")) + ":</b> " + esc(f.conta) + ". <b>" + esc(t("agro.fontes.rendimento")) + ":</b> " + esc(v.regra.fonteDoRendimento) +
      ". <b>" + esc(t("agro.fontes.periodo")) + ":</b> " + esc(t("agro.fontes.de", { de: f.primeiroDia, ate: f.ultimoDia })) + ".</p>";
    return painel(t("agro.limites.titulo"), t("agro.limites.sub"), '<ul class="plain-list">' + itens.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul><h3 class='sub' style='margin-top:16px'>" + esc(t("agro.fontes.titulo")) + "</h3>" + fontes);
  }
  function desenharAgronomo(v, val) {
    return '<div class="result-bar" style="margin-bottom:12px"><p class="agro-intro" style="margin:0;flex:1">' + esc(t("agro.intro")) + '</p><button class="ghost-action" data-acao="baixar">' + icone("download") + esc(t("agro.baixar")) + "</button></div>" +
           metodo(v) + faixaEPalha(v) + parametros(v) + calendario(v) + safraPorSafra(v) + validacao(v, val) + limites(v);
  }

  /* A chuva de cada mês do ano normal e do pior ano, lado a lado (para a visão geral). */
  function chuvaDupla(v) {
    var c = v.chuvaPorMes, a = v.anoDaTerra, n = c && c.safras[v.anos.normal], p = c && c.safras[v.anos.pior];
    if (!n || !p || !a || !c.maior) return "";
    return '<div class="pair-legend"><span><i class="a"></i>' + esc(t("visao.chuvaNormal", { safra: v.anos.normal })) + '</span><span><i class="b"></i>' + esc(t("visao.chuvaPior", { safra: v.anos.pior })) + '</span></div><div class="rain-pair">' +
      n.mm.map(function (mm, i) { return '<div style="flex:' + Number(a.diasPorMes[i] || 30) + ' 1 0" title="' + esc(a.meses[i] + ": " + um(mm) + " mm · " + um(p.mm[i]) + " mm") + '"><i class="a" style="height:' + (100 * mm / c.maior) + '%"></i><i class="b" style="height:' + (100 * p.mm[i] / c.maior) + '%"></i></div>'; }).join("") +
      "</div>" + meses(a, "rain-months");
  }

  window.ORBITA_RESULTADO = { produtor: desenharProdutor, agua: desenharAgua, agronomo: desenharAgronomo, resumo: resumo, linhasDoAno: linhasDoAno, legendaDoAno: legendaDoAno, chuvaDupla: chuvaDupla,
                              num: num, int: int, um: um, esc: esc, icone: icone };
})();
