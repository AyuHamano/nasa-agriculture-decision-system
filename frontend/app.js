// ---------- Config ----------
const STORAGE_KEY = 'orbitaRuralProperties';
const MUNICIPALITY_ZOOM = 12;

// Municipalities covered by the MVP (center as [lat, lng])
const MUNICIPALITIES = [
  { name: 'Rio Verde, GO', center: [-17.79, -50.92] },
  { name: 'Silvânia, GO', center: [-16.66, -48.61] },
  { name: 'Espumoso, RS', center: [-28.725, -52.85] }
];

// ---------- State ----------
// Coordinate order: Leaflet uses [lat, lng], GeoJSON and Turf use [lng, lat].
// `state.points` is always [lat, lng]; the swap only happens in the two
// conversion functions below.
const state = {
  map: null,
  plotLayer: null,    // layer group holding the polygon and the vertex markers
  points: [],         // vertices of the plot, [lat, lng]
  mode: 'idle',       // 'idle' | 'draw' | 'edit'
  editingId: null     // id of the saved property being edited, if any
};

const $ = id => document.getElementById(id);

// ---------- Helpers ----------
function showToast(message) {
  const toast = $('toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 2800);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function pointsToFeature(points) {
  const ring = points.map(([lat, lng]) => [lng, lat]);
  ring.push(ring[0]); // GeoJSON rings must be closed
  return turf.polygon([ring]);
}

function featureToPoints(feature) {
  return feature.geometry.coordinates[0].slice(0, -1).map(([lng, lat]) => [lat, lng]);
}

// Returns null while there are fewer than 3 vertices
function getPlotMetrics(points) {
  if (points.length < 3) return null;
  const feature = pointsToFeature(points);
  const [lng, lat] = turf.centerOfMass(feature).geometry.coordinates;
  return {
    feature,
    areaHa: turf.area(feature) / 10000, // turf.area returns m²
    center: [lat, lng],
    selfIntersects: turf.kinks(feature).features.length > 0
  };
}

function loadProperties() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
  } catch {
    return [];
  }
}

function storeProperties(properties) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(properties));
  $('savedCount').textContent = properties.length;
}

// ---------- Navigation ----------
function showPage(page) {
  document.querySelectorAll('[data-page]').forEach(el => el.classList.toggle('active', el.dataset.page === page));
  document.querySelectorAll('.tab').forEach(el => el.classList.toggle('active', el.dataset.tab === page));
  if (page === 'saved') renderSavedList();
  if (page === 'register') state.map.invalidateSize(); // the map was hidden
  window.scrollTo({ top: 0 });
}

function initNavigation() {
  document.querySelectorAll('[data-tab]').forEach(button => {
    button.addEventListener('click', () => {
      // Opening the register tab while editing starts a fresh registration
      if (button.dataset.tab === 'register' && state.editingId) resetForm();
      showPage(button.dataset.tab);
    });
  });
}

// ---------- Map ----------
function initMap() {
  if (!window.L) {
    $('map').innerHTML = '<p style="padding:30px;color:#fff">Não foi possível carregar o mapa. Verifique sua conexão com a internet.</p>';
    return;
  }
  state.map = L.map('map', { doubleClickZoom: false }).setView([-15.5, -51.5], 5);

  // Base maps the user can switch between (satellite is the default)
  const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: 'Imagery © Esri, NASA, USGS'
  });
  const streets = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors'
  });
  satellite.addTo(state.map);
  L.control.layers({ 'Satélite': satellite, 'Ruas': streets }, null, { collapsed: false }).addTo(state.map);

  state.plotLayer = L.layerGroup().addTo(state.map);

  state.map.on('click', event => {
    if (state.mode !== 'draw') return;
    state.points.push([event.latlng.lat, event.latlng.lng]);
    renderPlot();
  });
}

function setMode(mode) {
  state.mode = mode;
  $('drawButton').classList.toggle('active', mode === 'draw');
  $('editButton').classList.toggle('active', mode === 'edit');
  $('drawLabel').textContent = mode === 'draw' ? 'Concluir desenho' : 'Desenhar polígono';
  $('mapHint').classList.toggle('show', mode === 'draw');
  $('map').classList.toggle('drawing', mode === 'draw');
  renderPlot(); // vertices are draggable only in edit mode
}

// Redraws the polygon and its vertex markers from state.points
function renderPlot() {
  state.plotLayer.clearLayers();

  const polygon = L.polygon(state.points, {
    color: '#7fce3f', weight: 3, fillColor: '#7fce3f', fillOpacity: 0.3, interactive: false
  }).addTo(state.plotLayer);

  state.points.forEach((point, index) => {
    const marker = L.marker(point, {
      draggable: state.mode === 'edit',
      icon: L.divIcon({
        className: 'vertex' + (state.mode === 'edit' ? ' draggable' : ''),
        iconSize: [16, 16]
      })
    }).addTo(state.plotLayer);

    // Update the shape while dragging without rebuilding the markers
    marker.on('drag', () => {
      const { lat, lng } = marker.getLatLng();
      state.points[index] = [lat, lng];
      polygon.setLatLngs(state.points);
      updateSummary();
    });
  });

  updateSummary();
}

function updateSummary() {
  const metrics = getPlotMetrics(state.points);
  $('plotArea').textContent = metrics ? `${metrics.areaHa.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} ha` : '—';
  $('plotCentroid').textContent = metrics ? metrics.center.map(v => v.toFixed(4)).join(', ') : '—';
  $('vertexCount').textContent = state.points.length;
  $('coordinatesPanel').textContent = state.points.length
    ? state.points.map((p, i) => `${i + 1}. ${p[0].toFixed(6)}, ${p[1].toFixed(6)}`).join('\n')
    : 'Nenhuma coordenada definida.';
}

