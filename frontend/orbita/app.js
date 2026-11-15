/* Gerado com IA (Claude). */
/* Liga as peças do aplicativo do produtor: a entrada (o assistente monta a ficha da lavoura, por toque ou por texto),
   a lavoura guardada no aparelho, as três telas (Hoje, Ensaiar, Registrar), o ano ruim dia a dia, o assistente à mão
   em qualquer tela e a leitura do agrônomo, no rodapé. A tela não faz conta: mostra o que o motor devolve (js/dados.js). */
(function () {
  "use strict";

  var D = window.ORBITA_DADOS, T = window.ORBITA_TELAS, esc = T.esc, ic = T.ic;
  function $(id) { return document.getElementById(id); }
  var CHAVE = "orbita.lavoura.v1", CHAVE_SAFRAS = "orbita.safras.v1";
  var TELAS = ["hoje", "ensaiar", "registrar", "agronomo"];
  var CAMPOS = ["cidade_id", "rotacao_id", "plantio_da_soja", "terra"];
  var PERGUNTAS = { cidade_id: "Onde fica a sua lavoura?", rotacao_id: "Qual é o seu ciclo de plantio hoje?", plantio_da_soja: "Quando você plantou, ou vai plantar, a soja desta safra?", terra: "Como é a sua terra?" };
  var NOMES = { cidade_id: "Cidade", rotacao_id: "O que planta", plantio_da_soja: "Plantio da soja", terra: "A terra" };
  var MOMENTO = { hoje: "durante", ensaiar: "antes", registrar: "depois" };
  var SUGESTOES = {
    hoje: ["Como está a água da minha lavoura?", "O que eu devo olhar esta semana?"],
    ensaiar: ["Vale trocar o milho pelo sorgo?", "Como foi a pior safra?"],
    registrar: ["O que a última safra mostrou?", "Como foi a pior safra?"]
  };
  var APOIO = { conta: "Tirado da conta da sua lavoura.", dados_do_lugar: "Tirado dos dados da NASA do lugar.", conhecimento_geral: "Conhecimento geral: a conta não mede este assunto." };
  var SEM_ASSISTENTE = "O assistente está sem conexão agora. O painel, o ensaio e o registro seguem funcionando.";
  var app = { lavoura: null, tela: "", vez: 0, cache: {}, safra: "", ensaio: null, registro: null, pronto: null, terraDoAgronomo: "", respostaDoAgronomo: null };
  var en = null;                                                    // a entrada: a conversa que monta a ficha
  var ag = { estado: null, confirmada: false, falas: [], ocupado: false };   // o assistente à mão

  function ler(chave) { try { return JSON.parse(window.localStorage.getItem(chave) || "null"); } catch (erro) { return null; } }
  function gravar(chave, valor) { try { if (valor === null) window.localStorage.removeItem(chave); else window.localStorage.setItem(chave, JSON.stringify(valor)); return true; } catch (erro) { return false; } }
  function valida(l) { return !!(l && T.CIDADES[l.cidade_id] && T.ROTACOES[l.rotacao_id] && T.TERRAS[l.terra] && /^\d{4}-(09|10|11|12)-\d{2}$/.test(l.plantio_da_soja || "")); }
  function norm(s) { return String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ").trim(); }
  function anoDoPlantio() { var h = new Date(); return h.getMonth() < 7 ? h.getFullYear() - 1 : h.getFullYear(); }
  function doisDigitos(n) { return (n < 10 ? "0" : "") + n; }

  /* ---------- welcome screen: logo, a short text and a start button, shown before the assistant chat ---------- */
  // Hides the app shell (tabs, farm button, "Perguntar" button, cached-data note) and sets the body class of the screen being opened.
  function leaveApp(bodyClass) {
    app.tela = ""; app.vez += 1; fecharTudo();
    document.body.className = bodyClass;
    $("nave").hidden = true; $("botaoLavoura").hidden = true; $("perguntar").hidden = true; $("reserva").hidden = true;
  }
  function openWelcome() {
    leaveApp("on-welcome");
    $("conteudo").innerHTML = '<section class="o-welcome" aria-labelledby="welcomeTitle">' +
      '<h1 class="o-welcome-logo" id="welcomeTitle"><img src="marca/logo-verde-sem-lema.png" width="546" height="220" alt="Órbita Rural"></h1>' +
      '<p class="o-welcome-tagline">' + esc(t("rodape.lema")) + "</p>" +
      '<p class="o-welcome-text">' + esc(t("welcome.text")) + "</p>" +
      '<button type="button" class="o-bt" data-acao="start">' + esc(t("welcome.button")) + "</button></section>";
    window.scrollTo(0, 0);
  }

  /* ---------- a entrada: o assistente pergunta, o produtor toca ou escreve ---------- */
  function opcoes(campo) {
    if (campo === "cidade_id") return Object.keys(T.CIDADES).map(function (k) { return { v: k, n: T.CIDADES[k] }; });
    if (campo === "rotacao_id") return Object.keys(T.ROTACOES).map(function (k) { return { v: k, n: T.ROTACOES[k].nome }; });
    if (campo === "terra") return Object.keys(T.TERRAS).map(function (k) { return { v: k, n: T.TERRAS[k].nome, d: T.TERRAS[k].dica }; });
    var a = anoDoPlantio();
    return [["09", "Setembro"], ["10", "Outubro"], ["11", "Novembro"], ["12", "Dezembro"]].map(function (m) { return { v: a + "-" + m[0] + "-15", n: m[1], d: "dia 15" }; });
  }
  // A leitura simples do texto, sem IA: serve quando o assistente está sem conexão.
  function lerTexto(txt) {
    var s = norm(txt), achou = {}, m;
    if (/rio verde/.test(s)) achou.cidade_id = "rio_verde"; else if (/jatai/.test(s)) achou.cidade_id = "jatai"; else if (/silvania/.test(s)) achou.cidade_id = "silvania";
    if (/sorgo|milho|capim|braquiaria/.test(s)) achou.rotacao_id = T.idDaRotacao(s);
    if (/arenos|areia/.test(s)) achou.terra = "pouca"; else if (/argilos|barro/.test(s)) achou.terra = "muita"; else if (/\bmedia\b|mista/.test(s)) achou.terra = "media";
    if ((m = /\b(\d{1,2})\/(\d{1,2})\b/.exec(s)) && Number(m[2]) >= 9 && Number(m[2]) <= 12 && Number(m[1]) >= 1 && Number(m[1]) <= 31) achou.plantio_da_soja = anoDoPlantio() + "-" + doisDigitos(Number(m[2])) + "-" + doisDigitos(Number(m[1]));
    else if ((m = /setembro|outubro|novembro|dezembro/.exec(s))) achou.plantio_da_soja = anoDoPlantio() + "-" + { setembro: "09", outubro: "10", novembro: "11", dezembro: "12" }[m[0]] + "-15";
    return achou;
  }
  function falar(de, texto) { en.falas.push({ de: de, texto: texto }); }
  function faltando() { return CAMPOS.filter(function (c) { return !en.l[c]; })[0] || ""; }
  function perguntarOProximo() {
    en.campo = faltando(); en.outroDia = false;
    if (en.campo) falar("assistente", PERGUNTAS[en.campo]); else { en.campo = "ficha"; falar("assistente", "Anotei a sua lavoura. Está certo?"); }
    desenharEntrada(true);
  }
  var DITO = { cidade_id: "lugar_dito", rotacao_id: "rotacao_dita" };      // o que o produtor disse e a ficha guarda ao lado da cidade e da rotação da conta
  function escolher(campo, valor, nome) { en.l[campo] = valor; if (DITO[campo]) delete en.l[DITO[campo]]; falar("produtor", nome); perguntarOProximo(); }
  function anotar(achou, respostaDaIA) {
    var novos = CAMPOS.filter(function (c) { return achou[c] && achou[c] !== en.l[c]; });
    novos.forEach(function (c) { en.l[c] = achou[c]; });
    if (novos.length) falar("assistente", "Anotei: " + novos.map(function (c) { return T.valorDaFicha(c, en.l[c]); }).join(", ") + ".");
    else falar("assistente", respostaDaIA || "Não entendi. Toque numa das opções abaixo." + (D.ia ? "" : " O assistente está sem conexão agora."));
    en.campo = faltando(); en.outroDia = false;
    if (!en.campo) { en.campo = "ficha"; if (novos.length) falar("assistente", "Está certo?"); } else if (novos.length) falar("assistente", PERGUNTAS[en.campo]);
    desenharEntrada(true);
  }
  function escritaNaEntrada(txt) {
    txt = String(txt || "").trim(); if (!txt || en.ocupado) return;
    falar("produtor", txt);
    var exata = en.campo && en.campo !== "ficha" ? opcoes(en.campo).filter(function (o) { return norm(o.n) === norm(txt); })[0] : null;
    if (exata) { en.l[en.campo] = exata.v; perguntarOProximo(); return; }
    en.ocupado = true; desenharEntrada(true);
    app.pronto.then(function () {
      if (!D.api || !D.ia) throw new Error("sem_ia");
      return D.post("/agente", { estado: en.estado, texto: txt }, 120000);
    }).then(function (s) {
      var f = s.ficha || {}, antes = en.fichaDaIA || {}, achou = {};
      function mudou(c) { return f[c] && JSON.stringify(f[c]) !== JSON.stringify(antes[c]); }      // só o que ele disse agora: o toque de antes não é desfeito
      if (mudou("cidade_id") && T.CIDADES[f.cidade_id]) achou.cidade_id = f.cidade_id;
      if (mudou("rotacao_atual") && Array.isArray(f.rotacao_atual)) achou.rotacao_id = T.idDaRotacao(f.rotacao_atual);
      if (mudou("terra") && T.TERRAS[f.terra]) achou.terra = f.terra;
      if (mudou("plantio_da_soja") && /^\d{4}-(09|10|11|12)-\d{2}$/.test(f.plantio_da_soja)) achou.plantio_da_soja = f.plantio_da_soja;
      if (f.preocupacao) en.l.preocupacao = f.preocupacao;
      [["lugar_dito", "cidade_id"], ["rotacao_dita", "rotacao_atual"]].forEach(function (d) {      // o que ele disse com as palavras dele (o lugar fora da lista, a rotação)
        if (f[d[0]]) en.l[d[0]] = String(f[d[0]]); else if (mudou(d[1])) delete en.l[d[0]];
      });
      en.estado = s.estado || en.estado; en.fichaDaIA = f; en.ocupado = false; anotar(achou, s.resposta || "");
    }, function () { en.ocupado = false; anotar(lerTexto(txt), ""); });
  }
  function opcoesHtml(campo) {
    var h = opcoes(campo).map(function (o) {
      return '<button type="button" class="o-opcao" data-acao="opcao" data-campo="' + campo + '" data-valor="' + esc(o.v) + '" data-nome="' + esc(o.n) + '">' + esc(o.n) + (o.d ? "<small>" + esc(o.d) + "</small>" : "") + "</button>";
    }).join("");
    if (campo === "plantio_da_soja") {
      var a = anoDoPlantio();
      h += en.outroDia ? '<span class="o-dia"><input type="date" id="diaDoPlantio" min="' + a + '-09-01" max="' + a + '-12-31" value="' + a + '-10-15" aria-label="O dia do plantio da soja"><button type="button" class="o-opcao cheia" data-acao="usar-dia">Usar este dia</button></span>'
        : '<button type="button" class="o-opcao" data-acao="outro-dia">Escolher o dia</button>';
    }
    return '<div class="o-opcoes" role="group" aria-label="' + esc(PERGUNTAS[campo]) + '">' + h + "</div>" + (campo === "cidade_id" ? '<p class="o-legenda">Três cidades de Goiás.</p>' : "");
  }
  function valorNaFicha(l, c) { return c === "cidade_id" ? T.CIDADES[l[c]] : c === "rotacao_id" ? T.ROTACOES[l[c]].nome : c === "terra" ? T.TERRAS[l[c]].nome : T.dataPorExtenso(l[c]); }
  function fichaHtml(l, trocavel) {
    return "<dl>" + CAMPOS.map(function (c) {
      return '<div class="linha"><div><dt>' + NOMES[c] + "</dt><dd>" + esc(valorNaFicha(l, c)) + (DITO[c] && l[DITO[c]] ? '<small class="o-dito">Você disse: ' + esc(l[DITO[c]]) + "</small>" : "") + "</dd></div>" + (trocavel ? '<button type="button" class="o-trocar" data-acao="trocar-campo" data-campo="' + c + '">Trocar</button>' : "") + "</div>";
    }).join("") + "</dl>";
  }
  function desenharEntrada(descer) {
    var falas = en.falas.map(function (f) { return '<li class="o-fala ' + f.de + '">' + esc(f.texto) + "</li>"; }).join("") + (en.ocupado ? '<li class="o-fala assistente o-pensando" aria-label="O assistente está escrevendo"><i></i><i></i><i></i></li>' : "");
    var respostas = en.ocupado ? "" : en.campo === "ficha" ? '<div class="o-ficha">' + fichaHtml(en.l, true) + '<button type="button" class="o-bt" data-acao="confirmar-lavoura">' + ic("certo") + "Está certo, ver minha lavoura</button></div>" : en.campo ? opcoesHtml(en.campo) : "";
    $("conteudo").innerHTML = '<div class="o-entrada"><h1 class="so-leitor">Cadastre a sua lavoura</h1><ol class="o-chat" aria-live="polite">' + falas + '</ol><div class="o-respostas">' + respostas + "</div>" +
      '<form class="o-compor" id="formDaEntrada"><input type="text" id="campoDaEntrada" autocomplete="off" enterkeyhint="send" placeholder="Ou escreva aqui" aria-label="Escreva para o assistente"><button type="submit" aria-label="Enviar">' + ic("seta") + "</button></form></div>";
    if (descer) window.scrollTo(0, document.documentElement.scrollHeight);
  }
  function abrirEntrada() {
    en = { l: {}, falas: [], campo: "", ocupado: false, estado: null, fichaDaIA: null, outroDia: false };
    leaveApp("na-entrada");
    falar("assistente", "Olá! Sou o assistente do Órbita Rural. Acompanho a sua lavoura com os dados dos satélites da NASA.");
    en.campo = faltando(); falar("assistente", PERGUNTAS[en.campo]);
    desenharEntrada(false); window.scrollTo(0, 0);
  }
  function confirmarLavoura() {
    if (faltando()) return;
    app.lavoura = { cidade_id: en.l.cidade_id, rotacao_id: en.l.rotacao_id, terra: en.l.terra, plantio_da_soja: en.l.plantio_da_soja };
    ["preocupacao", "lugar_dito", "rotacao_dita"].forEach(function (k) { if (en.l[k]) app.lavoura[k] = en.l[k]; });
    gravar(CHAVE, app.lavoura); app.cache = {}; app.safra = ""; ag = { estado: null, confirmada: false, falas: [], ocupado: false };
    abrirApp("hoje");
  }

  /* ---------- o aplicativo: as três telas ---------- */
  function busca(tipo, safra) {
    var k = tipo + "|" + (safra || "");
    if (!app.cache[k]) app.cache[k] = D.buscar(tipo, app.lavoura, safra).then(function (r) { if (r.reserva) delete app.cache[k]; return r; }, function (e) { delete app.cache[k]; throw e; });
    return app.cache[k];
  }
  function mostrarReserva(r) {
    var el = $("reserva");
    if (!r || !r.reserva) { el.hidden = true; return; }
    el.textContent = "Dados guardados" + (r.gerado_em ? " em " + T.dataCurta(r.gerado_em) : "") + (/-10-15$/.test(app.lavoura.plantio_da_soja || "") ? "" : ", para a soja plantada em 15/10") + ".";
    el.hidden = false;
  }
  function marcarNave() {
    Array.prototype.forEach.call($("nave").querySelectorAll("a"), function (a) { if (a.getAttribute("data-tela") === app.tela) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
    document.body.classList.toggle("lendo-agronomo", app.tela === "agronomo");
  }
  function falhou(vez) {
    return function () {
      if (vez !== app.vez) return;
      $("conteudo").innerHTML = '<div class="o-tela estreita"><p class="o-nota">Não deu para buscar os dados agora. Confira a internet e tente de novo.</p><button type="button" class="o-bt claro" data-acao="tentar">Tentar de novo</button></div>';
    };
  }
  function colheitaGuardada(safra) { var l = app.lavoura; return (ler(CHAVE_SAFRAS) || {})[[l.cidade_id, l.rotacao_id, safra].join("|")] || null; }
  function desenharRegistro(recado) {
    var x = app.registro; if (!x) return;
    $("conteudo").innerHTML = T.registro(x.r.dados, app.lavoura, x.safras, x.safra, colheitaGuardada(x.safra), recado);
  }
  function mostrar(tela) {
    var vez = ++app.vez, main = $("conteudo"), l = app.lavoura;
    app.tela = tela; marcarNave(); fecharTudo();
    if (tela === "agronomo") { abrirAgronomo(vez); return; }
    main.innerHTML = T.esperando(); $("reserva").hidden = true; window.scrollTo(0, 0);
    if (tela === "hoje") busca("painel").then(function (r) { if (vez !== app.vez) return; main.innerHTML = T.painel(r.dados, l); mostrarReserva(r); }, falhou(vez));
    else if (tela === "ensaiar") busca("ensaio").then(function (r) { if (vez !== app.vez) return; app.ensaio = r.dados; main.innerHTML = T.ensaio(r.dados, l); mostrarReserva(r); }, falhou(vez));
    else busca("ensaio").then(function (e) {
      var d = e.dados || {}, safras = Object.keys((d.regra_dos_anos || {}).rendimento_por_safra_kg_ha || {}), ultima = (d.safra_2025_26 || {}).safra;
      if (ultima && safras.indexOf(ultima) < 0) safras.push(ultima);
      var safra = safras.indexOf(app.safra) >= 0 ? app.safra : (ultima || safras[safras.length - 1] || "");
      return busca("registro", safra).then(function (r) {
        if (r.reserva && r.safras) safras = r.safras.slice();      // sem a API, só as safras guardadas
        return { r: r, safras: safras.sort().reverse(), safra: (r.dados && r.dados.safra) || safra };
      });
    }).then(function (x) { if (vez !== app.vez) return; app.safra = x.safra; app.registro = x; desenharRegistro(""); mostrarReserva(x.r); }, falhou(vez));
  }
  function rota() {
    if (!app.lavoura) return;
    var h = window.location.hash.replace(/^#/, "");
    mostrar(TELAS.indexOf(h) >= 0 ? h : "hoje");
  }
  function irPara(tela) { if (window.location.hash.replace(/^#/, "") === tela) mostrar(tela); else window.location.hash = tela; }
  function abrirApp(tela) {
    document.body.className = "no-app";
    $("nave").hidden = false; $("botaoLavoura").hidden = false; $("perguntar").hidden = false;
    $("botaoLavoura").innerHTML = ic("pino") + "<span>" + esc(T.CIDADES[app.lavoura.cidade_id]) + "</span>";
    if (tela) irPara(tela); else rota();
  }
  function guardarColheita(form) {
    var x = app.registro, l = app.lavoura, valores = {}, algum = false, acimaDoLimite = false;
    Array.prototype.forEach.call(form.querySelectorAll("input[name]"), function (c) { var n = Number(String(c.value).replace(",", ".")); if (c.value !== "" && isFinite(n) && n > 9999) acimaDoLimite = true; else if (c.value !== "" && isFinite(n) && n > 0) { valores[c.name] = n; algum = true; } });
    if (acimaDoLimite) { form.querySelector(".o-recado").textContent = "O limite é 9999 sacas por hectare."; return; }
    if (!algum) { form.querySelector(".o-recado").textContent = "Escreva quanto colheu, em sacas por hectare."; return; }
    var h = new Date(), todas = ler(CHAVE_SAFRAS) || {};
    valores.em = h.getFullYear() + "-" + doisDigitos(h.getMonth() + 1) + "-" + doisDigitos(h.getDate());
    todas[[l.cidade_id, l.rotacao_id, x.safra].join("|")] = valores;
    desenharRegistro(gravar(CHAVE_SAFRAS, todas) ? "Safra " + x.safra + " guardada neste aparelho." : "Este aparelho não deixou guardar a safra.");
  }

  /* ---------- o ano ruim, dia a dia (atrás do botão do ensaio) ---------- */
  function abrirAnoRuim() {
    var safra = ((app.ensaio || {}).regra_dos_anos || {}).pior_ano || "2015-16", vez = app.vez, el = $("prova");
    $("folha").hidden = false; document.body.classList.add("com-folha"); $("folhaNota").textContent = "";
    el.innerHTML = '<p class="o-espera">Buscando a safra…</p>'; $("folha").scrollTop = 0;
    busca("replay", safra).then(function (r) {
      if (vez !== app.vez || $("folha").hidden) return;
      window.ORBITA_REPLAY.montar(el, r.dados, T.CIDADES[app.lavoura.cidade_id]);
      $("folhaNota").textContent = r.reserva ? "Dados guardados" + (r.gerado_em ? " em " + T.dataCurta(r.gerado_em) : "") + ", em terra média." : "";
    }, function () { el.innerHTML = '<p class="o-espera">Não deu para buscar a safra agora.</p>'; });
    $("fecharFolha").focus();
  }
  function fecharFolha() { if ($("folha").hidden) return; window.ORBITA_REPLAY.parar(); $("folha").hidden = true; $("prova").innerHTML = ""; document.body.classList.remove("com-folha"); }

  /* ---------- a lavoura guardada ---------- */
  function abrirLavoura() {
    $("janelaCorpo").innerHTML = fichaHtml(app.lavoura, false) + '<p class="o-legenda">A lavoura fica guardada neste aparelho.</p>';
    $("janela").hidden = false; $("fecharJanela").focus();
  }
  function trocarDeLavoura() {
    gravar(CHAVE, null); app.lavoura = null; app.cache = {}; app.safra = ""; app.ensaio = null; app.registro = null;
    ag = { estado: null, confirmada: false, falas: [], ocupado: false };
    try { window.history.replaceState(null, "", window.location.pathname + window.location.search); } catch (erro) { /* aberta como arquivo */ }
    abrirEntrada();
  }
  function fecharTudo() { fecharFolha(); $("janela").hidden = true; $("gaveta").hidden = true; document.body.classList.remove("com-folha"); }

  /* ---------- o assistente à mão ---------- */
  function estadoDaFicha(pergunta) {
    var l = app.lavoura;      // a ficha que o produtor confirmou na entrada; o "sim" dela vai no texto, e o servidor põe o selo
    var ficha = { cidade_id: l.cidade_id, rotacao_atual: D.culturas[l.rotacao_id], terra: l.terra, plantio_da_soja: l.plantio_da_soja || null, preocupacao: l.preocupacao || "agua", confirmada: false };
    if (l.lugar_dito) ficha.lugar_dito = l.lugar_dito;
    if (l.rotacao_dita) ficha.rotacao_dita = l.rotacao_dita;
    return { v: 1, ficha: ficha,
             selo: null, pergunta: pergunta, momento: MOMENTO[app.tela] || "durante", falas: [] };
  }
  function horaDaConversa() { return new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" }).format(new Date()); }
  function htmlDaFala(f) {
    var produtor = f.de === "produtor", rodape = '<span class="o-fala-rodape"><time>' + esc(f.hora || horaDaConversa()) + "</time>" + (produtor ? '<span class="o-fala-lida" aria-label="Entregue e lida">✓✓</span>' : "") + "</span>";
    return '<li class="o-fala ' + esc(f.de) + '"><span class="o-fala-texto">' + esc(f.texto) + "</span>" + (f.apoio ? '<small class="o-apoio">' + esc(f.apoio) + "</small>" : "") + (f.usou ? '<small class="o-usou">' + esc(f.usou) + "</small>" : "") + rodape + "</li>";
  }
  function respostaGuardada(texto) {
    var s = norm(texto), aviso = "Converse com um profissional de agronomia antes de decidir.";
    function pronta(resposta, origem) { return { simulada: true, resposta: resposta, apoio: origem || "Demonstração com os dados guardados do Órbita Rural." }; }
    if (/^(oi|ola|bom dia|boa tarde|boa noite)\b/.test(s)) return Promise.resolve(pronta("Olá! Sou o assistente do Órbita Rural. Posso explicar como está a água, o calor e a cobertura da terra, comparar rotações ou resumir uma safra. O que você quer saber?"));
    if (/ajuda|o que voce faz|o que posso perguntar/.test(s)) return Promise.resolve(pronta("Você pode perguntar, por exemplo:\n\n• Como está a água da minha lavoura?\n• Houve calor forte?\n• Vale trocar o milho pelo sorgo?\n• O que a última safra mostrou?"));

    if (/ultima safra|safra mostrou|registro|colheita|depois de colher/.test(s)) {
      return busca("registro", app.safra).then(function (r) {
        var d = r.dados || {};
        return pronta((d.frase || "O registro desta safra não está disponível agora.") + (d.aviso ? "\n\n" + d.aviso : ""), r.reserva ? "Resposta com o registro guardado desta lavoura." : "Resposta tirada da conta atual da lavoura.");
      });
    }

    if (/trocar|comparar|rotac|plantar|milho|sorgo|braquiaria|capim|ano ruim/.test(s)) {
      return busca("ensaio").then(function (r) {
        var d = r.dados || {}, lista = Array.isArray(d.comparacao_das_rotacoes) ? d.comparacao_das_rotacoes : [];
        if (!lista.length) return pronta("A comparação das rotações não está disponível agora.");
        var local = T.CIDADES[app.lavoura.cidade_id] || "a sua região";
        var partes = lista.map(function (c) {
          var nome = c.apelido || c.nome || c.id, marca = c.de_hoje ? "Sua rotação" : "Alternativa";
          var beneficio = c.beneficio || c.evidencia || "Veja os números no ensaio.";
          var risco = c.risco_curto || c.risco || "O manejo precisa ser conferido em campo.";
          return marca + " — " + nome + ": " + beneficio + " Risco: " + risco;
        });
        return pronta("Comparação simulada para " + local + ":\n\n" + partes.join("\n\n") + "\n\n" + (d.aviso || aviso), r.reserva ? "Resposta com o ensaio guardado desta lavoura." : "Resposta tirada da conta atual da lavoura.");
      });
    }

    return busca("painel").then(function (r) {
      var d = r.dados || {}, itens = Array.isArray(d.itens) ? d.itens : [], id = "";
      if (/calor|temperatura/.test(s)) id = "calor";
      else if (/verde|satelite|imagem/.test(s)) id = "verde";
      else if (/cobertura|terra sem|erosao|planta viva/.test(s)) id = "terra_coberta";
      else if (/sede|sem chuva|vai faltar/.test(s)) id = "aviso_de_sede";
      else if (/fase|plantio|cultura/.test(s)) id = "fase";
      else if (/agua|chuva|seca|lavoura|semana|hoje/.test(s)) id = "agua";
      var item = itens.filter(function (x) { return x.id === id; })[0];
      var resposta = item && item.frase ? item.frase : d.frase;
      if (!resposta) resposta = "Posso responder sobre água, calor, cobertura da terra, comparação de rotações e registro da safra. Escreva uma dessas perguntas para testar.";
      return pronta(resposta + "\n\n" + (d.aviso || aviso), r.reserva ? "Resposta com os dados guardados desta lavoura." : "Resposta tirada da conta atual da lavoura.");
    }).catch(function () {
      return pronta("Estou no modo de demonstração. Posso conversar sobre água, calor, cobertura da terra, rotações e histórico da safra. Tente perguntar: “Como está a água da minha lavoura?”.");
    });
  }
  function desenharGaveta() {
    var falas = ag.falas.length ? ag.falas : [{ de: "assistente", texto: "Olá! Sou o assistente do Órbita Rural. Pergunte sobre a sua lavoura, a água, o calor ou as rotações. Eu respondo com a conta disponível e os dados guardados.", hora: horaDaConversa() }];
    $("chatDoAssistente").innerHTML = falas.map(htmlDaFala).join("") +
      (ag.ocupado ? '<li class="o-fala assistente o-pensando" aria-label="O assistente está escrevendo"><i></i><i></i><i></i></li>' : "");
    $("sugestoes").innerHTML = ag.falas.length ? "" : (SUGESTOES[app.tela] || SUGESTOES.hoje).map(function (s) { return '<button type="button" class="o-opcao" data-acao="sugestao" data-texto="' + esc(s) + '">' + esc(s) + "</button>"; }).join("");
    $("presencaDoAssistente").textContent = ag.ocupado ? "digitando…" : D.api && D.ia ? "online · conectado à API" : "online · demonstração local";
    $("modoDoAssistente").textContent = D.api && D.ia ? "Conectado ao motor do Órbita Rural" : "Modo demonstração · dados guardados";
    $("campoDoAssistente").disabled = ag.ocupado; $("formDoAssistente").querySelector("button[type=submit]").disabled = ag.ocupado;
    var rolo = $("roloDoAssistente"); rolo.scrollTop = rolo.scrollHeight;
  }
  function abrirGaveta() { $("gaveta").hidden = false; document.body.classList.add("com-folha"); desenharGaveta(); $("campoDoAssistente").focus(); }
  function fecharGaveta() { $("gaveta").hidden = true; document.body.classList.remove("com-folha"); $("perguntar").focus(); }
  function abrirChatbot() {
    var destino = "chatbot.html", api = "";
    try { api = new URLSearchParams(window.location.search).get("api") || ""; } catch (erro) { api = ""; }
    if (/^https?:\/\//.test(api)) destino += "?api=" + encodeURIComponent(api);
    window.location.assign(destino);
  }
  function oQueAContaUsou(f) {      // a ficha da conversa ficou diferente da guardada: uma linha diz o que a conta usou
    var l = app.lavoura, p = [];
    var rot = typeof f.rotacao_atual === "string" ? f.rotacao_atual : Object.keys(D.culturas).filter(function (k) { return String(D.culturas[k]) === String(f.rotacao_atual); })[0];
    if (T.ROTACOES[rot] && rot !== l.rotacao_id) p.push(T.ROTACOES[rot].nome.toLowerCase());
    if (f.plantio_da_soja && f.plantio_da_soja !== l.plantio_da_soja) p.push("a soja plantada em " + T.dataCurta(f.plantio_da_soja));
    if (T.TERRAS[f.terra] && f.terra !== l.terra) p.push("terra " + T.TERRAS[f.terra].nome.toLowerCase());
    if (T.CIDADES[f.cidade_id] && f.cidade_id !== l.cidade_id) p.push("o clima de " + T.CIDADES[f.cidade_id]);
    return p.length ? "Conta com " + p.join(", com ") + "." : "";
  }
  function perguntar(texto) {
    texto = String(texto || "").trim(); if (!texto || ag.ocupado) return;
    ag.falas.push({ de: "produtor", texto: texto, hora: horaDaConversa() }); ag.ocupado = true; desenharGaveta();
    function mandar(corpo, jaConfirmou) {
      return D.post("/agente", corpo, 120000).then(function (s) {
        var confirmada = !!(s.ficha && s.ficha.confirmada);
        // O produtor disse um fato da lavoura na pergunta e a ficha da conversa mudou (ou o servidor religou e o selo de
        // antes não vale): a tela confirma sozinha, uma vez só, com a ficha que o servidor devolveu e a pergunta dele.
        // A lavoura guardada no aparelho não muda; se ainda assim não confirmar, mostra o que veio e a conversa volta a ela.
        if (!confirmada && !jaConfirmou && s.estado && s.ficha && !(s.ficha.falta || []).length) { s.estado.pergunta = texto; return mandar({ estado: s.estado, texto: "sim" }, true); }
        ag.estado = confirmada ? s.estado : null; ag.confirmada = confirmada; return s;
      });
    }
    app.pronto.then(function () {
      if (!D.api || !D.ia) return respostaGuardada(texto);
      return mandar(ag.estado && ag.confirmada ? { estado: ag.estado, texto: texto } : { estado: estadoDaFicha(texto), texto: "sim" }, false);
    }).then(function (s) {
      ag.falas.push({ de: "assistente", texto: s.resposta || "", apoio: s.simulada ? s.apoio : APOIO[s.apoio] || "", usou: !s.simulada && s.apoio === "conta" && ag.confirmada ? oQueAContaUsou(s.ficha) : "", hora: horaDaConversa() });
    }, function (e) {
      return respostaGuardada(texto).then(function (s) {
        ag.falas.push({ de: "assistente", texto: s.resposta, apoio: "A API não respondeu; " + s.apoio.toLowerCase(), hora: horaDaConversa() });
      });
    }).then(function () { ag.ocupado = false; desenharGaveta(); $("campoDoAssistente").focus(); });
  }

  /* ---------- a leitura do agrônomo (o link do rodapé) ---------- */
  function respostasDoMotor() { var o = window.ORBITA_RESPOSTAS; return o && typeof o === "object" ? (o.respostas && typeof o.respostas === "object" ? o.respostas : o) : {}; }
  function desenharAgronomo() {
    var el = $("leituraAgronomo"); if (!el) return;
    var R = respostasDoMotor(), terras = ["pouca", "media", "muita"].filter(function (k) { return R[k]; });
    var topo = '<header class="agro-topo"><h1>' + esc(t("agronomo.titulo")) + "</h1><p>" + esc(t("agronomo.texto")) + "</p>";
    if (!terras.length || !window.ORBITA_ADAPTAR || !window.ORBITA_RESULTADO) { el.innerHTML = topo + '<p class="nota">' + esc(t("agronomo.sem")) + "</p></header>"; return; }
    var daFicha = app.lavoura ? app.lavoura.terra : "";
    var terra = terras.indexOf(app.terraDoAgronomo) >= 0 ? app.terraDoAgronomo : terras.indexOf(daFicha) >= 0 ? daFicha : terras.indexOf("media") >= 0 ? "media" : terras[0];
    app.terraDoAgronomo = terra; app.respostaDoAgronomo = R[terra];
    var v = window.ORBITA_ADAPTAR(R[terra], { complementos: window.ORBITA_COMPLEMENTOS, guardada: R[terra] });
    el.innerHTML = topo + '<p class="nota">' + esc(t("agronomo.nota")) + '</p><div class="agro-acoes"><div class="segmento" role="group" aria-label="' + esc(t("agronomo.terra")) + '"><span>' + esc(t("agronomo.terra")) + "</span>" +
      terras.map(function (k) { return '<button data-acao="terra-do-agronomo" data-terra="' + k + '" aria-pressed="' + (k === terra) + '">' + esc(String(t("ficha.terras." + k)).replace(/\s*\(.*\)\s*$/, "")) + "</button>"; }).join("") +
      '</div><button class="botao" data-acao="voltar-produtor">Voltar para a minha lavoura</button></div></header>' + window.ORBITA_RESULTADO.agronomo(v, window.ORBITA_VALIDACAO);
    window.ORBITA_RESULTADO.ajustar(el);
  }
  function abrirAgronomo(vez) {
    var main = $("conteudo"); main.innerHTML = T.esperando("Abrindo as contas…"); $("reserva").hidden = true; window.scrollTo(0, 0);
    D.emOrdem(["dados/respostas.js", "dados/complementos.js", "dados/validacao.js", "js/textos-agronomo.js", "js/adaptar.js", "js/resultado.js"]).then(function () {
      if (vez !== app.vez) return;
      main.innerHTML = '<section id="leituraAgronomo"></section>'; desenharAgronomo();
    }, function () { if (vez === app.vez) main.innerHTML = '<div class="o-tela estreita"><p class="o-nota">Não deu para abrir as contas agora.</p></div>'; });
  }
  var relogioDoAgronomo = 0;
  window.addEventListener("resize", function () {
    clearTimeout(relogioDoAgronomo);
    relogioDoAgronomo = setTimeout(function () { var el = $("leituraAgronomo"); if (el && app.respostaDoAgronomo && window.ORBITA_RESULTADO) window.ORBITA_RESULTADO.ajustar(el); }, 150);
  });
  function semPrioridades(o) {      // as notas de prioridade saíram do produto: o arquivo que se baixa não as leva
    if (Array.isArray(o)) return o.map(semPrioridades);
    if (o && typeof o === "object") { var s = {}; Object.keys(o).forEach(function (k) { if (k !== "prioridades") s[k] = semPrioridades(o[k]); }); return s; }
    return o;
  }
  function baixarResposta() {
    if (!app.respostaDoAgronomo) return;
    var endereco = URL.createObjectURL(new Blob([JSON.stringify(semPrioridades(app.respostaDoAgronomo), null, 2)], { type: "application/json" }));
    var a = document.createElement("a"); a.href = endereco; a.download = "orbita-rural-resposta-" + app.terraDoAgronomo + ".json";
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(function () { URL.revokeObjectURL(endereco); }, 1000);
  }
  function filtrarParametros(botao) {
    var so = botao.getAttribute("data-filtro") === "hipotese";
    Array.prototype.forEach.call(botao.parentNode.querySelectorAll("button"), function (b) { b.classList.toggle("active", b === botao); });
    Array.prototype.forEach.call(document.querySelectorAll("#parametrosBox tbody tr"), function (tr) { tr.hidden = so && tr.getAttribute("data-etiqueta") === "publicado"; });
  }

  /* ---------- os toques ---------- */
  var ACOES = {
    "start": abrirEntrada,
    "opcao": function (b) { escolher(b.getAttribute("data-campo"), b.getAttribute("data-valor"), b.getAttribute("data-nome")); },
    "outro-dia": function () { en.outroDia = true; desenharEntrada(true); var c = $("diaDoPlantio"); if (c) c.focus(); },
    "usar-dia": function () { var c = $("diaDoPlantio"), v = c ? c.value : ""; if (/^\d{4}-(09|10|11|12)-\d{2}$/.test(v)) escolher("plantio_da_soja", v, T.dataPorExtenso(v)); },
    "trocar-campo": function (b) { var c = b.getAttribute("data-campo"); delete en.l[c]; if (DITO[c]) delete en.l[DITO[c]]; en.campo = c; en.outroDia = false; falar("assistente", PERGUNTAS[c]); desenharEntrada(true); },
    "confirmar-lavoura": confirmarLavoura,
    "ano-ruim": abrirAnoRuim, "fechar-folha": fecharFolha,
    "abrir-lavoura": abrirLavoura, "fechar-janela": function () { $("janela").hidden = true; $("botaoLavoura").focus(); }, "trocar-lavoura": trocarDeLavoura,
    "perguntar": abrirChatbot, "fechar-gaveta": fecharGaveta, "sugestao": function (b) { perguntar(b.getAttribute("data-texto")); },
    "limpar-chat": function () { ag = { estado: null, confirmada: false, falas: [], ocupado: false }; desenharGaveta(); $("campoDoAssistente").focus(); },
    "tentar": function () { mostrar(app.tela || "hoje"); },
    "terra-do-agronomo": function (b) { app.terraDoAgronomo = b.getAttribute("data-terra"); desenharAgronomo(); },
    "baixar": baixarResposta, "voltar-produtor": function () { irPara("hoje"); }
  };
  document.addEventListener("click", function (ev) {
    var alvo = ev.target instanceof Element ? ev.target : null; if (!alvo) return;
    if (alvo.id === "gaveta") { fecharGaveta(); return; }
    if (alvo.id === "janela") { $("janela").hidden = true; return; }
    var filtro = alvo.closest("[data-filtro]"); if (filtro) { filtrarParametros(filtro); return; }
    var b = alvo.closest("[data-acao]"); if (b && ACOES[b.getAttribute("data-acao")]) { ev.preventDefault(); ACOES[b.getAttribute("data-acao")](b); }
  });
  document.addEventListener("submit", function (ev) {
    var f = ev.target, campo; ev.preventDefault();
    if (f.id === "formDaEntrada") { campo = $("campoDaEntrada"); escritaNaEntrada(campo.value); }
    else if (f.id === "formDoAssistente") { campo = $("campoDoAssistente"); var txt = campo.value; campo.value = ""; perguntar(txt); }
    else if (f.id === "formDaColheita") guardarColheita(f);
  });
  document.addEventListener("change", function (ev) { if (ev.target && ev.target.id === "safraDoRegistro") { app.safra = ev.target.value; mostrar("registrar"); } });
  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Escape") return;
    if (!$("gaveta").hidden) fecharGaveta(); else if (!$("janela").hidden) $("janela").hidden = true; else fecharFolha();
  });
  window.addEventListener("hashchange", rota);

  /* ---------- o começo ---------- */
  function comecar() {
    try {
      var linkDoChat = $("perguntar"), apiDoEndereco = "";
      try { apiDoEndereco = new URLSearchParams(window.location.search).get("api") || ""; } catch (erro) { apiDoEndereco = ""; }
      if (linkDoChat && /^https?:\/\//.test(apiDoEndereco)) linkDoChat.href = "chatbot.html?v=5&api=" + encodeURIComponent(apiDoEndereco);
      app.pronto = D.saude();
      app.lavoura = ler(CHAVE); if (!valida(app.lavoura)) app.lavoura = null;
      if (app.lavoura) abrirApp(""); else openWelcome();
    } finally { document.documentElement.classList.remove("montando"); }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", comecar); else comecar();
})();
