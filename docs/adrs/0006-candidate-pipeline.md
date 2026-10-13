# ADR 0006 — Pipeline candidato aislado y autenticación federada

Estado: implementado y validado en la fase real de transformación de desarrollo. Acceso aplicado con autorización el 12 de octubre de 2026; workflow desactivado. No hay merge, activación, promoción ni despliegue.

## Problema

El cron histórico recargaba un recurso 2025 y CI sólo comprobaba parse dbt. El raw compartido contiene múltiples años y no puede recrearse para una extracción monoanual. Las identidades históricas tienen permisos más amplios que los necesarios; federarlas directamente ampliaría el acceso del workflow. DataStore consultado tampoco reproduce agosto de 2026 disponible en el CSV oficial.

## Decisión

Un [CLI compartido](../../pipeline/CLI.md) ejecuta las mismas etapas localmente y en GitHub: descarga del CSV estándar 2026 → validación técnica independiente de cobertura → normalización/carga aislada → descarga Brent y carga de referencia → raw/freshness/linaje → dbt parse/compile/build/tests. Se conserva Meltano/Singer para la ruta histórica CKAN; no es la extracción activa del CLI candidato CSV. Elegir CSV responde a cobertura comprobada, no a una sustitución de datos oficiales.

Extracción escribe sólo `raw_cap4_candidate_dev`; transformación lee ese raw y escribe `stg_cap4_candidate_dev`, `int_cap4_candidate_dev`, `marts_cap4_candidate_dev`. Cuentas separadas, WIF configurado y ninguna clave permanente generada. WIF restringe repositorio/propietario por IDs numéricos, rama main, workflow `data-pipeline.yml`, evento schedule/workflow_dispatch y ambiente de etapa `data-dev-extract`/`data-dev-dbt`. La configuración de acceso fue verificada; autenticación desde un runner real permanece pendiente.

La fuente y el corte son explícitos: recurso estándar `fb7a47a0-cba9-4667-a004-6f6c1c346c23`, año 2026, agosto aceptado. La descarga revisada tiene 663.748 filas, SHA-256 `719a21cae8209d87f4c9a785c478233bdfbdba6a5f4ff3653bce9403e6ebe1fb`; dieciséis anchors enero–agosto × petróleo/gas concilian. Septiembre parcial no se acepta aunque sea el máximo disponible.

Las cargas `WRITE_TRUNCATE` reemplazan atómicamente cada tabla candidata, sin DROP/DML ni escritura al histórico compartido. Precio y producción son tablas separadas y no se presentan como una transacción conjunta. Los manifiestos/recibos y SHA por fila vinculan destino, bytes fuente y corte; transformación revalida ese vínculo y freshness con consultas limitadas. El hash por fila es linaje declarado, no digest calculado de cada valor almacenado.

El presupuesto de consulta es 1 GiB por job; descarga máximo 1 GiB y fuente máximo dos millones de filas. Dependencias se instalan antes de autenticar. GitHub conserva sólo JSON reducido durante siete días, sin raw, perfiles, credenciales ni logs dbt completos. Resultados dbt error/skip/warn impiden aceptación del build. Una anomalía de redondeo fuera de VM en `[-1e-12, 0)` se conserva y advierte; negativos del producto siempre fallan.

Cadencia preparada: día 5 a las 06:00 UTC (**03:00 Argentina**), bloqueada por `DATA_PIPELINE_ENABLED=false`. El calendario no implica publicación de la fuente ese día. La concurrencia serializa el candidato entre eventos. El CLI no cambia IAM, no activa facturación ni aprueba publicación.

## Precios y límites

Brent es fuente dinámica raw, no seed permanente. Se descargó nuevamente la respuesta EIA y se cargaron 472 meses hasta agosto en `monthly_reference_price`; agosto 91,08 USD/bbl. dbt construye valor bruto de referencia y comparaciones calendario con NULL para ausencias/invalidaciones; no ingresos realizados. Gas PPP oficial sigue hasta mayo, 4,01 USD/MMBTU, sin cobertura agosto ni compatibilidad térmica acreditada con CapIV: gas USD permanece NULL.

El build candidato sólo incluye agosto, producción/dimensiones/precios seleccionados; completaciones necesitan su propio contrato. No genera historia multianual ni exporta el release del dashboard. El frontend continúa con el snapshot de revisión anterior y valorización TypeScript hasta el cierre integrado. Los modelos de publicación originales y exportadores requieren integración y conciliación antes de promoción.

El portal redirige recursos públicos a HTTP; host/ruta/recurso están restringidos, sin envío de cookies/credenciales. SHA demuestra identidad de bytes retenidos, no autenticidad criptográfica del tránsito. Esta limitación queda visible en el manifiesto y exige revisión antes de ampliar a publicación. Ver [evidencia de fuente](../evidence/source-candidate/README.md).

## Evidencia de ejecución

El CLI compartido `all` pasó 12 etapas con descargas, cargas y transformación reales. dbt: 83 nodos aprobados, cero errores/warnings/skips; 8 tablas, 3 vistas, 66 tests de datos y 6 unit tests. Conciliaciones reales y 75 pruebas offline aprobadas. El código de modelos/macros/tests del proyecto ejecutado se contrastó con el árbol integrado. Las descargas/cargas y el build se repitieron en una ejecución completa. WIF desde un runner GitHub aún no fue probado. Los controles endurecidos de metadatos/linaje se repitieron con BigQuery y artefactos reales, y pasaron. Ver [evidencia](../evidence/orchestration/README.md).

## Extensión autorizada: referencias internacionales

Precios candidatos ahora incluyen Brent y Henry Hub mensuales EIA con metadata y hashes propios. El manifest v2 conserva freshness independiente de cada fuente y SHA conjunto del payload. Gas se valoriza únicamente como escenario energético EIA versionado, explicitado también en UI/CSV. [Contrato](../../specs/017-international-gas-reference.md). Extracción y transformación volvieron a ejecutarse realmente; 88 nodos dbt aprobados. [Evidencia actual](../evidence/gas-reference/README.md). No altera identidades, permisos, confianza WIF, cron desactivado ni aprobación de promoción.
