/* Gerado com IA (Claude). */
/* As três telas do produtor, desenhadas a partir do que o motor devolve: "Minha lavoura hoje" (POST /lavoura-hoje),
   "Ensaiar" (POST /recomendacao) e "Registrar" (POST /registro). Aqui não há conta: cada número é o que veio; as
   frases curtas são montadas com os campos da resposta, e a frase inteira do motor fica em "Entender". */
(function () {
  "use strict";

  var CIDADES = { rio_verde: "Rio Verde", jatai: "Jataí", silvania: "Silvânia" };
  var ROTACOES = {
    soja_milho_pousio: { nome: "Soja e depois milho", curto: "Milho", artigo: "o milho" },
    soja_milho_braquiaria: { nome: "Soja e depois milho com capim", curto: "Milho com capim", artigo: "o milho com capim" },
    soja_sorgo_pousio: { nome: "Soja e depois sorgo", curto: "Sorgo", artigo: "o sorgo" }
  };
  var TERRAS = { pouca: { nome: "Arenosa", dica: "seca rápido" }, media: { nome: "Média", dica: "nem areia nem barro" }, muita: { nome: "Argilosa", dica: "segura a água" } };
  var MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
  var CULTURA = { soja: "soja", milho: "milho", sorgo: "sorgo", braquiaria: "capim", sem_planta: "terra sem planta" };
  var ITEM = { fase: "a fase da cultura", agua: "a água", calor: "o calor", verde: "o verde do satélite", terra_coberta: "a terra coberta", aviso_de_sede: "o aviso de sede" };
  var AGRONOMO = "Converse com o agrônomo antes de decidir.";      // só quando a resposta não traz o aviso curto do motor
  var MAIS = {
    fechar: '<path d="M6 6l12 12M18 6 6 18"/>',
    pino: '<path d="M12 21s6.500-5.800 6.500-11a6.500 6.500 0 0 0-13 0c0 5.200 6.500 11 6.500 11z"/><circle cx="12" cy="10" r="2.300"/>',
    painel: '<path d="M4.500 16a7.500 7.500 0 0 1 15 0"/><path d="M12 16l3.500-5"/><path d="M3 19.500h18"/>',
    caderno: '<path d="M6 3.500h12v17H6z"/><path d="M9 8h6M9 12h6M9 16h3.500"/>'
  };

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function ic(nome) {
    if (MAIS[nome]) return '<svg class="ic" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' + MAIS[nome] + "</svg>";
    return window.ORBITA_ICONE ? window.ORBITA_ICONE(nome) : "";
  }
  function num(x, casas) { return typeof x === "number" && isFinite(x) ? x.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas }) : ""; }
  function faixa(v, casas) { return v && typeof v === "object" ? num(v.de, casas) + " a " + num(v.ate, casas) : num(v, casas); }
  // A falta de água do milho com capim vem do motor como faixa (do menor ao maior efeito do capim). Na tabela vai um
  // número só: o do meio, que o motor também devolve (o cenário "meio" da disputa do capim com o milho). Nada é
  // calculado aqui: se o motor não mandar o do meio, fica a faixa.
  function doMeio(e, v) {
    if (!v || typeof v !== "object") return v;
    if (typeof v.meio === "number") return v.meio;
    var m = (((((e.comparacao || {}).agua || {}).pela_faixa || {}).por_cenario || {}).meio || {}).falta_mm;
    return typeof m === "number" && m >= v.de && m <= v.ate ? m : v;
  }
  function partes(iso) { return /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || "")); }
  function dataCurta(iso) { var m = partes(iso); return m ? m[3] + "/" + m[2] : String(iso || ""); }
  function dataBR(iso) { var m = partes(iso); return m ? m[3] + "/" + m[2] + "/" + m[1] : String(iso || ""); }
  function dataPorExtenso(iso) { var m = partes(iso); return m ? Number(m[3]) + " de " + MESES[Number(m[2]) - 1] : String(iso || ""); }
  function nd(n) { return typeof n === "number" ? { num: num(n, 0), un: n === 1 ? "dia" : "dias" } : { num: "", un: "" }; }
  function dias(n) { var d = nd(n); return d.num + " " + d.un; }
  function cultura(c) { return CULTURA[c] || String(c || "").replace(/_/g, " "); }
  function maiuscula(s) { s = String(s || ""); return s.charAt(0).toUpperCase() + s.slice(1); }
  function juntar(lista) { return lista.length < 2 ? lista.join("") : lista.slice(0, -1).join(", ") + " e " + lista[lista.length - 1]; }
  function primeiraFrase(s) { var m = /^[\s\S]*?[.!?](?=\s+[A-ZÀ-Ý]|\s*$)/.exec(String(s || "")); return m ? m[0] : String(s || ""); }
  function idDaRotacao(lista) {
    var txt = (Array.isArray(lista) ? lista.join(" ") : String(lista || "")).toLowerCase();
    return /sorgo/.test(txt) ? "soja_sorgo_pousio" : /braqui|capim/.test(txt) ? "soja_milho_braquiaria" : "soja_milho_pousio";
  }
  function valorDaFicha(campo, v) {
    if (campo === "cidade_id") return CIDADES[v] || v;
    if (campo === "rotacao_id") return ROTACOES[v] ? ROTACOES[v].nome.toLowerCase() : v;
    if (campo === "terra") return TERRAS[v] ? "terra " + TERRAS[v].nome.toLowerCase() : v;
    if (campo === "plantio_da_soja") return "soja plantada em " + dataPorExtenso(v);
    return String(v || "");
  }
  function ondeEOQue(l) { return (CIDADES[l.cidade_id] || "") + ", " + (ROTACOES[l.rotacao_id] ? ROTACOES[l.rotacao_id].nome.toLowerCase() : ""); }
  function esperando(texto) { return '<div class="o-tela"><p class="o-espera" role="status">' + esc(texto || "Buscando os dados da sua lavoura…") + "</p></div>"; }
  function entender(frase, dado) {
    return '<details class="o-mais"><summary>Entender</summary><p>' + esc(frase) + "</p>" + (dado ? '<p class="o-dado">Dado de ' + esc(dataBR(dado)) + "</p>" : "") + "</details>";
  }

  /* ---------- Minha lavoura hoje ---------- */
  var CARTAO = {
    aviso_de_sede: function (it, naTerra) {
      var planta = naTerra && naTerra !== "sem_planta" ? "a " + cultura(naTerra) : "a lavoura", d;
      if (it.ja_com_sede) { d = nd(it.dias_seguidos_de_sede); return { titulo: "Aviso de sede", num: d.num, un: d.un, ex: maiuscula(planta) + " já está com sede.", largo: true }; }
      if (typeof it.dias_ate_a_sede === "number") { d = nd(it.dias_ate_a_sede); return { titulo: "Aviso de sede", num: d.num, un: d.un, ex: "Se não chover, " + planta + " entra em sede em " + dataCurta(it.data_da_sede) + ".", largo: true }; }
      return { titulo: "Aviso de sede", num: "Sem aviso", ex: primeiraFrase(it.frase), largo: true };
    },
    agua: function (it) {
      var barras = "";
      function linha(nome, o, hoje) {
        if (!o || typeof o.agua_na_terra_mm !== "number") return "";
        return "<span>" + esc(nome) + '</span><i><b' + (hoje ? ' class="h"' : "") + ' style="width:' + Math.max(0, Math.min(100, Number(o.agua_na_terra_pct) || 0)) + '%"></b></i><span>' + num(o.agua_na_terra_mm, 1) + "</span>";
      }
      barras = linha("hoje", it, true) + linha("ano normal", it.no_ano_normal) + linha("ano ruim", it.no_pior_ano);
      return { titulo: "Água na terra", num: num(it.agua_na_terra_mm, 1), un: "mm", largo: true,
        ex: it.com_sede ? "Com sede há " + dias(it.dias_seguidos_de_sede) + "." : "Sem sede: " + num(it.agua_na_terra_pct, 0) + "% do que a terra segura.",
        extra: barras ? '<div class="o-barras" role="img" aria-label="A água de hoje ao lado do mesmo dia do ano normal e do ano ruim, em mm">' + barras + "</div>" : "" };
    },
    fase: function (it) {
      var d;
      if (it.cultura) {
        d = nd(it.dias_desde_o_plantio);
        return { titulo: "Fase da " + cultura(it.cultura), num: d.num, un: d.un,
          ex: maiuscula(it.fase_nome || "na terra") + "." + (it.fase_critica ? " É a fase crítica, até " + dataCurta(it.fase_critica_ate) + "." : it.fase_critica_de && typeof it.dias_para_a_fase_critica === "number" && it.dias_para_a_fase_critica > 0 ? " A fase crítica começa em " + dataCurta(it.fase_critica_de) + "." : "") };
      }
      if (it.proximo_plantio && typeof it.proximo_plantio.faltam_dias === "number") {
        d = nd(it.proximo_plantio.faltam_dias);
        return { titulo: "Fase da cultura", num: d.num, un: d.un, ex: "Para a " + cultura(it.proximo_plantio.cultura) + " entrar, em " + dataCurta(it.proximo_plantio.data) + "." };
      }
      return { titulo: "Fase da cultura", num: "–", ex: primeiraFrase(it.frase) };
    },
    calor: function (it) {
      if (!it.cultura || typeof it.dias_de_calor_forte_desde_o_plantio !== "number") return { titulo: "Calor", num: "–", ex: primeiraFrase(it.frase) };
      var d = nd(it.dias_de_calor_forte_desde_o_plantio), meio = ((it.nas_safras_guardadas || {}).desde_o_plantio || {}).valor_do_meio;
      return { titulo: "Calor", num: d.num, un: d.un, ex: "Acima de " + num(it.limite_c, 0) + " °C desde o plantio." + (typeof meio === "number" ? " O normal é " + num(meio, 0) + "." : "") };
    },
    verde: function (it) {
      if (typeof it.verde !== "number") return { titulo: "Verde do satélite", num: "–", ex: primeiraFrase(it.frase) };
      var meio = (it.outros_anos || {}).valor_do_meio, como = { acima: "Acima do normal da época", dentro: "Dentro do normal da época", abaixo: "Abaixo do normal da época" }[it.leitura];
      return { titulo: "Verde do satélite", num: num(it.verde, 2), ex: (como ? como + (typeof meio === "number" ? " (" + num(meio, 2) + ")" : "") + "." : "Sem outros anos para comparar.") + " Imagem de " + dataCurta(it.imagem) + "." };
    },
    terra_coberta: function (it) {
      var d = nd(it.dias_seguidos), antes = it.antes || {};
      return { titulo: "Terra coberta", num: d.num, un: d.un,
        ex: (it.com_planta_viva ? "Com planta viva." : "Sem planta viva.") + (typeof antes.dias_seguidos === "number" ? " Antes, " + dias(antes.dias_seguidos) + (antes.com_planta_viva ? " com planta." : " sem.") : "") };
    }
  };
  var ORDEM = ["aviso_de_sede", "agua", "fase", "calor", "verde", "terra_coberta"];

  function fraseDoTopo(itens) {
    function nomes(sit) { return itens.filter(function (i) { return i.situacao === sit; }).map(function (i) { return ITEM[i.id] || i.titulo; }); }
    var alerta = nomes("alerta"), atencao = nomes("atencao"), f = [];
    if (alerta.length) f.push("Em alerta: " + juntar(alerta) + ".");
    if (atencao.length) f.push((atencao.length > 1 ? "Pedem atenção: " : "Pede atenção: ") + juntar(atencao) + ".");
    return f.length ? f.join(" ") : "Tudo tranquilo na lavoura.";
  }
  function painel(p, l) {
    var itens = Array.isArray(p && p.itens) ? p.itens : [], porId = {};
    itens.forEach(function (i) { porId[i.id] = i; });
    if (!p || p.disponivel === false || !itens.length) {
      return '<div class="o-tela"><header class="o-missao s-sem_dado"><p class="o-missao-onde">' + esc(ondeEOQue(l)) + '</p><h1>Minha lavoura hoje</h1><p class="o-missao-frase">Sem dado novo desta lavoura agora.</p></header>' +
        (p && p.aviso ? '<p class="o-nota">' + esc(p.aviso) + "</p>" : "") + "</div>";
    }
    var naTerra = (porId.fase || {}).o_que_esta_na_terra || (porId.agua || {}).o_que_esta_na_terra || "", fase = porId.fase || {};
    var agora = fase.cultura ? maiuscula(cultura(fase.cultura)) + " com " + dias(fase.dias_desde_o_plantio) + ", " + (fase.fase_nome || "na terra") + "." : "";
    var cartoes = ORDEM.filter(function (id) { return porId[id] && CARTAO[id]; }).map(function (id) {
      var it = porId[id], o = CARTAO[id](it, naTerra);
      return '<article class="o-cartao k-' + esc(id) + " s-" + esc(it.situacao) + (o.largo ? " largo" : "") + '"><h2>' + esc(o.titulo) + '</h2><p class="o-num">' + esc(o.num) + (o.un ? " <small>" + esc(o.un) + "</small>" : "") + "</p>" +
        '<p class="o-sit"><i></i>' + esc(it.situacao_nome || it.situacao) + '</p><p class="o-ex">' + esc(o.ex) + "</p>" + (o.extra || "") + entender(it.frase, (it.ultimo_dado || {}).data) + "</article>";
    }).join("");
    return '<div class="o-tela"><header class="o-missao s-' + esc(p.situacao) + '"><p class="o-missao-onde">' + esc(ondeEOQue(l)) + "</p><h1>Minha lavoura hoje</h1>" +
      '<p class="o-missao-sit"><i></i>' + esc(p.situacao_nome || p.situacao) + '</p><p class="o-missao-frase">' + esc(fraseDoTopo(itens)) + (agora ? " <span>" + esc(agora) + "</span>" : "") + "</p>" +
      '<p class="o-missao-data">Dado de ' + esc(dataBR(p.ultimo_dia_com_dado)) + "</p></header>" +
      '<div class="o-cartoes">' + cartoes + '</div><p class="o-agronomo">' + esc(p.aviso || AGRONOMO) + "</p></div>";
  }

  /* ---------- Ensaiar ---------- */
  function anoRuim(e) { var s = String(((e || {}).regra_dos_anos || {}).pior_ano || ""); return /^\d{4}-\d{2}$/.test(s) ? s.slice(0, 2) + s.slice(5) : s; }
  function respostaDoEnsaio(lista, ano) {
    var hoje = lista.filter(function (c) { return c.de_hoje; })[0] || lista[0], ganhos = [];
    lista.forEach(function (o) {
      if (o === hoje) return;
      var c = (o.contra_as_outras || {})[hoje.id] || {}, g = [];
      if (c.agua === "melhor") g.push("com menos falta de água");
      if (c.calor === "melhor") g.push((o.calor || {}).dias_de_calor_forte_no_pior_ano === 0 ? "sem calor forte" : "com menos calor forte");
      if (c.terra_coberta === "melhor") g.push("com menos dias de terra sem planta");
      if (g.length) ganhos.push({ n: g.length, frase: (ROTACOES[o.id] ? ROTACOES[o.id].artigo : o.apelido) + " passa " + juntar(g) });
    });
    ganhos = ganhos.sort(function (x, y) { return y.n - x.n; }).map(function (x) { return x.frase; });      // primeiro quem ficou na frente em mais medidas
    return "Num ano ruim como " + ano + ", " + (ganhos.length ? ganhos.join("; ") : "a sua rotação ficou na frente ou empatada nas três medidas") + ".";
  }
  function ensaio(e, l) {
    var lista = Array.isArray(e && e.comparacao_das_rotacoes) ? e.comparacao_das_rotacoes : [];
    if (!lista.length) return '<div class="o-tela estreita"><header class="o-cab"><h1>Ensaiar</h1></header><p class="o-nota">O ensaio desta lavoura não está disponível agora.</p></div>';
    var cal = e.calendario || {}, ano = anoRuim(e), segunda = /sorgo/.test(l.rotacao_id) ? cal.sorgo : cal.milho;
    var MEDIDAS = [
      { k: "agua", nome: "Água que falta", sub: "mm no ano ruim", v: function (c) { return faixa(doMeio(e, (c.agua || {}).falta_no_pior_ano_mm), 1); } },
      { k: "calor", nome: "Calor forte", sub: "dias na fase crítica", v: function (c) { return faixa((c.calor || {}).dias_de_calor_forte_no_pior_ano, 0); } },
      { k: "terra_coberta", nome: "Terra sem planta", sub: "dias seguidos", v: function (c) { return faixa((c.terra_coberta || {}).dias_sem_planta_viva, 0); } }
    ];
    function curto(c) { return ROTACOES[c.id] ? ROTACOES[c.id].curto : maiuscula(c.apelido); }
    function melhor(c, k) {
      var f = lista.filter(function (o) { return o !== c; }).map(function (o) { return ((c.contra_as_outras || {})[o.id] || {})[k]; });
      return f.length > 0 && f.every(function (x) { return x === "melhor" || x === "empate"; }) && f.some(function (x) { return x === "melhor"; });
    }
    var tabela = '<div class="o-t3-caixa"><table class="o-t3"><thead><tr><th scope="col"><span class="so-leitor">A medida</span></th>' +
      lista.map(function (c) { return '<th scope="col"' + (c.de_hoje ? ' class="sua"' : "") + ">" + (c.de_hoje ? "<small>A sua</small>" : "") + esc(curto(c)) + "</th>"; }).join("") + "</tr></thead><tbody>" +
      MEDIDAS.map(function (m) {
        return '<tr><th scope="row" class="k-' + m.k + '">' + esc(m.nome) + "<small>" + esc(m.sub) + "</small></th>" +
          lista.map(function (c) { return "<td" + (melhor(c, m.k) ? ' class="m"' : "") + ">" + esc(m.v(c)) + "</td>"; }).join("") + "</tr>";
      }).join("") + '</tbody></table></div><p class="o-legenda">Em destaque, o melhor número de cada linha. Todas começam com soja.</p>';
    var riscos = '<h2 class="o-sub">O risco de cada caminho</h2><ul class="o-riscos">' + lista.map(function (c) {
      return "<li><b>" + esc(curto(c)) + (c.de_hoje ? " (a sua)" : "") + "</b>" + esc(c.risco_curto || c.risco) + "</li>";
    }).join("") + "</ul>";
    var prova = '<details class="o-prova"><summary class="o-bt claro">Ver a prova</summary><div class="o-prova-dentro">' +
      lista.map(function (c) {
        var falta = (c.agua || {}).falta_no_pior_ano_mm;
        return "<h3>" + esc(maiuscula(c.nome || c.apelido)) + "</h3><p>" + esc(c.evidencia) + "</p>" +
          (falta && typeof falta === "object" ? "<p>A água que falta no ano ruim vai de " + esc(faixa(falta, 1)) + " mm, conforme o capim disputa água com o milho.</p>" : "") + (c.falta_saber ? "<p><b>O que falta saber.</b> " + esc(c.falta_saber) + "</p>" : "");
      }).join("") +
      "<h3>De onde vêm os números</h3><p>A chuva é a medida por satélite da NASA (GPM IMERG). A temperatura é a da NASA POWER. O verde da lavoura vem do satélite MODIS, da NASA. A conta da água segue o manual da FAO. O ano ruim (" + esc(String((e.regra_dos_anos || {}).pior_ano || "")) + ") e o ano normal (" + esc(String((e.regra_dos_anos || {}).ano_normal || "")) + ') são os da colheita do IBGE na cidade.</p><p><a href="#agronomo">Ver as contas completas, para o agrônomo</a></p></div></details>';
    return '<div class="o-tela estreita"><header class="o-cab"><h1>Ensaiar</h1><p>' + esc(CIDADES[l.cidade_id] || "") + (cal.soja && cal.soja.plantio ? ". Soja em " + esc(cal.soja.plantio) + (segunda && segunda.plantio ? ", a 2ª safra entra em " + esc(segunda.plantio) : "") : "") + ".</p></header>" +
      '<p class="o-resp">' + esc(respostaDoEnsaio(lista, ano)) + "</p>" + tabela + riscos +
      '<p class="o-agronomo">' + esc(e.aviso || AGRONOMO) + "</p>" +
      '<div class="o-acoes">' + prova + '<button type="button" class="o-bt" data-acao="ano-ruim">' + ic("tocar") + "Ver um ano ruim: " + esc(ano) + "</button></div></div>";
  }

  /* ---------- Registrar ---------- */
  function registro(r, l, safras, safra, colheita, recado) {
    var cab = '<header class="o-cab"><h1>Registrar</h1><p>' + esc(CIDADES[l.cidade_id] || "") + ", a safra que terminou.</p></header>";
    var escolha = safras && safras.length > 1 ? '<label class="o-campo" for="safraDoRegistro"><span>Safra</span><select id="safraDoRegistro">' +
      safras.map(function (s) { return '<option value="' + esc(s) + '"' + (s === safra ? " selected" : "") + ">" + esc(s) + "</option>"; }).join("") + "</select></label>" : "";
    if (!r || !r.agua) return '<div class="o-tela estreita">' + cab + escolha + '<p class="o-nota">O registro desta safra não está disponível agora.</p></div>';
    var plantado = Array.isArray(r.o_que_foi_plantado) ? r.o_que_foi_plantado : [], entre = r.entre_as_safras_guardadas || {}, calor = r.calor || {}, terra = r.terra_coberta || {};
    var linhas = plantado.map(function (c) { return "<li><span>" + esc(maiuscula(cultura(c.cultura))) + "</span><span>" + esc(dataCurta(c.entra)) + " a " + esc(dataCurta(c.sai)) + ", " + esc(dias(c.dias)) + "</span></li>"; }).join("");
    function tile(k, titulo, n, un, ex) { return '<article class="o-cartao k-' + k + '"><h2>' + esc(titulo) + '</h2><p class="o-num">' + esc(n) + (un ? " <small>" + esc(un) + "</small>" : "") + '</p><p class="o-ex">' + esc(ex) + "</p></article>"; }
    var dCalor = nd(calor.dias_de_calor_forte), dTerra = nd(terra.dias_sem_planta_viva);
    var tiles = tile("agua", "Água que faltou", num(r.agua.falta_mm, 1), "mm", "Com " + dias(r.agua.dias_de_sede) + " de sede.") +
      tile("calor", "Calor forte", dCalor.num, dCalor.un, "Na fase crítica das culturas.") +
      tile("terra_coberta", "Terra sem planta", dTerra.num, dTerra.un, "Dos " + num(terra.dias_da_safra, 0) + " dias da safra.");
    var posicao = typeof entre.posicao === "number" && entre.de ? '<p class="o-posicao">' + (entre.a_parte ? "Ao lado das " + num(entre.de, 0) + " safras guardadas, a falta de água da 2ª safra seria a " : "Entre as " + num(entre.de, 0) + " safras guardadas, a falta de água da 2ª safra foi a ") + num(entre.posicao, 0) + "ª maior.</p>" : "";
    var campos = plantado.map(function (c) {
      var v = colheita && colheita[c.cultura] != null ? colheita[c.cultura] : "";
      return '<label class="o-campo"><span>' + esc(maiuscula(cultura(c.cultura))) + '</span><input type="number" inputmode="decimal" min="0" max="400" step="0.1" name="' + esc(c.cultura) + '" value="' + esc(v) + '" placeholder="sacas por hectare"></label>';
    }).join("");
    return '<div class="o-tela estreita">' + cab + escolha +
      '<h2 class="o-sub">O que foi plantado</h2><ul class="o-linhas">' + linhas + "</ul>" +
      '<h2 class="o-sub">O que a terra mostrou</h2><div class="o-cartoes tres">' + tiles + "</div>" + posicao + entender(r.frase, "") +
      '<form id="formDaColheita" class="o-colheita"><h2 class="o-sub">Quanto você colheu</h2>' + campos +
      '<button type="submit" class="o-bt">' + ic("certo") + 'Guardar a safra</button><p class="o-recado" role="status">' + esc(recado || (colheita ? "Safra guardada neste aparelho em " + dataBR(colheita.em) + "." : "")) + "</p></form></div>";
  }

  window.ORBITA_TELAS = { CIDADES: CIDADES, ROTACOES: ROTACOES, TERRAS: TERRAS, esc: esc, ic: ic, dataBR: dataBR, dataCurta: dataCurta, dataPorExtenso: dataPorExtenso,
    idDaRotacao: idDaRotacao, valorDaFicha: valorDaFicha, esperando: esperando, painel: painel, ensaio: ensaio, registro: registro, anoRuim: anoRuim };
})();
