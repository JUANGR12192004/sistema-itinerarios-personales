/**
 * Piezas de interfaz comunes: avisos (toasts) y diálogo de confirmación.
 * Todo texto se escribe con textContent (nunca innerHTML).
 */

const TOAST_DURATION_MS = { success: 4000, error: 7000 };

/**
 * Muestra un aviso que se cierra solo.
 * - type 'success': región aria-live="polite" (el lector lo anuncia sin interrumpir).
 * - type 'error': región role="alert" (se anuncia de inmediato).
 * El temporizador se pausa mientras el cursor o el foco están sobre el aviso.
 */
export function showToast(message, type = 'success') {
  const region = document.getElementById(type === 'error' ? 'toast-alerts' : 'toast-status');
  if (!region) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const text = document.createElement('p');
  text.className = 'toast-message';
  text.textContent = message;

  const close = document.createElement('button');
  close.type = 'button';
  close.className = 'toast-close';
  close.setAttribute('aria-label', 'Cerrar aviso');
  close.textContent = '×';

  toast.append(text, close);
  region.appendChild(toast);

  let timer = null;
  const dismiss = () => {
    clearTimeout(timer);
    toast.remove();
  };
  const start = () => {
    clearTimeout(timer);
    timer = setTimeout(dismiss, TOAST_DURATION_MS[type] ?? TOAST_DURATION_MS.success);
  };
  const pause = () => clearTimeout(timer);

  close.addEventListener('click', dismiss);
  toast.addEventListener('mouseenter', pause);
  toast.addEventListener('mouseleave', start);
  toast.addEventListener('focusin', pause);
  toast.addEventListener('focusout', start);
  start();
}

/**
 * Pide confirmación con el <dialog> nativo de index.html.
 * Devuelve una promesa con true (confirmó) o false (canceló o pulsó Escape).
 * El foco empieza en «Cancelar»: la opción segura para una acción que no se puede deshacer.
 */
export function confirmAction({ title, message, confirmLabel }) {
  const dialog = document.getElementById('confirm-dialog');
  dialog.querySelector('#confirm-title').textContent = title;
  dialog.querySelector('#confirm-message').textContent = message;
  dialog.querySelector('.confirm-accept').textContent = confirmLabel;

  return new Promise((resolve) => {
    dialog.addEventListener(
      'close',
      () => resolve(dialog.returnValue === 'confirm'),
      { once: true },
    );
    dialog.returnValue = '';
    dialog.showModal();
    dialog.querySelector('.confirm-cancel').focus();
  });
}
