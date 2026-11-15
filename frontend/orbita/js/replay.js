/* Gerado com IA (Claude). */
/* O replay de uma safra, dia a dia (o formato 7.5 do mapa: "dias" e "marcos").
   Nada é calculado aqui: cada número é o do dia, como veio. A única conta é de desenho (a altura de cada barra e
   da água, na escala do maior valor da própria série) e de tempo (quantos milésimos cada dia fica na tela). */
(function () {
  "use strict";

  var C = window.ORBITA_COMPARACAO, esc = C.esc, fmt = C.fmt;
  function ic(nome) { return window.ORBITA_ICONE ? window.ORBITA_ICONE(nome) : ""; }
  var MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
  var MS_POR_DIA = 55, PARADA_MS = 900, PARADA_FORTE_MS = 3600, JANELA_DIAS = 25, JANELA_FORTE_DIAS = 45;      // um ano inteiro com os marcos cabe em uns 30 segundos
  var ativo = null;   // o replay montado agora (só um por vez)

  function partesDaData(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
    return m ? { dia: String(Number(m[3])), mes: MESES[Number(m[2]) - 1] + " de " + m[1] } : { dia: "", mes: String(iso || "") };
  }
  // O nome de cada cobertura como o motor manda ("milho", "sem_planta") vira a palavra do produtor.
  function nomeDaCultura(tipo) { var n = t("replay.culturas." + tipo); return n === "replay.culturas." + tipo ? String(tipo == null ? "" : tipo).replace(/_/g, " ") : n; }
  function maiorDe(dias, campo) { var m = 0; dias.forEach(function (d) { if (typeof d[campo] === "number" && d[campo] > m) m = d[campo]; }); return m; }

  function desenho(dias) {
    var n = dias.length, maiorChuva = maiorDe(dias, "chuva_mm") || 1, maiorAgua = maiorDe(dias, "agua_na_terra_mm") || 1;
    var faixas = "", chuva = "", sede = "", calor = "", area = "M0,88", ultima = null, inicio = 0, par = false;
    dias.forEach(function (d, i) {
      if (d.cultura !== ultima) {
        if (ultima !== null) { faixas += '<rect x="' + inicio + '" y="0" width="' + (i - inicio) + '" height="100" class="' + (par ? "fx-a" : "fx-b") + '"/>'; par = !par; }
        ultima = d.cultura; inicio = i;
      }
      if (d.chuva_mm > 0) chuva += '<rect x="' + (i + 0.1) + '" y="0" width="0.8" height="' + (34 * d.chuva_mm / maiorChuva).toFixed(2) + '"/>';
      var y = (88 - 46 * (d.agua_na_terra_mm || 0) / maiorAgua).toFixed(2);
      area += "L" + i + "," + y + "L" + (i + 1) + "," + y;
      if (d.com_sede) sede += '<rect x="' + i + '" y="91" width="1" height="4"/>';
      if (d.calor_forte) calor += '<rect x="' + i + '" y="96" width="1" height="4"/>';
    });
    faixas += '<rect x="' + inicio + '" y="0" width="' + (n - inicio) + '" height="100" class="' + (par ? "fx-a" : "fx-b") + '"/>';
    area += "L" + n + ",88Z";
    return '<svg class="rp-svg" viewBox="0 0 ' + n + ' 100" preserveAspectRatio="none" aria-hidden="true" focusable="false">' +
      '<defs><clipPath id="rpCorte"><rect id="rpCorteRet" x="0" y="0" width="0" height="100"/></clipPath></defs>' +
      '<g class="rp-faixas">' + faixas + '</g><line class="rp-chao" x1="0" x2="' + n + '" y1="88" y2="88"/>' +
      '<g clip-path="url(#rpCorte)"><g class="rp-chuva">' + chuva + '</g><path class="rp-agua" d="' + area + '"/><g class="rp-sede">' + sede + '</g><g class="rp-calor">' + calor + "</g></g></svg>";
  }

  function culturas(dias) {
    var saida = "", ultima = null, inicio = 0, n = dias.length;
    function trecho(nome, a, b) {      // trecho curto demais (uns dias entre uma cultura e outra) fica só com o risco, sem o nome
      return '<span style="left:' + (100 * a / n).toFixed(2) + "%;width:" + (100 * (b - a) / n).toFixed(2) + '%" data-nome="' + esc(nomeDaCultura(nome)) + '"></span>';
    }
    dias.forEach(function (d, i) { if (d.cultura !== ultima) { if (ultima !== null) saida += trecho(ultima, inicio, i); ultima = d.cultura; inicio = i; } });
    return saida + trecho(ultima, inicio, n);
  }

  function montar(el, replay, cidade) {
    desmontar();
    cidade = (replay && replay.local && replay.local.nome) || cidade || "";
    var dias = (replay && Array.isArray(replay.dias) ? replay.dias : []).filter(function (d) { return d && d.data; });
    if (!dias.length) { el.innerHTML = '<div class="palco-dentro"><p class="rp-sem">' + esc(t("replay.sem")) + "</p></div>"; el.classList.add("sem-replay"); return; }
    el.classList.remove("sem-replay");
    var n = dias.length, indice = {};
    dias.forEach(function (d, i) { indice[d.data] = i; });
    var marcos = (Array.isArray(replay.marcos) ? replay.marcos : []).filter(function (m) { return m && indice[m.data] !== undefined; })
      .map(function (m) { return { i: indice[m.data], tipo: m.tipo, frase: m.frase || "", cultura: m.cultura || "", principal: m.principal === true }; }).sort(function (a, b) { return a.i - b.i; });
    // O marco do pulso: o que o motor marcou como principal; sem essa marca, o único (ou o último) "a água acabou".
    if (!marcos.some(function (m) { return m.principal; })) {
      var deAgua = marcos.filter(function (m) { return m.tipo === "agua_acabou"; });
      if (deAgua.length) deAgua[deAgua.length - 1].principal = true;
    }
    var maiorAgua = maiorDe(dias, "agua_na_terra_mm") || 1, temTmax = dias.some(function (d) { return typeof d.tmax_c === "number"; });
    var bandeiras = marcos.map(function (m, k) {
      var pct = 100 * (m.i + 0.5) / n;
      var nome = t(m.tipo === "agua_acabou" && !m.principal ? "replay.marcos.sede" : "replay.marcos." + m.tipo);
      if (nome === "replay.marcos." + m.tipo) nome = m.tipo;
      if ((m.tipo === "plantio" || m.tipo === "colheita") && m.cultura) nome += ": " + nomeDaCultura(m.cultura);
      return '<span class="rp-marco m-' + esc(m.tipo) + (m.principal ? " principal" : "") + '" data-marco="' + k + '" style="left:' + pct.toFixed(2) + '%"><b>' + esc(nome) + "</b></span>";
    }).join("");

    el.innerHTML = '<div class="palco-dentro"><header class="palco-topo"><h2 id="tituloDoReplay">' + esc(t("replay.titulo", { safra: replay.safra || "" })) + "</h2><p>" + esc(t(cidade ? "replay.texto" : "replay.textoSemLugar", { cidade: cidade })) + (replay.rotacao && replay.rotacao.nome ? " " + esc(t("replay.rotacao", { nome: replay.rotacao.nome })) : "") + "</p></header>" +
      '<div class="replay" id="replay">' +
        '<div class="rp-leitura"><p class="rp-data"><span class="rp-dia" id="rpDia"></span><span class="rp-mes" id="rpMes"></span></p>' +
          '<p class="rp-cultura" id="rpCultura"></p><p class="rp-conta" id="rpConta"></p>' +
          '<dl class="rp-numeros"><div class="rp-caixa-linha"><dt>' + esc(t("replay.agua")) + '</dt><dd><span class="rp-caixa" aria-hidden="true"><i id="rpNivel"></i></span><b id="rpAgua"></b> mm</dd></div>' +
            "<div><dt>" + esc(t("replay.chuva")) + '</dt><dd><b id="rpChuva"></b> mm</dd></div>' +
            "<div><dt>" + esc(t("replay.falta")) + '</dt><dd><b id="rpFalta"></b> mm</dd></div>' +
            (temTmax ? "<div><dt>" + esc(t("replay.tmax")) + '</dt><dd><b id="rpTmax"></b> °C</dd></div>' : "") + "</dl>" +
          '<p class="rp-sinais"><span id="rpSede" class="sinal sede">' + ic("gota") + esc(t("replay.comSede")) + '</span><span id="rpCalor" class="sinal calor">' + ic("sol") + esc(t("replay.calorForte")) + "</span></p></div>" +
        '<div class="rp-quadro"><div class="rp-grafico">' + desenho(dias) + '<div class="rp-marcos">' + bandeiras + '</div><i class="rp-agulha" id="rpAgulha"></i></div>' +
          '<div class="rp-culturas" aria-hidden="true">' + culturas(dias) + "</div>" +
          '<p class="rp-legenda"><span class="l-chuva">' + esc(t("replay.legenda.chuva")) + '</span><span class="l-agua">' + esc(t("replay.legenda.agua")) + '</span><span class="l-sede">' + esc(t("replay.legenda.sede")) + '</span><span class="l-calor">' + esc(t("replay.legenda.calor")) + "</span></p></div>" +
        '<p class="rp-frase" id="rpFrase" aria-live="polite"></p>' +
        '<div class="rp-controles"><button class="rp-botao principal" id="rpTocar" type="button"></button>' +
          '<button class="rp-botao" id="rpVoltar" type="button" aria-label="' + esc(t("replay.voltar")) + '" title="' + esc(t("replay.voltar")) + '">' + ic("voltar") + "</button>" +
          '<input type="range" id="rpLinha" min="0" max="' + (n - 1) + '" step="1" value="0" aria-label="' + esc(t("replay.linha")) + '">' +
          '<button class="rp-botao texto" id="rpVelocidade" type="button" aria-label="' + esc(t("replay.velocidade")) + ': 1×">1×</button>' +
          '<button class="rp-botao" id="rpCheia" type="button" aria-label="' + esc(t("replay.cheia")) + '" title="' + esc(t("replay.cheia")) + '">' + ic("cheia") + "</button></div>" +
      "</div></div>";

    function $(id) { return el.querySelector("#" + id); }
    var pecas = { dia: $("rpDia"), mes: $("rpMes"), cultura: $("rpCultura"), conta: $("rpConta"), nivel: $("rpNivel"), agua: $("rpAgua"), chuva: $("rpChuva"), falta: $("rpFalta"), tmax: $("rpTmax"),
                  sede: $("rpSede"), calor: $("rpCalor"), corte: $("rpCorteRet"), agulha: $("rpAgulha"), frase: $("rpFrase"), tocar: $("rpTocar"), linha: $("rpLinha"), velocidade: $("rpVelocidade"), caixa: el.querySelector(".rp-caixa") };
    var bandeirasEl = el.querySelectorAll(".rp-marco"), quadro = $("replay"), grafico = el.querySelector(".rp-grafico");
    // As etiquetas dos marcos: cada uma no andar mais baixo em que não cobre outra (medido na tela, porque a largura muda).
    function arrumarMarcos() {
      var largura = grafico.clientWidth, ocupados = [], maior = 0;
      if (!largura) return;
      Array.prototype.forEach.call(bandeirasEl, function (b, k) {
        var etiqueta = b.firstElementChild, w = etiqueta.offsetWidth, x = largura * (marcos[k].i + 0.5) / n;
        var aEsquerda = x + 5 + w > largura;
        b.classList.toggle("a-esquerda", aEsquerda);
        var x0 = aEsquerda ? x - 5 - w : x + 5, x1 = x0 + w, andar = 0;
        while (ocupados[andar] && ocupados[andar].some(function (o) { return x0 < o[1] + 6 && x1 > o[0] - 6; })) andar += 1;
        (ocupados[andar] = ocupados[andar] || []).push([x0, x1]);
        etiqueta.style.top = (andar * 24) + "px"; maior = Math.max(maior, andar);
      });
      grafico.style.setProperty("--andares", maior + 1);
      // O nome de cada cultura embaixo do desenho: só onde cabe inteiro.
      Array.prototype.forEach.call(el.querySelectorAll(".rp-culturas span"), function (s) {
        s.textContent = s.getAttribute("data-nome") || "";
        if (s.scrollWidth > s.clientWidth + 1) s.textContent = "";
      });
    }
    var st = { i: 0, tocando: false, velocidade: 1, antes: 0, resto: 0, parada: 0, quadro: 0, comecou: false };

    function mostrar(i) {
      var d = dias[i], p = partesDaData(d.data);
      pecas.dia.textContent = p.dia.length < 2 ? "0" + p.dia : p.dia; pecas.mes.textContent = p.mes;      // dois algarismos sempre: a data não dança
      pecas.cultura.textContent = !d.cultura ? "" : d.cultura === "sem_planta" || d.cultura === "sem planta" ? t("replay.semPlanta") : nomeDaCultura(d.cultura) + " " + t("replay.naTerra");
      pecas.conta.textContent = t("replay.dia", { n: i + 1, total: n });
      pecas.agua.textContent = fmt(d.agua_na_terra_mm); pecas.chuva.textContent = fmt(d.chuva_mm); pecas.falta.textContent = fmt(d.falta_mm);
      if (pecas.tmax) pecas.tmax.textContent = fmt(d.tmax_c);
      pecas.nivel.style.height = Math.max(0, Math.min(100, 100 * (d.agua_na_terra_mm || 0) / maiorAgua)).toFixed(1) + "%";
      pecas.sede.classList.toggle("aceso", !!d.com_sede); pecas.calor.classList.toggle("aceso", !!d.calor_forte);
      pecas.sede.setAttribute("aria-hidden", d.com_sede ? "false" : "true"); pecas.calor.setAttribute("aria-hidden", d.calor_forte ? "false" : "true");   // sinal apagado não é lido
      pecas.corte.setAttribute("width", i + 1);
      pecas.agulha.style.left = (100 * (i + 1) / n).toFixed(2) + "%";
      pecas.linha.value = i;
      pecas.linha.setAttribute("aria-valuetext", p.dia + " de " + p.mes);
      var ultimo = null, principal = null;
      marcos.forEach(function (m, k) { var passou = m.i <= i; bandeirasEl[k].classList.toggle("passou", passou); if (passou) { ultimo = m; if (m.principal) principal = m; } });
      // A frase de um marco fica uns dias na tela e sai (não diz "neste dia" meses depois); no último dia volta a do fim.
      // No marco principal entra o pulso da demonstração (três frases, sem número), com a frase da conta embaixo.
      var recente = !!ultimo && (i - ultimo.i <= JANELA_DIAS || i === n - 1);
      var pulso = st.comecou && !!principal && i - principal.i <= JANELA_FORTE_DIAS;
      var texto = !st.comecou ? t("replay.comeco") : pulso ? (recente ? ultimo.frase : principal.frase) : recente ? ultimo.frase : "";
      var chave = (pulso ? "pulso|" : "") + texto;
      if (pecas.frase.getAttribute("data-texto") !== chave) {
        pecas.frase.setAttribute("data-texto", chave);
        pecas.frase.innerHTML = pulso
          ? '<strong class="rp-pulso">' + [].concat(t("replay.pulso")).map(function (f) { return "<span>" + esc(f) + "</span>"; }).join(" ") + "</strong>" + (texto ? "<small>" + esc(texto) + "</small>" : "")
          : "<span>" + esc(texto) + "</span>";
      }
      pecas.frase.classList.toggle("forte", pulso);
      quadro.classList.toggle("sem-agua", !!d.com_sede);
    }
    function botao() {
      pecas.tocar.innerHTML = ic(st.tocando ? "pausar" : "tocar") + "<span>" + esc(t(st.tocando ? "replay.pausar" : "replay.tocar")) + "</span>";
      pecas.tocar.setAttribute("aria-pressed", st.tocando ? "true" : "false");
    }
    function passo(agora) {
      if (!st.tocando) return;
      var passou = Math.min(200, agora - st.antes); st.antes = agora;
      if (st.parada > 0) { st.parada -= passou; }
      else {
        st.resto += passou;
        var cada = MS_POR_DIA / st.velocidade;
        while (st.resto >= cada && st.i < n - 1 && st.parada <= 0) {
          st.resto -= cada; st.i += 1;
          for (var k = 0; k < marcos.length; k++) if (marcos[k].i === st.i) st.parada = Math.max(st.parada, (marcos[k].principal ? PARADA_FORTE_MS : PARADA_MS) / st.velocidade);
        }
        mostrar(st.i);
        if (st.i >= n - 1) { parar(); return; }
      }
      st.quadro = requestAnimationFrame(passo);
    }
    function tocar() {
      if (st.i >= n - 1) st.i = 0;
      st.tocando = true; st.comecou = true; st.antes = performance.now(); st.resto = 0; st.parada = 0; botao(); mostrar(st.i);
      st.quadro = requestAnimationFrame(passo);
    }
    function parar() { st.tocando = false; cancelAnimationFrame(st.quadro); botao(); }
    function irPara(i) { st.i = Math.max(0, Math.min(n - 1, i)); st.comecou = st.comecou || st.i > 0; st.parada = 0; st.resto = 0; mostrar(st.i); }

    pecas.tocar.addEventListener("click", function () { st.tocando ? parar() : tocar(); });
    $("rpVoltar").addEventListener("click", function () { parar(); st.comecou = false; irPara(0); });
    pecas.linha.addEventListener("input", function () { parar(); st.comecou = true; irPara(Number(pecas.linha.value)); });
    pecas.velocidade.addEventListener("click", function () { st.velocidade = st.velocidade === 1 ? 2 : st.velocidade === 2 ? 0.5 : 1; pecas.velocidade.textContent = String(st.velocidade).replace(".", ",") + "×"; pecas.velocidade.setAttribute("aria-label", t("replay.velocidade") + ": " + pecas.velocidade.textContent); });
    $("rpCheia").addEventListener("click", function () {
      if (document.fullscreenElement) document.exitFullscreen(); else if (el.requestFullscreen) el.requestFullscreen();
    });
    Array.prototype.forEach.call(bandeirasEl, function (b) { b.addEventListener("click", function () { parar(); st.comecou = true; irPara(marcos[Number(b.getAttribute("data-marco"))].i); }); });

    var relogioDaLargura = 0;
    function aoMudarALargura() { clearTimeout(relogioDaLargura); relogioDaLargura = setTimeout(arrumarMarcos, 120); }
    window.addEventListener("resize", aoMudarALargura); document.addEventListener("fullscreenchange", aoMudarALargura);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(arrumarMarcos);
    ativo = { parar: function () { parar(); }, soltar: function () { window.removeEventListener("resize", aoMudarALargura); document.removeEventListener("fullscreenchange", aoMudarALargura); } };
    botao(); mostrar(0); arrumarMarcos();
  }

  function desmontar() { if (ativo) { ativo.parar(); ativo.soltar(); ativo = null; } }

  window.ORBITA_REPLAY = { montar: montar, parar: function () { if (ativo) ativo.parar(); } };
})();
