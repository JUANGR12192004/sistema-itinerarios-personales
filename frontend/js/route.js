/**
 * Bloque de ruta: dos códigos de aeropuerto unidos por la línea de vuelo, como en una
 * tarjeta de embarque. Lo usan la tabla de itinerarios, la vista previa del formulario y
 * el aviso de ruta sobre el mapa.
 * Todo texto se escribe con textContent (nunca innerHTML).
 */

const SVG_NS = 'http://www.w3.org/2000/svg';

/** Código corto del aeropuerto: IATA si existe, si no OACI (algunos no tienen IATA). */
export function airportCode(airport) {
  if (!airport) return '—';
  return airport.iata_code ?? airport.oaci_code ?? '—';
}

function _planeIcon() {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');
  const path = document.createElementNS(SVG_NS, 'path');
  path.setAttribute('fill', 'currentColor');
  path.setAttribute(
    'd',
    'M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z',
  );
  // El avión del ícono apunta hacia arriba: se gira para que vaya de salida a llegada
  path.setAttribute('transform', 'rotate(90 12 12)');
  svg.appendChild(path);
  return svg;
}

function _routeEnd(airport) {
  const end = document.createElement('div');
  end.className = 'route-end';
  const code = document.createElement('span');
  code.className = 'route-code';
  code.textContent = airportCode(airport);
  const city = document.createElement('span');
  city.className = 'route-city';
  city.textContent = airport ? airport.city : 'Sin elegir';
  end.append(code, city);
  return end;
}

/** Descripción completa de la ruta para lectores de pantalla y botones. */
export function routeDescription(departure, arrival, durationMinutes = null) {
  const duration = durationMinutes > 0 ? `, ${durationMinutes} minutos` : '';
  return `De ${departure.name} (${departure.city}) a ${arrival.name} (${arrival.city})${duration}`;
}

/**
 * Construye el bloque de ruta; con aeropuertos nulos queda en estado vacío.
 * La duración (si se conoce) va bajo la línea de vuelo.
 * Con decorative = true no anuncia nada (cuando el texto ya lo da un botón que lo contiene).
 */
export function buildRoute(departure, arrival, durationMinutes = null, { decorative = false } = {}) {
  const route = document.createElement('div');
  route.className = 'route';
  route.classList.toggle('is-empty', !departure || !arrival);

  const lineEl = document.createElement('div');
  lineEl.className = 'route-line';
  lineEl.appendChild(_planeIcon());
  if (durationMinutes > 0) {
    const duration = document.createElement('span');
    duration.className = 'route-duration';
    duration.textContent = `${durationMinutes} min`;
    lineEl.appendChild(duration);
  }

  route.append(_routeEnd(departure), lineEl, _routeEnd(arrival));

  if (decorative) {
    route.setAttribute('aria-hidden', 'true');
  } else if (departure && arrival) {
    // Los códigos solos no se entienden: el lector de pantalla lee la ruta completa
    route.setAttribute('role', 'img');
    route.setAttribute('aria-label', routeDescription(departure, arrival, durationMinutes));
  }
  return route;
}
