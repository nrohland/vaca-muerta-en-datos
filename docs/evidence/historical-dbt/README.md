# dbt histórico y controles de calidad

Histórico candidato enero 2023–agosto 2026 verificado en BigQuery. **106 nodos distintos aprobados**: build inicial, reparación focalizada y diez controles de claves adicionales. No fue una única corrida limpia: el primer build tuvo un error SQL en ARRAY_AGG(DISTINCT STRUCT); la reparación del modelo y sus tres tests pasó. El resultado inicial se conserva. [Resumen con invocaciones y hashes](dbt-summary.json).

**Freshness: dos fuentes aprobadas.** Es recuperación/carga técnica, no aprobación de un mes económico. [Resultado](freshness.json).

**audit_helper: 112.506 filas físicas coincidentes y 24 incorporaciones explicadas** por la diferencia de clasificación del pozo 164323. Se compararon clave, año, mes y volúmenes petróleo/gas; no se afirma identidad de todos los campos. [Diff](data-diff.json).

**Arquitectura: 75 resultados aprobados y tres advertencias, cero errores**, mediante dbt_project_evaluator local en DuckDB. Son recomendaciones sobre layout y fanout, no errores de cálculo. El intento BigQuery fue bloqueado por INSERT en sandbox; no se habilitó facturación. [Hallazgos](architecture.json).

**Rendimiento medido:** tiempos de nodo, bytes y slot-ms del adaptador BigQuery. [Primera corrida](initial/performance.html), [modelo reparado](repair/performance.html), [claves dashboard](dashboard_keys/performance.html), [claves intermedio](intermediate_keys/performance.html). No hay baseline estadístico comparable.

Esta auditoría corresponde a la etapa histórica previa. Después se conectó el frontend y pasó una corrida integrada limpia: [estado actual](../orchestration-export/README.md). GitHub WIF desde runner sigue pendiente; no hubo main, activación ni despliegue.
