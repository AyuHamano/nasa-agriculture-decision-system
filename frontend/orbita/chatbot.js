(function () {
  "use strict";

  var messages = document.getElementById("mensagens");
  var quickReplies = document.getElementById("respostasRapidas");
  var form = document.getElementById("formulario");
  var input = document.getElementById("mensagem");
  var sendButton = document.getElementById("enviar");
  var presence = document.getElementById("presenca");
  var query = new URLSearchParams(window.location.search);
  var apiBase = String(query.get("api") || "").replace(/\/+$/, "");
  var apiState = null;
  var waiting = false;
  var profile = { city: "", crop: "", soil: "", concern: "" };

  var initialReplies = [
    "Resumo da minha fazenda"
  ];

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (char) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char];
    });
  }

  function timeNow() {
    var now = new Date();
    return String(now.getHours()).padStart(2, "0") + ":" + String(now.getMinutes()).padStart(2, "0");
  }

  function dateFromISO(value) {
    var match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ""));
    return match ? match[3] + "/" + match[2] + "/" + match[1] : "data não informada";
  }

  function todayBR() {
    return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date());
  }

  function numberBR(value, digits) {
    var n = Number(value);
    return isFinite(n) ? n.toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits }) : "—";
  }

  function scrollToEnd() {
    window.requestAnimationFrame(function () {
      messages.scrollTo({ top: messages.scrollHeight, behavior: "smooth" });
    });
  }

  function addMessage(kind, text) {
    var article = document.createElement("article");
    article.className = "message " + kind;
    var paragraphs = String(text).split(/\n{2,}/).map(function (paragraph) {
      var formatted = escapeHtml(paragraph).replace(/\*([^*\n]+)\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
      return "<p>" + formatted + "</p>";
    }).join("");
    var checks = kind === "user" ? '<span class="checks" aria-label="Entregue e lida">✓✓</span>' : "";
    article.innerHTML = paragraphs + '<small><span class="message-time">' + timeNow() + "</span>" + checks + "</small>";
    messages.insertBefore(article, quickReplies);
    scrollToEnd();
  }

  function showTyping() {
    var typing = document.createElement("div");
    typing.className = "message bot typing";
    typing.id = "digitando";
    typing.setAttribute("aria-label", "Órbita Rural está digitando");
    typing.innerHTML = "<span></span><span></span><span></span>";
    messages.insertBefore(typing, quickReplies);
    presence.textContent = "digitando…";
    scrollToEnd();
  }

  function hideTyping() {
    var typing = document.getElementById("digitando");
    if (typing) typing.remove();
    presence.textContent = apiBase ? "online · conectado ao motor" : "online · assistente virtual";
  }

  function setReplies(replies) {
    quickReplies.innerHTML = "";
    (replies || []).forEach(function (label) {
      var button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.addEventListener("click", function () { send(label); });
      quickReplies.appendChild(button);
    });
    scrollToEnd();
  }

  function normalize(text) {
    return String(text).toLocaleLowerCase("pt-BR").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  function savedFarm() {
    try {
      var farm = JSON.parse(window.localStorage.getItem("orbita.lavoura.v1") || "null");
      return farm && farm.cidade_id && farm.rotacao_id && farm.terra ? farm : null;
    } catch (error) {
      return null;
    }
  }

  function itemById(panel, id) {
    return (Array.isArray(panel && panel.itens) ? panel.itens : []).filter(function (item) { return item.id === id; })[0] || null;
  }

  function summaryMessage(panel, farm) {
    var phase = itemById(panel, "fase") || {};
    var water = itemById(panel, "agua") || {};
    var heat = itemById(panel, "calor") || {};
    var green = itemById(panel, "verde") || {};
    var drought = itemById(panel, "aviso_de_sede") || {};
    var soilNames = { pouca: "arenoso / pouca retenção", media: "textura média", muita: "argiloso / maior retenção" };
    var lines = [
      "📋 *RESUMO DA SUA LAVOURA*",
      "📍 " + ((panel.local || {}).nome || farm.cidade_id),
      "🌱 " + ((panel.rotacao || {}).nome || farm.rotacao_id),
      "🟤 Solo: " + (soilNames[farm.terra] || farm.terra),
      "📅 Dados atualizados até " + dateFromISO(panel.ultimo_dia_com_dado)
    ];

    if (phase.cultura) lines.push("🌿 Fase: " + (phase.fase_nome || phase.fase || phase.cultura) + (typeof phase.dias_desde_o_plantio === "number" ? " — " + phase.dias_desde_o_plantio + " dias do plantio" : ""));
    if (typeof water.agua_na_terra_mm === "number") lines.push("💧 Água no solo: " + numberBR(water.agua_na_terra_mm, 1) + " mm de " + numberBR(water.agua_que_a_terra_segura_mm, 1) + " mm (" + numberBR(water.agua_na_terra_pct, 0) + "%) — " + (water.com_sede ? "com sede" : "sem sede"));
    if (typeof heat.dias_de_calor_forte_desde_o_plantio === "number") lines.push("🌡️ Calor forte: " + heat.dias_de_calor_forte_desde_o_plantio + " dia(s) desde o plantio");
    if (typeof green.verde === "number") lines.push("🛰️ Verde do satélite: " + numberBR(green.verde, 2) + " — " + (green.situacao_nome || green.leitura || "sem classificação"));
    if (drought.ja_com_sede) lines.push("🚨 Aviso: a cultura já está com sede.");
    else if (typeof drought.dias_ate_a_sede === "number") lines.push("⚠️ Sem nova chuva, a sede pode começar em " + drought.dias_ate_a_sede + " dia(s), em " + dateFromISO(drought.data_da_sede) + ".");
    lines.push("", "Situação geral: " + (panel.situacao_nome || panel.situacao || "sem classificação") + ".", "Converse com um profissional de agronomia antes de decidir.");
    return lines.join("\n");
  }

  function softwareReply(text) {
    var value = normalize(text);
    var asksSummary = /resumo|resuma|minha fazenda|minha propriedade/.test(value);
    var asksComparison = /comparar|comparacao|rotac|trocar|milho.*sorgo|sorgo.*milho/.test(value);
    var asksHarvest = /ultima safra|safra mostrou|registro|colheita/.test(value);
    var asksPanel = /como esta|minha lavoura|agua|chuva|calor|temperatura|verde|satelite|sede|semana|fase|cobertura|erosao/.test(value);
    if (!asksSummary && !asksComparison && !asksHarvest && !asksPanel) return Promise.resolve(null);

    var farm = savedFarm(), data = window.ORBITA_DADOS;
    if (!farm) {
      return Promise.resolve({
        text: "Ainda não encontrei uma lavoura cadastrada neste navegador. Volte pela seta, preencha a ficha no Órbita Rural e depois peça: “Me mande um resumo sobre a minha fazenda”.",
        replies: ["Ver um exemplo"]
      });
    }
    if (!data || typeof data.buscar !== "function") return Promise.resolve(null);

    if (asksComparison) {
      return data.buscar("ensaio", farm).then(function (result) {
        var report = result.dados || {}, options = Array.isArray(report.comparacao_das_rotacoes) ? report.comparacao_das_rotacoes : [];
        var cityNames = { rio_verde: "Rio Verde (GO)", jatai: "Jataí (GO)", silvania: "Silvânia (GO)" };
        var lines = ["🌱 *COMPARAÇÃO DE ROTAÇÕES*", "📍 " + (cityNames[farm.cidade_id] || farm.cidade_id)];
        options.forEach(function (option) {
          lines.push("", (option.de_hoje ? "✅ Sua rotação: " : "🔎 Alternativa: ") + (option.apelido || option.nome || option.id));
          if (option.beneficio) lines.push("Ganho: " + option.beneficio);
          if (option.risco_curto || option.risco) lines.push("Risco: " + (option.risco_curto || option.risco));
        });
        lines.push("", report.aviso || "Converse com um profissional de agronomia antes de decidir.");
        return { text: lines.join("\n"), replies: ["Resumo da minha fazenda", "Como está a água?"] };
      });
    }

    if (asksHarvest) {
      return data.buscar("registro", farm).then(function (result) {
        var report = result.dados || {};
        return { text: "📒 *RESUMO DA SAFRA " + (report.safra || "") + "*\n\n" + (report.frase || "O registro da safra não está disponível agora.") + "\n\n" + (report.aviso || "Converse com um profissional de agronomia."), replies: ["Resumo da minha fazenda", "Comparar rotações"] };
      });
    }

    return data.buscar("painel", farm).then(function (result) {
      var panel = result.dados || {};
      if (asksSummary || /como esta|minha lavoura/.test(value)) return { text: summaryMessage(panel, farm), replies: ["Como está a água?", "E o calor?", "Comparar rotações"] };
      var id = /calor|temperatura/.test(value) ? "calor" : /verde|satelite/.test(value) ? "verde" : /cobertura|erosao/.test(value) ? "terra_coberta" : /sede|sem chuva/.test(value) ? "aviso_de_sede" : /fase/.test(value) ? "fase" : "agua";
      var item = itemById(panel, id);
      var message = item && item.frase ? item.frase : panel.frase || "Não encontrei esse dado agora.";
      return { text: message + "\n\n📅 Dado de " + dateFromISO((item && item.ultimo_dado || {}).data || panel.ultimo_dia_com_dado) + ".\n\n" + (panel.aviso || "Converse com um profissional de agronomia."), replies: ["Resumo da minha fazenda", "Comparar rotações"] };
    }).catch(function () { return null; });
  }

  function learnFrom(text) {
    var value = normalize(text);
    if (/rio verde/.test(value)) profile.city = "Rio Verde (GO)";
    else if (/jatai/.test(value)) profile.city = "Jataí (GO)";
    else if (/silvania/.test(value)) profile.city = "Silvânia (GO)";

    if (/soja/.test(value) && /milho/.test(value)) profile.crop = "soja → milho safrinha";
    else if (/soja/.test(value) && /sorgo/.test(value)) profile.crop = "soja → sorgo";
    else if (/soja/.test(value)) profile.crop = "soja";
    else if (/milho/.test(value)) profile.crop = "milho";
    else if (/sorgo/.test(value)) profile.crop = "sorgo";

    if (/arenos|pouca agua|solo leve/.test(value)) profile.soil = "solo arenoso";
    else if (/argilos|muita agua|solo pesado/.test(value)) profile.soil = "solo argiloso";
    else if (/textura media|solo medio|terra media/.test(value)) profile.soil = "solo de textura média";

    if (/agua|chuva|seca|sede/.test(value)) profile.concern = "água";
    else if (/calor|temperatura/.test(value)) profile.concern = "calor";
    else if (/cobertura|erosao|terra/.test(value)) profile.concern = "cobertura da terra";
  }

  function missingProfile() {
    var missing = [];
    if (!profile.city) missing.push("município");
    if (!profile.crop) missing.push("o que você planta hoje");
    if (!profile.soil) missing.push("tipo de solo");
    if (!profile.concern) missing.push("sua maior preocupação");
    return missing;
  }

  function localReply(text) {
    var value = normalize(text);
    learnFrom(text);

    if (/^(oi|ola|bom dia|boa tarde|boa noite)\b/.test(value)) {
      return { text: "Olá! Que bom falar com você. Me conte em qual município fica a sua lavoura e o que está plantando hoje.", replies: ["Rio Verde, soja e milho", "Jataí, soja", "Silvânia, soja e sorgo"] };
    }

    if (/ver um exemplo|mostrar exemplo|exemplo/.test(value)) {
      profile = { city: "Rio Verde (GO)", crop: "soja → milho safrinha", soil: "solo de textura média", concern: "água" };
      return {
        text: "Exemplo preenchido:\n📍 Rio Verde (GO)\n🌱 soja → milho safrinha\n🟤 solo de textura média\n💧 maior preocupação: água\n\nCom essa ficha, o Órbita Rural pode organizar a leitura da chuva, da água disponível no solo, do calor e do tempo sem planta viva. Nesta página, a resposta é simulada; a decisão deve ser confirmada com um profissional de agronomia.",
        replies: ["Comparar rotações", "Como a água é calculada?", "Começar com meus dados"]
      };
    }

    if (/comecar com meus dados|recomecar|nova conversa/.test(value)) {
      profile = { city: "", crop: "", soil: "", concern: "" };
      return { text: "Certo, vamos começar com os seus dados. Em qual município fica a lavoura?", replies: ["Rio Verde (GO)", "Jataí (GO)", "Silvânia (GO)"] };
    }

    if (/como.*agua|agua.*calcul|chuva.*dado/.test(value)) {
      return { text: "A leitura combina a chuva observada, a necessidade de água da cultura e a capacidade do solo de armazenar água. O resultado serve para comparar cenários — não substitui medição em campo nem recomendação agronômica.", replies: ["Informar meu tipo de solo", "Comparar rotações", "O que mais você analisa?"] };
    }

    if (/o que mais|analisa|dados.*usa/.test(value)) {
      return { text: "Eu organizo quatro grupos de informação: chuva e água no solo, dias de calor forte, cobertura viva da terra e histórico da safra. Também deixo claros os limites e o que ainda precisa ser conferido em campo.", replies: ["Como está minha lavoura?", "Comparar rotações", "Ver um exemplo"] };
    }

    var missing = missingProfile();
    if (/como esta|minha lavoura|plantar agora|comparar|rotac|safra/.test(value) && missing.length) {
      return { text: "Consigo ajudar com isso. Para montar a ficha da lavoura, ainda preciso saber: " + missing.join(", ") + ". Pode escrever tudo em uma mensagem, do seu jeito.", replies: ["Ver um exemplo", "Rio Verde, soja e milho", "Meu foco é água"] };
    }

    if (/comparar|rotac/.test(value) && !missing.length) {
      return {
        text: "Comparação simulada para " + profile.city + ":\n\n1. Manter " + profile.crop + ": preserva o manejo que você já conhece, mas ainda precisa ser conferido no critério “" + profile.concern + "”.\n\n2. Incluir uma cultura de cobertura: pode reduzir o tempo com a terra sem planta viva, mas muda custos e manejo.\n\n3. Avaliar outra segunda safra: altera a necessidade de água e a exposição ao calor.\n\nAntes de decidir, o Órbita Rural mostraria os números e as fontes de cada cenário. Converse com um profissional de agronomia para validar a escolha.",
        replies: ["Como a água é calculada?", "Revisar meus dados", "Nova conversa"]
      };
    }

    if (/corrigir|trocar/.test(value) && /municipio/.test(value)) {
      profile.city = "";
      return { text: "Certo. Qual é o município correto?", replies: ["Rio Verde (GO)", "Jataí (GO)", "Silvânia (GO)"] };
    }

    if (/corrigir|trocar/.test(value) && /plantio|cultura|rotac/.test(value)) {
      profile.crop = "";
      return { text: "Certo. O que você planta hoje?", replies: ["Soja e milho", "Soja e sorgo", "Somente soja"] };
    }

    if (/corrigir|trocar/.test(value) && /solo|terra/.test(value)) {
      profile.soil = "";
      return { text: "Certo. Como é o solo da lavoura?", replies: ["Solo arenoso", "Textura média", "Solo argiloso"] };
    }

    if (/revisar/.test(value)) {
      return {
        text: "Esta é a ficha atual:\n📍 " + (profile.city || "não informado") + "\n🌱 " + (profile.crop || "não informado") + "\n🟤 " + (profile.soil || "não informado") + "\n🎯 " + (profile.concern || "não informado") + "\n\nQual dado deseja corrigir?",
        replies: ["Corrigir município", "Corrigir plantio", "Corrigir tipo de solo"]
      };
    }

    if (!missing.length) {
      return {
        text: "Entendi a sua ficha:\n📍 " + profile.city + "\n🌱 " + profile.crop + "\n🟤 " + profile.soil + "\n🎯 foco em " + profile.concern + "\n\nNesta simulação, eu prepararia uma comparação dos cenários de rotação, mostrando benefício, risco e o que falta confirmar. Quer ver a comparação ou revisar algum dado?",
        replies: ["Comparar rotações", "Revisar meus dados", "Nova conversa"]
      };
    }

    return { text: "Anotei o que você contou. Para eu responder melhor, complete estes dados: " + missing.join(", ") + ". Por exemplo: “Minha lavoura fica em Rio Verde, planto soja e milho, o solo é argiloso e me preocupo com a água”.", replies: ["Ver um exemplo", "Como está minha lavoura?", "Comparar rotações"] };
  }

  async function apiReply(text) {
    var controller = new AbortController();
    var timeout = window.setTimeout(function () { controller.abort(); }, 18000);
    try {
      var response = await fetch(apiBase + "/agente", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ estado: apiState, texto: text }),
        signal: controller.signal
      });
      var data = await response.json();
      if (!response.ok || data.erro) throw new Error(data.erro || "A API não respondeu.");
      apiState = data.estado || apiState;
      return { text: data.resposta || "Recebi sua mensagem.", replies: [] };
    } finally {
      window.clearTimeout(timeout);
    }
  }

  async function send(text) {
    text = String(text || "").trim();
    if (!text || waiting) return;
    waiting = true;
    sendButton.disabled = true;
    input.value = "";
    resizeInput();
    setReplies([]);
    addMessage("user", text);
    showTyping();

    var answer;
    try {
      await new Promise(function (resolve) { window.setTimeout(resolve, 500 + Math.min(text.length * 6, 450)); });
      answer = await softwareReply(text);
      if (!answer && apiBase) answer = await apiReply(text);
      if (!answer) answer = localReply(text);
    } catch (error) {
      answer = await softwareReply(text).catch(function () { return null; });
      if (!answer) answer = localReply(text);
      answer.text = "Não consegui atualizar os dados agora, então usei o modo de demonstração.\n\n" + answer.text;
      apiBase = "";
    }

    hideTyping();
    addMessage("bot", answer.text);
    setReplies([]);
    waiting = false;
    sendButton.disabled = false;
    input.focus();
  }

  function resizeInput() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 116) + "px";
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    send(input.value);
  });

  input.addEventListener("input", resizeInput);
  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  var dateLabel = document.getElementById("dataDaConversa");
  if (dateLabel) dateLabel.textContent = "Hoje · " + todayBR();
  Array.prototype.forEach.call(document.querySelectorAll(".message-time"), function (el) { el.textContent = timeNow(); });
  setReplies(initialReplies);
  resizeInput();
  scrollToEnd();
}());
