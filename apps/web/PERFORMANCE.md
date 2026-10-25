# Rendimiento del frontend

Auditoría local del 20 de octubre de 2026. Se conservan datos, definiciones y diseño.

**Publicación validada posteriormente:** 41 pruebas browser aprobadas en CI, revisión manual Chrome desktop/mobile y headers de caché verificados en producción. El build de Vercel registra 149.957 bytes gzip iniciales, frente a 150.474 en el build local integrado; la diferencia depende del base path/build. [Cierre y evidencia](../../docs/archive/evidence/share-readiness/publication.md). Las limitaciones de la auditoría original se conservan abajo como registro histórico.

| Medición | Antes | Después | Alcance |
| --- | ---: | ---: | --- |
| JavaScript moderno en el HTML, gzip | 269.986 bytes | 150.475 bytes | −44,3%; export local, no bytes de toda la sesión |
| JavaScript moderno en el HTML, sin comprimir | 917.067 bytes | 508.211 bytes | Gráficos diferidos hasta abrir una vista con datos válidos |
| 300 rankings de áreas | 4.150 ms | 213 ms | Mismo snapshot, proceso Node local |
| 10.000 pares número/mes | 698 ms | 17 ms | Mismo locale y valores; reutilización de Intl |

Las cifras CPU son muestras comparables, no un SLA ni Core Web Vitals. El Resumen
necesita descargar su módulo de gráficos al mostrarse; diferirlo reduce el JavaScript
inicial, no elimina ese trabajo ni demuestra una reducción del payload total de sesión.
MapLibre y su worker ya se descargaban sólo en Áreas y mantienen esa separación.

## Cambios

- Filtros globales separados del módulo analítico; Resumen se carga dinámicamente,
  al igual que las otras vistas. Se precarga sólo el módulo de la vista activa
  desde la URL en paralelo al bootstrap de datos, para evitar una cascada
  datos → gráficos. Estado de carga traducido durante la descarga.
- Bases de comparación de áreas indexadas por ID/mes; sin búsquedas del histórico
  por cada fila. Filtros locales reutilizan el ranking calculado y preservan
  denominadores, ceros, ausencias y comparaciones de calendario exactas.
- Historia de operadores/áreas reutilizada en interacciones de búsqueda o tarjetas;
  detalle de operador no prepara las tres series de líderes que no muestra.
- Formatos Intl y valor del contexto de idioma estables. Un filtro ya activo no
  agrega otra navegación ni dispara una actualización de selección equivalente.
- Un reintento de detalle vuelve a pedir sólo ese shard; no descarga nuevamente
  manifiesto, resumen y precios. La caché de promesas por hash reutiliza también
  una descarga en vuelo al salir y volver rápidamente; los errores se expulsan
  para permitir reintentos. Sólo el consumidor activo actualiza su vista.
- Shards con hash: `Cache-Control: public, max-age=31536000, immutable` en Vercel.
  JSON de nombre estable: `max-age=0, must-revalidate`; fetch de manifiesto,
  aprobación y precios revalida también en el browser. Hashes y contratos siguen
  verificándose antes de usar los datos. Configuración en `vercel.json`.
- Logos fuera de vista con lazy loading nativo y dimensiones explícitas. Se
  conservan SVG y WebP existentes, sin otra compresión que reduzca calidad. Las
  fuentes son del sistema: no hay solicitudes externas de fuentes ni scripts
  de analítica de terceros añadidos.

No existe SQL, ORM ni conexión al warehouse en el frontend: las búsquedas repetidas
eran recorridos de arrays locales, no N+1 de red/base de datos. Los requests del mapa
base OSM siguen sujetos a su disponibilidad y política de caché; no se precargan.

## Reproducir y límites

Desde `apps/web`:

```sh
npm run typecheck
npm test
npm run build
node --experimental-strip-types scripts/benchmark_analysis.mjs
npm run test:browser
```

El build impone ahora 200 KiB gzip para scripts modernos en el HTML (antes 350 KiB).
Typecheck, 68 tests Node y build pasaron en el checkout de auditoría. La suite de
navegador contiene 41 pruebas, incluyendo reintento sin descargar el resumen y
navegación sin duplicados, precarga paralela y descarga en vuelo compartida; enumerarla no equivale a ejecutarla. La validación real
de navegador y los headers efectivos de Vercel deben registrarse en la integración;
este informe no acredita un nuevo despliegue ni una medición de tráfico real.

Documentación de la plataforma: [headers de caché](https://vercel.com/docs/caching/cache-control-headers)
y [configuración estática](https://vercel.com/docs/project-configuration/vercel-json).
