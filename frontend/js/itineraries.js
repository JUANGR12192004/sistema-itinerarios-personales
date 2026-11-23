/**
 * Sección Itinerarios: CRUD completo contra /api/itineraries.
 * Carga la lista de aeropuertos una sola vez para los desplegables y la tabla.
 * Todo texto de datos se escribe con textContent (nunca innerHTML).
 *
 * La validación del navegador repite las reglas del dominio (ADR-015) para avisar antes
 * de enviar; el servidor las vuelve a validar siempre (la fuente de verdad es el backend).
 */

import { apiFetch, renderError } from './api.js';
import { buildRoute, routeDescription } from './route.js';
import { confirmAction, showToast } from './ui.js';

/**
 * Carga la sección. Con quiet = true (después de guardar o eliminar) no reemplaza el
 * contenido por el indicador de carga: la barra de la cabecera ya muestra la actividad
 * y así la página no «parpadea».
 */
export async function loadItineraries(container, { quiet = false } = {}) {
  if (!quiet || !container.hasChildNodes()) _showLoading(container);

  let airports, itineraries;
  try {
    [airports, itineraries] = await Promise.all([
      apiFetch('/api/airports'),
      apiFetch('/api/itineraries'),
    ]);
  } catch (error) {
    renderError(container, error);
    showToast('No se cargaron los itinerarios. El detalle está en la página.', 'error');
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
  const offset = -new Date(localDt).getTimezoneOffset();
  const sign = offset >= 0 ? '+' : '-';
  const abs = Math.abs(offset);
  const hh = String(Math.floor(abs / 60)).padStart(2, '0');
  const mm = String(abs % 60).padStart(2, '0');
  return `${localDt}:00${sign}${hh}:${mm}`;
}

// Date → "2026-12-15T08:00" en la hora local del navegador (formato de datetime-local)
function _toLocalInput(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${_time(date)}`;
}

// La API devuelve la fecha en UTC ("2026-12-18T13:00:00Z"). Para rellenar datetime-local hay
// que convertirla a la hora local: cortar el texto tomaría la hora UTC como si fuera local
// (en Colombia, 13:00 en vez de 08:00) y al guardar correría el viaje 5 horas.
function _isoToLocal(isoString) {
  return _toLocalInput(new Date(isoString));
}

// Fecha y hora actuales en el formato de datetime-local, para el atributo min
function _nowLocal() {
  return _toLocalInput(new Date());
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

/**
 * Agrega al grupo la zona del mensaje de error del campo y, si se pide, una zona de ayuda.
 * El control las referencia con aria-describedby para que el lector de pantalla las lea.
 */
function _attachMessages(group, control, { hint = false } = {}) {
  const ids = [];
  if (hint) {
    const hintEl = document.createElement('p');
    hintEl.className = 'field-hint';
    hintEl.id = `${control.id}-hint`;
    hintEl.hidden = true;
    group.appendChild(hintEl);
    ids.push(hintEl.id);
  }
  const error = document.createElement('p');
  error.className = 'field-error';
  error.id = `${control.id}-error`;
  error.hidden = true;
  group.appendChild(error);
  ids.push(error.id);
  control.setAttribute('aria-describedby', ids.join(' '));
}

function _makeField(name, labelText, type, required, attrs = {}, messageOptions = {}) {
  const group = _makeGroup(name, labelText, required);
  const input = document.createElement('input');
  input.type = type;
  input.name = name;
  input.id = name;
  input.required = required;
  for (const [k, v] of Object.entries(attrs)) input[k] = v;
  group.appendChild(input);
  _attachMessages(group, input, messageOptions);
  return group;
}

function _addAirportOptions(select, airports) {
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = '— Seleccionar —';
  placeholder.disabled = true;
  placeholder.selected = true;
  select.appendChild(placeholder);
  for (const airport of airports) {
    const option = document.createElement('option');
    option.value = String(airport.id);
    option.textContent = _airportOptionText(airport);
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
  _attachMessages(group, select);
  return group;
}

// ── Validación del formulario (antes de enviar) ──────────────────────────────

/**
 * Devuelve un objeto { campo: mensaje } con los errores encontrados (vacío si todo está bien).
 * Reglas de ADR-015: nombre no vacío, salida distinta de llegada, duración > 0 (así la llegada
 * es posterior a la salida) y, solo al crear, salida no en el pasado.
 */
function _validate(form, { editing }) {
  const errors = {};
  const el = form.elements;

  if (!el.traveler_name.value.trim()) {
    errors.traveler_name = 'Escribe el nombre del viajero.';
  }

  const email = el.traveler_email.value.trim();
  if (email && !el.traveler_email.checkValidity()) {
    errors.traveler_email = 'Escribe un correo válido (por ejemplo, ana@example.com) o deja el campo vacío.';
  }

  if (!el.departure_airport_id.value) {
    errors.departure_airport_id = 'Elige el aeropuerto de salida.';
  }
  if (!el.arrival_airport_id.value) {
    errors.arrival_airport_id = 'Elige el aeropuerto de llegada.';
  } else if (el.arrival_airport_id.value === el.departure_airport_id.value) {
    errors.arrival_airport_id = 'La llegada debe ser un aeropuerto distinto del de salida.';
  }

  const dateValue = el.travel_date.value;
  if (!dateValue) {
    errors.travel_date = 'Elige la fecha y la hora de salida.';
  } else if (!editing && new Date(dateValue) <= new Date()) {
    errors.travel_date =
      'La salida no puede estar en el pasado. Elige una fecha y hora posteriores a este momento.';
  }

  const durationText = el.duration_minutes.value.trim();
  const duration = Number(durationText);
  if (!durationText) {
    errors.duration_minutes = 'Escribe la duración del vuelo en minutos.';
  } else if (!Number.isInteger(duration) || duration <= 0) {
    errors.duration_minutes =
      'La duración debe ser un número entero de minutos mayor que 0, para que la llegada sea posterior a la salida.';
  }

  return errors;
}

/** Pinta (o limpia) el mensaje de error de cada campo y marca aria-invalid. */
function _showFieldErrors(form, errors) {
  for (const name of FIELD_NAMES) {
    const control = form.elements[name];
    const errorEl = form.querySelector(`#${name}-error`);
    const message = errors[name];
    control.setAttribute('aria-invalid', message ? 'true' : 'false');
    errorEl.textContent = message ?? '';
    errorEl.hidden = !message;
  }
}

