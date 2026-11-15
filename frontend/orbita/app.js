/* Base: o painel do ramo nat do time (nathancabrall). Ligação com o motor e telas de resultado geradas com IA (Claude) */
/* A casca do aplicativo: a navegação, o mapa do talhão (do colega), o cadastro em passos, a lista das propriedades,
   a visão geral e a pergunta ao motor (pela API, se houver; senão, pelas respostas guardadas em dados/).
   As constantes NOME_DO_PRODUTO e API_BASE e os textos estão em js/textos.js. */

const R = window.ORBITA_RESULTADO;
const CHAVE_DAS_PROPRIEDADES = 'orbitaRuralPropriedades';
const TALHAO_DE_EXEMPLO = [[-17.7975, -50.9050], [-17.7972, -50.9020], [-17.7995, -50.9008], [-17.8016, -50.9024], [-17.8012, -50.9056]];   // um desenho de exemplo, para o usuário ajustar
const NOTAS_INICIAIS = { agua: 3, solo: 3, renda: 3, erosao: 3 };
const ICONES_DAS_NOTAS = { agua: 'droplets', solo: 'sprout', renda: 'wallet', erosao: 'mountain' };

const state = {
  activePage: 'properties', view: 'register', step: 1,
  drawMode: false, editMode: false, points: TALHAO_DE_EXEMPLO.slice(), markers: [], map: null, polygon: null,
  properties: [], draft: null, result: null, lastSource: 'guardada'
};

/* ---------- utilidades ---------- */
function icons() { if (window.lucide) lucide.createIcons(); }
function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 2800);
}
function quando(iso) {
  const d = new Date(iso);
  return isNaN(d) ? '' : d.toLocaleDateString('pt-BR') + ' às ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}
function apiBase() {
  const daPagina = new URLSearchParams(location.search).get('api');
  return String(daPagina || API_BASE || '').replace(/\/+$/, '');
}
function respostaGuardada(terra) { return (window.ORBITA_RESPOSTAS || {})[terra] || null; }
function ler(resposta, terra) { return window.ORBITA_ADAPTAR(resposta, { complementos: window.ORBITA_COMPLEMENTOS, guardada: respostaGuardada(terra) }); }
function doMunicipio() { const r = respostaGuardada('media'); return r ? ler(r, 'media') : null; }   // chuva, colheita e calendário não mudam com a terra

/* ---------- o que fica guardado neste navegador ---------- */
function carregarPropriedades() {
  try { const lista = JSON.parse(localStorage.getItem(CHAVE_DAS_PROPRIEDADES) || '[]'); state.properties = Array.isArray(lista) ? lista : []; }
  catch (erro) { state.properties = []; }
}
function gravarPropriedades() {
  try { localStorage.setItem(CHAVE_DAS_PROPRIEDADES, JSON.stringify(state.properties)); } catch (erro) { /* sem espaço ou sem permissão: segue só na memória */ }
  const badge = document.getElementById('navCount');
  badge.textContent = state.properties.length;
  badge.hidden = !state.properties.length;
}

/* ---------- navegação ---------- */
function setPage(page) {
  state.activePage = page;
  document.querySelectorAll('[data-page-content]').forEach(el => el.classList.toggle('active', el.dataset.pageContent === page));
  document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.page === page));
  document.getElementById('sidebar').classList.remove('open');
  if (page === 'overview') desenharVisaoGeral();
  if (page === 'properties' && state.view === 'list') desenharLista();
  if (page === 'properties' && state.map) setTimeout(() => state.map.invalidateSize(), 80);
  window.scrollTo({ top: 0 });
}
function setView(view) {
  state.view = view;
  document.querySelectorAll('[data-view]').forEach(el => { el.hidden = el.dataset.view !== view; });
  if (view === 'list') desenharLista();
  if (view === 'register' && state.map) setTimeout(() => state.map.invalidateSize(), 80);
  window.scrollTo({ top: 0 });
}
function setStep(step) {
  state.step = step;
  document.querySelectorAll('.wizard-step').forEach(el => { el.hidden = Number(el.dataset.step) !== step; });
  document.querySelectorAll('.step').forEach(el => el.classList.toggle('active', Number(el.dataset.gotoStep) <= step));
  document.getElementById('registerTitle').textContent = t(step === 1 ? 'cadastro.titulo' : 'cadastro.titulo2');
  document.getElementById('registerSub').textContent = t(step === 1 ? 'cadastro.sub1' : 'cadastro.sub2');
  document.getElementById('stepBack').hidden = step === 1;
  document.getElementById('stepNextLabel').textContent = t(step === 1 ? 'passos.continuar' : 'passos.comparar');
  if (step === 2) desenharDadosLocais();
  if (step === 1 && state.map) setTimeout(() => state.map.invalidateSize(), 80);
  window.scrollTo({ top: 0 });
}
function initNavigation() {
  document.querySelectorAll('[data-page]').forEach(button => button.addEventListener('click', () => {
    if (button.dataset.page === 'properties') setView(state.properties.length ? 'list' : 'register');
    setPage(button.dataset.page);
  }));
  document.getElementById('menuButton').addEventListener('click', () => document.getElementById('sidebar').classList.toggle('open'));
  document.getElementById('newPropertyButton').addEventListener('click', novaPropriedade);
  document.getElementById('backToList').addEventListener('click', () => setView('list'));
  document.getElementById('savedPropertiesButton').addEventListener('click', () => setView('list'));
  document.querySelectorAll('[data-goto-step]').forEach(button => button.addEventListener('click', () => irParaOPasso(Number(button.dataset.gotoStep))));
  document.getElementById('stepBack').addEventListener('click', () => setStep(1));
  document.getElementById('stepNext').addEventListener('click', () => irParaOPasso(state.step + 1));
}
function irParaOPasso(passo) {
  if (passo === 1) return setStep(1);
  if (passo === 2) { if (state.step === 1) return document.getElementById('propertyForm').requestSubmit(); return setStep(2); }
  if (state.step === 1 && !state.draft) return showToast(t('passos.antesSalve'));
  if (state.step === 1) setStep(2);
  comparar();
}

