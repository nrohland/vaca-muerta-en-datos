# Gates del pipeline dev

Implementación aislada de controles, sin ingesta ni cambios warehouse. Conserva la separación DE/extracción y AE/transformación. Un resultado técnico pass no aprueba publicación, no promueve un corte y no habilita gas USD.

## Antes de dbt

`extraction/scripts/check_raw_snapshot.py` lee únicamente `produccion_pozo_mes` del dataset explícito. Año, mes y resource ID son obligatorios. Query parametrizada; identificadores validados; caché deshabilitada; presupuesto `maximum_bytes_billed` obligatorio positivo, default 1 GiB. `--dry-run` devuelve estimación y no ejecuta el gate ni concede pass. El rol requiere lectura de tabla y creación de query jobs, no permisos de escritura. No se cambia IAM aquí.

La evidencia es un JSON revisado derivado de la descarga exacta del recurso anual:

- `resource_id`: ID CKAN que coincida con el solicitado.
- `year`: año solicitado.
- `source_sha256`: SHA-256 real de bytes CSV (`hash_scope=official_csv_bytes`) o fingerprint de metadatos/esquema/conteos CKAN (`hash_scope=ckan_metadata_counts`, nunca presentado como bytes).
- `extracted_at`: timestamp ISO con zona.
- `year_rows`: cantidad total exacta de filas del año en ese snapshot.
- `month_rows`: objeto período `YYYY-MM-01` → cantidad exacta de filas del mes.
- `coverage_status`: `reviewed_complete_snapshot`.
- `accepted_periods`: meses técnicamente revisados como completos, incluyendo el solicitado.

No se genera este archivo con valores por defecto. Contar el recurso no demuestra cierre del mes: la revisión de completitud exige evidencia independiente (declarantes/cobertura, archivo completo, comparación de snapshots). El script nunca acepta el máximo raw automáticamente. Un mes parcial falla aunque su conteo coincida exactamente con la fuente. `accepted_periods` aquí es aceptación técnica de cobertura, no aprobación de promoción por el dueño.

Checks: conteo anual y mensual exactos; al menos una fila del mes; unicidad pozo/año/mes; claves no nulas; meses válidos y no futuros; petróleo/gas finitos y no negativos; timestamps de carga presentes, no futuros, posteriores a extracción y con antigüedad máxima de 7 días para todas las filas del año. Se usa MIN además de MAX para no esconder un snapshot viejo detrás de una fila nueva. La extracción también debe estar dentro de 7 días. Esta exigencia implica reload completo del año verificado; no es compatible con append que acumule snapshots duplicados.

Limitación: la tabla raw existente no incluye hash/recurso por fila. Coincidencia de identidad en evidencia + conteos no prueba identidad byte a byte del warehouse. El orquestador debe vincular evidencia inmutable al job de carga; futura tabla de auditoría puede almacenar resource/hash/job ID sin duplicar el tap. Tampoco este gate valida el orden temporal de revisiones de declaraciones. No se descartan rectificativas sin contrato.

El gate no debe ejecutar `dbt build` completo: `fracturas_adjunto_iv` tiene una extracción separada. Ejecutar sólo modelos de producción seleccionados después de pasar este gate. Completaciones requiere su propio recurso, cobertura/freshness y revisión de join.

## Después de transformación/export candidato

`transform/scripts/check_candidate.py` es un control separado: release SHA-256 ligado a manifiesto, meses aceptados contiguos, cutoffs coherentes, ambos fluidos en cada mes, sin duplicados, volúmenes finitos/no negativos, cobertura técnica explícita, rankings completos operador/área conciliados con total y cronología extracción/ingesta/generación. No altera ficheros ni estados de aprobación. La falta de precios debe conservar nulos; no se crean precios ni se habilita USD gas.

