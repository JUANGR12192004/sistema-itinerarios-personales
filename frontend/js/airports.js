/**
 * Sección Aeropuertos: consulta /api/airports/map-data y dibuja el mapa
 * con Plotly scattergeo, agrupando los aeropuertos por tipo.
 *
 * Plotly se carga como script clásico (plotly-geo.min.js) y queda en window.Plotly.
 * Este módulo lo usa como global; no hace falta importarlo.
 */

import { apiFetch, renderError } from './api.js';

const TYPE_COLORS = {
  'Internacional':   '#0f3460',
  'Nacional':        '#e94560',
  'Militar':         '#f7b731',
  'En Construccion': '#888',
};

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
  const header = document.createElement('div');
  header.className = 'airports-header';
  const countEl = document.createElement('p');
  countEl.className = 'airports-count';
  countEl.textContent = `${data.count} aeropuertos con ubicación en el mapa`;
  header.appendChild(countEl);
  container.appendChild(header);

  // Plotly necesita un contenedor con altura definida
  const mapDiv = document.createElement('div');
  mapDiv.className = 'airports-map';
  container.appendChild(mapDiv);

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
      type,
    ]);
  }

  const traces = Object.entries(byType).map(([type, pts]) => ({
    type: 'scattergeo',
    lat: pts.lats,
    lon: pts.lons,
    customdata: pts.customdata,
    name: type,
    // %{customdata[N]} accede al arreglo por índice; <extra></extra> oculta el nombre del trazo
    hovertemplate:
      '<b>%{customdata[0]}</b><br>%{customdata[1]}, %{customdata[2]}<br>%{customdata[3]}<extra></extra>',
    marker: {
      size: 9,
      color: TYPE_COLORS[type] ?? '#555',
      opacity: 0.85,
      line: { width: 0.5, color: '#fff' },
    },
  }));

  const layout = {
    margin: { t: 10, b: 10, l: 0, r: 0 },
    paper_bgcolor: 'transparent',
    geo: {
      scope: 'south america',
      showland: true,
      landcolor: '#f0f4f8',
      showocean: true,
      oceancolor: '#d6eaf8',
      showcountries: true,
      countrycolor: '#aaa',
      showcoastlines: true,
      coastlinecolor: '#888',
      showlakes: true,
      lakecolor: '#d6eaf8',
      // Recortar la vista a Colombia (lat -5..13, lon -82..-65)
      lonaxis: { range: [-82, -65] },
      lataxis: { range: [  -5,  13] },
    },
    legend: {
      x: 0.01,
      y: 0.99,
      bgcolor: 'rgba(255,255,255,0.8)',
      bordercolor: '#ccc',
      borderwidth: 1,
    },
  };

  // responsive: true hace que el mapa se redimensione con la ventana
  Plotly.newPlot(mapDiv, traces, layout, { responsive: true, displayModeBar: false });
}