/* ---------- o mapa do talhão (do colega) ---------- */
function polygonArea(points) {   // a área do desenho do usuário, em hectares (não é dado do motor)
  if (points.length < 3) return 0;
  const meanLat = points.reduce((sum, p) => sum + p[0], 0) / points.length;
  const scaleX = 111320 * Math.cos(meanLat * Math.PI / 180);
  const scaleY = 110540;
  let area = 0;
  for (let i = 0; i < points.length; i++) {
    const [lat1, lng1] = points[i];
    const [lat2, lng2] = points[(i + 1) % points.length];
    area += (lng1 * scaleX) * (lat2 * scaleY) - (lng2 * scaleX) * (lat1 * scaleY);
  }
  return Math.abs(area / 2) / 10000;
}
function updatePlotSummary() {
  const area = polygonArea(state.points);
  const centroid = state.points.length ? state.points.reduce((acc, p) => [acc[0] + p[0], acc[1] + p[1]], [0, 0]).map(v => v / state.points.length) : [0, 0];
  document.getElementById('plotArea').textContent = state.points.length >= 3 ? `${area.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} ha` : '—';
  document.getElementById('plotCentroid').textContent = state.points.length ? `${centroid[0].toFixed(4)}, ${centroid[1].toFixed(4)}` : '—';
  document.getElementById('vertexCount').textContent = state.points.length;
  document.getElementById('coordinatesPanel').textContent = state.points.length ? state.points.map((p, i) => `${i + 1}. ${p[0].toFixed(6)}, ${p[1].toFixed(6)}`).join('\n') : t('mapa.semCoordenadas');
}
function renderPolygon() {
  updatePlotSummary();
  if (!state.map) return;
  state.markers.forEach(marker => marker.remove());
  state.markers = [];
  if (state.polygon) { state.polygon.remove(); state.polygon = null; }
  if (state.points.length >= 2) {
    state.polygon = L.polygon(state.points, { color: '#8be36c', weight: 3, fillColor: '#4e9f4a', fillOpacity: .5 }).addTo(state.map);
  }
  state.points.forEach((point, index) => {
    const marker = L.circleMarker(point, { radius: 7, color: '#1e4937', weight: 2, fillColor: '#fff', fillOpacity: 1 }).addTo(state.map);
    if (state.editMode) {
      const draggable = L.marker(point, { draggable: true, opacity: 0, zIndexOffset: 1000 }).addTo(state.map);
      draggable.on('dragend', e => {
        const latlng = e.target.getLatLng();
        state.points[index] = [latlng.lat, latlng.lng];
        renderPolygon();
      });
      state.markers.push(draggable);
    }
    state.markers.push(marker);
  });
}
function enquadrarTalhao() {
  if (state.map && state.polygon && state.points.length >= 3) state.map.fitBounds(state.polygon.getBounds(), { padding: [60, 60] });
}
function initMap() {
  const mapNode = document.getElementById('map');
  if (!window.L) {
    mapNode.innerHTML = '<div style="display:grid;place-items:center;height:100%;padding:30px;text-align:center"></div>';
    mapNode.firstChild.textContent = t('mapa.semMapa');
    updatePlotSummary();
    return;
  }
  const centro = t('municipios')[0].centro;
  state.map = L.map('map', { zoomControl: true, doubleClickZoom: false }).setView(centro, 15);
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19, attribution: 'Imagery © Esri, NASA, USGS'
  }).addTo(state.map);
  state.map.on('click', event => {
    if (!state.drawMode) return;
    state.points.push([event.latlng.lat, event.latlng.lng]);
    renderPolygon();
  });
  renderPolygon();
  enquadrarTalhao();

  document.getElementById('drawButton').addEventListener('click', () => {
    state.drawMode = !state.drawMode;
    state.editMode = false;
    document.getElementById('drawButton').classList.toggle('active', state.drawMode);
    document.getElementById('editButton').classList.remove('active');
    document.getElementById('mapHint').classList.toggle('show', state.drawMode);
    if (state.drawMode && state.points.length) { state.points = []; }
    renderPolygon();
  });
  document.getElementById('editButton').addEventListener('click', () => {
    state.editMode = !state.editMode;
    state.drawMode = false;
    document.getElementById('editButton').classList.toggle('active', state.editMode);
    document.getElementById('drawButton').classList.remove('active');
    document.getElementById('mapHint').classList.remove('show');
    renderPolygon();
    showToast(t(state.editMode ? 'mapa.arraste' : 'mapa.fimEdicao'));
  });
  document.getElementById('clearButton').addEventListener('click', () => {
    state.points = [];
    renderPolygon();
    showToast(t('mapa.removido'));
  });
}

