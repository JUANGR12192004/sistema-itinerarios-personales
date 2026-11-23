/**
 * Punto de entrada del frontend.
 * Gestiona las pestañas Aeropuertos / Itinerarios, el botón de tema y carga cada
 * sección bajo demanda (aeropuertos con mapa; CRUD de itinerarios).
 *
 * Las pestañas siguen el patrón de WAI-ARIA: solo la pestaña activa está en el orden de
 * tabulación (tabindex="0"); con las flechas, Inicio y Fin se pasa a otra pestaña y se
 * activa en ese momento.
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

const TAB_ORDER = Object.keys(TABS);

function switchTab(active) {
  for (const [name, tab] of Object.entries(TABS)) {
    const isActive = name === active;
    tab.btn.classList.toggle('active', isActive);
    tab.btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
    tab.btn.tabIndex = isActive ? 0 : -1;
    tab.section.classList.toggle('hidden', !isActive);
  }
}

/** Activa la pestaña y recarga su sección: así siempre muestra datos frescos. */
function openTab(name) {
  switchTab(name);
  if (name === 'airports') loadAirports(TABS.airports.section);
  if (name === 'itineraries') loadItineraries(TABS.itineraries.section);
}

/** Flechas izquierda/derecha (circulares), Inicio y Fin entre las pestañas. */
function onTabKeydown(event, current) {
  const index = TAB_ORDER.indexOf(current);
  const last = TAB_ORDER.length - 1;
  const targets = {
    ArrowRight: index === last ? 0 : index + 1,
    ArrowLeft: index === 0 ? last : index - 1,
    Home: 0,
    End: last,
  };
  if (!(event.key in targets)) return;
  event.preventDefault();
  const next = TAB_ORDER[targets[event.key]];
  TABS[next].btn.focus();
  if (next !== current) openTab(next);
}

document.addEventListener('DOMContentLoaded', () => {
  const themeButton = document.getElementById('theme-toggle');
  if (themeButton) initThemeToggle(themeButton);

  for (const [name, tab] of Object.entries(TABS)) {
    tab.btn = document.getElementById(tab.btnId);
    tab.section = document.getElementById(tab.sectionId);
    if (!tab.btn || !tab.section) continue;

    tab.btn.addEventListener('click', () => openTab(name));
    tab.btn.addEventListener('keydown', (event) => onTabKeydown(event, name));
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