const FIELD_NAMES = [
  'traveler_name', 'traveler_email', 'departure_airport_id',
  'arrival_airport_id', 'travel_date', 'duration_minutes',
];

// ── Vista previa de la ruta en el formulario ─────────────────────────────────

function _buildPreview() {
  const preview = document.createElement('div');
  preview.className = 'route-preview';

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
  parts.routeSlot.replaceChildren(buildRoute(dep, arr, duration));

  const departure = dateValue ? new Date(dateValue) : null;
  const validDeparture = departure && !Number.isNaN(departure.getTime());

  parts.departureEl.textContent = validDeparture ? _formatDate(departure) : '—';
  parts.arrivalEl.textContent =
    validDeparture && Number.isInteger(duration) && duration > 0
      ? _formatDate(_arrivalDate(departure, duration))
      : '—';
}

/**
 * Al editar un viaje cuya salida ya pasó, el servidor acepta el cambio (la regla de fecha
 * futura es solo de creación, ADR-015). En vez de bloquear, se explica bajo el campo.
 */
function _updatePastTripHint(form) {
  const hint = form.querySelector('#travel_date-hint');
  const dateValue = form.elements.travel_date.value;
  const isPast = Boolean(form.dataset.editId) && dateValue && new Date(dateValue) <= new Date();
  hint.textContent = isPast
    ? 'Este viaje ya salió. Puedes guardar los cambios igual: solo los itinerarios nuevos deben salir en el futuro.'
    : '';
  hint.hidden = !isPast;
}

// ── Botón de envío con estado de carga ───────────────────────────────────────

