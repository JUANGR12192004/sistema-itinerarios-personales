/**
 * Sección Aeropuertos: consulta /api/airports/map-data y dibuja el mapa con Plotly
 * scattergeo (un trazo por tipo), junto a una lista con buscador.
 *
 * - Buscador: filtra la lista por nombre, ciudad, departamento, código o tipo; en el mapa
 *   los aeropuertos que no coinciden se atenúan.
 * - Selección: elegir un aeropuerto en la lista (o tocarlo en el mapa) lo resalta en los dos.
 * - Ruta: la sección Itinerarios puede pedir que se dibuje la ruta de un itinerario
 *   (setRoute); el origen y el destino se resaltan en magenta y el resto se atenúa.
 *
 * Plotly se carga como script clásico (plotly-geo.min.js) y queda en window.Plotly.
 * Plotly no entiende variables CSS: los colores se leen del tema activo con cssVar()
 * y el mapa se vuelve a dibujar cuando cambia el tema (evento 'themechange').
 * Todo texto de datos se escribe con textContent (nunca innerHTML).
 */

import { apiFetch, renderError } from './api.js';
import { buildRoute } from './route.js';
import { cssVar } from './theme.js';
import { showToast } from './ui.js';

// Color de cada tipo de aeropuerto: variable CSS de la paleta de la carta
const TYPE_COLOR_VARS = {
  'Internacional':   '--chart-blue',
  'Nacional':        '--chart-magenta',
  'Militar':         '--olive',
  'En Construccion': '--pending',
};

// Etiqueta legible del tipo (API Colombia envía «En Construccion» sin tilde)
const TYPE_LABELS = {
  'En Construccion': 'En construcción',
};

function _typeLabel(type) {
  return TYPE_LABELS[type] ?? type;
}

// Vista de Colombia: latitud fija (hasta 14° para no cortar San Andrés, a 12,6°)
// y longitud centrada en el país
const LAT_RANGE = [-5, 14];
const LON_CENTER = -73.5;
const MIN_LON_SPAN = 17; // nunca más angosto que el país (lon -82..-65)

/**
 * El mapa base conserva la proporción: con solo -82..-65 en un contenedor ancho quedaba un
 * recuadro casi cuadrado con franjas vacías a los lados. Se ensancha el rango de longitudes
 * según la proporción del contenedor (en Mercator, cerca del ecuador, 1° de latitud ≈ 1° de
 * longitud), así el mapa llena el ancho y muestra los países vecinos.
 */
function _lonRange(mapDiv) {
  const { clientWidth: width, clientHeight: height } = mapDiv;
  const latSpan = LAT_RANGE[1] - LAT_RANGE[0];
  const span = height > 0 ? Math.max(MIN_LON_SPAN, latSpan * (width / height)) : MIN_LON_SPAN;
  return [LON_CENTER - span / 2, LON_CENTER + span / 2];
}

// ── Estado de la sección ─────────────────────────────────────────────────────
// Se conserva entre recargas de la pestaña: la búsqueda, el aeropuerto elegido y la ruta.
const state = {
  airports: [],      // [{ id, name, iata, city, department, type, lat, lon, search }]
  query: '',
  selectedId: null,
  route: null,       // { travelerName, durationMinutes, departure, arrival } (aeropuertos de /api/airports)
  els: null,         // elementos de la vista actual
};

/** La sección Itinerarios pide dibujar una ruta (o null para quitarla). */
export function setRoute(route) {
  state.route = route;
  if (!route) return;
  state.selectedId = null;

  // El aeropuerto 43 (en construcción) no tiene coordenadas: se avisa una sola vez
  const missing = [route.departure, route.arrival].filter((a) => !a.coordinates);
  if (missing.length) {
    showToast(
      `${missing.map((a) => a.name).join(' y ')} no tiene ubicación conocida: el mapa no puede dibujar la ruta completa.`,
      'error',
    );
  }
}

function _redraw() {
  if (state.els && state.els.mapDiv.isConnected) _drawMap();
}

document.addEventListener('themechange', _redraw);

let resizeTimer = null;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(_redraw, 150);
});

