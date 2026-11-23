/**
 * Sección Aeropuertos: consulta /api/airports/map-data y dibuja el mapa
 * con Plotly scattergeo, agrupando los aeropuertos por tipo.
 *
 * Plotly se carga como script clásico (plotly-geo.min.js) y queda en window.Plotly.
 * Este módulo lo usa como global; no hace falta importarlo.
 *
 * Plotly no entiende variables CSS: los colores se leen del tema activo con cssVar()
 * y el mapa se vuelve a dibujar cuando cambia el tema (evento 'themechange').
 */

import { apiFetch, renderError } from './api.js';
import { cssVar } from './theme.js';

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

// Últimos datos dibujados: permiten repintar el mapa al cambiar de tema o de tamaño
// sin volver a pedirlos al gateway
let lastRender = null;

function _redraw() {
  if (lastRender && lastRender.mapDiv.isConnected) {
    _drawMap(lastRender.mapDiv, lastRender.data);
  }
}

document.addEventListener('themechange', _redraw);

let resizeTimer = null;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(_redraw, 150);
});

export async function loadAirports(container) {
  _showLoading(container);
  let data;
  try {
    data = await apiFetch('/api/airports/map-data');
  } catch (error) {
    renderError(container, error);
    return;
  }
  _renderMap(container, data);
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

function _renderMap(container, data) {
  container.replaceChildren();

  // Cabecera con el conteo real (el id 43 no tiene coordenadas: no se asume 52)
  const head = document.createElement('div');
  head.className = 'section-head airports-header';
  const title = document.createElement('h2');
  title.textContent = 'Aeropuertos de Colombia';
  const countEl = document.createElement('p');
  countEl.className = 'section-meta airports-count';
  countEl.textContent = `${data.count} aeropuertos con ubicación en el mapa`;
  head.append(title, countEl);
  container.appendChild(head);

  const card = document.createElement('div');
  card.className = 'card map-card';

  // Plotly necesita un contenedor con altura definida (la da .airports-map en el CSS)
  const mapDiv = document.createElement('div');
  mapDiv.className = 'airports-map';
  card.appendChild(mapDiv);

  const note = document.createElement('p');
  note.className = 'map-note';
  note.textContent =
    'Datos de API Colombia. Pasa el cursor o toca un punto para ver el aeropuerto.';
  card.appendChild(note);
  container.appendChild(card);

  lastRender = { mapDiv, data };
  _drawMap(mapDiv, data);
}

function _drawMap(mapDiv, data) {
  // Un trazo por tipo → leyenda automática
  const byType = {};
  for (let i = 0; i < data.count; i++) {
    const type = data.types[i];
    if (!byType[type]) byType[type] = { lats: [], lons: [], customdata: [] };
    const iata = data.iata_codes[i] ? ` (${data.iata_codes[i]})` : '';
    byType[type].lats.push(data.latitudes[i]);
    byType[type].lons.push(data.longitudes[i]);
    // customdata se pasa como arreglo de arreglos: cada fila es un punto
    byType[type].customdata.push([
      data.names[i] + iata,
      data.cities[i],
      data.departments[i],
      TYPE_LABELS[type] ?? type,
    ]);
  }

  const surface = cssVar('--surface');
  const ink = cssVar('--ink');
  const line = cssVar('--line-strong');
  const font = { family: cssVar('--font'), color: ink, size: 14 };

  const traces = Object.entries(byType).map(([type, pts]) => ({
    type: 'scattergeo',
    lat: pts.lats,
    lon: pts.lons,
    customdata: pts.customdata,
    name: TYPE_LABELS[type] ?? type,
    // %{customdata[N]} accede al arreglo por índice; <extra></extra> oculta el nombre del trazo
    hovertemplate:
      '<b>%{customdata[0]}</b><br>%{customdata[1]}, %{customdata[2]}<br>%{customdata[3]}<extra></extra>',
    marker: {
      size: 10,
      color: cssVar(TYPE_COLOR_VARS[type] ?? '--pending'),
      opacity: 0.95,
      line: { width: 1.5, color: surface },
    },
  }));

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

  // Plotly.react reutiliza el gráfico si ya existe (cambio de tema o de tamaño) o lo crea si no.
  // responsive: true hace que el mapa se redimensione con la ventana.
  Plotly.react(mapDiv, traces, layout, { responsive: true, displayModeBar: false });
}