/* ---------- o cadastro (passo 1) ---------- */
function preencherFormulario() {
  const municipios = t('municipios');
  document.getElementById('municipality').innerHTML = municipios.map(m =>
    `<option value="${m.id}" ${m.comDados ? '' : 'disabled'}>${R.esc(m.nome)}${m.comDados ? '' : ' · ' + R.esc(t('cadastro.emBreve'))}</option>`).join('');
  document.getElementById('irrigation').innerHTML = `<option>${R.esc(t('cadastro.semIrrigacao'))}</option><option disabled>Pivô · ${R.esc(t('cadastro.emBreve'))}</option><option disabled>Gotejo · ${R.esc(t('cadastro.emBreve'))}</option>`;
  document.getElementById('propertyName').placeholder = t('cadastro.exemploNome');
  document.getElementById('producerName').placeholder = t('cadastro.exemploProdutor');
}
function desenharClima() {
  const v = doMunicipio();
  if (!v) return;
  const normal = v.porSafra[v.anos.normal], pior = v.porSafra[v.anos.pior];
  const linha = (icone, rotulo, sub, valor) => `<div>${R.icone(icone)}<span>${R.esc(rotulo)}<small>${R.esc(sub)}</small></span><strong>${valor}</strong></div>`;
  document.getElementById('climateMetrics').innerHTML =
    linha('droplet', t('clima.normal'), t('clima.safra', { safra: v.anos.normal }), R.int(normal.chuvaJanela) + ' mm') +
    linha('cloud-off', t('clima.pior'), t('clima.safra', { safra: v.anos.pior }), R.int(pior.chuvaJanela) + ' mm') +
    linha('wheat', t('clima.colheita'), t('clima.regiao'), R.int(pior.rendimento) + ' kg/ha');
  document.getElementById('climateNote').textContent = t('clima.nota');
  document.getElementById('climateSource').textContent = t('clima.fonte');
}
function novaPropriedade() {
  state.draft = null;
  state.points = TALHAO_DE_EXEMPLO.slice();
  state.drawMode = false; state.editMode = false;
  document.getElementById('propertyForm').reset();
  ['drawButton', 'editButton'].forEach(id => document.getElementById(id).classList.remove('active'));
  renderPolygon();
  setPage('properties'); setView('register'); setStep(1);
  setTimeout(enquadrarTalhao, 120);
}
function salvarTalhao(event) {
  event.preventDefault();
  const nome = document.getElementById('propertyName').value.trim(), produtor = document.getElementById('producerName').value.trim();
  if (!nome || !produtor) { showToast(t('cadastro.faltaNome')); document.getElementById(nome ? 'producerName' : 'propertyName').focus(); return; }
  if (state.points.length < 3) { showToast(t('cadastro.faltaTalhao')); return; }
  const municipio = t('municipios').find(m => m.id === document.getElementById('municipality').value) || t('municipios')[0];
  const antes = state.draft || {};
  state.draft = {
    id: antes.id || Date.now().toString(36), nome, produtor, cidadeId: municipio.id, municipio: municipio.nome,
    area: polygonArea(state.points), pontos: state.points.map(p => p.slice()),
    terra: antes.terra || null, notas: antes.notas || Object.assign({}, NOTAS_INICIAIS), rotacao: antes.rotacao || ['soja', 'milho', 'pousio'],
    salvoEm: new Date().toISOString(), comparadoEm: antes.comparadoEm || null
  };
  guardarRascunho();
  showToast(t('cadastro.salvo'));
  setStep(2);
}
function guardarRascunho() {
  const i = state.properties.findIndex(p => p.id === state.draft.id);
  if (i >= 0) state.properties[i] = state.draft; else state.properties.push(state.draft);
  gravarPropriedades();
}

