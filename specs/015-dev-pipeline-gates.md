# Gates del pipeline candidato de desarrollo

Estado: implementados, con cargas reales de producción/Brent/Henry Hub y fase de transformación validada en BigQuery aislado. Un resultado técnico pass nunca aprueba publicación, cambia el corte de la UI ni aprueba su publicación.

## Contrato activo de fuente

`pipeline/run_candidate.py` usa el mismo `StageRunner` localmente y en GitHub. `extract` ejecuta preparación CSV, carga de producción, preparación/carga Brent, gate raw y vínculo de linaje. `transform` valida los JSON de extracción, revalida raw/linaje y ejecuta dbt parse/compile/build. No construye completaciones ni exporta el dashboard. La ruta histórica Meltano/CKAN conserva helpers de preflight, pero no es la fuente activa de este CLI.

Recurso estándar CapIV 2026 `fb7a47a0-cba9-4667-a004-6f6c1c346c23`; corte fijo agosto 2026. CSV descargado/revisado: 663.748 filas, SHA-256 `719a21cae8209d87f4c9a785c478233bdfbdba6a5f4ff3653bce9403e6ebe1fb`. Dieciséis anchors enero–agosto × fluido concilian conteos y volúmenes VM con el snapshot independientemente revisado. Agosto raw 79.576 filas y VM 3.404. Septiembre raw 4.181 y VM 26: parcial, excluido del candidato. No inferir completitud desde conteo exacto, fecha reciente o máximo período.

Una anomalía petrolera microscópica fuera de VM, dentro de `[-1e-12, 0)`, se conserva intacta y se advierte; no se reemplaza por cero. Cualquier negativo en VM no convencional, negativo mayor, NULL, NaN o Inf falla. El umbral es una excepción acotada de calidad raw, no una regla de valorización del producto.

## Antes de dbt

Evidencia `official_csv_bytes`: recurso/año, hash real de bytes, extracción UTC real, counts anual/mensual, meses técnicamente aceptados y revisión de anchors. Manifest liga schema, digest CSV/NDJSON y tiempos de descarga/normalización; recibo liga job ID, destino, filas y digest. No rejuvenecer un archivo retenido usando una fecha nueva de procesamiento.

`source_csv_pipeline.py load` sólo escribe producción candidata fija con schema explícito y `WRITE_TRUNCATE` atómico. El raw retiene todas las filas del recurso anual, incluido septiembre, con `_source_sha256` por fila y timestamps de ingesta. No recrea el raw histórico multianual. Precios se cargan separadamente en `monthly_reference_price`; no hay transacción atómica de ambas tablas juntas.

`check_raw_snapshot.py` consulta la tabla entera, no sólo año/mes seleccionados. Exige total/year counts exactos, cero años ajenos o inválidos, mes requerido con cobertura revisada, claves no nulas, unicidad pozo/año/mes, períodos válidos/no futuros, volúmenes dentro de la política y timestamps presentes. MIN y MAX de ingesta deben quedar entre extracción y hora de validación; extracción y todas las filas tienen antigüedad máxima siete días. Un append de snapshots duplicados no cumple el contrato.

`verify_loaded_lineage.py` compara SHA declarado por cada fila raw con evidencia, y filas de referencia con snapshot/hash/cutoff/benchmark/moneda/unidad esperados. Exige cantidad total esperada y exactamente un precio del corte. Repetir raw y linaje después de descargar evidencia del job de extracción evita aceptar un candidato reemplazado por otra ejecución. No equivale a comparar cada valor de warehouse con los bytes CSV ni a autenticación criptográfica de HTTP.

Identificadores fijos/validados, SQL parametrizado, query cache deshabilitada y `maximum_bytes_billed=1 GiB` obligatorio. Dry-run sólo estima y no concede pass. Download ≤1 GiB y filas ≤2 millones son límites separados, no estimación de costo total. El portal oficial redirige CSV/API a HTTP público; sólo host/ruta/recurso exactos, sin credenciales ni cookies y sin redirects a destinos arbitrarios.

## Precios y transformación