function _setSubmitting(button, submitting, label) {
  button.disabled = submitting;
  button.replaceChildren();
  if (submitting) {
    const spinner = document.createElement('span');
    spinner.className = 'spinner spinner-sm';
    spinner.setAttribute('aria-hidden', 'true');
    button.appendChild(spinner);
  }
  button.appendChild(document.createTextNode(label));
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
  title.id = 'itinerary-form-title';
  title.textContent = 'Nuevo itinerario';
  wrapperBody.appendChild(title);

  const errorZone = document.createElement('div');
  errorZone.className = 'form-error-zone';
  wrapperBody.appendChild(errorZone);

  const form = document.createElement('form');
  form.className = 'itinerary-form';
  form.noValidate = true; // la validación la hace _validate, con mensajes en español
  form.setAttribute('aria-labelledby', 'itinerary-form-title');

  const previewParts = _buildPreview();
  form.appendChild(previewParts.preview);

  form.appendChild(_makeField('traveler_name', 'Nombre del viajero', 'text', true, {
    autocomplete: 'name', maxLength: 200,
  }));
  form.appendChild(_makeField('traveler_email', 'Correo electrónico (opcional)', 'email', false, {
    autocomplete: 'email',
  }));
  form.appendChild(_airportSelect('departure_airport_id', 'Aeropuerto de salida', airports));
  form.appendChild(_airportSelect('arrival_airport_id', 'Aeropuerto de llegada', airports));
  form.appendChild(_makeField('travel_date', 'Fecha y hora de salida', 'datetime-local', true, {
    min: _nowLocal(),
  }, { hint: true }));
  form.appendChild(_makeField('duration_minutes', 'Duración (minutos)', 'number', true, {
    min: 1, step: 1, inputMode: 'numeric',
  }));

  // Tras el primer intento de envío, los errores se actualizan mientras se escribe
  let attempted = false;
  const refresh = () => {
    _updatePreview(previewParts, form, airportMap);
    _updatePastTripHint(form);
    if (attempted) _showFieldErrors(form, _validate(form, { editing: Boolean(form.dataset.editId) }));
  };
  form.addEventListener('input', refresh);
  form.addEventListener('change', refresh);
  refresh();

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

  const resetToCreate = () => {
    form.reset();
    delete form.dataset.editId;
    form.elements.travel_date.min = _nowLocal();
    attempted = false;
    title.textContent = 'Nuevo itinerario';
    submitBtn.textContent = 'Guardar itinerario';
    cancelBtn.hidden = true;
    errorZone.replaceChildren();
    _showFieldErrors(form, {});
    refresh();
  };
  cancelBtn.addEventListener('click', resetToCreate);

  actions.append(submitBtn, cancelBtn);
  form.appendChild(actions);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorZone.replaceChildren();
    const editId = form.dataset.editId;

    attempted = true;
    const errors = _validate(form, { editing: Boolean(editId) });
    _showFieldErrors(form, errors);
    const firstInvalid = FIELD_NAMES.find((name) => errors[name]);
    if (firstInvalid) {
      form.elements[firstInvalid].focus();
      const count = Object.keys(errors).length;
      showToast(
        count === 1 ? 'Revisa el campo marcado antes de guardar.' : `Revisa los ${count} campos marcados antes de guardar.`,
        'error',
      );
      return;
    }

    const raw = Object.fromEntries(new FormData(form).entries());
    const body = {
      traveler_name:        raw.traveler_name.trim(),
      traveler_email:       raw.traveler_email.trim() || null,
      departure_airport_id: Number(raw.departure_airport_id),
      arrival_airport_id:   Number(raw.arrival_airport_id),
      travel_date:          _localToISO(raw.travel_date),
      duration_minutes:     Number(raw.duration_minutes),
    };

    const idleLabel = submitBtn.textContent;
    _setSubmitting(submitBtn, true, editId ? 'Actualizando…' : 'Guardando…');
    cancelBtn.disabled = true;
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
      showToast(editId ? 'Itinerario actualizado.' : 'Itinerario guardado.');
      await loadItineraries(container, { quiet: true });
    } catch (error) {
      _setSubmitting(submitBtn, false, idleLabel);
      cancelBtn.disabled = false;
      renderError(errorZone, error);
      showToast(
        editId ? 'No se actualizó el itinerario. El detalle está en el formulario.'
          : 'No se guardó el itinerario. El detalle está en el formulario.',
        'error',
      );
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

  const listErrorZone = document.createElement('div');
  listErrorZone.className = 'form-error-zone';
  listSection.appendChild(listErrorZone);

  const listCard = document.createElement('div');
  listCard.className = 'card table-card';

  if (itineraries.length === 0) {
    listCard.appendChild(_buildEmptyState(form));
  } else {
    const hint = document.createElement('p');
    hint.className = 'list-hint';
    hint.textContent = 'Elige una ruta para verla en el mapa.';
    listSection.appendChild(hint);

    listCard.appendChild(
      _buildTable(itineraries, airportMap, {
        onEdit(itin) {
          // Rellenar el formulario con los datos del itinerario seleccionado
          resetToCreate();
          form.elements.traveler_name.value = itin.traveler_name;
          form.elements.traveler_email.value = itin.traveler_email ?? '';
          form.elements.departure_airport_id.value = String(itin.departure_airport_id);
          form.elements.arrival_airport_id.value = String(itin.arrival_airport_id);
          form.elements.travel_date.value = _isoToLocal(itin.travel_date);
          form.elements.travel_date.removeAttribute('min'); // un viaje ya pasado se puede editar
          form.elements.duration_minutes.value = String(itin.duration_minutes);
          form.dataset.editId = itin.id;
          title.textContent = 'Editar itinerario';
          submitBtn.textContent = 'Actualizar itinerario';
          cancelBtn.hidden = false;
          refresh();
          wrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
          form.elements.traveler_name.focus({ preventScroll: true });
        },
        async onDelete(itin, triggerButton) {
          const confirmed = await confirmAction({
            title: 'Eliminar itinerario',
            message: `Se eliminará el itinerario de ${itin.traveler_name}. Esta acción no se puede deshacer.`,
            confirmLabel: 'Eliminar itinerario',
          });
          if (!confirmed) {
            triggerButton.focus();
            return;
          }
          listErrorZone.replaceChildren();
          triggerButton.disabled = true;
          triggerButton.textContent = 'Eliminando…';
          try {
            await apiFetch(`/api/itineraries/${itin.id}`, { method: 'DELETE' });
            showToast('Itinerario eliminado.');
            await loadItineraries(container, { quiet: true });
          } catch (error) {
            triggerButton.disabled = false;
            triggerButton.textContent = 'Eliminar';
            renderError(listErrorZone, error);
            showToast('No se eliminó el itinerario. El detalle está sobre la lista.', 'error');
          }
        },
        onShowRoute(itin, departure, arrival) {
          document.dispatchEvent(new CustomEvent('showroute', {
            detail: {
              travelerName: itin.traveler_name,
              durationMinutes: itin.duration_minutes,
              departure,
              arrival,
            },
          }));
        },
      }),
    );
  }

  listSection.appendChild(listCard);
  layout.appendChild(listSection);
  container.appendChild(layout);
}

