# Fuente candidata oficial y transporte — 12/10/2026

Se consultaron recursos estándar de [Capítulo IV](https://datos.energia.gob.ar/dataset/produccion-de-petroleo-y-gas-por-pozo), sin usar clones «con identificador» ni DDJJ abiertas/cerradas. Recursos oficiales: [2026](https://datos.energia.gob.ar/api/3/action/resource_show?id=fb7a47a0-cba9-4667-a004-6f6c1c346c23) y [2025](https://datos.energia.gob.ar/api/3/action/resource_show?id=d774b5d7-0756-48fe-88f2-8729b57b22da).

## Hallazgos reales

- CSV 2026: 663.748 filas, 215.289.138 bytes, SHA-256 `719a21cae8209d87f4c9a785c478233bdfbdba6a5f4ff3653bce9403e6ebe1fb`. La copia retenida anterior tenía 663.675 filas: la fuente es revisable.
- DataStore 2026: 561.000 filas. Aún no reproduce agosto.
- DataStore 2025: 109.000 filas al consultar hoy; no equivale a la extracción histórica de 991.844 filas. CSV anual 2025 metadata declara 315.374.928 bytes. No se descargó ni cargó ese año en esta prueba.
- Agosto 2026: 79.576 filas raw; 3.404 filas Vaca Muerta no convencional. Las 16 combinaciones enero–agosto × petróleo/gas concilian filas y volúmenes con el snapshot independientemente revisado del dashboard.
- Septiembre: 4.181 filas raw y apenas 26 filas VM; permanece excluido. No se acepta un período por ser el máximo disponible ni por tener una carga reciente.
- Una anomalía fuera de VM: petróleo `-0.000000000000000597557597885158`, pozo 135614, febrero, Cañadón Seco. Se conserva intacta y se registra como warning. El umbral técnico sólo permite `-1e-12 <= valor < 0` fuera de VM no convencional; cualquier negativo en VM, negativo de mayor magnitud, NULL, NaN o Inf falla. No se reemplaza por cero.

## Transporte y límites

El portal redirige HTTPS a HTTP para API y CSV. Reintentar la URL final con HTTPS devuelve la misma redirección. Sólo se permite el host exacto `datos.energia.gob.ar` y la ruta/ID del recurso 2026 revisado; no se envían credenciales o cookies y se bloquean redirects a otros destinos. El manifiesto registra URLs finales y esta limitación. El hash demuestra identidad de bytes retenidos, no autenticidad criptográfica del tránsito HTTP; la conciliación independiente reduce el riesgo de incoherencia, sin conceder publicación.

Descarga limitada a 1 GiB; fuente limitada a 2 millones de filas; cada request tiene timeout 30 segundos. La normalización produjo NDJSON de ~629 MiB y digest `42cd060b605f96404bec409d6f9198f6fca0d046b5493b232d67af0bcb9adc57`. Fecha de descarga y normalización son separadas: no se rejuvenece una copia histórica con una nueva fecha de procesamiento.

La carga preparada usa schema explícito, `_source_sha256` por fila, timestamps reales de extracción/ingesta y `WRITE_TRUNCATE` atómico sólo sobre `vaca-muerta-pulse.raw_cap4_candidate_dev.produccion_pozo_mes`. El histórico compartido queda fuera del permiso de escritura del helper. No hace DML, DROP, IAM, promoción ni lectura del esquema de otra tabla. La API de carga debe retornar el mismo número de filas y se registra job ID/hash/destino. Los timestamps de fecha de declaración fuente carecen de zona y no se usan para medir freshness; BigQuery interpreta TIMESTAMP sin zona en UTC, sin demostrar zona de origen.

La ejecución posterior del raw gate y dbt corresponde al coordinador. Presupuesto de consultas recomendado máximo 1 GiB por job. Este límite no se presenta como costo monetario estimado ni como cantidad de bytes facturados observada.

## Código y verificación

`source_csv_pipeline.py prepare` descarga, revisa, normaliza y genera `manifest.json` + `evidence.json`; `load` requiere ese candidato y el contrato de schema explícito, y escribe sólo el dataset candidato fijo. Usa `prepare_csv_candidate.py` existente. Catorce tests offline pasan: rutas/recurso exactos, destino y proyecto aislados, rechazo de corte no revisado, anchors ausentes, revisiones de volumen, negativos VM y no VM, warning de redondeo preservado, exclusión de septiembre, manifiesto alterado y presupuesto de filas.

Preparación real pasó sobre `/private/tmp/vm-source-2026-reviewed`. La carga no se ejecuta hasta coordinación explícita con el agente que valida dbt.
