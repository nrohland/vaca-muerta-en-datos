# Arquitectura — Vaca Muerta en Datos

La arquitectura separa fuente, semántica analítica y presentación. Python obtiene snapshots oficiales; BigQuery conserva datos aislados y dbt construye reglas y agregados verificables. El frontend consume JSON de revisión, sin credenciales ni consultas raw desde el browser. [Producto y preguntas](../README.md), [decisiones](adrs/README.md) y [linaje real](lineage/README.md).

## Recorrido implementado

```mermaid
flowchart LR
  SE["Capítulo IV · cuatro CSV oficiales"] --> PY["Python · esquema, hashes y cobertura"]
  EIA["EIA · Brent y Henry Hub mensuales"] --> PY
  PY --> RAW["BigQuery · raw candidato aislado"]
  RAW --> STG["dbt staging · tipos y claves"]
  STG --> INT["Intermediate · universo y reglas"]
  INT --> MART["Marts · pozos, entidades y USD"]
  MART --> GATE["Tests, frescura y conciliación"]
  GATE --> EXPORT["Export agregado y manifiestos"]
  EXPORT --> CHECK["Contrato del consumidor + hashes"]
  CHECK --> WEB["Next.js · componentes React/Recharts"]
```

El CLI encadena transformación histórica, export y validación del contrato frontend. GitHub tiene preparación pública antes de WIF, identidades de carga/dbt separadas y tests/build del consumidor; su calendario permanece desactivado. La promoción pública es una decisión independiente, no una etapa implícita de construcción.

## Capas y motivos

| Capa | Implementación | Motivo |
| --- | --- | --- |
| Fuente | Declaraciones oficiales pozo × mes y cotizaciones EIA | Datos públicos revisables, sin inferir telemetría ni ingresos |
| Extracción | Python, contratos y snapshots de CSV/HTML | CSV oficial mostró más cobertura que DataStore; controlar rectificativas y cambios de esquema |
| Raw | BigQuery candidato aislado, partición por ingesta y clustering | Fidelidad al source y separación de permisos; carga atómica por tabla |
| Staging | Tipos, claves, nombres y filtro VM no convencional | Resolver formato de origen antes de reglas de negocio |
| Intermediate | Clave pozo × mes y días calendario | Una sola definición evita filtros/conversiones distintos entre marts |
| Marts | Grano pozo × mes, dimensiones y agregados | Reglas auditables de pozos únicos, tasas, comparaciones exactas y YTD |
| Precios | Brent/Henry Hub en raw y dbt de valorización | Cotizaciones cambiantes no se mantienen como seeds; seeds para catálogos estables |
| Export | fct_dashboard_month + cotizaciones de la misma carga | Evitar aritmética monetaria duplicada y ligar fuente, build y consumidor |
| UI | Next.js 16, React 19, TypeScript 7, Recharts 3 | Export estático y componentes/filtros comunes sin secretos cloud |
| Gates | Python, dbt, contrato Node y tests/build frontend | Una falla bloquea el siguiente paso; aprobación/publish separado |

Raw se particiona por `_sdc_batched_at`, no por el mes de producción: particionar marts históricos por `periodo` en el sandbox de 60 días podía eliminar datos recién construidos. Los marts usan clustering. Las métricas de performance registran bytes, tiempos y slot-ms reales; una vista CREATE con cero bytes no garantiza costo nulo de sus consultas. [Calidad y rendimiento](../transform/docs/quality-and-performance.md).

Staging puede alimentar directamente un mart: intermediate se usa cuando hay transformación reutilizable que separar. Aquí `stg_monthly_reference_price` valida referencias a grano producto × mes; `fct_reference_valuation_month` las cruza con producción y calcula valores a grano pozo × mes. Esa dependencia directa es intencional.

## Semántica del producto

Universo: `formacion = 'vaca muerta'` y `tipo_de_recurso = 'NO CONVENCIONAL'`, no toda la Cuenca Neuquina. Corte aceptado fijo enero 2023–agosto 2026; septiembre parcial queda fuera. Petróleo m³ × 6,28981077 → bbl; gas miles de m³ → MMm³. Tasa = volumen / días calendario.

