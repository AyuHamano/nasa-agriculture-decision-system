/* Gerado com IA (Claude). */
/* Os ícones da tela, desenhados aqui mesmo (traço simples, 24x24), para a tela abrir sem internet. */
(function () {
  "use strict";
  var D = {
    gota: '<path d="M12 3c3.5 4.2 6 7.4 6 10.6A6 6 0 0 1 6 13.6C6 10.4 8.5 7.2 12 3z"/>',
    sol: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"/>',
    broto: '<path d="M12 21v-9"/><path d="M12 12c0-4 2.5-6.5 7-7 .3 4.6-2.2 7.3-7 7z"/><path d="M12 15c0-3-2-5-5.5-5.4C6.2 13.200 8.200 15.200 12 15z"/>',
    satelite: '<rect x="9.2" y="9.2" width="5.6" height="5.6" rx="1" transform="rotate(45 12 12)"/><path d="M8 8 4.200 4.200M16 16l3.800 3.800M6.500 9.500 3 6M9.500 6.500 6 3M17.500 14.500 21 18M14.500 17.500 18 21"/><path d="M4 16a4 4 0 0 0 4 4"/>',
    tocar: '<path d="M7 4.500v15l12-7.500z" fill="currentColor"/>',
    pausar: '<path d="M8 5v14M16 5v14" stroke-width="3"/>',
    voltar: '<path d="M4 12a8 8 0 1 0 2.600-5.900"/><path d="M4 4.500v4.500h4.500"/>',
    cheia: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
    certo: '<path d="M4.500 12.500l5 5L19.500 7"/>',
    lapis: '<path d="M4 20l1-4L16.500 4.500l3 3L8 19z"/><path d="M14.500 6.500l3 3"/>',
    baixar: '<path d="M12 4v11M7.500 11l4.500 4.500L16.500 11M5 20h14"/>',
    seta: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    pessoa: '<circle cx="12" cy="8" r="3.500"/><path d="M5 20c.600-3.800 3.300-6 7-6s6.400 2.200 7 6"/>',
    alerta: '<path d="M12 4 2.500 20h19z"/><path d="M12 10v5M12 17.500v.100"/>',
    balao: '<path d="M4 5h16v11H10l-4.500 4v-4H4z"/>',
    download: '<path d="M12 4v11M7.500 11l4.500 4.500L16.500 11M5 20h14"/>'
  };
  window.ORBITA_ICONE = function (nome) {
    var d = D[nome]; if (!d) return "";
    return '<svg class="ic" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' + d + "</svg>";
  };
})();