/* ---------- os dados locais (passo 2) ---------- */
function desenharDadosLocais() {
  const p = state.draft, v = doMunicipio(), textos = TEXTOS.pt.locais;
  if (!p) return;
  const gotas = n => '<span class="drops">' + [1, 2, 3].map(i => `<span data-lucide="droplet" class="${i <= n ? 'on' : ''}"></span>`).join('') + '</span>';
  const terras = ['pouca', 'media', 'muita'].map((id, i) => `
    <label class="soil-card ${p.terra === id ? 'selected' : ''}"><input type="radio" name="terra" value="${id}" ${p.terra === id ? 'checked' : ''}>${gotas(i + 1)}
      <strong>${R.esc(textos.terras[id].nome)}</strong><small>${R.esc(textos.terras[id].texto)}</small></label>`).join('');
  const rotacoes = textos.rotacoes.map(r => `<option value="${r.id}" ${r.comDados ? 'selected' : 'disabled'}>${R.esc(r.nome)}${r.comDados ? '' : ' · ' + R.esc(t('cadastro.emBreve'))}</option>`).join('');
  const notas = ['agua', 'solo', 'renda', 'erosao'].map(id => `
    <div class="score-row"><div><strong>${R.icone(ICONES_DAS_NOTAS[id])}${R.esc(textos.notas[id].nome)}</strong><small>${R.esc(textos.notas[id].texto)}</small></div>
      <div class="score" data-nota="${id}" role="group" aria-label="${R.esc(textos.notas[id].nome)}">${[1, 2, 3, 4, 5].map(n =>
        `<button type="button" data-valor="${n}" class="${n === p.notas[id] ? 'on' : n < p.notas[id] ? 'under' : ''}" aria-pressed="${n === p.notas[id]}">${n}</button>`).join('')}</div></div>`).join('');
  document.getElementById('localDataRoot').innerHTML = `
    <div class="plot-recap">${R.icone('map-pin')}<strong>${R.esc(p.nome)}</strong><span>${R.esc(p.produtor)}</span><span>${R.esc(p.municipio)}</span>
      <span>${R.esc(t('mapa.area'))}: <b>${R.um(p.area)} ha</b></span></div>
    <div class="local-grid">
      <article class="panel local-card"><h2>${R.icone('layers')}${R.esc(textos.terraTitulo)}</h2><p class="sub">${R.esc(textos.terraSub)}</p>
        <h3>${R.esc(textos.terraPergunta)}</h3><div class="soil-options" role="radiogroup" aria-label="${R.esc(textos.terraPergunta)}">${terras}</div><p class="field-error" id="soilError" role="alert"></p>
        <h3>${R.esc(textos.rotacaoPergunta)}</h3><select class="rotation-select" id="rotationSelect">${rotacoes}</select>
        <p class="form-note">${R.esc(textos.comparaCom)}</p>
        <div class="rot-line alt"><b>${R.esc(textos.alternativa)}</b><span>${R.esc(v ? v.nomes.alternativa : '')}</span></div></article>
      <article class="panel local-card"><h2>${R.icone('scale')}${R.esc(textos.notasTitulo)}</h2><p class="sub">${R.esc(textos.notasSub)}</p>${notas}
        <div class="score-scale"><span>${R.esc(textos.pouco)}</span><span>${R.esc(textos.muito)}</span></div></article>
    </div>`;
  icons();
}
function initDadosLocais() {
  const raiz = document.getElementById('localDataRoot');
  raiz.addEventListener('change', event => {
    if (event.target.name !== 'terra' || !state.draft) return;
    state.draft.terra = event.target.value;
    raiz.querySelectorAll('.soil-card').forEach(card => card.classList.toggle('selected', card.querySelector('input').checked));
    document.getElementById('soilError').textContent = '';
    guardarRascunho();
  });
  raiz.addEventListener('click', event => {
    const botao = event.target.closest('.score button');
    if (!botao || !state.draft) return;
    const grupo = botao.parentElement, valor = Number(botao.dataset.valor);
    state.draft.notas[grupo.dataset.nota] = valor;
    grupo.querySelectorAll('button').forEach(b => {
      const n = Number(b.dataset.valor);
      b.className = n === valor ? 'on' : n < valor ? 'under' : '';
      b.setAttribute('aria-pressed', n === valor);
    });
    guardarRascunho();
  });
}

