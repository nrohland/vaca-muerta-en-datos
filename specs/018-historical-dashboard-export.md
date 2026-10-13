# Export histórico candidato desde dbt

## Contrato

`candidate_start_period` y `candidate_period` delimitan un rango mensual cerrado. Si no se declara inicio, conserva el candidato de un solo mes. La carga y sus gates deben demostrar cobertura completa para cada mes: cambiar la variable no acepta ni inventa historia.

`fct_dashboard_month` persiste el grano fluido × dimensión × ID × mes. Dimensiones: cuenca, operador comercial de presentación y permiso/concesión. El grid explicita cero únicamente para entidades ausentes dentro de meses de cuenca que sí existen y han pasado cobertura. MoM/YoY unen meses calendario; una base cero produce porcentaje NULL. YTD monetario sólo existe con todos los meses enero–mes y valores válidos.

El seed `operator_groups` mantiene exclusivamente el mapping revisado PCN/PLU → PLUSPETROL desde enero 2023. No reatribuye historia de vendedores adquiridos ni infiere grupos nuevos. IDs desconocidos conservan la identidad legal y nombres declarados. Nombres actuales de dimensiones se seleccionan de forma determinística desde el último período observado; conflictos de nombre dentro de un mismo ID/mes siguen siendo un error. La procedencia legal se conserva en el export.

Volumen físico y valor de referencia proceden de dbt. Brent y Henry Hub siguen el contrato de precios y escenario energético de la spec 017. Valor ausente o inválido → NULL; no forward fill. El consumidor no multiplica volumen por precio.

## Export y aceptación técnica

`pipeline/export_dashboard.py` exporta exclusivamente desde `marts_cap4_candidate_dev.fct_dashboard_month`; el gate de linaje hace consultas agregadas read-only a raw y precios, sin exportar registros individuales. Cada consulta tiene presupuesto 1 GiB. Exige resultado dbt aprobado técnicamente, sin warnings/errors/skips, incluido el nuevo modelo. Antes de escribir, compara todos los anclajes físicos de cuenca y entidades (volumen, tasa y pozos positivos) con el snapshot de revisión y concilia sumas de entidades y valor. No copia valores monetarios del baseline.

Entrega `release.json` con métricas USD/YTD calculadas, `manifest.json` ligado por SHA-256 y recibo del job. `--manifest` aporta la plantilla del baseline. El export reconstruye su procedencia desde `--extract-artifact` (fuentes, hashes, fechas reales de ingesta y corte), exige que los hashes de entrada coincidan con `--dbt-summary` y revalida el linaje cargado. `--revision` y `--assignment-revision` contienen las correcciones históricas verificadas y ligadas al SHA del baseline y al bundle fuente; no son un permiso general para omitir diferencias. Referencias geográficas del baseline se conservan con validación de bytes/hash del índice y copia de assets cuando existen.

`status: candidate`, `publication_approved: false`. El campo heredado `acceptance_basis: approved_complete_snapshot` significa aceptación técnica del snapshot, no aprobación del propietario para promoción. No crea aprobación, no modifica main, no sube artefactos ni despliega.

## Verificación

Tests dbt nuevos: contrato de filas, cobertura de meses, conciliación física/monetaria cuenca–entidades. Tests exporter: duplicados, historia incompleta, anclajes modificados, escenario desconocido, valores no finitos, campos faltantes y diferencias de suma. Parse offline no demuestra ejecución SQL en BigQuery; build y export reales deben registrar sus propios jobs y resultados.

## Revisiones aceptadas en esta entrega

El baseline retenido excluía el pozo 164323 por clasificación convencional. La fuente oficial lo reclasifica no convencional en 24 meses de 2024–2025 sin cambiar sus volúmenes individuales. También revisa IDs de área en 96 registros mensuales de 2025 (48 grupos), sin cambiar operador ni volumen: AVI→AVN, MBE→MBE1 y LTAC→LTI/LTII. Ambas revisiones se comparan explícitamente; toda diferencia restante sigue bloqueando. Conversión de petróleo exacta del contrato: 6,28981077 bbl/m³.

El CLI histórico ejecuta dashboard-export y snapshot-check después del build aceptado. El baseline dbt actual se liga a su manifiesto y no reaplica las correcciones iniciales; las dos revisiones siguen disponibles para la migración original. El workflow valida y construye el consumidor, sin promover ni publicar. [Evidencia de integración](../docs/evidence/snapshot-integration/README.md).
