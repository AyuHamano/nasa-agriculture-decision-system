const state = {
  activePage: 'properties',
  drawMode: false,
  editMode: false,
  points: [
    [-17.7898, -50.9236], [-17.7865, -50.9178], [-17.7892, -50.9122],
    [-17.7960, -50.9135], [-17.7968, -50.9209]
  ],
  markers: [],
  map: null,
  polygon: null
};

const climateByCity = {
  '-16.6869,-49.2648': { rain: '1.570 mm', dry: 'Mai–Set', risk: 'Moderado' },
  '-17.7923,-50.9190': { rain: '1.480 mm', dry: 'Mai–Set', risk: 'Moderado' },
  '-17.8814,-51.7144': { rain: '1.615 mm', dry: 'Mai–Ago', risk: 'Baixo' },
  '-18.9146,-48.2754': { rain: '1.420 mm', dry: 'Mai–Set', risk: 'Moderado' }
};

function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 2600);
}

function setPage(page) {
  state.activePage = page;
  document.querySelectorAll('[data-page-content]').forEach(el => el.classList.toggle('active', el.dataset.pageContent === page));
  document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.page === page));
  document.getElementById('sidebar').classList.remove('open');
  if (page === 'properties' && state.map) setTimeout(() => state.map.invalidateSize(), 80);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function initNavigation() {
  document.querySelectorAll('[data-page]').forEach(button => button.addEventListener('click', () => setPage(button.dataset.page)));
  document.querySelectorAll('[data-go]').forEach(button => button.addEventListener('click', () => setPage(button.dataset.go)));
  document.getElementById('menuButton').addEventListener('click', () => document.getElementById('sidebar').classList.toggle('open'));
}

function polygonArea(points) {
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
  document.getElementById('plotArea').textContent = `${area.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} ha`;
  document.getElementById('plotCentroid').textContent = state.points.length ? `${centroid[0].toFixed(4)}, ${centroid[1].toFixed(4)}` : '—';
  document.getElementById('vertexCount').textContent = state.points.length;
  document.getElementById('coordinatesPanel').textContent = state.points.length ? state.points.map((p, i) => `${i + 1}. ${p[0].toFixed(6)}, ${p[1].toFixed(6)}`).join('\n') : 'Nenhuma coordenada definida.';
}

function renderPolygon() {
  if (!state.map) return;
  state.markers.forEach(marker => marker.remove());
  state.markers = [];
  if (state.polygon) state.polygon.remove();
  if (state.points.length >= 2) {
    state.polygon = L.polygon(state.points, { color: '#8be36c', weight: 3, fillColor: '#4e9f4a', fillOpacity: .5 }).addTo(state.map);
  }
  state.points.forEach((point, index) => {
    const marker = L.circleMarker(point, { radius: 7, color: '#1e4937', weight: 2, fillColor: '#fff', fillOpacity: 1, draggable: false }).addTo(state.map);
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
  updatePlotSummary();
}

function initMap() {
  const mapNode = document.getElementById('map');
  if (!window.L) {
    mapNode.innerHTML = '<div style="display:grid;place-items:center;height:100%;padding:30px;text-align:center">Não foi possível carregar o mapa. Verifique sua conexão com a internet.</div>';
    return;
  }
  state.map = L.map('map', { zoomControl: true, doubleClickZoom: false }).setView([-17.7923, -50.9190], 15);
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19, attribution: 'Imagery © Esri, NASA, USGS'
  }).addTo(state.map);
  state.map.on('click', event => {
    if (!state.drawMode) return;
    state.points.push([event.latlng.lat, event.latlng.lng]);
    renderPolygon();
  });
  renderPolygon();
  state.map.fitBounds(state.polygon.getBounds(), { padding: [60, 60] });

  document.getElementById('drawButton').addEventListener('click', () => {
    state.drawMode = !state.drawMode;
    state.editMode = false;
    document.getElementById('drawButton').classList.toggle('active', state.drawMode);
    document.getElementById('editButton').classList.remove('active');
    document.getElementById('mapHint').classList.toggle('show', state.drawMode);
    if (state.drawMode && state.points.length) {
      state.points = [];
      renderPolygon();
    }
  });
  document.getElementById('editButton').addEventListener('click', () => {
    state.editMode = !state.editMode;
    state.drawMode = false;
    document.getElementById('editButton').classList.toggle('active', state.editMode);
    document.getElementById('drawButton').classList.remove('active');
    document.getElementById('mapHint').classList.remove('show');
    renderPolygon();
    showToast(state.editMode ? 'Arraste os pontos para ajustar o talhão.' : 'Edição finalizada.');
  });
  document.getElementById('clearButton').addEventListener('click', () => {
    state.points = [];
    renderPolygon();
    showToast('Desenho removido. Clique em “Desenhar polígono” para recomeçar.');
  });
}

