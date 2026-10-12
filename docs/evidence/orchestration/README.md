# Validación real del candidato — 12 de octubre de 2026

El comando compartido `pipeline/run_candidate.py all` completó sus 12 etapas: descarga/validación/carga de CSV, descarga/preparación/carga de Brent, controles raw/linaje/artefactos y dbt parse, compile y build sobre BigQuery. [Registro de etapas](run.json). Desarrollo aislado, `publication_approved=false`.

El [resumen dbt](dbt-summary.json) contiene 83 resultados satisfactorios: 11 modelos, 66 tests de datos y 6 unit tests. No hubo errores, advertencias ni pruebas omitidas. Los SQL/YAML/macros de la copia ejecutada coinciden byte por byte con el checkout; [digests](paridad-fuentes-dbt.json). Runtime dbt Core 1.12.5 / BigQuery 1.12.1, paquetes del lock existente y presupuesto máximo 1 GiB por consulta. [75 tests locales](tests-locales.json) pasaron tras la revisión final de seguridad (31 pipeline, 32 extracción, 12 precios). Los [controles de linaje endurecidos](linaje-final.json) y la [revisión de hashes de artefactos](artefactos-final.json) también pasaron sobre el candidato real.

## Fuente y precios realmente cargados

La descarga oficial CSV 2026 fue recuperada el 12 de octubre, normalizada y cargada en una tabla candidata tipada mediante reemplazo atómico: 663.748 filas nacionales; 16 anclas de volumen/conteo de ambos fluidos enero–agosto concilian con el snapshot revisado. Septiembre parcial no se acepta. La única anomalía diminuta negativa, fuera de Vaca Muerta, se preservó y registró como warning de raw; no se redondearon volúmenes. Se cargaron 472 meses Brent EIA, agosto 91,08 USD/bbl. Las etapas de extracción/carga y transformación se repitieron en una única corrida real, de punta a punta, sin omisiones.

El raw anual alimenta marts candidatos restringidos a agosto: 3.404 registros pozo-mes de Vaca Muerta no convencional. [Conciliación de producción](conciliacion-produccion.json) y [conciliación de referencia monetaria](conciliacion-precios.json) pasaron independientemente, incluyendo suma por operador y área. Valor bruto de referencia agregado: aproximadamente USD 1.891,17 millones; no es ingreso realizado. Las pequeñas diferencias de FLOAT64 se evalúan mediante tolerancia, no igualdad decimal exacta.

Gas USD continúa NULL: PPP Neuquina/TOTAL oficial llega a mayo y no existe equivalencia energética demostrada para multiplicarlo por el volumen CapIV. No se hizo forward fill.

## Reparaciones y límites

La primera ejecución detectó dos consultas de tests incompatibles con BigQuery; después se corrigieron la forma de las filas esperadas y una expectativa FLOAT64. La corrida completa del CLI detectó además dimensiones no incluidas en sus selectors. Se añadieron `dim_company` y `dim_area` y se repitió el build completo, obteniendo los 83 resultados correctos. No se ocultaron errores ni se omitieron tests para conseguir el resultado final.

WIF y permisos por etapa están configurados sin claves de cuenta de servicio, pero el runner de GitHub no fue probado: la confianza está limitada al workflow de main y esta implementación todavía no fue mergeada. `DATA_PIPELINE_ENABLED=false`; cron mensual propuesto día 5, 03:00 Argentina. No se activó, publicó ni desplegó nada.

El CSV oficial redirige a HTTP en la misma ruta pública permitida. No se enviaron credenciales; SHA-256 vincula bytes descargados, no acredita autenticación TLS del transporte. La evidencia cargada verifica metadatos, hashes etiquetados, conteos y anclas agregadas; no compara cada campo del warehouse con cada fila del CSV.

El consumidor web conserva su snapshot anterior. Restan integración histórica de modelos/exportadores, consolidación comercial de operadores y cierre visual de las cinco pestañas con nuevas capturas. Comparaciones/YTD del candidato de un solo mes permanecen NULL cuando falta historia; no se inventó contexto temporal.
