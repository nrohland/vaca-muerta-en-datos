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

## Identidad de ejecución

- Desarrollo personal: `dev_oauth`, con la identidad del usuario autenticado.
- Ejecución con permisos de dbt: `dev_impersonated`, con ADC y la cuenta
  `vm-pulse-dbt@vaca-muerta-pulse.iam.gserviceaccount.com`. Requiere que el usuario
  tenga `roles/iam.serviceAccountTokenCreator` **sobre esa cuenta**, no sobre todo
  el proyecto. Este perfil no concede el permiso por sí mismo.
- GitHub Actions: requiere su propia autenticación. Las credenciales locales no
  se transfieren al runner. El CI actual sólo ejecuta `deps` y `parse`.
  Preferir federación de identidad para automatización; no reutilizar la cuenta
  de extracción ni subir una clave como solución implícita.

Ambos perfiles locales apuntan a desarrollo: `raw_cap4_dev` → `stg_cap4_dev` →
`int_cap4_dev` → `marts_cap4_dev`, en `vaca-muerta-pulse`, región `US`.
El perfil `prod` existente no debe ejecutarse por accidente.

Antes de construir marts, comprobar cobertura del raw y confirmar qué modelos
de publicación están integrados. Un `dbt build` exitoso no aprueba automáticamente
un nuevo snapshot ni lo publica en la aplicación.

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