// ── Estado vacío ─────────────────────────────────────────────────────────────

function _buildEmptyState(form) {
  const empty = document.createElement('div');
  empty.className = 'empty-state';

  const heading = document.createElement('p');
  heading.className = 'empty-title';
  heading.textContent = 'Todavía no hay itinerarios';

  const text = document.createElement('p');
  text.textContent = 'Elige la salida, la llegada y la fecha del viaje en el formulario para planear el primero.';

  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'btn btn-secondary';
  button.textContent = 'Crear el primer itinerario';
  button.addEventListener('click', () => {
    form.scrollIntoView({ behavior: 'smooth', block: 'start' });
    form.elements.traveler_name.focus({ preventScroll: true });
  });

  empty.append(buildRoute(null, null, null, { decorative: true }), heading, text, button);
  return empty;
}

// ── Tabla ────────────────────────────────────────────────────────────────────

function _cell(label, className) {
  const td = document.createElement('td');
  if (label) td.setAttribute('data-label', label);
  if (className) td.className = className;
  return td;
}

function _buildTable(itineraries, airportMap, { onEdit, onDelete, onShowRoute }) {
  const table = document.createElement('table');
  table.className = 'itinerary-table';

  const caption = document.createElement('caption');
  caption.className = 'visually-hidden';
  caption.textContent = 'Itinerarios registrados';
  table.appendChild(caption);

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
    const departureAirport = airportMap.get(itin.departure_airport_id);
    const arrivalAirport = airportMap.get(itin.arrival_airport_id);

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

    // La ruta es un botón: lleva al mapa con el origen y el destino resaltados
    const tdRuta = _cell(null, 'cell-route');
    const route = buildRoute(departureAirport, arrivalAirport, itin.duration_minutes, { decorative: true });
    if (departureAirport && arrivalAirport) {
      const routeBtn = document.createElement('button');
      routeBtn.type = 'button';
      routeBtn.className = 'route-button';
      routeBtn.title = 'Ver en el mapa';
      routeBtn.setAttribute(
        'aria-label',
        `Ver en el mapa la ruta de ${itin.traveler_name}: ${routeDescription(departureAirport, arrivalAirport, itin.duration_minutes)}`,
      );
      routeBtn.appendChild(route);
      routeBtn.addEventListener('click', () => onShowRoute(itin, departureAirport, arrivalAirport));
      tdRuta.appendChild(routeBtn);
    } else {
      // Aeropuerto que ya no está en el catálogo: se muestra el id, sin enlace al mapa
      tdRuta.appendChild(route);
      const missing = document.createElement('span');
      missing.className = 'secondary';
      missing.textContent =
        `Los aeropuertos ${itin.departure_airport_id} y ${itin.arrival_airport_id} no están en el catálogo`;
      tdRuta.appendChild(missing);
    }

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
    deleteBtn.addEventListener('click', () => onDelete(itin, deleteBtn));

    btnGroup.append(editBtn, deleteBtn);
    tdAcciones.appendChild(btnGroup);

    tr.append(tdViajero, tdRuta, tdHorario, tdAcciones);
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  return table;
}