// Búsqueda sin distinguir mayúsculas ni tildes: «bogota» encuentra «Bogotá»
function _normalize(text) {
  return String(text ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

function _matches(airport) {
  const query = _normalize(state.query.trim());
  return !query || airport.search.includes(query);
}

// ── Carga ────────────────────────────────────────────────────────────────────

export async function loadAirports(container) {
  _showLoading(container);
  let data;
  try {
    data = await apiFetch('/api/airports/map-data');
  } catch (error) {
    state.els = null;
    renderError(container, error);
    return;
  }

  state.airports = [];
  for (let i = 0; i < data.count; i++) {
    const airport = {
      id: data.ids[i],
      name: data.names[i],
      iata: data.iata_codes[i],
      city: data.cities[i],
      department: data.departments[i],
      type: data.types[i],
      lat: data.latitudes[i],
      lon: data.longitudes[i],
    };
    airport.search = _normalize(
      [airport.name, airport.iata, airport.city, airport.department, _typeLabel(airport.type)].join(' '),
    );
    state.airports.push(airport);
  }
  state.airports.sort((a, b) => a.city.localeCompare(b.city, 'es') || a.name.localeCompare(b.name, 'es'));
  if (!state.airports.some((a) => a.id === state.selectedId)) state.selectedId = null;

  _render(container, data.count);
}

function _showLoading(container) {
  container.replaceChildren();
  const loading = document.createElement('div');
  loading.className = 'loading';
  const spinner = document.createElement('div');
  spinner.className = 'spinner';
  const text = document.createElement('span');
  text.textContent = 'Cargando aeropuertos...';
  loading.append(spinner, text);
  container.appendChild(loading);
}

// ── Vista ────────────────────────────────────────────────────────────────────

function _render(container, count) {
  container.replaceChildren();

  // Cabecera con el conteo real (el id 43 no tiene coordenadas: no se asume 52)
  const head = document.createElement('div');
  head.className = 'section-head airports-header';
  const title = document.createElement('h2');
  title.textContent = 'Aeropuertos de Colombia';
  const countEl = document.createElement('p');
  countEl.className = 'section-meta airports-count';
  countEl.textContent = `${count} aeropuertos con ubicación en el mapa`;
  head.append(title, countEl);
  container.appendChild(head);

  const layout = document.createElement('div');
  layout.className = 'airports-layout';

  // Mapa
  const card = document.createElement('div');
  card.className = 'card map-card';

  const routeBar = document.createElement('div');
  routeBar.className = 'route-bar';
  card.appendChild(routeBar);

  // Plotly necesita un contenedor con altura definida (la da .airports-map en el CSS)
  const mapDiv = document.createElement('div');
  mapDiv.className = 'airports-map';
  mapDiv.setAttribute('role', 'img');
  mapDiv.setAttribute(
    'aria-label',
    `Mapa de Colombia con ${count} aeropuertos, coloreados por tipo. La lista con buscador tiene los mismos datos.`,
  );
  card.appendChild(mapDiv);

  const note = document.createElement('p');
  note.className = 'map-note';
  note.textContent =
    'Datos de API Colombia. Pasa el cursor sobre un punto, tócalo o elige el aeropuerto en la lista.';
  card.appendChild(note);

  // Lista con buscador
  const panel = document.createElement('div');
  panel.className = 'card airport-panel';

  const searchBox = document.createElement('div');
  searchBox.className = 'airport-search';
  const label = document.createElement('label');
  label.htmlFor = 'airport-search';
  label.textContent = 'Buscar aeropuerto';
  const input = document.createElement('input');
  input.type = 'search';
  input.id = 'airport-search';
  input.placeholder = 'Ciudad, nombre o código IATA';
  input.autocomplete = 'off';
  input.value = state.query;
  input.setAttribute('aria-controls', 'airport-list');
  input.setAttribute('aria-describedby', 'airport-results');
  const results = document.createElement('p');
  results.className = 'airport-results';
  results.id = 'airport-results';
  results.setAttribute('aria-live', 'polite');
  searchBox.append(label, input, results);

  const list = document.createElement('ul');
  list.className = 'airport-list';
  list.id = 'airport-list';
  list.setAttribute('aria-label', 'Aeropuertos');

  panel.append(searchBox, list);
  layout.append(card, panel);
  container.appendChild(layout);

  state.els = { mapDiv, list, results, routeBar, input };

  let mapTimer = null;
  input.addEventListener('input', () => {
    state.query = input.value;
    _renderList();
    // El mapa se redibuja un poco después de dejar de escribir
    clearTimeout(mapTimer);
    mapTimer = setTimeout(_drawMap, 150);
  });

  _renderRouteBar();
  _renderList();
  _drawMap();

  // Tocar un punto del mapa lo elige también en la lista
  mapDiv.on('plotly_click', (event) => {
    const point = event.points?.[0];
    const id = point?.customdata?.[4];
    if (typeof id === 'number') _select(id, { fromMap: true });
  });
}

function _select(id, { fromMap = false } = {}) {
  state.selectedId = state.selectedId === id && !fromMap ? null : id;
  _renderList();
  _drawMap();
  const { list, mapDiv } = state.els;
  if (fromMap) {
    list.querySelector(`[data-id="${id}"]`)?.scrollIntoView({ block: 'nearest' });
  } else if (state.selectedId !== null) {
    // En pantallas angostas la lista queda debajo del mapa: se lleva el mapa a la vista
    const rect = mapDiv.getBoundingClientRect();
    if (rect.bottom < 0 || rect.top > window.innerHeight) {
      mapDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
}

function _renderList() {
  const { list, results } = state.els;
  const matching = state.airports.filter(_matches);
  list.replaceChildren();

  const total = state.airports.length;
  results.textContent = state.query.trim()
    ? `${matching.length} de ${total} aeropuertos`
    : `${total} aeropuertos`;

  if (matching.length === 0) {
    const empty = document.createElement('li');
    empty.className = 'airport-empty';
    empty.textContent =
      `Ningún aeropuerto coincide con «${state.query.trim()}». Prueba con la ciudad, el departamento o el código IATA.`;
    list.appendChild(empty);
    return;
  }

  for (const airport of matching) {
    const li = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'airport-item';
    button.dataset.id = String(airport.id);
    button.setAttribute('aria-pressed', airport.id === state.selectedId ? 'true' : 'false');

    const dot = document.createElement('span');
    dot.className = `type-dot type-${_normalize(airport.type).replace(/\s+/g, '-')}`;
    dot.setAttribute('aria-hidden', 'true');

    const code = document.createElement('span');
    code.className = 'airport-code';
    code.textContent = airport.iata ?? '—';

    const text = document.createElement('span');
    text.className = 'airport-text';
    const name = document.createElement('span');
    name.className = 'airport-name';
    name.textContent = airport.name;
    const place = document.createElement('span');
    place.className = 'airport-place';
    place.textContent = `${airport.city}, ${airport.department}. ${_typeLabel(airport.type)}`;
    text.append(name, place);

    button.append(dot, code, text);
    button.addEventListener('click', () => _select(airport.id));
    li.appendChild(button);
    list.appendChild(li);
  }
}

function _renderRouteBar() {
  const { routeBar } = state.els;
  routeBar.replaceChildren();
  routeBar.hidden = !state.route;
  if (!state.route) return;

  const { travelerName, durationMinutes, departure, arrival } = state.route;

  const info = document.createElement('div');
  info.className = 'route-bar-info';
  const label = document.createElement('p');
  label.className = 'route-bar-label';
  label.textContent = `Ruta de ${travelerName}`;
  info.append(label, buildRoute(departure, arrival, durationMinutes));

  const clear = document.createElement('button');
  clear.type = 'button';
  clear.className = 'btn btn-secondary btn-sm';
  clear.textContent = 'Quitar ruta';
  clear.addEventListener('click', () => {
    setRoute(null);
    _renderRouteBar();
    _drawMap();
    state.els.input.focus();
  });

  routeBar.append(info, clear);
}

// ── Mapa ─────────────────────────────────────────────────────────────────────

function _drawMap() {
  const { mapDiv } = state.els;
  const surface = cssVar('--surface');
  const ink = cssVar('--ink');
  const line = cssVar('--line-strong');
  const magenta = cssVar('--chart-magenta');
  const font = { family: cssVar('--font'), color: ink, size: 14 };
  const filtering = Boolean(state.query.trim());
  const dimAll = Boolean(state.route);

  // Un trazo por tipo con los aeropuertos que coinciden con la búsqueda → leyenda automática,
  // siempre en el mismo orden. Los que no coinciden van aparte, en gris y sin leyenda
  // (si se atenuaran dentro del mismo trazo, Plotly atenuaría también la leyenda).
  const byType = new Map(Object.keys(TYPE_COLOR_VARS).map((type) => [type, []]));
  const others = [];
  for (const airport of state.airports) {
    if (filtering && !_matches(airport)) {
      others.push(airport);
      continue;
    }
    if (!byType.has(airport.type)) byType.set(airport.type, []);
    byType.get(airport.type).push(airport);
  }

  const pointData = (airports) => ({
    lat: airports.map((a) => a.lat),
    lon: airports.map((a) => a.lon),
    customdata: airports.map((a) => [
      a.name,
      a.iata ? `Código IATA: ${a.iata}` : 'Sin código IATA',
      `${a.city}, ${a.department}`,
      `Tipo: ${_typeLabel(a.type)}`,
      a.id,
    ]),
    // %{customdata[N]} accede al arreglo por índice; <extra></extra> oculta el nombre del trazo
    hovertemplate:
      '<b>%{customdata[0]}</b><br>%{customdata[2]}<br>%{customdata[1]}<br>%{customdata[3]}<extra></extra>',
  });

  const traces = [];
  if (others.length) {
    traces.push({
      type: 'scattergeo',
      ...pointData(others),
      name: 'No coinciden con la búsqueda',
      showlegend: false,
      marker: { size: 7, color: cssVar('--line-strong'), opacity: 0.8 },
    });
  }
  for (const [type, airports] of byType) {
    if (!airports.length) continue;
    traces.push({
      type: 'scattergeo',
      ...pointData(airports),
      name: _typeLabel(type),
      marker: {
        size: 10,
        color: cssVar(TYPE_COLOR_VARS[type] ?? '--pending'),
        // Mientras se ve una ruta, el resto de aeropuertos queda de fondo
        opacity: dimAll ? 0.35 : 0.95,
        line: { width: 1.5, color: surface },
      },
    });
  }

  // Aeropuerto elegido en la lista: anillo con el color de la tinta
  const selected = state.airports.find((a) => a.id === state.selectedId);
  if (selected) {
    traces.push({
      type: 'scattergeo',
      lat: [selected.lat],
      lon: [selected.lon],
      mode: 'markers+text',
      text: [selected.iata ?? selected.city],
      textposition: 'top center',
      textfont: { family: font.family, size: 15, color: ink },
      marker: { size: 24, symbol: 'circle-open', color: ink, line: { width: 3, color: ink } },
      hoverinfo: 'skip',
      showlegend: false,
    });
  }

  // Ruta de un itinerario: línea discontinua y extremos en magenta con su código
  if (state.route) {
    const ends = [state.route.departure, state.route.arrival].filter((a) => a.coordinates);
    if (ends.length === 2) {
      traces.push({
        type: 'scattergeo',
        mode: 'lines',
        lat: ends.map((a) => a.coordinates.latitude),
        lon: ends.map((a) => a.coordinates.longitude),
        line: { color: magenta, width: 3, dash: 'dash' },
        hoverinfo: 'skip',
        showlegend: false,
      });
    }
    traces.push({
      type: 'scattergeo',
      mode: 'markers+text',
      lat: ends.map((a) => a.coordinates.latitude),
      lon: ends.map((a) => a.coordinates.longitude),
      text: ends.map((a) => a.iata_code ?? a.oaci_code ?? a.city),
      customdata: ends.map((a) => [a.name, `${a.city}, ${a.department}`, a === state.route.departure ? 'Salida' : 'Llegada']),
      hovertemplate: '<b>%{customdata[2]}: %{customdata[0]}</b><br>%{customdata[1]}<extra></extra>',
      textposition: 'top center',
      textfont: { family: font.family, size: 16, color: ink },
      marker: { size: 16, color: magenta, line: { width: 2.5, color: surface } },
      showlegend: false,
    });
  }

  const layout = {
    margin: { t: 0, b: 0, l: 0, r: 0 },
    paper_bgcolor: cssVar('--map-water'),
    font,
    hoverlabel: { bgcolor: surface, bordercolor: line, font },
    geo: {
      scope: 'south america',
      bgcolor: cssVar('--map-water'),
      showland: true,
      landcolor: cssVar('--map-land'),
      showocean: true,
      oceancolor: cssVar('--map-water'),
      showcountries: true,
      countrycolor: cssVar('--map-border'),
      showcoastlines: true,
      coastlinecolor: cssVar('--map-coast'),
      showlakes: true,
      lakecolor: cssVar('--map-water'),
      showframe: false,
      // Vista de Colombia: latitudes -5..14 fijas; el ancho en longitud se adapta al contenedor
      lonaxis: { range: _lonRange(mapDiv) },
      lataxis: { range: LAT_RANGE },
    },
    // Leyenda horizontal abajo: no tapa el mapa en pantallas angostas
    legend: {
      orientation: 'h',
      x: 0.5,
      xanchor: 'center',
      y: 0.02,
      yanchor: 'bottom',
      bgcolor: surface,
      bordercolor: line,
      borderwidth: 1,
      font,
    },
  };

  // Plotly.react reutiliza el gráfico si ya existe (cambio de tema, búsqueda o tamaño)
  // o lo crea si no. responsive: true hace que el mapa se redimensione con la ventana.
  Plotly.react(mapDiv, traces, layout, { responsive: true, displayModeBar: false });
}
