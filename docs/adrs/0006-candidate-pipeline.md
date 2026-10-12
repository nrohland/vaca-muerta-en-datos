# ADR 0006 — Pipeline de desarrollo aislado y autenticación federada

Estado: preparado para validación; no desplegado ni activado.

## Problema

El cron histórico recarga un recurso 2025 y sólo existe CI de parse dbt. Las
cuentas históricas de extracción y dbt tienen dataEditor a nivel proyecto, más
amplio que el contrato documentado por dataset. Vincularlas directamente a
GitHub ampliaría el acceso del workflow.

## Decisión

Preparar un workflow candidato con identidades nuevas y permisos sobre datasets
aislados. Extracción escribe únicamente `raw_cap4_candidate_dev`; transformación
lee ese raw y escribe `stg_cap4_candidate_dev`, `int_cap4_candidate_dev` y
`marts_cap4_candidate_dev`. El usuario local conserva ADC; no se exportan claves.

WIF acepta exclusivamente el repositorio y propietario por sus IDs numéricos,
la rama main, el archivo `.github/workflows/data-pipeline.yml` y eventos schedule
o workflow_dispatch. No acepta pull_request ni ramas arbitrarias. Ambientes
GitHub `data-dev-extract` / `data-dev-dbt` permite configurar aprobación antes de ejecutar.

Fuente/año/mes requerido son explícitos. La carga candidata completa reemplaza
únicamente su tabla aislada; no recorta el raw histórico actual. Conteo fuente,
cobertura y frescura se validan antes de construir marts. Un fallo detiene el
flujo y no cambia el snapshot aprobado. La concurrencia serializa todo acceso
al candidato, independientemente de rama o evento.

Cadencia preparada: día 5 a las 06:00 UTC (03:00 Argentina), desactivada mediante
`DATA_PIPELINE_ENABLED` hasta validar el contrato. Esto no demuestra que la
fuente publique ese día. El workflow conserva el recurso/año requeridos como
configuración explícita y no elige automáticamente un mes aceptado.

## Límites

Este workflow produce marts candidatos únicamente del mes requerido, a partir de un recurso anual, no un release con
historia multianual. Los modelos de publicación que originaron el snapshot UI
están en otras ramas y aún no están integrados aquí. No exporta, aprueba, hace
commit, despliega ni publica datos. Precios/valorización tampoco están migrados
a dbt. Estos límites deben resolverse antes de llamar al pipeline de publicación
completo.

Activar APIs, crear identidades/datasets y conceder WIF son cambios persistentes
de infraestructura. El plan se revisa antes de aplicarlo; no modifica roles de
las cuentas históricas ni habilita facturación.
