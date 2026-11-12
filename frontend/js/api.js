/**
 * Capa de comunicación con el API Gateway.
 * Toda la interacción HTTP del frontend pasa por apiFetch.
 * Los errores se normalizan siempre a ApiError para que las vistas
 * no tengan que manejar distintos formatos de fallo.
 */

export class ApiError extends Error {
  constructor(code, message, details, correlationId, status) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.details = details;
    this.correlationId = correlationId;
    this.status = status;
  }
}

/**
 * Realiza una petición al gateway y devuelve el cuerpo JSON parseado.
 * Las respuestas 204 devuelven null.
 * Lanza ApiError en cualquier condición de error.
 */
export async function apiFetch(path, opts = {}) {
  const options = {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  };
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new ApiError(
      'NETWORK_ERROR',
      'No se pudo conectar con el servidor.',
      null,
      null,
      0,
    );
  }
  if (response.status === 204) return null;
  let body;
  try {
    body = await response.json();
  } catch {
    throw new ApiError(
      'INVALID_RESPONSE',
      'El servidor devolvió una respuesta inesperada.',
      null,
      response.headers.get('x-correlation-id'),
      response.status,
    );
  }
  if (!response.ok) {
    const err = body?.error ?? {};
    throw new ApiError(
      err.code ?? 'UNKNOWN_ERROR',
      err.message ?? 'Error desconocido.',
      err.details ?? null,
      body.correlation_id ?? response.headers.get('x-correlation-id'),
      response.status,
    );
  }
  return body;
}

/**
 * Pinta un error dentro de container limpiando el contenido anterior.
 * Muestra el correlation_id con botón de copia en errores 5xx.
 * Todo el texto de datos se pinta con textContent (nunca innerHTML).
 */
export function renderError(container, error) {
  container.replaceChildren();
  const banner = document.createElement('div');
  banner.className =
    'error-banner' +
    (error instanceof ApiError && error.status >= 500 ? ' error' : '');

  const msg = document.createElement('div');
  msg.className = 'error-message';

  const title = document.createElement('strong');
  title.textContent = error.message;
  msg.appendChild(title);

  if (error instanceof ApiError && error.details) {
    const detail = document.createElement('p');
    detail.textContent = _formatDetails(error.code, error.details);
    msg.appendChild(detail);
  }

  if (error instanceof ApiError && error.correlationId) {
    const corr = document.createElement('div');
    corr.className = 'error-correlation';
    corr.appendChild(document.createTextNode('ID de error: '));

    const idSpan = document.createElement('code');
    idSpan.textContent = error.correlationId;
    corr.appendChild(idSpan);

    const copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.className = 'btn-copy';
    copyBtn.textContent = 'Copiar';
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(error.correlationId).then(() => {
        copyBtn.textContent = '¡Copiado!';
        setTimeout(() => {
          copyBtn.textContent = 'Copiar';
        }, 1500);
      });
    });
    corr.appendChild(copyBtn);
    msg.appendChild(corr);
  }

  banner.appendChild(msg);
  container.appendChild(banner);
}

function _formatDetails(code, details) {
  if (code === 'VALIDATION_ERROR' && Array.isArray(details.errors)) {
    return details.errors
      .map((e) => `${Array.isArray(e.loc) ? e.loc.join('.') : 'campo'}: ${e.msg}`)
      .join('; ');
  }
  if (typeof details.field === 'string') return `Campo: ${details.field}`;
  return JSON.stringify(details);
}
