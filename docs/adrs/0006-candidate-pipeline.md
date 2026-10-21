# ADR 0006 — Pipeline candidato aislado

**Estado:** implementado y validado localmente y en GitHub.

## Contexto

La ruta inicial recargaba un recurso 2025 y CI sólo comprobaba parse. El raw compartido contenía varios años y no podía recrearse con una carga monoanual. El CSV oficial mostró mayor cobertura que DataStore; la aceptación exige conciliar historia, clasificaciones y áreas.

## Decisión vigente

Un [CLI compartido](../../pipeline/CLI.md) prepara cuatro CSV 2023–2026 y Brent/Henry Hub, carga raw aislado, comprueba cobertura/freshness/linaje, ejecuta dbt y exporta el contrato del dashboard. El corte fijo enero 2023–agosto 2026 excluye septiembre parcial. La ruta antigua CKAN/Meltano se retiró del árbol vigente.

Extracción escribe sólo `raw_cap4_candidate_dev`; dbt lee ese raw y construye `stg_cap4_candidate_dev`, `int_cap4_candidate_dev`, `marts_cap4_candidate_dev`. Cuentas separadas y WIF restringido por repo/propietario, main, workflow y ambientes; sin claves permanentes nuevas. El cron preparado sigue desactivado.

Se comprueban SHA de bytes retenidos, cronología, grano, conteos, unidades y agregados. Los hashes no prueban por sí solos autenticidad del transporte ni equivalencia de cada celda warehouse/CSV. Los recursos oficiales redirigen a HTTP público: host/ruta limitados y sin credenciales. Cargas atómicas por tabla, no transacción conjunta producción/precios. Consulta máxima 1 GiB por job, no costo total del run.

El export lee marts, reconstruye cotizaciones desde la misma carga y liga manifiestos. Los gates físicos bloquean revisiones sin evidencia; el bundle se escribe completo en staging temporal. El frontend presenta USD persistido, no recalcula valorización. Seeds sólo para catálogos estables.

## Consecuencias y verificación

Aislamiento permite validar sin reemplazar datasets compartidos. Preparación pública precede WIF; uploads sólo metadata JSON sanitizada. Sin cambios IAM, push, promoción o despliegue implícitos. El recorrido integrado local pasó nueve etapas y 106/106 nodos dbt limpios; reutilizó carga fresca aceptada, no una nueva descarga/ingesta. [Evidencia](../evidence/orchestration-export/README.md).

WIF y el pipeline pasaron en [runner GitHub real](../evidence/github-actions/README.md). La [demo está publicada en Vercel](../vercel.md) con el snapshot preliminar. El monitor de meses/rectificativas existe, pero está pausado junto con la carga por problemas de conectividad de los runners con Energía. La reactivación exige resolver acceso, validar la corrida y revisar la promoción del nuevo snapshot; no se deduce del deploy de la interfaz. No ampliar permisos ni confianza de rama para simular la prueba.
