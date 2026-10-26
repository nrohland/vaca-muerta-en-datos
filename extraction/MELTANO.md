# Meltano: única entrada de ingesta

Meltano configura plugins Singer reales para producción y precios. Los comandos batch de preparación/carga están retirados y ya no escriben BigQuery. `tap-cap4` usa singer-sdk y emite SCHEMA/RECORD/STATE; `target-bigquery` usa el código de [Blueprint](https://github.com/blueprint-data/target-bigquery/tree/caad808faf94102067a1da42bcfced26845b5b42), fijado en `pyproject.toml`. El ejecutable `target-bigquery-sandbox` agrega gates al target y conserva su worker batch.

## Instalación y prueba sin cloud

Desde la raíz, con Python 3.12:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r extraction/requirements-meltano.txt
python -m unittest discover -s extraction/singer/tests
meltano install extractor tap-cap4 tap-eia-prices
meltano install loader target-bigquery target-bigquery-prices
export VM_RUN_ID=offline_check
meltano invoke tap-cap4 --discover
meltano invoke tap-eia-prices --discover
meltano invoke target-bigquery --about
meltano invoke target-bigquery-prices --about
```

Los tests simulan IO de fuente y Google Cloud. Ejecutan el protocolo SDK y el worker batch real de Blueprint. Discovery/about no descargan fuentes ni cargan BigQuery. No crear `.env`: configuración no secreta en `meltano.yml`; credenciales efímeras ADC/WIF sólo en el runner.

## Corrida real: exclusivamente en runner remoto habilitado

**Esta ruta aún no está programada ni habilitada.** Requiere acceso remoto comprobado a los CSV oficiales, ADC/WIF existente y permisos de metadatos para verificar facturación deshabilitada. No instala cron, launchd ni servicios en la Mac.

El comando de una corrida autorizada sería:

```sh
export VM_RUN_ID="remote_$(date -u +%Y%m%d_%H%M%S)_${GITHUB_RUN_ID}_${GITHUB_RUN_ATTEMPT}"
meltano run candidate-history
# El job encadena:
# tap-cap4 target-bigquery
# tap-eia-prices target-bigquery-prices
python pipeline/singer_completion.py
```

El ID acepta letras minúsculas, dígitos y underscores, empieza con letra y tiene hasta 48 caracteres. Siempre usar uno nuevo; no reanudar corridas fallidas con el mismo ID. El tap hace FULL_TABLE porque la fuente puede rectificar meses viejos.

Los precios Brent/Henry Hub se validan con los parsers existentes y la cobertura completa de los meses aceptados. Su destino es `vaca-muerta-pulse.raw_cap4_candidate_dev.monthly_reference_price_singer_<run_id>`; sus recibos quedan en `.local/singer/prices/<run_id>/`. El loader de precios hereda la misma política batch/ADC sin billing.

Destino de producción: `vaca-muerta-pulse.raw_cap4_candidate_dev.produccion_pozo_mes_singer_<run_id>`. Se crea exclusivamente una tabla nueva, sin particionar, con expiración de un día. No hay bucket, streaming, Storage Write API, DML, vista ni reemplazo del raw vigente. Si el dataset falta, falla. Los límites gratuitos del Sandbox pueden detener una carga; la facturación debe permanecer deshabilitada durante toda la operación. El preflight verifica el estado observado, no bloquea cambios de billing hechos por otra identidad.

Los CSV temporales y recibos quedan en `.local/singer/<run_id>/`, fuera de Git. Tap verifica contratos, hashes originales, frescura y anclajes existentes antes de certificar un bundle. El target conserva los timestamps originales, espera todos los load jobs, concilia hash/número de registros y filas reales de BigQuery; sólo entonces escribe `target-complete.json` y confirma STATE. Un EOF parcial, duplicación por reintento o worker fallido no produce certificación. Una carga parcial puede existir en la tabla aislada hasta expirar.

## Alcance y límites

- Cobertura/corte aceptado: enero 2023–agosto 2026; no se actualiza por detectar un mes mayor.
- Producción y precios ingresan exclusivamente por Meltano. Promoción de tablas canónicas, adaptación de recibos para dbt y aceptación end-to-end siguen pendientes; no se ejecuta automáticamente dbt/export contra las nuevas tablas. El CLI downstream conserva sólo transform/export de artefactos canónicos previamente aceptados.
- La indisponibilidad TCP del portal oficial sigue sin resolver. Cambiar tap/target no cambia la conectividad del runner.
- Los workflows de datos continúan pausados. CI sólo usa fixtures/snapshots y nunca depende de Energía ni de credenciales cloud.
- No se habilita facturación, se modifica IAM ni se aplica Terraform en esta entrega.

## Activación y retiro del batch

`data-pipeline.yml` usa Meltano y no tiene cron armado. `mode=verify` sólo prueba plugins; `mode=ingest` requiere main, `DATA_PIPELINE_ENABLED=true` y `SOURCE_CONNECTIVITY_VERIFIED=true`, además del ambiente WIF existente. Antes de autenticar exige conectividad pública; el target exige billing observado deshabilitado. No se habilitaron esas variables ni se modificó IAM. El workflow permanece deshabilitado en GitHub hasta su revisión.

`pipeline/run_candidate.py prepare|load|extract|all` deja de existir como vía ejecutable. Los CLIs de `source_history_pipeline.py`, `source_csv_pipeline.py`, `prepare_reference_prices.py` y `load_reference_prices.py` rechazan ejecución. Los antiguos loaders de producción ya no contienen implementación de carga. Se conservan helpers de validación y pruebas: son dependencias del tap/monitor, no un segundo extractor operativo.

La validación remota previa de plugins no equivale a certificación productiva. Faltan fuente accesible desde el runner, revisión del trust WIF del repositorio recreado, validación de duración/renovación de credenciales para la carga completa, benchmark de volumen y contrato de promoción/transformación con pruebas reales. No habilitar ingesta por el solo hecho de que CI pase.
