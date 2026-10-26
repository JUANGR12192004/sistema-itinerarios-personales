## Qué incluye

<!-- Resume qué agrega o cambia este pull request. Si es una fase o entrega, indícala (por ejemplo: Fase 2, entrega 2A). -->

-

## Cómo probarlo

<!-- Pasos y comandos para que quien revisa lo compruebe. Incluye PowerShell y CMD si los comandos cambian. -->

```powershell
cd services\<servicio>
.\.venv\Scripts\Activate.ps1
pytest -v
```

## Evidencias

<!-- Resultado de las pruebas y capturas (Swagger, consola, curl.exe, mapa, etc.). -->

**Pruebas:**

```
N passed
```

**Capturas:**

## Decisiones tomadas

<!-- Decisiones de diseño o de alcance tomadas en este PR, y dónde quedaron registradas (CLAUDE.md, docs/06-decisiones-arquitectonicas.md). Escribe "Ninguna" si no aplica. -->

-

## Issues relacionados

<!-- Usa "Closes #N" para que el issue se cierre automáticamente al fusionar. Un "Closes" por issue. -->

Closes #

## Lista de verificación

- [ ] Las pruebas pasan localmente y en la integración continua.
- [ ] `CLAUDE.md` actualizado (sección 15 y decisiones, si aplica).
- [ ] Documentación actualizada si aplica (`README.md`, `docs/`, README del servicio).
- [ ] No se suben archivos `.env` ni entornos virtuales (`.venv`).
- [ ] Los commits siguen Conventional Commits (prefijo en inglés, descripción en español).