/* ---------- a pergunta ao motor: pela API, se houver; senão, pelas respostas guardadas ---------- */
async function chamarApi(rota, corpo) {
  const controle = new AbortController(), relogio = setTimeout(() => controle.abort(), 8000);
  try {
    const resposta = await fetch(apiBase() + rota, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo), signal: controle.signal });
    if (!resposta.ok) throw new Error('HTTP ' + resposta.status);
    return await resposta.json();
  } finally { clearTimeout(relogio); }
}
async function perguntarAoMotor(entrada) {
  const guardada = respostaGuardada(entrada.terra);
  if (!apiBase()) return { resposta: guardada, origem: 'guardada' };
  try {
    const resposta = await chamarApi('/recomendacao', entrada);
    if (!resposta || !resposta.rotacoes || !resposta.veredito) throw new Error('resposta fora do formato');
    return { resposta, origem: 'api' };
  } catch (erro) { return { resposta: guardada, origem: 'falhou' }; }
}
function entradaDe(p) { return { cidade_id: p.cidadeId, rotacao_atual: p.rotacao, prioridades: p.notas, terra: p.terra }; }
async function comparar(propriedade) {
  const p = propriedade || state.draft;
  if (!p) return showToast(t('passos.antesSalve'));
  if (!p.terra) {
    const erro = document.getElementById('soilError');
    if (erro) { erro.textContent = t('passos.antesTerra'); const primeiro = document.querySelector('input[name=terra]'); if (primeiro) primeiro.focus(); }
    return showToast(t('passos.antesTerra'));
  }
  const botao = document.getElementById('stepNext'), rotulo = document.getElementById('stepNextLabel');
  botao.disabled = true; rotulo.textContent = t('passos.comparando');
  const { resposta, origem } = await perguntarAoMotor(entradaDe(p));
  botao.disabled = false; rotulo.textContent = t('passos.comparar');
  if (!resposta) return showToast(t('fonte.apiFalhou'));
  p.comparadoEm = new Date().toISOString();
  state.draft = p; guardarRascunho();
  state.lastSource = origem;
  state.result = { prop: p, bruto: resposta, v: ler(resposta, p.terra), origem, tab: 'produtor', ano: 'normal', mensagem: null };
  desenharFonte();
  desenharResultado();
  setPage('properties'); setView('result');
  if (origem === 'api') {   // o texto curto para mensagem, do próprio motor, com as notas desta pergunta
    chamarApi('/mensagem', entradaDe(p)).then(m => {
      if (!m || typeof m.texto !== 'string' || !state.result || state.result.prop !== p) return;
      state.result.mensagem = m.texto;
      const caixa = document.getElementById('resumoTexto'); if (caixa) caixa.textContent = m.texto;
    }).catch(() => {});
  }
}

