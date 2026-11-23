/**
 * Aplica el tema guardado antes de que se pinte la página.
 * Es un script clásico (no módulo) cargado en <head> sin defer, para que el atributo
 * data-theme exista antes de que el navegador aplique la hoja de estilos.
 * Si no hay elección guardada, no hace nada: manda prefers-color-scheme del sistema.
 */
(function () {
  try {
    var saved = window.localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark') {
      document.documentElement.setAttribute('data-theme', saved);
    }
  } catch (e) {
    // localStorage no disponible (ventana privada, almacenamiento bloqueado): tema del sistema
  }
})();
