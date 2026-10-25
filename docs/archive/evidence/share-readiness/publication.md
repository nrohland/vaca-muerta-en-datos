# Publicación de las mejoras y QA en Chrome

Mejoras autorizadas por Nicolás después de la auditoría. Código integrado por fast-forward a `feat/dashboard-visual-polish`, sin merge a `main`. El PR [#55](https://github.com/nrohland/vaca-muerta-en-datos/pull/55) quedó integrado contra esa rama de despliegue.

## Validación de código

Commit `2e8d46843a460cbf1d71b54339d2e1181335b192`:

- [CI 39511599481](https://github.com/nrohland/vaca-muerta-en-datos/actions/runs/39511599481): validate, browser y architecture aprobados.
- **41 pruebas browser aprobadas en 48,2 s**, incluyendo reintentos sin recargar overview, precarga paralela del tab activo y requests compartidos al navegar rápidamente.
- 68 tests Node, 194 tests Python offline, typecheck/build y contrato de snapshot aprobados en la auditoría integrada. La corrida CI también ejecutó sus gates correspondientes.
- Sin nueva extracción, consultas BigQuery ni cambios en datos, credenciales o facturación.

## Producción

[Deployment GJ7sL8DsrtmUAtzzPApZ1ppraakx](https://vercel.com/nicolasrohland-2302/vaca-muerta-en-datos/GJ7sL8DsrtmUAtzzPApZ1ppraakx) verificado **Ready / Production**, commit `2e8d468`, rama `feat/dashboard-visual-polish`, dominio [vaca-muerta-en-datos.vercel.app](https://vaca-muerta-en-datos.vercel.app).

Requests HTTPS públicos confirmaron 200 y estas políticas:

| Recurso | Cache-Control efectivo |
| --- | --- |
| `data/manifest.json` | `public, max-age=0, must-revalidate` |
| `data/snapshots/<releaseSHA>/overview-<hash>.json.gz` | `public, max-age=31536000, immutable` |

El reporte público de build registra **149.957 bytes gzip** de JavaScript moderno inicial, dentro de 200 KiB. No es medición de LCP ni del tráfico total de una sesión. Las dependencias de gráficos siguen descargándose cuando se necesitan.

## Revisión solicitada en Google Chrome

Inspección manual de la demo publicada mediante Chrome:

- Cinco pestañas en desktop 1440×900; búsqueda YPF, rankings y mapa con 68 marcadores. Áreas conserva documento 1440×900.
- Gas/USD, EN y tema oscuro; mobile efectivo 390×844 y documento de 390 px, sin overflow horizontal de página observado.
- Selección LCAM desde ranking, URL con ID correcto y persistencia al recargar; detalle de área disponible.
- Enero de 2023 conserva falta de comparación interanual, sin inventar valores.
- Operadores, Áreas, Actividad y Producción en viewport mobile; consola del tab sin warnings/errores capturados al cierre.

Capturas y logs persistentes: `outputs/share-quality-2026-10-20/chrome-production/` y `ci-browser/` en el workspace de ejecución. Se inspeccionaron imágenes desktop/mobile. Los archivos sólo documentan estados públicos y no contienen credenciales. No es prueba en dispositivo físico ni medición de campo. Se restauró el viewport de Chrome al terminar.

El snapshot conserva enero de 2023–agosto de 2026, carácter preliminar y hash `ce6056ff9fd00e1816048b2f7c9e32685b6440981c72d83b43d2b4ea77113690`. Extracción y monitor siguen pausados. El chat continúa diferido. Este registro documental no cambia código ejecutable ni cálculos; las revisiones posteriores del mismo código pueden identificarse por el historial Git.
