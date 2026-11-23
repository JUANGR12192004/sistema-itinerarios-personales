/**
 * Sección Itinerarios: CRUD completo contra /api/itineraries.
 * Carga la lista de aeropuertos una sola vez para los desplegables y la tabla.
 * Todo texto de datos se escribe con textContent (nunca innerHTML).
 */

import { apiFetch, renderError } from './api.js';

const SVG_NS = 'http://www.w3.org/2000/svg';

export async function loadItineraries(container) {
  _showLoading(container);

  let airports, itineraries;
  try {
    [airports, itineraries] = await Promise.all([
      apiFetch('/api/airports'),
      apiFetch('/api/itineraries'),
    ]);
  } catch (error) {
    renderError(container, error);
    return;
  }

  airports.sort((a, b) => a.city.localeCompare(b.city, 'es'));
  const airportMap = new Map(airports.map((a) => [a.id, a]));
  _render(container, airports, airportMap, itineraries);
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function _showLoading(container) {
  container.replaceChildren();
  const loading = document.createElement('div');
  loading.className = 'loading';
  const spinner = document.createElement('div');
  spinner.className = 'spinner';
  const text = document.createElement('span');
  text.textContent = 'Cargando itinerarios...';
  loading.append(spinner, text);
  container.appendChild(loading);
}

// Código corto del aeropuerto: IATA si existe, si no OACI (algunos no tienen IATA)
function _airportCode(airport) {
  if (!airport) return '—';
  return airport.iata_code ?? airport.oaci_code ?? '—';
}

function _airportOptionText(airport) {
  const iata = airport.iata_code ? ` (${airport.iata_code})` : '';
  return `${airport.name}${iata} — ${airport.city}`;
}

const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

function _time(date) {
  const hh = String(date.getHours()).padStart(2, '0');
  const mm = String(date.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

// "18 dic 2026, 08:00" (hora local del navegador)
function _formatDate(date) {
  return `${date.getDate()} ${MONTHS[date.getMonth()]} ${date.getFullYear()}, ${_time(date)}`;
}

// Llegada abreviada: solo la hora si es el mismo día de la salida; si no, el día y la hora
function _formatArrival(departure, arrival) {
  if (arrival.toDateString() === departure.toDateString()) return _time(arrival);
  const year = arrival.getFullYear() !== departure.getFullYear() ? ` ${arrival.getFullYear()}` : '';
  return `${arrival.getDate()} ${MONTHS[arrival.getMonth()]}${year}, ${_time(arrival)}`;
}

// Llegada estimada = salida + duración (el itinerario no guarda la hora de llegada)
function _arrivalDate(departure, durationMinutes) {
  return new Date(departure.getTime() + durationMinutes * 60_000);
}

// "2026-12-15T08:00" (datetime-local) → "2026-12-15T08:00:00-05:00" (ADR-017)
function _localToISO(localDt) {
  const offset = -new Date().getTimezoneOffset();
  const sign = offset >= 0 ? '+' : '-';
  const abs = Math.abs(offset);
  const hh = String(Math.floor(abs / 60)).padStart(2, '0');
  const mm = String(abs % 60).padStart(2, '0');
  return `${localDt}:00${sign}${hh}:${mm}`;
}

// "2026-12-15T08:00:00-05:00" → "2026-12-15T08:00" (para rellenar datetime-local)
function _isoToLocal(isoString) {
  return isoString.substring(0, 16);
}

// ── Ruta: dos códigos unidos por la línea de vuelo ───────────────────────────

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
  code.textContent = _airportCode(airport);
  const city = document.createElement('span');
  city.className = 'route-city';
  city.textContent = airport ? airport.city : 'Sin elegir';
  end.append(code, city);
  return end;
}

/**
 * Construye el bloque de ruta; con aeropuertos nulos queda en estado vacío.
 * La duración (si se conoce) va bajo la línea de vuelo, como en una tarjeta de embarque.
 */
function _buildRoute(departure, arrival, durationMinutes = null) {
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

  // Texto completo para lectores de pantalla (los códigos solos no se entienden)
  if (departure && arrival) {
    const duration = durationMinutes > 0 ? `, ${durationMinutes} minutos` : '';
    route.setAttribute('role', 'img');
    route.setAttribute('aria-label', `De ${departure.name} a ${arrival.name}${duration}`);
  }
  return route;
}

// ── Construcción del formulario ──────────────────────────────────────────────

function _makeGroup(name, labelText, required) {
  const group = document.createElement('div');
  group.className = 'form-group';
  const label = document.createElement('label');
  label.htmlFor = name;
  label.textContent = labelText;
  if (required) {
    const mark = document.createElement('span');
    mark.className = 'required-mark';
    mark.setAttribute('aria-hidden', 'true');
    mark.textContent = ' *';
    label.appendChild(mark);
  }
  group.appendChild(label);
  return group;
}

function _makeField(name, labelText, type, required, attrs = {}) {
  const group = _makeGroup(name, labelText, required);
  const input = document.createElement('input');
  input.type = type;
  input.name = name;
  input.id = name;
  input.required = required;
  for (const [k, v] of Object.entries(attrs)) input[k] = v;
  group.appendChild(input);
  return group;
}

function _addAirportOptions(select, airports, selectedId = null) {
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = '— Seleccionar —';
  placeholder.disabled = true;
  placeholder.selected = selectedId === null;
  select.appendChild(placeholder);
  for (const airport of airports) {
    const option = document.createElement('option');
    option.value = String(airport.id);
    option.textContent = _airportOptionText(airport);
    if (selectedId !== null && airport.id === selectedId) option.selected = true;
    select.appendChild(option);
  }
}

function _airportSelect(name, labelText, airports) {
  const group = _makeGroup(name, labelText, true);
  const select = document.createElement('select');
  select.name = name;
  select.id = name;
  select.required = true;
  _addAirportOptions(select, airports);
  group.appendChild(select);
  return group;
}

// ── Vista previa de la ruta en el formulario ─────────────────────────────────

function _buildPreview() {
  const preview = document.createElement('div');
  preview.className = 'route-preview';
  preview.setAttribute('aria-live', 'polite');

  const routeSlot = document.createElement('div');

  const times = document.createElement('dl');
  times.className = 'route-times';
  const makeTime = (label) => {
    const wrap = document.createElement('div');
    const dt = document.createElement('dt');
    dt.textContent = label;
    const dd = document.createElement('dd');
    dd.textContent = '—';
    wrap.append(dt, dd);
    times.appendChild(wrap);
    return dd;
  };
  const departureEl = makeTime('Salida');
  const arrivalEl = makeTime('Llegada estimada');

  preview.append(routeSlot, times);
  return { preview, routeSlot, departureEl, arrivalEl };
}

function _updatePreview(parts, form, airportMap) {
  const dep = airportMap.get(Number(form.elements.departure_airport_id.value));
  const arr = airportMap.get(Number(form.elements.arrival_airport_id.value));
  const dateValue = form.elements.travel_date.value;
  const duration = Number(form.elements.duration_minutes.value);
  parts.routeSlot.replaceChildren(_buildRoute(dep, arr, duration));

  const departure = dateValue ? new Date(dateValue) : null;
  const validDeparture = departure && !Number.isNaN(departure.getTime());

  parts.departureEl.textContent = validDeparture ? _formatDate(departure) : '—';
  parts.arrivalEl.textContent =
    validDeparture && duration > 0 ? _formatDate(_arrivalDate(departure, duration)) : '—';
}

// ── Render principal ─────────────────────────────────────────────────────────

function _render(container, airports, airportMap, itineraries) {
  container.replaceChildren();

  const layout = document.createElement('div');
  layout.className = 'itinerary-layout';

  // ── Formulario ──────────────────────────────────────────────────────────────
  const wrapper = document.createElement('div');
  wrapper.className = 'card itinerary-wrapper';
  const wrapperBody = document.createElement('div');
  wrapperBody.className = 'card-body';
  wrapper.appendChild(wrapperBody);

  const title = document.createElement('h2');
  title.className = 'card-title';
  title.textContent = 'Nuevo itinerario';
  wrapperBody.appendChild(title);

  const errorZone = document.createElement('div');
  errorZone.className = 'form-error-zone';
  wrapperBody.appendChild(errorZone);

  const form = document.createElement('form');
  form.className = 'itinerary-form';

  const previewParts = _buildPreview();
  form.appendChild(previewParts.preview);

  form.appendChild(_makeField('traveler_name', 'Nombre del viajero', 'text', true, {
    autocomplete: 'name',
  }));
  form.appendChild(_makeField('traveler_email', 'Correo electrónico (opcional)', 'email', false, {
    autocomplete: 'email',
  }));
  form.appendChild(_airportSelect('departure_airport_id', 'Aeropuerto de salida', airports));
  form.appendChild(_airportSelect('arrival_airport_id', 'Aeropuerto de llegada', airports));
  form.appendChild(_makeField('travel_date', 'Fecha y hora de salida', 'datetime-local', true));
  form.appendChild(_makeField('duration_minutes', 'Duración (minutos)', 'number', true, {
    min: 1, step: 1, inputMode: 'numeric',
  }));

  const refreshPreview = () => _updatePreview(previewParts, form, airportMap);
  form.addEventListener('input', refreshPreview);
  form.addEventListener('change', refreshPreview);
  refreshPreview();

  // Botones
  const actions = document.createElement('div');
  actions.className = 'form-actions';

  const submitBtn = document.createElement('button');
  submitBtn.type = 'submit';
  submitBtn.className = 'btn btn-primary';
  submitBtn.textContent = 'Guardar itinerario';

  const cancelBtn = document.createElement('button');
  cancelBtn.type = 'button';
  cancelBtn.className = 'btn btn-secondary';
  cancelBtn.textContent = 'Cancelar edición';
  cancelBtn.hidden = true;

  cancelBtn.addEventListener('click', () => {
    form.reset();
    delete form.dataset.editId;
    title.textContent = 'Nuevo itinerario';
    submitBtn.textContent = 'Guardar itinerario';
    cancelBtn.hidden = true;
    errorZone.replaceChildren();
    refreshPreview();
  });

  actions.append(submitBtn, cancelBtn);
  form.appendChild(actions);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorZone.replaceChildren();
    submitBtn.disabled = true;

    const raw = Object.fromEntries(new FormData(form).entries());
    const body = {
      traveler_name:        raw.traveler_name,
      traveler_email:       raw.traveler_email || null,
      departure_airport_id: Number(raw.departure_airport_id),
      arrival_airport_id:   Number(raw.arrival_airport_id),
      travel_date:          _localToISO(raw.travel_date),
      duration_minutes:     Number(raw.duration_minutes),
    };

    const editId = form.dataset.editId;
    try {
      if (editId) {
        await apiFetch(`/api/itineraries/${editId}`, {
          method: 'PUT', body: JSON.stringify(body),
        });
      } else {
        await apiFetch('/api/itineraries', {
          method: 'POST', body: JSON.stringify(body),
        });
      }
      await loadItineraries(container);
    } catch (error) {
      submitBtn.disabled = false;
      renderError(errorZone, error);
    }
  });

  wrapperBody.appendChild(form);
  layout.appendChild(wrapper);

  // ── Lista ────────────────────────────────────────────────────────────────────
  const listSection = document.createElement('div');
  listSection.className = 'itinerary-list';

  const listHeader = document.createElement('div');
  listHeader.className = 'section-head list-header';
  const listTitle = document.createElement('h2');
  listTitle.textContent = 'Itinerarios';
  const countEl = document.createElement('span');
  countEl.className = 'section-meta itinerary-count';
  countEl.textContent =
    `${itineraries.length} registrado${itineraries.length !== 1 ? 's' : ''}`;
  listHeader.append(listTitle, countEl);
  listSection.appendChild(listHeader);

  const listCard = document.createElement('div');
  listCard.className = 'card table-card';

  if (itineraries.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'empty-state';
    empty.textContent = 'No hay itinerarios. Crea uno con el formulario.';
    listCard.appendChild(empty);
  } else {
    listCard.appendChild(
      _buildTable(itineraries, airportMap, {
        onEdit(itin) {
          // Rellenar el formulario con los datos del itinerario seleccionado
          form.elements.traveler_name.value = itin.traveler_name;
          form.elements.traveler_email.value = itin.traveler_email ?? '';
          form.elements.departure_airport_id.value = String(itin.departure_airport_id);
          form.elements.arrival_airport_id.value = String(itin.arrival_airport_id);
          form.elements.travel_date.value = _isoToLocal(itin.travel_date);
          form.elements.duration_minutes.value = String(itin.duration_minutes);
          form.dataset.editId = itin.id;
          title.textContent = 'Editar itinerario';
          submitBtn.textContent = 'Actualizar itinerario';
          cancelBtn.hidden = false;
          errorZone.replaceChildren();
          refreshPreview();
          wrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
        },
        async onDelete(itin) {
          if (!confirm(`¿Eliminar el itinerario de ${itin.traveler_name}?`)) return;
          try {
            await apiFetch(`/api/itineraries/${itin.id}`, { method: 'DELETE' });
            await loadItineraries(container);
          } catch (error) {
            renderError(errorZone, error);
            wrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        },
      }),
    );
  }

  listSection.appendChild(listCard);
  layout.appendChild(listSection);
  container.appendChild(layout);
}

// ── Tabla ────────────────────────────────────────────────────────────────────

function _cell(label, className) {
  const td = document.createElement('td');
  if (label) td.setAttribute('data-label', label);
  if (className) td.className = className;
  return td;
}

function _buildTable(itineraries, airportMap, { onEdit, onDelete }) {
  const table = document.createElement('table');
  table.className = 'itinerary-table';

  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  for (const col of ['Viajero', 'Ruta y duración', 'Horario', 'Acciones']) {
    const th = document.createElement('th');
    th.scope = 'col';
    th.textContent = col;
    headerRow.appendChild(th);
  }
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  for (const itin of itineraries) {
    const tr = document.createElement('tr');

    const tdViajero = _cell(null, 'cell-traveler');
    const name = document.createElement('span');
    name.className = 'traveler-name';
    name.textContent = itin.traveler_name;
    tdViajero.appendChild(name);
    if (itin.traveler_email) {
      const email = document.createElement('span');
      email.className = 'secondary';
      email.textContent = itin.traveler_email;
      tdViajero.appendChild(email);
    }

    const tdRuta = _cell(null, 'cell-route');
    tdRuta.appendChild(_buildRoute(
      airportMap.get(itin.departure_airport_id),
      airportMap.get(itin.arrival_airport_id),
      itin.duration_minutes,
    ));

    // Horario: salida y, debajo, la llegada estimada (salida + duración)
    const departure = new Date(itin.travel_date);
    const arrival = _arrivalDate(departure, itin.duration_minutes);
    const tdHorario = _cell('Horario', 'cell-schedule');
    const schedule = document.createElement('div');
    const departureEl = document.createElement('span');
    departureEl.className = 'schedule-departure';
    departureEl.textContent = _formatDate(departure);
    const arrivalEl = document.createElement('span');
    arrivalEl.className = 'secondary';
    arrivalEl.textContent = `Llega ${_formatArrival(departure, arrival)}`;
    schedule.append(departureEl, arrivalEl);
    tdHorario.appendChild(schedule);

    const tdAcciones = _cell(null, 'cell-actions');
    const btnGroup = document.createElement('div');
    btnGroup.className = 'action-btns';

    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'btn btn-secondary btn-sm';
    editBtn.textContent = 'Editar';
    editBtn.setAttribute('aria-label', `Editar el itinerario de ${itin.traveler_name}`);
    editBtn.addEventListener('click', () => onEdit(itin));

    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.className = 'btn btn-danger btn-sm';
    deleteBtn.textContent = 'Eliminar';
    deleteBtn.setAttribute('aria-label', `Eliminar el itinerario de ${itin.traveler_name}`);
    deleteBtn.addEventListener('click', () => onDelete(itin));

    btnGroup.append(editBtn, deleteBtn);
    tdAcciones.appendChild(btnGroup);

    tr.append(tdViajero, tdRuta, tdHorario, tdAcciones);
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  return table;
}
