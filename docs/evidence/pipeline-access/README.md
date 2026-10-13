# Acceso federado candidato — 12 de octubre de 2026

El usuario autorizó el plan de acceso. Se aplicó y verificó su configuración
en Google Cloud y las variables públicas de GitHub; no se ejecutó el workflow.

- Pool `vm-data-dev`, provider `github-data-pipeline`, ambos activos.
- Confianza restringida a repository ID `1364547377`, owner ID `55503418`, rama
  `main`, archivo `.github/workflows/data-pipeline.yml`, eventos schedule/manual
  y ambientes `data-dev-extract` / `data-dev-dbt`.
- `vm-pulse-ci-extract-dev`: jobUser en proyecto; WRITER en raw candidato.
- `vm-pulse-ci-dbt-dev`: jobUser en proyecto; READER en raw candidato y WRITER
  en stg/int/marts candidatos. Todos los datasets están en US.
- Cada cuenta sólo acepta el principal federado de su etapa. Verificados los
  bindings exactos, sin bindings cruzados ni roles dataEditor a nivel proyecto
  para estas cuentas nuevas.
- Cero claves administradas por usuario en las dos cuentas nuevas. No se creó
  ningún JSON de clave ni se añadió un secreto de GitHub. Las credenciales de
  ejecución serán temporales por WIF.
- Variables GCP_WIF_PROVIDER, GCP_CI_EXTRACT_SA y GCP_CI_DBT_SA configuradas;
  DATA_PIPELINE_ENABLED=`false` verificado.
- No se alteraron roles de cuentas históricas, facturación, main, snapshots ni
  aplicación publicada. No se probó todavía un token real emitido por el runner.

Datasets nuevos: raw_cap4_candidate_dev, stg_cap4_candidate_dev,
int_cap4_candidate_dev y marts_cap4_candidate_dev. Vacíos al provisionarse;
retención temporal por defecto de 60 días.

El script `configure_pipeline_identity.py --apply` es de provisión inicial y
rechaza recursos existentes. No repetirlo para modificar permisos: inspeccionar
la configuración y preparar un cambio revisable.

## Tamaño real del raw histórico

`raw_cap4_dev.produccion_pozo_mes`: 3.511.366 registros; 1.483.839.845 bytes
lógicos y 59.156.402 bytes físicos actuales (aprox. 1,48 GB y 59,2 MB decimales).
Es el raw previo al recorte Vaca Muerta; no representa 3,5 millones de pozos.
Conteos por año: 2023=974.971; 2024=983.551; 2025=991.844; 2026=561.000.
No se atribuye cobertura anual completa a 2026 por este conteo.

Son medidas de esa tabla, no del proyecto completo ni del tamaño de una consulta.
La consulta de conteos fue sólo lectura y tuvo presupuesto máximo de 1 GiB.