/* ---------- o resultado ---------- */
function estadoDoResultado() { const x = state.result; return { ano: x.ano, notas: x.prop.notas, propriedade: x.prop, mensagem: x.mensagem }; }
function notaDaFonte(origem, v) {
  const gerado = quando(v.geradoEm);
  if (origem === 'api') return t('fonte.notaApi', { onde: apiBase() });
  return t(origem === 'falhou' ? 'fonte.notaFalhou' : 'fonte.notaGuardada', { quando: gerado });
}
function desenharResultado() {
  const x = state.result, p = x.prop, tr = TEXTOS.pt.resultado;
  document.getElementById('resultRoot').innerHTML = `
    <div class="page-heading property-heading result-heading">
      <button class="back-button" data-acao="lista" aria-label="${R.esc(t('passos.voltar'))}">${R.icone('arrow-left')}</button>
      <div><span class="eyebrow">${R.esc(tr.sobre)}</span><h1>${R.esc(p.nome)}</h1>
        <p class="chips"><span class="chip">${R.icone('map-pin')}${R.esc(p.municipio)}</span><span class="chip">${R.icone('layers')}${R.esc(tr.terraChip[p.terra] || '')}</span>
          <span class="chip">${R.icone('land-plot')}${R.um(p.area)} ha</span><span class="chip">${R.icone('user')}${R.esc(p.produtor)}</span></p></div>
      <button class="ghost-action" data-acao="alterar">${R.icone('sliders-horizontal')}${R.esc(tr.alterar)}</button>
    </div>
    <div class="result-bar">
      <div class="tabs" role="tablist">
        <button role="tab" data-tab="produtor" aria-selected="${x.tab === 'produtor'}" class="${x.tab === 'produtor' ? 'active' : ''}">${R.icone('sprout')}${R.esc(tr.abaProdutor)} <small>· ${R.esc(tr.abaProdutorSub)}</small></button>
        <button role="tab" data-tab="agronomo" aria-selected="${x.tab === 'agronomo'}" class="${x.tab === 'agronomo' ? 'active' : ''}">${R.icone('microscope')}${R.esc(tr.abaAgronomo)} <small>· ${R.esc(tr.abaAgronomoSub)}</small></button>
      </div>
      <span class="source-note ${x.origem === 'api' ? 'live' : ''}" id="sourceNote"><i></i>${R.esc(notaDaFonte(x.origem, x.v))}</span>
    </div>
    <div id="tabBody" role="tabpanel"></div>`;
  desenharAba();
}
function desenharAba() {
  const x = state.result;
  document.getElementById('tabBody').innerHTML = x.tab === 'produtor' ? R.produtor(x.v, estadoDoResultado()) : R.agronomo(x.v, window.ORBITA_VALIDACAO);
  icons();
}
function trocarAba(aba) {
  state.result.tab = aba;
  document.querySelectorAll('#resultRoot [data-tab]').forEach(b => { b.classList.toggle('active', b.dataset.tab === aba); b.setAttribute('aria-selected', b.dataset.tab === aba); });
  desenharAba();
  window.scrollTo({ top: 0 });
}
async function copiarResumo() {
  const texto = document.getElementById('resumoTexto').textContent;
  let copiou = false;
  try { await navigator.clipboard.writeText(texto); copiou = true; } catch (erro) {
    const area = document.createElement('textarea');
    area.value = texto; area.setAttribute('readonly', ''); area.style.position = 'fixed'; area.style.opacity = '0';
    document.body.appendChild(area); area.select();
    try { copiou = document.execCommand('copy'); } catch (outro) { copiou = false; }
    area.remove();
  }
  showToast(t(copiou ? 'resultado.mensagem.copiado' : 'resultado.mensagem.naoCopiou'));
  return copiou;
}
function baixarResposta() {
  const x = state.result, arquivo = new Blob([JSON.stringify(x.bruto, null, 1)], { type: 'application/json' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(arquivo);
  link.download = `resposta-do-motor-${x.prop.terra}.json`;
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 2000);
  showToast(t('agro.baixado'));
}
function initResultado() {
  document.getElementById('resultRoot').addEventListener('click', event => {
    const alvo = event.target.closest('[data-tab],[data-ano],[data-acao],[data-filtro]');
    if (!alvo || !state.result) return;
    if (alvo.dataset.tab) return trocarAba(alvo.dataset.tab);
    if (alvo.dataset.ano) {
      state.result.ano = alvo.dataset.ano;
      document.querySelectorAll('#resultRoot [data-ano]').forEach(b => b.classList.toggle('active', b === alvo));
      document.getElementById('waterBody').innerHTML = R.agua(state.result.v, state.result.ano);
      return icons();
    }
    if (alvo.dataset.filtro) {
      document.querySelectorAll('#resultRoot [data-filtro]').forEach(b => b.classList.toggle('active', b === alvo));
      return document.querySelectorAll('#parametrosBox tbody tr').forEach(tr => { tr.hidden = alvo.dataset.filtro === 'hipotese' && tr.dataset.etiqueta === 'publicado'; });
    }
    const acao = alvo.dataset.acao;
    if (acao === 'copiar') copiarResumo();
    if (acao === 'baixar') baixarResposta();
    if (acao === 'aba-agronomo') trocarAba('agronomo');
    if (acao === 'lista') setView('list');
    if (acao === 'alterar') alterarDados(state.result.prop);
  });
}
function alterarDados(p) {
  state.draft = p;
  state.points = (p.pontos || TALHAO_DE_EXEMPLO).map(x => x.slice());
  document.getElementById('propertyName').value = p.nome;
  document.getElementById('producerName').value = p.produtor;
  renderPolygon();
  setPage('properties'); setView('register'); setStep(2);
  setTimeout(enquadrarTalhao, 120);
}

/* ---------- a lista das propriedades ---------- */
function linhasDasPropriedades() {
  const tl = TEXTOS.pt.lista, terras = TEXTOS.pt.locais.terras, rotacao = TEXTOS.pt.locais.rotacoes[0].nome;
  return state.properties.map(p => `<tr>
    <td><strong>${R.esc(p.nome)}</strong><small>${R.esc(p.produtor)}</small></td><td>${R.esc(p.municipio)}</td><td>${R.um(p.area)} ha</td>
    <td>${p.terra ? R.esc(terras[p.terra].nome) : '—'}</td><td>${R.esc(rotacao)}</td>
    <td><span class="status ${p.comparadoEm ? 'success' : 'warning'}">${R.esc(p.comparadoEm ? t('lista.comparada', { quando: quando(p.comparadoEm) }) : tl.semComparacao)}</span></td>
    <td><div class="row-actions"><button class="go" data-abrir="${R.esc(p.id)}">${R.icone('git-compare-arrows')}${R.esc(p.comparadoEm ? tl.abrir : tl.comparar)}</button>
      <button data-editar="${R.esc(p.id)}" aria-label="${R.esc(tl.editar)}" title="${R.esc(tl.editar)}">${R.icone('pencil')}</button>
      <button data-apagar="${R.esc(p.id)}" aria-label="${R.esc(tl.apagar)}" title="${R.esc(tl.apagar)}">${R.icone('trash-2')}</button></div></td></tr>`).join('');
}
function tabelaDasPropriedades() {
  const tl = TEXTOS.pt.lista;
  if (!state.properties.length) return `<div class="empty-state">${R.icone('sprout')}<h3>${R.esc(tl.vaziaTitulo)}</h3><p>${R.esc(tl.vaziaTexto)}</p>
    <button class="primary-action" data-nova>${R.icone('plus')}${R.esc(tl.nova)}</button></div>`;
  return `<div class="table-wrap"><table><thead><tr>${tl.colunas.map(c => `<th>${R.esc(c)}</th>`).join('')}</tr></thead><tbody>${linhasDasPropriedades()}</tbody></table></div>`;
}
function desenharLista() {
  document.getElementById('propertiesList').innerHTML = tabelaDasPropriedades();
  icons();
}
function cliqueNaTabela(event) {
  const alvo = event.target.closest('[data-abrir],[data-editar],[data-apagar],[data-nova]');
  if (!alvo) return;
  if (alvo.dataset.nova !== undefined) return novaPropriedade();
  const id = alvo.dataset.abrir || alvo.dataset.editar || alvo.dataset.apagar, p = state.properties.find(x => x.id === id);
  if (!p) return;
  if (alvo.dataset.apagar) {
    state.properties = state.properties.filter(x => x.id !== id);
    gravarPropriedades(); showToast(t('lista.apagada'));
    if (state.activePage === 'overview') desenharVisaoGeral(); else desenharLista();
    return;
  }
  if (alvo.dataset.editar || !p.terra) return alterarDados(p);
  comparar(p);
}

/* ---------- a visão geral: só números do motor e das propriedades cadastradas ---------- */
function desenharVisaoGeral() {
  const v = doMunicipio(), tv = TEXTOS.pt.visao, raiz = document.getElementById('overviewRoot');
  if (!v) { raiz.innerHTML = ''; return; }
  const normal = v.porSafra[v.anos.normal], pior = v.porSafra[v.anos.pior], n = state.properties.length;
  const cartao = (cor, icone, rotulo, valor, nota) => `<article class="metric-card"><span class="metric-icon ${cor}">${R.icone(icone)}</span><div><small>${R.esc(rotulo)}</small><strong>${valor}</strong><em>${R.esc(nota)}</em></div></article>`;
  raiz.innerHTML = `
    <div class="page-heading"><div><span class="eyebrow">${R.esc(tv.sobre)}</span><h1>${R.esc(tv.titulo)}</h1><p>${R.esc(tv.sub)}</p></div>
      <button class="primary-action" data-nova>${R.icone('plus')}${R.esc(tv.nova)}</button></div>
    <div class="metric-grid">
      ${cartao('green', 'land-plot', tv.cartoes.propriedades, n, n ? tv.cartoes.neste : tv.cartoes.nenhuma)}
      ${cartao('violet', 'map-pin', tv.cartoes.municipio, R.esc(v.cidade), tv.cartoes.outros)}
      ${cartao('blue', 'cloud-rain', tv.cartoes.normal, R.int(normal.chuvaJanela) + ' mm', t('visao.cartoes.safra', { safra: v.anos.normal, kg: R.int(normal.rendimento) }))}
      ${cartao('amber', 'cloud-off', tv.cartoes.pior, R.int(pior.chuvaJanela) + ' mm', t('visao.cartoes.safra', { safra: v.anos.pior, kg: R.int(pior.rendimento) }))}
    </div>
    <div class="overview-two">
      <article class="panel block"><div class="panel-head"><div><span class="eyebrow">${R.esc(tv.chuvaSobre)}</span><h2>${R.esc(tv.chuvaTitulo)}</h2></div></div>
        ${R.chuvaDupla(v)}<p class="rain-foot">${R.esc(tv.chuvaTexto)}</p></article>
      <article class="panel block mini-years"><div class="panel-head"><div><span class="eyebrow">${R.esc(tv.anoSobre)}</span><h2>${R.esc(tv.anoTitulo)}</h2></div></div>
        <p class="rain-foot" style="margin:0 0 12px">${R.esc(tv.anoTexto)}</p>${v.anoDaTerra ? R.linhasDoAno(v, true) + R.legendaDoAno(v.anoDaTerra) : ''}</article>
    </div>
    <article class="panel properties-table-panel"><div class="panel-head"><div><span class="eyebrow">${R.esc(tv.tabelaSobre)}</span><h2>${R.esc(tv.tabelaTitulo)}</h2></div>
      <button class="text-button" data-gerenciar>${R.esc(tv.gerenciar)}</button></div>${n ? tabelaDasPropriedades() : `<p class="rain-foot" style="padding:6px 0 4px">${R.esc(tv.semPropriedade)}</p>`}</article>`;
  icons();
}
function initVisaoGeral() {
  document.getElementById('overviewRoot').addEventListener('click', event => {
    if (event.target.closest('[data-gerenciar]')) { setView(state.properties.length ? 'list' : 'register'); return setPage('properties'); }
    cliqueNaTabela(event);
  });
  document.getElementById('propertiesList').addEventListener('click', cliqueNaTabela);
}

/* ---------- a casca: os textos fixos, a fonte dos números, a ajuda e as telas de exemplo ---------- */
function aplicarTextos() {
  document.title = NOME_DO_PRODUTO + ' | Painel';
  document.getElementById('brandName').innerHTML = R.esc(NOME_DO_PRODUTO.toUpperCase()).replace(' ', '<br>');
  document.querySelector('.brand').setAttribute('aria-label', NOME_DO_PRODUTO);
  document.querySelectorAll('[data-t]').forEach(el => { el.textContent = t(el.dataset.t); });
  const r = TEXTOS.pt.rodape;
  document.getElementById('appFooter').innerHTML = [NOME_DO_PRODUTO + ' · ' + r.prototipo, r.dados, r.ia, r.demo].map(x => `<p>${R.esc(x)}</p>`).join('');
}
function desenharFonte() {
  const c = window.ORBITA_COMPLEMENTOS || {}, aoVivo = state.lastSource === 'api';
  const linha = aoVivo ? t('fonte.api') : state.lastSource === 'falhou' ? t('fonte.apiFalhou') : t('fonte.guardada');
  document.getElementById('dataSource').innerHTML = `<b>${R.esc(t('fonte.titulo'))}</b><span class="live ${aoVivo ? '' : 'off'}"></span>${R.esc(linha)}` +
    (aoVivo || !c.gerado_em ? '' : `<br>${R.esc(t('fonte.geradaEm', { quando: quando(c.gerado_em) }))}`);
}
function initAjuda() {
  const fundo = document.getElementById('modalBackdrop'), fechar = () => { fundo.hidden = true; };
  document.getElementById('helpButton').addEventListener('click', () => {
    document.getElementById('modalTitle').textContent = t('ajuda.titulo');
    document.getElementById('modalText').textContent = t('ajuda.texto');
    document.getElementById('modalConfirm').textContent = t('ajuda.fechar');
    fundo.hidden = false;
  });
  document.getElementById('modalClose').addEventListener('click', fechar);
  document.getElementById('modalConfirm').addEventListener('click', fechar);
  fundo.addEventListener('click', e => { if (e.target === fundo) fechar(); });
}
function initTelasDeExemplo() {   // do colega: o calendário e os avisos das telas de demonstração
  const days = [26, 27, 28, 29, 30, 31, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 1, 2, 3, 4, 5, 6];
  const grid = document.getElementById('calendarGrid');
  if (grid) grid.innerHTML = days.map((day, i) => `<button class="${i < 6 || i > 35 ? 'muted ' : ''}${day === 14 && i > 6 ? 'today ' : ''}${[20, 23, 26].includes(i) ? 'event' : ''}">${day}</button>`).join('');
  const aviso = 'Tela de demonstração: esta ação ainda não está ligada.';
  ['newDemand', 'exportReport'].forEach(id => { const b = document.getElementById(id); if (b) b.addEventListener('click', () => showToast(aviso)); });
}

document.addEventListener('DOMContentLoaded', () => {
  aplicarTextos();
  preencherFormulario();
  carregarPropriedades();
  gravarPropriedades();
  initNavigation();
  initMap();
  document.getElementById('propertyForm').addEventListener('submit', salvarTalhao);
  document.getElementById('coordinatesButton').addEventListener('click', () => { const painel = document.getElementById('coordinatesPanel'); painel.hidden = !painel.hidden; });
  initDadosLocais();
  initResultado();
  initVisaoGeral();
  initAjuda();
  initTelasDeExemplo();
  desenharClima();
  desenharFonte();
  setStep(1);
  setView(state.properties.length ? 'list' : 'register');
  icons();
});
