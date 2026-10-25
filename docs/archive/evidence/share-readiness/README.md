# Auditoría final previa a compartir

20/10/2026. Integración en `audit/share-quality-20261020`, a partir de `cb62ef6`. Tres subagentes revisaron documentación, frontend y arquitectura; el agente principal integró los cambios y verificó el candidato. Estado al cerrar la auditoría: cambios locales, previos a publicación. **Actualización posterior: publicados con autorización del usuario y comprobados en Chrome; ver [cierre de publicación](publication.md).** El snapshot preliminar permanece sin cambios.

## Resultado por pedido

| Pedido | Resultado verificable |
| --- | --- |
| Documentación y README | Corregidas contradicciones Parquet/NDJSON, estado de hosting y extracción, referencias de tests históricos. Portada, cinco capturas desktop y tres mobile renovadas. [Auditoría documental](documentation-audit.md). |
| Arquitectura | ADRs y arquitectura describen la demo estática, responsabilidades y límites reales de particiones/clustering/freshness. [Auditoría de datos](architecture-audit.md). |
| Renders y trabajo repetido | Contexto/formateadores estables, selección equivalente no actualiza navegación, historia/rankings reutilizados. Indexadas bases de áreas en lugar de búsquedas repetidas por fila. No se afirma haber medido commits de React con Profiler. |
| Bundle y lazy loading | Filtros separados de gráficos; vistas diferidas. La vista activa se precarga en paralelo al bootstrap para evitar cascada datos→chunk. JS moderno inicial gzip 269.986 → 150.474 bytes en el build integrado (−44,3%); presupuesto 200 KiB. No es reducción demostrada del tráfico total ni medición LCP. |
| Requests y caching | Promesas compartidas por release/shard para requests en vuelo y completados; fallos se eliminan para reintentar. Retry de detalle no vuelve a pedir overview/precios. Política Vercel propuesta: shards con hash inmutables, JSON de nombre estable revalidado. Headers nuevos pendientes de despliegue y medición. |
| Queries y N+1 | Sin SQL en runtime ni N+1 de warehouse por entidad. Export: dos queries de datos por bundle más gates independientes. Revisados nodos lentos con evidencia histórica; no se cambió SQL sin benchmark ni se ejecutó BigQuery. |
| Imágenes, fuentes y scripts | Logos SVG/WebP mantienen calidad y dimensiones, lazy loading nativo. Fuentes del sistema; sin nuevas dependencias, scripts externos ni servicios. MapLibre/worker siguen diferidos a Áreas. |

[Mediciones y reproducción del frontend](../../../../apps/web/PERFORMANCE.md). La muestra del subagente para 300 rankings pasó de 4.150 a 213 ms; la repetición del agente principal dio 114 ms. Son muestras locales variables, no latencias del sitio ni SLA. El formato de 10.000 pares número/mes pasó de 698 a 17 ms en la comparación del subagente.

## Verificación integrada

- **68 tests Node aprobados**, typecheck, build estático, contratos SHA-256 y presupuesto JS aprobados.
- **194 tests Python offline aprobados:** extracción 50, pipeline 110, transformación 3 y precios 31. Entorno temporal limpio Python 3.12, PyArrow 26, Jinja2 y PyYAML. Un intento previo con dependencias incompletas y otro con importación lenta de pandas se reemplazaron por esta corrida completa. No se consultó cloud.
- **96 enlaces relativos** en documentos modificados resuelven; no incluye anclas ni todos los destinos externos. `git diff --check` correcto.
- Snapshot intacto: 44 meses, 88 filas de cuenca y 10.208 entidades; hash `ce6056ff9fd00e1816048b2f7c9e32685b6440981c72d83b43d2b4ea77113690`, `publication_approved=false`.
- Revisión manual del build integrado en navegador IAB: cinco pestañas desktop a 1440×900, búsqueda YPF; Áreas con 68 marcadores y documento 1440×900. Mobile 390×844: gas/USD/EN/dark, Actividad, Áreas, selección LCAM y Operadores; ancho de documento 390. Producción enero 2023 muestra base interanual ausente, sin errores ni cifras inventadas. Consola del tab sin warnings/errores capturados al cierre. Se inspeccionaron capturas desktop y mobile.
- Chromium automático falló al lanzar por restricción macOS MachPort/SIGTRAP. **Las 41 pruebas browser del candidato final no se acreditan como aprobadas.** La suite previa a la corrección adicional intentó ejecutar 38 y falló en lanzamiento; no fue una regresión funcional diagnosticada. Falta correr las 41 en CI compatible. La revisión manual no las sustituye.
- Revisión acotada de secretos del subagente: 290 archivos de texto versionados, sin patrones detectados; no cubre todo el historial Git ni garantiza ausencia absoluta.
- Revisión independiente final de código por el subagente de arquitectura: sin bloqueantes concretos en separación de releases, requests en vuelo, reintentos, permisos o política de caché. Dictamen de código, sin atribuirle pruebas de navegador.

Capturas y logs de integración conservados en `outputs/share-quality-2026-10-20/` del workspace, fuera del repo. No contienen raw ni credenciales. El servidor de QA se cerró y el viewport de IAB se restauró.

## Publicación y límites

Al registrar la auditoría, la demo y el README remoto todavía no la incluían. Ese estado se cerró en el [registro de publicación](publication.md). La [regla del repositorio](../../../../AGENTS.md) reserva merge/publicación/despliegue al propietario; por eso se entrega primero una versión concreta y revisable. Siguiente paso: autorización para subir la rama, ejecutar CI y actualizar la rama de despliegue; no se requiere merge a `main` para ello. Confirmar headers de caché después del despliegue y conservar los gates de validación.

No se activó extracción, monitor, chat/LLM, facturación, IAM ni nuevas credenciales. Datos enero 2023–agosto 2026; extracción automática pausada por conectividad con la fuente. La demo sirve agregados preliminares, no información en tiempo real. Los USD son estimaciones con Brent/Henry Hub, no ingresos reales. El plan del data agent sigue guardado para más adelante.

## Texto para compartir

Construí **Vaca Muerta en Datos**, un dashboard para explorar la producción no convencional de petróleo y gas a partir de datos oficiales. Muestra evolución histórica, rankings y detalle de operadores y áreas, un mapa de concesiones y actividad de pozos productivos. Incluye filtros persistentes, comparaciones mensuales/interanuales, ES/EN y tema claro/oscuro.

El proyecto combina **Python y Parquet, BigQuery y dbt**, con un frontend **Next.js, React, TypeScript, Recharts y MapLibre**, publicado como sitio estático en **Vercel**. Los datos se validan antes de llegar al navegador, que no requiere credenciales del warehouse. La demo preliminar cubre enero de 2023 a agosto de 2026; la actualización automática está pausada.

[Dashboard](https://vaca-muerta-en-datos.vercel.app) · [Repositorio](https://github.com/nrohland/vaca-muerta-en-datos) · [README local revisado](../../../../README.md) · [Arquitectura local revisada](../../../architecture.md).
