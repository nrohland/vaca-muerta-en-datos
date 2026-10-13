# dbt — Vaca Muerta en Datos

Modelado SQL sobre BigQuery: producción física, dimensiones, referencias de precio y agregados persistidos para las cinco vistas. La aplicación consume el export de `fct_dashboard_month`, sin repetir la valorización en el browser.

## Capas

- **Staging:** tipos, claves y campos de origen normalizados.
- **Intermediate:** universo Vaca Muerta no convencional y reglas reutilizadas.
- **Marts:** pozo × mes, dimensiones, entidades, tasas, valores USD y contrato del dashboard.
- **Seeds:** agrupamientos estables de operadores. Brent/Henry Hub cambiantes provienen de raw.

Intermediate no es obligatorio entre cada staging y cada fact. `stg_monthly_reference_price` valida producto × mes y alimenta directamente la fact de valorización; el cambio de grano ocurre al cruzarla con producción. [Linaje generado](../docs/lineage/README.md).

## Ejecución

Python 3.12, versiones fijadas en `requirements.txt` y paquetes resueltos en `package-lock.yml`. Usar el [CLI histórico](../pipeline/CLI.md) para el recorrido que aplica gates, freshness, parse, compile, build, export y validación del consumidor.

Para configuración local: [ADC y perfiles](docs/local-setup.md). Credenciales fuera del repo; `profiles.yml.example` y `ci-profiles.yml.example` contienen configuración de ejemplo. La ruta candidata escribe sólo datasets aislados. No ejecutar scripts IAM para suplir problemas de autenticación.

## Calidad y performance

La ejecución integrada validó **106/106 nodos**: 12 modelos, 1 seed, 83 tests de datos y 10 unit tests, sin warnings, errores o skips. Se comprueban claves, unidades, cobertura calendario, agregados, valorización, comparaciones y YTD. [Evidencia actual](../docs/evidence/orchestration-export/README.md).

`audit_helper` compara hechos físicos; `dbt_project_evaluator` evalúa estructura sobre metadata. Sus advertencias de arquitectura no equivalen a fallos de datos. Los reportes registran tiempos, bytes y slot-ms reales; no se deduce costo de una vista sólo de su CREATE. [Herramientas y límites](docs/quality-and-performance.md), [auditoría histórica](../docs/evidence/historical-dbt/README.md).

Los prototipos de completaciones se retiraron del árbol vigente; no forman parte de V1. Sin fuente validada, la UI no presenta esas métricas. El acceso federado y la ejecución local están preparados; falta probar el runner real de GitHub después de promoción autorizada. La automatización sigue desactivada.