Pozos productivos = IDs únicos con volumen positivo del fluido en el mes; los conteos petróleo/gas no se suman. Cambio neto es diferencia de conteos, no altas/bajas. Promedio diario por pozo no mide días efectivos, declinación de pozos comparables o eficiencia. No se infiere relación operador–área contemporánea desde agregados marginales; completaciones están fuera de esta entrega.

USD es estimación de referencia calculada por dbt: Brent mensual USD/bbl para petróleo; Henry Hub mensual USD/MMBtu para gas. Gas usa escenario EIA de 1.036 BTU/pie³ (0,03658599472346218 MMBtu/m³), no calorificidad medida de Vaca Muerta. No son ingresos, márgenes o precios realizados. Faltantes → NULL, sin relleno; base cero → porcentaje NULL; YTD sólo con calendario completo.

El mart persiste fluido × dimensión × ID × mes. Los ceros explícitos de entidades ausentes pertenecen a meses de cuenca aceptados; huecos fuera de cobertura siguen sin dato. “Áreas reportadas” cuenta registros actuales, no todo el catálogo histórico. PCN/PLU → Pluspetrol es el único agrupamiento comercial explícito; se conserva procedencia legal y no se reatribuye historia de vendedores adquiridos.

## Contrato frontend y seguridad

`release.json`, `manifest.json`, `prices.json` y `valuation-manifest.json` forman un bundle con SHA-256. `check_snapshot.mjs` utiliza los contratos del consumidor antes de que CI lo copie a su checkout temporal. `publication_approved=false`; sin aprobación independiente válida la app muestra Preliminar.

KPIs, cards, barras y filtros compartidos mantienen identidad visual: petróleo azul, gas violeta, dinero ámbar, variación verde/rojo. ES/EN, tema y contexto de producto/período/modo/comparación se conservan al navegar y recargar; detalles tienen deep links. Resumen conserva la base aprobada.

WIF/ADC sólo en el entorno, sin claves en Git ni cliente. SA de extracción escribe raw candidato; SA dbt lee raw y construye staging/intermediate/marts candidatos. Se mantienen restricciones de repo, main, workflow y ambientes. CI conserva sólo JSON reducidos, sin raw, perfiles, logs de conexiones, manifest dbt completo ni builds. No hay push, deploy o cambios IAM en el pipeline.

## Frecuencia, freshness y aceptación

La frecuencia de datos es mensual. Cron preparado día 5 a las 03:00 Argentina; `DATA_PIPELINE_ENABLED=false`. No se asume que la fuente publique ese día ni que el mayor mes disponible sea completo.

Los gates distinguen mes de negocio, recuperación real, ingesta y generación del snapshot. Frescura operativa máxima siete días; warning dbt a cinco días también detiene el CLI. No se rejuvenecen fuentes retenidas. Recuperación reciente no equivale a frescura económica ni cobertura: ambas se verifican aparte.

Cargas aisladas atómicas por tabla, no transacción conjunta producción/precios. El bundle se escribe en staging temporal y se mueve completo; un fallo no modifica el snapshot del repo. [Recorrido ejecutable](../pipeline/CLI.md) y [evidencia de integración](evidence/orchestration-export/README.md).

El recorrido real de GitHub/WIF está [validado](evidence/github-actions/README.md). Antes de operar públicamente faltan promoción y activación autorizadas, responsables de atención a fallos y decisión de hosting. El código y la validación local no sustituyen esos pasos. No se habilitó facturación, cron o despliegue.

La validación manual del workflow de datos está permitida únicamente en `main`, independientemente del opt-in del calendario. `DATA_PIPELINE_ENABLED=false` mantiene el cron desactivado; `workflow_dispatch` ejecuta una corrida puntual con los mismos permisos y gates.

El [monitor](../pipeline/MONITOR.md) observa producción/precios sin warehouse ni WIF. Separa estado observado de datos aceptados, conserva fingerprints agregados y avisa mediante Issues deduplicadas. Cadencia diaria, lectura histórica completa semanal y al finalizar ingesta. Señales de cobertura/estabilidad habilitan revisión; no prueban cierre oficial ni publican snapshots.

La ingesta histórica usa CSV → Parquet tipado; la entrega frontend mantiene el JSON canónico y genera overview/detalles gzip vinculados al manifiesto. Staging candidato es tabla para reutilizar deduplicación y evitar escaneos repetidos de raw. Ver [contrato de rendimiento](../specs/021-performance-optimization.md).
