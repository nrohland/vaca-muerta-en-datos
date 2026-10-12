# Revisión independiente de Analytics Engineering

Auditoría de código y artefactos locales realizada el 11 de octubre de 2026. Se inspeccionaron la integración y los ámbitos aislados Operadores, Áreas y Actividad. Sin consultas al warehouse, extracción nueva, promoción o publicación externa.

## Resultado

Los nuevos cálculos preservan el grano mes × fluido y entidad × mes × fluido; las comparaciones usan meses calendario exactos, no la observación más cercana. Gas permanece físico sin referencia monetaria inventada. La producción acumulada suma enero–mes seleccionado y exige todos los meses/precios. El promedio por pozo usa volumen mensual / días calendario / pozos únicos positivos; no se presenta como eficiencia individual ni tasa por tiempo efectivo. Actividad muestra variación neta de conteos, sin inferir altas, cierres o reactivaciones. Áreas declara que no existe relación operador–área validada en el release y no la inventa.

Conciliación independiente, fuera de los tests de los autores, sobre `release.json`: 44 meses, 88 agregados y 8.936 filas de entidades. Cada ranking completo de operadores y áreas concilia con el total y las participaciones mantienen el denominador del universo. Mayor error absoluto de suma: 7,45 × 10⁻⁸ bbl, consistente con coma flotante. Los conteos productivos de entidades también suman exactamente el conteo total en todos los períodos de este artefacto.

Agosto de 2026: 25 operadores y 87 áreas por fluido. Petróleo: 20.763.871,222585 bbl y 2.678 pozos; gas: 2.958,950899 MMm³ y 2.884 pozos. Acumulado enero–agosto: petróleo 151.138.512,086228 bbl (+33,217594% contra enero–agosto de 2025), gas 21.352,520825 MMm³ (+11,877662%). No se suman pozos entre fluidos.

## Hallazgo accionable

El filtro de áreas en crecimiento usa `pct > 0`. Excluye áreas con base observada cero y delta positivo, aunque el filtro equivalente de operadores usa correctamente delta. Ejemplo real: gas, AGCA / AGUADA DE CASTRO, diciembre de 2025 = 0; enero de 2026 = 10,444175438 MMm³. La variación absoluta es positiva; el porcentaje carece de base válida. Resuelto por el integrador: filtro por delta, porcentaje nulo conservado y test de regresión AGCA incorporado. Verificación independiente: los 5 tests integrados de Áreas pasan.

## Pruebas ejecutadas

26 tests focalizados pasan: operadores 7, áreas 4, actividad 4, producción 5 y métricas comunes 6. Cubren conciliación de rankings, precios propios de cada mes, bases ausentes/cero, huecos calendario, años bisiestos, unidades de gas y exportación. Estas pruebas no equivalen a ejecutar dbt ni a revalidar los archivos oficiales completos. La definición de pozos únicos se apoya además en el contrato/marts y en la evidencia previa retenida; los nuevos agregados no incluyen IDs de pozo para deduplicarlos otra vez en cliente.

## Pipeline y freshness verificados en el repositorio

La única extracción programada en los workflows locales es `extract-cap4.yml`: día 5 de cada mes a las 06:00 UTC (03:00 Argentina). El schedule carga el entorno dev, hace reemisión completa, conserva el recurso anual por defecto de 2025 y está condicionado a `ALLOW_FULL_YEAR_LOAD=true`. Producción requiere dispatch explícito con entorno prod/reemisión. No se inspeccionaron ejecuciones de GitHub ni variables/secrets: no puede afirmarse que ese cron esté operativo.

`dbt-transform.yml` sólo ejecuta deps/parse en PR/push; no corre dbt build ni encadena extracción → transformación → exportación. No se encontró freshness de dbt (`loaded_at_field` y umbrales warn/error) en la declaración local de sources. Hay timestamps y trazabilidad, pero no un SLA automatizado de frescura ni alertas demostrados por este código.

El manifiesto del candidato actual registra extracción oficial CSV 2026 el 9 de octubre, ingesta 19:14 UTC y generación 19:18 UTC. Acepta agosto de 2026; septiembre está retenido pero excluido por parcialidad. La evidencia previa documenta retraso de DataStore respecto del CSV oficial, por lo que el cron DataStore antiguo no garantiza mantener este candidato al día. Estado de publicación: pendiente, sin fecha inventada. Precios Brent mensuales EIA ligados por hashes; gas indisponible.

Necesidades futuras para cerrar la operación: selección explícita del recurso anual vigente, extracción idempotente con control de revisiones, gate de completitud, ejecución dbt build/tests después de la extracción, generación/verificación de release y precios, política freshness por etapa y alertas. Mantener aprobación independiente para promoción/publicación. Esta revisión no habilita ni altera esos procesos.

## Auditoría de cambio de marca y nombres técnicos

Cambio de producto a **Vaca Muerta en Datos**, modelo dbt a `fct_production_rate` y notebooks a `production_basin.ipynb` / `production_spike.ipynb`. Los nombres de modelo y unit tests en YAML concuerdan y la macro/factor de conversión se mantienen. El exportador Python tiene sintaxis válida, pero ahora apunta a la nueva relación física.

La auditoría detectó y el integrador corrigió dos regresiones de reemplazo literal: alias SQL con espacios y variable Python con espacios. Verificación independiente final: alias SQL `production` válido; 7 celdas Python de `production_spike.ipynb` y 8 de `production_basin.ipynb` pasan `ast.parse`; outputs y execution counts anteriores están vacíos. Todas las referencias SQL literales apuntan a modelos o seeds presentes. Sin errores pendientes de este rename en las comprobaciones estáticas realizadas. El intento del integrador de importar el runtime dbt superó 20 segundos y se detuvo por timeout: no se declara dbt deps/parse/build ejecutado ni validación en warehouse. La validación estática no sustituye ejecución dbt o sintaxis SQL en BigQuery.

La nueva tabla no está desplegada por renombrar el archivo: requiere un dbt build autorizado y validado en el warehouse. La relación anterior no desaparece automáticamente; cualquier retiro o compatibilidad necesita una migración controlada. No se ejecutó acceso al warehouse en esta auditoría. El modelo renombrado preserva el comportamiento legado de última observación raw, petróleo, y no reemplaza los marts de publicación con gate de meses aceptados; con septiembre parcial raw no debe alimentar la publicación de agosto.