function updateClimate() {
  const select = document.getElementById('municipality');
  const climate = climateByCity[select.value] || climateByCity['-17.7923,-50.9190'];
  document.getElementById('annualRain').textContent = climate.rain;
  document.getElementById('dryMonths').textContent = climate.dry;
  document.getElementById('waterRisk').textContent = climate.risk;
  const [lat, lng] = select.value.split(',').map(Number);
  if (state.map) state.map.flyTo([lat, lng], 14, { duration: .8 });
}

function saveProperty(event) {
  event.preventDefault();
  if (state.points.length < 3) {
    showToast('Desenhe pelo menos três pontos para salvar o talhão.');
    return;
  }
  const select = document.getElementById('municipality');
  const record = {
    name: document.getElementById('propertyName').value.trim(),
    municipality: select.options[select.selectedIndex].text,
    producer: document.getElementById('producerName').value.trim(),
    soil: document.getElementById('soil').value,
    irrigation: document.getElementById('irrigation').value,
    rotation: document.getElementById('rotation').value,
    area: polygonArea(state.points).toFixed(1),
    coordinates: state.points,
    savedAt: new Date().toISOString()
  };
  const properties = JSON.parse(localStorage.getItem('terraPonteProperties') || '[]');
  properties.push(record);
  localStorage.setItem('terraPonteProperties', JSON.stringify(properties));
  document.getElementById('propertyCount').textContent = 18 + properties.length;
  document.getElementById('modalText').textContent = `${record.name}, com ${record.area} ha, foi adicionada à carteira da cooperativa.`;
  document.getElementById('modalBackdrop').hidden = false;
}

function initPropertyActions() {
  document.getElementById('propertyForm').addEventListener('submit', saveProperty);
  document.getElementById('municipality').addEventListener('change', updateClimate);
  document.getElementById('coordinatesButton').addEventListener('click', () => {
    const panel = document.getElementById('coordinatesPanel');
    panel.hidden = !panel.hidden;
  });
  document.getElementById('refreshClimate').addEventListener('click', () => {
    const button = document.getElementById('refreshClimate');
    button.classList.add('loading');
    setTimeout(() => { button.classList.remove('loading'); updateClimate(); showToast('Contexto climático atualizado.'); }, 700);
  });
  document.getElementById('savedPropertiesButton').addEventListener('click', () => {
    const count = JSON.parse(localStorage.getItem('terraPonteProperties') || '[]').length;
    showToast(count ? `${count} propriedade(s) salva(s) neste navegador.` : 'Nenhuma propriedade nova salva ainda.');
  });
}

function initModal() {
  const close = () => document.getElementById('modalBackdrop').hidden = true;
  document.getElementById('modalClose').addEventListener('click', close);
  document.getElementById('modalConfirm').addEventListener('click', close);
  document.getElementById('modalBackdrop').addEventListener('click', e => { if (e.target.id === 'modalBackdrop') close(); });
}

function initCalendar() {
  const days = [26,27,28,29,30,31,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,1,2,3,4,5,6];
  const grid = document.getElementById('calendarGrid');
  grid.innerHTML = days.map((day, i) => `<button class="${i < 6 || i > 35 ? 'muted ' : ''}${day === 14 && i > 6 ? 'today ' : ''}${[20,23,26].includes(i) ? 'event' : ''}">${day}</button>`).join('');
}

function initExtras() {
  document.getElementById('newDemand').addEventListener('click', () => showToast('Nova demanda iniciada. Preencha os dados do cooperado.'));
  document.getElementById('exportReport').addEventListener('click', () => showToast('Relatório preparado para exportação.'));
  document.querySelectorAll('.step').forEach((step, index, all) => step.addEventListener('click', () => {
    all.forEach((item, i) => item.classList.toggle('active', i <= index));
    showToast(index === 0 ? 'Delimite o talhão no mapa.' : index === 1 ? 'Etapa de dados locais selecionada.' : 'Comparação de rotações selecionada.');
  }));
}

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();
  initNavigation();
  initMap();
  initPropertyActions();
  initModal();
  initCalendar();
  initExtras();
  const properties = JSON.parse(localStorage.getItem('terraPonteProperties') || '[]');
  document.getElementById('propertyCount').textContent = 18 + properties.length;
});