function initMapTools() {
  $('drawButton').addEventListener('click', () => {
    if (state.mode === 'draw') return setMode('idle'); // finish drawing
    state.points = []; // a new drawing replaces the previous one
    setMode('draw');
  });

  $('editButton').addEventListener('click', () => {
    if (!state.points.length) return showToast('Desenhe o talhão antes de editar os pontos.');
    setMode(state.mode === 'edit' ? 'idle' : 'edit');
    if (state.mode === 'edit') showToast('Arraste os pontos para ajustar o talhão.');
  });

  $('clearButton').addEventListener('click', () => {
    state.points = [];
    setMode('idle');
  });

  $('coordinatesButton').addEventListener('click', () => {
    $('coordinatesPanel').hidden = !$('coordinatesPanel').hidden;
  });
}

// ---------- Form ----------
function initForm() {
  $('municipality').innerHTML = '<option value="">Selecione o município</option>' +
    MUNICIPALITIES.map(m => `<option value="${m.name}">${m.name}</option>`).join('');

  $('municipality').addEventListener('change', event => {
    const municipality = MUNICIPALITIES.find(m => m.name === event.target.value);
    if (municipality) state.map.flyTo(municipality.center, MUNICIPALITY_ZOOM, { duration: 0.8 });
  });

  $('propertyForm').addEventListener('submit', saveProperty);
}

function resetForm() {
  $('propertyForm').reset();
  state.editingId = null;
  state.points = [];
  $('registerTitle').textContent = 'Cadastrar propriedade';
  $('saveButton').lastChild.textContent = 'Salvar cadastro';
  setMode('idle');
}

function saveProperty(event) {
  event.preventDefault();
  const metrics = getPlotMetrics(state.points);
  if (!metrics) return showToast('Desenhe pelo menos três pontos para salvar o talhão.');
  if (metrics.selfIntersects) return showToast('As linhas do talhão se cruzam. Ajuste os pontos antes de salvar.');

  const record = {
    id: state.editingId || Date.now().toString(36),
    savedAt: new Date().toISOString(),
    producer: {
      name: $('producerName').value.trim(),
      document: $('documentNumber').value.trim(),
      phone: $('phoneNumber').value.trim(),
      email: $('emailAddress').value.trim()
    },
    property: {
      name: $('propertyName').value.trim(),
      municipality: $('municipality').value,
      declaredAreaHa: $('declaredArea').value,
      soil: $('soil').value,
      irrigation: $('irrigation').value,
      rotation: $('rotation').value
    },
    areaHa: Number(metrics.areaHa.toFixed(2)),
    plot: metrics.feature // GeoJSON Feature, coordinates as [lng, lat]
  };

  // Replace the record when editing, otherwise add a new one
  const properties = loadProperties().filter(p => p.id !== record.id);
  properties.push(record);
  storeProperties(properties);

  showToast(`${record.property.name} foi salva.`);
  resetForm();
  showPage('saved');
}

// Loads a saved property into the form and map for viewing or editing
function openProperty(id) {
  const record = loadProperties().find(p => p.id === id);
  if (!record) return;

  resetForm();
  state.editingId = record.id;
  $('producerName').value = record.producer.name;
  $('documentNumber').value = record.producer.document;
  $('phoneNumber').value = record.producer.phone;
  $('emailAddress').value = record.producer.email;
  $('propertyName').value = record.property.name;
  $('municipality').value = record.property.municipality;
  $('declaredArea').value = record.property.declaredAreaHa;
  $('soil').value = record.property.soil;
  $('irrigation').value = record.property.irrigation;
  $('rotation').value = record.property.rotation;
  $('registerTitle').textContent = 'Editar propriedade';
  $('saveButton').lastChild.textContent = 'Salvar alterações';

  state.points = featureToPoints(record.plot);
  showPage('register');
  renderPlot();
  state.map.fitBounds(L.polygon(state.points).getBounds(), { padding: [40, 40] });
}

// ---------- Saved properties ----------
function renderSavedList() {
  const properties = loadProperties();
  $('savedTable').hidden = !properties.length;
  $('emptyState').hidden = properties.length > 0;

  $('savedRows').innerHTML = properties.map(p => `
    <tr>
      <td><strong>${escapeHtml(p.property.name)}</strong><small>${escapeHtml(p.producer.name)}</small></td>
      <td>${escapeHtml(p.property.municipality)}</td>
      <td>${p.areaHa.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} ha</td>
      <td>${new Date(p.savedAt).toLocaleDateString('pt-BR')}</td>
      <td class="row-actions">
        <button data-action="open" data-id="${p.id}">Ver no mapa</button>
        <button class="danger" data-action="delete" data-id="${p.id}">Excluir</button>
      </td>
    </tr>`).join('');
}

function initSavedList() {
  $('savedRows').addEventListener('click', event => {
    const button = event.target.closest('button[data-action]');
    if (!button) return;
    if (button.dataset.action === 'open') return openProperty(button.dataset.id);

    if (confirm('Excluir esta propriedade?')) {
      storeProperties(loadProperties().filter(p => p.id !== button.dataset.id));
      renderSavedList();
    }
  });
}

// ---------- Start ----------
document.addEventListener('DOMContentLoaded', () => {
  initMap();
  if (!state.map) return;
  initNavigation();
  initMapTools();
  initForm();
  initSavedList();
  storeProperties(loadProperties()); // refreshes the counter in the tab
  if (window.lucide) lucide.createIcons();
});