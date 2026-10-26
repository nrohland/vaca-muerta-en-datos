# Meltano: tap-cap4 → target-bigquery

Meltano configura plugins Singer reales. `tap-cap4` usa singer-sdk y emite SCHEMA/RECORD/STATE; `target-bigquery` usa el código de [Blueprint](https://github.com/blueprint-data/target-bigquery/tree/caad808faf94102067a1da42bcfced26845b5b42), fijado en `pyproject.toml`. El ejecutable `target-bigquery-sandbox` agrega gates al target y conserva su worker batch.

## Instalación y prueba sin cloud

Desde la raíz, con Python 3.12:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r extraction/requirements-meltano.txt
python -m unittest discover -s extraction/singer/tests
meltano install extractor tap-cap4
meltano install loader target-bigquery
export VM_RUN_ID=offline_check
meltano invoke tap-cap4 --discover
meltano invoke target-bigquery --about
```

Los tests simulan IO de fuente y Google Cloud. Ejecutan el protocolo SDK y el worker batch real de Blueprint. Discovery/about no descargan fuentes ni cargan BigQuery. No crear `.env`: configuración no secreta en `meltano.yml`; credenciales efímeras ADC/WIF sólo en el runner.

## Corrida real: exclusivamente en runner remoto habilitado

**Esta ruta aún no está programada ni habilitada.** Requiere acceso remoto comprobado a los CSV oficiales, ADC/WIF existente y permisos de metadatos para verificar facturación deshabilitada. No instala cron, launchd ni servicios en la Mac.

El comando de una corrida autorizada sería:

```sh
export VM_RUN_ID="remote_$(date -u +%Y%m%d_%H%M%S)_${GITHUB_RUN_ID}_${GITHUB_RUN_ATTEMPT}"
meltano run candidate-history
# El job ejecuta: tap-cap4 target-bigquery
```

El ID acepta letras minúsculas, dígitos y underscores, empieza con letra y tiene hasta 48 caracteres. Siempre usar uno nuevo; no reanudar corridas fallidas con el mismo ID. El tap hace FULL_TABLE porque la fuente puede rectificar meses viejos.

Destino directo: `vaca-muerta-pulse.raw_cap4_candidate_dev.produccion_pozo_mes_singer_<run_id>`. Se crea exclusivamente una tabla nueva, sin particionar, con expiración de un día. No hay bucket, streaming, Storage Write API, DML, vista ni reemplazo del raw vigente. Si el dataset falta, falla. Los límites gratuitos del Sandbox pueden detener una carga; la facturación debe permanecer deshabilitada durante toda la operación. El preflight verifica el estado observado, no bloquea cambios de billing hechos por otra identidad.

Los CSV temporales y recibos quedan en `.local/singer/<run_id>/`, fuera de Git. Tap verifica contratos, hashes originales, frescura y anclajes existentes antes de certificar un bundle. El target conserva los timestamps originales, espera todos los load jobs, concilia hash/número de registros y filas reales de BigQuery; sólo entonces escribe `target-complete.json` y confirma STATE. Un EOF parcial, duplicación por reintento o worker fallido no produce certificación. Una carga parcial puede existir en la tabla aislada hasta expirar.

## Alcance y límites

- Cobertura/corte aceptado: enero 2023–agosto 2026; no se actualiza por detectar un mes mayor.
- Es ingesta candidata de producción. Precios EIA, promoción de tabla canónica, dbt y export siguen en el CLI histórico; este job no los ejecuta ni certifica.
- La indisponibilidad TCP del portal oficial sigue sin resolver. Cambiar tap/target no cambia la conectividad del runner.
- Los workflows de datos continúan pausados. CI sólo usa fixtures/snapshots y nunca depende de Energía ni de credenciales cloud.
- No se habilita facturación, se modifica IAM ni se aplica Terraform en esta entrega.
