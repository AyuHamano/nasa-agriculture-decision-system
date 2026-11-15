/* Gerado com IA (Claude). */
/* A conversa do produtor com o agente, em dois modos:
   - guardadas: toca uma conversa de dados/conversas.js (o formato 7.5 do mapa); a próxima fala guardada vira um botão;
   - ao vivo: chama POST /agente (o formato 7.4), guarda o "estado" e devolve na fala seguinte.
   Se a API falhar, avisa e cai nas guardadas. A tela não faz conta nem escreve número: mostra o que chega. */
(function () {
  "use strict";

  var C = window.ORBITA_COMPARACAO, esc = C.esc;
  function ic(nome) { return window.ORBITA_ICONE ? window.ORBITA_ICONE(nome) : ""; }
  var ESPERA_MS = 650, LIMITE_MS = 60000, LONGA = 620, VISTA = 380;
  var calmo = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // O texto do agente em blocos: cada linha vira um parágrafo; linhas seguidas que começam com "•" viram uma lista.
  function blocos(texto) {
    var saida = [], itens = [], tamanho = 0;
    function fechar() { if (itens.length) { saida.push({ html: "<ul>" + itens.map(function (i) { return "<li>" + esc(i) + "</li>"; }).join("") + "</ul>", n: tamanho, lista: true }); itens = []; tamanho = 0; } }
    String(texto || "").split(/\n+/).map(function (l) { return l.trim(); }).filter(Boolean).forEach(function (l) {
      var m = /^•\s*(.+)$/.exec(l);
      if (m) { itens.push(m[1]); tamanho += m[1].length; } else { fechar(); saida.push({ html: "<p>" + esc(l) + "</p>", n: l.length, lista: false }); }
    });
    fechar();
    return saida;
  }
  // Resposta comprida (as frases prontas da conta): o começo e o fecho ficam à vista, o miolo abre com um toque.
  // Nada é cortado: o texto inteiro está na página.
  function paragrafos(texto) {
    var b = blocos(texto), total = b.reduce(function (s, x) { return s + x.n; }, 0);
    function junta(lista) { return lista.map(function (x) { return x.html; }).join(""); }
    if (total <= LONGA || b.length < 3) return junta(b);
    var cabeca = [b[0]], i = 1, soma = b[0].n;
    while (i < b.length - 1 && !b[i].lista && soma + b[i].n <= VISTA) { cabeca.push(b[i]); soma += b[i].n; i += 1; }
    var ultimo = b[b.length - 1], fecho = !ultimo.lista && ultimo.n <= 220 ? [ultimo] : [];
    var miolo = b.slice(i, b.length - fecho.length);
    if (!miolo.length) return junta(b);
    return junta(cabeca) + '<details class="miolo"><summary>' + esc(t("conversa.lerTudo")) + "</summary>" + junta(miolo) + "</details>" + junta(fecho);
  }

  // ganchos: { aoResponder(saida, ehAUltima), aoCair(motivo), aoMudar() }
  function criar(elFalas, elCompositor, ganchos) {
    var st = { modo: "guardadas", api: "", momento: "antes", conversa: null, passo: 0, falas: [], estadoDaApi: null, esperando: false, relogio: 0, vez: 0 };

    function ultimaSaida() { for (var i = st.falas.length - 1; i >= 0; i--) if (st.falas[i].saida) return st.falas[i].saida; return null; }
    function proximaGuardada() {
      var p = st.conversa && st.conversa.passos ? st.conversa.passos[st.passo] : null;
      return p && p.de === "produtor" ? String(p.texto || "") : null;
    }
    function acabou() { return st.modo === "guardadas" && !!st.conversa && st.passo >= (st.conversa.passos || []).length && !st.esperando; }

    /* ---------- desenho ---------- */
    function falaDoAgente(f, ehAUltima) {
      var s = f.saida, apoio = s.apoio && t("conversa.apoio." + s.apoio) !== "conversa.apoio." + s.apoio ? s.apoio : "";
      var conf = s.conferencia && typeof s.conferencia.passou === "boolean" ? s.conferencia.passou : null;
      var pe = "";
      if (apoio) pe += '<span class="apoio a-' + esc(apoio) + '">' + ic(apoio === "conhecimento_geral" ? "alerta" : "satelite") + esc(t("conversa.apoio." + apoio)) + "</span>";
      if (conf !== null && apoio && apoio !== "conhecimento_geral" && /\d/.test(String(s.resposta || ""))) pe += '<span class="conferido">' + ic("certo") + esc(t(conf ? "conversa.conferido" : "conversa.naoConferido")) + "</span>";
      var atalhos = "";
      if (ehAUltima) {
        if (s.comparacao && s.comparacao.length) atalhos += '<button class="atalho" data-acao="ir-comparacao">' + esc(t("conversa.verComparacao")) + ic("seta") + "</button>";
        else if (s.ficha) atalhos += '<button class="atalho" data-acao="ir-ficha">' + esc(t("conversa.verFicha")) + ic("seta") + "</button>";
        if ((st.conversa && st.conversa.replay) || (s.replay && Array.isArray(s.replay.dias) && s.replay.dias.length)) atalhos += '<button class="atalho so-replay" data-acao="ir-replay">' + esc(t("conversa.verReplay")) + ic("seta") + "</button>";
      }
      return '<li class="fala agente"><span class="quem">' + esc(t("conversa.agente")) + '</span><div class="balao">' + paragrafos(s.resposta) +
        (s.aviso && ehAUltima ? '<p class="aviso-agro">' + ic("pessoa") + esc(s.aviso) + "</p>" : "") + "</div>" +
        (pe ? '<p class="pe">' + pe + "</p>" : "") + (atalhos ? '<p class="atalhos">' + atalhos + "</p>" : "") + "</li>";
    }
    function desenharFalas() {
      var ultimaDoAgente = -1;
      st.falas.forEach(function (f, i) { if (f.saida) ultimaDoAgente = i; });
      var html = st.falas.map(function (f, i) {
        if (f.saida) return falaDoAgente(f, i === ultimaDoAgente);
        if (f.nota) return '<li class="fala nota">' + ic("alerta") + "<p>" + esc(f.nota) + "</p></li>";
        return '<li class="fala produtor"><span class="quem">' + esc(t("conversa.produtor")) + '</span><div class="balao"><p>' + esc(f.texto) + "</p></div></li>";
      }).join("");
      if (st.esperando) html += '<li class="fala agente esperando"><span class="quem">' + esc(t("conversa.agente")) + '</span><div class="balao"><span class="pontos" role="status" aria-label="' + esc(t("conversa.escrevendo")) + '"><i></i><i></i><i></i></span></div></li>';
      elFalas.innerHTML = html;
      elFalas.classList.toggle("vazia", !st.falas.length && !st.esperando);
    }
    // Depois de desenhar as falas E o compositor (ele muda a altura da lista): a última fala fica à vista desde o começo dela.
    function rolar() {
      var ultima = elFalas.lastElementChild;
      if (!ultima || !st.falas.length) return;
      if (elFalas.scrollHeight > elFalas.clientHeight + 4) {       // no computador a lista rola por dentro
        var doAgente = ultima.classList.contains("agente") && !ultima.classList.contains("esperando");
        elFalas.scrollTop = doAgente ? Math.min(ultima.offsetTop - 8, elFalas.scrollHeight - elFalas.clientHeight) : elFalas.scrollHeight;
      } else if (st.falas.length > 1 && ultima.getBoundingClientRect().bottom > window.innerHeight) {
        ultima.scrollIntoView({ block: "nearest", behavior: calmo ? "auto" : "smooth" });
      }
    }
    function desenharCompositor() {
      var html = "";
      if (st.modo === "ao_vivo") {
        var sugestao = !st.falas.length ? t("momentos." + st.momento + ".comeco") : "";
        html = '<form class="fala-nova" id="formDaFala"><label for="campoDaFala">' + esc(t("conversa.rotuloDoCampo")) + '</label><div class="linha"><textarea id="campoDaFala" rows="2" maxlength="1500" placeholder="' + esc(t("conversa.campo")) + '"' + (st.esperando ? " disabled" : "") + ">" +
          "</textarea><button class=\"botao cheio\" type=\"submit\"" + (st.esperando ? " disabled" : "") + ">" + esc(t("conversa.enviar")) + "</button></div>" +
          (sugestao && sugestao !== "momentos." + st.momento + ".comeco" ? '<button class="sugestao" type="button" data-acao="usar-sugestao" data-texto="' + esc(sugestao) + '">' + esc(sugestao) + "</button>" : "") + "</form>";
      } else if (st.conversa) {
        var proxima = proximaGuardada();
        if (proxima && !st.esperando) html = '<div class="proxima"><span>' + esc(t("conversa.proxima")) + '</span><button class="dizer" data-acao="dizer-proxima"><q>' + esc(proxima) + "</q><b>" + esc(t("conversa.dizer")) + ic("seta") + "</b></button></div>";
        else if (acabou()) html = '<div class="fim"><span>' + esc(t("conversa.fim")) + '</span><button class="botao" data-acao="recomecar">' + ic("voltar") + esc(t("conversa.recomecar")) + "</button></div>";
      }
      elCompositor.innerHTML = html;
    }
    function desenhar() { desenharFalas(); desenharCompositor(); rolar(); if (ganchos.aoMudar) ganchos.aoMudar(); }

    /* ---------- o modo guardadas ---------- */
    function entrarAgente(vez) {
      if (vez !== st.vez) return;
      var p = st.conversa.passos[st.passo];
      st.esperando = false;
      if (p && p.de === "agente" && p.saida) { st.falas.push({ saida: p.saida }); st.passo += 1; ganchos.aoResponder(p.saida); }
      desenhar();
    }
    function avancarGuardada() {
      var texto = proximaGuardada(); if (texto === null || st.esperando) return;
      st.falas.push({ texto: texto }); st.passo += 1;
      var p = st.conversa.passos[st.passo];
      if (p && p.de === "agente") { st.esperando = true; var vez = st.vez; clearTimeout(st.relogio); st.relogio = setTimeout(function () { entrarAgente(vez); }, calmo ? 0 : ESPERA_MS); }
      desenhar();
    }
    function abrirGuardada(conversa, momento) {
      st.vez += 1; clearTimeout(st.relogio);
      st.modo = "guardadas"; st.conversa = conversa || null; st.momento = momento || (conversa && conversa.momento) || st.momento;
      st.passo = 0; st.falas = []; st.esperando = false; st.estadoDaApi = null;
      var p = conversa && conversa.passos ? conversa.passos[0] : null;
      if (p && p.de === "agente" && p.saida) { st.falas.push({ saida: p.saida }); st.passo = 1; ganchos.aoResponder(p.saida); }
      desenhar();
    }

    /* ---------- o modo ao vivo ---------- */
    function abrirAoVivo(api, momento) {
      st.vez += 1; clearTimeout(st.relogio);
      st.modo = "ao_vivo"; st.api = api; st.momento = momento || st.momento; st.conversa = null; st.passo = 0; st.falas = []; st.esperando = false; st.estadoDaApi = null;
      desenhar();
    }
    function chamar(texto) {
      var controle = typeof AbortController === "function" ? new AbortController() : null;
      var relogio = setTimeout(function () { if (controle) controle.abort(); }, LIMITE_MS);
      return fetch(st.api + "/agente", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ estado: st.estadoDaApi, texto: texto }), signal: controle ? controle.signal : undefined })
        .then(function (r) {
          clearTimeout(relogio);
          return r.json().catch(function () { return null; }).then(function (j) {
            if (!r.ok) throw { codigo: r.status, erro: j && j.erro };
            if (!j || typeof j.resposta !== "string") throw { codigo: 0 };
            return j;
          });
        }, function () { clearTimeout(relogio); throw { codigo: -1 }; });
    }
    function enviarAoVivo(texto) {
      var vez = st.vez;
      st.falas.push({ texto: texto }); st.esperando = true; desenhar();
      chamar(texto).then(function (saida) {
        if (vez !== st.vez) return;
        st.esperando = false; st.estadoDaApi = saida.estado === undefined ? null : saida.estado;
        st.falas.push({ saida: saida }); ganchos.aoResponder(saida); desenhar();
        var campo = elCompositor.querySelector("#campoDaFala"); if (campo) campo.focus();
      }, function (falha) {
        if (vez !== st.vez) return;
        st.esperando = false;
        // Pedido recusado pelo agente (a fala, o tamanho): mostra a frase dele e continua ao vivo. O resto derruba para as guardadas.
        if (falha && falha.codigo >= 400 && falha.codigo < 500 && falha.codigo !== 404 && falha.erro) { st.falas.push({ nota: String(falha.erro) }); desenhar(); return; }
        var motivo = falha && falha.codigo === 503 ? "semChave" : falha && falha.codigo === -1 ? "semResposta" : "erro";
        ganchos.aoCair(motivo);
      });
    }

    function dizer(texto) {
      texto = String(texto || "").trim();
      if (st.esperando) return;
      if (st.modo === "ao_vivo") { if (texto) enviarAoVivo(texto); }
      else avancarGuardada();
    }

    return { estado: st, abrirGuardada: abrirGuardada, abrirAoVivo: abrirAoVivo, dizer: dizer, ultimaSaida: ultimaSaida, proximaGuardada: proximaGuardada, desenhar: desenhar };
  }

  window.ORBITA_CONVERSA = { criar: criar };
})();
