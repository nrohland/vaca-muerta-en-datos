# ADR 0005 — Precios y valorización en la capa de datos

Estado: implementado en candidato; decisión de gas internacional autorizada el 12 de octubre de 2026. Validación y alcance actual en spec 017 y evidencia de orquestación/export.

## Problema

La primera versión modelaba volúmenes en dbt, pero llevaba precios al frontend como artefacto independiente y calculaba la valoración principal en TypeScript. Esto fragmenta la definición de la métrica y dificulta reproducir una publicación completa desde la misma cadena de datos.

## Decisión

Ingerir Brent EIA y Henry Hub mensual EIA como fuentes mensuales con recurso, fecha, unidades, hash y revisiones. BigQuery conserva el raw. dbt normaliza las referencias y cruza el precio del mismo mes con los volúmenes de meses aceptados. Los marts/export entregan importes, bases, variaciones y estados de disponibilidad; el frontend presenta los resultados.

Seeds para catálogos, factores/metodologías estables y un histórico temporal explícitamente versionado. No mantener cotizaciones revisables con edición manual del seed como solución permanente. [dbt recomienda seeds para datos estáticos o que cambian poco](https://docs.getdbt.com/docs/build/seeds).

## Contratos

Precio: producto × mes × benchmark × versión. No sumar referencias alternativas ni categorías ya agregadas. Petróleo: Brent mensual USD/bbl. Gas: Henry Hub mensual USD/MMBtu, con equivalencia energética de referencia EIA explícita y versionada. Es una estimación internacional, no un precio realizado ni calorificidad medida de Vaca Muerta. [Definición](../../specs/017-international-gas-reference.md). Los huecos permanecen nulos; comparaciones y YTD exigen todas las bases/precios necesarios. Valor bruto de referencia no es ingreso realizado.

## Cierre operativo

Tests de unicidad/unidades/precios/cobertura, snapshot revisions, gates de freshness por fuente y por período económico, conciliación entidad-total, idempotencia de cargas y vínculo de manifiestos. Integrar marts/exportadores candidatos existentes; configurar identidad de dbt; encadenar extracción y build/tests antes del release. La promoción pública requiere aprobación separada.

## Estado actual verificable

El browser consume el export de `fct_dashboard_month`, con importes USD, bases exactas y YTD persistidos en dbt. Las cotizaciones del bundle se reconstruyen desde la misma carga raw y se ligan por hashes. El consumidor no multiplica volumen por precio. El recorrido histórico de transformación/export/contrato y build está validado localmente y en [runner GitHub](../evidence/github-actions/README.md). La demo está publicada con el snapshot preliminar; la ingesta automática está pausada. Publicar la UI no aprueba ni actualiza cotizaciones. [Evidencia](../archive/evidence/orchestration-export/README.md).
