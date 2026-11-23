/**
 * Tema claro / oscuro.
 *
 * - Sin elección guardada, el tema sigue al sistema operativo (prefers-color-scheme).
 * - El botón de la cabecera fija el tema contrario al actual y lo guarda en localStorage.
 * - Cada cambio emite el evento 'themechange' en document: el mapa de Plotly lo escucha
 *   para volver a dibujarse con los colores del tema (Plotly no lee variables CSS).
 */

const STORAGE_KEY = 'theme';
const darkQuery = window.matchMedia('(prefers-color-scheme: dark)');

/** Tema efectivo en este momento: 'light' o 'dark'. */
export function currentTheme() {
  const explicit = document.documentElement.getAttribute('data-theme');
  if (explicit === 'light' || explicit === 'dark') return explicit;
  return darkQuery.matches ? 'dark' : 'light';
}

/** Lee una variable CSS del tema activo (por ejemplo '--chart-blue'). */
export function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function _save(theme) {
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Sin almacenamiento: el tema se aplica igual, solo que no se recuerda
  }
}

function _updateButton(button) {
  const next = currentTheme() === 'dark' ? 'claro' : 'oscuro';
  button.querySelector('.theme-toggle-label').textContent = `Tema ${next}`;
  button.setAttribute('aria-label', `Cambiar a tema ${next}`);
}

export function initThemeToggle(button) {
  _updateButton(button);

  button.addEventListener('click', () => {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    _save(next);
    _updateButton(button);
    document.dispatchEvent(new CustomEvent('themechange'));
  });

  // Si el usuario no eligió tema y cambia el del sistema, la página lo sigue
  darkQuery.addEventListener('change', () => {
    if (document.documentElement.hasAttribute('data-theme')) return;
    _updateButton(button);
    document.dispatchEvent(new CustomEvent('themechange'));
  });
}
