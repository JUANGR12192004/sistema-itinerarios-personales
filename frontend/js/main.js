/**
 * Punto de entrada del frontend.
 * Gestiona las pestañas Aeropuertos / Itinerarios y carga cada sección
 * bajo demanda (8B: aeropuertos con mapa; 8C: CRUD de itinerarios).
 */

const TABS = {
  airports: {
    btnId: 'tab-airports',
    sectionId: 'section-airports',
    btn: null,
    section: null,
  },
  itineraries: {
    btnId: 'tab-itineraries',
    sectionId: 'section-itineraries',
    btn: null,
    section: null,
  },
};

function switchTab(active) {
  for (const [name, tab] of Object.entries(TABS)) {
    const isActive = name === active;
    tab.btn.classList.toggle('active', isActive);
    tab.btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
    tab.section.classList.toggle('hidden', !isActive);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  for (const [name, tab] of Object.entries(TABS)) {
    tab.btn = document.getElementById(tab.btnId);
    tab.section = document.getElementById(tab.sectionId);
    if (!tab.btn || !tab.section) continue;
    tab.btn.addEventListener('click', () => switchTab(name));
  }
});