Las advertencias 40 días / errores 70 días de extracción y lag económico 2/3 meses en este checker son propuesta de monitoreo mensual de un artefacto histórico de revisión, no reemplazan el gate post-load de 7 días. Son límites configurables en la función; no se activó freshness dbt global ni schedule. Para producción hay que acordar SLA y alertas por etapa; max batch reciente no equivale a período económico fresco.

## Modelos que faltan en la entrega auditada

La entrega contiene `fct_well_month`, `fct_company_month`, `fct_area_month`, `fct_production_rate` (headline legacy latest raw, petróleo), dims y completaciones. No contiene los modelos de publicación historia × fluido, entidad × historia × fluido, política de períodos aceptados, grouping comercial trazable y rankings/contribuciones exportados a `release.json`. Los 88 totales y 8.936 entidades del frontend provienen de ejecución anterior de ramas #25–31, no de reconstruir esta entrega legacy. No usar `fct_production_rate` para decidir corte cuando raw tiene septiembre parcial.

Por tanto dbt legacy pass no autoriza generación de un release nuevo equivalente al dashboard. Integrar los modelos de publicación originales y sus seeds/tests mediante comparación de contrato antes de exportar. Gas monetario permanece fuera hasta cierre de precio por mes y contrato térmico.

## Verificación local

18 tests offline: 10 de policy raw, 5 del preflight CKAN y 3 del candidato. Los raw cubren: happy path sin aprobación, parcial con counts exactos, diferencias de conteos, snapshot viejo oculto por max nuevo, duplicados/volúmenes/fechas/claves inválidas, load futuro/recurso distinto y timestamp sin zona. No se ejecutó BigQuery, ingesta o build dbt. La consulta debe dry-runarse contra el esquema real antes de conectar el workflow.


## Preflight CKAN anual (para workflow Meltano)

Antes de extracción: `check_ckan_snapshot.py --resource-id ID --year YEAR --month MONTH --evidence REVIEWED.json --output BEFORE.json`. El archivo de revisión debe tener hash scope CKAN y fingerprint/cuentas/mes aceptado ya revisados; no reutilizar evidencia CSV o del snapshot UI. Sin esa revisión, falla cerrado.

Después de carga: mismos argumentos agregando `--before BEFORE.json --output AFTER.json`. Exige resource total = conteo del año, campos esenciales, conteo mensual exacto, esquema y metadata sin cambios antes/después y respecto de revisión. Es observación acotada `limit=0`, no extracción de filas.

Raw: `check_raw_snapshot.py --project PROJECT --dataset raw_cap4_candidate_dev --resource-id ID --year YEAR --month MONTH --evidence REVIEWED.json --observation BEFORE.json --max-bytes BUDGET`. Usar BEFORE para cronología: AFTER se tomó después del load. Dry run sólo estima; ejecutar gate para pass real. Fresh observation supplies extraction timestamp, while reviewed evidence keeps immutable accepted coverage and source fingerprint. Cambios de metadata sin cambio de conteo también requieren revisión; opción conservadora para evitar aceptar revisiones inadvertidas.

Build seleccionado por el coordinador: `+fct_company_month +fct_area_month +fct_production_rate`, sin fracturas. Estos modelos legacy no son modelos de publicación nuevos. No activar exportación final del dashboard mientras faltan sus modelos de historia/fluido y aceptación.


## Corrección QA: toda la tabla raw

El gate ya no filtra año antes de inspeccionar: CTE `all_rows` sin WHERE incluye todas las filas. Emite `total_table_rows`, `year_rows`, `outside_year_rows` y `invalid_year_rows`. Exige tabla total igual al snapshot anual exacto y al subconjunto solicitado, cero años ajenos y cero años nulos/malformados/fraccionales/futuros. Los controles de volumen, claves, períodos, duplicados y timestamps también cubren la tabla entera. El presupuesto de escaneo sigue vigente. Tres tests de regresión prueban que counts seleccionados correctos no esconden filas ajenas, que el bucket de año inválido falla y que un total correcto no sustituye el scope anual.
