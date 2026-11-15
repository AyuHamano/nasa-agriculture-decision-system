/* Gerado com IA (Claude). */
/* De onde a tela tira os números: da API do motor (o endereço vem de "?api=..." no fim do endereço da página, ou de
   API_BASE em js/textos.js) e, quando ela não responde, dos dados guardados em dados/ (gerados pelo gerar-dados.py).
   A tela não faz conta: mostra o que o motor devolve. Os arquivos guardados só são baixados quando fazem falta. */
(function () {
  "use strict";

  var ROTAS = { painel: "/lavoura-hoje", ensaio: "/recomendacao", replay: "/replay", registro: "/registro" };
  var CULTURAS = { soja_milho_pousio: ["soja", "milho", "pousio"], soja_milho_braquiaria: ["soja", "milho", "braquiaria"], soja_sorgo_pousio: ["soja", "sorgo", "pousio"] };

  function base() {
    var daPagina = "";
    try { daPagina = new URLSearchParams(window.location.search).get("api") || ""; } catch (erro) { daPagina = ""; }
    var b = String(daPagina || (typeof API_BASE === "string" ? API_BASE : "") || "").replace(/\/+$/, "");
    return /^https?:\/\//.test(b) ? b : "";
  }
  var D = { api: base(), ia: false, culturas: CULTURAS };

  function comPrazo(ms) {
    var c = typeof AbortController === "function" ? new AbortController() : null;
    return { sinal: c ? c.signal : undefined, relogio: c ? setTimeout(function () { c.abort(); }, ms) : 0 };
  }
  function lerResposta(r) {
    return r.json().catch(function () { return null; }).then(function (j) {
      if (!r.ok || j === null) { var e = new Error((j && j.erro) || "erro_" + r.status); e.codigo = r.status; e.frase = (j && j.erro) || ""; throw e; }
      return j;
    });
  }
  function post(rota, corpo, ms) {
    if (!D.api) return Promise.reject(new Error("sem_api"));
    var p = comPrazo(ms || 15000);
    return fetch(D.api + rota, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo), signal: p.sinal })
      .then(lerResposta).then(function (j) { clearTimeout(p.relogio); return j; }, function (e) { clearTimeout(p.relogio); throw e; });
  }
  // Pergunta à API se ela está de pé e se a IA do assistente está ligada. Sem resposta, a tela segue só com os guardados.
  function saude() {
    if (!D.api) return Promise.resolve(false);
    var p = comPrazo(6000);
    return fetch(D.api + "/saude", { signal: p.sinal }).then(lerResposta).then(function (j) {
      clearTimeout(p.relogio); D.ia = !!(j.ia_do_agente && j.ia_do_agente.ligada); return true;
    }, function () { clearTimeout(p.relogio); D.api = ""; D.ia = false; return false; });
  }

  var pedidos = {};
  function script(src) {
    if (!pedidos[src]) pedidos[src] = new Promise(function (ok, falhou) {
      var s = document.createElement("script"); s.src = src;
      s.onload = function () { ok(true); }; s.onerror = function () { delete pedidos[src]; falhou(new Error("sem_arquivo")); };
      document.head.appendChild(s);
    });
    return pedidos[src];
  }
  function emOrdem(lista) { return lista.reduce(function (antes, src) { return antes.then(function () { return script(src); }); }, Promise.resolve()); }

  function pedido(l, safra) {
    var p = { cidade_id: l.cidade_id, rotacao_atual: CULTURAS[l.rotacao_id], terra: l.terra };
    if (l.plantio_da_soja) p.plantio_da_soja = l.plantio_da_soja;
    if (safra) p.safra = safra;
    return p;
  }
  // Os guardados valem para a soja no dia de costume (15/10); o registro e a safra dia a dia, para a terra média.
  function guardado(tipo, l, safra) {
    var replay = tipo === "replay";
    return script(replay ? "dados/guardados-replay.js" : "dados/guardados.js").then(function () {
      var g = (replay ? window.ORBITA_GUARDADOS_REPLAY : window.ORBITA_GUARDADOS) || {};
      var no = ((g[tipo] || {})[l.cidade_id] || {})[l.rotacao_id], d = null, safras = null;
      if (no && replay) d = no;
      else if (no && tipo === "registro") { safras = Object.keys(no); d = no[safra] || no[safras[0]]; }
      else if (no) d = no[l.terra] || no.media;
      if (!d) throw new Error("sem_guardado");
      return { dados: d, reserva: true, gerado_em: g.gerado_em || "", safras: safras };
    });
  }
  // A safra dia a dia e o registro têm rota própria só nas versões mais novas da API: se a rota não respondeu uma
  // vez, a tela não insiste nela até a página ser aberta de novo (o painel e o ensaio tentam sempre).
  var semRota = {};
  function buscar(tipo, l, safra) {
    if (semRota[tipo]) return guardado(tipo, l, safra);
    return post(ROTAS[tipo], pedido(l, safra)).then(function (d) { return { dados: d, reserva: false }; }, function () {
      if (tipo === "replay" || tipo === "registro") semRota[tipo] = true;
      return guardado(tipo, l, safra);
    });
  }

  D.post = post; D.saude = saude; D.buscar = buscar; D.script = script; D.emOrdem = emOrdem;
  window.ORBITA_DADOS = D;
})();