Descarga fresca EIA mensual → parser revisado → NDJSON/manifest con respuesta SHA, filas SHA, retrieval real, fecha de publicación, benchmark USD/bbl y corte → loader candidato → dbt. Las referencias cargadas contienen 472 meses Brent (agosto 91,08 USD/bbl) y 356 Henry Hub (agosto 2,78 USD/MMBtu), hasta agosto de 2026, con metadatos propios por producto. No seeds permanentes de cotizaciones dinámicas ni live fetch del browser.

Modelos de precios sólo habilitados con target `candidate` y `enable_candidate_pricing=true`. `candidate_period=2026-08-01` restringe producción/marts al mes aceptado, aunque raw contenga septiembre parcial. Selección incluye padres de company/area/headline/valorización y dimensiones company/area. Sin dimensiones, tests de relaciones fallan; no aceptar un subconjunto verde que omita dependencias necesarias.

Gates de precios: unidad/currency/benchmark válidos, precio finito >0, hash y snapshot coherentes, fechas/corte, unicidad de producto × mes y presencia del precio requerido. Valorización usa mismo mes, convierte petróleo m³→bbl una vez y conserva NULL ante precio/volumen inválidos. Agregados requieren todas las filas disponibles. MoM/YoY usan joins calendario; base cero → porcentaje NULL. YTD exige enero–mes actual completos; un candidato sólo agosto no inventa YTD enero–agosto.

Unit tests prueban missing/invalid price, volumen negativo/cero, huecos de calendario, YTD incompleto y base cero. Tests SQL concilian operador/área/cuenca y coherencia disponibilidad/NULL. Gas usa Henry Hub y el escenario energético EIA versionado explícitamente en spec 017; no usa PPP Neuquina, ni forward fill, ni una calorificidad argentina supuestamente medida.


Cada etapa debe emitir gate nuevo `status=pass`, `publication_approved=false`, perteneciente al run. Fallo de subprocess o gate corta la cadena. Un build con resultados error/skip/warn no cumple aceptación. GitHub preserva sólo JSON reducido siete días; `dbt-summary.json` contiene ID/status/duración, no profiles, raw, logs completos, manifest completo ni credenciales.

## Publicación y lo pendiente

La autenticación WIF está configurada por etapa/dataset sin claves nuevas; `DATA_PIPELINE_ENABLED=false` y prueba desde runner real pendiente. Schedule preparado día 5 a las 03:00 Argentina, sin merge ni activación. El código candidato no exporta ni promueve.

El frontend conserva snapshot anterior multianual y valorización TypeScript. Los modelos originales historia × fluido/entidad, grouping comercial, política de meses aceptados y exportadores requieren integración/conciliación. `check_candidate.py` conserva gates de hash, cobertura, rankings completos, cronología y NULL, pero un build del candidato agosto no demuestra reconstrucción equivalente del dashboard. Completaciones y relación operador–área requieren contratos independientes. Cierre integrado queda para después de la validación real completa.

## Resultado real verificado

El CLI compartido `all` pasó 12 etapas reales, desde descarga hasta build. dbt completó 83 nodos: 8 tablas, 3 vistas, 66 tests de datos, 6 unit tests; cero errores/warnings/skips. Las conciliaciones pasaron y 75 pruebas offline están aprobadas. Modelos/macros/tests ejecutados tienen paridad con el árbol integrado. Preparación, carga y transformación se repitieron como una sola ejecución completa. La autenticación desde GitHub sigue pendiente. Los gates endurecidos de linaje y artefactos se repitieron sobre el candidato real y pasaron; no reemplazan la evidencia fechada del build. Ver [orquestación](../docs/evidence/orchestration/README.md).

## Decisión posterior: Henry Hub

La autorización de referencia internacional reemplaza los requisitos anteriores de gas PPP/NULL. [Spec vigente de gas](017-international-gas-reference.md): Henry Hub EIA mensual, manifest v2 y escenario energético fijo EIA explícito. La ingesta actual carga 828 precios (472 Brent, 356 HH); controles de freshness/hash/unidad/basis separados por producto. Unicidad producto × mes y precio del corte para ambos. Gas válido tiene `reference_scenario`, no calorificidad medida de Vaca Muerta. Nueva validación completa de 88 nodos en [evidencia](../docs/evidence/gas-reference/README.md). Los resultados anteriores se conservan como historial verificable.
