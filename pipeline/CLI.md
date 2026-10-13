# CLI compartido del candidato

`run_candidate.py` usa el mismo `StageRunner` en ejecución local y GitHub. El contrato actual está restringido al recurso estándar 2026 y corte agosto de 2026; no se presenta como selección automática del último mes.

## Extracción

```bash
python pipeline/run_candidate.py extract --run-dir /tmp/extract-evidence
```

Requiere ADC con permisos de carga sólo al dataset candidato. Ejecuta descarga CSV oficial, validación contra el snapshot revisado, normalización, carga atómica, descargas frescas EIA de Brent y Henry Hub, carga aislada, gate raw y verificación de linaje contra las dos tablas cargadas. No cambia IAM ni envía secretos al portal de datos. CSV/NDJSON/HTML permanecen en scratch temporal; sólo los JSON reducidos son evidencia transferible entre jobs.

El directorio de ejecución debe ser nuevo. Una etapa fallida corta el flujo y nunca permite transformar/publicar el candidato. No hay reintento automático de cargas. La preparación y carga de precios es una etapa real: no se etiqueta como nueva extracción un archivo histórico retenido.

## Transformación

```bash
python pipeline/run_candidate.py transform \
  --extract-artifact /tmp/extract-evidence \
  --run-dir /tmp/transform-evidence \
  --dbt-bin /ruta/runtime/bin/dbt
```

Consume exclusivamente estos JSON:

- `source-evidence.json`: recurso, digest CSV, counts, fechas y períodos técnicamente revisados.
- `source-manifest.json`: esquema y revisión de cobertura/concilación.
- `source-load.json`: job real, destino, filas y digest vinculado.
- `price-manifest.json`: fuente/moneda/unidad, hash, retrieval real, corte y gas de referencia habilitado con basis de escenario explícito.
- `price-load.json`: job real y número de filas cargadas.

Revalida identidad/corte/destinos/freshness, ejecuta nuevamente el gate raw y la verificación de SHA/corte/unidades de las dos tablas sobre BigQuery y genera un profile candidato ADC sin secretos. Luego ejecuta dbt parse, compile y build con `candidate_period=2026-08-01`, `enable_candidate_pricing=true`, seis selectors de producción/precios/dimensiones y presupuesto de 1 GiB por consulta. Selección actual:

```text
+fct_company_month +fct_area_month +fct_production_rate
+fct_reference_valuation_entity_month +dim_company +dim_area
```

Dimensiones se incluyen expresamente porque los tests de relaciones las necesitan. Resultados skipped/error/warn no satisfacen el gate final.

`--dbt-project-dir` permite usar una copia revisada del mismo proyecto para evitar dependencias locales dañadas; `--python` selecciona un runtime de Python instalado. Ambos son rutas de ejecutables/proyecto, nunca comandos shell interpolados. El modo `all` encadena ambas fases con una identidad que ya tenga los permisos necesarios; GitHub debe usar extract/transform separados y sus identidades específicas.

## Evidencia y límites

Upload de GitHub: únicamente `run-dir/*.json`. No subir CSV, NDJSON, HTML, logs dbt, perfiles, manifests completos de dbt ni run_results sin sanitizar. `dbt-summary.json` contiene sólo ID de nodo, status y duración. El workflow debe seguir desactivado hasta aceptación independiente de la configuración y validación desde el runner.

`run.json` registra etapas, tiempos y fallos; cada gate debe ser nuevo, pertenecer al directorio de ese run, devolver `status=pass` y `publication_approved=false`. Se conservan las limitaciones de fuente HTTP y de la conciliación raw: counts/timestamps y el SHA declarado por fila no equivalen a comparar cada valor de warehouse con los bytes CSV. El portal redirige a HTTP público; el helper restringe host/ruta/recurso exactos y no envía credenciales. Cualquier negativo del universo VM falla; sólo redondeos fuera de VM en `[-1e-12, 0)` se preservan como advertencia. No hay exportación del dashboard ni promoción/publicación en este CLI.

Once tests del CLI verifican: transformación sin cargar, extracción sin dbt, hash/destino/referencia gas indebidos rechazados, precio antiguo no rejuvenecido por raw reciente, fallo de gate corta antes de dbt, profile seguro con presupuesto y rechazo de resultados dbt skipped.

## Fuente y estado comprobado el 12 de octubre de 2026

CSV estándar 2026: **663.748 filas**, SHA-256 `719a21cae8209d87f4c9a785c478233bdfbdba6a5f4ff3653bce9403e6ebe1fb`, cargado realmente en raw candidato. Dieciséis anchors enero–agosto × petróleo/gas concilian contra el snapshot revisado. Septiembre permanece parcial y excluido. Ver [evidencia de la fuente](../docs/evidence/source-candidate/README.md).

Las descargas oficiales cargaron **828 meses-producto: 472 Brent y 356 Henry Hub**, hasta agosto de 2026. Precios de agosto: **91,08 USD/bbl** y **2,78 USD/MMBtu**. Gas USD usa la equivalencia energética del escenario EIA versionado y explícito, no calorificidad medida argentina. Ambos marts representan valor estimado de referencia, no ingresos realizados. La investigación PPP Neuquina se conserva como alternativa histórica, fuera del benchmark activo.


Las cargas son atómicas por tabla candidata (`WRITE_TRUNCATE`), pero no una transacción conjunta entre precio y producción. Los errores posteriores impiden aceptar el run, sin modificar el snapshot UI. El recorrido `all` completo pasó 12 etapas con descarga, carga y BigQuery reales y dbt completó 83 nodos (8 tablas, 3 vistas, 66 tests de datos y 6 unit tests), sin errores, warnings ni skips. Conciliaciones y 75 pruebas offline pasan. Preparación/carga real de producción y precio se ejecutaron junto con dbt en una sola corrida aprobada; queda comprobar WIF desde GitHub; los gates de lectura endurecidos ya fueron repetidos y aprobados. Ver [evidencia de orquestación](../docs/evidence/orchestration/README.md).

WIF está configurado y verificado con identidades separadas; no hay claves nuevas. `DATA_PIPELINE_ENABLED=false`, ejecución en GitHub pendiente. Cadencia preparada día 5 a las 03:00 Argentina después de merge/activación aprobados; no se ejecuta hoy como cron operativo.

Este candidato produce agosto únicamente. El frontend continúa con el snapshot multianual de revisión anterior y cálculo monetario TypeScript. Exportar historia completa, migrar su consumidor y cerrar QA son tareas del cierre integrado, fuera del CLI actual.

## Actualización autorizada de gas

El manifest de precios activo es v2: `products.oil` y `products.gas` contienen URLs, unidades, SHA-256, snapshot, fecha de publicación, recuperación y conteos propios. El timestamp combinado es la recuperación más antigua; ambos productos deben tener el precio del corte. Recibo: hashes por producto y digest conjunto de filas. Unicidad producto × mes, nunca mes solamente. Pipeline y gates requieren ambos productos, y rechazan gas sin basis `EIA_US_AVERAGE_1036_BTU_PER_CUBIC_FOOT_SCENARIO_V1`.

El 12 de octubre se ejecutaron nuevamente extracción y transformación con ambos benchmarks. Gas USD usa un escenario energético de referencia documentado; no un poder calorífico argentino medido. [Spec 017](../specs/017-international-gas-reference.md) y [evidencia de gas](../docs/evidence/gas-reference/README.md). La evidencia de 83 nodos del apartado anterior pertenece a la corrida previa; la nueva completa 88 (11 modelos, 67 tests de datos, 10 unit tests).
