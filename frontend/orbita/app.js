/* Gerado com IA (Claude). */
/* Liga as peças da tela do produtor: as duas leituras (produtor e agrônomo), os três momentos, a conversa,
   a mesa (a ficha e a comparação), o replay e os dois modos (conversas guardadas e agente ao vivo).
   Os textos estão em js/textos.js. A tela não faz conta: mostra o que o motor e o agente devolvem. */
(function () {
  "use strict";

  var C = window.ORBITA_COMPARACAO, esc = C.esc;
  function ic(nome) { return window.ORBITA_ICONE ? window.ORBITA_ICONE(nome) : ""; }
  function $(id) { return document.getElementById(id); }
  var MOMENTOS = ["antes", "durante", "depois"];
  var app = { api: "", dados: null, momento: "antes", idDaConversa: "", corrigindo: false, avisos: [], terraDoAgronomo: "", agronomoPronto: false };
  var conversa = null;

  /* ---------- de onde vêm as conversas ---------- */
  function apiBase() {
    var daPagina = "";
    try { daPagina = new URLSearchParams(window.location.search).get("api") || ""; } catch (erro) { daPagina = ""; }
    var base = String(daPagina || API_BASE || "").replace(/\/+$/, "");
    return /^https?:\/\//.test(base) ? base : "";
  }
  function aoVivo() { return !!app.api; }
  function todas() { return app.dados && Array.isArray(app.dados.conversas) ? app.dados.conversas.filter(function (c) { return c && Array.isArray(c.passos); }) : []; }
  function conversasDo(momento) { return todas().filter(function (c) { return c.momento === momento; }); }
  function conversaPorId(id) { return todas().filter(function (c) { return c.id === id; })[0] || null; }
  function conversaDoReplay() { return todas().filter(function (c) { return c.replay && Array.isArray(c.replay.dias) && c.replay.dias.length; })[0] || null; }
  function respostasDoMotor() { var o = window.ORBITA_RESPOSTAS; return o && typeof o === "object" ? (o.respostas && typeof o.respostas === "object" ? o.respostas : o) : {}; }

  /* ---------- os avisos do topo e o modo ---------- */
  function desenharAvisos() {
    var el = $("avisoDoModo");
    el.innerHTML = app.avisos.map(function (a) { return "<p>" + ic("alerta") + "<span>" + esc(a) + "</span></p>"; }).join("");
    el.hidden = !app.avisos.length;
  }
  function avisar(texto) { if (app.avisos.indexOf(texto) < 0) app.avisos.push(texto); desenharAvisos(); }
  function desenharModo() {
    var el = $("modo"), vivo = aoVivo();
    el.className = "modo " + (vivo ? "vivo" : "guardadas");
    el.textContent = t(vivo ? "modo.aoVivo" : "modo.guardadas");
    el.title = t(vivo ? "modo.explicaAoVivo" : "modo.explicaGuardadas");
  }

  /* ---------- os três momentos ---------- */
  function desenharMomentos() {
    $("momentos").setAttribute("aria-label", t("momentos.rotulo"));
    $("momentos").innerHTML = MOMENTOS.map(function (m) {
      var semConversa = !aoVivo() && todas().length > 0 && !conversasDo(m).length, escolhido = m === app.momento;   // há conversas, mas não deste momento
      return '<button class="momento' + (semConversa ? " adiante" : "") + '" role="tab" id="momento-' + m + '" aria-controls="painelDoMomento" data-momento="' + m + '" aria-selected="' + escolhido + '" tabindex="' + (escolhido ? "0" : "-1") + '">' +
        '<span class="quando">' + esc(t("momentos." + m + ".quando")) + '</span><strong class="pergunta">' + esc(t("momentos." + m + ".pergunta")) + "</strong>" +
        (semConversa ? '<span class="estado">' + esc(t("momentos.proximo")) + "</span>" : "") + "</button>";
    }).join("");
  }
  function marcarMomento() {
    Array.prototype.forEach.call(document.querySelectorAll(".momento"), function (b) {
      var escolhido = b.getAttribute("data-momento") === app.momento;
      b.setAttribute("aria-selected", escolhido); b.tabIndex = escolhido ? 0 : -1;
    });
    $("painelDoMomento").setAttribute("aria-labelledby", "momento-" + app.momento);
  }
  function desenharOutras() {
    var el = $("outras"), lista = aoVivo() ? [] : conversasDo(app.momento), atual = conversaPorId(app.idDaConversa), html = "";
    if (lista.length > 1) {
      html += '<div class="fichas" role="group" aria-label="' + esc(t("conversa.escolha")) + '">' + lista.map(function (c) {
        return '<button class="ficha-de-conversa" data-acao="abrir-conversa" data-id="' + esc(c.id) + '" aria-pressed="' + (c.id === app.idDaConversa) + '">' + esc(c.titulo || c.id) + "</button>";
      }).join("") + "</div>";
    }
    var ultima = conversa.ultimaSaida();      // ao vivo, cada resposta diz de quem é o texto; nas guardadas, a conversa diz
    var de = aoVivo() ? (ultima && ultima.texto_de) || "" : atual ? atual.texto_de : "";
    if (de && t("conversa.textoDe." + de) !== "conversa.textoDe." + de) html += '<p class="texto-de">' + esc(t("conversa.textoDe." + de)) + "</p>";
    el.innerHTML = html; el.hidden = !html;
  }
  function abrirConversa(c) {
    app.idDaConversa = c ? c.id : ""; app.corrigindo = false;
    montarReplay(c && c.replay ? c.replay : null);      // o replay da conversa aberta, ou o guardado; nunca o que sobrou de outra conversa
    conversa.abrirGuardada(c, app.momento);
    if (!c) $("compositor").innerHTML = '<p class="proximo-passo">' + esc(t(todas().length ? "momentos.proximoTexto" : "modo.semConversas")) + "</p>";
  }
  function escolherMomento(m) {
    app.momento = m; app.corrigindo = false; marcarMomento();
    if (aoVivo()) { app.idDaConversa = ""; montarReplay(null); conversa.abrirAoVivo(app.api, m); }
    else abrirConversa(conversasDo(m)[0] || null);
  }

  /* ---------- a mesa: a ficha e a comparação ---------- */
  function desenharMesa() {
    var s = conversa.ultimaSaida(), vivo = conversa.estado.modo === "ao_vivo", html;
    if (!s || !s.ficha) html = C.ficha(null);
    else html = C.ficha(s.ficha, { podeAgir: vivo || conversa.proximaGuardada() !== null, aoVivo: vivo, corrigindo: app.corrigindo });
    if (s && Array.isArray(s.comparacao) && s.comparacao.length && !(s.ficha && s.ficha.confirmada === false)) {
      html += C.comparacao(s.comparacao, s.ficha ? s.ficha.preocupacao : "", s.aviso);
    }
    $("mesa").innerHTML = html;
    $("mesa").classList.toggle("com-comparacao", html.indexOf('id="comparacao"') >= 0);
  }

  /* ---------- o replay ---------- */
  function montarReplay(replay) {
    var c = conversaDoReplay(), el = $("prova");
    replay = replay || (c ? c.replay : null);
    if (!replay || !Array.isArray(replay.dias) || !replay.dias.length) { el.hidden = true; $("paraAProva").hidden = true; return; }
    // O mesmo replay pode chegar de novo dentro de uma resposta: se é o que já está na tela, fica como está (não volta ao começo).
    var na = app.replayNaTela;
    if (na && (na === replay || (na.safra === replay.safra && na.cidade_id === replay.cidade_id && na.terra === replay.terra && na.dias.length === replay.dias.length &&
        (na.rotacao || {}).id === (replay.rotacao || {}).id))) return;
    app.replayNaTela = replay; el.hidden = false;
    $("paraAProva").hidden = false;
    $("paraAProva").firstElementChild.innerHTML = esc(t("momentos.prova", { safra: replay.safra || "" })) + ic("seta");
    var cidade = t("ficha.cidades." + replay.cidade_id);
    window.ORBITA_REPLAY.montar(el, replay, cidade === "ficha.cidades." + replay.cidade_id ? "" : cidade);
  }

  /* ---------- a leitura do agrônomo ---------- */
  function desenharAgronomo() {
    var el = $("leituraAgronomo"), R = respostasDoMotor(), terras = ["pouca", "media", "muita"].filter(function (k) { return R[k]; });
    var topo = '<header class="agro-topo"><h1>' + esc(t("agronomo.titulo")) + "</h1><p>" + esc(t("agronomo.texto")) + "</p>";
    if (!terras.length || !window.ORBITA_ADAPTAR || !window.ORBITA_RESULTADO) { el.innerHTML = topo + '<p class="nota">' + esc(t("agronomo.sem")) + "</p></header>"; return; }
    var s = conversa.ultimaSaida(), daFicha = s && s.ficha ? s.ficha.terra : "";
    var terra = terras.indexOf(app.terraDoAgronomo) >= 0 ? app.terraDoAgronomo : terras.indexOf(daFicha) >= 0 ? daFicha : terras.indexOf("media") >= 0 ? "media" : terras[0];
    app.terraDoAgronomo = terra;
    var v = window.ORBITA_ADAPTAR(R[terra], { complementos: window.ORBITA_COMPLEMENTOS, guardada: R[terra] });
    app.respostaDoAgronomo = R[terra];
    el.innerHTML = topo + '<p class="nota">' + esc(t("agronomo.nota")) + '</p><div class="agro-acoes"><div class="segmento" role="group" aria-label="' + esc(t("agronomo.terra")) + '"><span>' + esc(t("agronomo.terra")) + "</span>" +
      terras.map(function (k) { return '<button data-acao="terra-do-agronomo" data-terra="' + k + '" aria-pressed="' + (k === terra) + '">' + esc(String(t("ficha.terras." + k)).replace(/\s*\(.*\)\s*$/, "")) + "</button>"; }).join("") +
      '</div><button class="botao" data-acao="voltar-produtor">' + esc(t("agronomo.voltar")) + "</button></div></header>" + window.ORBITA_RESULTADO.agronomo(v, window.ORBITA_VALIDACAO);
  }
  function baixarResposta() {
    if (!app.respostaDoAgronomo) return;
    var endereco = URL.createObjectURL(new Blob([JSON.stringify(app.respostaDoAgronomo, null, 2)], { type: "application/json" }));
    var a = document.createElement("a"); a.href = endereco; a.download = "orbita-rural-resposta-" + app.terraDoAgronomo + ".json";
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(function () { URL.revokeObjectURL(endereco); }, 1000);
  }
  function filtrarParametros(botao) {
    var so = botao.getAttribute("data-filtro") === "hipotese";
    Array.prototype.forEach.call(botao.parentNode.querySelectorAll("button"), function (b) { b.classList.toggle("active", b === botao); });
    Array.prototype.forEach.call(document.querySelectorAll("#parametrosBox tbody tr"), function (tr) { tr.hidden = so && tr.getAttribute("data-etiqueta") === "publicado"; });
  }

  /* ---------- as duas leituras ---------- */
  function abrirLeitura(qual, focar) {
    var agro = qual === "agronomo";
    $("abaProdutor").setAttribute("aria-selected", !agro); $("abaProdutor").tabIndex = agro ? -1 : 0;
    $("abaAgronomo").setAttribute("aria-selected", agro); $("abaAgronomo").tabIndex = agro ? 0 : -1;
    $("leituraProdutor").hidden = agro; $("leituraAgronomo").hidden = !agro;
    document.body.classList.toggle("lendo-agronomo", agro);
    if (agro) { window.ORBITA_REPLAY.parar(); desenharAgronomo(); }
    if (focar) { window.scrollTo(0, 0); $(agro ? "abaAgronomo" : "abaProdutor").focus(); }
  }
  function irPara(id) {
    var el = $(id); if (!el) return;
    var calmo = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollIntoView({ block: "start", behavior: calmo ? "auto" : "smooth" });
    if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "-1");
    el.focus({ preventScroll: true });
  }

  /* ---------- os cliques ---------- */
  var ACOES = {
    "dizer-proxima": function () { conversa.dizer(); },
    "recomecar": function () { abrirConversa(conversaPorId(app.idDaConversa)); },
    "abrir-conversa": function (b) { abrirConversa(conversaPorId(b.getAttribute("data-id"))); },
    "usar-sugestao": function (b) { var campo = $("campoDaFala"); if (campo) { campo.value = b.getAttribute("data-texto") || ""; campo.focus(); } },
    "confirmar-ficha": function () { conversa.dizer(t("ficha.confirmarFala")); },
    "corrigir-ficha": function () { app.corrigindo = true; desenharMesa(); var f = $("correcao"); if (f) f.querySelector("select, input").focus(); },
    "cancelar-correcao": function () { app.corrigindo = false; desenharMesa(); },
    "abrir-agronomo": function () { abrirLeitura("agronomo", true); },
    "voltar-produtor": function () { abrirLeitura("produtor", true); },
    "terra-do-agronomo": function (b) { app.terraDoAgronomo = b.getAttribute("data-terra"); desenharAgronomo(); },
    "baixar": baixarResposta,
    "ir-comparacao": function () { irPara("comparacao"); },
    "ir-ficha": function () { irPara("ficha"); },
    "ir-replay": function () { irPara("prova"); }
  };
  document.addEventListener("click", function (ev) {
    var alvo = ev.target instanceof Element ? ev.target : null; if (!alvo) return;
    var momento = alvo.closest(".momento"); if (momento) { escolherMomento(momento.getAttribute("data-momento")); return; }
    var leitura = alvo.closest("[data-leitura]"); if (leitura) { abrirLeitura(leitura.getAttribute("data-leitura")); return; }
    var filtro = alvo.closest("[data-filtro]"); if (filtro) { filtrarParametros(filtro); return; }
    var b = alvo.closest("[data-acao]"); if (b && ACOES[b.getAttribute("data-acao")]) { ev.preventDefault(); ACOES[b.getAttribute("data-acao")](b); }
  });
  document.addEventListener("submit", function (ev) {
    var f = ev.target;
    if (f.id === "formDaFala") { ev.preventDefault(); var campo = $("campoDaFala"); if (campo && campo.value.trim()) conversa.dizer(campo.value); }
    else if (f.id === "correcao") { ev.preventDefault(); app.corrigindo = false; conversa.dizer(C.falaDaCorrecao(f)); }
  });
  document.addEventListener("keydown", function (ev) {
    var alvo = ev.target instanceof Element ? ev.target : null; if (!alvo) return;
    if (alvo.id === "campoDaFala" && ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); if (alvo.value.trim()) conversa.dizer(alvo.value); return; }
    // As setas andam entre as abas (as duas leituras e os três momentos).
    if ((ev.key === "ArrowRight" || ev.key === "ArrowLeft") && alvo.getAttribute("role") === "tab") {
      var abas = Array.prototype.slice.call(alvo.parentNode.querySelectorAll('[role="tab"]')), i = abas.indexOf(alvo);
      var outra = abas[(i + (ev.key === "ArrowRight" ? 1 : abas.length - 1)) % abas.length];
      ev.preventDefault(); outra.focus(); outra.click();
    }
  });

  /* ---------- o começo ---------- */
  function porOsTextos() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-t]"), function (el) { el.textContent = t(el.getAttribute("data-t")); });
    $("abaProdutor").textContent = t("leituras.produtor"); $("abaAgronomo").textContent = t("leituras.agronomo");
    $("leituras").setAttribute("aria-label", t("leituras.rotulo"));
  }
  function comecar() {
    app.dados = window.ORBITA_CONVERSAS && Array.isArray(window.ORBITA_CONVERSAS.conversas) ? window.ORBITA_CONVERSAS : null;
    app.api = apiBase();
    conversa = window.ORBITA_CONVERSA.criar($("falas"), $("compositor"), {
      aoResponder: function (saida) {
        app.corrigindo = false;
        $("anuncio").textContent = t("conversa.agente") + ": " + String(saida.resposta || "");      // para o leitor de tela, só a resposta nova
        if (saida.replay) montarReplay(saida.replay);      // ao vivo, o agente pode mandar o replay junto da resposta
        if (aoVivo() && MOMENTOS.indexOf(saida.momento) >= 0 && saida.momento !== app.momento) { app.momento = saida.momento; marcarMomento(); }
      },
      aoCair: function (motivo) {
        app.api = "";
        avisar(t("modo.caiu", { motivo: t("modo." + motivo) }));
        desenharModo(); desenharMomentos(); escolherMomento(app.momento);
      },
      aoMudar: function () { desenharMesa(); desenharOutras(); }
    });
    if (!aoVivo() && !todas().length) avisar(t("modo.semConversas"));
    desenharModo(); desenharMomentos(); montarReplay(); escolherMomento("antes");
  }
  function carregarEComecar() {
    try { porOsTextos(); comecar(); }
    finally { document.documentElement.classList.remove("montando"); }      // a página aparece já montada (ver o index.html)
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", carregarEComecar); else carregarEComecar();
})();
