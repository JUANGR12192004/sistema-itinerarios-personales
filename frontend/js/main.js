/**
 * Punto de entrada del frontend.
 * Gestiona las pestañas Aeropuertos / Itinerarios, el botón de tema y carga cada
 * sección bajo demanda (aeropuertos con mapa; CRUD de itinerarios).
 */

import { loadAirports, setRoute } from './airports.js';
import { loadItineraries } from './itineraries.js';
import { initThemeToggle } from './theme.js';

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
  const themeButton = document.getElementById('theme-toggle');
  if (themeButton) initThemeToggle(themeButton);

  for (const [name, tab] of Object.entries(TABS)) {
    tab.btn = document.getElementById(tab.btnId);
    tab.section = document.getElementById(tab.sectionId);
    if (!tab.btn || !tab.section) continue;

    tab.btn.addEventListener('click', () => {
      switchTab(name);
      // Recargar la sección al activarla: así siempre muestra datos frescos
      if (name === 'airports') loadAirports(tab.section);
      if (name === 'itineraries') loadItineraries(tab.section);
    });
  }

  // «Ver en el mapa» desde la tabla de itinerarios: cambia a la pestaña Aeropuertos
  // con el origen y el destino resaltados
  document.addEventListener('showroute', (event) => {
    setRoute(event.detail);
    switchTab('airports');
    window.scrollTo({ top: 0, behavior: 'smooth' });
    TABS.airports.btn.focus({ preventScroll: true });
    loadAirports(TABS.airports.section);
  });

  // La pestaña de aeropuertos está activa por defecto: cargar el mapa al arrancar
  loadAirports(TABS.airports.section);
});
