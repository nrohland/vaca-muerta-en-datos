# dbt local: Core y BigQuery

Este proyecto usa **dbt Core**, no dbt Fusion ni dbt Cloud. Ejecutar el binario
del entorno virtual evita que un `dbt` global de otra distribución tome el control.

Desde `transform/`:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp profiles.yml.example profiles.yml
.venv/bin/dbt deps --profiles-dir .
.venv/bin/dbt parse --profiles-dir . --target dev_oauth
.venv/bin/dbt debug --profiles-dir . --target dev_oauth
```

`dev_oauth` usa Application Default Credentials (ADC). Si no hay una sesión ADC
válida, el titular debe completar `gcloud auth application-default login` en su
navegador. Una sesión de `gcloud auth login` por sí sola no configura ADC.
No copiar tokens ni archivos de credenciales al repositorio o al chat.

`debug` comprueba la conexión; no construye los modelos. `parse` valida el proyecto
sin ejecutar SQL en BigQuery. Una conexión local válida no demuestra que CI esté
configurado ni que los marts estén actualizados.

## Identidad candidata

Para el histórico, copiar `ci-profiles.yml.example` como `profiles.yml` en un directorio externo al repo y usar `--profiles-dir /ruta/perfil --target candidate`. Autenticar con ADC/WIF de la identidad autorizada y fijar `DBT_RAW_DATASET=raw_cap4_candidate_dev`. El CLI crea el perfil de transformación aislado y establece sus variables; preferir ese recorrido a comandos de build manuales. [Guía CLI](../../pipeline/CLI.md).

Los perfiles `dev_oauth`/`dev_impersonated` del ejemplo anterior apuntan a datasets compartidos; no son la ruta de aceptación histórica y no deben usarse para reemplazarlos. `debug` verifica conectividad, sin construir modelos. WIF de GitHub tiene identidades separadas y restricciones main/workflow/ambiente; el workflow de datos está desactivado y su primera ejecución real sigue pendiente.

El workflow de checks de PR ejecuta pruebas offline, parse y build frontend, sin autenticación cloud ni ejecución SQL. Una conexión local no demuestra operación del runner ni aprobación del snapshot.

## Por qué staging e intermediate

Son responsabilidades del SQL, no dos motores distintos:

| Capa | Trabajo real en este proyecto | Materialización |
| --- | --- | --- |
| `stg_produccion_pozo_mes` | Tipos, nombres/unidades, mes, deduplicación y recorte Vaca Muerta no convencional | Vista |
| `int_produccion_vm_noconv` | Clave pozo-mes y días calendario del mes | Vista |
| `fct_well_month` y marts derivados | Base analítica materializada y agregados por operador/área | Tabla |

La capa intermedia es pequeña y sólo alimenta `fct_well_month`. Mantener una carpeta
intermediate no es una exigencia de dbt. Su utilidad actual es separar los campos
derivados de la limpieza de origen; no hace joins complejos ni agrega fuentes.
El filtro de negocio ya está en staging: esta es la implementación vigente,
no una frontera idealizada. Reubicar ese filtro o simplificar el modelo requeriría
verificar equivalencia de resultados y actualizar tests/contratos; este setup
no modifica la semántica de los modelos.

Las vistas no almacenan una copia adicional de las filas; las consultas que las
usan sí pueden consumir cómputo de BigQuery.
