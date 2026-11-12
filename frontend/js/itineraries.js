/**
 * Sección Itinerarios: CRUD completo contra /api/itineraries.
 * Carga la lista de aeropuertos una sola vez para los desplegables y la tabla.
 * Todo texto de datos se escribe con textContent (nunca innerHTML).
 */

import { apiFetch, renderError } from './api.js';

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

function _airportTableLabel(id, airportMap) {
  const a = airportMap.get(id);
  if (!a) return String(id);
  return a.iata_code ? `${a.iata_code} — ${a.city}` : `${a.name} — ${a.city}`;
}

function _airportOptionText(airport) {
  const iata = airport.iata_code ? ` (${airport.iata_code})` : '';
  return `${airport.name}${iata} — ${airport.city}`;
}

function _formatDate(isoString) {
  return new Date(isoString).toLocaleString('es', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
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

// ── Construcción del formulario ──────────────────────────────────────────────

function _makeGroup(name, labelText, required) {
  const group = document.createElement('div');
  group.className = 'form-group';
  const label = document.createElement('label');
  label.htmlFor = name;
  label.textContent = labelText + (required ? ' *' : '');
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

// ── Render principal ─────────────────────────────────────────────────────────

function _render(container, airports, airportMap, itineraries) {
  container.replaceChildren();

  // ── Formulario ──────────────────────────────────────────────────────────────
  const wrapper = document.createElement('div');
  wrapper.className = 'itinerary-wrapper';

  const title = document.createElement('h2');
  title.className = 'section-title';
  title.textContent = 'Nuevo itinerario';
  wrapper.appendChild(title);

  const errorZone = document.createElement('div');
  errorZone.className = 'form-error-zone';
  wrapper.appendChild(errorZone);

  const form = document.createElement('form');
  form.className = 'itinerary-form';

  // Fila 1: nombre y correo
  form.appendChild(_makeField('traveler_name', 'Nombre del viajero', 'text', true));
  form.appendChild(_makeField('traveler_email', 'Correo electrónico (opcional)', 'email', false));

  // Fila 2: aeropuertos (select creado a mano para poder llenarlo)
  const depGroup = _makeGroup('departure_airport_id', 'Aeropuerto de salida', true);
  const depSelect = document.createElement('select');
  depSelect.name = 'departure_airport_id';
  depSelect.id = 'departure_airport_id';
  depSelect.required = true;
  _addAirportOptions(depSelect, airports);
  depGroup.appendChild(depSelect);
  form.appendChild(depGroup);

  const arrGroup = _makeGroup('arrival_airport_id', 'Aeropuerto de llegada', true);
  const arrSelect = document.createElement('select');
  arrSelect.name = 'arrival_airport_id';
  arrSelect.id = 'arrival_airport_id';
  arrSelect.required = true;
  _addAirportOptions(arrSelect, airports);
  arrGroup.appendChild(arrSelect);
  form.appendChild(arrGroup);

  // Fila 3: fecha y duración
  form.appendChild(_makeField('travel_date', 'Fecha y hora de salida', 'datetime-local', true));
  form.appendChild(_makeField('duration_minutes', 'Duración (minutos)', 'number', true, { min: 1, step: 1 }));

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
  cancelBtn.textContent = 'Cancelar';
  cancelBtn.style.display = 'none';

  cancelBtn.addEventListener('click', () => {
    form.reset();
    delete form.dataset.editId;
    title.textContent = 'Nuevo itinerario';
    submitBtn.textContent = 'Guardar itinerario';
    cancelBtn.style.display = 'none';
    errorZone.replaceChildren();
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

  wrapper.appendChild(form);
  container.appendChild(wrapper);

  // ── Lista ────────────────────────────────────────────────────────────────────
  const listSection = document.createElement('div');
  listSection.className = 'itinerary-list';

  const listHeader = document.createElement('div');
  listHeader.className = 'list-header';
  const listTitle = document.createElement('h2');
  listTitle.className = 'section-title';
  listTitle.textContent = 'Itinerarios';
  const countEl = document.createElement('span');
  countEl.className = 'itinerary-count';
  countEl.textContent =
    `${itineraries.length} registrado${itineraries.length !== 1 ? 's' : ''}`;
  listHeader.append(listTitle, countEl);
  listSection.appendChild(listHeader);

  if (itineraries.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'empty-state';
    empty.textContent = 'No hay itinerarios. Crea uno con el formulario de arriba.';
    listSection.appendChild(empty);
  } else {
    listSection.appendChild(
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
          cancelBtn.style.display = '';
          errorZone.replaceChildren();
          wrapper.scrollIntoView({ behavior: 'smooth' });
        },
        async onDelete(itin) {
          if (!confirm(`¿Eliminar el itinerario de ${itin.traveler_name}?`)) return;
          try {
            await apiFetch(`/api/itineraries/${itin.id}`, { method: 'DELETE' });
            await loadItineraries(container);
          } catch (error) {
            renderError(errorZone, error);
            wrapper.scrollIntoView({ behavior: 'smooth' });
          }
        },
      }),
    );
  }

  container.appendChild(listSection);
}

// ── Tabla ────────────────────────────────────────────────────────────────────

function _buildTable(itineraries, airportMap, { onEdit, onDelete }) {
  const table = document.createElement('table');
  table.className = 'itinerary-table';

  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  for (const col of ['Viajero', 'Salida', 'Llegada', 'Fecha', 'Duración', 'Acciones']) {
    const th = document.createElement('th');
    th.textContent = col;
    headerRow.appendChild(th);
  }
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  for (const itin of itineraries) {
    const tr = document.createElement('tr');

    const tdViajero = document.createElement('td');
    tdViajero.textContent = itin.traveler_name;
    if (itin.traveler_email) {
      const email = document.createElement('span');
      email.className = 'secondary';
      email.textContent = itin.traveler_email;
      tdViajero.appendChild(email);
    }

    const tdSalida = document.createElement('td');
    tdSalida.textContent = _airportTableLabel(itin.departure_airport_id, airportMap);

    const tdLlegada = document.createElement('td');
    tdLlegada.textContent = _airportTableLabel(itin.arrival_airport_id, airportMap);

    const tdFecha = document.createElement('td');
    tdFecha.textContent = _formatDate(itin.travel_date);

    const tdDuracion = document.createElement('td');
    tdDuracion.textContent = `${itin.duration_minutes} min`;

    const tdAcciones = document.createElement('td');
    const btnGroup = document.createElement('div');
    btnGroup.className = 'action-btns';

    const editBtn = document.createElement('button');
    editBtn.type = 'button';
    editBtn.className = 'btn btn-secondary btn-sm';
    editBtn.textContent = 'Editar';
    editBtn.addEventListener('click', () => onEdit(itin));

    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.className = 'btn btn-danger btn-sm';
    deleteBtn.textContent = 'Eliminar';
    deleteBtn.addEventListener('click', () => onDelete(itin));

    btnGroup.append(editBtn, deleteBtn);
    tdAcciones.appendChild(btnGroup);

    tr.append(tdViajero, tdSalida, tdLlegada, tdFecha, tdDuracion, tdAcciones);
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  return table;
}
