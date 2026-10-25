# Histórico oficial: extracción y candidato raw

Rango técnicamente revisado: enero de 2023 a agosto de 2026, 44 meses y 88 conciliaciones de volumen/conteo Vaca Muerta × fluido. Se usan cuatro recursos CSV anuales estándar con UUID y rutas fijas; las variantes DDJJ abiertas/cerradas no se mezclan. Septiembre de 2026 se conserva en raw si existe en la fuente, pero no entra en los períodos aceptados ni en el producto.

Se valida esquema, unicidad pozo/año/mes, claves, números finitos, metadatos estables, SHA-256 y recuperación original de cada CSV. No se renueva la fecha de extracción al normalizar un archivo retenido. El raw conserva todos los registros y valores oficiales.

Los negativos de petróleo o gas dentro de formación Vaca Muerta + recurso NO CONVENCIONAL bloquean el candidato. Negativos fuera de ese universo se preservan y registran como anomalías de fuente, sin incorporarlos a los marts del producto. Esto no declara válida la producción convencional nacional: su interpretación está fuera del alcance. Valores no finitos y claves inválidas siguen bloqueando toda carga. La política mensual anterior conserva su tolerancia restringida; la política histórica explícita es strict_vm_preserve_flag_outside_product.

La carga es atómica mediante WRITE_TRUNCATE exclusivamente en vaca-muerta-pulse.raw_cap4_candidate_dev.produccion_pozo_mes. No modifica raw_cap4_dev ni raw_cap4. Un recibo liga job, filas y hashes por año al conjunto revisado. El gate de sólo lectura compara período a período conteos, hashes declarados, cronología, negativos fuera del producto y sumas de ambos fluidos contra las fuentes revisadas. Cada consulta tiene límite de 1 GiB.

El SHA por fila declara su fuente; conteos y sumas no equivalen a comparar cada celda del warehouse con los bytes CSV. El portal oficial puede redirigir a HTTP público: el digest fija identidad de bytes, no autenticidad criptográfica del transporte.

La aprobación técnica no permite publicar, desplegar, mergear ni activar cron. dbt, export y consumo frontend son etapas posteriores con evidencias independientes.

## Discrepancia de clasificación revisada el 13 de octubre

El CSV estándar vigente clasifica el pozo 164323 como NO CONVENCIONAL en los 24 meses de 2024–2025; el raw retenido del snapshot anterior lo clasificaba CONVENCIONAL. La consulta de sólo lectura verifica igual formación, cero petróleo y exactamente el mismo gas en esos 24 registros. La diferencia de pertenencia explica todas las diferencias mensuales de conteo y gas detectadas frente al baseline. No se afirma cuándo cambió la clasificación ni que se hayan comparado todas las celdas históricas.

La política ya elegida usa el CSV oficial estándar para el candidato. Los anclajes físicos nuevos agregan exclusivamente esos 24 registros al universo; se conserva el SHA del baseline anterior y de los cuatro CSV. Cualquier diferencia adicional continúa bloqueando preparación. Evidencia en docs/evidence/historical-source/physical-anchors.json y classification-revision.json. La aplicación sigue usando su snapshot anterior hasta validación de dbt/export; esta revisión no promueve datos.

## Esquema anual

El CSV estándar de 2024 incluye una columna adicional `id` de fila, ausente en 2023, 2025 y 2026. Se conserva como entero nullable en raw; los otros años representan su ausencia con NULL. No sustituye idpozo ni se usa como clave analítica. Sólo se permite esa extensión conocida en 2024; cualquier otro campo extra o faltante bloquea. Los esquemas y anclajes de los cuatro archivos se revisan antes de producir el payload grande.
