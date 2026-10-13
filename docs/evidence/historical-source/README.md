# Histórico: fuente y raw candidato verificados

Prueba de acceso local y etapa de fuente completadas el 13 de octubre de 2026. Son 3.614.213 registros nacionales de cuatro CSV estándar; el universo analítico sigue limitado a Vaca Muerta no convencional. Se aceptan 44 meses, enero de 2023–agosto de 2026. Septiembre se conserva en raw pero se excluye del producto.

La carga atómica y la conciliación de BigQuery pasaron. Ver [resumen](summary.json), [recibo de carga](source-load.json), [conciliación](reconciliation.json), [fuentes](source-evidence.json) y [51 pruebas de extracción](extraction-tests.json). La etapa no modificó el raw compartido ni la UI. No ejecutó dbt histórico ni probó GitHub WIF; no hubo merge ni publicación.

La discrepancia CSV/raw retenido del pozo 164323 explica 24 cambios de pertenencia en 2024–2025: CONVENCIONAL frente a NO CONVENCIONAL, con los mismos volúmenes. El candidato usa la fuente CSV elegida; se preservan SHA y los anclajes anteriores. [Revisión](classification-revision.json), [anclajes físicos revisados](physical-anchors.json). No se afirma cuándo cambió la clasificación ni que se haya comparado cada celda histórica.

Se conservaron y señalaron 13 campos negativos fuera del universo del producto; no hay negativos aceptados en Vaca Muerta no convencional. El CSV de 2024 tiene un id de fila adicional: se preserva en raw y no se utiliza como clave analítica.

La consulta tiene presupuesto de 1 GiB. Conteos, sumas y hashes declarados no equivalen a comparar cada celda cargada contra bytes CSV. El portal oficial puede redirigir a HTTP público: SHA fija identidad de bytes, no autenticidad del transporte.

Siguiente etapa: dbt histórico y sus conciliaciones. Luego export, consumidor y QA. La UI continúa en el snapshot anterior validado.
